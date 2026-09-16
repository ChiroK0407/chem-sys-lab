"""
simulation/data/loader.py

Clean Python interface over the three reference data files.

All other simulation modules import from here — never read JSON/CSV directly.
This keeps the data format decoupled from the simulation logic.

Public API
----------
get_fluid_properties(fluid_id, temperature_K)  → dict of cp, density, etc.
get_u_range(service_type)                      → (U_min, U_max, typical)
get_steam_saturation(pressure_Pa)              → dict of sat. properties
list_fluids()                                  → list of available fluid IDs
list_u_services()                              → list of service type keys
"""

from __future__ import annotations

import csv
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parent


# ── Cached loaders ────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_components() -> dict:
    with open(_DATA_DIR / "components.json", "r") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_u_values() -> dict:
    with open(_DATA_DIR / "u_values.json", "r") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_steam_tables() -> list[dict]:
    """
    Load steam_tables.csv into a list of dicts.
    All numeric values are converted to float on load.
    """
    rows = []
    with open(_DATA_DIR / "steam_tables.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["T_sat_K"].startswith("#"):
                continue
            rows.append({
                k: float(v) if k != "phase" else v
                for k, v in row.items()
            })
    return rows


# ── Fluid properties ──────────────────────────────────────────────────────────

def list_fluids() -> list[str]:
    """Return all available fluid IDs."""
    data = _load_components()
    return [k for k in data if not k.startswith("_")]


def get_fluid_properties(
    fluid_id: str,
    temperature_K: Optional[float] = None,
) -> dict:
    """
    Return physical properties for a fluid.

    If temperature_K is given, returns the closest temperature variant.
    Otherwise returns properties at the reference temperature T_ref.

    Returns
    -------
    dict with keys:
        cp                  [J/(kg·K)]
        density             [kg/m³]
        viscosity           [Pa·s]
        thermal_conductivity [W/(m·K)]
        phase               str
        T_used_K            float — temperature the properties are valid at
        source_note         str

    Raises
    ------
    KeyError  if fluid_id not found
    """
    data = _load_components()

    if fluid_id not in data:
        available = list_fluids()
        raise KeyError(
            f"Fluid '{fluid_id}' not found. "
            f"Available: {available}"
        )

    fluid = data[fluid_id]

    if temperature_K is None or "temperature_variants" not in fluid:
        props = fluid["properties"]
        T_used = fluid["T_ref"]
    else:
        # Find closest temperature variant
        variants = fluid["temperature_variants"]
        T_used, props = _nearest_variant(variants, temperature_K)

    return {
        "fluid_id":             fluid_id,
        "name":                 fluid["name"],
        "cp":                   props["cp"],
        "density":              props["density"],
        "viscosity":            props["viscosity"],
        "thermal_conductivity": props["thermal_conductivity"],
        "phase":                fluid["phase_at_ref"],
        "T_used_K":             T_used,
        "molecular_weight":     fluid.get("molecular_weight"),
        "boiling_point_K":      fluid.get("boiling_point"),
        "source_note": (
            f"Properties at {T_used - 273.15:.0f}°C from components.json "
            f"(NIST WebBook / Perry's)"
        ),
    }


def _nearest_variant(variants: dict, target_T: float) -> tuple[float, dict]:
    """
    Find the temperature variant closest to target_T.

    Variant keys are formatted as e.g. "303K_30C". Extract the K value
    from the key prefix and find the closest one.
    """
    best_key  = None
    best_diff = float("inf")
    best_T    = None

    for key in variants:
        try:
            T_variant = float(key.split("K")[0])
        except ValueError:
            continue
        diff = abs(T_variant - target_T)
        if diff < best_diff:
            best_diff = diff
            best_key  = key
            best_T    = T_variant

    if best_key is None:
        # Fall through — return first variant
        first_key = next(iter(variants))
        T_variant = float(first_key.split("K")[0])
        return T_variant, variants[first_key]

    return best_T, variants[best_key]


def build_stream_kwargs(
    fluid_id: str,
    temperature_K: float,
    pressure_Pa: float,
    mass_flowrate_kg_s: float,
    name: Optional[str] = None,
) -> dict:
    """
    Build keyword arguments ready to pass to ProcessStream().

    Usage
    -----
    from simulation.core.stream import ProcessStream
    from simulation.data.loader import build_stream_kwargs

    kwargs = build_stream_kwargs("water", 353.15, 300_000, 2.5)
    stream = ProcessStream(**kwargs)
    """
    props = get_fluid_properties(fluid_id, temperature_K)
    return {
        "name":                 name or f"{fluid_id}_{temperature_K - 273.15:.0f}C",
        "temperature":          temperature_K,
        "pressure":             pressure_Pa,
        "mass_flowrate":        mass_flowrate_kg_s,
        "cp":                   props["cp"],
        "density":              props["density"],
        "viscosity":            props["viscosity"],
        "thermal_conductivity": props["thermal_conductivity"],
        "phase":                props["phase"],
    }


# ── U-value lookup ────────────────────────────────────────────────────────────

def list_u_services() -> list[str]:
    """Return all available HX service type keys."""
    data = _load_u_values()
    return [k for k in data if not k.startswith("_")]


def get_u_range(service_type: str) -> dict:
    """
    Return typical U-value range for a given HX service type.

    Parameters
    ----------
    service_type : str
        Key from u_values.json. Call list_u_services() to see options.

    Returns
    -------
    dict with keys:
        U_min        [W/(m²·K)]
        U_max        [W/(m²·K)]
        typical      [W/(m²·K)]
        description  str
        examples     list[str]

    Raises
    ------
    KeyError  if service_type not found
    """
    data = _load_u_values()
    if service_type not in data:
        available = list_u_services()
        raise KeyError(
            f"Service type '{service_type}' not found. "
            f"Available: {available}"
        )
    entry = data[service_type]
    return {
        "service_type": service_type,
        "U_min":        entry["U_min"],
        "U_max":        entry["U_max"],
        "typical":      entry["typical"],
        "description":  entry["description"],
        "examples":     entry.get("examples", []),
    }


def suggest_u_value(hot_phase: str, cold_phase: str) -> dict:
    """
    Suggest a service type and U range based on stream phases.

    Parameters
    ----------
    hot_phase  : "liquid" | "vapor" | "mixed"
    cold_phase : "liquid" | "vapor" | "mixed"

    Returns
    -------
    dict — same format as get_u_range()
    """
    data = _load_u_values()
    matches = []
    for key, entry in data.items():
        if key.startswith("_"):
            continue
        if (entry.get("hot_phase") == hot_phase and
                entry.get("cold_phase") == cold_phase):
            matches.append(key)

    if not matches:
        # Default fallback
        return get_u_range("liquid_liquid")

    # Prefer the most specific match (longest key)
    best = max(matches, key=len)
    return get_u_range(best)


# ── Steam table lookup ────────────────────────────────────────────────────────

def get_steam_saturation(pressure_Pa: float) -> dict:
    """
    Return saturation properties at a given pressure by interpolation.

    Parameters
    ----------
    pressure_Pa : float
        Saturation pressure [Pa]. Valid range: ~101 kPa to ~4.2 MPa
        (373 K to 600 K).

    Returns
    -------
    dict with keys:
        T_sat_K         saturation temperature [K]
        P_sat_Pa        saturation pressure [Pa]
        h_f_J_kg        liquid enthalpy [J/kg]
        h_g_J_kg        vapour enthalpy [J/kg]
        h_fg_J_kg       latent heat of vaporisation [J/kg]
        rho_liq_kg_m3   liquid density [kg/m³]
        rho_vap_kg_m3   vapour density [kg/m³]
        cp_liq_J_kgK    liquid Cp [J/(kg·K)]
        mu_liq_Pa_s     liquid viscosity [Pa·s]
        k_liq_W_mK      liquid thermal conductivity [W/(m·K)]

    Raises
    ------
    ValueError  if pressure out of table range
    """
    rows = _load_steam_tables()
    P_min = rows[0]["P_sat_Pa"]
    P_max = rows[-1]["P_sat_Pa"]

    if not (P_min <= pressure_Pa <= P_max):
        raise ValueError(
            f"Pressure {pressure_Pa:.0f} Pa is outside steam table range "
            f"[{P_min:.0f}, {P_max:.0f}] Pa "
            f"({P_min/1e5:.2f} bar to {P_max/1e5:.2f} bar)."
        )

    # Linear interpolation between two bracketing rows
    for i in range(len(rows) - 1):
        P_lo = rows[i]["P_sat_Pa"]
        P_hi = rows[i + 1]["P_sat_Pa"]
        if P_lo <= pressure_Pa <= P_hi:
            f = (pressure_Pa - P_lo) / (P_hi - P_lo)
            result = {}
            for key in rows[i]:
                if key == "phase":
                    result[key] = rows[i][key]
                else:
                    result[key] = rows[i][key] + f * (rows[i+1][key] - rows[i][key])
            return result

    # Exact match on last row
    return rows[-1].copy()


def get_steam_saturation_by_T(temperature_K: float) -> dict:
    """
    Return saturation properties at a given temperature by interpolation.

    Parameters
    ----------
    temperature_K : float
        Valid range: 373 K to 600 K.
    """
    rows = _load_steam_tables()
    T_min = rows[0]["T_sat_K"]
    T_max = rows[-1]["T_sat_K"]

    if not (T_min <= temperature_K <= T_max):
        raise ValueError(
            f"Temperature {temperature_K:.2f} K is outside steam table range "
            f"[{T_min:.2f}, {T_max:.2f}] K "
            f"({T_min - 273.15:.1f}°C to {T_max - 273.15:.1f}°C)."
        )

    for i in range(len(rows) - 1):
        T_lo = rows[i]["T_sat_K"]
        T_hi = rows[i + 1]["T_sat_K"]
        if T_lo <= temperature_K <= T_hi:
            f = (temperature_K - T_lo) / (T_hi - T_lo)
            result = {}
            for key in rows[i]:
                if key == "phase":
                    result[key] = rows[i][key]
                else:
                    result[key] = rows[i][key] + f * (rows[i+1][key] - rows[i][key])
            return result

    return rows[-1].copy()


# ── Convenience: steam grade lookup ──────────────────────────────────────────

_STEAM_GRADES = {
    "lp_steam": 227_570,    # ~2.3 bar → 140°C  (low pressure steam)
    "mp_steam": 474_010,    # ~4.7 bar → 180°C  (medium pressure steam)
    "hp_steam": 1_456_600,  # ~14.6 bar → 250°C (high pressure steam)
}


def get_steam_grade_properties(grade: str) -> dict:
    """
    Return saturation properties for a named steam grade.

    Parameters
    ----------
    grade : "lp_steam" | "mp_steam" | "hp_steam"

    Returns
    -------
    Same as get_steam_saturation(), with h_fg as the latent heat.
    """
    if grade not in _STEAM_GRADES:
        raise KeyError(
            f"Steam grade '{grade}' unknown. "
            f"Available: {list(_STEAM_GRADES.keys())}"
        )
    P = _STEAM_GRADES[grade]
    return get_steam_saturation(P)
