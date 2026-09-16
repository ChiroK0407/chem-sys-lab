import React from 'react';
import { NavLink } from 'react-router-dom';

export default function HCRecoveryHome() {
  const modules = [
    {
      title: "Feed Characterization",
      description: "Analyze purge vent compositions, balance molar flows, and quantify baseline raw monomer losses to flare.",
      path: "/hc-recovery/feed",
      icon: "📊"
    },
    {
      title: "Cryogenic Condensation",
      description: "Simulate vapor-liquid equilibrium (VLE) loops using Antoine equations to find optimal refrigeration thresholds.",
      path: "/hc-recovery/condensation",
      icon: "❄️"
    },
    {
      title: "Fixed-Bed Adsorption",
      description: "Evaluate multi-component competitive bed loadings using Extended Langmuir affinity parameters.",
      path: "/hc-recovery/adsorption",
      icon: "🪨"
    },
    {
      title: "Polymeric Membrane",
      description: "Model solution-diffusion transport flux rates and stage cuts across specialized high-selectivity skins.",
      path: "/hc-recovery/membrane",
      icon: "🕸️"
    }
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Hydrocarbon Recovery Assessment Platform</h1>
        <p className="mt-2 text-sm text-slate-500 max-w-3xl">
          Evaluate and optimize downstream separation units for a nitrogen-rich polypropylene plant purge gas stream 
          to reduce environmental emissions and recover valuable monomer payloads.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {modules.map((mod) => (
          <div key={mod.path} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-3 mb-4">
                <span className="text-3xl bg-slate-50 p-2 rounded-lg border border-slate-100">{mod.icon}</span>
                <h2 className="text-xl font-semibold text-slate-800">{mod.title}</h2>
              </div>
              <p className="text-sm text-slate-600 leading-relaxed mb-6">{mod.description}</p>
            </div>
            
            <NavLink
              to={mod.path}
              className="w-full text-center inline-flex justify-center items-center px-4 py-2.5 bg-slate-900 text-white text-sm font-medium rounded-lg hover:bg-slate-800 transition-colors"
            >
              Configure Simulator &rarr;
            </NavLink>
          </div>
        ))}
      </div>
    </div>
  );
}