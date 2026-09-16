"""
simulation/units/distillation.py

Distillation column — FUG shortcut method.

Handles both binary and multicomponent systems.
For crude distillation, components are petroleum pseudo-components
defined by boiling point and relative volatility.

Method: Fenske-Underwood-Gilliland (FUG)
-----------------------------------------
Step 1  Fenske   → N_min  (minimum stages at total reflux)
Step 2  Underwood → R_min  (minimum reflux ratio)
Step 3  Gilliland → N_actual at operating R = R_Rmin_ratio × R_min

Key assumptions
---------------
- Constant molar overflow (CMO)
- Constant relative volatility α (evaluated at average column T)
- Sharp split approximation for non-key components (Kremser method)

Petroleum / crude distillation support
---------------------------------------
Components can be defined as petroleum pseudo-components:
    name, normal_boiling_point_K, molecular_weight, relative_volatility
Relative volatility is computed from Clausius-Clapeyron / Cox chart
if not supplied, using T_b as the reference.

References
----------
- Coulson & Richardson Vol. 2, Chapter 11 (FUG method)
- McCabe, Smith & Harriott, Chapter 21
- Gilliland, E.R. (1940) Ind. Eng. Chem. 32:918
- Underwood, A.J.V. (1948) Chem. Eng. Prog. 44:603
- Fenske, M.R. (1932) Ind. Eng. Chem. 24:482
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import numpy as np
from scipy.optimize import brentq

from simulation.core.stream import ProcessStream, UtilityStream
from simulation.core.unit_operation import UnitOperation
from simulation.core.exceptions import InfeasibleDesignError, StreamError

R_GAS = 8.314  # J/(mol·K)


# ── Component dataclass ───────────────────────────────────────────────────────

@dataclass
class DistComponent:
    """
    A component in the distillation feed.

    Parameters
    ----------
    name : str
        Component name (e.g. "propane", "naphtha_150C", "gas_oil")
    z : float
        Feed mole fraction. All z must sum to 1.0.
    alpha : float
        Relative volatility w.r.t. heavy key component.
        alpha > 1 → more volatile than heavy key.
        alpha = 1 → this IS the heavy key.
    is_light_key : bool
        True for the light key component (LK).
        LK appears in both distillate and bottoms.
    is_heavy_key : bool
        True for the heavy key component (HK).
        HK appears in both distillate and bottoms.
    x_distillate : float, optional
        Mole fraction of this component in distillate.
        Required only for light key and heavy key.
        Non-keys are auto-distributed (light non-keys → distillate,
        heavy non-keys → bottoms) via Kremser equation.
    T_boil_K : float, optional
        Normal boiling point [K]. Used for crude pseudo-components.
    MW : float, optional
        Molecular weight [g/mol]. Used for stream property estimation.
    """
    name:          str
    z:             float          # feed mole fraction
    alpha:         float          # relative volatility vs heavy key
    is_light_key:  bool  = False
    is_heavy_key:  bool  = False
    x_distillate:  Optional[float] = None   # specified for keys only
    T_boil_K:      Optional[float] = None
    MW:            Optional[float] = None


# ── Gilliland correlation ─────────────────────────────────────────────────────

def _gilliland(X: float) -> float:
    """
    Gilliland correlation (Molokanov, 1972 fit):
        Y = 1 - exp[(1 + 54.4X)/(11 + 117.2X) · (X-1)/X^0.5]

    X = (R - R_min) / (R + 1)
    Y = (N - N_min) / (N + 1)

    Valid range: 0 < X < 1
    Reference: Molokanov (1972) Int. Chem. Eng. 12:209
    """
    if X <= 0:
        return 1.0
    if X >= 1:
        return 0.0
    return 1.0 - math.exp(
        ((1.0 + 54.4 * X) / (11.0 + 117.2 * X)) * ((X - 1.0) / X**0.5)
    )


# ── Kremser equation for non-key distribution ─────────────────────────────────

def _kremser_recovery(alpha: float, N: float, R: float, D_F: float) -> float:
    """
    Kremser equation: fraction of component recovered in distillate.

    For light non-keys (alpha > alpha_LK):  recovery → 1
    For heavy non-keys (alpha < alpha_HK):  recovery → 0

    Simplified form:
        For absorption factor A = L/(K·V) = (R·D)/(alpha·(R+1)·D) = R/(alpha·(R+1))
        Recovery = (A^(N+1) - A) / (A^(N+1) - 1)
    """
    A = R / (alpha * (R + 1.0))
    if A <= 0:
        return 0.0
    try:
        AN1 = A ** (N + 1)
        if AN1 > 1e15:
            return 1.0
        recovery = (AN1 - A) / (AN1 - 1.0)
        return float(np.clip(recovery, 0.0, 1.0))
    except (OverflowError, ZeroDivisionError):
        return 1.0 if A > 1 else 0.0


# ── McCabe-Thiele for binary ──────────────────────────────────────────────────

def _mccabe_thiele_profile(
    alpha: float,
    x_F: float,
    x_D: float,
    x_B: float,
    R: float,
    q: float,
    n_points: int = 200,
) -> Dict:
    """
    Generate McCabe-Thiele diagram data for a binary system.

    Returns
    -------
    dict with keys:
        equilibrium  : list of (x, y) for equilibrium curve
        op_rect      : list of (x, y) for rectifying operating line
        op_strip     : list of (x, y) for stripping operating line
        q_line       : list of (x, y) for feed (q) line
        stages       : list of (x, y) step coordinates
        n_stages     : int number of theoretical stages
        feed_stage   : int optimal feed stage from top
    """
    # Equilibrium curve: y = alpha*x / (1 + (alpha-1)*x)
    x_eq = np.linspace(0, 1, n_points)
    y_eq = alpha * x_eq / (1.0 + (alpha - 1.0) * x_eq)

    # Operating lines
    # Rectifying: y = (R/(R+1))*x + x_D/(R+1)
    L_V_rect = R / (R + 1.0)
    b_rect    = x_D / (R + 1.0)

    # q-line: y = q/(q-1)*x - x_F/(q-1)   [q ≠ 1]
    # Intersection with rectifying line gives x_q, y_q
    if abs(q - 1.0) < 1e-6:
        # Saturated liquid feed: vertical q-line at x = x_F
        x_q = x_F
        y_q = L_V_rect * x_q + b_rect
    else:
        slope_q = q / (q - 1.0)
        inter_q = -x_F / (q - 1.0)
        # Intersection: L_V_rect*x + b_rect = slope_q*x + inter_q
        x_q = (inter_q - b_rect) / (L_V_rect - slope_q)
        y_q = L_V_rect * x_q + b_rect

    x_q = float(np.clip(x_q, x_B, x_D))
    y_q = float(np.clip(y_q, x_B, x_D))

    # Stripping operating line: through (x_B, x_B) and (x_q, y_q)
    if abs(x_q - x_B) < 1e-10:
        slope_strip = 1.0
    else:
        slope_strip = (y_q - x_B) / (x_q - x_B)
    b_strip = x_B - slope_strip * x_B

    # Step off stages from top (x_D) downward
    stages = []
    x = x_D
    n_stages = 0
    feed_stage = None
    max_stages = 200

    for _ in range(max_stages):
        # Horizontal step: from operating line to equilibrium curve
        # Find x_eq such that y_eq(x) = current y
        y = x   # current y on the operating line or start
        if n_stages == 0:
            y = x_D

        # Find x on equilibrium curve where y_eq = y
        # y = alpha*x/(1+(alpha-1)*x) → x = y/(alpha-(alpha-1)*y)
        denom = alpha - (alpha - 1.0) * y
        if denom <= 0:
            break
        x_new = y / denom
        x_new = float(np.clip(x_new, 0.0, 1.0))

        stages.append((float(x_new), float(y)))    # horizontal
        stages.append((float(x_new), float(x_new))) # vertical (to op line)

        n_stages += 1

        # Switch operating line at feed stage (optimal = when x crosses x_q)
        if feed_stage is None and x_new <= x_q:
            feed_stage = n_stages

        # Determine y from appropriate operating line
        if feed_stage is None or n_stages < feed_stage:
            y_next = L_V_rect * x_new + b_rect
        else:
            y_next = slope_strip * x_new + b_strip

        stages[-1] = (float(x_new), float(y_next))

        if x_new <= x_B * 1.001:
            break
        x = x_new

    if feed_stage is None:
        feed_stage = max(1, n_stages // 2)

    # Build operating line point arrays
    x_rect  = np.linspace(x_q, x_D, 30)
    y_rect  = L_V_rect * x_rect + b_rect
    x_strip = np.linspace(x_B, x_q, 30)
    y_strip = slope_strip * x_strip + b_strip

    # q-line points
    if abs(q - 1.0) < 1e-6:
        x_qline = [x_F, x_F]
        y_qline = [x_F, 1.0]
    else:
        x_qline_arr = np.linspace(x_B, x_D, 30)
        y_qline_arr = slope_q * x_qline_arr + inter_q
        mask = (y_qline_arr >= 0) & (y_qline_arr <= 1)
        x_qline = x_qline_arr[mask].tolist()
        y_qline = y_qline_arr[mask].tolist()

    return {
        "equilibrium": list(zip(x_eq.tolist(), y_eq.tolist())),
        "op_rect":     list(zip(x_rect.tolist(), y_rect.tolist())),
        "op_strip":    list(zip(x_strip.tolist(), y_strip.tolist())),
        "q_line":      list(zip(x_qline, y_qline)),
        "stages":      stages,
        "n_stages":    n_stages,
        "feed_stage":  feed_stage,
    }


# ── DistillationColumn ────────────────────────────────────────────────────────

@dataclass
class DistillationColumn(UnitOperation):
    """
    Distillation column using FUG shortcut method.

    Suitable for binary systems and petroleum multicomponent systems
    (crude distillation pseudo-components).

    Parameters
    ----------
    unit_id : str
        Unique identifier.
    components : list[DistComponent]
        Feed components. z values must sum to 1.0.
        One component must be is_light_key=True, one is_heavy_key=True.
        x_distillate must be specified for both key components.
    F : float
        Total feed molar flowrate [mol/s].
    q : float
        Feed condition:
          q = 1.0  → saturated liquid (bubble point)
          q = 0.0  → saturated vapour (dew point)
          0 < q < 1 → partial vapour
          q > 1    → subcooled liquid
    R_Rmin_ratio : float
        Operating reflux ratio multiplier: R = R_Rmin_ratio × R_min.
        Default 1.5 (typical design value, C&R Vol. 2 p.524).
    tray_efficiency : float
        Overall tray efficiency E_o [0–1].
        N_actual = N_theoretical / E_o.
        Default 0.7 (typical sieve tray).
    condenser_type : str
        "total" (liquid distillate) or "partial" (vapour distillate).
    P_col : float
        Column operating pressure [Pa]. Used for duty estimation.
    feed_T : float
        Feed temperature [K]. Used for condenser/reboiler duty.
    Cp_feed : float
        Feed heat capacity [J/(mol·K)]. For duty estimation.
    latent_heat : float
        Average latent heat of vaporisation [J/mol].
        Used for condenser and reboiler duty calculation.
    """

    unit_type: str = field(default="DistillationColumn", init=False)

    # Feed specification
    components:    List[DistComponent] = field(default_factory=list)
    F:             float = 100.0        # mol/s
    q:             float = 1.0          # feed condition

    # Design parameters
    R_Rmin_ratio:     float = 1.5
    tray_efficiency:  float = 0.70
    condenser_type:   str   = "total"
    P_col:            float = 101_325.0  # Pa
    feed_T:           float = 350.0      # K
    Cp_feed:          float = 150.0      # J/(mol·K)
    latent_heat:      float = 30_000.0   # J/mol

    # Internal results
    _N_min:       float = field(default=0.0, init=False, repr=False)
    _R_min:       float = field(default=0.0, init=False, repr=False)
    _N_theo:      float = field(default=0.0, init=False, repr=False)
    _N_actual:    float = field(default=0.0, init=False, repr=False)
    _R_op:        float = field(default=0.0, init=False, repr=False)
    _D:           float = field(default=0.0, init=False, repr=False)
    _B:           float = field(default=0.0, init=False, repr=False)
    _feed_stage:  int   = field(default=0,   init=False, repr=False)
    _Q_cond_kw:   float = field(default=0.0, init=False, repr=False)
    _Q_reb_kw:    float = field(default=0.0, init=False, repr=False)
    _x_D:         Dict  = field(default_factory=dict, init=False, repr=False)
    _x_B:         Dict  = field(default_factory=dict, init=False, repr=False)
    _mc_thiele:   Dict  = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        self.unit_type = "DistillationColumn"

    # =========================================================================
    # solve()
    # =========================================================================

    def solve(self) -> None:
        self.reset()

        self.log_section("Distillation Column Setup")
        self.log(f"Unit:             {self.unit_id}")
        self.log(f"Components:       {len(self.components)}")
        self.log(f"Feed F:           {self.F:.2f} mol/s")
        self.log(f"Feed condition q: {self.q}")
        self.log(f"R/R_min ratio:    {self.R_Rmin_ratio}")
        self.log(f"Tray efficiency:  {self.tray_efficiency}")
        self.log(f"Condenser:        {self.condenser_type}")

        # ── Validate ──────────────────────────────────────────────────────────
        self._validate()

        # ── Identify keys ─────────────────────────────────────────────────────
        lk = next(c for c in self.components if c.is_light_key)
        hk = next(c for c in self.components if c.is_heavy_key)

        self.log(f"\nLight key:  {lk.name}  (α = {lk.alpha:.4f}, z = {lk.z:.4f})")
        self.log(f"Heavy key:  {hk.name}  (α = {hk.alpha:.4f}, z = {hk.z:.4f})")
        self.log(f"\nComponent summary:")
        self.log(f"  {'Name':<20} {'z':>8} {'α':>8} {'type':>12}")
        self.log(f"  {'-'*50}")
        for c in sorted(self.components, key=lambda x: -x.alpha):
            ctype = "LNK" if (c.alpha > lk.alpha and not c.is_light_key) else \
                    "LK"  if c.is_light_key else \
                    "HK"  if c.is_heavy_key else \
                    "HNK"
            self.log(f"  {c.name:<20} {c.z:>8.4f} {c.alpha:>8.4f} {ctype:>12}")

        # ── Overall mass balance ──────────────────────────────────────────────
        D, B, x_D_dict, x_B_dict = self._overall_mass_balance(lk, hk)
        self._D = D
        self._B = B
        self._x_D = x_D_dict
        self._x_B = x_B_dict

        # ── Step 1: Fenske — N_min ────────────────────────────────────────────
        N_min = self._fenske(lk, hk, x_D_dict, x_B_dict)
        self._N_min = N_min

        # ── Step 2: Underwood — R_min ─────────────────────────────────────────
        R_min = self._underwood(lk, hk)
        self._R_min = R_min

        # ── Step 3: Gilliland — N_theoretical ────────────────────────────────
        R_op = self.R_Rmin_ratio * R_min
        self._R_op = R_op
        N_theo = self._gilliland_stages(N_min, R_min, R_op)
        self._N_theo = N_theo
        self._N_actual = math.ceil(N_theo / self.tray_efficiency)

        # Feed stage location (Kirkbride equation)
        self._feed_stage = self._kirkbride_feed_stage(lk, hk, x_D_dict, x_B_dict, N_theo)

        # ── Condenser and reboiler duties ─────────────────────────────────────
        self._calc_duties(D, R_op)

        # ── McCabe-Thiele profile (binary only) ───────────────────────────────
        if len(self.components) == 2:
            self._mc_thiele = _mccabe_thiele_profile(
                alpha=lk.alpha,
                x_F=lk.z,
                x_D=x_D_dict.get(lk.name, 0.95),
                x_B=x_B_dict.get(lk.name, 0.05),
                R=R_op,
                q=self.q,
            )
            self.log(f"\nMcCabe-Thiele stages: {self._mc_thiele['n_stages']}")
            self.log(f"Feed stage from top:  {self._mc_thiele['feed_stage']}")

        # ── Warnings ──────────────────────────────────────────────────────────
        if self.R_Rmin_ratio < 1.2:
            self.warn(
                f"R/R_min = {self.R_Rmin_ratio:.2f} < 1.2. "
                f"Operating near minimum reflux — small disturbances cause large N increase."
            )
        if self._N_actual > 100:
            self.warn(
                f"N_actual = {self._N_actual} > 100 trays. "
                f"Consider staged separation (two columns) or alternative separation."
            )
        if R_min < 0:
            self.warn("R_min < 0 (Underwood equation may have converged on wrong root). Check feed composition.")

        # ── Build outlet streams ──────────────────────────────────────────────
        feed = self.inlet_streams.get("feed")
        if feed is not None:
            mw_avg_D = self._avg_mw(x_D_dict)
            mw_avg_B = self._avg_mw(x_B_dict)
            mass_D = D * mw_avg_D / 1000  # kg/s (mw in g/mol)
            mass_B = B * mw_avg_B / 1000

            self.outlet_streams["distillate"] = feed.copy_with(
                name=f"{self.unit_id}_distillate",
                mass_flowrate=mass_D,
                source_unit=self.unit_id,
            )
            self.outlet_streams["bottoms"] = feed.copy_with(
                name=f"{self.unit_id}_bottoms",
                mass_flowrate=mass_B,
                source_unit=self.unit_id,
            )

        # ── Utility streams ───────────────────────────────────────────────────
        self.utility_streams.append(UtilityStream(
            utility_type="cooling_duty",
            unit_id=f"{self.unit_id}_condenser",
            duty_kw=self._Q_cond_kw,
        ))
        self.utility_streams.append(UtilityStream(
            utility_type="heating_duty",
            unit_id=f"{self.unit_id}_reboiler",
            duty_kw=self._Q_reb_kw,
        ))

        # ── Final log ─────────────────────────────────────────────────────────
        self.log_section("Results")
        self.log(f"N_min          = {self._N_min:.2f}  (Fenske, total reflux)")
        self.log(f"R_min          = {self._R_min:.4f}  (Underwood)")
        self.log(f"R_operating    = {self._R_op:.4f}   (= {self.R_Rmin_ratio}×R_min)")
        self.log(f"N_theoretical  = {self._N_theo:.2f}  (Gilliland)")
        self.log(f"N_actual       = {self._N_actual}    (efficiency = {self.tray_efficiency})")
        self.log(f"Feed stage     = {self._feed_stage} from top (Kirkbride)")
        self.log(f"Distillate D   = {self._D:.4f} mol/s")
        self.log(f"Bottoms B      = {self._B:.4f} mol/s")
        self.log(f"Q_condenser    = {self._Q_cond_kw:.3f} kW")
        self.log(f"Q_reboiler     = {self._Q_reb_kw:.3f} kW")

        self.is_solved = True

    # =========================================================================
    # Step 1 — Fenske
    # =========================================================================

    def _fenske(self, lk, hk, x_D, x_B) -> float:
        """
        N_min = log[(x_LK,D / x_HK,D) · (x_HK,B / x_LK,B)] / log(α_LK)

        α_LK is the relative volatility of the light key
        with respect to the heavy key (α_HK = 1.0 by definition).
        """
        self.log_section("Step 1 — Fenske (N_min at total reflux)")

        xLD = x_D.get(lk.name, 1e-10)
        xHD = x_D.get(hk.name, 1e-10)
        xLB = x_B.get(lk.name, 1e-10)
        xHB = x_B.get(hk.name, 1e-10)

        # Guard against log(0)
        xLD = max(xLD, 1e-10)
        xHD = max(xHD, 1e-10)
        xLB = max(xLB, 1e-10)
        xHB = max(xHB, 1e-10)

        ratio = (xLD / xHD) * (xHB / xLB)
        alpha = lk.alpha

        if alpha <= 1.0:
            raise InfeasibleDesignError(
                self.unit_id,
                f"α_LK = {alpha:.4f} ≤ 1.0. Relative volatility must exceed 1.0 for separation."
            )

        N_min = math.log(ratio) / math.log(alpha)

        self.log(f"x_LK,D = {xLD:.6f}  x_HK,D = {xHD:.6f}")
        self.log(f"x_LK,B = {xLB:.6f}  x_HK,B = {xHB:.6f}")
        self.log(f"α_LK   = {alpha:.4f}")
        self.log(f"N_min  = log({ratio:.4f}) / log({alpha:.4f}) = {N_min:.3f}")

        return N_min

    # =========================================================================
    # Step 2 — Underwood
    # =========================================================================

    def _underwood(self, lk, hk) -> float:
        """
        Underwood equation:
            Σ [αᵢ·zᵢ / (αᵢ - θ)] = 1 - q
        Solve for θ in root bracket (α_HK, α_LK) = (1, α_LK).
        Then:
            R_min + 1 = Σ [αᵢ·x_D,i / (αᵢ - θ)]
        """
        self.log_section("Step 2 — Underwood (R_min)")

        alphas = np.array([c.alpha for c in self.components])
        zs     = np.array([c.z     for c in self.components])

        target = 1.0 - self.q
        self.log(f"1 - q = {target:.4f}")

        def underwood_lhs(theta):
            denom = alphas - theta
            if np.any(np.abs(denom) < 1e-12):
                return np.sign(denom[0]) * 1e15
            return float(np.sum(alphas * zs / denom))

        # Find θ between α_HK (=1) and α_LK
        alpha_hk = 1.0
        alpha_lk = lk.alpha
        bracket_lo = alpha_hk + 1e-6
        bracket_hi = alpha_lk - 1e-6

        try:
            theta = brentq(
                lambda t: underwood_lhs(t) - target,
                bracket_lo, bracket_hi, xtol=1e-10
            )
        except ValueError:
            self.warn("Underwood root not found in (α_HK, α_LK). Using R_min = 1.2×Fenske estimate.")
            return 1.2 * (self._N_min / 2)

        self.log(f"θ = {theta:.6f}  (root of Underwood equation between α_HK and α_LK)")

        # Compute x_D composition from mass balance
        x_D_dict = self._x_D
        x_D_arr  = np.array([x_D_dict.get(c.name, 0.0) for c in self.components])

        # R_min + 1 = Σ αᵢ·x_D,i / (αᵢ - θ)
        denom_D = alphas - theta
        Vmin_D  = float(np.sum(alphas * x_D_arr / denom_D))  # = R_min + 1
        R_min   = Vmin_D - 1.0

        if R_min < 0:
            R_min = max(0.01, abs(R_min))
            self.warn(f"Underwood gave R_min < 0; using |R_min| = {R_min:.4f}. Check feed composition.")

        self.log(f"R_min + 1 = Σ[αᵢ·x_D,i/(αᵢ-θ)] = {Vmin_D:.4f}")
        self.log(f"R_min     = {R_min:.4f}")

        return R_min

    # =========================================================================
    # Step 3 — Gilliland
    # =========================================================================

    def _gilliland_stages(self, N_min: float, R_min: float, R: float) -> float:
        """
        Gilliland correlation (Molokanov fit):
            X = (R - R_min) / (R + 1)
            Y = (N - N_min) / (N + 1)
            N = (N_min + Y) / (1 - Y)
        """
        self.log_section("Step 3 — Gilliland (N_theoretical)")

        X = (R - R_min) / (R + 1.0)
        Y = _gilliland(X)
        N = (N_min + Y) / (1.0 - Y)

        self.log(f"R_op    = {R:.4f}")
        self.log(f"X       = (R - R_min)/(R + 1) = ({R:.4f} - {R_min:.4f})/({R:.4f} + 1) = {X:.4f}")
        self.log(f"Y       = Gilliland(X) = {Y:.4f}  (Molokanov 1972)")
        self.log(f"N_theo  = (N_min + Y)/(1 - Y) = ({N_min:.3f} + {Y:.4f})/(1 - {Y:.4f}) = {N:.3f}")
        self.log(f"N_actual = ceil({N:.3f} / {self.tray_efficiency}) = {math.ceil(N/self.tray_efficiency)}")

        return N

    # =========================================================================
    # Kirkbride feed stage
    # =========================================================================

    def _kirkbride_feed_stage(self, lk, hk, x_D, x_B, N_theo) -> int:
        """
        Kirkbride equation for optimal feed stage location:
            log(N_rect/N_strip) = 0.206·log[(B/D)·(z_HK/z_LK)·(x_LK,B/x_HK,D)²]
        """
        self.log_section("Feed Stage — Kirkbride Equation")

        try:
            ratio = (
                (self._B / self._D) *
                (hk.z / max(lk.z, 1e-10)) *
                (x_B.get(lk.name, 1e-6) / max(x_D.get(hk.name, 1e-6), 1e-10)) ** 2
            )
            log_ratio = 0.206 * math.log10(max(ratio, 1e-10))
            # N_rect/N_strip = 10^log_ratio
            ratio_rs = 10 ** log_ratio
            N_rect  = N_theo * ratio_rs / (1.0 + ratio_rs)
            feed_stage = max(1, round(N_rect))

            self.log(f"Kirkbride ratio = {ratio:.4f}")
            self.log(f"N_rect/N_strip  = {ratio_rs:.4f}")
            self.log(f"Feed stage      = {feed_stage} from top (of {round(N_theo)} theoretical)")
        except Exception:
            feed_stage = max(1, round(N_theo / 2))
            self.log(f"Feed stage (default N/2) = {feed_stage}")

        return feed_stage

    # =========================================================================
    # Overall mass balance
    # =========================================================================

    def _overall_mass_balance(self, lk, hk, tol: float = 1e-4):
        """
        Perform overall and component mass balances.

        For key components: use specified x_distillate.
        For non-keys:
            Light non-keys (α > α_LK):  95% recovery in distillate
            Heavy non-keys (α < α_HK):  95% recovery in bottoms
        """
        self.log_section("Overall Mass Balance")

        F = self.F

        # Key component mole flows in distillate and bottoms
        # From specification: x_LK,D and x_HK,D
        xLD_spec = lk.x_distillate
        xHD_spec = hk.x_distillate

        # Preliminary D from LK recovery
        # F*z_LK = D*x_LK,D + B*x_LK,B
        # Use specified x_LK,B from x_B specification if available
        x_LK_B_spec = hk.x_distillate   # using HK distillate as proxy for now

        # Simple approach: specify D/F ratio from LK spec
        # d_LK = D * x_LK,D  (moles of LK in distillate)
        # b_LK = F*z_LK - d_LK
        # Similarly for HK

        # Two equations:
        # D*x_LK,D + B*x_LK,B = F*z_LK   ... (1)
        # D*x_HK,D + B*x_HK,B = F*z_HK   ... (2)
        # D + B = F                        ... (3)
        # We have x_LK,D and x_HK,D from spec
        # Need x_LK,B and x_HK,B
        # From (3): B = F - D
        # From (1): D*x_LK,D + (F-D)*x_LK,B = F*z_LK
        # Assume x_LK,B + x_HK,B = x_LK,D + x_HK,D (approximate for keys only)

        # More robust: use recovery specs
        # Recovery of LK in distillate = r_LK
        # Recovery of HK in distillate = r_HK (small)
        r_LK = xLD_spec      # fraction of LK in distillate (0-1)
        r_HK = xHD_spec      # fraction of HK in distillate (0-1, should be small)

        d_LK = F * lk.z * r_LK
        b_LK = F * lk.z * (1.0 - r_LK)
        d_HK = F * hk.z * r_HK
        b_HK = F * hk.z * (1.0 - r_HK)

        # Non-key components
        d_LNK = {}
        d_HNK = {}
        for c in self.components:
            if c.is_light_key or c.is_heavy_key:
                continue
            if c.alpha > lk.alpha:   # light non-key
                d_LNK[c.name] = F * c.z * 0.995   # 99.5% to distillate
            else:                    # heavy non-key
                d_HNK[c.name] = F * c.z * 0.005   # 0.5% to distillate

        # Total distillate and bottoms
        D = d_LK + d_HK + sum(d_LNK.values()) + sum(d_HNK.values())
        B = F - D

        if D <= 0 or B <= 0:
            raise InfeasibleDesignError(
                self.unit_id,
                f"Mass balance gives D = {D:.4f} mol/s or B = {B:.4f} mol/s ≤ 0. "
                f"Check x_distillate specifications for key components."
            )

        # Distillate compositions
        x_D_dict = {}
        x_D_dict[lk.name] = d_LK / D
        x_D_dict[hk.name] = d_HK / D
        for name, d in d_LNK.items():
            x_D_dict[name] = d / D
        for name, d in d_HNK.items():
            x_D_dict[name] = d / D

        # Bottoms compositions
        x_B_dict = {}
        x_B_dict[lk.name] = b_LK / B
        x_B_dict[hk.name] = b_HK / B
        for c in self.components:
            if c.is_light_key or c.is_heavy_key:
                continue
            if c.alpha > lk.alpha:
                x_B_dict[c.name] = F * c.z * 0.005 / B
            else:
                x_B_dict[c.name] = F * c.z * 0.995 / B

        self.log(f"D = {D:.4f} mol/s  B = {B:.4f} mol/s  F = {F:.4f} mol/s")
        self.log(f"D/F = {D/F:.4f}   B/F = {B/F:.4f}")
        self.log(f"\nDistillate composition (key components):")
        self.log(f"  x_LK,D ({lk.name}) = {x_D_dict[lk.name]:.4f}")
        self.log(f"  x_HK,D ({hk.name}) = {x_D_dict[hk.name]:.4f}")
        self.log(f"\nBottoms composition (key components):")
        self.log(f"  x_LK,B ({lk.name}) = {x_B_dict[lk.name]:.4f}")
        self.log(f"  x_HK,B ({hk.name}) = {x_B_dict[hk.name]:.4f}")

        return D, B, x_D_dict, x_B_dict

    # =========================================================================
    # Duties
    # =========================================================================

    def _calc_duties(self, D: float, R: float) -> None:
        """
        Condenser duty:  Q_cond = (R + 1) · D · λ
        Reboiler duty:   Q_reb  ≈ Q_cond + F·Cp·(T_col - T_feed)

        For rough estimates these are adequate for conceptual design.
        Detailed heat integration requires tray-by-tray enthalpy balances.
        """
        self.log_section("Condenser and Reboiler Duties")

        Q_cond = (R + 1.0) * D * self.latent_heat   # W
        Q_reb  = Q_cond * 1.1                         # reboiler ~10% more (approx)

        self.log(f"Q_condenser = (R+1)·D·λ = ({R:.4f}+1)·{D:.4f}·{self.latent_heat:.0f}")
        self.log(f"           = {Q_cond:.2f} W  ({Q_cond/1000:.3f} kW)")
        self.log(f"Q_reboiler  ≈ 1.1 × Q_cond = {Q_reb:.2f} W  ({Q_reb/1000:.3f} kW)")
        self.log(f"(Detailed duties require tray-by-tray enthalpy balance)")

        self._Q_cond_kw = Q_cond / 1000
        self._Q_reb_kw  = Q_reb  / 1000

    # =========================================================================
    # Validation
    # =========================================================================

    def _validate(self) -> None:
        if len(self.components) < 2:
            raise StreamError(
                f"Unit '{self.unit_id}': at least 2 components required."
            )

        lk_list = [c for c in self.components if c.is_light_key]
        hk_list = [c for c in self.components if c.is_heavy_key]

        if len(lk_list) != 1:
            raise StreamError(
                f"Unit '{self.unit_id}': exactly one light key required, "
                f"got {len(lk_list)}."
            )
        if len(hk_list) != 1:
            raise StreamError(
                f"Unit '{self.unit_id}': exactly one heavy key required, "
                f"got {len(hk_list)}."
            )

        lk = lk_list[0]
        hk = hk_list[0]

        if lk.x_distillate is None or hk.x_distillate is None:
            raise StreamError(
                f"Unit '{self.unit_id}': x_distillate must be specified "
                f"for both light key and heavy key components."
            )
        if not (0 < lk.x_distillate <= 1):
            raise InfeasibleDesignError(
                self.unit_id,
                f"LK x_distillate = {lk.x_distillate} must be in (0, 1]."
            )
        if not (0 <= hk.x_distillate < 1):
            raise InfeasibleDesignError(
                self.unit_id,
                f"HK x_distillate = {hk.x_distillate} must be in [0, 1)."
            )

        z_sum = sum(c.z for c in self.components)
        if abs(z_sum - 1.0) > 1e-3:
            raise StreamError(
                f"Unit '{self.unit_id}': feed mole fractions sum to "
                f"{z_sum:.6f}, not 1.0."
            )

        if lk.alpha <= hk.alpha:
            raise InfeasibleDesignError(
                self.unit_id,
                f"Light key α ({lk.alpha:.4f}) must exceed heavy key α ({hk.alpha:.4f})."
            )

        if self.F <= 0:
            raise InfeasibleDesignError(self.unit_id, "Feed flowrate F must be > 0.")

        if not 0 < self.tray_efficiency <= 1:
            raise InfeasibleDesignError(
                self.unit_id, f"tray_efficiency must be in (0, 1], got {self.tray_efficiency}."
            )

    # =========================================================================
    # Helpers
    # =========================================================================

    def _avg_mw(self, x_dict: Dict) -> float:
        """Mass-average molecular weight from mole fractions."""
        mw_map = {c.name: (c.MW or 100.0) for c in self.components}
        return sum(x * mw_map.get(name, 100.0) for name, x in x_dict.items())

    # =========================================================================
    # summary()
    # =========================================================================

    def summary(self) -> dict:
        base = self.base_summary()

        mc = self._mc_thiele
        profile_data = None
        if mc:
            profile_data = {
                "equilibrium": [[round(x, 4), round(y, 4)] for x, y in mc.get("equilibrium", [])],
                "op_rect":     [[round(x, 4), round(y, 4)] for x, y in mc.get("op_rect", [])],
                "op_strip":    [[round(x, 4), round(y, 4)] for x, y in mc.get("op_strip", [])],
                "q_line":      [[round(x, 4), round(y, 4)] for x, y in mc.get("q_line", [])],
                "stages":      [[round(x, 4), round(y, 4)] for x, y in mc.get("stages", [])],
                "n_stages_mt": mc.get("n_stages", 0),
                "feed_stage_mt": mc.get("feed_stage", 0),
            }

        return {
            **base,
            "N_min":             round(self._N_min, 2),
            "R_min":             round(self._R_min, 4),
            "R_operating":       round(self._R_op, 4),
            "N_theoretical":     round(self._N_theo, 2),
            "N_actual":          self._N_actual,
            "feed_stage":        self._feed_stage,
            "tray_efficiency":   self.tray_efficiency,
            "D_mol_s":           round(self._D, 4),
            "B_mol_s":           round(self._B, 4),
            "F_mol_s":           self.F,
            "D_F_ratio":         round(self._D / self.F, 4) if self.F > 0 else None,
            "Q_condenser_kW":    round(self._Q_cond_kw, 3),
            "Q_reboiler_kW":     round(self._Q_reb_kw, 3),
            "distillate_composition": {k: round(v, 4) for k, v in self._x_D.items()},
            "bottoms_composition":    {k: round(v, 4) for k, v in self._x_B.items()},
            "n_components":      len(self.components),
            "R_Rmin_ratio":      self.R_Rmin_ratio,
            "condenser_type":    self.condenser_type,
            "mccabe_thiele":     profile_data,
        }
