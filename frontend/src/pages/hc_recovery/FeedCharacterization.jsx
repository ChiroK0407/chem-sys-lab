import React, { useState } from 'react';
import { characterizeFeed } from '../../api/hcRecovery';

export default function FeedCharacterization() {
  const [flowrate, setFlowrate] = useState(150.0);
  const [pressure, setPressure] = useState(0.8);
  const [temperature, setTemperature] = useState(35.0);

  const [pctN2, setPctN2] = useState(95.0);
  const [pctC3H6, setPctC3H6] = useState(4.0);
  const [pctC3H8, setPctC3H8] = useState(1.0);

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const compSum = parseFloat(pctN2) + parseFloat(pctC3H6) + parseFloat(pctC3H8);
  const isSumValid = Math.abs(compSum - 100.0) < 0.01;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isSumValid) {
      setErrorMsg("Cannot execute simulation: Stream compositions must sum to exactly 100%.");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setResults(null); // Clear old data to force fresh redraw frames

    const payload = {
      flowrate_kmol_hr: parseFloat(flowrate),
      pressure_MPa: parseFloat(pressure),
      temperature_C: parseFloat(temperature),
      x_N2: parseFloat(pctN2) / 100.0,
      x_C3H6: parseFloat(pctC3H6) / 100.0,
      x_C3H8: parseFloat(pctC3H8) / 100.0
    };

    try {
      const data = await characterizeFeed(payload);
      setResults(data);
    } catch (err) {
      console.error("Full Full-Stack Connection Catch:", err);
      const data = err.response?.data;
      if (data?.detail && Array.isArray(data.detail)) {
        setErrorMsg(data.detail[0]?.msg || "Pydantic constraint error.");
      } else if (data?.detail?.message) {
        setErrorMsg(data.detail.message);
      } else {
        setErrorMsg("Failed to communicate with first-principles backend engine calculations.");
      }
    } finally {
      // CRITICAL: Guarantees loading spinner is stripped off screen regardless of calculation outcomes!
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Feed Stream Characterization</h1>
        <p className="text-sm text-slate-500 mt-1">Specify header process states and analyze current losses sent to flare.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form Controls */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded-xl p-6 shadow-sm h-fit">
          <form onSubmit={handleSubmit} className="space-y-6">
            <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider border-b border-slate-100 pb-2">Stream Conditions</h2>
            
            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Total Flowrate (kmol/hr)</label>
              <input 
                type="number" step="0.1" value={flowrate} onChange={(e) => setFlowrate(e.target.value)} required
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Pressure (MPa)</label>
              <input 
                type="number" step="0.01" value={pressure} onChange={(e) => setPressure(e.target.value)} required
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 uppercase tracking-wider mb-1">Temperature (°C)</label>
              <input 
                type="number" step="0.1" value={temperature} onChange={(e) => setTemperature(e.target.value)} required
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-slate-900 text-sm"
              />
            </div>

            <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wider border-b border-slate-100 pt-2 pb-2">Compositions (mol %)</h2>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-medium text-slate-700">Nitrogen (N₂)</span>
                  <span className="text-slate-500">{pctN2}%</span>
                </div>
                <input type="range" min="0" max="100" step="0.1" value={pctN2} onChange={(e) => setPctN2(e.target.value)} className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-900" />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-medium text-slate-700">Propylene (C₃H₆)</span>
                  <span className="text-slate-500">{pctC3H6}%</span>
                </div>
                <input type="range" min="0" max="100" step="0.1" value={pctC3H6} onChange={(e) => setPctC3H6(e.target.value)} className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-900" />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-medium text-slate-700">Propane (C₃H₈)</span>
                  <span className="text-slate-500">{pctC3H8}%</span>
                </div>
                <input type="range" min="0" max="100" step="0.1" value={pctC3H8} onChange={(e) => setPctC3H8(e.target.value)} className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-900" />
              </div>
            </div>

            <div className={`p-3 rounded-lg border text-sm flex justify-between ${isSumValid ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-rose-50 border-rose-200 text-rose-800'}`}>
              <span className="font-medium">Total Mixture Sum:</span>
              <span className="font-bold">{compSum.toFixed(2)}%</span>
            </div>

            {errorMsg && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 leading-normal">
                {errorMsg}
              </div>
            )}

            <button
              type="submit" disabled={loading || !isSumValid}
              className="w-full py-2.5 px-4 bg-slate-900 text-white rounded-md text-sm font-medium hover:bg-slate-800 disabled:opacity-50 transition-colors"
            >
              {loading ? "Characterizing..." : "Run Characterization"}
            </button>
          </form>
        </div>

        {/* Results Screen */}
        <div className="lg:col-span-2 space-y-6">
          {!results && !loading && (
            <div className="bg-slate-50 border border-slate-200 border-dashed rounded-xl p-12 text-center text-slate-400 text-sm">
              Enter valid stream boundaries and execute solver calculations to analyze system data.
            </div>
          )}

          {loading && (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 text-sm shadow-sm">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-950 mx-auto mb-4"></div>
              Evaluating thermodynamic stream vectors...
            </div>
          )}

          {results && !loading && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Monomer Concentration</div>
                  <div className="text-2xl font-bold text-slate-800">{results.hc_content_mol_pct?.toFixed(2)} <span className="text-sm font-normal text-slate-500">mol%</span></div>
                </div>
                <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm border-l-4 border-l-rose-500">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Annual Flared Loss Baseline</div>
                  <div className="text-2xl font-bold text-rose-600">{results.annual_hc_loss_tonnes_yr?.toFixed(1)} <span className="text-sm font-normal text-slate-500">tonnes/yr</span></div>
                </div>
              </div>

              {results.molar_flowrates && (
                <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                  <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50">
                    <h3 className="text-sm font-semibold text-slate-800">Molar Flow Partition Balance</h3>
                  </div>
                  <table className="w-full text-left text-sm border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-500 tracking-wider">
                        <th className="px-5 py-3">Component Identifier</th>
                        <th className="px-5 py-3 text-right">Molar Flowrate (kmol/hr)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {Object.entries(results.molar_flowrates).map(([comp, val]) => (
                        <tr key={comp} className="hover:bg-slate-50/50">
                          <td className="px-5 py-3 font-medium capitalize text-slate-700">{comp}</td>
                          <td className="px-5 py-3 text-right text-slate-600 font-mono">{typeof val === 'number' ? val.toFixed(3) : val}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}