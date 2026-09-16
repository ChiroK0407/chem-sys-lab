"""
simulation/units/pfr.py

Plug Flow Reactor (PFR) — steady-state design.

No axial mixing. Mole balance is an ODE integrated along reactor length:

    dF_A / dV = r_A
    F_A0 · dX / dV = -r_A

Integrated form:
    V = F_A0 · ∫₀ˣ dX / (-r_A)

Kinetics: power-law rate expression (same as CSTR)
    -r_A = k(T) · C_A^n
    k(T) = A · exp(-Ea / R·T)

Thermal modes
-------------
isothermal : T constant. Simple quadrature over X.
adiabatic  : Coupled ODE system in [X, T]:
             dX/dV  = -r_A / F_A0
             dT/dV  = (-ΔH_rxn · (-r_A)) / (F_total · Cp)

Profile output (unique to PFR)
-------------------------------
solve() stores X vs V/τ profiles and 1/-r_A vs X (Levenspiel plot data).
Returned in summary() for the frontend chart.

References
----------
- Fogler, H.S., Elements of Chemical Reaction Engineering, 5th ed.
  Chapters 2, 5, 8
- Levenspiel, O., Chemical Reaction Engineering, 3rd ed., Chapter 5
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, List

import numpy as np
from scipy.integrate import solve_ivp

from simulation.core.stream import ProcessStream, UtilityStream
from simulation.core.unit_operation import UnitOperation
from simulation.core.exceptions import InfeasibleDesignError

R_GAS = 8.314  # J/(mol·K)

# Re-use the same thermal and reactor mode enums
from simulation.units.cstr import ThermalMode, ReactorMode


@dataclass
class PFR(UnitOperation):
    """
    PFR steady-state design.

    Inlet stream keyed "feed". Same kinetic parameters as CSTR.

    Additional outputs vs CSTR
    --------------------------
    - X vs V profile (concentration profile along reactor)
    - Levenspiel plot data: 1/(-r_A) vs X
    - Volume comparison with CSTR at same X

    Parameters
    ----------
    Same as CSTR. Additional:
    n_points : int
        Number of integration points for profile output. Default 100.
    """

    unit_type: str = field(default="PFR", init=False)

    # Kinetics
    k_ref:   float = 0.01
    T_ref:   float = 298.15
    Ea:      float = 50_000.0
    n:       float = 1.0

    # Thermochemistry
    delta_H_rxn: float = -50_000.0  # J/mol_A

    # Operating spec
    mode:         ReactorMode  = ReactorMode.DESIGN
    thermal_mode: ThermalMode  = ThermalMode.ISOTHERMAL
    T_rxn:        float        = 298.15
    X_target:     float        = 0.90
    volume_m3:    Optional[float] = None

    # Feed
    C_A0:  float = 1000.0
    MW_A:  float = 100.0

    # Profile resolution
    n_points: int = 100

    # Internal results
    _X:        float = field(default=0.0,  init=False, repr=False)
    _V:        float = field(default=0.0,  init=False, repr=False)
    _tau:      float = field(default=0.0,  init=False, repr=False)
    _T_out:    float = field(default=0.0,  init=False, repr=False)
    _C_A_out:  float = field(default=0.0,  init=False, repr=False)
    _k_rxn:    float = field(default=0.0,  init=False, repr=False)
    _Q_kw:     float = field(default=0.0,  init=False, repr=False)

    # Profile data (returned for charting)
    _V_profile:   List[float] = field(default_factory=list, init=False, repr=False)
    _X_profile:   List[float] = field(default_factory=list, init=False, repr=False)
    _T_profile:   List[float] = field(default_factory=list, init=False, repr=False)
    _rA_profile:  List[float] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self):
        self.unit_type = "PFR"

    # =========================================================================
    # solve()
    # =========================================================================

    def solve(self) -> None:
        self.reset()

        self.log_section("PFR Setup")
        self.log(f"Unit:          {self.unit_id}")
        self.log(f"Mode:          {self.mode.value}")
        self.log(f"Thermal mode:  {self.thermal_mode.value}")
        self.log(f"n = {self.n},  k_ref = {self.k_ref},  Ea = {self.Ea:.0f} J/mol")
        self.log(f"ΔH_rxn = {self.delta_H_rxn:.0f} J/mol_A")

        # ── Feed ──────────────────────────────────────────────────────────────
        feed = self.get_inlet("feed")
        self._log_stream(feed)

        if self.mode == ReactorMode.DESIGN and not 0 < self.X_target < 1.0:
            raise InfeasibleDesignError(
                self.unit_id,
                f"X_target = {self.X_target} must be in (0, 1)."
            )
        if self.mode == ReactorMode.RATING and (
            self.volume_m3 is None or self.volume_m3 <= 0
        ):
            raise InfeasibleDesignError(self.unit_id, "Rating mode requires volume_m3 > 0.")

        F_A0 = (feed.mass_flowrate / self.MW_A) * 1000  # mol/s
        self.log(f"\nF_A0 = {F_A0:.4f} mol/s")

        # ── Solve ─────────────────────────────────────────────────────────────
        if self.thermal_mode == ThermalMode.ISOTHERMAL:
            X, V, T_out = self._solve_isothermal(feed, F_A0)
        else:
            X, V, T_out = self._solve_adiabatic(feed, F_A0)

        # ── Store results ─────────────────────────────────────────────────────
        C_A_out   = self.C_A0 * (1 - X)
        k_out     = self._arrhenius(T_out)
        self._X       = X
        self._V       = V
        self._tau     = V / feed.volumetric_flowrate
        self._T_out   = T_out
        self._C_A_out = C_A_out
        self._k_rxn   = k_out

        # ── Heat duty ─────────────────────────────────────────────────────────
        self._calc_heat_duty(F_A0, X)

        # ── Outlet stream ─────────────────────────────────────────────────────
        self.outlet_streams["outlet"] = feed.copy_with(
            name=f"{feed.name}_out",
            temperature=T_out,
            source_unit=self.unit_id,
        )

        # ── Results log ───────────────────────────────────────────────────────
        self.log_section("Results")
        self.log(f"Conversion X     = {X:.4f}  ({X*100:.2f}%)")
        self.log(f"Volume V         = {V:.4f} m³  ({V*1000:.2f} L)")
        self.log(f"Residence time τ = {self._tau:.2f} s  ({self._tau/60:.2f} min)")
        self.log(f"T_out            = {T_out - 273.15:.2f} °C")
        self.log(f"C_A_out          = {C_A_out:.4f} mol/m³")
        self.log(f"Heat duty Q      = {self._Q_kw:.3f} kW")

        self.is_solved = True

    # =========================================================================
    # Isothermal solve
    # =========================================================================

    def _solve_isothermal(
        self, feed: ProcessStream, F_A0: float
    ) -> tuple[float, float, float]:
        """
        V = F_A0 · ∫₀ˣ dX / (-r_A(X))
        Solved via scipy.integrate.quad.
        Profile generated by evaluating over n_points.
        """
        from scipy.integrate import quad

        self.log_section("Isothermal PFR Mole Balance")

        T = self.T_rxn
        k = self._arrhenius(T)
        self.log(f"T = {T - 273.15:.2f} °C,  k = {k:.4e}")

        def integrand(X):
            C_A = self.C_A0 * (1 - X)
            if C_A <= 0:
                return 1e10
            return 1.0 / (k * C_A ** self.n)

        if self.mode == ReactorMode.DESIGN:
            X = self.X_target
            integral, _ = quad(integrand, 0, X)
            V = F_A0 * integral

            self.log(f"V = F_A0 · ∫₀^{X:.3f} dX/(-r_A)")
            self.log(f"  = {F_A0:.4f} × {integral:.4f}")
            self.log(f"  = {V:.4f} m³")

        else:
            # Rating: find X such that V_needed(X) = V_given
            V = self.volume_m3
            self.log(f"Rating: V = {V:.4f} m³, solving for X...")

            from scipy.optimize import brentq

            def residual(X_try):
                if X_try <= 0 or X_try >= 1:
                    return 1e9
                intg, _ = quad(integrand, 0, X_try)
                return F_A0 * intg - V

            try:
                X = brentq(residual, 1e-8, 1 - 1e-8, xtol=1e-8)
            except ValueError:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"Cannot find X for V = {V:.4f} m³. Check kinetics."
                )
            self.log(f"Converged: X = {X:.6f}")

        # Generate profile
        self._generate_isothermal_profile(F_A0, k, X, feed)

        return X, V, T

    # =========================================================================
    # Adiabatic solve
    # =========================================================================

    def _solve_adiabatic(
        self, feed: ProcessStream, F_A0: float
    ) -> tuple[float, float, float]:
        """
        Coupled ODE system integrated with scipy.integrate.solve_ivp:

            dX/dV = -r_A(X, T) / F_A0
            dT/dV = (-ΔH_rxn · (-r_A)) / (ṁ_total · Cp)

        For design mode: integrate until X = X_target.
        For rating mode: integrate until V = volume_m3.
        """
        self.log_section("Adiabatic PFR — coupled ODE integration")

        rho = feed.density
        Cp  = feed.cp
        m_dot = feed.mass_flowrate

        dT_ad_per_dX = (-self.delta_H_rxn * self.C_A0 * feed.volumetric_flowrate) / (m_dot * Cp)
        self.log(f"dT/dX_max = {dT_ad_per_dX:.4f} K (adiabatic temperature rise per unit X)")

        if abs(dT_ad_per_dX) > 100:
            self.warn(
                f"|dT/dX| = {abs(dT_ad_per_dX):.1f} K — large adiabatic T rise. "
                f"Runaway risk. Consider heat removal."
            )

        def odes(V, y):
            X, T = y
            if X >= 1.0 or T <= 0:
                return [0.0, 0.0]
            k   = self._arrhenius(T)
            C_A = self.C_A0 * (1 - X)
            if C_A <= 0:
                return [0.0, 0.0]
            r_A = k * C_A ** self.n
            dXdV = r_A / F_A0
            dTdV = (-self.delta_H_rxn * r_A) / (m_dot * Cp)
            return [dXdV, dTdV]

        y0  = [0.0, self.T_rxn]
        V0  = 0.0

        if self.mode == ReactorMode.DESIGN:
            # Integrate until X_target reached
            X_stop = self.X_target

            def event_X(V, y): return y[0] - X_stop
            event_X.terminal  = True
            event_X.direction = 1

            # Upper bound: estimate V_max from isothermal at inlet T
            k_in   = self._arrhenius(self.T_rxn)
            r_A_in = k_in * self.C_A0 ** self.n
            V_est  = F_A0 * X_stop / r_A_in * 10   # 10× safety factor

            sol = solve_ivp(odes, [0, V_est], y0,
                            events=event_X, max_step=V_est/500,
                            rtol=1e-6, atol=1e-9, dense_output=True)

            if sol.t_events[0].size == 0:
                raise InfeasibleDesignError(
                    self.unit_id,
                    f"Could not reach X = {X_stop:.3f} in estimated V = {V_est:.4f} m³. "
                    f"Increase V estimate or check kinetics."
                )

            V   = float(sol.t_events[0][0])
            X   = float(sol.y_events[0][0][0])
            T_out = float(sol.y_events[0][0][1])
            self.log(f"Integration converged: X={X:.6f}, T_out={T_out-273.15:.3f}°C, V={V:.4f} m³")

        else:
            V = self.volume_m3
            sol = solve_ivp(odes, [0, V], y0,
                            max_step=V/500, rtol=1e-6, atol=1e-9,
                            dense_output=True)
            X     = float(sol.y[0, -1])
            T_out = float(sol.y[1, -1])
            self.log(f"Integration over V={V:.4f} m³: X={X:.6f}, T_out={T_out-273.15:.3f}°C")

        # Generate profile from dense output
        self._generate_adiabatic_profile(sol, V)

        return X, V, T_out

    # =========================================================================
    # Profile generation
    # =========================================================================

    def _generate_isothermal_profile(
        self, F_A0: float, k: float, X_max: float, feed: ProcessStream
    ) -> None:
        from scipy.integrate import quad

        V_points, X_points, T_points, rA_points = [], [], [], []
        X_vals = np.linspace(0, X_max * 0.9999, self.n_points)

        cumulative_V = 0.0
        prev_X = 0.0
        for Xi in X_vals:
            if Xi == 0:
                V_points.append(0.0)
            else:
                intg, _ = quad(lambda x: 1.0 / max(k * (self.C_A0*(1-x))**self.n, 1e-20),
                               prev_X, Xi)
                cumulative_V += F_A0 * intg
                prev_X = Xi
                V_points.append(cumulative_V)

            C_A  = self.C_A0 * (1 - Xi)
            r_A  = k * max(C_A, 0) ** self.n
            X_points.append(float(Xi))
            T_points.append(float(self.T_rxn - 273.15))
            rA_points.append(float(1.0 / r_A) if r_A > 0 else 1e10)

        self._V_profile  = V_points
        self._X_profile  = X_points
        self._T_profile  = T_points
        self._rA_profile = rA_points

    def _generate_adiabatic_profile(self, sol, V_max: float) -> None:
        V_vals = np.linspace(0, V_max, self.n_points)
        y_vals = sol.sol(V_vals)

        V_prof, X_prof, T_prof, rA_prof = [], [], [], []
        for i, Vi in enumerate(V_vals):
            Xi = float(np.clip(y_vals[0, i], 0, 1))
            Ti = float(y_vals[1, i])
            k  = self._arrhenius(Ti)
            C_A = self.C_A0 * max(1 - Xi, 0)
            r_A = k * C_A ** self.n if C_A > 0 else 1e-20
            V_prof.append(float(Vi))
            X_prof.append(Xi)
            T_prof.append(Ti - 273.15)
            rA_prof.append(1.0 / r_A if r_A > 0 else 1e10)

        self._V_profile  = V_prof
        self._X_profile  = X_prof
        self._T_profile  = T_prof
        self._rA_profile = rA_prof

    # =========================================================================
    # Heat duty
    # =========================================================================

    def _calc_heat_duty(self, F_A0: float, X: float) -> None:
        Q    = F_A0 * X * self.delta_H_rxn
        Q_kw = Q / 1000
        self.log_section("Heat Duty")
        self.log(f"Q = F_A0·X·ΔH = {F_A0:.4f}×{X:.4f}×{self.delta_H_rxn:.0f} = {Q:.2f} W")
        if self.thermal_mode == ThermalMode.ADIABATIC:
            self.log("  Adiabatic: Q_removed = 0, heat stays in fluid")
        self._Q_kw = Q_kw
        u = UtilityStream(
            utility_type="heating_duty" if Q > 0 else "cooling_duty",
            unit_id=self.unit_id,
            duty_kw=abs(Q_kw),
        )
        self.utility_streams.append(u)

    # =========================================================================
    # Arrhenius
    # =========================================================================

    def _arrhenius(self, T: float) -> float:
        if self.Ea == 0:
            return self.k_ref
        return self.k_ref * math.exp(
            -self.Ea / R_GAS * (1.0 / T - 1.0 / self.T_ref)
        )

    # =========================================================================
    # Logging
    # =========================================================================

    def _log_stream(self, stream: ProcessStream) -> None:
        self.log(f"\nFeed stream '{stream.name}':")
        self.log(f"  T   = {stream.temperature_c:.2f} °C")
        self.log(f"  ṁ   = {stream.mass_flowrate:.4f} kg/s")
        self.log(f"  ρ   = {stream.density:.2f} kg/m³")
        self.log(f"  Q_v = {stream.volumetric_flowrate:.5f} m³/s")

    # =========================================================================
    # summary()
    # =========================================================================

    def summary(self) -> dict:
        base = self.base_summary()
        return {
            **base,
            "reactor_type":      "PFR",
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
            "k_rxn":             round(self._k_rxn, 8),
            "heat_duty_kW":      round(self._Q_kw, 4),
            "n_order":           self.n,
            "Ea_J_mol":          self.Ea,
            "delta_H_rxn_J_mol": self.delta_H_rxn,
            "C_A0_mol_m3":       self.C_A0,
            # Profile data for Levenspiel chart
            "profile": {
                "V_m3":          [round(v, 6) for v in self._V_profile],
                "X":             [round(x, 5) for x in self._X_profile],
                "T_C":           [round(t, 3) for t in self._T_profile],
                "inv_rA":        [round(min(r, 1e6), 4) for r in self._rA_profile],
            },
        }
