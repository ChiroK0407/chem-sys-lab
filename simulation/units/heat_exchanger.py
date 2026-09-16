"""
simulation/units/heat_exchanger.py

Heat Exchanger unit operation.
Supports two operating modes and three flow configurations.

Modes
-----
sizing  : Given inlet/outlet temperatures → find required area A
rating  : Given area A and inlet temperatures → find outlet temperatures

Flow configurations
-------------------
counterflow         : pure counterflow, F = 1.0 always
parallelflow        : co-current, F = 1.0 always
shell_tube_1_2      : 1 shell pass / 2 tube passes, F from Bowman-Mueller-Nagle

Utility side
------------
cooling_water       : CW supply/return at configurable temperatures
lp_steam            : LP steam condensing (~3.5 bar, 138°C), latent heat only
mp_steam            : MP steam condensing (~10 bar, 180°C), latent heat only
hp_steam            : HP steam condensing (~40 bar, 250°C), latent heat only
process             : process-to-process — both sides are ProcessStreams

References
----------
- Coulson & Richardson Vol. 1, Chapter 12 (LMTD, F-factor)
- McCabe, Smith & Harriott, Chapter 15 (ε-NTU)
- Bowman, Mueller & Nagle (1940), Trans. ASME 62:283 (F-factor correlation)
"""

from __future__ import annotations
from backend.schemas.units.hx_catalog import HeatExchangerClass, EXCHANGER_CLASS_CATALOG

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from simulation.core.stream import ProcessStream, UtilityStream
from simulation.core.unit_operation import UnitOperation
from simulation.core.exceptions import (
    InfeasibleDesignError,
    PhaseError,
    StreamNotFoundError,
)


# ── Enumerations ──────────────────────────────────────────────────────────────

class HXMode(str, Enum):
    SIZING = "sizing"
    RATING = "rating"


class FlowConfig(str, Enum):
    COUNTERFLOW    = "counterflow"
    PARALLELFLOW   = "parallelflow"
    SHELL_TUBE_1_2 = "shell_tube_1_2"


class UtilityFluid(str, Enum):
    COOLING_WATER = "cooling_water"
    LP_STEAM      = "lp_steam"
    MP_STEAM      = "mp_steam"
    HP_STEAM      = "hp_steam"
    PROCESS       = "process"    # process-to-process, no utility stream


# ── Steam latent heat table (J/kg) at saturation ─────────────────────────────
# Source: steam tables; values at nominal saturation temperature for each grade.
# LP ~3.5 bar / 138°C, MP ~10 bar / 180°C, HP ~40 bar / 250°C

_STEAM_LATENT_HEAT = {
    UtilityFluid.LP_STEAM: 2125e3,   # J/kg  @ ~2.3 bar / 140°C
    UtilityFluid.MP_STEAM: 1980e3,   # J/kg  @ ~4.7 bar / 180°C
    UtilityFluid.HP_STEAM: 1678e3,   # J/kg  @ ~14.6 bar / 250°C
}

_STEAM_SATURATION_T = {
    UtilityFluid.LP_STEAM: 413.15,   # K  (140°C)
    UtilityFluid.MP_STEAM: 453.15,   # K  (180°C)
    UtilityFluid.HP_STEAM: 523.15,   # K  (250°C)
}

# Typical U-value ranges [W/(m²·K)] by service
# Used to warn the user if their U is outside literature range.
# Source: Coulson & Richardson Vol. 1, Table 12.1
_U_RANGES = {
    "liquid_liquid":  (100,  800),
    "liquid_gas":     (10,   50),
    "gas_gas":        (10,   30),
    "condensing_steam_liquid": (500, 4000),
    "condensing_steam_gas":    (30,  200),
    "liquid_vaporising":       (200, 1000),
}


# ── HeatExchanger ─────────────────────────────────────────────────────────────

@dataclass
class HeatExchanger(UnitOperation):
    """
    Shell-and-tube or double-pipe heat exchanger.

    Parameters
    ----------
    unit_id : str
        Unique identifier in the process network.
    mode : HXMode
        "sizing" — find required area.
        "rating" — find outlet temperatures given area.
    flow_config : FlowConfig
        Flow arrangement (counterflow, parallelflow, shell_tube_1_2).
    U : float
        Overall heat transfer coefficient [W/(m²·K)].
        User-supplied. No film resistance calculation here.
    utility_fluid : UtilityFluid
        Which utility service heats or cools the process stream.
        Use "process" for process-to-process exchangers.
    area : float, optional
        Heat transfer area [m²]. Required for rating mode.
        Computed and stored by sizing mode.

    Utility side parameters (ignored when utility_fluid == "process")
    -----------------------------------------------------------------
    cw_supply_T : float
        Cooling water supply temperature [K]. Default 303.15 K (30°C).
    cw_return_T : float
        Cooling water return temperature [K]. Default 318.15 K (45°C).
    cw_cp : float
        Cooling water specific heat [J/(kg·K)]. Default 4182 (liquid water).

    Sizing mode inputs
    ------------------
    Add inlets via add_inlet():
        "hot"  : hot process stream (required)
        "cold" : cold process stream (required if utility_fluid == "process")

    For utility-side cooling/heating, only "hot" (or "cold") is needed —
    the utility stream is built internally.

    If utility_fluid == "process", add both "hot" and "cold" inlets.
    Both must have their outlet temperatures specified via:
        hot_outlet_T  : float  [K]  (required in sizing mode)
        cold_outlet_T : float  [K]  (required in sizing mode, unless derivable)

    Rating mode inputs
    ------------------
    Same inlets as sizing, plus area must be set.
    Outlet temperatures are computed — do not set hot_outlet_T / cold_outlet_T.
    """

    selected_class: Optional[HeatExchangerClass] = None

    # Core design parameters
    mode: HXMode            = HXMode.SIZING
    flow_config: FlowConfig = FlowConfig.COUNTERFLOW
    U: float                = 500.0          # W/(m²·K)
    utility_fluid: UtilityFluid = UtilityFluid.COOLING_WATER

    # Area — populated by sizing, required for rating
    area: Optional[float]   = None           # m²

    # Outlet temperature specs (sizing mode only)
    # Set ONE of these to drive the energy balance.
    # The other is derived from it.
    hot_outlet_T: Optional[float]  = None    # K
    cold_outlet_T: Optional[float] = None    # K

    # Cooling water parameters
    cw_supply_T: float = 303.15   # K  (30°C)
    cw_return_T: float = 318.15   # K  (45°C)
    cw_cp: float       = 4182.0   # J/(kg·K)

    # Internal results (populated by solve)
    _duty_kw:        float = field(default=0.0, init=False, repr=False)
    _lmtd:           float = field(default=0.0, init=False, repr=False)
    _f_factor:       float = field(default=1.0, init=False, repr=False)
    _ntu:            float = field(default=0.0, init=False, repr=False)
    _effectiveness:  float = field(default=0.0, init=False, repr=False)
    _hot_outlet_T:   float = field(default=0.0, init=False, repr=False)
    _cold_outlet_T:  float = field(default=0.0, init=False, repr=False)
    _dt_min:         float = field(default=0.0, init=False, repr=False)

    def __post_init__(self):
        # dataclass inheritance: set unit_type after super fields are ready
        self.unit_type = "HeatExchanger"

    # =========================================================================
    # Public interface
    # =========================================================================

    def solve(self) -> None:
        """
        Run heat exchanger calculations.

        Sizing  → populates self.area, outlet streams, utility stream.
        Rating  → populates outlet temperatures, utility stream.

        All intermediate values are appended to self.calculation_log.
        """
        self.reset()
        self.log_section("Heat Exchanger Setup")
        self.log(f"Unit:          {self.unit_id}")
        self.log(f"Mode:          {self.mode.value}")
        self.log(f"Flow config:   {self.flow_config.value}")
        self.log(f"U:             {self.U} W/(m²·K)")
        self.log(f"Utility fluid: {self.utility_fluid.value}")

        # ── Retrieve inlet streams ────────────────────────────────────────────
        # For steam utilities the process stream is the cold side (being heated).
        # Accept either "hot" or "cold" key so the API is unambiguous:
        # - Cooling duty  → user adds "hot" (the stream being cooled)
        # - Heating duty  → user adds "cold" (the stream being heated)
        # Internally we always call the process stream "hot" in the energy
        # balance when it's being cooled, and swap roles for steam.
        is_steam = self.utility_fluid in (
            UtilityFluid.LP_STEAM, UtilityFluid.MP_STEAM, UtilityFluid.HP_STEAM
        )

        if is_steam:
            # Process stream is cold side — user should add "cold" inlet
            if "cold" in self.inlet_streams:
                process_stream = self.get_inlet("cold")
            else:
                process_stream = self.get_inlet("hot")   # fallback
            self._check_phase(process_stream, "cold")
            steam_hot = self._build_utility_stream_as_process(process_stream)
            hot  = steam_hot
            cold = process_stream
        elif self.utility_fluid == UtilityFluid.PROCESS:
            hot  = self.get_inlet("hot")
            cold = self.get_inlet("cold")
            self._check_phase(hot, "hot")
            self._check_phase(cold, "cold")
        else:
            # Cooling water — process stream is hot side
            hot  = self.get_inlet("hot")
            self._check_phase(hot, "hot")
            cold = self._build_utility_stream_as_process(hot)

        self._log_stream(hot, "Hot inlet")

        # Only log cold stream details when it's a real process stream.
        # For utility-side streams the flowrate is a solver placeholder —
        # logging it would be misleading. Show supply conditions instead.
        if self.utility_fluid == UtilityFluid.PROCESS:
            self._log_stream(cold, "Cold inlet")
        elif self.utility_fluid == UtilityFluid.COOLING_WATER:
            self.log(f"\nCooling water (utility):")
            self.log(f"  Supply T = {self.cw_supply_T - 273.15:.1f} °C")
            self.log(f"  Return T = {self.cw_return_T - 273.15:.1f} °C  (plant header constraint)")
            self.log(f"  Cp       = {self.cw_cp:.0f} J/(kg·K)")
            self.log(f"  Flowrate = solved from Q after energy balance")
        else:
            # Steam utility
            T_sat = _STEAM_SATURATION_T.get(self.utility_fluid, 0)
            lam   = _STEAM_LATENT_HEAT.get(self.utility_fluid, 0)
            self.log(f"\n{self.utility_fluid.value} (utility):")
            self.log(f"  Saturation T = {T_sat - 273.15:.1f} °C  (isothermal condensation)")
            self.log(f"  Latent heat  = {lam/1000:.0f} kJ/kg")
            self.log(f"  Steam rate   = solved from Q / λ after energy balance")

        # ── Validate temperatures ─────────────────────────────────────────────
        if hot.temperature <= cold.temperature:
            raise InfeasibleDesignError(
                self.unit_id,
                f"Hot inlet T ({hot.temperature - 273.15:.1f}°C) must be "
                f"greater than cold inlet T ({cold.temperature - 273.15:.1f}°C)."
            )
        
        # ── Industrial Code Compliance Audits ──────────────────────────────────
        if self.selected_class and self.selected_class in EXCHANGER_CLASS_CATALOG:
            meta = EXCHANGER_CLASS_CATALOG[self.selected_class]
            
            # Enforce maximum design pressure thresholds
            # Assuming pressure is tracked in Pascals internally
            max_p_pa = meta["max_design_pressure_bar"] * 100000.0
            if hot.pressure > max_p_pa or cold.pressure > max_p_pa:
                self.warn(
                    f"[COMPLIANCE RISK] Stream pressure exceeds the maximum physical envelope "
                    f"specified for a {meta['extended_name']} ({meta['max_design_pressure_bar']} bar)."
                )

            # Enforce minimum design metal temperature (MDMT) or max operating thresholds
            if hot.temperature_c > meta["max_design_temp_c"]:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"Operating temperature ({hot.temperature_c:.1f}°C) exceeds structural rating "
                    f"for {self.selected_class.value} ({meta['max_design_temp_c']}°C)."
                )
                
            # Isothermal phase override validator rule
            if not meta["allows_phase_change"] and (hot.phase == "mixed" or cold.phase == "mixed"):
                raise PhaseError(
                    self.unit_id, "mixed",
                    f"Phase change detected! {self.selected_class.value} does not support latent heat profiles."
                )

        # ── Warn on U value ───────────────────────────────────────────────────
        self._warn_u_value(hot, cold)

        # ── Dispatch to solve path ────────────────────────────────────────────
        if self.mode == HXMode.SIZING:
            T_ho, T_co, Q = self._solve_sizing(hot, cold)
        else:
            if self.area is None:
                raise ValueError(
                    f"Unit '{self.unit_id}': area must be set for rating mode."
                )
            T_ho, T_co, Q = self._solve_rating(hot, cold)

        # ── Build outlet streams ──────────────────────────────────────────────
        self.outlet_streams["hot_out"] = hot.copy_with(
            name=f"{hot.name}_out",
            temperature=T_ho,
            source_unit=self.unit_id,
        )
        if self.utility_fluid == UtilityFluid.PROCESS:
            self.outlet_streams["cold_out"] = cold.copy_with(
                name=f"{cold.name}_out",
                temperature=T_co,
                source_unit=self.unit_id,
            )

        # ── Build utility stream ──────────────────────────────────────────────
        self._build_utility_stream(Q)

        # ── Energy balance check (process-to-process only) ───────────────────
        # Utility-side cold stream has placeholder flowrate=1.0 kg/s — checking
        # ṁCp balance against it is meaningless. Only check for process streams.
        if self.utility_fluid == UtilityFluid.PROCESS:
            Q_hot  = hot.heat_capacity_rate  * (hot.temperature - T_ho)
            Q_cold = cold.heat_capacity_rate * (T_co - cold.temperature)
            self.check_energy_balance(Q_hot, Q_cold)

        # ── Store results ─────────────────────────────────────────────────────
        self._duty_kw       = Q / 1000.0
        self._hot_outlet_T  = T_ho
        self._cold_outlet_T = T_co
        self._dt_min        = self._min_approach_temp(
            hot.temperature, T_ho, cold.temperature, T_co
        )

        self.log_section("Results")
        self.log(f"Duty Q             = {self._duty_kw:.3f} kW")
        self.log(f"Hot outlet T       = {T_ho - 273.15:.2f} °C")
        self.log(f"Cold outlet T      = {T_co - 273.15:.2f} °C")
        self.log(f"Min approach ΔT    = {self._dt_min:.2f} K")
        if self.mode == HXMode.SIZING:
            self.log(f"Required area A    = {self.area:.4f} m²")
        else:
            self.log(f"NTU                = {self._ntu:.4f}")
            self.log(f"Effectiveness ε    = {self._effectiveness:.4f}")

        # ── Final guards ──────────────────────────────────────────────────────
        if self._dt_min < 5.0:
            self.warn(
                f"Minimum approach temperature ΔT_min = {self._dt_min:.1f} K "
                f"< 5 K. This is impractically small — check your specifications."
            )

        self.is_solved = True

    # =========================================================================
    # Sizing path
    # =========================================================================

    def _solve_sizing(
        self,
        hot: ProcessStream,
        cold: ProcessStream,
    ) -> tuple[float, float, float]:
        """
        Given inlet + outlet temperatures → compute required area.

        Returns
        -------
        T_ho : float  hot outlet temperature [K]
        T_co : float  cold outlet temperature [K]
        Q    : float  duty [W]
        """
        self.log_section("Sizing Calculation")

        T_hi = hot.temperature
        T_ci = cold.temperature
        C_hot  = hot.heat_capacity_rate
        C_cold = cold.heat_capacity_rate
        is_steam = self.utility_fluid in (
            UtilityFluid.LP_STEAM, UtilityFluid.MP_STEAM, UtilityFluid.HP_STEAM
        )

        self.log(f"C_hot  = ṁ·Cp = {hot.mass_flowrate:.4f} × {hot.cp:.2f}"
                 f" = {C_hot:.2f} W/K")
        self.log(f"C_cold = ṁ·Cp = {cold.mass_flowrate:.4f} × {cold.cp:.2f}"
                 f" = {C_cold:.2f} W/K")

        if is_steam:
            # Steam is isothermal (condensing). Q is driven entirely by the
            # process (cold) side. Compute Q from cold side directly.
            if self.cold_outlet_T is None:
                raise ValueError(
                    f"Unit '{self.unit_id}': steam sizing requires cold_outlet_T "
                    f"(the process stream target temperature)."
                )
            T_co = self.cold_outlet_T
            T_ho = T_hi   # steam exits at saturation T (isothermal)
            Q    = C_cold * (T_co - T_ci)
            self.log(f"\nSteam heating (isothermal condensation):")
            self.log(f"Q = C_cold × (T_co - T_ci)")
            self.log(f"  = {C_cold:.2f} × ({T_co - 273.15:.2f} - {T_ci - 273.15:.2f})")
            self.log(f"  = {Q:.2f} W  ({Q/1000:.3f} kW)")
        else:
            if self.utility_fluid == UtilityFluid.COOLING_WATER:
                # CW return T is fixed by plant header — not a free variable.
                # User must specify hot_outlet_T (the process stream target T).
                object.__setattr__(self, 'cold_outlet_T', self.cw_return_T)
                if self.hot_outlet_T is None:
                    raise ValueError(
                        f"Unit '{self.unit_id}' (CW cooling, sizing): "
                        f"hot_outlet_T must be specified (process stream target T)."
                    )

            # Resolve outlet temperatures from user specifications
            T_ho, T_co = self._resolve_outlet_temperatures(
                T_hi, T_ci, C_hot, C_cold
            )

            # Validate temperature cross
            self._check_temperature_cross(T_hi, T_ho, T_ci, T_co)

            # Duty from hot side (primary reference)
            Q = C_hot * (T_hi - T_ho)
            self.log(f"\nQ = C_hot × (T_hi - T_ho)")
            self.log(f"  = {C_hot:.2f} × ({T_hi - 273.15:.2f} - {T_ho - 273.15:.2f})")
            self.log(f"  = {Q:.2f} W  ({Q/1000:.3f} kW)")

        # LMTD and F-factor
        lmtd, F = self._calc_lmtd_and_f(T_hi, T_ho, T_ci, T_co)
        self._lmtd    = lmtd
        self._f_factor = F

        # Required area
        if lmtd <= 0:
            raise InfeasibleDesignError(
                self.unit_id,
                f"LMTD = {lmtd:.4f} K ≤ 0. Check your temperature specifications."
            )

        area = Q / (self.U * F * lmtd)
        self.log(f"\nA = Q / (U · F · LMTD)")
        self.log(f"  = {Q:.2f} / ({self.U} × {F:.4f} × {lmtd:.4f})")
        self.log(f"  = {area:.4f} m²")

        self.area = area
        return T_ho, T_co, Q

    def _resolve_outlet_temperatures(
        self,
        T_hi: float,
        T_ci: float,
        C_hot: float,
        C_cold: float,
    ) -> tuple[float, float]:
        """
        Determine T_ho and T_co from user specifications.

        Logic
        -----
        Case 1: hot_outlet_T given         → derive T_co from energy balance
        Case 2: cold_outlet_T given        → derive T_ho from energy balance
        Case 3: neither given              → raise ValueError (under-specified)
        Case 4: both given                 → use both, verify energy balance
        """
        if self.hot_outlet_T is not None and self.cold_outlet_T is not None:
            # Both specified — trust the user, energy balance check happens later
            T_ho = self.hot_outlet_T
            T_co = self.cold_outlet_T
            self.log(f"\nBoth outlet Ts specified by user:")
            self.log(f"  T_ho = {T_ho - 273.15:.2f} °C")
            self.log(f"  T_co = {T_co - 273.15:.2f} °C")

        elif self.hot_outlet_T is not None:
            T_ho = self.hot_outlet_T
            Q    = C_hot * (T_hi - T_ho)
            T_co = T_ci + Q / C_cold
            self.log(f"\nHot outlet T specified: T_ho = {T_ho - 273.15:.2f} °C")
            self.log(f"Energy balance → T_co = {T_ci - 273.15:.2f} + "
                     f"{Q:.2f}/{C_cold:.2f} = {T_co - 273.15:.2f} °C")

        elif self.cold_outlet_T is not None:
            T_co = self.cold_outlet_T
            Q    = C_cold * (T_co - T_ci)
            T_ho = T_hi - Q / C_hot
            self.log(f"\nCold outlet T specified: T_co = {T_co - 273.15:.2f} °C")
            self.log(f"Energy balance → T_ho = {T_hi - 273.15:.2f} - "
                     f"{Q:.2f}/{C_hot:.2f} = {T_ho - 273.15:.2f} °C")

        else:
            # For utility-side streams the cold outlet T is already set
            # in _build_utility_stream_as_process. If we reach here with
            # neither specified, the spec is incomplete.
            raise ValueError(
                f"Unit '{self.unit_id}' (sizing mode): specify at least one of "
                f"hot_outlet_T or cold_outlet_T to define the duty."
            )

        return T_ho, T_co

    # =========================================================================
    # Rating path
    # =========================================================================

    def _solve_rating(
        self,
        hot: ProcessStream,
        cold: ProcessStream,
    ) -> tuple[float, float, float]:
        """
        Given area A and inlet temperatures → compute outlet temperatures.

        For process-to-process: full ε-NTU with Cr = C_min/C_max.
        For CW / steam utilities: Cr → 0 (isothermal utility side).
            ε = 1 - exp(-NTU),  NTU = U·A / C_process
            Q = ε · C_process · |T_utility_supply - T_process_in|

        Returns
        -------
        T_ho, T_co, Q
        """
        self.log_section("Rating Calculation (ε-NTU Method)")

        is_steam = self.utility_fluid in (
            UtilityFluid.LP_STEAM, UtilityFluid.MP_STEAM, UtilityFluid.HP_STEAM
        )

        # ── Utility-side rating: Cr = 0 model ────────────────────────────────
        if self.utility_fluid != UtilityFluid.PROCESS:
            if is_steam:
                # Steam condensing — isothermal hot side, fixed T_sat.
                # ε-NTU with Cr=0: ε = 1 - exp(-NTU), NTU = UA/C_cold
                C_process    = cold.heat_capacity_rate
                T_process_in = cold.temperature
                T_steam      = hot.temperature          # sat. T (isothermal)

                self.log(f"Steam utility — isothermal condensing (Cr=0 limit)")
                self.log(f"C_process (cold) = {C_process:.2f} W/K")
                NTU = (self.U * self.area) / C_process
                eps = 1.0 - math.exp(-NTU)
                Q   = eps * C_process * (T_steam - T_process_in)

                self.log(f"NTU = U·A / C_process = {self.U}×{self.area:.4f}/{C_process:.2f} = {NTU:.4f}")
                self.log(f"ε   = 1 - exp(-NTU) = {eps:.4f}")
                self.log(f"Q   = {eps:.4f}×{C_process:.2f}×{T_steam-T_process_in:.2f} = {Q:.2f} W")

                T_ho = T_steam                              # steam exits at sat. T
                T_co = T_process_in + Q / C_process
                self.log(f"T_process_out = {T_co-273.15:.2f} °C")
                self._ntu = NTU; self._effectiveness = eps

            else:
                # Cooling water — fixed supply T AND fixed return T.
                # Model: CW return T is a plant constraint (header pressure).
                # Solve: find T_ho such that Q_hot = U·A·LMTD(T_ho)
                # with T_co = cw_return_T fixed throughout.
                # One-variable root find using scipy.optimize.brentq.
                from scipy.optimize import brentq

                T_ci_cw = cold.temperature              # CW supply T
                T_co_cw = self.cw_return_T              # CW return T (fixed)
                C_hot_proc = hot.heat_capacity_rate
                T_hi = hot.temperature

                self.log(f"CW utility — fixed return T model")
                self.log(f"CW supply T  = {T_ci_cw-273.15:.1f} °C")
                self.log(f"CW return T  = {T_co_cw-273.15:.1f} °C (plant constraint)")
                self.log(f"C_hot = {C_hot_proc:.2f} W/K")

                def _residual(T_ho_try):
                    dT1 = T_hi - T_co_cw
                    dT2 = T_ho_try - T_ci_cw
                    if dT2 <= 1e-6: return 1e9
                    if abs(dT1 - dT2) < 1e-8:
                        lmtd_try = dT1
                    else:
                        lmtd_try = (dT1 - dT2) / math.log(dT1 / dT2)
                    Q_hx  = self.U * self.area * lmtd_try
                    Q_hot = C_hot_proc * (T_hi - T_ho_try)
                    return Q_hot - Q_hx

                T_ho = brentq(_residual, T_ci_cw + 0.01, T_hi - 0.01, xtol=1e-6)
                Q    = C_hot_proc * (T_hi - T_ho)
                T_co = T_co_cw

                NTU = (self.U * self.area) / C_hot_proc   # reference NTU
                eps  = Q / (C_hot_proc * (T_hi - T_ci_cw))

                self.log(f"Solved T_hot_out = {T_ho-273.15:.4f} °C")
                self.log(f"Q = {Q:.2f} W  ({Q/1000:.3f} kW)")
                self.log(f"NTU (ref) = {NTU:.4f},  ε = {eps:.4f}")
                self._ntu = NTU; self._effectiveness = eps

            lmtd, F = self._calc_lmtd_and_f(hot.temperature, T_ho,
                                              cold.temperature, T_co)
            self._lmtd = lmtd; self._f_factor = F
            return T_ho, T_co, Q

        # ── Process-to-process rating: full ε-NTU ────────────────────────────
        C_hot  = hot.heat_capacity_rate
        C_cold = cold.heat_capacity_rate
        C_min  = min(C_hot, C_cold)
        C_max  = max(C_hot, C_cold)
        Cr     = C_min / C_max   # heat capacity ratio [0, 1]

        self.log(f"C_hot  = {C_hot:.2f} W/K")
        self.log(f"C_cold = {C_cold:.2f} W/K")
        self.log(f"C_min  = {C_min:.2f} W/K  "
                 f"({'hot' if C_hot <= C_cold else 'cold'} side)")
        self.log(f"C_max  = {C_max:.2f} W/K")
        self.log(f"Cr     = C_min/C_max = {Cr:.4f}")

        NTU = (self.U * self.area) / C_min
        self.log(f"\nNTU = U·A / C_min")
        self.log(f"    = {self.U} × {self.area:.4f} / {C_min:.2f}")
        self.log(f"    = {NTU:.4f}")

        eps = self._calc_effectiveness(NTU, Cr)
        self.log(f"\nEffectiveness ε ({self.flow_config.value}) = {eps:.4f}")

        Q_max = C_min * (hot.temperature - cold.temperature)
        Q     = eps * Q_max
        self.log(f"\nQ_max = C_min × (T_hi - T_ci)")
        self.log(f"      = {C_min:.2f} × "
                 f"({hot.temperature - 273.15:.2f} - {cold.temperature - 273.15:.2f})")
        self.log(f"      = {Q_max:.2f} W")
        self.log(f"Q     = ε · Q_max = {eps:.4f} × {Q_max:.2f} = {Q:.2f} W")

        T_ho = hot.temperature  - Q / C_hot
        T_co = cold.temperature + Q / C_cold
        self.log(f"\nT_ho = T_hi - Q/C_hot = "
                 f"{hot.temperature - 273.15:.2f} - {Q/C_hot:.2f} = "
                 f"{T_ho - 273.15:.2f} °C")
        self.log(f"T_co = T_ci + Q/C_cold = "
                 f"{cold.temperature - 273.15:.2f} + {Q/C_cold:.2f} = "
                 f"{T_co - 273.15:.2f} °C")

        # Also compute LMTD for reference (not used in rating, but useful to report)
        lmtd, F = self._calc_lmtd_and_f(
            hot.temperature, T_ho, cold.temperature, T_co
        )
        self._lmtd        = lmtd
        self._f_factor    = F
        self._ntu         = NTU
        self._effectiveness = eps

        return T_ho, T_co, Q

    # =========================================================================
    # LMTD and F-factor
    # =========================================================================

    def _calc_lmtd_and_f(
        self,
        T_hi: float, T_ho: float,
        T_ci: float, T_co: float,
    ) -> tuple[float, float]:
        """
        Compute LMTD (counterflow basis) and F-factor correction.

        LMTD is always computed on a counterflow basis.
        F corrects for the actual flow arrangement:
            Q = U · A · F · LMTD_cf

        Returns
        -------
        lmtd : float  log mean temperature difference [K]
        F    : float  correction factor [dimensionless, 0 < F ≤ 1]
        """
        self.log_section("LMTD Calculation")

        # Counterflow terminal differences
        dT1 = T_hi - T_co   # hot inlet vs cold outlet
        dT2 = T_ho - T_ci   # hot outlet vs cold inlet

        self.log(f"Counterflow basis:")
        self.log(f"  ΔT₁ = T_hi - T_co = {T_hi - 273.15:.2f} - "
                 f"{T_co - 273.15:.2f} = {dT1:.2f} K")
        self.log(f"  ΔT₂ = T_ho - T_ci = {T_ho - 273.15:.2f} - "
                 f"{T_ci - 273.15:.2f} = {dT2:.2f} K")

        if dT1 <= 0 or dT2 <= 0:
            raise InfeasibleDesignError(
                self.unit_id,
                f"Temperature cross in counterflow basis: "
                f"ΔT₁={dT1:.2f} K, ΔT₂={dT2:.2f} K. "
                f"Both must be positive."
            )

        if abs(dT1 - dT2) < 1e-8:
            lmtd = dT1
            self.log(f"  ΔT₁ ≈ ΔT₂ → LMTD = {lmtd:.4f} K (limiting case)")
        else:
            lmtd = (dT1 - dT2) / math.log(dT1 / dT2)
            self.log(f"  LMTD = (ΔT₁ - ΔT₂) / ln(ΔT₁/ΔT₂)")
            self.log(f"       = ({dT1:.4f} - {dT2:.4f}) / "
                     f"ln({dT1:.4f}/{dT2:.4f})")
            self.log(f"       = {lmtd:.4f} K")

        F = self._calc_f_factor(T_hi, T_ho, T_ci, T_co)
        self.log(f"F-factor ({self.flow_config.value}) = {F:.4f}")

        return lmtd, F

    def _calc_f_factor(
        self,
        T_hi: float, T_ho: float,
        T_ci: float, T_co: float,
    ) -> float:
        """
        Compute LMTD correction factor F.

        Counterflow / parallel flow: F = 1.0 (exact).

        Shell & tube 1-2: Bowman-Mueller-Nagle (1940) analytical formula.
            R = (T_hi - T_ho) / (T_co - T_ci)   shell-side ratio
            P = (T_co - T_ci) / (T_hi - T_ci)   thermal effectiveness

        Special case R → 1: L'Hôpital limit of the BMN formula.
        """
        if self.flow_config in (FlowConfig.COUNTERFLOW, FlowConfig.PARALLELFLOW):
            return 1.0

        # Shell & tube 1-2
        dT_hot  = T_hi - T_ho
        dT_cold = T_co - T_ci

        if abs(dT_cold) < 1e-10:
            self.warn("Cold-side ΔT ≈ 0; F-factor undefined. Returning F = 1.0.")
            return 1.0

        R = dT_hot / dT_cold
        P = dT_cold / (T_hi - T_ci)

        self.log(f"\nF-factor parameters:")
        self.log(f"  R = (T_hi - T_ho)/(T_co - T_ci) = "
                 f"{dT_hot:.4f}/{dT_cold:.4f} = {R:.4f}")
        self.log(f"  P = (T_co - T_ci)/(T_hi - T_ci) = "
                 f"{dT_cold:.4f}/{T_hi - T_ci:.4f} = {P:.4f}")

        if P >= 1.0:
            self.warn(
                f"P = {P:.4f} ≥ 1.0 is thermodynamically impossible. "
                f"Check inlet temperatures."
            )
            return 1.0

        sqrt_R2_1 = math.sqrt(R**2 + 1.0)

        if abs(R - 1.0) < 1e-4:
            # L'Hôpital limiting form as R → 1
            # F = sqrt(2)·(1-P) / { (1-P)·ln[(2-P(2-sqrt(2))) / (2-P(2+sqrt(2)))] }
            sqrt2 = math.sqrt(2.0)
            numerator   = sqrt2 * (1.0 - P)
            inner_num   = 2.0 - P * (2.0 - sqrt2)
            inner_den   = 2.0 - P * (2.0 + sqrt2)
            if inner_den <= 0 or inner_num <= 0:
                self.warn("F-factor: argument of log ≤ 0 (R→1 case). Returning 1.0.")
                return 1.0
            denominator = (1.0 - P) * math.log(inner_num / inner_den)
        else:
            # General BMN formula
            # F = sqrt(R²+1) · ln[(1-P)/(1-PR)] /
            #     { (R-1) · ln[(2-P(R+1-sqrt(R²+1))) / (2-P(R+1+sqrt(R²+1)))] }
            if abs(1.0 - P * R) < 1e-10:
                self.warn("F-factor: 1 - P·R ≈ 0 (perfect effectiveness). "
                          "Returning F = 1.0.")
                return 1.0

            arg1    = (1.0 - P) / (1.0 - P * R)
            inner_a = 2.0 - P * (R + 1.0 - sqrt_R2_1)
            inner_b = 2.0 - P * (R + 1.0 + sqrt_R2_1)

            if arg1 <= 0 or inner_a <= 0 or inner_b == 0:
                self.warn(
                    f"F-factor: invalid log argument (arg1={arg1:.4f}, "
                    f"inner_a={inner_a:.4f}, inner_b={inner_b:.4f}). "
                    f"Returning F = 1.0."
                )
                return 1.0
            # inner_b is legitimately negative for typical S&T conditions
            # ln(inner_a / inner_b) requires inner_a and inner_b same sign
            if (inner_a > 0) != (inner_b > 0):
                # opposite signs → ln of negative → use abs and note sign flip
                # This means the denominator flips sign — handled by ratio
                pass

            numerator   = sqrt_R2_1 * math.log(arg1)
            denominator = (R - 1.0) * math.log(inner_a / inner_b)

        if abs(denominator) < 1e-10:
            self.warn("F-factor denominator ≈ 0. Returning F = 1.0.")
            return 1.0

        F = numerator / denominator

        if F < 0.75:
            self.warn(
                f"F-factor = {F:.3f} < 0.75. This configuration is thermally "
                f"inefficient. Consider adding a second shell pass."
            )
        if F > 1.0:
            self.warn(
                f"F-factor = {F:.4f} > 1.0 (should be impossible). "
                f"Check temperature specifications."
            )
            F = 1.0

        return F

    # =========================================================================
    # ε-NTU effectiveness
    # =========================================================================

    def _calc_effectiveness(self, NTU: float, Cr: float) -> float:
        """
        Compute heat exchanger effectiveness ε from NTU and Cr.

        ε = Q_actual / Q_max

        Relations from McCabe, Smith & Harriott (Chapter 15):

        Counterflow
        -----------
            Cr < 1:  ε = (1 - exp(-NTU(1-Cr))) / (1 - Cr·exp(-NTU(1-Cr)))
            Cr = 1:  ε = NTU / (1 + NTU)

        Parallel flow
        -------------
            ε = (1 - exp(-NTU(1+Cr))) / (1 + Cr)

        Shell & tube 1-2  (one shell pass, 2n tube passes)
        ---------------------------------------------------
            ε₁ = 2 / { 1 + Cr + sqrt(1+Cr²) ·
                       [(1 + exp(-NTU·sqrt(1+Cr²))) /
                        (1 - exp(-NTU·sqrt(1+Cr²)))] }
        """
        self.log_section("ε-NTU Effectiveness")
        self.log(f"NTU = {NTU:.4f},  Cr = {Cr:.4f}")

        if self.flow_config == FlowConfig.COUNTERFLOW:
            if abs(Cr - 1.0) < 1e-6:
                eps = NTU / (1.0 + NTU)
                self.log(f"Counterflow, Cr=1: ε = NTU/(1+NTU) = {eps:.4f}")
            else:
                exp_term = math.exp(-NTU * (1.0 - Cr))
                eps = (1.0 - exp_term) / (1.0 - Cr * exp_term)
                self.log(f"Counterflow: ε = (1-e^(-NTU(1-Cr)))/(1-Cr·e^(-NTU(1-Cr)))")
                self.log(f"           = {eps:.4f}")

        elif self.flow_config == FlowConfig.PARALLELFLOW:
            eps = (1.0 - math.exp(-NTU * (1.0 + Cr))) / (1.0 + Cr)
            self.log(f"Parallel flow: ε = (1-e^(-NTU(1+Cr)))/(1+Cr) = {eps:.4f}")

        elif self.flow_config == FlowConfig.SHELL_TUBE_1_2:
            sqrt_term = math.sqrt(1.0 + Cr**2)
            exp_arg   = -NTU * sqrt_term
            exp_val   = math.exp(exp_arg)
            if abs(1.0 - exp_val) < 1e-10:
                self.warn("Shell & tube ε: exp term ≈ 1 (very low NTU). "
                          "Falling back to counterflow.")
                eps = NTU / (1.0 + NTU) if abs(Cr - 1.0) < 1e-6 else \
                      (1.0 - math.exp(-NTU*(1.0-Cr))) / \
                      (1.0 - Cr*math.exp(-NTU*(1.0-Cr)))
            else:
                eps = 2.0 / (
                    1.0 + Cr + sqrt_term * (1.0 + exp_val) / (1.0 - exp_val)
                )
            self.log(f"Shell & tube 1-2: ε = {eps:.4f}")

        else:
            raise ValueError(
                f"Unknown flow_config: {self.flow_config}"
            )

        # Clip to [0, 1] — floating point can push slightly outside
        eps = max(0.0, min(1.0, eps))
        return eps

    # =========================================================================
    # Utility stream builders
    # =========================================================================

    def _build_utility_stream_as_process(
        self, process_stream: ProcessStream
    ) -> ProcessStream:
        """
        Create a placeholder ProcessStream representing the utility side.

        For cooling water: cold stream from supply to return temperature.
        For steam: hot stream at saturation temperature (condensing).

        For CW in rating mode: flowrate is set so C_cold >> C_hot, making
        CW always C_max. This is physically correct — the CW system adjusts
        its flowrate to maintain the return temperature, so it is never the
        capacity-limiting side.

        This ProcessStream is used internally only — it is NOT added to
        outlet_streams (unless utility_fluid == "process").
        """
        if self.utility_fluid == UtilityFluid.COOLING_WATER:
            # CW flowrate is unknown in rating mode — but CW outlet T is fixed
            # by plant design (CW return header temperature).
            # Model: treat CW as having a fixed outlet T = cw_return_T.
            # This is equivalent to Cr → 0 (infinite CW flow), which gives
            # ε = 1 - exp(-NTU) for counterflow. We achieve this numerically
            # by setting CW flowrate very large so C_cold >> C_hot.
            # The actual CW flowrate is back-calculated from Q after solve.
            # Factor of 1000 makes Cr < 0.001, error in ε < 0.1%.
            cw_flowrate = process_stream.heat_capacity_rate * 1000.0 / self.cw_cp

            return ProcessStream(
                name="cooling_water_supply",
                temperature=self.cw_supply_T,
                pressure=400_000.0,
                mass_flowrate=cw_flowrate,
                cp=self.cw_cp,
                density=995.0,
                viscosity=8.0e-4,
                thermal_conductivity=0.606,
                phase="liquid",
                source_unit=f"{self.unit_id}_utility",
            )

        elif self.utility_fluid in (
            UtilityFluid.LP_STEAM,
            UtilityFluid.MP_STEAM,
            UtilityFluid.HP_STEAM,
        ):
            # Steam is the hot side — condensing at saturation T
            T_sat = _STEAM_SATURATION_T[self.utility_fluid]

            if process_stream.temperature >= T_sat:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"Process stream inlet T ({process_stream.temperature - 273.15:.1f}°C) "
                    f"≥ {self.utility_fluid.value} saturation T "
                    f"({T_sat - 273.15:.1f}°C). "
                    f"Steam cannot heat this stream."
                )

            # For sizing, cold outlet T drives the duty.
            # Set hot_outlet_T = T_sat (isothermal condensation)
            if self.hot_outlet_T is None:
                object.__setattr__(self, 'hot_outlet_T', T_sat)

            return ProcessStream(
                name=f"{self.utility_fluid.value}_supply",
                temperature=T_sat,
                pressure=350_000.0,
                mass_flowrate=1.0,      # placeholder
                cp=4200.0,              # not used — latent heat path
                density=2.5,            # steam density approx
                viscosity=1.5e-5,
                thermal_conductivity=0.025,
                phase="mixed",          # condensing
                source_unit=f"{self.unit_id}_utility",
            )

        else:
            raise ValueError(
                f"Unit '{self.unit_id}': utility_fluid='{self.utility_fluid}' "
                f"requires both 'hot' and 'cold' inlets. Use utility_fluid='process'."
            )

    def _build_utility_stream(self, Q: float) -> None:
        """
        Create UtilityStream object with actual consumption quantities.
        Appended to self.utility_streams for UtilityTracker aggregation.
        """
        if self.utility_fluid == UtilityFluid.PROCESS:
            return  # no utility — process-to-process

        u = UtilityStream(
            utility_type=self.utility_fluid.value,
            unit_id=self.unit_id,
            duty_kw=Q / 1000.0,
        )

        if self.utility_fluid == UtilityFluid.COOLING_WATER:
            delta_T = self.cw_return_T - self.cw_supply_T
            u.mass_flowrate = Q / (self.cw_cp * delta_T)
            u.supply_temperature = self.cw_supply_T
            u.return_temperature = self.cw_return_T
            self.log(f"\nCooling water flowrate = Q / (Cp·ΔT)")
            self.log(f"  = {Q:.2f} / ({self.cw_cp} × {delta_T:.1f})")
            self.log(f"  = {u.mass_flowrate:.4f} kg/s")

        elif self.utility_fluid in _STEAM_LATENT_HEAT:
            lambda_steam = _STEAM_LATENT_HEAT[self.utility_fluid]
            u.mass_flowrate = Q / lambda_steam
            u.supply_temperature = _STEAM_SATURATION_T[self.utility_fluid]
            u.return_temperature  = _STEAM_SATURATION_T[self.utility_fluid]
            self.log(f"\n{self.utility_fluid.value} condensate rate = Q / λ")
            self.log(f"  = {Q:.2f} / {lambda_steam:.0f}")
            self.log(f"  = {u.mass_flowrate:.4f} kg/s")

        self.utility_streams.append(u)

    # =========================================================================
    # Validation helpers
    # =========================================================================

    def _check_phase(self, stream: ProcessStream, role: str) -> None:
        """
        Raise PhaseError for two-phase streams.

        The single-zone LMTD method is invalid when phase change occurs
        inside the exchanger. Condensers and reboilers require zone
        decomposition — not yet implemented.
        """
        if stream.phase == "mixed":
            raise PhaseError(
                self.unit_id,
                stream.phase,
                f"Stream '{stream.name}' ({role} side) is two-phase. "
                f"The LMTD/ε-NTU method requires single-phase streams. "
                f"Condensers and reboilers are not yet supported."
            )

    def _check_temperature_cross(
        self,
        T_hi: float, T_ho: float,
        T_ci: float, T_co: float,
    ) -> None:
        """
        Detect temperature cross violations.

        Counterflow: T_ho must be > T_ci  (hot outlet > cold inlet)
        Parallel:    T_ho must be > T_co  (otherwise Q would be negative)
        """
        if self.flow_config == FlowConfig.COUNTERFLOW:
            if T_ho < T_ci:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"Temperature cross: hot outlet ({T_ho - 273.15:.1f}°C) "
                    f"< cold inlet ({T_ci - 273.15:.1f}°C). "
                    f"Infeasible for counterflow. "
                    f"Increase hot side flowrate or reduce duty."
                )
        elif self.flow_config == FlowConfig.PARALLELFLOW:
            if T_ho < T_co:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"Temperature cross (parallel flow): "
                    f"hot outlet ({T_ho - 273.15:.1f}°C) "
                    f"< cold outlet ({T_co - 273.15:.1f}°C)."
                )

    def _warn_u_value(
        self,
        hot: ProcessStream,
        cold: ProcessStream,
    ) -> None:
        """
        Warn if U is outside typical literature range for this service.
        """
        hot_phase  = hot.phase
        cold_phase = "vapor" if self.utility_fluid in (
            UtilityFluid.LP_STEAM, UtilityFluid.MP_STEAM, UtilityFluid.HP_STEAM
        ) else cold.phase

        if hot_phase == "liquid" and cold_phase == "liquid":
            key = "liquid_liquid"
        elif hot_phase in ("vapor", "mixed") and cold_phase == "liquid":
            key = "condensing_steam_liquid"
        elif hot_phase == "liquid" and cold_phase == "vapor":
            key = "liquid_vaporising"
        elif hot_phase == "vapor" and cold_phase == "vapor":
            key = "gas_gas"
        else:
            return  # skip for mixed/supercritical

        lo, hi = _U_RANGES.get(key, (0, 1e9))
        if not (lo <= self.U <= hi):
            self.warn(
                f"U = {self.U} W/(m²·K) is outside typical range for "
                f"{key} service [{lo}, {hi}] W/(m²·K). "
                f"(Ref: Coulson & Richardson Vol. 1, Table 12.1)"
            )

    @staticmethod
    def _min_approach_temp(
        T_hi: float, T_ho: float,
        T_ci: float, T_co: float,
    ) -> float:
        """
        Minimum temperature difference (approach temperature) [K].

        For counterflow: min(T_hi - T_co, T_ho - T_ci)
        """
        return min(T_hi - T_co, T_ho - T_ci)

    # =========================================================================
    # Logging helpers
    # =========================================================================

    def _log_stream(self, stream: ProcessStream, label: str) -> None:
        self.log(f"\n{label}:")
        self.log(f"  T   = {stream.temperature - 273.15:.2f} °C")
        self.log(f"  ṁ   = {stream.mass_flowrate:.4f} kg/s")
        self.log(f"  Cp  = {stream.cp:.2f} J/(kg·K)")
        self.log(f"  ṁCp = {stream.heat_capacity_rate:.2f} W/K")
        self.log(f"  phase = {stream.phase}")

    # =========================================================================
    # summary()
    # =========================================================================

    def summary(self) -> dict:
        """
        Flat dict of key results for API response and UI rendering.

        All floats rounded to 4 significant figures.
        No ProcessStream or UtilityStream objects.
        """
        
        base = self.base_summary()

        hx_results = {
            "selected_class": self.selected_class.value if self.selected_class else None,
            "mode":          self.mode.value,
            "flow_config":   self.flow_config.value,
            "utility_fluid": self.utility_fluid.value,
            "U_W_m2K":       self.U,
            "area_m2":       round(self.area, 4) if self.area is not None else None,
            "duty_kW":       round(self._duty_kw, 4),
            "LMTD_K":        round(self._lmtd, 4),
            "F_factor":      round(self._f_factor, 4),
            "NTU":           round(self._ntu, 4),
            "effectiveness": round(self._effectiveness, 4),
            "hot_outlet_T_C":  round(self._hot_outlet_T - 273.15, 2)
                               if self._hot_outlet_T else None,
            "cold_outlet_T_C": round(self._cold_outlet_T - 273.15, 2)
                               if self._cold_outlet_T else None,
            "dt_min_K":      round(self._dt_min, 2),
        }

        # Utility consumption summary
        for u in self.utility_streams:
            if u.utility_type == "cooling_water":
                hx_results["cw_flowrate_kg_s"] = round(u.mass_flowrate, 4)
                hx_results["cw_duty_kW"]       = round(u.duty_kw, 3)
            elif "steam" in u.utility_type:
                hx_results["steam_type"]           = u.utility_type
                hx_results["steam_flowrate_kg_s"]  = round(u.mass_flowrate, 4)
                hx_results["steam_duty_kW"]        = round(u.duty_kw, 3)

        return {**base, **hx_results}