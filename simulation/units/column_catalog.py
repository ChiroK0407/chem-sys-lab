# simulation/data/column_catalog.py
# Catalog of standard column internals (packing & trays)
# Referenced by absorber/stripper/distillation modules

COLUMN_INTERNAL_CATALOG = {
    # --- Random Packing ---
    "PALL_RINGS_25M": {
        "name": "Metal Pall Rings (25mm / 1-inch)",
        "type": "random_packing",
        "packing_factor_sm1": 170,   # GPDC Fp factor
        "surface_area_m2_m3": 205,   # ap specific surface area
        "typical_h_etp_m": 0.45,     # HETP value
        "max_v_loading": 0.85        # Max vapor loading fraction
    },
    "PALL_RINGS_50M": {
        "name": "Metal Pall Rings (50mm / 2-inch)",
        "type": "random_packing",
        "packing_factor_sm1": 120,
        "surface_area_m2_m3": 125,
        "typical_h_etp_m": 0.60,
        "max_v_loading": 0.80
    },
    "RASCHIG_RING_CERAMIC": {
        "name": "Ceramic Raschig Rings",
        "type": "random_packing",
        "packing_factor_sm1": 200,
        "surface_area_m2_m3": 100,
        "typical_h_etp_m": 0.75,
        "max_v_loading": 0.70
    },

    # --- Structured Packing ---
    "MELLAPAK_250Y": {
        "name": "Sulzer Mellapak 250Y Structured",
        "type": "structured_packing",
        "packing_factor_sm1": 65,
        "surface_area_m2_m3": 250,
        "typical_h_etp_m": 0.35,
        "max_v_loading": 0.90
    },
    "MELLAPAK_500X": {
        "name": "Sulzer Mellapak 500X Structured",
        "type": "structured_packing",
        "packing_factor_sm1": 90,
        "surface_area_m2_m3": 500,
        "typical_h_etp_m": 0.25,
        "max_v_loading": 0.88
    },

    # --- Tray Internals ---
    "SIEVE_TRAY_18IN": {
        "name": "Sieve Tray (18-inch spacing)",
        "type": "tray",
        "tray_spacing_mm": 450,
        "classification": "sieve",
        "pressure_drop_pa": 250,
        "turn_down_ratio": 1.2
    },
    "VALVE_TRAY_GLITSCH_V1": {
        "name": "Valve Tray Glitsch V-1 (24-inch spacing)",
        "type": "tray",
        "tray_spacing_mm": 600,
        "classification": "valve",
        "pressure_drop_pa": 300,
        "turn_down_ratio": 2.5
    }
}

# simulation/data/column_catalog.py

# --- Section B: Structured Packing Catalog ---
STRUCTURED_PACKING_CATALOG = {
    "MELLAPAK_125Y": {
        "name": "Sulzer Mellapak 125Y",
        "type": "structured_packing",
        "packing_factor_sm1": 80,
        "surface_area_m2_m3": 125,
        "typical_h_etp_m": 0.50,
        "max_v_loading": 0.90,
        "corrugation_angle_deg": 45.0,
        "channel_base_mm": 6.0,
        "manufacturer": "Sulzer",
        "pressure_drop_Pa_per_m": 50
    },
    "MELLAPAK_250Y": {
        "name": "Sulzer Mellapak 250Y",
        "type": "structured_packing",
        "packing_factor_sm1": 65,
        "surface_area_m2_m3": 250,
        "typical_h_etp_m": 0.35,
        "max_v_loading": 0.90,
        "corrugation_angle_deg": 45.0,
        "channel_base_mm": 6.0,
        "manufacturer": "Sulzer",
        "pressure_drop_Pa_per_m": 60
    },
    "MELLAPAK_350Y": {
        "name": "Sulzer Mellapak 350Y",
        "type": "structured_packing",
        "packing_factor_sm1": 55,
        "surface_area_m2_m3": 350,
        "typical_h_etp_m": 0.30,
        "max_v_loading": 0.88,
        "corrugation_angle_deg": 45.0,
        "channel_base_mm": 6.0,
        "manufacturer": "Sulzer",
        "pressure_drop_Pa_per_m": 70
    },
    "MELLAPAK_500Y": {
        "name": "Sulzer Mellapak 500Y",
        "type": "structured_packing",
        "packing_factor_sm1": 45,
        "surface_area_m2_m3": 500,
        "typical_h_etp_m": 0.25,
        "max_v_loading": 0.85,
        "corrugation_angle_deg": 45.0,
        "channel_base_mm": 6.0,
        "manufacturer": "Sulzer",
        "pressure_drop_Pa_per_m": 80
    },
    "MELLAPAK_125X": {
        "name": "Sulzer Mellapak 125X",
        "type": "structured_packing",
        "packing_factor_sm1": 90,
        "surface_area_m2_m3": 125,
        "typical_h_etp_m": 0.55,
        "max_v_loading": 0.88,
        "corrugation_angle_deg": 60.0,
        "channel_base_mm": 6.0,
        "manufacturer": "Sulzer",
        "pressure_drop_Pa_per_m": 65
    },
    "MELLAPAK_250X": {
        "name": "Sulzer Mellapak 250X",
        "type": "structured_packing",
        "packing_factor_sm1": 75,
        "surface_area_m2_m3": 250,
        "typical_h_etp_m": 0.40,
        "max_v_loading": 0.88,
        "corrugation_angle_deg": 60.0,
        "channel_base_mm": 6.0,
        "manufacturer": "Sulzer",
        "pressure_drop_Pa_per_m": 75
    },
    "FLEXIPAC_1Y": {
        "name": "Koch-Glitsch Flexipac 1Y",
        "type": "structured_packing",
        "packing_factor_sm1": 70,
        "surface_area_m2_m3": 200,
        "typical_h_etp_m": 0.40,
        "max_v_loading": 0.88,
        "corrugation_angle_deg": 45.0,
        "channel_base_mm": 7.0,
        "manufacturer": "Koch-Glitsch",
        "pressure_drop_Pa_per_m": 55
    },
    "FLEXIPAC_2Y": {
        "name": "Koch-Glitsch Flexipac 2Y",
        "type": "structured_packing",
        "packing_factor_sm1": 60,
        "surface_area_m2_m3": 250,
        "typical_h_etp_m": 0.35,
        "max_v_loading": 0.88,
        "corrugation_angle_deg": 45.0,
        "channel_base_mm": 7.0,
        "manufacturer": "Koch-Glitsch",
        "pressure_drop_Pa_per_m": 65
    },
    "FLEXIPAC_3Y": {
        "name": "Koch-Glitsch Flexipac 3Y",
        "type": "structured_packing",
        "packing_factor_sm1": 50,
        "surface_area_m2_m3": 300,
        "typical_h_etp_m": 0.30,
        "max_v_loading": 0.85,
        "corrugation_angle_deg": 45.0,
        "channel_base_mm": 7.0,
        "manufacturer": "Koch-Glitsch",
        "pressure_drop_Pa_per_m": 70
    },
    "MONTZ_B1_200": {
        "name": "Montz B1-200",
        "type": "structured_packing",
        "packing_factor_sm1": 65,
        "surface_area_m2_m3": 200,
        "typical_h_etp_m": 0.40,
        "max_v_loading": 0.88,
        "corrugation_angle_deg": 45.0,
        "channel_base_mm": 6.5,
        "manufacturer": "Montz",
        "pressure_drop_Pa_per_m": 60
    },
    "MONTZ_B1_300": {
        "name": "Montz B1-300",
        "type": "structured_packing",
        "packing_factor_sm1": 55,
        "surface_area_m2_m3": 300,
        "typical_h_etp_m": 0.30,
        "max_v_loading": 0.85,
        "corrugation_angle_deg": 45.0,
        "channel_base_mm": 6.5,
        "manufacturer": "Montz",
        "pressure_drop_Pa_per_m": 70
    },
    "SULZER_MX_GAUZE": {
        "name": "Sulzer MX Gauze Packing",
        "type": "structured_packing",
        "packing_factor_sm1": 40,
        "surface_area_m2_m3": 500,
        "typical_h_etp_m": 0.20,
        "max_v_loading": 0.80,
        "corrugation_angle_deg": 45.0,
        "channel_base_mm": 5.0,
        "manufacturer": "Sulzer",
        "pressure_drop_Pa_per_m": 40
    }
}

# simulation/data/column_catalog.py

# --- Section C: Tray Catalog ---
TRAY_CATALOG = {
    "SIEVE_TRAY_STANDARD": {
        "extended_name": "Standard Sieve Tray",
        "tray_type": "sieve",
        "typical_tray_spacing_mm": [450, 600],
        "typical_tray_efficiency": 0.65,
        "efficiency_range": [0.55, 0.75],
        "hole_diameter_mm": 5.0,
        "hole_area_fraction": 0.10,
        "downcomer_area_fraction": 0.12,
        "turndown_ratio": 1.5,
        "pressure_drop_per_tray_mbar": 25.0,
        "weep_point_fraction": 0.25,
        "best_for": ["low cost", "simple design"],
        "not_suitable_for": ["low vapor rates", "high turndown"],
        "notes": "Prone to weeping at low loads",
        "source": "Kister Distillation Design Table 6.1"
    },
    "SIEVE_TRAY_HIGH_CAPACITY": {
        "extended_name": "High Capacity Sieve Tray",
        "tray_type": "sieve",
        "typical_tray_spacing_mm": [600],
        "typical_tray_efficiency": 0.70,
        "efficiency_range": [0.60, 0.75],
        "hole_diameter_mm": 8.0,
        "hole_area_fraction": 0.12,
        "downcomer_area_fraction": 0.15,
        "turndown_ratio": 1.4,
        "pressure_drop_per_tray_mbar": 30.0,
        "weep_point_fraction": 0.30,
        "best_for": ["high vapor throughput"],
        "not_suitable_for": ["low liquid rates"],
        "notes": "Improved vapor handling",
        "source": "Smith Chemical Process Design (2005)"
    },
    "VALVE_TRAY_GLITSCH_V1": {
        "extended_name": "Glitsch V-1 Valve Tray",
        "tray_type": "valve",
        "typical_tray_spacing_mm": [450, 600],
        "typical_tray_efficiency": 0.75,
        "efficiency_range": [0.65, 0.80],
        "hole_diameter_mm": None,
        "hole_area_fraction": None,
        "downcomer_area_fraction": 0.12,
        "turndown_ratio": 2.5,
        "pressure_drop_per_tray_mbar": 35.0,
        "weep_point_fraction": 0.20,
        "best_for": ["absorption", "wide turndown"],
        "not_suitable_for": ["very low pressure drop systems"],
        "notes": "Variable opening maintains efficiency",
        "source": "Kister Table 6.2"
    },
    "VALVE_TRAY_KOCH_FLEXITRAY": {
        "extended_name": "Koch Flexitray Valve Tray",
        "tray_type": "valve",
        "typical_tray_spacing_mm": [600],
        "typical_tray_efficiency": 0.78,
        "efficiency_range": [0.70, 0.82],
        "hole_diameter_mm": None,
        "hole_area_fraction": None,
        "downcomer_area_fraction": 0.13,
        "turndown_ratio": 3.0,
        "pressure_drop_per_tray_mbar": 32.0,
        "weep_point_fraction": 0.18,
        "best_for": ["flexible operation", "revamps"],
        "not_suitable_for": ["extreme fouling"],
        "notes": "Excellent turndown flexibility",
        "source": "Smith Table 14.3"
    },
    "VALVE_TRAY_NUTTER_MVG": {
        "extended_name": "Nutter MVG Valve Tray",
        "tray_type": "valve",
        "typical_tray_spacing_mm": [450],
        "typical_tray_efficiency": 0.80,
        "efficiency_range": [0.70, 0.85],
        "hole_diameter_mm": None,
        "hole_area_fraction": None,
        "downcomer_area_fraction": 0.12,
        "turndown_ratio": 2.8,
        "pressure_drop_per_tray_mbar": 30.0,
        "weep_point_fraction": 0.20,
        "best_for": ["high efficiency distillation"],
        "not_suitable_for": ["low pressure drop systems"],
        "notes": "High efficiency valve tray",
        "source": "Kister Table 6.4"
    },
    "BUBBLE_CAP_TRAY_STANDARD": {
        "extended_name": "Standard Bubble Cap Tray",
        "tray_type": "bubble_cap",
        "typical_tray_spacing_mm": [600],
        "typical_tray_efficiency": 0.70,
        "efficiency_range": [0.60, 0.75],
        "hole_diameter_mm": None,
        "hole_area_fraction": None,
        "downcomer_area_fraction": 0.15,
        "turndown_ratio": 4.0,
        "pressure_drop_per_tray_mbar": 40.0,
        "weep_point_fraction": 0.10,
        "best_for": ["low turndown risk", "fouling resistance"],
        "not_suitable_for": ["high pressure drop sensitive systems"],
        "notes": "Rarely used today; robust",
        "source": "Kister Table 6.5"
    },
    "DUAL_FLOW_TRAY": {
        "extended_name": "Dual Flow Tray",
        "tray_type": "dual_flow",
        "typical_tray_spacing_mm": [600],
        "typical_tray_efficiency": 0.55,
        "efficiency_range": [0.45, 0.60],
        "hole_diameter_mm": 10.0,
        "hole_area_fraction": 0.20,
        "downcomer_area_fraction": 0.0,
        "turndown_ratio": 1.2,
        "pressure_drop_per_tray_mbar": 20.0,
        "weep_point_fraction": 0.40,
        "best_for": ["low cost", "fouling tolerance"],
        "not_suitable_for": ["high efficiency separation"],
        "notes": "No downcomers; poor efficiency",
        "source": "Smith Table 14.5"
    },
    "FIXED_VALVE_TRAY": {
        "extended_name": "Fixed Valve Tray",
        "tray_type": "fixed_valve",
        "typical_tray_spacing_mm": [450, 600],
        "typical_tray_efficiency": 0.72,
        "efficiency_range": [0.65, 0.78],
        "hole_diameter_mm": None,
        "hole_area_fraction": None,
        "downcomer_area_fraction": 0.12,
        "turndown_ratio": 2.0,
        "pressure_drop_per_tray_mbar": 28.0,
        "weep_point_fraction": 0.22,
        "best_for": ["moderate turndown", "cost balance"],
        "not_suitable_for": ["extreme fouling"],
        "notes": "Simpler than movable valves",
        "source": "Kister Table 6.3"
    }
}

# --- Utility Functions ---
def get_packing(key: str) -> dict:
    return COLUMN_INTERNAL_CATALOG.get(key) or STRUCTURED_PACKING_CATALOG.get(key)

def get_tray(key: str) -> dict:
    return TRAY_CATALOG.get(key)

def list_random_packing() -> list[dict]:
    return list(COLUMN_INTERNAL_CATALOG.values())

def list_structured_packing() -> list[dict]:
    return list(STRUCTURED_PACKING_CATALOG.values())

def list_trays() -> list[dict]:
    return list(TRAY_CATALOG.values())

def get_all_internals() -> dict:
    return {
        "random_packing": list_random_packing(),
        "structured_packing": list_structured_packing(),
        "trays": list_trays()
    }
