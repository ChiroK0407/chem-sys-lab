"""
simulation/units/pump.py

Centrifugal pump — design mode with Industrial Standards compliance (API 610 / ASME B73.1).

Given inlet stream + suction/discharge conditions, computes:
  - Total head H
  - Hydraulic power, shaft power, motor power
  - NPSHa and cavitation check (vapour pressure from steam tables)
  - Outlet stream (raised pressure, slight temperature increase)
  - Specific speed Ns (pump type guidance)
  - Electricity utility consumption
  - Compliance audits against API 610 / ASME B73.1 maximum design bounds

References
----------
- Coulson & Richardson Vol. 1, Chapter 8
- McCabe, Smith & Harriott, Chapter 8
- NPSH: Hydraulic Institute Standards / API 610 Hydrocarbon Margins
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from simulation.core.stream import ProcessStream, UtilityStream
from simulation.core.unit_operation import UnitOperation
from simulation.core.exceptions import (
    InfeasibleDesignError,
    PhaseError,
    StreamNotFoundError,
)

# Import the decoupled standards catalog from your schema path
from backend.schemas.units.pump import PumpStandardEnum, INDUSTRIAL_PUMP_CATALOG


# ── Vapour pressure lookup ────────────────────────────────────────────────────

def _get_vapour_pressure(temperature_K: float) -> Optional[float]:
    """
    Return vapour pressure of water at given temperature [Pa]
    via linear interpolation from steam_tables.csv.
    """
    try:
        from simulation.data.loader import get_steam_saturation_by_T
        props = get_steam_saturation_by_T(temperature_K)
        return props["P_sat_Pa"]
    except (ValueError, Exception):
        return None


# ── Specific speed guidance ───────────────────────────────────────────────────

def _pump_type_from_Ns(Ns: float) -> str:
    """
    Recommend pump type from dimensionless specific speed.
    Ns = N * sqrt(Q) / H^(3/4)  (SI units: rpm, m³/s, m)
    """
    if Ns < 0.2:
        return "Reciprocating (positive displacement) — very low flow, high head"
    elif Ns < 1.0:
        return "Centrifugal — radial flow (standard)"
    elif Ns < 2.5:
        return "Centrifugal — mixed flow"
    elif Ns < 5.0:
        return "Axial flow (propeller) — high flow, low head"
    else:
        return "Axial flow — very high specific speed"


# ── Pump Unit Operation ───────────────────────────────────────────────────────

@dataclass
class Pump(UnitOperation):
    """
    Centrifugal pump — design mode audited by industrial standards templates.
    """

    unit_type: str = field(default="Pump", init=False)

    # Industrial Standard Selection Wrapper
    selected_standard: Optional[PumpStandardEnum] = None

    # Discharge conditions
    discharge_pressure_Pa:   float = 400_000.0   # Pa abs
    discharge_elevation_m:   float = 0.0          # m
    suction_elevation_m:     float = 0.0          # m
    suction_velocity_m_s:    float = 1.5          # m/s
    discharge_velocity_m_s:  float = 2.5          # m/s

    # Efficiency
    eta_pump:  float = 0.75
    eta_motor: float = 0.92

    # NPSH
    npsh_required_m:    float          = 2.0
    vapour_pressure_Pa: Optional[float] = None

    # Speed (for specific speed only)
    speed_rpm: float = 1450.0

    # Internal results
    _head_m:          float = field(default=0.0, init=False, repr=False)
    _p_hydraulic_kw:  float = field(default=0.0, init=False, repr=False)
    _p_shaft_kw:      float = field(default=0.0, init=False, repr=False)
    _p_motor_kw:      float = field(default=0.0, init=False, repr=False)
    _npsha_m:         float = field(default=0.0, init=False, repr=False)
    _delta_T_K:       float = field(default=0.0, init=False, repr=False)
    _specific_speed:  float = field(default=0.0, init=False, repr=False)
    _pump_type:       str   = field(default="",  init=False, repr=False)

    def __post_init__(self):
        self.unit_type = "Pump"

    def solve(self) -> None:
        self.reset()

        self.log_section("Pump Setup")
        self.log(f"Unit:              {self.unit_id}")
        if self.selected_standard:
            self.log(f"Selected Standard: {self.selected_standard.value}")
        else:
            self.log("Selected Standard: None (Manual Mode)")
            
        self.log(f"Speed:             {self.speed_rpm} rpm")
        self.log(f"η_pump:            {self.eta_pump}")
        self.log(f"η_motor:           {self.eta_motor}")
        self.log(f"Discharge P:       {self.discharge_pressure_Pa/1000:.1f} kPa")

        # ── 1. Retrieve and Validate Inlet Phase ──────────────────────────────
        inlet = self.get_inlet("feed")
        if inlet.phase in ("vapor", "mixed"):
            raise PhaseError(
                self.unit_id,
                inlet.phase,
                f"Stream '{inlet.name}' is {inlet.phase}. Centrifugal pumps handle liquid only."
            )
        self._log_stream_summary(inlet)

        # ── 2. Run Industrial Design Code Compliance Audits ──────────────────
        if self.selected_standard and self.selected_standard in INDUSTRIAL_PUMP_CATALOG:
            meta = INDUSTRIAL_PUMP_CATALOG[self.selected_standard]
            
            # Audit Operating Pressure
            discharge_bar = self.discharge_pressure_Pa / 100000.0
            if discharge_bar > meta["max_design_pressure_bar"]:
                self.warn(
                    f"[COMPLIANCE RISK] Discharge pressure ({discharge_bar:.1f} bar) "
                    f"exceeds the max envelope for {self.selected_standard.value} "
                    f"({meta['max_design_pressure_bar']} bar). Check pipeline spec."
                )
                
            # Audit Operating Temperature
            if inlet.temperature_c > meta["max_design_temp_c"]:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"Fluid temperature ({inlet.temperature_c:.1f}°C) exceeds max "
                    f"allowable temperature limit for standard template "
                    f"{self.selected_standard.value} ({meta['max_design_temp_c']}°C)."
                )

        # ── 3. Core Structural Calculations ───────────────────────────────────
        P_vap = self._resolve_vapour_pressure(inlet)
        H = self._calc_total_head(inlet)
        self._head_m = H

        if H <= 0:
            raise InfeasibleDesignError(
                self.unit_id,
                f"Total head H = {H:.3f} m ≤ 0. Discharge pressure must exceed suction pressure."
            )

        self._calc_power(inlet, H)
        self._calc_npsh(inlet, P_vap)
        self._calc_specific_speed(inlet, H)
        self._delta_T_K = self._calc_temp_rise(inlet)

        # ── 4. Build Output Streams and Utility Registers ────────────────────
        self.outlet_streams["outlet"] = inlet.copy_with(
            name=f"{inlet.name}_out",
            temperature=inlet.temperature + self._delta_T_K,
            pressure=self.discharge_pressure_Pa,
            source_unit=self.unit_id,
        )

        u = UtilityStream(
            utility_type="electricity",
            unit_id=self.unit_id,
            power_kw=self._p_motor_kw,
            duty_kw=self._p_motor_kw,
        )
        self.utility_streams.append(u)

        # ── 5. Standard Output Logging ────────────────────────────────────────
        self.log_section("Results")
        self.log(f"Total head H       = {self._head_m:.3f} m")
        self.log(f"Shaft power        = {self._p_shaft_kw:.3f} kW")
        self.log(f"Motor power        = {self._p_motor_kw:.3f} kW")
        self.log(f"NPSHa              = {self._npsha_m:.3f} m")
        self.log(f"Pump type guide    = {self._pump_type}")

        self.is_solved = True

    # =========================================================================
    # Extended Internal Mathematical Modules
    # =========================================================================

    def _calc_total_head(self, inlet: ProcessStream) -> float:
        g, rho = 9.81, inlet.density
        H_pressure = (self.discharge_pressure_Pa - inlet.pressure) / (rho * g)
        H_elevation = self.discharge_elevation_m - self.suction_elevation_m
        H_velocity = (self.discharge_velocity_m_s**2 - self.suction_velocity_m_s**2) / (2 * g)
        return H_pressure + H_elevation + H_velocity

    def _calc_power(self, inlet: ProcessStream, H: float) -> None:
        g, mdot = 9.81, inlet.mass_flowrate
        P_hyd = mdot * g * H
        P_shaft = P_hyd / self.eta_pump
        P_motor = P_shaft / self.eta_motor
        self._p_hydraulic_kw = P_hyd / 1000
        self._p_shaft_kw = P_shaft / 1000
        self._p_motor_kw = P_motor / 1000

    def _calc_npsh(self, inlet: ProcessStream, P_vap: Optional[float]) -> None:
        self.log_section("NPSH Calibration")
        g, rho = 9.81, inlet.density
        
        # FIX: Remove the malformed "import Optional" text
        if P_vap is None:
            self.warn("Vapour pressure unknown — skipping strict margin validation profiles.")
            self._npsha_m = float("nan")
            return

        NPSHa = (inlet.pressure - P_vap) / (rho * g) + (self.suction_velocity_m_s**2) / (2 * g)
        self._npsha_m = NPSHa

        # Extract safety buffer bounds dynamically based on active code spec
        safety_margin = 0.5  # Standard HI default
        if self.selected_standard and self.selected_standard in INDUSTRIAL_PUMP_CATALOG:
            safety_margin = INDUSTRIAL_PUMP_CATALOG[self.selected_standard]["npsh_margin_buffer_m"]

        self.log(f"Calculated NPSH Available: {NPSHa:.3f} m")
        self.log(f"Governing Template Buffer: {safety_margin:.2f} m")

        if NPSHa < self.npsh_required_m:
            raise InfeasibleDesignError(
                self.unit_id,
                f"Severe Cavitation! NPSHa ({NPSHa:.2f}m) < NPSHr ({self.npsh_required_m:.2f}m)."
            )
        elif NPSHa < (self.npsh_required_m + safety_margin):
            self.warn(
                f"[CAVITATION RISK] NPSHa ({NPSHa:.2f}m) violates the mandatory safety buffer "
                f"(+{safety_margin}m) required by {self.selected_standard.value if self.selected_standard else 'Standard'}."
            )

    def _calc_specific_speed(self, inlet: ProcessStream, H: float) -> None:
        Q = inlet.volumetric_flowrate
        N = self.speed_rpm / 60.0
        if H <= 0 or Q <= 0:
            self._specific_speed = 0.0
            return
        self._specific_speed = N * math.sqrt(Q) / (H**0.75)
        self._pump_type = _pump_type_from_Ns(self._specific_speed)

    def _calc_temp_rise(self, inlet: ProcessStream) -> float:
        P_loss = (self._p_shaft_kw - self._p_hydraulic_kw) * 1000
        return P_loss / (inlet.mass_flowrate * inlet.cp)

    def _resolve_vapour_pressure(self, inlet: ProcessStream) -> Optional[float]:
        if self.vapour_pressure_Pa is not None:
            return self.vapour_pressure_Pa
        P_vap = _get_vapour_pressure(inlet.temperature)
        if P_vap is not None:
            return P_vap
        
        # Water fallback via Antoine approximation
        T_C = inlet.temperature_c
        if 0 < T_C < 374:
            return (10 ** (8.07131 - 1730.63 / (233.426 + T_C))) * 133.322
        return None

    def _log_stream_summary(self, stream: ProcessStream) -> None:
        self.log(f"  Inlet Temperature: {stream.temperature_c:.2f} °C")
        self.log(f"  Inlet Density:     {stream.density:.2f} kg/m³")

    # =========================================================================
    # Serialization Summary Exporter
    # =========================================================================

    def summary(self) -> dict:
        base = self.base_summary()
        pump_results = {
            "selected_standard":       self.selected_standard.value if self.selected_standard else None,
            "discharge_pressure_kPa":  round(self.discharge_pressure_Pa / 1000, 2),
            "suction_pressure_kPa":    round(self.inlet_streams["feed"].pressure / 1000, 2) if "feed" in self.inlet_streams else None,
            "head_m":                  round(self._head_m, 4),
            "p_hydraulic_kW":          round(self._p_hydraulic_kw, 4),
            "p_shaft_kW":              round(self._p_shaft_kw, 4),
            "p_motor_kW":              round(self._p_motor_kw, 4),
            "eta_pump":                self.eta_pump,
            "eta_motor":               self.eta_motor,
            "npsha_m":                 round(self._npsha_m, 3) if not math.isnan(self._npsha_m) else None,
            "npshr_m":                 self.npsh_required_m,
            "delta_T_K":               round(self._delta_T_K, 5),
            "specific_speed":          round(self._specific_speed, 4),
            "pump_type":               self._pump_type,
            "speed_rpm":               self.speed_rpm,
        }
        return {**base, **pump_results}