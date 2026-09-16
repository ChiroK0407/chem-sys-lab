import ResultCard from "../shared/ResultCard";
import WarningBanner from "../shared/WarningBanner";
import CalcLog from "../shared/CalcLog";

function fmt(v, dp = 3) { return v == null ? "—" : Number(v).toFixed(dp); }

export default function SplitterResults({ result }) {
  if (!result) return null;

  return (
    <div className="space-y-5">
      <WarningBanner warnings={result.warnings} />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <ResultCard label="Outlets"       value={result.n_outlets}                              unit="streams" highlight />
        <ResultCard label="Feed flowrate" value={fmt(result.inlet_flowrate_kg_s, 3)}            unit="kg/s" />
        <ResultCard label="Split mode"    value={result.split_fractions ? "explicit" : "equal"} unit="" />
      </div>

      {result.outlet_streams?.length > 0 && (
        <div className="card p-4">
          <p className="section-title mb-3">Outlet streams</p>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                {["Name","Fraction","ṁ (kg/s)","T (°C)","P (kPa)","Phase"].map(h => (
                  <th key={h} className="pb-2 text-left text-xs font-medium text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.outlet_streams.map((s) => {
                const frac = result.split_fractions?.[s.name];
                return (
                  <tr key={s.name} className="border-b border-gray-100 last:border-0">
                    <td className="py-2 pr-3 text-sm font-medium text-gray-800">{s.name}</td>
                    <td className="py-2 pr-3 text-sm text-gray-600">
                      {frac != null ? (frac * 100).toFixed(2) + "%" : "—"}
                    </td>
                    <td className="py-2 pr-3 text-sm text-gray-600">{s.mass_flowrate_kg_s}</td>
                    <td className="py-2 pr-3 text-sm text-gray-600">{fmt(s.temperature_c, 2)}</td>
                    <td className="py-2 pr-3 text-sm text-gray-600">{fmt(s.pressure_kpa, 1)}</td>
                    <td className="py-2 text-sm text-gray-600">{s.phase}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <CalcLog log={result.calculation_log} unitId={result.unit_id} />
    </div>
  );
}
