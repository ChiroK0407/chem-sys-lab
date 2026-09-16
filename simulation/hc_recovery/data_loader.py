"""
Data Loader Module for Hydrocarbon Recovery Simulation.

Responsible for safely loading, parsing, validating, and caching component constants,
saturation curves, adsorption parameters, and membrane properties from the project data lake.
"""

import json
import pandas as pd
from typing import Any
from pathlib import Path
from simulation.core.exceptions import DataLoadError

# Module-level structure cache to minimize redundant disk I/O operations
_JSON_CACHE: dict[str, dict[str, Any]] = {}


def _get_data_directory() -> Path:
    """
    Dynamically resolves the backend data directory relative to this file's location.
    
    Assumes a workspace architecture where 'simulation' and 'backend' are siblings.
    Workspace Root:
      ├── backend/data/
      └── simulation/hc_recovery/data_loader.py
    """
    return Path(__file__).resolve().parent.parent.parent / "backend" / "data"


def load_component_constants(component: str) -> dict[str, Any]:
    """
    Loads and validates the thermodynamic and physical constants for a specified component.

    Args:
        component: The lowercase name of the target chemical species (e.g., 'propylene', 'nitrogen').

    Returns:
        A dictionary containing verified physical property constants.

    Raises:
        DataLoadError: If the constants file is missing, JSON is malformed, or required structural 
                       thermodynamic keys are absent.
    """
    data_dir = _get_data_directory()
    file_path = data_dir / "components" / component.lower() / "constants.json"
    cache_key = str(file_path.resolve())

    if cache_key in _JSON_CACHE:
        return _JSON_CACHE[cache_key]

    if not file_path.exists():
        raise DataLoadError(
            f"Component constants file not found for species '{component}'.",
            detail={"file_path": str(file_path), "component": component}
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise DataLoadError(
            f"Malformed JSON structure in component constants file for '{component}'.",
            detail={"file_path": str(file_path), "error": str(exc)}
        )

    # Strict physical property schema validation
    required_keys = {"name", "formula", "mw", "tc", "pc", "omega", "tb"}
    missing_keys = required_keys - data.keys()
    if missing_keys:
        raise DataLoadError(
            f"Missing required thermodynamic constants {list(missing_keys)} for component '{component}'.",
            detail={"file_path": str(file_path), "missing_keys": list(missing_keys)}
        )

    _JSON_CACHE[cache_key] = data
    return data


def load_saturation_curve(component: str) -> pd.DataFrame:
    """
    Loads and validates the vapor pressure/saturation matrix for a specific component.

    Args:
        component: The lowercase name of the target chemical species.

    Returns:
        A pandas DataFrame with columns ['T_K', 'P_sat_bar'] representing the saturation curve.

    Raises:
        DataLoadError: If the CSV file is missing, empty, or fails to adhere to structural column metrics.
    """
    data_dir = _get_data_directory()
    file_path = data_dir / "components" / component.lower() / "saturation.csv"

    if not file_path.exists():
        raise DataLoadError(
            f"Saturation data file missing for species '{component}'.",
            detail={"file_path": str(file_path), "component": component}
        )

    try:
        df = pd.read_csv(file_path)
    except Exception as exc:
        raise DataLoadError(
            f"Failed to read saturation matrix CSV for component '{component}'.",
            detail={"file_path": str(file_path), "error": str(exc)}
        )

    required_columns = {"T_K", "P_sat_bar"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise DataLoadError(
            f"Saturation curve data frame has incorrect schema mapping for component '{component}'.",
            detail={"file_path": str(file_path), "missing_columns": list(missing_columns)}
        )

    return df


def load_adsorption_parameters(adsorbent: str, component: str) -> dict[str, Any]:
    """
    Extracts multi-component Langmuir isotherm parameters from the adsorption data configuration.

    Args:
        adsorbent: The unique matching key for the targeted solid bed material (e.g., 'Zeolite 13X').
        component: The chemical component being evaluated.

    Returns:
        A dictionary containing isotherm parameter vectors (e.g., q_m, b constants).

    Raises:
        DataLoadError: If parameters file is unreadable, or keys for the selected adsorbent 
                       or compound are not mapped.
    """
    data_dir = _get_data_directory()
    file_path = data_dir / "adsorption" / parameters.json
    cache_key = str(file_path.resolve())

    if cache_key in _JSON_CACHE:
        root_data = _JSON_CACHE[cache_key]
    else:
        if not file_path.exists():
            raise DataLoadError(
                "Adsorption parameters database file is missing from data storage path.",
                detail={"file_path": str(file_path)}
            )
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                root_data = json.load(f)
            _JSON_CACHE[cache_key] = root_data
        except json.JSONDecodeError as exc:
            raise DataLoadError(
                "Structural JSON syntax error inside adsorption parameters database file.",
                detail={"file_path": str(file_path), "error": str(exc)}
            )

    if "adsorbents" not in root_data or adsorbent not in root_data["adsorbents"]:
        raise DataLoadError(
            f"Adsorbent matrix profile '{adsorbent}' is missing from the adsorption parameter ledger.",
            detail={"file_path": str(file_path), "requested_adsorbent": adsorbent}
        )

    adsorbent_profile = root_data["adsorbents"][adsorbent]
    if "components" not in adsorbent_profile or component not in adsorbent_profile["components"]:
        raise DataLoadError(
            f"Isotherm constants for component '{component}' are not defined on adsorbent matrix profile '{adsorbent}'.",
            detail={"file_path": str(file_path), "adsorbent": adsorbent, "requested_component": component}
        )

    return adsorbent_profile["components"][component]


def load_membrane_parameters(membrane: str, component: str) -> dict[str, Any]:
    """
    Extracts permeability and separation selectivity coefficients from the membrane configuration ledger.

    Args:
        membrane: The material name of the membrane configuration being evaluated (e.g., 'Polyimide').
        component: The target chemical component stream element.

    Returns:
        A dictionary containing transport constants (e.g., permeability rates, thickness coefficients).

    Raises:
        DataLoadError: If structural parameters file is unreadable, or missing membrane material 
                       or component property scopes.
    """
    data_dir = _get_data_directory()
    file_path = data_dir / "membrane" / "parameters.json"
    cache_key = str(file_path.resolve())

    if cache_key in _JSON_CACHE:
        root_data = _JSON_CACHE[cache_key]
    else:
        if not file_path.exists():
            raise DataLoadError(
                "Membrane transport parameters ledger file is missing from data storage path.",
                detail={"file_path": str(file_path)}
            )
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                root_data = json.load(f)
            _JSON_CACHE[cache_key] = root_data
        except json.JSONDecodeError as exc:
            raise DataLoadError(
                "Structural JSON syntax error inside membrane transport ledger file.",
                detail={"file_path": str(file_path), "error": str(exc)}
            )

    if "membranes" not in root_data or membrane not in root_data["membranes"]:
        raise DataLoadError(
            f"Membrane material configuration profile '{membrane}' is missing from the parameter ledger.",
            detail={"file_path": str(file_path), "requested_membrane": membrane}
        )

    membrane_profile = root_data["membranes"][membrane]
    if "components" not in membrane_profile or component not in membrane_profile["components"]:
        raise DataLoadError(
            f"Transport coefficients for component '{component}' are not defined on membrane profile '{membrane}'.",
            detail={"file_path": str(file_path), "membrane": membrane, "requested_component": component}
        )

    return membrane_profile["components"][component]