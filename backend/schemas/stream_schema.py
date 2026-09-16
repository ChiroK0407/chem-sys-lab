"""
backend/schemas/stream_schema.py

Pydantic v2 models for ProcessStream serialisation.
Used as request bodies and nested inside unit response models.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class StreamIn(BaseModel):
    """
    Incoming stream definition from the frontend.
    All temperatures in °C (converted to K before hitting simulation).
    All pressures in kPa (converted to Pa internally).
    """
    name:                  str
    temperature_c:         float  = Field(..., description="Temperature [°C]")
    pressure_kpa:          float  = Field(101.325, description="Pressure [kPa abs]")
    mass_flowrate_kg_s:    float  = Field(..., description="Mass flowrate [kg/s]", gt=0)
    cp_J_kgK:              float  = Field(..., description="Specific heat [J/(kg·K)]", gt=0)
    density_kg_m3:         float  = Field(..., description="Density [kg/m³]", gt=0)
    viscosity_Pa_s:        float  = Field(..., description="Dynamic viscosity [Pa·s]", gt=0)
    thermal_conductivity:  float  = Field(..., description="Thermal conductivity [W/(m·K)]", gt=0)
    phase:                 str    = Field("liquid", description="liquid | vapor | mixed")

    @field_validator("phase")
    @classmethod
    def validate_phase(cls, v: str) -> str:
        allowed = {"liquid", "vapor", "mixed", "supercritical"}
        if v not in allowed:
            raise ValueError(f"phase must be one of {allowed}, got '{v}'")
        return v

    @field_validator("temperature_c")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if v < -273.15:
            raise ValueError(f"temperature_c must be > -273.15°C, got {v}")
        return v

    def to_process_stream(self):
        """Convert to simulation.core.stream.ProcessStream (K, Pa)."""
        from simulation.core.stream import ProcessStream
        return ProcessStream(
            name=self.name,
            temperature=self.temperature_c + 273.15,
            pressure=self.pressure_kpa * 1000.0,
            mass_flowrate=self.mass_flowrate_kg_s,
            cp=self.cp_J_kgK,
            density=self.density_kg_m3,
            viscosity=self.viscosity_Pa_s,
            thermal_conductivity=self.thermal_conductivity,
            phase=self.phase,
        )

    model_config = {"json_schema_extra": {"example": {
        "name": "process_hot",
        "temperature_c": 120.0,
        "pressure_kpa": 300.0,
        "mass_flowrate_kg_s": 2.0,
        "cp_J_kgK": 4200.0,
        "density_kg_m3": 950.0,
        "viscosity_Pa_s": 3e-4,
        "thermal_conductivity": 0.65,
        "phase": "liquid",
    }}}


class StreamOut(BaseModel):
    """Outgoing stream state returned in API responses."""
    name:                  str
    temperature_c:         float
    pressure_kpa:          float
    mass_flowrate_kg_s:    float
    cp_J_kgK:              float
    density_kg_m3:         float
    phase:                 str
    heat_capacity_rate_W_K: float
    source_unit:           Optional[str] = None

    @classmethod
    def from_process_stream(cls, stream) -> "StreamOut":
        return cls(
            name=stream.name,
            temperature_c=round(stream.temperature_c, 3),
            pressure_kpa=round(stream.pressure_kpa, 3),
            mass_flowrate_kg_s=stream.mass_flowrate,
            cp_J_kgK=stream.cp,
            density_kg_m3=stream.density,
            phase=stream.phase,
            heat_capacity_rate_W_K=round(stream.heat_capacity_rate, 3),
            source_unit=stream.source_unit,
        )


class FluidLookupRequest(BaseModel):
    """Request body for fluid property lookup."""
    fluid_id:      str
    temperature_c: Optional[float] = None

    model_config = {"json_schema_extra": {"example": {
        "fluid_id": "water",
        "temperature_c": 80.0,
    }}}


class FluidPropertiesOut(BaseModel):
    """Response for fluid property lookup."""
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
    source_note:           str