import ResultCard from "../shared/ResultCard";
import WarningBanner from "../shared/WarningBanner";
import CalcLog from "../shared/CalcLog";

function fmt(v, dp = 3) { return v == null ? "—" : Number(v).toFixed(dp); }

export default function MixerResults({ result }) {
  if (!result) return null;
  return (
    <div className="space-y-5">
      <WarningBanner warnings={result.warnings} />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <ResultCard label="Outlet T"    value={fmt(result.outlet_temperature_C, 2)} unit="°C"    highlight />
        <ResultCard label="Total flow"  value={fmt(result.outlet_flowrate_kg_s, 3)} unit="kg/s"  highlight />
        <ResultCard label="Outlet Cp"   value={fmt(result.outlet_cp_J_kgK, 1)}      unit="J/kg·K" />
        <ResultCard label="Outlet ρ"    value={fmt(result.outlet_density_kg_m3, 2)} unit="kg/m³" />
      </div>
      <div className="card p-4">
        <p className="section-title mb-2">Inlet summary</p>
        <p className="text-xs text-gray-500">{result.n_inlets} streams mixed</p>
      </div>
      {result.outlet_stream && (
        <div className="card p-4">
          <p className="section-title mb-3">Outlet stream</p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-sm">
            {[
              ["Name",    result.outlet_stream.name],
              ["T (°C)",  fmt(result.outlet_stream.temperature_c, 2)],
              ["P (kPa)", fmt(result.outlet_stream.pressure_kpa, 1)],
              ["ṁ (kg/s)",result.outlet_stream.mass_flowrate_kg_s],
              ["Phase",   result.outlet_stream.phase],
              ["ṁCp (W/K)", fmt(result.outlet_stream.heat_capacity_rate_W_K, 1)],
            ].map(([label, value]) => (
              <div key={label}>
                <p className="text-xs text-gray-400">{label}</p>
                <p className="font-medium text-gray-800">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      <CalcLog log={result.calculation_log} unitId={result.unit_id} />
    </div>
  );
}
