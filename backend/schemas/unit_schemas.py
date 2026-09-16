"""
backend/schemas/unit_schemas.py

Pydantic v2 request/response models for all unit operations.
Currently: HeatExchanger.  Each future unit gets its own
Request/Response pair added to this file.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

from backend.schemas.stream_schema import StreamIn, StreamOut


# ── Heat Exchanger ────────────────────────────────────────────────────────────

class HeatExchangerRequest(BaseModel):
    """
    POST /solve/heat-exchanger

    Sizing mode  — provide hot_stream (+ cold_stream if process-to-process).
                   Set hot_outlet_T_c OR cold_outlet_T_c to define the duty.

    Rating mode  — provide hot_stream (+ cold_stream if process-to-process).
                   Set area_m2. Outlet temperatures are computed.
    """

    # Identity
    unit_id:       str   = Field("HX-001", description="Unique unit tag")

    # Mode and configuration
    mode:          str   = Field("sizing",       description="sizing | rating")
    flow_config:   str   = Field("counterflow",  description="counterflow | parallelflow | shell_tube_1_2")
    utility_fluid: str   = Field("cooling_water",description="cooling_water | lp_steam | mp_steam | hp_steam | process")

    # Design parameter
    U_W_m2K:       float = Field(600.0, gt=0,    description="Overall HTC [W/(m²·K)]")

    # Streams — hot required always; cold required for process-to-process
    hot_stream:    StreamIn
    cold_stream:   Optional[StreamIn] = None

    # Sizing mode: specify one outlet T to drive energy balance
    hot_outlet_T_c:  Optional[float] = Field(None, description="Hot outlet T [°C] — sizing mode")
    cold_outlet_T_c: Optional[float] = Field(None, description="Cold outlet T [°C] — sizing mode")

    # Rating mode: area required
    area_m2:       Optional[float] = Field(None, gt=0, description="Heat transfer area [m²] — rating mode")

    # CW parameters (ignored unless utility_fluid == cooling_water)
    cw_supply_T_c: float = Field(30.0,  description="CW supply temperature [°C]")
    cw_return_T_c: float = Field(45.0,  description="CW return temperature [°C]")

    @model_validator(mode="after")
    def check_mode_requirements(self) -> "HeatExchangerRequest":
        if self.mode == "rating" and self.area_m2 is None:
            raise ValueError("rating mode requires area_m2")
        if self.mode == "sizing":
            if self.hot_outlet_T_c is None and self.cold_outlet_T_c is None:
                if self.utility_fluid not in ("lp_steam", "mp_steam", "hp_steam"):
                    raise ValueError(
                        "sizing mode requires hot_outlet_T_c or cold_outlet_T_c"
                    )
        if self.utility_fluid == "process" and self.cold_stream is None:
            raise ValueError("utility_fluid='process' requires cold_stream")
        return self

    model_config = {"json_schema_extra": {"example": {
        "unit_id": "HX-101",
        "mode": "sizing",
        "flow_config": "counterflow",
        "utility_fluid": "cooling_water",
        "U_W_m2K": 600.0,
        "hot_stream": {
            "name": "process_hot",
            "temperature_c": 120.0,
            "pressure_kpa": 300.0,
            "mass_flowrate_kg_s": 2.0,
            "cp_J_kgK": 4200.0,
            "density_kg_m3": 950.0,
            "viscosity_Pa_s": 3e-4,
            "thermal_conductivity": 0.65,
            "phase": "liquid",
        },
        "hot_outlet_T_c": 50.0,
        "cw_supply_T_c": 30.0,
        "cw_return_T_c": 45.0,
    }}}


class UtilityConsumption(BaseModel):
    """Utility demand produced by a single unit operation."""
    utility_type:        str
    unit_id:             str
    duty_kW:             float
    mass_flowrate_kg_s:  float
    supply_temperature_c: float
    return_temperature_c: float


class HeatExchangerResponse(BaseModel):
    """
    Response for POST /solve/heat-exchanger.
    Contains all computed results, outlet streams, utility consumption,
    and the full step-by-step calculation log.
    """

    # Identity & status
    unit_id:        str
    unit_type:      str  = "HeatExchanger"
    is_solved:      bool
    warnings:       List[str] = []

    # Configuration echo
    mode:           str
    flow_config:    str
    utility_fluid:  str
    U_W_m2K:        float

    # Key results
    duty_kW:        float
    area_m2:        Optional[float]  = None
    LMTD_K:        float
    F_factor:       float
    NTU:            float
    effectiveness:  float
    hot_outlet_T_c:  Optional[float] = None
    cold_outlet_T_c: Optional[float] = None
    dt_min_K:       float

    # Outlet streams
    outlet_streams: List[StreamOut] = []

    # Utility consumption
    utility:        Optional[UtilityConsumption] = None

    # Transparency — full working shown in CalcLog panel
    calculation_log: List[str] = []

    @classmethod
    def from_unit(cls, unit, include_log: bool = True) -> "HeatExchangerResponse":
        """Build response from a solved HeatExchanger instance."""
        from simulation.core.stream import ProcessStream

        s = unit.summary()

        # Outlet streams
        outlets = [
            StreamOut.from_process_stream(stream)
            for stream in unit.outlet_streams.values()
            if isinstance(stream, ProcessStream)
        ]

        # Utility consumption
        utility = None
        if unit.utility_streams:
            u = unit.utility_streams[0]
            utility = UtilityConsumption(
                utility_type=u.utility_type,
                unit_id=u.unit_id,
                duty_kW=round(u.duty_kw, 3),
                mass_flowrate_kg_s=round(u.mass_flowrate, 4),
                supply_temperature_c=round(u.supply_temperature - 273.15, 1),
                return_temperature_c=round(u.return_temperature - 273.15, 1),
            )

        return cls(
            unit_id=s["unit_id"],
            is_solved=s["is_solved"],
            warnings=s["warnings"],
            mode=s["mode"],
            flow_config=s["flow_config"],
            utility_fluid=s["utility_fluid"],
            U_W_m2K=s["U_W_m2K"],
            duty_kW=s["duty_kW"],
            area_m2=s.get("area_m2"),
            LMTD_K=s["LMTD_K"],
            F_factor=s["F_factor"],
            NTU=s["NTU"],
            effectiveness=s["effectiveness"],
            hot_outlet_T_c=s.get("hot_outlet_T_C"),
            cold_outlet_T_c=s.get("cold_outlet_T_C"),
            dt_min_K=s["dt_min_K"],
            outlet_streams=outlets,
            utility=utility,
            calculation_log=unit.calculation_log if include_log else [],
        )


# ── Scenario sweep ────────────────────────────────────────────────────────────

class ScenarioSweepRequest(BaseModel):
    """
    POST /scenario/sweep

    Re-solve a heat exchanger while varying one parameter over a range.
    Returns a list of summary dicts — one per sweep point.

    sweep_parameter:  field name to vary (e.g. "mass_flowrate_kg_s",
                      "U_W_m2K", "hot_outlet_T_c")
    sweep_values:     list of values to try
    base_request:     the base HeatExchangerRequest (parameter overridden per step)
    """
    base_request:     HeatExchangerRequest
    sweep_parameter:  str
    sweep_values:     List[float] = Field(..., min_length=2, max_length=50)

    model_config = {"json_schema_extra": {"example": {
        "sweep_parameter": "mass_flowrate_kg_s",
        "sweep_values": [1.0, 1.5, 2.0, 2.5, 3.0],
        "base_request": {
            "unit_id": "HX-101",
            "mode": "sizing",
            "flow_config": "counterflow",
            "utility_fluid": "cooling_water",
            "U_W_m2K": 600.0,
            "hot_stream": {
                "name": "process_hot",
                "temperature_c": 120.0,
                "pressure_kpa": 300.0,
                "mass_flowrate_kg_s": 2.0,
                "cp_J_kgK": 4200.0,
                "density_kg_m3": 950.0,
                "viscosity_Pa_s": 3e-4,
                "thermal_conductivity": 0.65,
                "phase": "liquid",
            },
            "hot_outlet_T_c": 50.0,
        }
    }}}


class ScenarioSweepResponse(BaseModel):
    """Response for a parameter sweep."""
    sweep_parameter:  str
    sweep_values:     List[float]
    results:          List[Optional[dict]]  # one summary dict per point, None if failed
    errors:           List[Optional[str]]   # None if solved, error msg if failed


# ── Pump ──────────────────────────────────────────────────────────────────────

class PumpRequest(BaseModel):
    """POST /solve/pump"""

    unit_id:    str   = Field("P-001", description="Unique unit tag")

    # Stream
    feed_stream: StreamIn

    # Discharge conditions
    discharge_pressure_kPa:   float = Field(..., gt=0,
        description="Required discharge pressure [kPa abs]")
    discharge_elevation_m:    float = Field(0.0,
        description="Discharge elevation relative to pump [m]")
    suction_elevation_m:      float = Field(0.0,
        description="Suction elevation relative to pump [m]")
    suction_velocity_m_s:     float = Field(1.5, gt=0,
        description="Suction flange velocity [m/s]")
    discharge_velocity_m_s:   float = Field(2.5, gt=0,
        description="Discharge flange velocity [m/s]")

    # Efficiency
    eta_pump:  float = Field(0.75, gt=0, le=1,
        description="Pump hydraulic efficiency [0–1]")
    eta_motor: float = Field(0.92, gt=0, le=1,
        description="Motor efficiency [0–1]")

    # NPSH
    npsh_required_m:    float          = Field(2.0, ge=0,
        description="Required NPSH from manufacturer [m]")
    vapour_pressure_kPa: Optional[float] = Field(None, gt=0,
        description="Fluid vapour pressure [kPa]. Auto-looked up for water.")

    # Speed
    speed_rpm: float = Field(1450.0, gt=0,
        description="Pump speed [rpm] — used for specific speed Ns")

    model_config = {"json_schema_extra": {"example": {
        "unit_id": "P-101",
        "feed_stream": {
            "name": "feed_water",
            "temperature_c": 25.0,
            "pressure_kpa": 150.0,
            "mass_flowrate_kg_s": 5.0,
            "cp_J_kgK": 4182,
            "density_kg_m3": 997,
            "viscosity_Pa_s": 8.9e-4,
            "thermal_conductivity": 0.607,
            "phase": "liquid",
        },
        "discharge_pressure_kPa": 400.0,
        "eta_pump": 0.75,
        "eta_motor": 0.92,
        "npsh_required_m": 2.0,
    }}}


class PumpResponse(BaseModel):
    """Response for POST /solve/pump"""

    unit_id:     str
    unit_type:   str  = "Pump"
    is_solved:   bool
    warnings:    List[str] = []

    # Key results
    head_m:            float
    p_hydraulic_kW:    float
    p_shaft_kW:        float
    p_motor_kW:        float
    eta_pump:          float
    eta_motor:         float
    npsha_m:           Optional[float] = None
    npshr_m:           float
    delta_T_K:         float
    specific_speed:    float
    pump_type:         str
    speed_rpm:         float
    suction_pressure_kPa:   Optional[float] = None
    discharge_pressure_kPa: float

    # Streams
    outlet_stream:     Optional[StreamOut] = None

    # Utility
    motor_power_kW:    Optional[float] = None

    # Transparency
    calculation_log:   List[str] = []

    @classmethod
    def from_unit(cls, unit, include_log: bool = True) -> "PumpResponse":
        from simulation.core.stream import ProcessStream
        s = unit.summary()
        outlet = None
        if "outlet" in unit.outlet_streams:
            outlet = StreamOut.from_process_stream(unit.outlet_streams["outlet"])
        return cls(
            unit_id=s["unit_id"],
            is_solved=s["is_solved"],
            warnings=s["warnings"],
            head_m=s["head_m"],
            p_hydraulic_kW=s["p_hydraulic_kW"],
            p_shaft_kW=s["p_shaft_kW"],
            p_motor_kW=s["p_motor_kW"],
            eta_pump=s["eta_pump"],
            eta_motor=s["eta_motor"],
            npsha_m=s.get("npsha_m"),
            npshr_m=s["npshr_m"],
            delta_T_K=s["delta_T_K"],
            specific_speed=s["specific_speed"],
            pump_type=s["pump_type"],
            speed_rpm=s["speed_rpm"],
            suction_pressure_kPa=s.get("suction_pressure_kPa"),
            discharge_pressure_kPa=s["discharge_pressure_kPa"],
            outlet_stream=outlet,
            motor_power_kW=s.get("motor_power_kW"),
            calculation_log=unit.calculation_log if include_log else [],
        )


# ── Mixer ─────────────────────────────────────────────────────────────────────

class MixerRequest(BaseModel):
    """POST /solve/mixer — 2 to 10 inlet streams."""
    unit_id:      str            = Field("MX-001")
    outlet_name:  str            = Field("mixed_outlet")
    inlet_streams: List[StreamIn] = Field(..., min_length=2, max_length=10)

    model_config = {"json_schema_extra": {"example": {
        "unit_id": "MX-101",
        "outlet_name": "mixed_outlet",
        "inlet_streams": [
            {"name":"hot","temperature_c":80,"pressure_kpa":200,
             "mass_flowrate_kg_s":2.0,"cp_J_kgK":4182,"density_kg_m3":997,
             "viscosity_Pa_s":8.9e-4,"thermal_conductivity":0.607,"phase":"liquid"},
            {"name":"cold","temperature_c":40,"pressure_kpa":200,
             "mass_flowrate_kg_s":3.0,"cp_J_kgK":4182,"density_kg_m3":997,
             "viscosity_Pa_s":8.9e-4,"thermal_conductivity":0.607,"phase":"liquid"},
        ]
    }}}


class MixerResponse(BaseModel):
    unit_id:               str
    unit_type:             str   = "Mixer"
    is_solved:             bool
    warnings:              List[str] = []
    outlet_temperature_C:  float
    outlet_flowrate_kg_s:  float
    outlet_cp_J_kgK:       Optional[float] = None
    outlet_density_kg_m3:  Optional[float] = None
    outlet_phase:          Optional[str]   = None
    n_inlets:              int
    outlet_stream:         Optional[StreamOut] = None
    calculation_log:       List[str] = []

    @classmethod
    def from_unit(cls, unit, include_log=True):
        from simulation.core.stream import ProcessStream
        s = unit.summary()
        outlet = None
        if "outlet" in unit.outlet_streams:
            outlet = StreamOut.from_process_stream(unit.outlet_streams["outlet"])
        return cls(
            unit_id=s["unit_id"], is_solved=s["is_solved"], warnings=s["warnings"],
            outlet_temperature_C=s["outlet_temperature_C"],
            outlet_flowrate_kg_s=s["outlet_flowrate_kg_s"],
            outlet_cp_J_kgK=s.get("outlet_cp_J_kgK"),
            outlet_density_kg_m3=s.get("outlet_density_kg_m3"),
            outlet_phase=s.get("outlet_phase"),
            n_inlets=s["n_inlets"], outlet_stream=outlet,
            calculation_log=unit.calculation_log if include_log else [],
        )


# ── Splitter ──────────────────────────────────────────────────────────────────

class SplitterRequest(BaseModel):
    """POST /solve/splitter"""
    unit_id:         str                        = Field("SP-001")
    feed_stream:     StreamIn
    split_fractions: Optional[dict]             = Field(
        None, description='{"outlet_name": fraction, ...} — must sum to 1.0')
    n_outlets:       int                        = Field(
        2, ge=2, description="Equal-split outlet count (ignored if split_fractions given)")
    outlet_names:    Optional[List[str]]        = Field(
        None, description="Names for equal-split outlets")

    model_config = {"json_schema_extra": {"example": {
        "unit_id": "SP-101",
        "feed_stream": {
            "name":"feed","temperature_c":60,"pressure_kpa":200,
            "mass_flowrate_kg_s":10.0,"cp_J_kgK":4182,"density_kg_m3":997,
            "viscosity_Pa_s":8.9e-4,"thermal_conductivity":0.607,"phase":"liquid"},
        "split_fractions": {"overhead": 0.6, "bottoms": 0.4},
    }}}


class SplitterResponse(BaseModel):
    unit_id:              str
    unit_type:            str   = "Splitter"
    is_solved:            bool
    warnings:             List[str] = []
    n_outlets:            int
    split_fractions:      dict
    inlet_flowrate_kg_s:  Optional[float] = None
    outlet_streams:       List[StreamOut] = []
    calculation_log:      List[str] = []

    @classmethod
    def from_unit(cls, unit, include_log=True):
        from simulation.core.stream import ProcessStream
        s = unit.summary()
        outlets = [
            StreamOut.from_process_stream(stream)
            for stream in unit.outlet_streams.values()
            if isinstance(stream, ProcessStream)
        ]
        return cls(
            unit_id=s["unit_id"], is_solved=s["is_solved"], warnings=s["warnings"],
            n_outlets=s["n_outlets"], split_fractions=s["split_fractions"],
            inlet_flowrate_kg_s=s.get("inlet_flowrate_kg_s"),
            outlet_streams=outlets,
            calculation_log=unit.calculation_log if include_log else [],
        )


# ── Reactor shared ────────────────────────────────────────────────────────────

class ReactorKinetics(BaseModel):
    """Kinetic parameters shared by CSTR and PFR."""
    k_ref:          float = Field(0.01,    gt=0,  description="Rate constant at T_ref")
    T_ref_C:        float = Field(25.0,           description="Reference temperature [°C]")
    Ea_J_mol:       float = Field(50000.0, ge=0,  description="Activation energy [J/mol]")
    n_order:        float = Field(1.0,     gt=0,  description="Reaction order")
    delta_H_rxn:    float = Field(-50000.0,       description="Heat of reaction [J/mol_A]. Negative = exothermic.")
    C_A0_mol_m3:    float = Field(1000.0,  gt=0,  description="Initial concentration of A [mol/m³]")
    MW_A_g_mol:     float = Field(100.0,   gt=0,  description="Molecular weight of A [g/mol]")


class ReactorOperating(BaseModel):
    """Operating specification shared by CSTR and PFR."""
    mode:           str   = Field("design",      description="design | rating")
    thermal_mode:   str   = Field("isothermal",  description="isothermal | adiabatic")
    T_rxn_C:        float = Field(25.0,           description="Reaction/inlet temperature [°C]")
    X_target:       float = Field(0.90,  gt=0, lt=1.0, description="Target conversion (design mode)")
    volume_m3:      Optional[float] = Field(None, gt=0, description="Reactor volume [m³] (rating mode)")

    @model_validator(mode="after")
    def check_rating_has_volume(self) -> "ReactorOperating":
        if self.mode == "rating" and self.volume_m3 is None:
            raise ValueError("rating mode requires volume_m3")
        return self


class ReactorResponseBase(BaseModel):
    """Common result fields for CSTR and PFR responses."""
    unit_id:             str
    unit_type:           str
    is_solved:           bool
    warnings:            List[str] = []
    mode:                str
    thermal_mode:        str
    conversion:          float
    conversion_pct:      float
    volume_m3:           float
    volume_L:            float
    residence_time_s:    float
    residence_time_min:  float
    T_out_C:             float
    C_A_out_mol_m3:      float
    k_rxn:               float
    heat_duty_kW:        float
    n_order:             float
    Ea_J_mol:            float
    delta_H_rxn_J_mol:   float
    C_A0_mol_m3:         float
    outlet_stream:       Optional[StreamOut] = None
    calculation_log:     List[str] = []


# ── CSTR ──────────────────────────────────────────────────────────────────────

class CSTRRequest(BaseModel):
    unit_id:    str               = Field("R-101")
    feed_stream: StreamIn
    kinetics:   ReactorKinetics   = ReactorKinetics()
    operating:  ReactorOperating  = ReactorOperating()

    model_config = {"json_schema_extra": {"example": {
        "unit_id": "R-101",
        "feed_stream": {"name":"feed","temperature_c":25,"pressure_kpa":200,
            "mass_flowrate_kg_s":1.0,"cp_J_kgK":4000,"density_kg_m3":1000,
            "viscosity_Pa_s":8.9e-4,"thermal_conductivity":0.607,"phase":"liquid"},
        "kinetics": {"k_ref":0.01,"T_ref_C":25,"Ea_J_mol":50000,"n_order":1.0,
            "delta_H_rxn":-50000,"C_A0_mol_m3":1000,"MW_A_g_mol":100},
        "operating": {"mode":"design","thermal_mode":"isothermal",
            "T_rxn_C":25,"X_target":0.90},
    }}}


class CSTRResponse(ReactorResponseBase):
    unit_type: str = "CSTR"
    rate_mol_m3_s: Optional[float] = None

    @classmethod
    def from_unit(cls, unit, include_log=True):
        from simulation.core.stream import ProcessStream
        s = unit.summary()
        outlet = None
        if "outlet" in unit.outlet_streams:
            outlet = StreamOut.from_process_stream(unit.outlet_streams["outlet"])
        return cls(
            unit_id=s["unit_id"], is_solved=s["is_solved"], warnings=s["warnings"],
            mode=s["mode"], thermal_mode=s["thermal_mode"],
            conversion=s["conversion"], conversion_pct=s["conversion_pct"],
            volume_m3=s["volume_m3"], volume_L=s["volume_L"],
            residence_time_s=s["residence_time_s"], residence_time_min=s["residence_time_min"],
            T_out_C=s["T_out_C"], C_A_out_mol_m3=s["C_A_out_mol_m3"],
            k_rxn=s["k_rxn"], heat_duty_kW=s["heat_duty_kW"],
            n_order=s["n_order"], Ea_J_mol=s["Ea_J_mol"],
            delta_H_rxn_J_mol=s["delta_H_rxn_J_mol"], C_A0_mol_m3=s["C_A0_mol_m3"],
            rate_mol_m3_s=s.get("rate_mol_m3_s"),
            outlet_stream=outlet,
            calculation_log=unit.calculation_log if include_log else [],
        )


# ── PFR ───────────────────────────────────────────────────────────────────────

class PFRRequest(BaseModel):
    unit_id:    str               = Field("R-201")
    feed_stream: StreamIn
    kinetics:   ReactorKinetics   = ReactorKinetics()
    operating:  ReactorOperating  = ReactorOperating()
    n_points:   int               = Field(100, ge=10, le=500,
        description="Profile resolution points")

    model_config = {"json_schema_extra": {"example": {
        "unit_id": "R-201",
        "feed_stream": {"name":"feed","temperature_c":25,"pressure_kpa":200,
            "mass_flowrate_kg_s":1.0,"cp_J_kgK":4000,"density_kg_m3":1000,
            "viscosity_Pa_s":8.9e-4,"thermal_conductivity":0.607,"phase":"liquid"},
        "kinetics": {"k_ref":0.01,"T_ref_C":25,"Ea_J_mol":0,"n_order":1.0,
            "delta_H_rxn":-50000,"C_A0_mol_m3":1000,"MW_A_g_mol":100},
        "operating": {"mode":"design","thermal_mode":"isothermal",
            "T_rxn_C":25,"X_target":0.90},
    }}}


class PFRProfile(BaseModel):
    V_m3:    List[float]
    X:       List[float]
    T_C:     List[float]
    inv_rA:  List[float]


class PFRResponse(ReactorResponseBase):
    unit_type: str = "PFR"
    profile:   Optional[PFRProfile] = None

    @classmethod
    def from_unit(cls, unit, include_log=True):
        from simulation.core.stream import ProcessStream
        s = unit.summary()
        outlet = None
        if "outlet" in unit.outlet_streams:
            outlet = StreamOut.from_process_stream(unit.outlet_streams["outlet"])
        profile = None
        if "profile" in s:
            p = s["profile"]
            profile = PFRProfile(V_m3=p["V_m3"], X=p["X"], T_C=p["T_C"], inv_rA=p["inv_rA"])
        return cls(
            unit_id=s["unit_id"], is_solved=s["is_solved"], warnings=s["warnings"],
            mode=s["mode"], thermal_mode=s["thermal_mode"],
            conversion=s["conversion"], conversion_pct=s["conversion_pct"],
            volume_m3=s["volume_m3"], volume_L=s["volume_L"],
            residence_time_s=s["residence_time_s"], residence_time_min=s["residence_time_min"],
            T_out_C=s["T_out_C"], C_A_out_mol_m3=s["C_A_out_mol_m3"],
            k_rxn=s["k_rxn"], heat_duty_kW=s["heat_duty_kW"],
            n_order=s["n_order"], Ea_J_mol=s["Ea_J_mol"],
            delta_H_rxn_J_mol=s["delta_H_rxn_J_mol"], C_A0_mol_m3=s["C_A0_mol_m3"],
            outlet_stream=outlet, profile=profile,
            calculation_log=unit.calculation_log if include_log else [],
        )