import { Droplets, Flame, Zap, ThermometerSun } from "lucide-react";
import ResultCard from "../shared/ResultCard";
import WarningBanner from "../shared/WarningBanner";
import CalcLog from "../shared/CalcLog";
import TubeSizer from "./TubeSizer";
import { HXTemperatureProfile, HXHydraulicGauge } from "./HXSchematics";

function fmt(val, dp = 2) {
  if (val == null) return "—";
  return Number(val).toFixed(dp);
}

function StreamRow({ stream }) {
  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="py-2 pr-4 text-sm font-medium text-gray-800">{stream.name}</td>
      <td className="py-2 pr-4 text-sm text-gray-600">{fmt(stream.temperature_c)} °C</td>
      <td className="py-2 pr-4 text-sm text-gray-600">{fmt(stream.mass_flowrate_kg_s, 3)} kg/s</td>
      <td className="py-2 pr-4 text-sm text-gray-600">{stream.phase}</td>
      <td className="py-2 text-sm text-gray-600">{stream.source_unit ?? "—"}</td>
    </tr>
  );
}

function UtilityPanel({ utility }) {
  if (!utility) return null;
  const isCW    = utility.utility_type === "cooling_water";
  const isSteam = utility.utility_type?.includes("steam");

  return (
    <div className={`rounded-xl border p-4 flex items-start gap-3
      ${isCW ? "border-blue-200 bg-blue-50" : "border-orange-200 bg-orange-50"}`}
    >
      <div className={`rounded-lg p-2 ${isCW ? "bg-blue-100" : "bg-orange-100"}`}>
        {isCW
          ? <Droplets size={18} className="text-blue-600" />
          : <Flame    size={18} className="text-orange-600" />
        }
      </div>
      <div>
        <p className={`text-sm font-medium ${isCW ? "text-blue-800" : "text-orange-800"}`}>
          {isCW ? "Cooling water" : utility.utility_type.replace("_", " ").replace("steam","Steam")}
        </p>
        <div className="mt-1 flex flex-wrap gap-4">
          <span className="text-xs text-gray-600">
            Duty: <strong>{fmt(utility.duty_kW)} kW</strong>
          </span>
          <span className="text-xs text-gray-600">
            Flow: <strong>{fmt(utility.mass_flowrate_kg_s, 3)} kg/s</strong>
          </span>
          <span className="text-xs text-gray-600">
            Supply / return: <strong>{utility.supply_temperature_c}°C / {utility.return_temperature_c}°C</strong>
          </span>
        </div>
      </div>
    </div>
  );
}

export default function HXResults({ result }) {
  if (!result) return null;

  return (
    <div className="space-y-5">

      {/* Warnings */}
      <WarningBanner warnings={result.warnings} />

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <ResultCard label="Duty"         value={fmt(result.duty_kW, 1)}    unit="kW"   highlight />
        <ResultCard label="Area"         value={fmt(result.area_m2, 3)}    unit="m²"   highlight={result.mode === "sizing"} />
        <ResultCard label="LMTD"         value={fmt(result.LMTD_K, 2)}     unit="K" />
        <ResultCard label="F-factor"     value={fmt(result.F_factor, 4)}   unit="—"    warn={result.F_factor < 0.75} />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <ResultCard label="NTU"          value={fmt(result.NTU, 4)}        unit="—" />
        <ResultCard label="Effectiveness" value={fmt(result.effectiveness, 4)} unit="—" />
        <ResultCard label="ΔT min"       value={fmt(result.dt_min_K, 2)}   unit="K"    warn={result.dt_min_K < 5} />
        <ResultCard label="U"            value={result.U_W_m2K}            unit="W/m²·K" />
      </div>

      {/* Outlet temperatures */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <ThermometerSun size={16} className="text-green-700" />
          <p className="text-sm font-medium text-gray-800">Outlet temperatures</p>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {result.hot_outlet_T_c != null && (
            <div>
              <p className="text-xs text-gray-500">Hot side out</p>
              <p className="text-xl font-semibold text-gray-900">{fmt(result.hot_outlet_T_c, 2)} °C</p>
            </div>
          )}
          {result.cold_outlet_T_c != null && (
            <div>
              <p className="text-xs text-gray-500">Cold side out</p>
              <p className="text-xl font-semibold text-gray-900">{fmt(result.cold_outlet_T_c, 2)} °C</p>
            </div>
          )}
        </div>
      </div>

      {/* Utility */}
      <UtilityPanel utility={result.utility} />

      {/* Outlet stream table */}
      {result.outlet_streams?.length > 0 && (
        <div className="card p-4">
          <p className="section-title mb-3">Outlet streams</p>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="pb-2 text-left text-xs font-medium text-gray-500">Name</th>
                <th className="pb-2 text-left text-xs font-medium text-gray-500">T (°C)</th>
                <th className="pb-2 text-left text-xs font-medium text-gray-500">ṁ (kg/s)</th>
                <th className="pb-2 text-left text-xs font-medium text-gray-500">Phase</th>
                <th className="pb-2 text-left text-xs font-medium text-gray-500">From</th>
              </tr>
            </thead>
            <tbody>
              {result.outlet_streams.map((s) => <StreamRow key={s.name} stream={s} />)}
            </tbody>
          </table>
        </div>
      )}

      {/* Tube sizing — shown in sizing mode when area is available */}
      {result.mode === "sizing" && result.area_m2 && (
        <TubeSizer areaMm2={result.area_m2} />
      )}

      {/* Dynamic Schematic Analytics Row — Mounted in the lower layout viewport */}
      <div className="flex flex-col gap-5 my-4">
        <HXTemperatureProfile result={result} />
        <HXHydraulicGauge result={result} />
      </div>

      {/* Calculation log */}
      <CalcLog log={result.calculation_log} unitId={result.unit_id} />

    </div>
  );
}
