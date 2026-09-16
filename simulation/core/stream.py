"""
simulation/core/stream.py

Stream objects are the fundamental data carriers in the simulation.
They are immutable value objects — unit operations consume an inlet
stream and produce a NEW outlet stream via copy_with().

Design rules:
  - Never mutate a stream after creation.
  - All temperatures in Kelvin internally.
  - All pressures in Pa (absolute) internally.
  - All flowrates in kg/s.
  - UI layer is responsible for unit conversion before/after API calls.
"""

from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Optional
import numpy as np


# ── Allowed phase flags ───────────────────────────────────────────────────────

VALID_PHASES = {"liquid", "vapor", "mixed", "supercritical"}


# ── ProcessStream ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProcessStream:
    """
    Steady-state material stream.

    frozen=True enforces immutability — any modification must go
    through copy_with(), which returns a new instance. This prevents
    accidental in-place mutation when streams are shared between units
    in a network.

    Thermal properties (cp, density, viscosity, thermal_conductivity)
    are treated as constant at the stream's current temperature.
    Temperature-dependent properties will be handled by the thermo/
    module in a later phase — the interface here stays the same.

    Parameters
    ----------
    name : str
        Human-readable label shown in stream tables and the PFD.
    temperature : float
        Stream temperature [K].
    pressure : float
        Absolute pressure [Pa].
    mass_flowrate : float
        Mass flowrate [kg/s].
    cp : float
        Specific heat capacity [J/(kg·K)].
    density : float
        Mass density [kg/m³]. Used for sizing and hydraulic calcs.
    viscosity : float
        Dynamic viscosity [Pa·s]. Used for Re, Pr, Nu correlations.
    thermal_conductivity : float
        Thermal conductivity [W/(m·K)]. Used for Nu → h calculations.
    phase : str
        One of 'liquid', 'vapor', 'mixed', 'supercritical'.
    components : tuple[str, ...], optional
        Component names — required for multicomponent units (VLE, reactors).
    mole_fractions : tuple[float, ...], optional
        Mole fractions corresponding to components. Must sum to 1.0.
    stream_id : str, optional
        Unique identifier. Auto-assigned by network if not provided.
    source_unit : str, optional
        ID of the unit that produced this stream.
    sink_unit : str, optional
        ID of the unit consuming this stream (set during network.connect()).
    """

    name: str
    temperature: float                          # K
    pressure: float                             # Pa
    mass_flowrate: float                        # kg/s
    cp: float                                   # J/(kg·K)
    density: float                              # kg/m³
    viscosity: float                            # Pa·s
    thermal_conductivity: float                 # W/(m·K)
    phase: str = "liquid"

    # Multicomponent fields (optional for single-component streams)
    components: Optional[tuple] = None
    mole_fractions: Optional[tuple] = None

    # Metadata
    stream_id: Optional[str] = None
    source_unit: Optional[str] = None
    sink_unit: Optional[str] = None

    # ── Post-init validation ──────────────────────────────────────────────────

    def __post_init__(self):
        from simulation.core.exceptions import StreamError

        if self.temperature <= 0:
            raise StreamError(
                f"Stream '{self.name}': temperature must be > 0 K, "
                f"got {self.temperature} K."
            )
        if self.pressure <= 0:
            raise StreamError(
                f"Stream '{self.name}': pressure must be > 0 Pa, "
                f"got {self.pressure} Pa."
            )
        if self.mass_flowrate < 0:
            raise StreamError(
                f"Stream '{self.name}': mass_flowrate must be ≥ 0 kg/s, "
                f"got {self.mass_flowrate} kg/s."
            )
        if self.cp <= 0:
            raise StreamError(
                f"Stream '{self.name}': cp must be > 0 J/(kg·K), "
                f"got {self.cp}."
            )
        if self.phase not in VALID_PHASES:
            raise StreamError(
                f"Stream '{self.name}': phase '{self.phase}' is invalid. "
                f"Choose from {VALID_PHASES}."
            )
        if self.components is not None and self.mole_fractions is not None:
            if len(self.components) != len(self.mole_fractions):
                raise StreamError(
                    f"Stream '{self.name}': components length "
                    f"({len(self.components)}) != mole_fractions length "
                    f"({len(self.mole_fractions)})."
                )
            total = sum(self.mole_fractions)
            if abs(total - 1.0) > 1e-4:
                raise StreamError(
                    f"Stream '{self.name}': mole_fractions sum to {total:.6f}, "
                    f"expected 1.0."
                )

    # ── Derived thermodynamic properties ─────────────────────────────────────

    @property
    def heat_capacity_rate(self) -> float:
        """
        ṁ · Cp  [W/K]

        The single most important quantity in heat exchanger design.
        Appears in every energy balance and NTU-effectiveness equation.
        """
        return self.mass_flowrate * self.cp

    @property
    def volumetric_flowrate(self) -> float:
        """ṁ / ρ  [m³/s]"""
        return self.mass_flowrate / self.density

    @property
    def prandtl_number(self) -> float:
        """
        Pr = Cp · μ / k  [dimensionless]

        Required for Nusselt number correlations (Dittus-Boelter, Sieder-Tate)
        when computing film heat transfer coefficients.
        """
        return (self.cp * self.viscosity) / self.thermal_conductivity

    def enthalpy_flow(self, t_ref: float = 298.15) -> float:
        """
        Sensible enthalpy flow rate relative to reference temperature.

        H = ṁ · Cp · (T - T_ref)  [W]

        Used for energy balance checks across unit operations.
        t_ref defaults to 298.15 K (25°C) — standard reference state.
        """
        return self.mass_flowrate * self.cp * (self.temperature - t_ref)

    # ── Convenience properties (unit-converted for display) ──────────────────

    @property
    def temperature_c(self) -> float:
        """Temperature in °C (display only)."""
        return self.temperature - 273.15

    @property
    def pressure_kpa(self) -> float:
        """Pressure in kPa (display only)."""
        return self.pressure / 1000.0

    @property
    def pressure_bar(self) -> float:
        """Pressure in bar (display only)."""
        return self.pressure / 1e5

    # ── Mutation interface ────────────────────────────────────────────────────

    def copy_with(self, **kwargs) -> ProcessStream:
        """
        Return a new ProcessStream with specified fields overridden.

        This is the ONLY correct way to 'modify' a stream. It preserves
        all other fields unchanged.

        Usage
        -----
        hot_outlet = hot_inlet.copy_with(
            temperature=340.0,
            name="hot_outlet",
            source_unit="HX-101"
        )
        """
        return replace(self, **kwargs)

    # ── Energy balance helper ─────────────────────────────────────────────────

    def mix_with(self, other: ProcessStream, name: str = "mixed") -> ProcessStream:
        """
        Adiabatic mixing of two streams (same phase, miscible).

        Energy balance:
            T_mix = (ṁ₁·Cp₁·T₁ + ṁ₂·Cp₂·T₂) / (ṁ₁·Cp₁ + ṁ₂·Cp₂)

        Mixture Cp, density, viscosity use mass-weighted averages —
        adequate for conceptual design; not rigorous for multicomponent VLE.
        """
        m1, m2 = self.mass_flowrate, other.mass_flowrate
        m_total = m1 + m2

        cp_mix = (m1 * self.cp + m2 * other.cp) / m_total
        rho_mix = m_total / (m1 / self.density + m2 / other.density)
        mu_mix = (m1 * self.viscosity + m2 * other.viscosity) / m_total
        k_mix = (m1 * self.thermal_conductivity +
                 m2 * other.thermal_conductivity) / m_total

        C1 = self.heat_capacity_rate
        C2 = other.heat_capacity_rate
        T_mix = (C1 * self.temperature + C2 * other.temperature) / (C1 + C2)

        return ProcessStream(
            name=name,
            temperature=T_mix,
            pressure=min(self.pressure, other.pressure),   # conservative
            mass_flowrate=m_total,
            cp=cp_mix,
            density=rho_mix,
            viscosity=mu_mix,
            thermal_conductivity=k_mix,
            phase=self.phase,
        )

    # ── Display ───────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Flat dict for stream tables, API responses, and logging."""
        return {
            "name": self.name,
            "temperature_C": round(self.temperature_c, 2),
            "pressure_kPa": round(self.pressure_kpa, 2),
            "mass_flowrate_kg_s": self.mass_flowrate,
            "cp_J_kgK": self.cp,
            "density_kg_m3": self.density,
            "viscosity_Pa_s": self.viscosity,
            "thermal_conductivity_W_mK": self.thermal_conductivity,
            "heat_capacity_rate_W_K": round(self.heat_capacity_rate, 2),
            "phase": self.phase,
            "source_unit": self.source_unit,
            "sink_unit": self.sink_unit,
        }

    def __repr__(self) -> str:
        return (
            f"ProcessStream('{self.name}' | "
            f"T={self.temperature_c:.1f}°C | "
            f"P={self.pressure_kpa:.1f} kPa | "
            f"ṁ={self.mass_flowrate:.3f} kg/s | "
            f"phase={self.phase})"
        )


# ── UtilityStream ─────────────────────────────────────────────────────────────

@dataclass
class UtilityStream:
    """
    Represents a utility service consumed by a unit operation.

    Unlike ProcessStream, UtilityStream is mutable — it accumulates
    consumption as units are solved. The UtilityTracker aggregates
    these across the entire network for the dashboard.

    Utility types
    -------------
    cooling_water   : CW supply / return at fixed temperatures
    lp_steam        : Low-pressure steam (~3 bar, ~134°C)
    mp_steam        : Medium-pressure steam (~10 bar, ~180°C)
    hp_steam        : High-pressure steam (~40 bar, ~250°C)
    electricity     : Power draw in kW
    refrigeration   : Duty below ambient (negative CW)
    """

    utility_type: str                           # see docstring above
    unit_id: str                                # which unit consumes this

    # Consumption quantities
    mass_flowrate: float = 0.0                  # kg/s (CW, steam)
    duty_kw: float = 0.0                        # kW (all types)
    power_kw: float = 0.0                       # kW (electricity only)

    # Supply conditions (defaults are typical plant values)
    supply_temperature: float = 303.15          # K  (30°C for CW)
    return_temperature: float = 318.15          # K  (45°C for CW)
    cp: float = 4182.0                          # J/(kg·K) — water default

    def to_dict(self) -> dict:
        return {
            "utility_type": self.utility_type,
            "unit_id": self.unit_id,
            "mass_flowrate_kg_s": round(self.mass_flowrate, 4),
            "duty_kW": round(self.duty_kw, 3),
            "power_kW": round(self.power_kw, 3),
            "supply_temperature_C": round(self.supply_temperature - 273.15, 1),
            "return_temperature_C": round(self.return_temperature - 273.15, 1),
        }

    def __repr__(self) -> str:
        return (
            f"UtilityStream({self.utility_type} | "
            f"unit={self.unit_id} | "
            f"duty={self.duty_kw:.2f} kW | "
            f"ṁ={self.mass_flowrate:.3f} kg/s)"
        )