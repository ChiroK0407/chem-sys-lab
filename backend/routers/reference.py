"""
backend/routers/reference.py

Read-only reference data endpoints.
These are called by the frontend to populate dropdowns,
show U-value hints, and display steam table data.

GET /reference/fluids                → list all fluid IDs
GET /reference/fluid/{fluid_id}      → properties at optional temperature
GET /reference/u-values              → all HX service types with U ranges
GET /reference/u-values/suggest      → suggest U range for given phases
GET /reference/steam/{grade}         → saturation props for lp/mp/hp steam
GET /reference/steam/by-pressure     → saturation props at arbitrary pressure
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from backend.schemas.reference_schema import (
    FluidSummary,
    FluidDetailOut,
    UValueEntry,
    SteamSaturationOut,
)
from simulation.data.loader import (
    list_fluids,
    get_fluid_properties,
    list_u_services,
    get_u_range,
    suggest_u_value,
    get_steam_grade_properties,
    get_steam_saturation,
)

router = APIRouter(prefix="/reference", tags=["Reference Data"])


# ── Fluid endpoints ───────────────────────────────────────────────────────────

@router.get(
    "/fluids",
    response_model=List[FluidSummary],
    summary="List all available fluids",
)
async def list_available_fluids() -> List[FluidSummary]:
    """
    Returns all fluid IDs available in components.json.
    Used to populate the fluid selector dropdown in the frontend.
    """
    import json
    from pathlib import Path
    data_path = Path(__file__).parent.parent.parent / "simulation" / "data" / "components.json"
    with open(data_path) as f:
        raw = json.load(f)

    result = []
    for fluid_id, entry in raw.items():
        if fluid_id.startswith("_"):
            continue
        result.append(FluidSummary(
            fluid_id=fluid_id,
            name=entry["name"],
            phase_at_ref=entry["phase_at_ref"],
            boiling_point_C=(
                entry["boiling_point"] - 273.15
                if entry.get("boiling_point") else None
            ),
            molecular_weight=entry.get("molecular_weight"),
            typical_use=entry.get("typical_use", []),
        ))
    return result


@router.get(
    "/fluid/{fluid_id}",
    response_model=FluidDetailOut,
    summary="Get fluid properties at an optional temperature",
)
async def get_fluid_detail(
    fluid_id: str,
    temperature_c: Optional[float] = Query(
        None, description="Temperature [°C]. Returns reference T properties if omitted."
    ),
) -> FluidDetailOut:
    """
    Returns physical properties for a fluid at the requested temperature.
    Used when the user selects a fluid in the stream editor — populates
    cp, density, viscosity, thermal conductivity automatically.
    """
    try:
        T_K = temperature_c + 273.15 if temperature_c is not None else None
        props = get_fluid_properties(fluid_id, T_K)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    pr = (props["cp"] * props["viscosity"]) / props["thermal_conductivity"]

    return FluidDetailOut(
        fluid_id=props["fluid_id"],
        name=props["name"],
        cp_J_kgK=props["cp"],
        density_kg_m3=props["density"],
        viscosity_Pa_s=props["viscosity"],
        thermal_conductivity=props["thermal_conductivity"],
        phase=props["phase"],
        T_used_C=props["T_used_K"] - 273.15,
        molecular_weight=props.get("molecular_weight"),
        boiling_point_C=(
            props["boiling_point_K"] - 273.15
            if props.get("boiling_point_K") else None
        ),
        prandtl_number=round(pr, 3),
        source_note=props["source_note"],
    )


# ── U-value endpoints ─────────────────────────────────────────────────────────

@router.get(
    "/u-values",
    response_model=List[UValueEntry],
    summary="List all HX service types with typical U ranges",
)
async def list_u_values() -> List[UValueEntry]:
    """
    Returns all service types from u_values.json.
    Used to populate the HX service type dropdown and show U hints.
    """
    services = list_u_services()
    result = []
    for svc in services:
        u = get_u_range(svc)
        result.append(UValueEntry(
            service_type=u["service_type"],
            U_min=u["U_min"],
            U_max=u["U_max"],
            typical=u["typical"],
            description=u["description"],
            examples=u["examples"],
        ))
    return result


@router.get(
    "/u-values/suggest",
    response_model=UValueEntry,
    summary="Suggest U range based on stream phases",
)
async def suggest_u(
    hot_phase:  str = Query(..., description="hot stream phase: liquid | vapor | mixed"),
    cold_phase: str = Query(..., description="cold stream phase: liquid | vapor | mixed"),
) -> UValueEntry:
    """
    Given the hot and cold stream phases, returns the most appropriate
    U-value range. Used to auto-populate the U field when the user
    selects stream phases in the HX form.
    """
    try:
        u = suggest_u_value(hot_phase, cold_phase)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    return UValueEntry(
        service_type=u["service_type"],
        U_min=u["U_min"],
        U_max=u["U_max"],
        typical=u["typical"],
        description=u["description"],
        examples=u["examples"],
    )


# ── Steam endpoints ───────────────────────────────────────────────────────────

@router.get(
    "/steam/{grade}",
    response_model=SteamSaturationOut,
    summary="Get saturation properties for a named steam grade",
)
async def get_steam_grade(
    grade: str,
) -> SteamSaturationOut:
    """
    Returns saturation properties for `lp_steam`, `mp_steam`, or `hp_steam`.
    Used to auto-populate steam utility side properties in the HX form.
    """
    try:
        props = get_steam_grade_properties(grade)
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Steam grade '{grade}' not found. Use: lp_steam, mp_steam, hp_steam",
        )

    return _steam_props_to_out(grade, props)


@router.get(
    "/steam/lookup/by-pressure",
    response_model=SteamSaturationOut,
    summary="Get saturation properties at an arbitrary pressure",
)
async def get_steam_by_pressure(
    pressure_kpa: float = Query(..., gt=0, description="Saturation pressure [kPa abs]"),
) -> SteamSaturationOut:
    """
    Returns saturation properties at any pressure within the steam table range
    (~101 kPa to ~4200 kPa). Uses linear interpolation between table rows.
    """
    try:
        props = get_steam_saturation(pressure_kpa * 1000.0)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return _steam_props_to_out(f"custom_{pressure_kpa:.0f}kPa", props)


def _steam_props_to_out(grade: str, props: dict) -> SteamSaturationOut:
    return SteamSaturationOut(
        grade=grade,
        T_sat_C=round(props["T_sat_K"] - 273.15, 2),
        P_sat_kPa=round(props["P_sat_Pa"] / 1000.0, 2),
        h_f_kJ_kg=round(props["h_f_J_kg"] / 1000.0, 2),
        h_g_kJ_kg=round(props["h_g_J_kg"] / 1000.0, 2),
        h_fg_kJ_kg=round(props["h_fg_J_kg"] / 1000.0, 2),
        rho_liq_kg_m3=round(props["rho_liq_kg_m3"], 3),
        rho_vap_kg_m3=round(props["rho_vap_kg_m3"], 4),
        cp_liq_J_kgK=round(props["cp_liq_J_kgK"], 1),
        mu_liq_Pa_s=round(props["mu_liq_Pa_s"], 8),
        k_liq_W_mK=round(props["k_liq_W_mK"], 4),
    )