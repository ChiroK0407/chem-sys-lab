"""
backend/routers/units.py

Unit operation endpoints.

POST /solve/heat-exchanger   → size or rate a heat exchanger
POST /scenario/sweep         → parameter sweep over one variable
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.schemas.unit_schemas import (
    HeatExchangerRequest,
    HeatExchangerResponse,
    ScenarioSweepRequest,
    ScenarioSweepResponse,
    PumpRequest,
    PumpResponse,
    MixerRequest,
    MixerResponse,
    SplitterRequest,
    SplitterResponse,
    CSTRRequest,
    CSTRResponse,
    PFRRequest,
    PFRResponse,
)
from simulation.units.heat_exchanger import (
    HeatExchanger,
    HXMode,
    FlowConfig,
    UtilityFluid,
)
from simulation.units.pump import Pump
from simulation.units.mixer import Mixer
from simulation.units.splitter import Splitter
from simulation.units.cstr import CSTR, ThermalMode, ReactorMode
from simulation.units.pfr import PFR
from simulation.core.exceptions import SimulationError

router = APIRouter(prefix="/solve", tags=["Unit Operations"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_hx_from_request(req: HeatExchangerRequest) -> HeatExchanger:
    """
    Instantiate and configure a HeatExchanger from a validated request.
    Does NOT call solve() — caller decides when to solve.
    """
    hx = HeatExchanger(
        unit_id=req.unit_id,
        mode=HXMode(req.mode),
        flow_config=FlowConfig(req.flow_config),
        U=req.U_W_m2K,
        utility_fluid=UtilityFluid(req.utility_fluid),
        area=req.area_m2,
        hot_outlet_T=req.hot_outlet_T_c + 273.15 if req.hot_outlet_T_c is not None else None,
        cold_outlet_T=req.cold_outlet_T_c + 273.15 if req.cold_outlet_T_c is not None else None,
        cw_supply_T=req.cw_supply_T_c + 273.15,
        cw_return_T=req.cw_return_T_c + 273.15,
    )

    # Add inlet streams
    if req.utility_fluid in ("lp_steam", "mp_steam", "hp_steam"):
        # Steam heating: process stream is cold side
        if req.cold_stream is not None:
            hx.add_inlet("cold", req.cold_stream.to_process_stream())
        else:
            # Fallback: user passed hot_stream for a steam unit
            hx.add_inlet("cold", req.hot_stream.to_process_stream())
    else:
        hx.add_inlet("hot", req.hot_stream.to_process_stream())
        if req.cold_stream is not None:
            hx.add_inlet("cold", req.cold_stream.to_process_stream())

    return hx


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/heat-exchanger",
    response_model=HeatExchangerResponse,
    summary="Size or rate a shell-and-tube / double-pipe heat exchanger",
    description="""
**Sizing mode** (`mode: "sizing"`):
- Provide inlet stream(s) and one outlet temperature.
- Returns required heat transfer area A, LMTD, F-factor, utility demand.

**Rating mode** (`mode: "rating"`):
- Provide inlet stream(s) and the exchanger area.
- Returns outlet temperatures, NTU, effectiveness, utility demand.

**Flow configurations:** `counterflow`, `parallelflow`, `shell_tube_1_2`

**Utility fluids:** `cooling_water`, `lp_steam`, `mp_steam`, `hp_steam`, `process`
    """,
)
async def solve_heat_exchanger(
    request: HeatExchangerRequest,
    include_log: bool = Query(True, description="Include step-by-step calculation log"),
) -> HeatExchangerResponse:
    """
    Solve a heat exchanger in sizing or rating mode.

    All simulation errors are caught and returned as HTTP 422
    with a structured error message.
    """
    try:
        hx = _build_hx_from_request(request)
        hx.solve()
        return HeatExchangerResponse.from_unit(hx, include_log=include_log)

    except SimulationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "unit_id": request.unit_id,
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error_type": "ValueError",
                "message": str(e),
                "unit_id": request.unit_id,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_type": type(e).__name__,
                "message": f"Unexpected error: {str(e)}",
                "unit_id": request.unit_id,
            },
        )


@router.post(
    "/scenario/sweep",
    response_model=ScenarioSweepResponse,
    summary="Sweep one parameter across a range and return results for each point",
    description="""
Re-solves the heat exchanger at each value in `sweep_values`,
varying `sweep_parameter` while keeping everything else constant.

**Supported sweep parameters:**
- `mass_flowrate_kg_s`  — vary hot stream flowrate
- `U_W_m2K`            — vary overall HTC
- `hot_outlet_T_c`     — vary target outlet temperature (sizing mode)
- `area_m2`            — vary exchanger area (rating mode)
- `cw_supply_T_c`      — vary CW supply temperature

Returns one summary dict per point. Failed points return `null` in results
and the error message in `errors`.
    """,
)
async def scenario_sweep(
    request: ScenarioSweepRequest,
) -> ScenarioSweepResponse:
    """
    Parameter sweep for sensitivity analysis and scenario comparison.
    """
    results = []
    errors  = []

    for value in request.sweep_values:
        try:
            # Deep-copy the base request and override the sweep parameter
            base = request.base_request.model_copy(deep=True)
            param = request.sweep_parameter

            # Route to the correct field
            if param == "mass_flowrate_kg_s":
                base.hot_stream.mass_flowrate_kg_s = value
            elif param == "U_W_m2K":
                base.U_W_m2K = value
            elif param == "hot_outlet_T_c":
                base.hot_outlet_T_c = value
            elif param == "cold_outlet_T_c":
                base.cold_outlet_T_c = value
            elif param == "area_m2":
                base.area_m2 = value
            elif param == "cw_supply_T_c":
                base.cw_supply_T_c = value
            elif param == "cw_return_T_c":
                base.cw_return_T_c = value
            else:
                raise ValueError(
                    f"sweep_parameter '{param}' is not supported. "
                    f"Supported: mass_flowrate_kg_s, U_W_m2K, hot_outlet_T_c, "
                    f"cold_outlet_T_c, area_m2, cw_supply_T_c, cw_return_T_c"
                )

            hx = _build_hx_from_request(base)
            hx.solve()
            summary = hx.summary()
            # Inject the sweep value for easy plotting
            summary["sweep_value"] = value
            results.append(summary)
            errors.append(None)

        except (SimulationError, ValueError) as e:
            results.append(None)
            errors.append(f"{type(e).__name__}: {str(e)}")
        except Exception as e:
            results.append(None)
            errors.append(f"Unexpected: {str(e)}")

    return ScenarioSweepResponse(
        sweep_parameter=request.sweep_parameter,
        sweep_values=request.sweep_values,
        results=results,
        errors=errors,
    )


@router.post(
    "/pump",
    response_model=PumpResponse,
    summary="Design a centrifugal pump",
    description="""
Computes total head, hydraulic/shaft/motor power, NPSHa (auto-lookup for water),
specific speed, and outlet stream conditions.

Vapour pressure is auto-looked up from steam tables for water. For other fluids,
supply **vapour_pressure_kPa** manually.
    """,
)
async def solve_pump(
    request: PumpRequest,
    include_log: bool = Query(True, description="Include step-by-step calculation log"),
) -> PumpResponse:
    try:
        pump = Pump(
            unit_id=request.unit_id,
            discharge_pressure_Pa=request.discharge_pressure_kPa * 1000,
            discharge_elevation_m=request.discharge_elevation_m,
            suction_elevation_m=request.suction_elevation_m,
            suction_velocity_m_s=request.suction_velocity_m_s,
            discharge_velocity_m_s=request.discharge_velocity_m_s,
            eta_pump=request.eta_pump,
            eta_motor=request.eta_motor,
            npsh_required_m=request.npsh_required_m,
            vapour_pressure_Pa=(
                request.vapour_pressure_kPa * 1000
                if request.vapour_pressure_kPa is not None else None
            ),
            speed_rpm=request.speed_rpm,
        )
        pump.add_inlet("feed", request.feed_stream.to_process_stream())
        pump.solve()
        return PumpResponse.from_unit(pump, include_log=include_log)

    except SimulationError as e:
        raise HTTPException(status_code=422, detail={
            "error_type": type(e).__name__,
            "message": str(e),
            "unit_id": request.unit_id,
        })
    except ValueError as e:
        raise HTTPException(status_code=422, detail={
            "error_type": "ValueError",
            "message": str(e),
            "unit_id": request.unit_id,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error_type": type(e).__name__,
            "message": f"Unexpected error: {str(e)}",
            "unit_id": request.unit_id,
        })


@router.post("/mixer", response_model=MixerResponse,
    summary="Adiabatic stream mixer — N inlets to 1 outlet")
async def solve_mixer(
    request: MixerRequest,
    include_log: bool = Query(True),
) -> MixerResponse:
    try:
        mixer = Mixer(unit_id=request.unit_id, outlet_name=request.outlet_name)
        for i, s in enumerate(request.inlet_streams):
            mixer.add_inlet(f"inlet_{i+1}", s.to_process_stream())
        mixer.solve()
        return MixerResponse.from_unit(mixer, include_log)
    except SimulationError as e:
        raise HTTPException(422, detail={"error_type": type(e).__name__, "message": str(e), "unit_id": request.unit_id})
    except Exception as e:
        raise HTTPException(500, detail={"error_type": type(e).__name__, "message": str(e), "unit_id": request.unit_id})


@router.post("/splitter", response_model=SplitterResponse,
    summary="Stream splitter — 1 inlet to N outlets")
async def solve_splitter(
    request: SplitterRequest,
    include_log: bool = Query(True),
) -> SplitterResponse:
    try:
        splitter = Splitter(
            unit_id=request.unit_id,
            split_fractions=request.split_fractions,
            n_outlets=request.n_outlets,
            outlet_names=request.outlet_names,
        )
        splitter.add_inlet("feed", request.feed_stream.to_process_stream())
        splitter.solve()
        return SplitterResponse.from_unit(splitter, include_log)
    except SimulationError as e:
        raise HTTPException(422, detail={"error_type": type(e).__name__, "message": str(e), "unit_id": request.unit_id})
    except Exception as e:
        raise HTTPException(500, detail={"error_type": type(e).__name__, "message": str(e), "unit_id": request.unit_id})


def _build_reactor(req, cls):
    """Shared factory for CSTR and PFR from request."""
    return cls(
        unit_id=req.unit_id,
        k_ref=req.kinetics.k_ref,
        T_ref=req.kinetics.T_ref_C + 273.15,
        Ea=req.kinetics.Ea_J_mol,
        n=req.kinetics.n_order,
        delta_H_rxn=req.kinetics.delta_H_rxn,
        C_A0=req.kinetics.C_A0_mol_m3,
        MW_A=req.kinetics.MW_A_g_mol,
        mode=ReactorMode(req.operating.mode),
        thermal_mode=ThermalMode(req.operating.thermal_mode),
        T_rxn=req.operating.T_rxn_C + 273.15,
        X_target=req.operating.X_target,
        volume_m3=req.operating.volume_m3,
    )


@router.post("/cstr", response_model=CSTRResponse,
    summary="CSTR — isothermal or adiabatic, any reaction order")
async def solve_cstr(
    request: CSTRRequest,
    include_log: bool = Query(True),
) -> CSTRResponse:
    try:
        reactor = _build_reactor(request, CSTR)
        reactor.add_inlet("feed", request.feed_stream.to_process_stream())
        reactor.solve()
        return CSTRResponse.from_unit(reactor, include_log)
    except SimulationError as e:
        raise HTTPException(422, detail={"error_type": type(e).__name__,
            "message": str(e), "unit_id": request.unit_id})
    except Exception as e:
        raise HTTPException(500, detail={"error_type": type(e).__name__,
            "message": str(e), "unit_id": request.unit_id})


@router.post("/pfr", response_model=PFRResponse,
    summary="PFR — isothermal or adiabatic, any reaction order, with profile data")
async def solve_pfr(
    request: PFRRequest,
    include_log: bool = Query(True),
) -> PFRResponse:
    try:
        reactor = _build_reactor(request, PFR)
        reactor.n_points = request.n_points
        reactor.add_inlet("feed", request.feed_stream.to_process_stream())
        reactor.solve()
        return PFRResponse.from_unit(reactor, include_log)
    except SimulationError as e:
        raise HTTPException(422, detail={"error_type": type(e).__name__,
            "message": str(e), "unit_id": request.unit_id})
    except Exception as e:
        raise HTTPException(500, detail={"error_type": type(e).__name__,
            "message": str(e), "unit_id": request.unit_id})