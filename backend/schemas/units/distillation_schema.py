"""
backend/schemas/units/distillation_schema.py

Pydantic v2 request/response models for the FUG shortcut
DistillationColumn. Mirrors the payload DistillationForm.jsx sends
to POST /solve/distillation (note the request uses F_mol_s /
latent_heat_J_mol — mapped onto the dataclass's F / latent_heat
fields in the router).
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


class DistComponentIn(BaseModel):
    """One feed component row from the DistillationForm component table."""

    name: str
    z: float = Field(..., ge=0, le=1, description="Feed mole fraction")
    alpha: float = Field(..., gt=0, description="Relative volatility vs heavy key")
    is_light_key: bool = False
    is_heavy_key: bool = False
    x_distillate: Optional[float] = Field(None, description="Required for light/heavy key only")
    T_boil_K: Optional[float] = None
    MW: Optional[float] = None


class DistillationRequest(BaseModel):
    """POST /solve/distillation"""

    unit_id: str = Field("T-101", description="Unique unit tag")
    components: List[DistComponentIn] = Field(..., min_length=2)

    F_mol_s: float = Field(100.0, gt=0, description="Total feed molar flowrate [mol/s]")
    q: float = Field(1.0, description="Feed condition: 1=saturated liquid, 0=saturated vapour")
    R_Rmin_ratio: float = Field(1.5, gt=1.0, description="Operating reflux ratio multiplier over R_min")
    tray_efficiency: float = Field(0.70, gt=0, le=1, description="Overall tray efficiency")
    condenser_type: str = Field("total", description="total | partial")
    latent_heat_J_mol: float = Field(30_000.0, gt=0, description="Average latent heat of vaporisation [J/mol]")

    # Not currently exposed by DistillationForm.jsx — dataclass defaults apply if omitted
    P_col_kPa: Optional[float] = Field(None, description="Column pressure [kPa abs]")
    feed_T_C: Optional[float] = Field(None, description="Feed temperature [°C]")
    Cp_feed_J_molK: Optional[float] = Field(None, description="Feed heat capacity [J/(mol·K)]")

    @model_validator(mode="after")
    def _check_keys(self) -> "DistillationRequest":
        lk = [c for c in self.components if c.is_light_key]
        hk = [c for c in self.components if c.is_heavy_key]
        if len(lk) != 1 or len(hk) != 1:
            raise ValueError("exactly one light key and one heavy key component are required")
        if lk[0].x_distillate is None or hk[0].x_distillate is None:
            raise ValueError("x_distillate must be specified for both light key and heavy key components")
        z_sum = sum(c.z for c in self.components)
        if abs(z_sum - 1.0) > 1e-3:
            raise ValueError(f"feed mole fractions sum to {z_sum:.6f}, not 1.0")
        return self

    model_config = ConfigDict(json_schema_extra={"example": {
        "unit_id": "T-101",
        "components": [
            {"name": "benzene", "z": 0.40, "alpha": 2.5, "is_light_key": True, "is_heavy_key": False, "x_distillate": 0.95},
            {"name": "toluene", "z": 0.60, "alpha": 1.0, "is_light_key": False, "is_heavy_key": True, "x_distillate": 0.05},
        ],
        "F_mol_s": 100.0, "q": 1.0, "R_Rmin_ratio": 1.5,
        "tray_efficiency": 0.70, "condenser_type": "total", "latent_heat_J_mol": 30000.0,
    }})


class DistillationResponse(BaseModel):
    """Response for POST /solve/distillation — flattened FUG design summary."""

    unit_id: str
    unit_type: str = "DistillationColumn"
    is_solved: bool
    warnings: List[str] = []

    N_min: Optional[float] = None
    R_min: Optional[float] = None
    R_operating: Optional[float] = None
    N_theoretical: Optional[float] = None
    N_actual: Optional[int] = None
    feed_stage: Optional[int] = None
    tray_efficiency: Optional[float] = None
    D_mol_s: Optional[float] = None
    B_mol_s: Optional[float] = None
    F_mol_s: Optional[float] = None
    D_F_ratio: Optional[float] = None
    Q_condenser_kW: Optional[float] = None
    Q_reboiler_kW: Optional[float] = None
    distillate_composition: Dict[str, float] = {}
    bottoms_composition: Dict[str, float] = {}
    n_components: Optional[int] = None
    R_Rmin_ratio: Optional[float] = None
    condenser_type: Optional[str] = None
    mccabe_thiele: Optional[Dict[str, Any]] = None

    inlet_streams: List[Dict[str, Any]] = []
    outlet_streams: List[Dict[str, Any]] = []
    utility_streams: List[Dict[str, Any]] = []
    calculation_log: List[str] = []

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_unit(cls, unit, include_log: bool = True) -> "DistillationResponse":
        s = dict(unit.summary())
        # summary() reports the dataclass's own field name (F_mol_s already
        # matches — see DistillationColumn.summary()); calculation_log is
        # not part of base_summary() so it's added here explicitly.
        s["calculation_log"] = unit.calculation_log if include_log else []
        return cls(**s)
