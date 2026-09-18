"""
backend/schemas/units/hx_catalog.py

TEMA/industrial heat-exchanger class catalog referenced by
simulation/units/heat_exchanger.py (`from backend.schemas.units.hx_catalog
import HeatExchangerClass, EXCHANGER_CLASS_CATALOG`). Without this file
the whole backend fails to import at startup — same failure mode as
the missing backend/schemas/units/pump.py catalog.

NOTE: HeatExchangerRequest / HeatExchangerResponse in
backend/schemas/unit_schemas.py do not currently expose
`selected_class`, so /solve/heat-exchanger always runs without a
class compliance audit (HeatExchanger.selected_class stays None).
Wiring a `selected_class` field through the HX request/response and
into routers/units.py's `solve_heat_exchanger()` would be needed to
actually use these templates from the frontend — left out here since
it wasn't part of what was reported missing.
"""

from __future__ import annotations
from enum import Enum


class HeatExchangerClass(str, Enum):
    """TEMA / industrial heat exchanger construction classes."""

    TEMA_E_SHELL_TUBE = "TEMA E Shell-and-Tube"
    TEMA_BEM = "TEMA BEM Shell-and-Tube"
    PLATE_AND_FRAME = "Plate-and-Frame"
    DOUBLE_PIPE = "Double Pipe"
    AIR_COOLED_FIN_FAN = "Air-Cooled Fin-Fan"


EXCHANGER_CLASS_CATALOG = {
    HeatExchangerClass.TEMA_E_SHELL_TUBE: {
        "extended_name": "TEMA Class E Shell-and-Tube",
        "max_design_pressure_bar": 100.0,
        "max_design_temp_c": 400.0,
        "allows_phase_change": True,
    },
    HeatExchangerClass.TEMA_BEM: {
        "extended_name": "TEMA BEM Shell-and-Tube (fixed tubesheet)",
        "max_design_pressure_bar": 60.0,
        "max_design_temp_c": 350.0,
        "allows_phase_change": True,
    },
    HeatExchangerClass.PLATE_AND_FRAME: {
        "extended_name": "Gasketed Plate-and-Frame",
        "max_design_pressure_bar": 25.0,
        "max_design_temp_c": 180.0,
        "allows_phase_change": False,
    },
    HeatExchangerClass.DOUBLE_PIPE: {
        "extended_name": "Double Pipe (hairpin)",
        "max_design_pressure_bar": 140.0,
        "max_design_temp_c": 400.0,
        "allows_phase_change": True,
    },
    HeatExchangerClass.AIR_COOLED_FIN_FAN: {
        "extended_name": "Air-Cooled Fin-Fan",
        "max_design_pressure_bar": 40.0,
        "max_design_temp_c": 200.0,
        "allows_phase_change": True,
    },
}
