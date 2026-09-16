"""
Partial Condensation and Cryogenic Hydrocarbon Recovery Model.

Implements an isothermal flash equilibrium separator for a multi-component gas stream
consisting of hydrocarbons (propylene, propane) and a non-condensable carrier gas (nitrogen)
using the Antoine vapor pressure correlation, Raoult's Law, and the Rachford-Rice equation.
"""

import math
import numpy as np
from typing import Any
from scipy.optimize import brentq
from simulation.core.exceptions import OutOfRangeError, ConvergenceError
from simulation.hc_recovery import data_loader

# Global Thermodynamic Limits
MIN_VALID_TEMP_K = 173.15  # -100 °C engineering limit for Raoult's approximation
NITROGEN_CRIT_TEMP_K = 126.2  # Supercritical boundary for non-condensable logic


def antoine_pressure(component: str, T_K: float) -> float:
    """
    Computes the saturation vapor pressure of a condensable species using Antoine's equation.

    Formula:
        log10(P_sat) = A - [B / (T_K + C)]
        P_sat = 10^(A - [B / (T_K + C)])

    Args:
        component: The lowercase string matching key of the component (e.g., 'propylene').
        T_K: Absolute temperature of the system in Kelvin.

    Returns:
        The saturation vapor pressure (P_sat) in bar.

    Raises:
        OutOfRangeError: If the requested temperature falls outside the structural validity 
                       limits specified in the component's constants parameter database.
    """
    constants = data_loader.load_component_constants(component)
    
    # Extract Antoine parameters with fallback checks for safe deserialization
    antoine_data = constants.get("antoine", {})
    if not antoine_data:
        # Fallback to direct keys if flat structure is used in source data
        a = float(constants["antoine_A"])
        b = float(constants["antoine_B"])
        c = float(constants["antoine_C"])
        t_min = float(constants.get("antoine_T_min", MIN_VALID_TEMP_K))
        t_max = float(constants.get("antoine_T_max", float(constants["tc"])))
    else:
        a = float(antoine_data["A"])
        b = float(antoine_data["B"])
        c = float(antoine_data["C"])
        t_min = float(antoine_data.get("T_min", MIN_VALID_TEMP_K))  # Fixed NameError typo
        t_max = float(antoine_data.get("T_max", float(constants["tc"])))

    if not (t_min <= T_K <= t_max):
        raise OutOfRangeError(
            parameter=f"Temperature bound for {component} Antoine correlation",
            value=T_K,
            valid_min=t_min,
            valid_max=t_max,
            unit="K"
        )

    log10_p_sat = a - (b / (T_K + c))
    return float(math.pow(10.0, log10_p_sat))


def rachford_rice(V: float, z: list[float], K: list[float]) -> float:
    """
    Evaluates the Rachford-Rice objective function residual for a given vapor fraction V.

    Formula:
        F(V) = sum_i [ z_i * (K_i - 1) / (1 + V * (K_i - 1)) ] = 0

    Args:
        V: Evaluated vapor fraction split ratio (moles vapor / total feed moles) [0, 1].
        z: List of component mole fractions in the aggregate feed stream.
        K: List of component liquid-vapor distribution coefficients (K-values).

    Returns:
        The numerical residual scalar float value of the objective equation.
    """
    residual = 0.0
    for zi, Ki in zip(z, K):
        residual += (zi * (Ki - 1.0)) / (1.0 + V * (Ki - 1.0))
    return residual


def flash_calculation(feed_moles: dict[str, float], T_K: float, P_bar: float) -> dict[str, Any]:
    """
    Performs an isothermal vapor-liquid equilibrium (VLE) flash separation calculation.

    Assumptions:
        1. Ideal gas behavior and ideal solution liquid mixture behavior (Raoult's Law).
        2. Nitrogen is treated as an ideal non-condensable species if T_K > 126.2 K.
        3. Total pressure drop across the condenser volume is negligible.

    Args:
        feed_moles: Dictionary mapping component keys to their incoming molar amounts.
        T_K: System operating temperature in Kelvin.
        P_bar: System operating pressure in bar.

    Returns:
        A dictionary containing structured state data maps and a convergence note string.
    """
    if T_K < MIN_VALID_TEMP_K:
        raise OutOfRangeError("Condenser Temperature", T_K, MIN_VALID_TEMP_K, 400.0, "K")
    if P_bar <= 0.0:
        raise OutOfRangeError("Condenser Pressure", P_bar, 0.001, 50.0, "bar")

    components = list(feed_moles.keys())
    total_feed_moles = sum(feed_moles.values())
    
    if total_feed_moles <= 0.0:
        raise ValueError("Aggregate feed moles inside flash calculation must be positive.")

    z = [feed_moles[comp] / total_feed_moles for comp in components]
    
    K = []
    k_dict: dict[str, float] = {}
    
    for comp in components:
        if comp.lower() == "nitrogen" and T_K > NITROGEN_CRIT_TEMP_K:
            ki = 1e6
        else:
            p_sat = antoine_pressure(comp, T_K)
            ki = p_sat / P_bar
        K.append(ki)
        k_dict[comp] = ki

    f_zero = rachford_rice(0.0, z, K)
    f_one = rachford_rice(1.0, z, K)

    if f_zero <= 0.0:
        v_fraction = 0.0
        note = "Subcooled liquid state encountered. Analytical boundary assignment executed."
    elif f_one >= 0.0:
        v_fraction = 1.0
        note = "Superheated vapor state encountered. Analytical boundary assignment executed."
    else:
        try:
            v_fraction = float(brentq(rachford_rice, 0.0, 1.0, args=(z, K), xtol=1e-8, maxiter=100))
            note = "Isothermal VLE algorithm converged successfully using bounded Brent solver."
        except Exception as exc:
            raise ConvergenceError(
                unit_id="CRYOGENIC_CONDENSER",
                iterations=100,
                residual=float(abs(rachford_rice(0.5, z, K)))
            ) from exc

    vapor_moles: dict[str, float] = {}
    liquid_moles: dict[str, float] = {}

    for i, comp in enumerate(components):
        ki = K[i]
        zi = z[i]
        comp_feed_moles = total_feed_moles * zi
        
        if v_fraction == 0.0:
            vapor_moles[comp] = 0.0
            liquid_moles[comp] = comp_feed_moles
        elif v_fraction == 1.0:
            vapor_moles[comp] = comp_feed_moles
            liquid_moles[comp] = 0.0
        else:
            # First-principles mass split to preserve chemical component conservation rules
            v_fraction_comp = (ki * v_fraction) / (1.0 + v_fraction * (ki - 1.0))
            
            vapor_moles[comp] = float(comp_feed_moles * v_fraction_comp)
            liquid_moles[comp] = float(comp_feed_moles * (1.0 - v_fraction_comp))

    return {
        "vapor_moles": vapor_moles,
        "liquid_moles": liquid_moles,
        "vapor_fraction": v_fraction,
        "K_values": k_dict,
        "convergence_note": note
    }


def recovery_curve(
    feed_moles: dict[str, float], 
    P_bar: float, 
    T_min_K: float, 
    T_max_K: float, 
    n_points: int = 30
) -> list[dict[str, float]]:
    """
    Sweeps system temperature over a specified interval to generate a condensation performance sweep.
    """
    if T_min_K < MIN_VALID_TEMP_K:
        raise OutOfRangeError("Swept Minimum Temperature Boundary", T_min_K, MIN_VALID_TEMP_K, T_max_K, "K")
    
    hc_components = {"propylene", "propane", "c3h6", "c3h8"}
    total_hc_feed = sum(moles for comp, moles in feed_moles.items() if comp.lower() in hc_components)

    if total_hc_feed == 0.0:
        total_hc_feed = 1.0

    curve_results: list[dict[str, float]] = []
    temperatures = np.linspace(T_min_K, T_max_K, n_points)

    for T in temperatures:
        try:
            flash_res = flash_calculation(feed_moles=feed_moles, T_K=float(T), P_bar=P_bar)
            liq_moles = flash_res["liquid_moles"]
            
            hc_condensed = sum(moles for comp, moles in liq_moles.items() if comp.lower() in hc_components)
            recovery_pct = (hc_condensed / total_hc_feed) * 100.0

            curve_results.append({
                "T_K": float(T),
                "T_C": float(T - 273.15),
                "recovery_pct": float(recovery_pct),
                "vapor_fraction": float(flash_res["vapor_fraction"])
            })
        except (OutOfRangeError, ConvergenceError):
            continue

    return curve_results