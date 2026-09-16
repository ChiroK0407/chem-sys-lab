import React from 'react';
// Mock import mapping. Adjust according to where your frontend components folder houses CalcLog.
import CalcLog from '../shared/CalcLog';

export default function AbsorberResults({ data }) {
  if (!data || !data.is_solved) return null;

  const isStripper = data.unit_type === "Stripper";

  return (
    <div className="space-y-6 text-slate-200 mt-8">
      
      {/* Row 1 Metric Display Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Theoretical Stages ($N$)</div>
          <div className="text-2xl font-bold text-slate-100 mt-1 font-mono">{data.N_theoretical}</div>
          {data.N_actual && <div className="text-xs text-slate-400 mt-1">Actual Plates: {data.N_actual}</div>}
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Calculated Diameter</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">{data.column_diameter_m} m</div>
          <div className="text-xs text-slate-500 mt-1">Standard TEMA shell bound</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Height Sizing</div>
          <div className="text-2xl font-bold text-slate-100 mt-1 font-mono">{data.column_height_m} m</div>
          <div className="text-xs text-slate-500 mt-1">Includes 20% design margin</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Hydraulic Flood Loading</div>
          <div className={`text-2xl font-bold mt-1 font-mono ${data.flood_fraction > 0.80 ? 'text-amber-400' : 'text-slate-100'}`}>
            {(data.flood_fraction * 100).toFixed(1)}%
          </div>
          {data.flood_fraction > 0.80 ? (
            <div className="text-[10px] text-amber-500 font-semibold uppercase mt-1">⚠ High Velocity Warn Limit</div>
          ) : (
            <div className="text-xs text-emerald-500 mt-1">Safe velocity envelope</div>
          )}
        </div>
      </div>

      {/* Row 2 Matrix Metrics & Efficiency Summary Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-stretch">
        <div className="md:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-slate-500 block">Distribution Coeff ($K_{value}$)</span>
            <span className="text-slate-300 font-mono font-bold text-base">{data.K_value}</span>
          </div>
          <div>
            <span className="text-slate-500 block">{isStripper ? 'Stripping Factor ($S$)' : 'Absorption Factor ($A$)'}</span>
            <span className="text-slate-300 font-mono font-bold text-base">
              {isStripper ? data.stripping_factor_S : data.absorption_factor_A}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block">Circulation Rate ($L_{op}$)</span>
            <span className="text-slate-300 font-mono text-base">{data.L_operating_mol_s || data.L_mol_s} mol/s</span>
          </div>
          <div>
            <span className="text-slate-500 block">Henry Coefficient at T</span>
            <span className="text-slate-300 font-mono text-base">{data.H_at_T} atm</span>
          </div>
        </div>

        {/* Big Efficiency Badge Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 flex flex-col justify-center items-center text-center">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            {isStripper ? 'Solvent Clean Regeneration Efficiency' : 'Solute Separation Efficiency'}
          </div>
          <div className="px-6 py-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-3xl font-extrabold rounded-2xl font-mono">
            {isStripper ? data.regeneration_efficiency_pct : data.removal_efficiency_pct}%
          </div>
        </div>
      </div>

      {/* Heat Duty Sizing Allocation Panel */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Thermal Energy Balance Assessment</div>
        {!isStripper ? (
          <div>
            <span className="text-slate-400 text-sm">Exothermic Absorption Release Duty:</span>
            <span className="text-xl font-bold font-mono text-amber-400 ml-2">{data.Q_absorption_kW} kW</span>
            <div className="text-xs text-slate-500 mt-1">Requires standard utility cooling water coils.</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <span className="text-slate-500 text-xs block">Reboiler Duty Allocation</span>
              <span className="text-lg font-bold font-mono text-amber-500">{data.Q_reboiler_kW} kW</span>
            </div>
            <div>
              <span className="text-slate-500 text-xs block">Overhead Condenser Load</span>
              <span className="text-lg font-bold font-mono text-blue-400">{data.Q_condenser_kW} kW</span>
            </div>
            <div>
              <span className="text-slate-500 text-xs block">Regeneration Steam Consumption</span>
              <span className="text-lg font-bold font-mono text-slate-300">{data.steam_rate_kg_s} kg/s</span>
            </div>
          </div>
        )}
      </div>

      {/* Material Balance Stream Outlets Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="px-6 py-4 bg-slate-950/40 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
          Column Outlet Stream Material Balance
        </div>
        <table className="w-full text-left border-collapse text-sm">
          <thead>
            <tr className="bg-slate-950/20 text-slate-400 text-xs border-b border-slate-800">
              <th className="px-6 py-3 font-medium">Stream Key</th>
              <th className="px-6 py-3 font-medium">Flowrate [mol/s]</th>
              <th className="px-6 py-3 font-medium">Solute Concentration fraction</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            <tr>
              <td className="px-6 py-3 font-medium text-blue-400 font-mono">gas_out</td>
              <td className="px-6 py-3 font-mono">{data.G_mol_s}</td>
              <td className="px-6 py-3 font-mono text-amber-400">{data.y_out}</td>
            </tr>
            <tr>
              <td className="px-6 py-3 font-medium text-emerald-400 font-mono">liquid_out</td>
              <td className="px-6 py-3 font-mono">{data.L_operating_mol_s || data.L_mol_s}</td>
              <td className="px-6 py-3 font-mono text-amber-400">{data.x_out}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* ASME Compliance Warning block */}
      <div className="p-4 bg-slate-950/50 border border-slate-800/80 rounded-xl text-xs text-slate-500 italic flex justify-between items-center">
        <span>ASME Pressure Vessel Compliance Audit Note</span>
        <span className="text-slate-400 font-mono not-italic">Wall thickness: {data.wall_thickness_mm} mm per ASME VIII-1 UG-27</span>
      </div>

      {/* Calculation Log Transparency Component */}
      <CalcLog logs={data.calculation_log} />
    </div>
  );
}