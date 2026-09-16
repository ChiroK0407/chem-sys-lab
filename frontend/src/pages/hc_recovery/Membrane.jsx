import React, { useState } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { simulateMembrane } from '../../api/hcRecovery';

export default function Membrane() {
  // Unit Sizing & Operating Inputs State
  const [membrane, setMembrane] = useState("polyimide");
  const [pFeedBar, setPFeedBar] = useState(20.0);
  const [pPermBar, setPPermBar] = useState(1.2);
  const [maxArea, setMaxArea] = useState(300.0);

  // Reference purge vent stream composition blueprint configuration
  const sampleFeed = {
    flowrate_kmol_hr: 150.0,
    pressure_MPa: 2.0,
    temperature_C: 35.0,
    x_N2: 0.95,
    x_C3H6: 0.04,
    x_C3H8: 0.01
  };

  // UI Lifecycle & Network Mutation States
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleRunSimulation = async (e) => {
    e.preventDefault();
    if (parseFloat(pPermBar) >= parseFloat(pFeedBar)) {
      setErrorMsg("Transport Error: Permeate discharge pressure must be lower than feed compressor pressure.");
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    const payload = {
      feed: sampleFeed,
      membrane: membrane,
      P_feed_bar: parseFloat(pFeedBar),
      P_permeate_bar: parseFloat(pPermBar),
      area_m2: parseFloat(maxArea)
    };

    try {
      const data = await simulateMembrane(payload);
      setResults(data);
    } catch (err) {
      const detailedErr = err.response?.data?.detail;
      setErrorMsg(detailedErr?.message || "Rate-based fixed-point iteration loop failed to converge near bounds.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Polymeric Membrane Stage Simulator</h1>
        <p className="text-sm text-slate-500 mt-1">Simulate rate-based mass transfer across selective solution-diffusion skin elements.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sizing Parameters Panel Form */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded-xl p-6 shadow-sm h-fit">
          <form onSubmit={handleRunSimulation} className="space-y-5">
            <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-2">Module Configurations</h2>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Membrane Material</label>
              <select 
                value={membrane} onChange={(e) => setMembrane(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-slate-900 text-sm"
              >
                <option value="polyimide">Polyimide (High Hydrocarbon Selectivity)</option>
                <option value="cellulose_acetate">Cellulose Acetate (Robust Packing Skin)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Feed Side Compressor Pressure (bar)</label>
              <input 
                type="number" step="0.1" value={pFeedBar} onChange={(e) => setPFeedBar(e.target.value)} required
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Permeate Vacuum Pressure (bar)</label>
              <input 
                type="number" step="0.1" value={pPermBar} onChange={(e) => setPPermBar(e.target.value)} required
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Maximum Membrane Sizing Sizing Area (m²)</label>
              <input 
                type="number" step="10" value={maxArea} onChange={(e) => setMaxArea(e.target.value)} required
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
              {loading ? "Integrating Flux ODEs..." : "Execute Transport Simulation"}
            </button>
          </form>
        </div>

        {/* Presentation Data Analytics Screen Column */}
        <div className="lg:col-span-2 space-y-6">
          {!results && !loading && (
            <div className="bg-slate-50 border border-slate-200 border-dashed rounded-xl p-12 text-center text-slate-400 text-sm">
              Configure hollow fiber element geometry and run the transport solver to track recovery curves.
            </div>
          )}

          {loading && (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 text-sm shadow-sm">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-950 mx-auto mb-4"></div>
              Solving multi-component solution-diffusion driving forces...
            </div>
          )}

          {results && !loading && (
            <div className="space-y-6 animate-fade-in">
              {/* Macro Sizing Splits Metrics Overview */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Total Stage Cut Ratio (θ)</div>
                  <div className="text-2xl font-bold text-slate-800">{(results.stage_cut * 100).toFixed(2)} <span className="text-sm font-normal text-slate-500">% Flow Volumetric Split</span></div>
                </div>
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm border-l-4 border-l-indigo-500">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Integrated Hydrocarbon Recovery</div>
                  <div className="text-2xl font-bold text-indigo-600">{results.recovery_pct.toFixed(2)} <span className="text-sm font-normal text-slate-500">% Monomer Yield</span></div>
                </div>
              </div>

              {/* Recovery vs Area Graphic Chart */}
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-800 mb-4 uppercase tracking-wider text-left">Hydrocarbon Yield vs Active Membrane Area Sizing</h3>
                <div className="w-full h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={results.recovery_curve} margin={{ top: 5, right: 20, left: -15, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="area_m2" stroke="#94a3b8" fontSize={12} tickLine={false} label={{ value: 'Membrane Surface Footprint Area (m²)', position: 'insideBottom', offset: -5, fill: '#64748b', fontSize: 11 }} />
                      <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} domain={[0, 100]} label={{ value: 'Recovery Percentage (%)', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '12px' }} />
                      <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                      <Line type="monotone" dataKey="recovery_pct" name="Hydrocarbon Yield %" stroke="#4f46e5" strokeWidth={2.5} dot={false} />
                      <Line type="monotone" dataKey="stage_cut" name="Stage Cut θ Split" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Permeate Capture Stream Composition Balance Table */}
              <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50">
                  <h3 className="text-sm font-semibold text-slate-800">Permeate Discharged Output Split Balance</h3>
                </div>
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-500 tracking-wider">
                      <th className="px-5 py-3">Compound Element Species</th>
                      <th className="px-5 py-3 text-right">Permeate Stream Molar Delivery Rate (mol/s)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {Object.entries(results.permeate_composition).map(([comp, val]) => (
                      <tr key={comp} className="hover:bg-slate-50/50">
                        <td className="px-5 py-3 font-medium capitalize text-slate-700">{comp}</td>
                        <td className="px-5 py-3 text-right text-slate-600 font-mono">{val.toFixed(4)}</td>
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