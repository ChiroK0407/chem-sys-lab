import { Zap, Droplets } from "lucide-react";
import ResultCard from "../shared/ResultCard";
import WarningBanner from "../shared/WarningBanner";
import CalcLog from "../shared/CalcLog";

function fmt(v, dp = 3) {
  if (v == null || isNaN(v)) return "—";
  return Number(v).toFixed(dp);
}

export default function PumpResults({ result }) {
  if (!result) return null;

  const npshMargin = result.npsha_m != null
    ? result.npsha_m - result.npshr_m
    : null;

  return (
    <div className="space-y-5">

      <WarningBanner warnings={result.warnings} />

      {/* Head and power */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <ResultCard label="Total head"      value={fmt(result.head_m, 2)}        unit="m"   highlight />
        <ResultCard label="Shaft power"     value={fmt(result.p_shaft_kW, 3)}    unit="kW"  highlight />
        <ResultCard label="Motor power"     value={fmt(result.p_motor_kW, 3)}    unit="kW" />
        <ResultCard label="Hydraulic power" value={fmt(result.p_hydraulic_kW,3)} unit="kW" />
      </div>

      {/* Efficiency and NPSH */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <ResultCard label="η pump"          value={fmt(result.eta_pump, 2)}       unit="—" />
        <ResultCard label="η motor"         value={fmt(result.eta_motor, 2)}      unit="—" />
        <ResultCard label="NPSHa"           value={fmt(result.npsha_m, 2)}        unit="m"
          warn={npshMargin != null && npshMargin < 0.5} />
        <ResultCard label="NPSH margin"     value={fmt(npshMargin, 2)}            unit="m"
          warn={npshMargin != null && npshMargin < 0.5} />
      </div>

      {/* Pressures and specific speed */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <ResultCard label="Suction P"       value={fmt(result.suction_pressure_kPa, 1)}   unit="kPa" />
        <ResultCard label="Discharge P"     value={fmt(result.discharge_pressure_kPa, 1)} unit="kPa" />
        <ResultCard label="Specific speed"  value={fmt(result.specific_speed, 4)}          unit="Ns" />
        <ResultCard label="Fluid ΔT"        value={fmt(result.delta_T_K, 4)}               unit="K" />
      </div>

      {/* Pump type recommendation */}
      <div className="card p-4 flex items-start gap-3">
        <div className="rounded-lg bg-blue-50 border border-blue-200 p-2 flex-shrink-0">
          <Droplets size={16} className="text-blue-600" />
        </div>
        <div>
          <p className="text-xs font-medium text-gray-500 mb-0.5">
            Pump type recommendation (from Ns)
          </p>
          <p className="text-sm font-medium text-gray-900">{result.pump_type}</p>
          <p className="text-xs text-gray-400 mt-0.5">
            Based on dimensionless specific speed Ns = {fmt(result.specific_speed, 4)}
            — C&R Vol. 1, Section 8.3
          </p>
        </div>
      </div>

      {/* Electricity utility */}
      {result.motor_power_kW != null && (
        <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4
                        flex items-start gap-3">
          <div className="rounded-lg bg-yellow-100 p-2">
            <Zap size={18} className="text-yellow-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-yellow-800">Electricity</p>
            <div className="mt-1 flex gap-4">
              <span className="text-xs text-gray-600">
                Motor: <strong>{fmt(result.motor_power_kW, 3)} kW</strong>
              </span>
              <span className="text-xs text-gray-600">
                Speed: <strong>{result.speed_rpm} rpm</strong>
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Outlet stream */}
      {result.outlet_stream && (
        <div className="card p-4">
          <p className="section-title mb-3">Outlet stream</p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-sm">
            <div>
              <p className="text-xs text-gray-400">Name</p>
              <p className="font-medium text-gray-800">{result.outlet_stream.name}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Temperature</p>
              <p className="font-medium text-gray-800">
                {fmt(result.outlet_stream.temperature_c, 3)} °C
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Pressure</p>
              <p className="font-medium text-gray-800">
                {fmt(result.outlet_stream.pressure_kpa, 1)} kPa
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Flowrate</p>
              <p className="font-medium text-gray-800">
                {result.outlet_stream.mass_flowrate_kg_s} kg/s
              </p>
            </div>
          </div>
        </div>
      )}

      <CalcLog log={result.calculation_log} unitId={result.unit_id} />

    </div>
  );
}
