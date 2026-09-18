"""
backend/routers/columns.py

Separation column endpoints: Absorber, Stripper, DistillationColumn,
plus the read-only reference data the column forms depend on
(column internals catalog, gas/solvent absorption pairs, solvents).

POST /solve/absorber                    → size a gas absorption column
POST /solve/stripper                    → size a solvent regeneration column
POST /solve/distillation                → FUG shortcut distillation design
GET  /solve/reference/column-internals  → packing/tray catalog for ColumnInternalsPanel
GET  /solve/reference/absorption-pairs  → gas/solvent Henry's-law pairs
GET  /solve/reference/solvents          → solvent property catalog
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from backend.schemas.units.absorber_schema import AbsorberRequest, AbsorberResponse
from backend.schemas.units.stripper_schema import StripperRequest, StripperResponse
from backend.schemas.units.distillation_schema import (
    DistillationRequest,
    DistillationResponse,
)

from simulation.units.absorber import Absorber
from simulation.units.stripper import Stripper
from simulation.units.distillation import DistillationColumn, DistComponent
from simulation.units.column_catalog import (
    COLUMN_INTERNAL_CATALOG,
    STRUCTURED_PACKING_CATALOG,
    TRAY_CATALOG,
)
from simulation.core.exceptions import SimulationError

router = APIRouter(prefix="/solve", tags=["Columns"])

_DATA_DIR = Path(__file__).parent.parent.parent / "simulation" / "data"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_absorber_from_request(req: AbsorberRequest) -> Absorber:
    return Absorber(
        unit_id=req.unit_id,
        internal_type=req.internal_type,
        internal_key=req.internal_key,
        column_diameter_m=req.column_diameter_m,
        operating_pressure_Pa=req.P_kPa * 1000.0,
        gas_component=req.gas_component,
        solvent_id=req.solvent_id,
        y_in=req.y_in,
        y_out=req.y_out,
        x_in=req.x_in,
        G_mol_s=req.G_mol_s,
        L_mol_s=req.L_mol_s,
        T_K=req.T_C + 273.15,
        L_G_ratio_multiplier=req.L_G_ratio_multiplier,
    )


def _build_stripper_from_request(req: StripperRequest) -> Stripper:
    return Stripper(
        unit_id=req.unit_id,
        internal_type=req.internal_type,
        internal_key=req.internal_key,
        column_diameter_m=req.column_diameter_m,
        operating_pressure_Pa=req.P_kPa * 1000.0,
        stripping_agent=req.stripping_agent,
        gas_component=req.gas_component,
        solvent_id=req.solvent_id,
        x_in=req.x_in,
        x_out=req.x_out,
        y_in=req.y_in,
        L_mol_s=req.L_mol_s,
        G_mol_s=req.G_mol_s,
        T_K=req.T_C + 273.15,
        L_G_ratio_multiplier=req.L_G_ratio_multiplier,
    )


def _build_distillation_from_request(req: DistillationRequest) -> DistillationColumn:
    components = [
        DistComponent(
            name=c.name,
            z=c.z,
            alpha=c.alpha,
            is_light_key=c.is_light_key,
            is_heavy_key=c.is_heavy_key,
            x_distillate=c.x_distillate,
            T_boil_K=c.T_boil_K,
            MW=c.MW,
        )
        for c in req.components
    ]

    kwargs = dict(
        unit_id=req.unit_id,
        components=components,
        F=req.F_mol_s,
        q=req.q,
        R_Rmin_ratio=req.R_Rmin_ratio,
        tray_efficiency=req.tray_efficiency,
        condenser_type=req.condenser_type,
        latent_heat=req.latent_heat_J_mol,
    )
    if req.P_col_kPa is not None:
        kwargs["P_col"] = req.P_col_kPa * 1000.0
    if req.feed_T_C is not None:
        kwargs["feed_T"] = req.feed_T_C + 273.15
    if req.Cp_feed_J_molK is not None:
        kwargs["Cp_feed"] = req.Cp_feed_J_molK

    return DistillationColumn(**kwargs)


def _error_detail(unit_id: str, exc: Exception) -> dict:
    return {"error_type": type(exc).__name__, "message": str(exc), "unit_id": unit_id}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/absorber",
    response_model=AbsorberResponse,
    summary="Size a counter-current gas absorption column",
    description="""
Kremser-equation shortcut sizing for a packed or trayed gas absorber.

Computes minimum and operating solvent rate, number of theoretical
stages, hydraulic column diameter (flooding correlation), packed
height or tray count, ASME wall thickness, and absorption heat duty.
    """,
)
async def solve_absorber(
    request: AbsorberRequest,
    include_log: bool = Query(True, description="Include step-by-step calculation log"),
) -> AbsorberResponse:
    try:
        absorber = _build_absorber_from_request(request)
        absorber.solve()
        return AbsorberResponse.from_unit(absorber, include_log=include_log)
    except SimulationError as e:
        raise HTTPException(status_code=422, detail=_error_detail(request.unit_id, e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=_error_detail(request.unit_id, e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(request.unit_id, e))


@router.post(
    "/stripper",
    response_model=StripperResponse,
    summary="Size a solvent-regeneration stripping column",
    description="""
Kremser-equation shortcut sizing for a packed or trayed stripper
(solvent regenerator). Computes minimum and operating stripping gas
rate, number of theoretical stages, column hydraulics, ASME wall
thickness, and — for steam stripping — reboiler/condenser duties and
steam consumption.
    """,
)
async def solve_stripper(
    request: StripperRequest,
    include_log: bool = Query(True, description="Include step-by-step calculation log"),
) -> StripperResponse:
    try:
        stripper = _build_stripper_from_request(request)
        stripper.solve()
        return StripperResponse.from_unit(stripper, include_log=include_log)
    except SimulationError as e:
        raise HTTPException(status_code=422, detail=_error_detail(request.unit_id, e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=_error_detail(request.unit_id, e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(request.unit_id, e))


@router.post(
    "/distillation",
    response_model=DistillationResponse,
    summary="Design a distillation column via the FUG shortcut method",
    description="""
Fenske-Underwood-Gilliland shortcut design for binary or
multicomponent (petroleum pseudo-component) distillation.

Returns N_min (Fenske), R_min (Underwood), N_theoretical (Gilliland),
feed stage (Kirkbride), condenser/reboiler duties, product
compositions, and — for binary systems — a full McCabe-Thiele
diagram dataset.
    """,
)
async def solve_distillation(
    request: DistillationRequest,
    include_log: bool = Query(True, description="Include step-by-step calculation log"),
) -> DistillationResponse:
    try:
        column = _build_distillation_from_request(request)
        column.solve()
        return DistillationResponse.from_unit(column, include_log=include_log)
    except SimulationError as e:
        raise HTTPException(status_code=422, detail=_error_detail(request.unit_id, e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=_error_detail(request.unit_id, e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_error_detail(request.unit_id, e))


# ── Reference data for the column forms ───────────────────────────────────────

@router.get(
    "/reference/column-internals",
    summary="Packing and tray catalog for ColumnInternalsPanel",
    description="Returns { random_packing: {...}, structured_packing: {...}, tray: {...} }, "
                 "each keyed by catalog key (matches Absorber/Stripper `internal_type`/`internal_key`).",
)
async def get_column_internals() -> dict:
    random_packing = {
        k: v for k, v in COLUMN_INTERNAL_CATALOG.items()
        if v.get("type") == "random_packing"
    }
    structured_packing = {
        k: v for k, v in COLUMN_INTERNAL_CATALOG.items()
        if v.get("type") == "structured_packing"
    }
    # STRUCTURED_PACKING_CATALOG is the more detailed, canonical source —
    # it wins on any overlapping key (e.g. MELLAPAK_250Y appears in both).
    structured_packing.update(STRUCTURED_PACKING_CATALOG)

    return {
        "random_packing": random_packing,
        "structured_packing": structured_packing,
        "tray": TRAY_CATALOG,
    }


@router.get(
    "/reference/absorption-pairs",
    summary="Gas/solvent Henry's-law pairs for AbsorberForm / StripperForm",
    description="Returns { gas_component: [ {solvent_id, H_ref, dH_sol, T_ref}, ... ] }, "
                 "read from simulation/data/solubility_data.json.",
)
async def get_absorption_pairs() -> dict:
    path = _DATA_DIR / "solubility_data.json"
    try:
        with open(path) as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Reference data file not found: {path}")

    pairs: dict[str, list] = {}
    for entry in raw.get("pairs", []):
        gas = entry.get("gas_component")
        if not gas:
            continue
        pairs.setdefault(gas, []).append({
            "solvent_id": entry.get("liquid_solvent"),
            # NOTE: simulation/units/absorber.py & stripper.py look up
            # solubility_data.json directly using keys H_ref/T_ref/dH_sol,
            # which this data file does not actually contain (it stores
            # K_value_ref/T_ref_K/dH_sol_J_mol instead) — that mismatch
            # predates this router and means those two modules silently
            # fall back to hardcoded defaults rather than these values.
            # Surfaced here under the names the frontend already expects.
            "H_ref": entry.get("K_value_ref"),
            "dH_sol": entry.get("dH_sol_J_mol"),
            "T_ref": entry.get("T_ref_K"),
        })
    return pairs


@router.get(
    "/reference/solvents",
    summary="Solvent property catalog for AbsorberForm / StripperForm",
    description="Returns { solvent_id: {name, MW, properties, compatible_gases, ...} }, "
                 "read from simulation/data/solvent_properties.json.",
)
async def get_solvents() -> dict:
    path = _DATA_DIR / "solvent_properties.json"
    try:
        with open(path) as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Reference data file not found: {path}")

    solvents = {}
    for entry in raw.get("solvents", []):
        solvent_id = entry.get("solvent_id")
        if not solvent_id:
            continue
        solvents[solvent_id] = {
            "name": entry.get("name"),
            "formula": entry.get("formula"),
            "MW": entry.get("MW"),
            "compatible_gases": entry.get("compatible_gases", []),
            "max_operating_T_C": entry.get("max_operating_T_C"),
            "notes": entry.get("notes"),
            **entry.get("properties", {}),
        }
    return solvents
