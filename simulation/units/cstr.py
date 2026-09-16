"""
simulation/units/cstr.py

Continuously Stirred Tank Reactor (CSTR) — steady-state design.

Assumes perfect mixing (outlet conditions = reactor conditions).
Solves the mole balance design equation:

    V = F_A0 · X / (-r_A)   [design mode]
    X = V · (-r_A) / F_A0   [rating mode, solved iteratively]

Kinetics: power-law rate expression
    -r_A = k(T) · C_A^n
    k(T) = A · exp(-Ea / R·T)   [Arrhenius]

Thermal modes
-------------
isothermal : T constant at T_rxn. Rate constant evaluated at T_rxn.
adiabatic  : T rises (exo) or falls (endo) with conversion.
             Coupled mole + energy balance. For CSTR (algebraic):

             T = T_in + (-ΔH_rxn · C_A0 · X) / (ρ · Cp)
             → Solve simultaneously with mole balance.

References
----------
- Fogler, H.S., Elements of Chemical Reaction Engineering, 5th ed.
  Chapters 2 (mole balance), 5 (isothermal), 8 (non-isothermal)
- McCabe, Smith & Harriott, Chapter 25
- Coulson & Richardson Vol. 3, Chapter 1
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from scipy.optimize import brentq

from simulation.core.stream import ProcessStream, UtilityStream
from simulation.core.unit_operation import UnitOperation
from simulation.core.exceptions import InfeasibleDesignError, StreamError

R_GAS = 8.314  # J/(mol·K)


class ThermalMode(str, Enum):
    ISOTHERMAL = "isothermal"
    ADIABATIC  = "adiabatic"


class ReactorMode(str, Enum):
    DESIGN = "design"   # given X → find V
    RATING = "rating"   # given V → find X


@dataclass
class CSTR(UnitOperation):
    """
    CSTR steady-state design.

    Inlet stream must contain the key reactant A.
    Add via add_inlet("feed", stream).

    Kinetic parameters
    ------------------
    k_ref : float
        Rate constant at T_ref [mol^(1-n) · L^(n-1) · s^-1].
        If Ea = 0, k is used directly (no temperature correction).
    T_ref : float
        Reference temperature for k_ref [K]. Default 298.15 K.
    Ea : float
        Activation energy [J/mol]. 0 = no Arrhenius correction.
    n : float
        Reaction order [-]. Any positive value.

    Thermochemistry
    ---------------
    delta_H_rxn : float
        Heat of reaction [J/mol_A]. Negative = exothermic.
        Required for adiabatic mode and heat duty calculation.

    Operating specification
    -----------------------
    mode : ReactorMode
        "design" → specify X_target, find V.
        "rating" → specify volume_m3, find X.
    thermal_mode : ThermalMode
        "isothermal" → T = T_rxn throughout.
        "adiabatic"  → T coupled to conversion.
    T_rxn : float
        Reaction temperature [K].
        Isothermal: fixed throughout.
        Adiabatic: inlet temperature (T rises/falls with conversion).
    X_target : float
        Target fractional conversion (0, 1). Required for design mode.
    volume_m3 : float
        Reactor volume [m³]. Required for rating mode.
    C_A0 : float
        Initial concentration of A [mol/m³].
        If None, estimated from feed stream density and molecular weight.
    MW_A : float
        Molecular weight of A [g/mol]. Used for molar flowrate calculation.
    """

    unit_type: str = field(default="CSTR", init=False)

    # Kinetics
    k_ref:   float = 0.01       # rate constant at T_ref
    T_ref:   float = 298.15     # K
    Ea:      float = 50_000.0   # J/mol
    n:       float = 1.0        # reaction order

    # Thermochemistry
    delta_H_rxn: float = -50_000.0  # J/mol_A (negative = exothermic)

    # Operating spec
    mode:         ReactorMode  = ReactorMode.DESIGN
    thermal_mode: ThermalMode  = ThermalMode.ISOTHERMAL
    T_rxn:        float        = 298.15     # K
    X_target:     float        = 0.90       # design mode
    volume_m3:    Optional[float] = None    # rating mode

    # Feed specification
    C_A0:  float = 1000.0   # mol/m³ (1 mol/L)
    MW_A:  float = 100.0    # g/mol

    # Internal results
    _X:       float = field(default=0.0, init=False, repr=False)
    _V:       float = field(default=0.0, init=False, repr=False)
    _tau:     float = field(default=0.0, init=False, repr=False)
    _T_out:   float = field(default=0.0, init=False, repr=False)
    _C_A_out: float = field(default=0.0, init=False, repr=False)
    _r_A_out: float = field(default=0.0, init=False, repr=False)
    _k_rxn:   float = field(default=0.0, init=False, repr=False)
    _Q_kw:    float = field(default=0.0, init=False, repr=False)

    def __post_init__(self):
        self.unit_type = "CSTR"

    # =========================================================================
    # solve()
    # =========================================================================

    def solve(self) -> None:
        self.reset()

        self.log_section("CSTR Setup")
        self.log(f"Unit:          {self.unit_id}")
        self.log(f"Mode:          {self.mode.value}")
        self.log(f"Thermal mode:  {self.thermal_mode.value}")
        self.log(f"Reaction order n = {self.n}")
        self.log(f"k_ref = {self.k_ref}  at T_ref = {self.T_ref - 273.15:.1f}°C")
        self.log(f"Ea    = {self.Ea:.0f} J/mol")
        self.log(f"ΔH_rxn = {self.delta_H_rxn:.0f} J/mol_A")
        self.log(f"C_A0  = {self.C_A0:.2f} mol/m³")

        # ── Validate ──────────────────────────────────────────────────────────
        feed = self.get_inlet("feed")
        self._log_stream(feed)

        if self.mode == ReactorMode.DESIGN:
            if not 0 < self.X_target < 1.0:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"X_target = {self.X_target} must be in (0, 1). "
                    f"X = 1.0 requires infinite volume."
                )
        else:
            if self.volume_m3 is None or self.volume_m3 <= 0:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"Rating mode requires volume_m3 > 0."
                )

        # ── Molar flowrate ────────────────────────────────────────────────────
        self.log_section("Molar Flowrate")
        F_A0 = (feed.mass_flowrate / self.MW_A) * 1000  # mol/s
        self.log(f"F_A0 = ṁ / MW_A × 1000")
        self.log(f"     = {feed.mass_flowrate:.4f} / {self.MW_A} × 1000")
        self.log(f"     = {F_A0:.4f} mol/s")

        # ── Dispatch ──────────────────────────────────────────────────────────
        if self.thermal_mode == ThermalMode.ISOTHERMAL:
            X, V, T_out = self._solve_isothermal(feed, F_A0)
        else:
            X, V, T_out = self._solve_adiabatic(feed, F_A0)

        # ── Derived quantities ────────────────────────────────────────────────
        C_A_out = self.C_A0 * (1 - X)
        k_out   = self._arrhenius(T_out)
        r_A_out = k_out * C_A_out ** self.n
        tau     = V / feed.volumetric_flowrate

        self._X       = X
        self._V       = V
        self._tau     = tau
        self._T_out   = T_out
        self._C_A_out = C_A_out
        self._r_A_out = r_A_out
        self._k_rxn   = k_out

        # ── Heat duty ─────────────────────────────────────────────────────────
        self._calc_heat_duty(feed, F_A0, X, T_out)

        # ── CSTR vs PFR volume hint ───────────────────────────────────────────
        V_pfr_approx = self._pfr_volume_approx(F_A0, X, T_out)
        if V_pfr_approx > 0:
            ratio = V / V_pfr_approx
            self.log(f"\nV_CSTR / V_PFR ≈ {ratio:.2f}")
            if ratio > 3:
                self.warn(
                    f"V_CSTR / V_PFR ≈ {ratio:.1f} — a PFR would require "
                    f"~{ratio:.1f}× less volume for this conversion. "
                    f"Consider switching to a PFR or using a CSTR-PFR series."
                )

        # ── Build outlet stream ───────────────────────────────────────────────
        self.outlet_streams["outlet"] = feed.copy_with(
            name=f"{feed.name}_out",
            temperature=T_out,
            source_unit=self.unit_id,
        )

        # ── Results log ───────────────────────────────────────────────────────
        self.log_section("Results")
        self.log(f"Conversion X     = {X:.4f}  ({X*100:.2f}%)")
        self.log(f"Volume V         = {V:.4f} m³  ({V*1000:.2f} L)")
        self.log(f"Residence time τ = {tau:.2f} s  ({tau/60:.2f} min)")
        self.log(f"T_out            = {T_out - 273.15:.2f} °C")
        self.log(f"C_A_out          = {C_A_out:.4f} mol/m³")
        self.log(f"k(T_out)         = {k_out:.4e}")
        self.log(f"-r_A(outlet)     = {r_A_out:.4e} mol/(m³·s)")
        self.log(f"Heat duty Q      = {self._Q_kw:.3f} kW")

        self.is_solved = True

    # =========================================================================
    # Isothermal solve
    # =========================================================================

    def _solve_isothermal(
        self, feed: ProcessStream, F_A0: float
    ) -> tuple[float, float, float]:
        """
        Isothermal CSTR — T constant at T_rxn.

        Design:  V = F_A0 · X / (-r_A(X))
                 -r_A = k(T) · [C_A0(1-X)]^n

        Rating:  Solve  F_A0·X = V·k·C_A0^n·(1-X)^n  for X
                 via brentq on residual(X) = LHS - RHS
        """
        self.log_section("Isothermal Mole Balance")

        T  = self.T_rxn
        k  = self._arrhenius(T)
        self.log(f"T_rxn = {T - 273.15:.2f} °C")
        self.log(f"k(T)  = A·exp(-Ea/RT) = {self.k_ref:.4e}·exp(-{self.Ea:.0f}"
                 f"/(8.314·{T:.2f})) = {k:.4e}")

        if self.mode == ReactorMode.DESIGN:
            X     = self.X_target
            C_A   = self.C_A0 * (1 - X)
            r_A   = k * C_A ** self.n
            V     = F_A0 * X / r_A

            self.log(f"\nDesign mode: X = {X:.4f}")
            self.log(f"C_A = C_A0·(1-X) = {self.C_A0}·(1-{X}) = {C_A:.4f} mol/m³")
            self.log(f"-r_A = k·C_A^n = {k:.4e}·{C_A:.4f}^{self.n} = {r_A:.4e} mol/(m³·s)")
            self.log(f"V = F_A0·X / (-r_A) = {F_A0:.4f}·{X} / {r_A:.4e} = {V:.4f} m³")

        else:  # rating
            V = self.volume_m3
            self.log(f"\nRating mode: V = {V:.4f} m³")
            self.log("Solving F_A0·X = V·k·C_A0^n·(1-X)^n for X...")

            def residual(X):
                if X <= 0 or X >= 1:
                    return 1e9
                C_A = self.C_A0 * (1 - X)
                r_A = k * C_A ** self.n
                return F_A0 * X - V * r_A

            try:
                X = brentq(residual, 1e-8, 1 - 1e-8, xtol=1e-8)
            except ValueError:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"Could not find feasible conversion for V={V:.4f} m³. "
                    f"Check kinetic parameters and feed conditions."
                )
            self.log(f"Converged: X = {X:.6f}")

        return X, V, T

    # =========================================================================
    # Adiabatic solve
    # =========================================================================

    def _solve_adiabatic(
        self, feed: ProcessStream, F_A0: float
    ) -> tuple[float, float, float]:
        """
        Adiabatic CSTR — T rises/falls with conversion.

        Coupled algebraic equations (CSTR = perfect mixing → algebraic):

        Energy balance:
            T = T_in + (-ΔH_rxn · C_A0 · X) / (ρ · Cp)
            Δ_T_ad = (-ΔH_rxn · C_A0) / (ρ · Cp)  [adiabatic T rise per unit X]
            T(X) = T_in + X · ΔT_ad

        Mole balance:
            V = F_A0 · X / (-r_A(T(X), X))

        For design mode: X is given → T(X) from energy balance → V from mole balance.
        For rating mode: solve simultaneously for X using brentq.
        """
        self.log_section("Adiabatic Energy Balance")

        T_in  = self.T_rxn   # inlet temperature
        rho   = feed.density
        Cp    = feed.cp

        # Adiabatic temperature rise [K per unit conversion]
        dT_ad = (-self.delta_H_rxn * self.C_A0) / (rho * Cp)

        self.log(f"T_inlet = {T_in - 273.15:.2f} °C")
        self.log(f"ΔH_rxn  = {self.delta_H_rxn:.0f} J/mol_A")
        self.log(f"ρ·Cp    = {rho:.2f} × {Cp:.2f} = {rho*Cp:.2f} J/(m³·K)")
        self.log(f"ΔT_ad   = -ΔH_rxn·C_A0 / (ρ·Cp)")
        self.log(f"        = -{self.delta_H_rxn:.0f}×{self.C_A0:.2f} / {rho*Cp:.2f}")
        self.log(f"        = {dT_ad:.4f} K per unit conversion")

        if abs(dT_ad) > 100:
            self.warn(
                f"|ΔT_ad| = {abs(dT_ad):.1f} K — large adiabatic temperature rise. "
                f"Runaway risk for exothermic reactions. "
                f"Consider staged cooling or heat removal."
            )

        def T_from_X(X):
            return T_in + X * dT_ad

        if self.mode == ReactorMode.DESIGN:
            X   = self.X_target
            T   = T_from_X(X)
            k   = self._arrhenius(T)
            C_A = self.C_A0 * (1 - X)
            r_A = k * C_A ** self.n

            if T <= 0:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"Adiabatic outlet T = {T:.2f} K ≤ 0 K at X = {X}. "
                    f"Check ΔH_rxn and feed conditions."
                )

            V = F_A0 * X / r_A

            self.log_section("Adiabatic Mole Balance")
            self.log(f"X      = {X:.4f}")
            self.log(f"T_out  = T_in + X·ΔT_ad = {T_in-273.15:.2f} + {X:.4f}×{dT_ad:.4f}"
                     f" = {T-273.15:.4f} °C")
            self.log(f"k(T)   = {k:.4e}")
            self.log(f"C_A    = {C_A:.4f} mol/m³")
            self.log(f"-r_A   = {r_A:.4e} mol/(m³·s)")
            self.log(f"V      = {V:.4f} m³")

        else:
            V = self.volume_m3
            self.log_section("Adiabatic Rating — solving for X")

            def residual(X):
                if X <= 0 or X >= 1:
                    return 1e9
                T   = T_from_X(X)
                if T <= 0:
                    return 1e9
                k   = self._arrhenius(T)
                C_A = self.C_A0 * (1 - X)
                r_A = k * C_A ** self.n
                return F_A0 * X - V * r_A

            try:
                X = brentq(residual, 1e-8, 1 - 1e-8, xtol=1e-8)
            except ValueError:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"Could not solve adiabatic CSTR for V = {V:.4f} m³. "
                    f"Check kinetic parameters."
                )

            T = T_from_X(X)
            self.log(f"Converged: X = {X:.6f}  T_out = {T-273.15:.4f} °C")

        return X, V, T

    # =========================================================================
    # Heat duty
    # =========================================================================

    def _calc_heat_duty(
        self, feed: ProcessStream, F_A0: float, X: float, T_out: float
    ) -> None:
        """
        Q = F_A0 · X · ΔH_rxn  [W]

        Positive Q → heat must be supplied (endothermic).
        Negative Q → heat must be removed (exothermic).
        For isothermal: Q = full reaction heat.
        For adiabatic: Q = 0 by definition (but we still compute to confirm).
        """
        self.log_section("Heat Duty")

        Q = F_A0 * X * self.delta_H_rxn   # W
        Q_kw = Q / 1000

        self.log(f"Q = F_A0 · X · ΔH_rxn")
        self.log(f"  = {F_A0:.4f} × {X:.4f} × {self.delta_H_rxn:.0f}")
        self.log(f"  = {Q:.2f} W  ({Q_kw:.3f} kW)")
        self.log(f"  {'Endothermic — heat input required' if Q > 0 else 'Exothermic — heat must be removed'}")

        if self.thermal_mode == ThermalMode.ADIABATIC:
            self.log("  (Adiabatic mode: Q_removed = 0, heat stays in fluid)")

        self._Q_kw = Q_kw

        # Utility stream
        u = UtilityStream(
            utility_type="heating_duty" if Q > 0 else "cooling_duty",
            unit_id=self.unit_id,
            duty_kw=abs(Q_kw),
        )
        self.utility_streams.append(u)

    # =========================================================================
    # CSTR vs PFR hint
    # =========================================================================

    def _pfr_volume_approx(self, F_A0: float, X: float, T: float) -> float:
        """
        Approximate PFR volume using Simpson's rule over 50 intervals.
        V_PFR = F_A0 · ∫₀ˣ dX / (-r_A(X))
        """
        try:
            from scipy.integrate import quad
            k = self._arrhenius(T)

            def integrand(xi):
                C_A = self.C_A0 * (1 - xi)
                if C_A <= 0:
                    return 1e10
                r_A = k * C_A ** self.n
                if r_A <= 0:
                    return 1e10
                return 1.0 / r_A

            V_pfr, _ = quad(integrand, 0, X)
            return F_A0 * V_pfr
        except Exception:
            return 0.0

    # =========================================================================
    # Arrhenius
    # =========================================================================

    def _arrhenius(self, T: float) -> float:
        """k(T) = k_ref · exp(-Ea/R · (1/T - 1/T_ref))"""
        if self.Ea == 0:
            return self.k_ref
        return self.k_ref * math.exp(
            -self.Ea / R_GAS * (1.0 / T - 1.0 / self.T_ref)
        )

    # =========================================================================
    # Logging helper
    # =========================================================================

    def _log_stream(self, stream: ProcessStream) -> None:
        self.log(f"\nFeed stream '{stream.name}':")
        self.log(f"  T   = {stream.temperature_c:.2f} °C")
        self.log(f"  ṁ   = {stream.mass_flowrate:.4f} kg/s")
        self.log(f"  ρ   = {stream.density:.2f} kg/m³")
        self.log(f"  Cp  = {stream.cp:.2f} J/(kg·K)")
        self.log(f"  Q_v = {stream.volumetric_flowrate:.5f} m³/s")

    # =========================================================================
    # summary()
    # =========================================================================

    def summary(self) -> dict:
        base = self.base_summary()
        return {
            **base,
            "reactor_type":      "CSTR",
            "mode":              self.mode.value,
            "thermal_mode":      self.thermal_mode.value,
            "conversion":        round(self._X, 6),
            "conversion_pct":    round(self._X * 100, 3),
            "volume_m3":         round(self._V, 6),
            "volume_L":          round(self._V * 1000, 3),
            "residence_time_s":  round(self._tau, 3),
            "residence_time_min":round(self._tau / 60, 4),
            "T_out_C":           round(self._T_out - 273.15, 3),
            "C_A_out_mol_m3":    round(self._C_A_out, 4),
            "rate_mol_m3_s":     round(self._r_A_out, 6),
            "k_rxn":             round(self._k_rxn, 8),
            "heat_duty_kW":      round(self._Q_kw, 4),
            "n_order":           self.n,
            "Ea_J_mol":          self.Ea,
            "delta_H_rxn_J_mol": self.delta_H_rxn,
            "C_A0_mol_m3":       self.C_A0,
        }
