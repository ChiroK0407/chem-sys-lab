import React, { useState } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { simulateCondensation } from '../../api/hcRecovery';

export default function Condensation() {
  // Simulator Input Parameters
  const [pressureBar, setPressureBar] = useState(15.0);
  const [tMinC, setTMinC] = useState(-80.0);
  const [tMaxC, setTMaxC] = useState(20.0);

  // Parent State Fallback for the validated context stream
  // In a real integrated layout, this passes down out of a shared Context provider or parent Stream ledger
  const sampleFeed = {
    flowrate_kmol_hr: 150.0,
    pressure_MPa: 1.5,
    temperature_C: 35.0,
    x_N2: 0.95,
    x_C3H6: 0.04,
    x_C3H8: 0.01
  };

  // State Management For Calculation Lifecycles
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleRunSimulation = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);

    const payload = {
      feed: sampleFeed,
      T_min_C: parseFloat(tMinC),
      T_max_C: parseFloat(tMaxC),
      P_bar: parseFloat(pressureBar)
    };

    try {
      const data = await simulateCondensation(payload);
      setResults(data);
    } catch (err) {
      const detailedErr = err.response?.data?.detail;
      setErrorMsg(detailedErr?.message || "Thermodynamic flash convergence failure inside bounded Brent solver.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Cryogenic Condensation Simulator</h1>
        <p className="text-sm text-slate-500 mt-1">Simulate multi-component vapor-liquid equilibrium (VLE) loops to optimize heavy monomer capture sweeps.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input Parameters Card */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded-xl p-6 shadow-sm h-fit">
          <form onSubmit={handleRunSimulation} className="space-y-5">
            <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-2">Unit Sizing Parameters</h2>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Column Pressure (bar)</label>
              <input 
                type="number" step="0.1" value={pressureBar} onChange={(e) => setPressureBar(e.target.value)} required
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Minimum Temperature Sweep (°C)</label>
              <input 
                type="number" step="1" min="-100" max="100" value={tMinC} onChange={(e) => setTMinC(e.target.value)} required
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900 text-sm"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">Thermodynamic validity limit: &ge; -100°C</span>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Maximum Temperature Sweep (°C)</label>
              <input 
                type="number" step="1" min="-100" max="100" value={tMaxC} onChange={(e) => setTMaxC(e.target.value)} required
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
              {loading ? "Solving Flash Loops..." : "Execute Thermodynamic Sweep"}
            </button>
          </form>
        </div>

        {/* Dynamic Analytics & Graphics Panel */}
        <div className="lg:col-span-2 space-y-6">
          {!results && !loading && (
            <div className="bg-slate-50 border border-slate-200 border-dashed rounded-xl p-12 text-center text-slate-400 text-sm">
              Configure chiller bounds and execute calculation loops to plot VLE recovery curves.
            </div>
          )}

          {loading && (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 text-sm shadow-sm">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-950 mx-auto mb-4"></div>
              Iterating Rachford-Rice residuals...
            </div>
          )}

          {results && !loading && (
            <div className="space-y-6 animate-fade-in">
              {/* Summary Performance Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm border-l-4 border-l-cyan-500">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Optimal Separation Target</div>
                  <div className="text-2xl font-bold text-slate-800">{results.optimal_T_C.toFixed(1)} <span className="text-sm font-normal text-slate-500">°C</span></div>
                </div>
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Maximum Hydrocarbon Recovery</div>
                  <div className="text-2xl font-bold text-emerald-600">{results.max_recovery_pct.toFixed(2)} <span className="text-sm font-normal text-slate-500">%</span></div>
                </div>
              </div>

              {/* Chart Component Panel */}
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-800 mb-4 uppercase tracking-wider text-left">Hydrocarbon Recovery vs Chiller Temperature</h3>
                <div className="w-full h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={results.recovery_curve} margin={{ top: 5, right: 20, left: -15, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="T_C" stroke="#94a3b8" fontSize={12} tickLine={false} label={{ value: 'Temperature (°C)', position: 'insideBottom', offset: -5, fill: '#64748b', fontSize: 11 }} />
                      <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} domain={[0, 100]} label={{ value: 'Recovery (%)', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', fontSize: '12px' }} />
                      <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                      <Line type="monotone" dataKey="recovery_pct" name="Hydrocarbon Recovery" stroke="#0f172a" strokeWidth={2.5} dot={false} activeDot={{ r: 6 }} />
                      <Line type="monotone" dataKey="vapor_fraction" name="Phase Split Split (V)" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}