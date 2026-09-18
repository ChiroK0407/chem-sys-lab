"""
backend/schemas/units/stripper_schema.py

Pydantic v2 request/response models for the solvent-regeneration
Stripper column. Mirrors the flat payload StripperForm.jsx sends to
POST /solve/stripper.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


def _blank_to_none(v):
    if v == "" or v is None:
        return None
    return v


class StripperRequest(BaseModel):
    """POST /solve/stripper"""

    unit_id: str = Field("STR-001", description="Unique unit tag")

    # Column internals
    internal_type: str = Field("structured_packing", description="random_packing | structured_packing | tray")
    internal_key: str = Field("MELLAPAK_250Y", description="Catalog key — see /solve/reference/column-internals")

    # Gas / solvent system
    gas_component: str = Field("CO2", description="Solute being stripped out")
    solvent_id: str = Field("MEA_30wt%", description="Rich solvent being regenerated")
    stripping_agent: str = Field("steam", description="steam | air | nitrogen | inert_gas")

    # Mass transfer specification
    x_in: float = Field(0.05, description="Solute mole fraction in rich solvent feed")
    x_out: float = Field(0.005, description="Target solute mole fraction in lean solvent outlet")
    y_in: float = Field(0.0, description="Solute mole fraction in stripping gas feed")
    L_mol_s: float = Field(150.0, gt=0, description="Rich solvent molar flow rate [mol/s]")
    G_mol_s: Optional[float] = Field(None, description="Stripping gas rate [mol/s]. None = solve for minimum × multiplier")
    L_G_ratio_multiplier: float = Field(1.5, gt=1.0, description="Safety multiplier over minimum stripping gas rate")

    # Operating conditions
    T_C: float = Field(120.0, description="Stripping operating temperature [°C]")
    P_kPa: float = Field(101.325, gt=0, description="Operating pressure [kPa abs]")

    # Geometry overrides
    column_diameter_m: Optional[float] = Field(None, description="Fixed column diameter override [m]")
    tray_efficiency: Optional[float] = Field(None, gt=0, le=1, description="Tray efficiency override (tray internals only)")
    tray_spacing_mm: Optional[float] = Field(None, gt=0, description="Tray spacing override [mm] (tray internals only)")
    flood_fraction_design: Optional[float] = Field(None, gt=0, lt=1, description="Design flood-loading fraction override")

    @field_validator("G_mol_s", "column_diameter_m", "tray_efficiency", "tray_spacing_mm",
                      "flood_fraction_design", mode="before")
    @classmethod
    def _coerce_blank(cls, v):
        return _blank_to_none(v)

    model_config = ConfigDict(json_schema_extra={"example": {
        "unit_id": "STR-101",
        "internal_type": "structured_packing",
        "internal_key": "MELLAPAK_250Y",
        "gas_component": "CO2",
        "solvent_id": "MEA_30wt%",
        "stripping_agent": "steam",
        "x_in": 0.05, "x_out": 0.005, "y_in": 0.0,
        "L_mol_s": 150.0, "L_G_ratio_multiplier": 1.5,
        "T_C": 120.0, "P_kPa": 101.325,
    }})


class StripperResponse(BaseModel):
    """Response for POST /solve/stripper — flattened design summary."""

    unit_id: str
    unit_type: str = "Stripper"
    is_solved: bool
    warnings: List[str] = []

    stripping_agent: str
    gas_component: str
    solvent_id: str
    internal_type: str
    internal_key: str

    K_value: Optional[float] = None
    H_at_T: Optional[float] = None
    x_in: Optional[float] = None
    x_out: Optional[float] = None
    y_in: Optional[float] = None
    y_out: Optional[float] = None
    L_mol_s: Optional[float] = None
    G_mol_s: Optional[float] = None
    stripping_factor_S: Optional[float] = None
    N_theoretical: Optional[float] = None
    N_actual: Optional[int] = None
    column_diameter_m: Optional[float] = None
    column_height_m: Optional[float] = None
    HETP_m: Optional[float] = None
    flood_fraction: Optional[float] = None
    wall_thickness_mm: Optional[float] = None
    Q_reboiler_kW: Optional[float] = None
    Q_condenser_kW: Optional[float] = None
    steam_rate_kg_s: Optional[float] = None
    operating_pressure_kPa: Optional[float] = None
    operating_T_C: Optional[float] = None

    # Computed for the UI — not produced by Stripper.summary() itself
    regeneration_efficiency_pct: Optional[float] = None

    inlet_streams: List[Dict[str, Any]] = []
    outlet_streams: List[Dict[str, Any]] = []
    utility_streams: List[Dict[str, Any]] = []
    calculation_log: List[str] = []

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_unit(cls, unit, include_log: bool = True) -> "StripperResponse":
        s = dict(unit.summary())
        regen_pct = None
        if s.get("x_in"):
            regen_pct = round(((s["x_in"] - s.get("x_out", 0.0)) / s["x_in"]) * 100.0, 2)
        s["regeneration_efficiency_pct"] = regen_pct
        s["calculation_log"] = unit.calculation_log if include_log else []
        return cls(**s)
