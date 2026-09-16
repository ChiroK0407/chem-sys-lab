import React, { useState } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { simulateAdsorption } from '../../api/hcRecovery';

export default function Adsorption() {
  // Column Bed Sizing States
  const [pressureBar, setPressureBar] = useState(8.0);
  const [adsorbent, setAdsorbent] = useState("zeolite_13x");
  const [bedMassKg, setBedMassKg] = useState(1200.0);

  // Shared Reference Stream Context Mock Matrix
  const sampleFeed = {
    flowrate_kmol_hr: 150.0,
    pressure_MPa: 1.5,
    temperature_C: 35.0,
    x_N2: 0.95,
    x_C3H6: 0.04,
    x_C3H8: 0.01
  };

  // Solver States Layout Matrix
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleRunSimulation = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);

    const payload = {
      feed: sampleFeed,
      pressure_bar: parseFloat(pressureBar),
      adsorbent: adsorbent,
      adsorbent_mass_kg: parseFloat(bedMassKg)
    };

    try {
      const data = await simulateAdsorption(payload);
      setResults(data);
    } catch (err) {
      const detailedErr = err.response?.data?.detail;
      setErrorMsg(detailedErr?.message || "Convergence error or failure parsing equilibrium affinity constants.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Fixed-Bed Adsorption Simulator</h1>
        <p className="text-sm text-slate-500 mt-1">Model multi-component affinity mechanics using competitive Extended Langmuir Isotherms.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form Entry Module */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded-xl p-6 shadow-sm h-fit">
          <form onSubmit={handleRunSimulation} className="space-y-5">
            <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-2">Bed Specifications</h2>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Solid Phase Adsorbent</label>
              <select 
                value={adsorbent} onChange={(e) => setAdsorbent(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-slate-900 text-sm"
              >
                <option value="activated_carbon">Activated Carbon (High Capacity)</option>
                <option value="zeolite_13x">Zeolite 13X (Polar Selective)</option>
                <option value="molecular_sieve_5a">Molecular Sieve 5A (Size Exclusion)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Adsorption Pressure (bar)</label>
              <input 
                type="number" step="0.1" value={pressureBar} onChange={(e) => setPressureBar(e.target.value)} required
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Total Active Bed Mass (kg)</label>
              <input 
                type="number" step="10" value={bedMassKg} onChange={(e) => setBedMassKg(e.target.value)} required
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900 text-sm"
              />
            </div>

            {errorMsg && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 leading-normal">
                {errorMsg}
              </div>
            )}

            <button
              type="submit" disabled={loading}
              className="w-full py-2.5 px-4 bg-slate-900 text-white rounded-md text-sm font-medium hover:bg-slate-800 disabled:opacity-50 transition-colors"
            >
              {loading ? "Iterating Isotherms..." : "Run Sorption Solver"}
            </button>
          </form>
        </div>

        {/* Graphic Output Visualization Modules */}
        <div className="lg:col-span-2 space-y-6">
          {!results && !loading && (
            <div className="bg-slate-50 border border-slate-200 border-dashed rounded-xl p-12 text-center text-slate-400 text-sm">
              Submit column mass limits to view competitive solid loading profiles.
            </div>
          )}

          {loading && (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 text-sm shadow-sm">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-950 mx-auto mb-4"></div>
              Evaluating active site pore occupancies...
            </div>
          )}

          {results && !loading && (
            <div className="space-y-6 animate-fade-in">
              {/* Sizing Indicator Card */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Sorption Capture Yield Efficiency</div>
                <div className="text-2xl font-bold text-slate-800">{results.recovery_pct.toFixed(2)} <span className="text-sm font-normal text-slate-500">% Capture Efficiency</span></div>
              </div>

              {/* Isotherm Multi-Series Line Chart */}
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-800 mb-4 uppercase tracking-wider text-left">Competitive Loading Isotherms</h3>
                <div className="w-full h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={results.loading_curve} margin={{ top: 5, right: 20, left: -15, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="pressure_bar" stroke="#94a3b8" fontSize={12} tickLine={false} label={{ value: 'Column Pressure (bar)', position: 'insideBottom', offset: -5, fill: '#64748b', fontSize: 11 }} />
                      <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} label={{ value: 'Solid Loading (mol/kg)', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '12px' }} />
                      <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                      <Line type="monotone" dataKey="loading_propylene" name="Propylene (C₃H₆)" stroke="#2563eb" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="loading_propane" name="Propane (C₃H₈)" stroke="#16a34a" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="loading_nitrogen" name="Nitrogen (N₂ Carrier)" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Equilibrium Load Table Matrix */}
              <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50">
                  <h3 className="text-sm font-semibold text-slate-800">Equilibrium Sorbent Load Distribution Balance</h3>
                </div>
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-500 tracking-wider">
                      <th className="px-5 py-3">Compound Phase Element</th>
                      <th className="px-5 py-3 text-right">Solid Phase Loading (mol/kg)</th>
                      <th className="px-5 py-3 text-right">Absolute Captured Payload (moles adsorbed)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {Object.entries(results.loadings).map(([comp, val]) => (
                      <tr key={comp} className="hover:bg-slate-50/50">
                        <td className="px-5 py-3 font-medium capitalize text-slate-700">{comp}</td>
                        <td className="px-5 py-3 text-right text-slate-600 font-mono">{val.toFixed(4)}</td>
                        <td className="px-5 py-3 text-right text-slate-600 font-mono">{(results.adsorbed_moles[comp] || 0.0).toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}