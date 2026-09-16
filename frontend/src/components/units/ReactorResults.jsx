import { Flame, Snowflake, FlaskConical } from "lucide-react";
import ResultCard from "../shared/ResultCard";
import WarningBanner from "../shared/WarningBanner";
import CalcLog from "../shared/CalcLog";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

function fmt(v, dp = 3) { return v == null ? "—" : Number(v).toFixed(dp); }

function HeatDutyBadge({ Q }) {
  if (Q == null) return null;
  const isExo = Q < 0;
  return (
    <div className={`rounded-xl border p-4 flex items-start gap-3
      ${isExo ? "border-blue-200 bg-blue-50" : "border-orange-200 bg-orange-50"}`}>
      <div className={`rounded-lg p-2 ${isExo ? "bg-blue-100" : "bg-orange-100"}`}>
        {isExo ? <Snowflake size={18} className="text-blue-600" />
                : <Flame    size={18} className="text-orange-600" />}
      </div>
      <div>
        <p className={`text-sm font-medium ${isExo ? "text-blue-800" : "text-orange-800"}`}>
          {isExo ? "Exothermic — heat must be removed" : "Endothermic — heat input required"}
        </p>
        <p className="text-xs text-gray-600 mt-0.5">
          |Q| = <strong>{fmt(Math.abs(Q), 3)} kW</strong>
        </p>
      </div>
    </div>
  );
}

function LevenspielChart({ profile }) {
  if (!profile?.X?.length) return null;
  const data = profile.X.map((x, i) => ({
    X: parseFloat(x.toFixed(4)),
    inv_rA: Math.min(parseFloat(profile.inv_rA[i].toFixed(4)), 200),
    T_C: profile.T_C ? parseFloat(profile.T_C[i].toFixed(2)) : null,
  }));

  return (
    <div className="card p-4">
      <p className="section-title mb-3">Levenspiel plot  <span className="text-gray-400 font-normal normal-case ml-1">1/(−r_A) vs X</span></p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="X" label={{ value: "Conversion X", position: "insideBottom", offset: -2, fontSize: 11 }} tick={{ fontSize: 11 }} />
          <YAxis label={{ value: "1/(−r_A)", angle: -90, position: "insideLeft", fontSize: 11 }} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v, n) => [v, n === "inv_rA" ? "1/(−r_A)" : "T (°C)"]} />
          <Legend />
          <Line type="monotone" dataKey="inv_rA" stroke="#3b6d11" dot={false} strokeWidth={2} name="1/(−r_A)" />
          {data[0]?.T_C != null && (
            <Line type="monotone" dataKey="T_C" stroke="#d97706" dot={false} strokeWidth={1.5} name="T (°C)" yAxisId="T" />
          )}
        </LineChart>
      </ResponsiveContainer>
      <p className="text-xs text-gray-400 mt-2">
        Area under curve = V/F_A0. Shaded area represents PFR volume; rectangle represents CSTR volume at same X.
      </p>
    </div>
  );
}

export default function ReactorResults({ result }) {
  if (!result) return null;
  const isExo = result.heat_duty_kW < 0;

  return (
    <div className="space-y-5">
      <WarningBanner warnings={result.warnings} />

      {/* Header */}
      <div className="flex items-center gap-3 px-1">
        <div className="rounded-xl bg-purple-50 border border-purple-200 p-2">
          <FlaskConical size={18} className="text-purple-600" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900">
            {result.unit_type} — {result.mode} / {result.thermal_mode}
          </p>
          <p className="text-xs text-gray-500">
            n = {result.n_order}  |  Ea = {result.Ea_J_mol?.toLocaleString()} J/mol  |  ΔH = {result.delta_H_rxn_J_mol?.toLocaleString()} J/mol
          </p>
        </div>
      </div>

      {/* Key results */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <ResultCard label="Conversion X"   value={`${fmt(result.conversion_pct, 2)}%`} highlight />
        <ResultCard label="Volume"         value={fmt(result.volume_L, 2)}    unit="L"    highlight />
        <ResultCard label="Residence time" value={fmt(result.residence_time_min, 3)} unit="min" />
        <ResultCard label="T outlet"       value={fmt(result.T_out_C, 2)}     unit="°C"
          warn={result.thermal_mode === "adiabatic" && Math.abs(result.T_out_C - (result.profile?.T_C?.[0] ?? result.T_out_C)) > 50} />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <ResultCard label="C_A out"        value={fmt(result.C_A_out_mol_m3, 2)} unit="mol/m³" />
        <ResultCard label="k(T_rxn)"       value={result.k_rxn?.toExponential(3)}  unit="" />
        <ResultCard label="|Heat duty|"    value={fmt(Math.abs(result.heat_duty_kW), 3)} unit="kW"
          warn={Math.abs(result.heat_duty_kW) > 500} />
        <ResultCard label="Volume"         value={fmt(result.volume_m3, 4)}    unit="m³" />
      </div>

      {/* Heat duty */}
      <HeatDutyBadge Q={result.heat_duty_kW} />

      {/* Outlet stream */}
      {result.outlet_stream && (
        <div className="card p-4">
          <p className="section-title mb-3">Outlet stream</p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-sm">
            {[["Name", result.outlet_stream.name],
              ["T (°C)", fmt(result.outlet_stream.temperature_c, 2)],
              ["P (kPa)", fmt(result.outlet_stream.pressure_kpa, 1)],
              ["ṁ (kg/s)", result.outlet_stream.mass_flowrate_kg_s]
            ].map(([label, value]) => (
              <div key={label}>
                <p className="text-xs text-gray-400">{label}</p>
                <p className="font-medium text-gray-800">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Levenspiel chart — PFR only */}
      {result.profile && <LevenspielChart profile={result.profile} />}

      <CalcLog log={result.calculation_log} unitId={result.unit_id} />
    </div>
  );
}
