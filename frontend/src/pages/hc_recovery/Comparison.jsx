import React, { useState } from 'react';
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Tooltip, Legend } from 'recharts';
import { compareTechnologies } from '../../api/hcRecovery';

export default function Comparison() {
  // Comprehensive Unified Sizing Parameters States
  const [condTC, setCondTC] = useState(-45.0);
  const [condPBar, setCondPBar] = useState(18.0);
  const [adsPBar, setAdsPBar] = useState(9.0);
  const [adsMass, setAdsMass] = useState(1500.0);
  const [membArea, setMembArea] = useState(250.0);
  const [membPFeed, setMembPFeed] = useState(22.0);
  const [membPPerm, setMembPPerm] = useState(1.1);

  // Fixed core feedstock parameters matrix
  const sampleFeed = {
    flowrate_kmol_hr: 150.0,
    pressure_MPa: 1.2,
    temperature_C: 35.0,
    x_N2: 0.95,
    x_C3H6: 0.04,
    x_C3H8: 0.01
  };

  // Evaluation States
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleRunComparison = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);

    const payload = {
      feed: sampleFeed,
      condensation_T_C: parseFloat(condTC),
      condensation_P_bar: parseFloat(condPBar),
      adsorption_pressure_bar: parseFloat(adsPBar),
      adsorption_mass_kg: parseFloat(adsMass),
      membrane_area_m2: parseFloat(membArea),
      membrane_P_feed_bar: parseFloat(membPFeed),
      membrane_P_permeate_bar: parseFloat(membPPerm)
    };

    try {
      const data = await compareTechnologies(payload);
      setResults(data);
    } catch (err) {
      setErrorMsg("An unexpected validation conflict occurred within the combined evaluation routing block.");
    } finally {
      setLoading(false);
    }
  };

  // Re-map localized technology flat objects to axis array vectors for Radar widget consumption
  const formatRadarData = (techList) => {
    if (!techList) return [];
    const metrics = [
      { key: "recovery_score", label: "Monomer Recovery Efficiency" },
      { key: "energy_score", label: "Utility Sizing (Lower Penalty)" },
      { key: "complexity_score", label: "Operational Simplicity" },
      { key: "capital_score", label: "Asset CAPEX Index" },
      { key: "operating_score", label: "Bed Replacement OPEX Index" }
    ];

    return metrics.map((m) => {
      const row = { subject: m.label };
      techList.forEach((tech) => {
        // Yield recovery score maps out of normalized bounds [0-10] derived from raw percentage values
        if (m.key === "recovery_score") {
          row[tech.name] = parseFloat((tech.recovery_pct / 10).toFixed(2));
        } else {
          row[tech.name] = tech[m.key];
        }
      });
      return row;
    });
  };

  const radarChartData = results ? formatRadarData(results.technologies) : [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Multi-Technology Strategic Assessment Matrix</h1>
        <p className="text-sm text-slate-500 mt-1">Simulate and evaluate competing hydrocarbon recovery stacks using cross-attribute radar models.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sizing Controls Column Grid Form */}
        <div className="lg:col-span-1 bg-white border border-slate-200 rounded-xl p-6 shadow-sm h-fit max-h-[80vh] overflow-y-auto space-y-6">
          <form onSubmit={handleRunComparison} className="space-y-6">
            
            {/* Sec A: Condenser */}
            <div>
              <h3 className="text-xs font-bold text-cyan-600 uppercase tracking-wider border-b border-cyan-100 pb-1 mb-3">1. Cryogenic Chiller Parameters</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">Target Temp (°C)</label>
                  <input type="number" step="0.5" value={condTC} onChange={(e) => setCondTC(e.target.value)} required className="w-full px-2 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-slate-900" />
                </div>
                <div>
                  <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">Pressure (bar)</label>
                  <input type="number" step="0.1" value={condPBar} onChange={(e) => setCondPBar(e.target.value)} required className="w-full px-2 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-slate-900" />
                </div>
              </div>
            </div>

            {/* Sec B: Adsorber */}
            <div>
              <h3 className="text-xs font-bold text-emerald-600 uppercase tracking-wider border-b border-emerald-100 pb-1 mb-3">2. Adsorption Bed Parameters</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">Pressure (bar)</label>
                  <input type="number" step="0.1" value={adsPBar} onChange={(e) => setAdsPBar(e.target.value)} required className="w-full px-2 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-slate-900" />
                </div>
                <div>
                  <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">Bed Mass (kg)</label>
                  <input type="number" step="10" value={adsMass} onChange={(e) => setAdsMass(e.target.value)} required className="w-full px-2 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-slate-900" />
                </div>
              </div>
            </div>

            {/* Sec C: Membranes */}
            <div>
              <h3 className="text-xs font-bold text-indigo-600 uppercase tracking-wider border-b border-indigo-100 pb-1 mb-3">3. Membrane Skin Parameters</h3>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">Active Area (m²)</label>
                    <input type="number" step="5" value={membArea} onChange={(e) => setMembArea(e.target.value)} required className="w-full px-2 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-slate-900" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">P-Feed (bar)</label>
                    <input type="number" step="0.1" value={membPFeed} onChange={(e) => setMembPFeed(e.target.value)} required className="w-full px-2 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-slate-900" />
                  </div>
                </div>
                <div>
                  <label className="block text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">P-Permeate Vacuum (bar)</label>
                  <input type="number" step="0.05" value={membPPerm} onChange={(e) => setMembPPerm(e.target.value)} required className="w-full px-2 py-1 border border-slate-300 rounded text-sm focus:outline-none focus:ring-slate-900" />
                </div>
              </div>
            </div>

            {errorMsg && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-md text-xs text-rose-700">
                {errorMsg}
              </div>
            )}

            <button
              type="submit" disabled={loading}
              className="w-full py-2.5 bg-slate-950 text-white rounded-md text-sm font-medium hover:bg-slate-800 disabled:opacity-50 transition-colors"
            >
              {loading ? "Synthesizing Core Engines..." : "Run Attribute Assessment Matrix"}
            </button>
          </form>
        </div>

        {/* Presentation Graphics Panel Display */}
        <div className="lg:col-span-2 space-y-6">
          {!results && !loading && (
            <div className="bg-slate-50 border border-slate-200 border-dashed rounded-xl p-12 text-center text-slate-400 text-sm">
              Execute cross-simulations to overlay normalized strategic metric scores on the radar map.
            </div>
          )}

          {loading && (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 text-sm shadow-sm">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-950 mx-auto mb-4"></div>
              Evaluating capital indexes, utility penalties, and recovery margins simultaneously...
            </div>
          )}

          {results && !loading && (
            <div className="space-y-6 animate-fade-in">
              
              {/* Strategic Radar Diagram Visual Chart */}
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-800 mb-2 uppercase tracking-wider text-left">Multi-Attribute Comparison Profile</h3>
                <div className="w-full h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarChartData}>
                      <PolarGrid stroke="#e2e8f0" />
                      <PolarAngleAxis dataKey="subject" stroke="#64748b" fontSize={11} />
                      <PolarRadiusAxis angle={30} domain={[0, 10]} stroke="#cbd5e1" fontSize={10} />
                      <Radar name="Cryogenic Condensation" dataKey="Cryogenic Condensation" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.15} />
                      <Radar name="Fixed-Bed Adsorption" dataKey="Fixed-Bed Adsorption" stroke="#10b981" fill="#10b981" fillOpacity={0.15} />
                      <Radar name="Polymeric Membrane" dataKey="Polymeric Membrane" stroke="#6366f1" fill="#6366f1" fillOpacity={0.15} />
                      <Tooltip contentStyle={{ fontSize: '12px', borderRadius: '6px' }} />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Comprehensive Summary Comparison Matrix Table Grid */}
              <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50">
                  <h3 className="text-sm font-semibold text-slate-800">Normalized Technical Index Ledger</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm border-collapse min-w-[500px]">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-bold uppercase text-slate-500 tracking-wider">
                        <th className="px-4 py-3">Separation Technology Stack</th>
                        <th className="px-4 py-3 text-right">Raw Yield Recovery %</th>
                        <th className="px-4 py-3 text-right">Utility Utility Index</th>
                        <th className="px-4 py-3 text-right">Simplicity Index</th>
                        <th className="px-4 py-3 text-right">CAPEX Score</th>
                        <th className="px-4 py-3 text-right">OPEX Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-600">
                      {results.technologies.map((tech) => (
                        <tr key={tech.name} className="hover:bg-slate-50/50">
                          <td className="px-4 py-3 font-semibold text-slate-800 text-xs">{tech.name}</td>
                          <td className="px-4 py-3 text-right font-bold text-slate-900">{tech.recovery_pct.toFixed(2)}%</td>
                          <td className="px-4 py-3 text-right font-mono">{tech.energy_score.toFixed(1)}/10</td>
                          <td className="px-4 py-3 text-right font-mono">{tech.complexity_score.toFixed(1)}/10</td>
                          <td className="px-4 py-3 text-right font-mono">{tech.capital_score.toFixed(1)}/10</td>
                          <td className="px-4 py-3 text-right font-mono">{tech.operating_score.toFixed(1)}/10</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}