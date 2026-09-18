"""
backend/schemas/units/absorber_schema.py

Pydantic v2 request/response models for the gas Absorber column.

Mirrors the flat scalar payload AbsorberForm.jsx already sends to
POST /solve/absorber (unit_id, internal_type/key, gas/solvent system,
process boundary conditions in °C / kPa, and geometry overrides).
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


def _blank_to_none(v):
    """Frontend number inputs send '' instead of omitting the field."""
    if v == "" or v is None:
        return None
    return v


class AbsorberRequest(BaseModel):
    """POST /solve/absorber"""

    unit_id: str = Field("ABS-001", description="Unique unit tag")

    # Column internals
    internal_type: str = Field("structured_packing", description="random_packing | structured_packing | tray")
    internal_key: str = Field("MELLAPAK_250Y", description="Catalog key — see /solve/reference/column-internals")

    # Gas / solvent system
    gas_component: str = Field("CO2", description="Solute being absorbed")
    solvent_id: str = Field("water", description="Absorbent solvent")

    # Mass transfer specification
    y_in: float = Field(0.12, description="Solute mole fraction in rich gas feed")
    y_out: float = Field(0.01, description="Target solute mole fraction in lean gas outlet")
    x_in: float = Field(0.0, description="Solute mole fraction in lean solvent feed")
    G_mol_s: float = Field(100.0, gt=0, description="Gas molar flow rate [mol/s]")
    L_mol_s: Optional[float] = Field(150.0, description="Operating solvent rate [mol/s]. None = solve for minimum × multiplier")
    L_G_ratio_multiplier: float = Field(1.5, gt=1.0, description="Multiplier over minimum solvent rate")

    # Operating conditions
    T_C: float = Field(25.0, description="Operating temperature [°C]")
    P_kPa: float = Field(101.325, gt=0, description="Operating pressure [kPa abs]")

    # Geometry overrides (optional — None triggers auto-sizing from flooding correlation)
    column_diameter_m: Optional[float] = Field(None, description="Fixed column diameter override [m]")
    tray_efficiency: Optional[float] = Field(None, gt=0, le=1, description="Tray efficiency override (tray internals only)")
    tray_spacing_mm: Optional[float] = Field(None, gt=0, description="Tray spacing override [mm] (tray internals only)")
    flood_fraction_design: Optional[float] = Field(None, gt=0, lt=1, description="Design flood-loading fraction override")

    @field_validator("L_mol_s", "column_diameter_m", "tray_efficiency", "tray_spacing_mm",
                      "flood_fraction_design", mode="before")
    @classmethod
    def _coerce_blank(cls, v):
        return _blank_to_none(v)

    model_config = ConfigDict(json_schema_extra={"example": {
        "unit_id": "ABS-101",
        "internal_type": "structured_packing",
        "internal_key": "MELLAPAK_250Y",
        "gas_component": "CO2",
        "solvent_id": "water",
        "y_in": 0.12, "y_out": 0.01, "x_in": 0.0,
        "G_mol_s": 100.0, "L_mol_s": 150.0, "L_G_ratio_multiplier": 1.5,
        "T_C": 25.0, "P_kPa": 101.325,
    }})


class AbsorberResponse(BaseModel):
    """Response for POST /solve/absorber — flattened design summary."""

    unit_id: str
    unit_type: str = "Absorber"
    is_solved: bool
    warnings: List[str] = []

    gas_component: str
    solvent_id: str
    internal_type: str
    internal_key: str

    K_value: Optional[float] = None
    H_at_T: Optional[float] = None
    y_in: Optional[float] = None
    y_out: Optional[float] = None
    x_in: Optional[float] = None
    x_out: Optional[float] = None
    L_min_mol_s: Optional[float] = None
    L_operating_mol_s: Optional[float] = None
    G_mol_s: Optional[float] = None
    absorption_factor_A: Optional[float] = None
    N_theoretical: Optional[float] = None
    N_actual: Optional[int] = None
    column_diameter_m: Optional[float] = None
    column_height_m: Optional[float] = None
    HETP_m: Optional[float] = None
    flood_fraction: Optional[float] = None
    wall_thickness_mm: Optional[float] = None
    Q_absorption_kW: Optional[float] = None
    operating_pressure_kPa: Optional[float] = None
    operating_T_C: Optional[float] = None

    # Computed for the UI — not produced by Absorber.summary() itself
    removal_efficiency_pct: Optional[float] = None

    inlet_streams: List[Dict[str, Any]] = []
    outlet_streams: List[Dict[str, Any]] = []
    utility_streams: List[Dict[str, Any]] = []
    calculation_log: List[str] = []

    model_config = ConfigDict(extra="allow")  # tolerate any additional summary() keys

    @classmethod
    def from_unit(cls, unit, include_log: bool = True) -> "AbsorberResponse":
        s = dict(unit.summary())
        removal_pct = None
        if s.get("y_in"):
            removal_pct = round(((s["y_in"] - s.get("y_out", 0.0)) / s["y_in"]) * 100.0, 2)
        s["removal_efficiency_pct"] = removal_pct
        s["calculation_log"] = unit.calculation_log if include_log else []
        return cls(**s)
