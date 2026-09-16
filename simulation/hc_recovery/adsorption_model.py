"""
Multi-component Adsorption Separation Engine Module.

Implements equilibrium bed-loading calculations using the Extended (Competitive) 
Langmuir Isotherm framework for recovery of hydrocarbons from nitrogen-rich purge streams.
"""

import numpy as np
from typing import Any
from simulation.core.exceptions import OutOfRangeError
from simulation.hc_recovery import data_loader

# Engineering Operating Envelopes
MAX_VALID_PRESSURE_BAR = 50.0
MIN_VALID_PRESSURE_BAR = 0.01


def extended_langmuir_loading(
    adsorbent: str, 
    feed_moles: dict[str, float], 
    P_bar: float
) -> dict[str, float]:
    """
    Computes the competitive equilibrium loading matrix for all stream components.

    Mathematical Model:
        q_i = (q_m,i * b_i * P_i) / (1 + sum_j (b_j * P_j))
        Where partial pressure P_i = y_i * P_total

    Args:
        adsorbent: The unique name of the target bed material (e.g., 'Zeolite 13X').
        feed_moles: Dictionary of incoming component molar amounts.
        P_bar: Total column operating pressure in bar.

    Returns:
        A dictionary mapping component names to solid phase loading values (mol/kg-adsorbent).
    """
    if not (MIN_VALID_PRESSURE_BAR <= P_bar <= MAX_VALID_PRESSURE_BAR):
        raise OutOfRangeError("Adsorption Total Pressure", P_bar, MIN_VALID_PRESSURE_BAR, MAX_VALID_PRESSURE_BAR, "bar")

    total_moles = sum(feed_moles.values())
    if total_moles <= 0.0:
        raise ValueError("Aggregate feed moles inside adsorption calculation must be positive.")

    components = list(feed_moles.keys())
    y = {comp: moles / total_moles for comp, moles in feed_moles.items()}
    
    # Collect isotherm parameters and calculate individual denominators
    q_m: dict[str, float] = {}
    b: dict[str, float] = {}
    p_partial: dict[str, float] = {}
    
    denominator_sum = 0.0
    
    for comp in components:
        params = data_loader.load_adsorption_parameters(adsorbent, comp)
        q_m[comp] = float(params["q_m"])
        b[comp] = float(params["b"])
        p_partial[comp] = float(y[comp] * P_bar)
        
        denominator_sum += b[comp] * p_partial[comp]

    # Calculate actual solid loadings
    loadings: dict[str, float] = {}
    for comp in components:
        numerator = q_m[comp] * b[comp] * p_partial[comp]
        loadings[comp] = float(numerator / (1.0 + denominator_sum))

    return loadings


def adsorption_performance(
    adsorbent: str, 
    feed_moles: dict[str, float], 
    P_bar: float,
    bed_mass_kg: float
) -> dict[str, Any]:
    """
    Evaluates macro bed separation performance, recovery efficiency, and relative requirements.

    Assumptions:
        1. Isothermal, isobaric equilibrium step behavior.
        2. Mass transfer resistance inside macro-pores is negligible.
        3. Breakthrough limit matches exact equilibrium loading values.

    Args:
        adsorbent: Selected solid bed material.
        feed_moles: Incoming molar composition map.
        P_bar: Operational adsorption pressure in bar.
        bed_mass_kg: Total available solid phase absorbent inventory mass.

    Returns:
        Structured performance dictionary for API routing blocks.
    """
    loadings = extended_langmuir_loading(adsorbent, feed_moles, P_bar)
    
    hc_components = {"propylene", "propane", "c3h6", "c3h8"}
    
    # Calculate absolute component capture capacities in moles
    moles_adsorbed: dict[str, float] = {}
    for comp, loading in loadings.items():
        moles_adsorbed[comp] = float(loading * bed_mass_kg)

    # Recovery evaluation metrics
    total_hc_feed = sum(moles for comp, moles in feed_moles.items() if comp.lower() in hc_components)
    total_hc_adsorbed = sum(moles for comp, moles in moles_adsorbed.items() if comp.lower() in hc_components)
    
    # Bound estimated recovery safely to physical realities (cannot exceed available feed)
    if total_hc_feed > 0.0:
        estimated_recovery_pct = min((total_hc_adsorbed / total_hc_feed) * 100.0, 99.9)
    else:
        estimated_recovery_pct = 0.0

    # Benchmark indicator: Relative Adsorbent Requirement scaling index
    # Defined as kg-adsorbent needed per mole of hydrocarbon trapped
    specific_loading_hc = sum(loading for comp, loading in loadings.items() if comp.lower() in hc_components)
    relative_adsorbent_req = float(1.0 / specific_loading_hc) if specific_loading_hc > 0.0 else 0.0

    return {
        "loadings_mol_kg": loadings,
        "moles_adsorbed": moles_adsorbed,
        "recovery_pct": estimated_recovery_pct,
        "relative_adsorbent_req_kg_mol": relative_adsorbent_req,
        "bed_mass_kg": bed_mass_kg
    }


def loading_vs_pressure_curves(
    adsorbent: str,
    feed_moles: dict[str, float],
    p_min_bar: float = 0.5,
    p_max_bar: float = 25.0,
    n_points: int = 30
) -> list[dict[str, Any]]:
    """
    Generates partial pressure equilibrium sweep maps to construct charting grids.
    """
    if p_min_bar < MIN_VALID_PRESSURE_BAR:
        raise OutOfRangeError("Swept Minimum Pressure", p_min_bar, MIN_VALID_PRESSURE_BAR, p_max_bar, "bar")

    pressure_space = np.linspace(p_min_bar, p_max_bar, n_points)
    curve_results: list[dict[str, Any]] = []

    for P in pressure_space:
        try:
            loadings = extended_langmuir_loading(adsorbent, feed_moles, float(P))
            row: dict[str, Any] = {"pressure_bar": float(P)}
            for comp, val in loadings.items():
                row[f"loading_{comp}"] = float(val)
            curve_results.append(row)
        except OutOfRangeError:
            continue

    return curve_results