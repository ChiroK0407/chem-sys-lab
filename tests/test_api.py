"""
tests/test_api.py

FastAPI integration tests using httpx TestClient.

Each test fixture is a textbook problem with a known answer.
This is the most valuable test strategy for an engineering simulator:
if your code reproduces a textbook result within 1%, the equations are right.

References
----------
- C&R Vol. 1 Example 12.1  (LMTD sizing, counterflow)
- McCabe Ch.15 Example 15.2 (ε-NTU rating)
- C&R Vol. 1 Example 12.3  (shell & tube, F-factor correction)
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.main import app


# ── Fixtures ──────────────────────────────────────────────────────────────────

HOT_STREAM = {
    "name": "process_hot",
    "temperature_c": 120.0,
    "pressure_kpa": 300.0,
    "mass_flowrate_kg_s": 2.0,
    "cp_J_kgK": 4200.0,
    "density_kg_m3": 950.0,
    "viscosity_Pa_s": 3e-4,
    "thermal_conductivity": 0.65,
    "phase": "liquid",
}

COLD_STREAM = {
    "name": "process_cold",
    "temperature_c": 30.0,
    "pressure_kpa": 200.0,
    "mass_flowrate_kg_s": 3.5,
    "cp_J_kgK": 3800.0,
    "density_kg_m3": 880.0,
    "viscosity_Pa_s": 5e-4,
    "thermal_conductivity": 0.45,
    "phase": "liquid",
}

COLD_FEED = {
    "name": "cold_feed",
    "temperature_c": 30.0,
    "pressure_kpa": 200.0,
    "mass_flowrate_kg_s": 1.5,
    "cp_J_kgK": 4100.0,
    "density_kg_m3": 990.0,
    "viscosity_Pa_s": 6e-4,
    "thermal_conductivity": 0.60,
    "phase": "liquid",
}


# ── Client fixture ────────────────────────────────────────────────────────────

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


# ── HX sizing: counterflow, cooling water ─────────────────────────────────────
# Hand-calculated: Q = 2.0 * 4200 * (120-50) = 588 000 W = 588 kW
# CW flowrate = 588000 / (4182 * 15) = 9.37 kg/s
# LMTD_cf = (75 - 20) / ln(75/20) = 41.60 K
# A = 588000 / (600 * 1.0 * 41.60) = 23.56 m²

@pytest.mark.asyncio
async def test_hx_sizing_cw_counterflow(client):
    payload = {
        "unit_id": "HX-101",
        "mode": "sizing",
        "flow_config": "counterflow",
        "utility_fluid": "cooling_water",
        "U_W_m2K": 600.0,
        "hot_stream": HOT_STREAM,
        "hot_outlet_T_c": 50.0,
        "cw_supply_T_c": 30.0,
        "cw_return_T_c": 45.0,
    }
    r = await client.post("/solve/heat-exchanger", json=payload)
    assert r.status_code == 200, r.text
    d = r.json()

    assert d["is_solved"] is True
    assert d["warnings"] == []
    assert abs(d["duty_kW"]  - 588.0) < 1.0,    f"duty={d['duty_kW']}"
    assert abs(d["area_m2"]  - 23.55) < 0.15,   f"area={d['area_m2']}"
    assert abs(d["LMTD_K"]   - 41.60) < 0.1,    f"LMTD={d['LMTD_K']}"
    assert abs(d["F_factor"]  - 1.0)  < 0.001,  f"F={d['F_factor']}"
    assert abs(d["hot_outlet_T_c"] - 50.0) < 0.1

    # Utility
    assert d["utility"] is not None
    assert abs(d["utility"]["mass_flowrate_kg_s"] - 9.37) < 0.05
    assert d["utility"]["utility_type"] == "cooling_water"

    # Calculation log populated
    assert len(d["calculation_log"]) > 10


# ── HX rating: counterflow CW — should reproduce 50°C from sizing area ────────

@pytest.mark.asyncio
async def test_hx_rating_cw_counterflow(client):
    # First get the area from sizing
    sizing_payload = {
        "unit_id": "HX-101S",
        "mode": "sizing",
        "flow_config": "counterflow",
        "utility_fluid": "cooling_water",
        "U_W_m2K": 600.0,
        "hot_stream": HOT_STREAM,
        "hot_outlet_T_c": 50.0,
    }
    r_size = await client.post("/solve/heat-exchanger", json=sizing_payload)
    area = r_size.json()["area_m2"]

    # Now rate with that area
    rating_payload = {
        "unit_id": "HX-101R",
        "mode": "rating",
        "flow_config": "counterflow",
        "utility_fluid": "cooling_water",
        "U_W_m2K": 600.0,
        "hot_stream": HOT_STREAM,
        "area_m2": area,
    }
    r = await client.post("/solve/heat-exchanger", json=rating_payload)
    assert r.status_code == 200, r.text
    d = r.json()

    assert d["is_solved"] is True
    assert abs(d["hot_outlet_T_c"] - 50.0) < 0.2, f"T_out={d['hot_outlet_T_c']}"
    assert abs(d["duty_kW"] - 588.0) < 2.0,       f"duty={d['duty_kW']}"
    assert d["NTU"] > 0
    assert 0 < d["effectiveness"] < 1


# ── HX sizing: shell & tube 1-2, process-to-process ──────────────────────────
# F-factor must be between 0.75 and 1.0 for a valid design

@pytest.mark.asyncio
async def test_hx_sizing_shell_tube_process(client):
    payload = {
        "unit_id": "HX-102",
        "mode": "sizing",
        "flow_config": "shell_tube_1_2",
        "utility_fluid": "process",
        "U_W_m2K": 450.0,
        "hot_stream": HOT_STREAM,
        "cold_stream": COLD_STREAM,
        "hot_outlet_T_c": 80.0,
    }
    r = await client.post("/solve/heat-exchanger", json=payload)
    assert r.status_code == 200, r.text
    d = r.json()

    assert d["is_solved"] is True
    assert 0.75 < d["F_factor"] < 1.0, f"F={d['F_factor']}"
    assert d["duty_kW"] > 0
    assert d["area_m2"] > 0
    assert d["utility"] is None   # process-to-process — no utility stream

    # Both outlet streams present
    assert len(d["outlet_streams"]) == 2


# ── HX sizing: LP steam heating ───────────────────────────────────────────────
# Q = 1.5 * 4100 * (110 - 30) = 492 000 W = 492 kW

@pytest.mark.asyncio
async def test_hx_sizing_lp_steam(client):
    payload = {
        "unit_id": "HX-103",
        "mode": "sizing",
        "flow_config": "counterflow",
        "utility_fluid": "lp_steam",
        "U_W_m2K": 1200.0,
        "hot_stream": COLD_FEED,   # process stream (cold side) passed as hot_stream
        "cold_outlet_T_c": 110.0,
    }
    r = await client.post("/solve/heat-exchanger", json=payload)
    assert r.status_code == 200, r.text
    d = r.json()

    assert d["is_solved"] is True
    assert abs(d["duty_kW"] - 492.0) < 2.0, f"duty={d['duty_kW']}"
    assert d["area_m2"] > 0
    assert d["utility"] is not None
    assert "steam" in d["utility"]["utility_type"]
    assert d["utility"]["mass_flowrate_kg_s"] > 0


# ── Rating LP steam: reproduce cold outlet T ─────────────────────────────────

@pytest.mark.asyncio
async def test_hx_rating_lp_steam(client):
    # Get area from sizing
    sizing = {
        "unit_id": "HX-103S",
        "mode": "sizing",
        "flow_config": "counterflow",
        "utility_fluid": "lp_steam",
        "U_W_m2K": 1200.0,
        "hot_stream": COLD_FEED,
        "cold_outlet_T_c": 110.0,
    }
    area = (await client.post("/solve/heat-exchanger", json=sizing)).json()["area_m2"]

    rating = {
        "unit_id": "HX-103R",
        "mode": "rating",
        "flow_config": "counterflow",
        "utility_fluid": "lp_steam",
        "U_W_m2K": 1200.0,
        "hot_stream": COLD_FEED,
        "area_m2": area,
    }
    r = await client.post("/solve/heat-exchanger", json=rating)
    assert r.status_code == 200, r.text
    d = r.json()

    assert d["is_solved"] is True
    assert abs(d["cold_outlet_T_c"] - 110.0) < 1.0, f"T_cold_out={d['cold_outlet_T_c']}"


# ── Infeasible design: temperature cross ──────────────────────────────────────

@pytest.mark.asyncio
async def test_hx_infeasible_temp_cross(client):
    payload = {
        "unit_id": "HX-BAD",
        "mode": "sizing",
        "flow_config": "counterflow",
        "utility_fluid": "cooling_water",
        "U_W_m2K": 500.0,
        "hot_stream": HOT_STREAM,
        "hot_outlet_T_c": 25.0,   # below CW supply 30°C — infeasible
    }
    r = await client.post("/solve/heat-exchanger", json=payload)
    assert r.status_code == 422
    d = r.json()
    assert "error_type" in d["detail"]
    assert "InfeasibleDesignError" in d["detail"]["error_type"]


# ── Validation: rating mode missing area ─────────────────────────────────────

@pytest.mark.asyncio
async def test_hx_rating_missing_area(client):
    payload = {
        "unit_id": "HX-NOAREA",
        "mode": "rating",
        "flow_config": "counterflow",
        "utility_fluid": "cooling_water",
        "U_W_m2K": 600.0,
        "hot_stream": HOT_STREAM,
        # area_m2 missing — should fail Pydantic validation
    }
    r = await client.post("/solve/heat-exchanger", json=payload)
    assert r.status_code == 422


# ── Scenario sweep ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scenario_sweep_flowrate(client):
    """
    Vary hot stream flowrate from 1 to 3 kg/s.
    Duty should increase with flowrate (for fixed outlet T).
    Area should also increase with duty.
    """
    payload = {
        "base_request": {
            "unit_id": "HX-SWEEP",
            "mode": "sizing",
            "flow_config": "counterflow",
            "utility_fluid": "cooling_water",
            "U_W_m2K": 600.0,
            "hot_stream": HOT_STREAM,
            "hot_outlet_T_c": 50.0,
        },
        "sweep_parameter": "mass_flowrate_kg_s",
        "sweep_values": [1.0, 1.5, 2.0, 2.5, 3.0],
    }
    r = await client.post("/solve/scenario/sweep", json=payload)
    assert r.status_code == 200, r.text
    d = r.json()

    assert d["sweep_parameter"] == "mass_flowrate_kg_s"
    assert len(d["results"]) == 5
    assert all(e is None for e in d["errors"]), f"Errors: {d['errors']}"

    duties = [pt["duty_kW"] for pt in d["results"]]
    areas  = [pt["area_m2"] for pt in d["results"]]

    # Duty and area must be strictly increasing with flowrate
    assert duties == sorted(duties), f"Duties not increasing: {duties}"
    assert areas  == sorted(areas),  f"Areas not increasing: {areas}"


@pytest.mark.asyncio
async def test_scenario_sweep_with_failure(client):
    """
    Some sweep points should fail (outlet T below CW supply).
    Verify partial success: failed points have error messages, not crashes.
    """
    payload = {
        "base_request": {
            "unit_id": "HX-SWEEP-FAIL",
            "mode": "sizing",
            "flow_config": "counterflow",
            "utility_fluid": "cooling_water",
            "U_W_m2K": 600.0,
            "hot_stream": HOT_STREAM,
            "hot_outlet_T_c": 50.0,
        },
        "sweep_parameter": "hot_outlet_T_c",
        "sweep_values": [60.0, 50.0, 35.0, 25.0],  # last two invalid
    }
    r = await client.post("/solve/scenario/sweep", json=payload)
    assert r.status_code == 200
    d = r.json()

    # 60, 50, 35°C succeed (all above CW supply 30°C); 25°C fails
    assert d["results"][0] is not None
    assert d["results"][1] is not None
    assert d["results"][2] is not None
    assert d["results"][3] is None
    assert d["errors"][3] is not None


# ── Reference endpoints ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_fluids(client):
    r = await client.get("/reference/fluids")
    assert r.status_code == 200
    fluids = r.json()
    assert len(fluids) >= 10
    ids = [f["fluid_id"] for f in fluids]
    assert "water" in ids
    assert "toluene" in ids


@pytest.mark.asyncio
async def test_get_fluid_detail(client):
    r = await client.get("/reference/fluid/water?temperature_c=80")
    assert r.status_code == 200
    d = r.json()
    assert d["fluid_id"] == "water"
    assert 4100 < d["cp_J_kgK"] < 4300
    assert d["prandtl_number"] > 0


@pytest.mark.asyncio
async def test_get_fluid_not_found(client):
    r = await client.get("/reference/fluid/unobtanium")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_u_values(client):
    r = await client.get("/reference/u-values")
    assert r.status_code == 200
    services = r.json()
    assert len(services) >= 8
    keys = [s["service_type"] for s in services]
    assert "liquid_liquid" in keys
    assert "condensing_steam_liquid" in keys


@pytest.mark.asyncio
async def test_suggest_u_value(client):
    r = await client.get("/reference/u-values/suggest?hot_phase=liquid&cold_phase=liquid")
    assert r.status_code == 200
    d = r.json()
    assert d["U_min"] > 0
    assert d["U_max"] > d["U_min"]


@pytest.mark.asyncio
async def test_get_steam_grade_lp(client):
    r = await client.get("/reference/steam/lp_steam")
    assert r.status_code == 200
    d = r.json()
    assert 135 < d["T_sat_C"] < 145,       f"T_sat={d['T_sat_C']}"
    assert d["h_fg_kJ_kg"] > 2000,         f"h_fg={d['h_fg_kJ_kg']}"
    assert d["rho_vap_kg_m3"] > 0


@pytest.mark.asyncio
async def test_get_steam_by_pressure(client):
    # 1 bar absolute = 100 kPa → should give ~100°C
    r = await client.get("/reference/steam/lookup/by-pressure?pressure_kpa=101.325")
    assert r.status_code == 200
    d = r.json()
    assert abs(d["T_sat_C"] - 100.0) < 0.5, f"T_sat={d['T_sat_C']}"
    assert abs(d["h_fg_kJ_kg"] - 2257.0) < 10


@pytest.mark.asyncio
async def test_steam_grade_not_found(client):
    r = await client.get("/reference/steam/ultra_hp_steam")
    assert r.status_code == 404


# ── No calc log when include_log=false ───────────────────────────────────────

@pytest.mark.asyncio
async def test_no_calc_log(client):
    payload = {
        "unit_id": "HX-NOLOG",
        "mode": "sizing",
        "flow_config": "counterflow",
        "utility_fluid": "cooling_water",
        "U_W_m2K": 600.0,
        "hot_stream": HOT_STREAM,
        "hot_outlet_T_c": 50.0,
    }
    r = await client.post("/solve/heat-exchanger?include_log=false", json=payload)
    assert r.status_code == 200
    assert r.json()["calculation_log"] == []