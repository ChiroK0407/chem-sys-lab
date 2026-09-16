"""
backend/schemas/reference_schema.py

Response models for reference data endpoints:
  GET /reference/fluids
  GET /reference/fluid/{fluid_id}
  GET /reference/u-values
  GET /reference/steam/{grade}
  GET /utilities/report
"""

from __future__ import annotations
from typing import List, Optional, Dict
from pydantic import BaseModel


# ── Fluid reference ───────────────────────────────────────────────────────────

class FluidSummary(BaseModel):
    """One entry in the fluid list."""
    fluid_id:          str
    name:              str
    phase_at_ref:      str
    boiling_point_C:   Optional[float] = None
    molecular_weight:  Optional[float] = None
    typical_use:       List[str] = []


class FluidDetailOut(BaseModel):
    """Full fluid properties at a requested temperature."""
    fluid_id:              str
    name:                  str
    cp_J_kgK:              float
    density_kg_m3:         float
    viscosity_Pa_s:        float
    thermal_conductivity:  float
    phase:                 str
    T_used_C:              float
    molecular_weight:      Optional[float] = None
    boiling_point_C:       Optional[float] = None
    prandtl_number:        Optional[float] = None
    source_note:           str


# ── U-value reference ─────────────────────────────────────────────────────────

class UValueEntry(BaseModel):
    """One HX service type with U range."""
    service_type:  str
    U_min:         float
    U_max:         float
    typical:       float
    description:   str
    examples:      List[str] = []


# ── Steam reference ───────────────────────────────────────────────────────────

class SteamSaturationOut(BaseModel):
    """Saturation properties for one steam grade."""
    grade:           str
    T_sat_C:         float
    P_sat_kPa:       float
    h_f_kJ_kg:       float
    h_g_kJ_kg:       float
    h_fg_kJ_kg:      float   # latent heat
    rho_liq_kg_m3:   float
    rho_vap_kg_m3:   float
    cp_liq_J_kgK:    float
    mu_liq_Pa_s:     float
    k_liq_W_mK:      float


# ── Utility report ────────────────────────────────────────────────────────────

class UtilityReportOut(BaseModel):
    """
    Aggregated utility consumption across the full network or
    a list of solved units.

    Used by the Utility Dashboard page.
    """
    total_cooling_duty_kW:    float = 0.0
    total_heating_duty_kW:    float = 0.0
    total_power_kW:           float = 0.0
    cooling_water_kg_s:       float = 0.0
    lp_steam_kg_s:            float = 0.0
    mp_steam_kg_s:            float = 0.0
    hp_steam_kg_s:            float = 0.0

    # Per-unit breakdown for the dashboard table
    breakdown: List[Dict] = []