"""
backend/schemas/units/pump.py

Industrial pump-standard catalog referenced by simulation/units/pump.py
(`from backend.schemas.units.pump import PumpStandardEnum,
INDUSTRIAL_PUMP_CATALOG`). Without this file the whole backend fails
to import — simulation/units/__init__.py imports Pump unconditionally,
so every router (units, reference, columns, hc_recovery) breaks at
startup, not just the pump endpoint.

NOTE: PumpRequest / PumpResponse in backend/schemas/unit_schemas.py
do not currently expose `selected_standard`, so /solve/pump always
runs in "Manual Mode" (Pump.selected_standard stays None) regardless
of this catalog. Wiring a `selected_standard` field through the pump
request/response and into routers/units.py's `solve_pump()` would be
needed to actually use these compliance templates from the frontend —
left out here since it wasn't part of what was reported missing.
"""

from __future__ import annotations
from enum import Enum


class PumpStandardEnum(str, Enum):
    """Industrial pump design-code templates audited by Pump.solve()."""

    API_610 = "API 610"
    ASME_B73_1 = "ASME B73.1"
    ISO_2858 = "ISO 2858"


INDUSTRIAL_PUMP_CATALOG = {
    PumpStandardEnum.API_610: {
        "full_name": "API 610 — Centrifugal Pumps for Petroleum, Petrochemical, "
                      "and Natural Gas Industries",
        "max_design_pressure_bar": 100.0,
        "max_design_temp_c": 400.0,
        "npsh_margin_buffer_m": 1.0,
    },
    PumpStandardEnum.ASME_B73_1: {
        "full_name": "ASME B73.1 — Horizontal End Suction Centrifugal Pumps "
                      "for Chemical Process",
        "max_design_pressure_bar": 27.6,
        "max_design_temp_c": 260.0,
        "npsh_margin_buffer_m": 0.6,
    },
    PumpStandardEnum.ISO_2858: {
        "full_name": "ISO 2858 — End Suction Centrifugal Pumps (Nominal Duty Point)",
        "max_design_pressure_bar": 16.0,
        "max_design_temp_c": 140.0,
        "npsh_margin_buffer_m": 0.5,
    },
}
