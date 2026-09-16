import React, { useState, useEffect } from 'react';
import client from '../../api/client';
import ColumnInternalsPanel from './ColumnInternalsPanel';

export default function AbsorberForm({ onResult, initialData = {} }) {
  const [showOverrides, setShowOverrides] = useState(false);
  const [pairs, setPairs] = useState({});
  const [solvents, setSolvents] = useState({});
  const [solving, setSolving] = useState(false);
  const [error, setError] = useState(null);

  const [formData, setFormData] = useState({
    unit_id: initialData.unit_id || "ABS-001",
    internal_type: initialData.internal_type || "structured_packing",
    internal_key: initialData.internal_key || "MELLAPAK_250Y",
    gas_component: initialData.gas_component || "CO2",
    solvent_id: initialData.solvent_id || "water",
    y_in: initialData.y_in || 0.12,
    y_out: initialData.y_out || 0.01,
    x_in: initialData.x_in || 0.0,
    G_mol_s: initialData.G_mol_s || 100.0,
    L_G_ratio_multiplier: initialData.L_G_ratio_multiplier || 1.5,
    L_mol_s: initialData.L_mol_s || 150,
    T_C: initialData.T_C || 25.0,
    P_kPa: initialData.P_kPa || 101.325,
    column_diameter_m: initialData.column_diameter_m || 5.0,
    tray_efficiency: initialData.tray_efficiency || 0.70,
    tray_spacing_mm: initialData.tray_spacing_mm || 600,
    flood_fraction_design: initialData.flood_fraction_design || 0.75
  });

  useEffect(() => {
    // 1. Fetch Gas/Solvent pairs dynamically
    client.get('/solve/reference/absorption-pairs')
        .then(res => {
          const data = res.data;
          setPairs(data);
          if (data && Object.keys(data).length > 0) {
            if (!data[formData.gas_component]) {
              const firstAvailableGas = Object.keys(data)[0];
              setFormData(prev => ({ ...prev, gas_component: firstAvailableGas }));
            }
          }
        })
      .catch(err => console.error("Absorption pair sync breakdown:", err));

    // 2. Fetch Solvents dynamically
    client.get('/solve/reference/solvents')
      .then(res => {
        const data = res.data;
        setSolvents(data);
        if (data && Object.keys(data).length > 0) {
          if (!data[formData.solvent_id]) {
            const firstAvailableSolvent = Object.keys(data)[0];
            setFormData(prev => ({ ...prev, solvent_id: firstAvailableSolvent }));
          }
        }
      })
      .catch(err => console.error("Solvent catalog sync breakdown:", err));
  }, []);

  const handleInputChange = (field, val) => {
    setFormData(prev => ({ ...prev, [field]: val }));
  };

  const handleSolve = () => {
    setSolving(true);
    setError(null);

    console.log("Payload being sent:", formData);

    client.post('/solve/absorber', formData)
      .then(res => {
        onResult(res.data);
      })
      .catch(err => {
        setError(err.message || 'Solve failed');
      })
      .finally(() => {
        setSolving(false);
      });
  };

  const computeRemovalLive = () => {
    const { y_in, y_out } = formData;
    if (!y_in || !y_out || parseFloat(y_in) <= 0) return "0.0%";
    return (((parseFloat(y_in) - parseFloat(y_out)) / parseFloat(y_in)) * 100).toFixed(1) + "%";
  };

  const selectedPairMetadata = pairs[formData.gas_component]?.find(p => p.solvent_id === formData.solvent_id);

  return (
    <div className="max-w-5xl mx-auto space-y-8 text-slate-200">
      
      {/* Step 1: Gas-Solvent System */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Step 1 — Gas & Solvent Binary Equilibrium Interface</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 uppercase mb-2">Solute Gas Target</label>
            <select 
              value={formData.gas_component} 
              onChange={(e) => handleInputChange("gas_component", e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-slate-300 focus:outline-none text-sm"
            >
              {Object.keys(pairs).length > 0 ? (
                Object.keys(pairs).map(g => <option key={g} value={g}>{g}</option>)
              ) : (
                <option value="CO2">CO2 (Default Baseline)</option>
              )}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 uppercase mb-2">Absorbent Solvent Vehicle</label>
            <select 
              value={formData.solvent_id} 
              onChange={(e) => handleInputChange("solvent_id", e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-slate-300 focus:outline-none text-sm"
            >
              {Object.keys(solvents).length > 0 ? (
                Object.keys(solvents).map(s => <option key={s} value={s}>{s}</option>)
              ) : (
                <option value="water">water (Default Baseline)</option>
              )}
            </select>
          </div>
        </div>

        {selectedPairMetadata && (
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div>
              <span className="text-slate-500 block">{"Henry Reference H_ref"}</span>
              <span className="font-mono text-slate-300 text-sm">{selectedPairMetadata.H_ref} atm</span>
            </div>
            <div>
              <span className="text-slate-500 block">{"Heat of Solution dH_sol"}</span>
              <span className="font-mono text-amber-400 text-sm">{selectedPairMetadata.dH_sol} J/mol</span>
            </div>
            <div>
              <span className="text-slate-500 block">{"Reference Temp T_ref"}</span>
              <span className="font-mono text-slate-300 text-sm">{selectedPairMetadata.T_ref} K</span>
            </div>
          </div>
        )}
      </div>

      {/* Step 2: Column Internals Panel */}
      <ColumnInternalsPanel 
        title="Step 2 — Column Hardware Internals"
        value={{ internal_type: formData.internal_type, internal_key: formData.internal_key }}
        onChange={(updated) => {
          handleInputChange("internal_type", updated.internal_type);
          handleInputChange("internal_key", updated.internal_key);
        }}
      />

      {/* Step 3: Process Conditions */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4 flex justify-between items-center">
          <span>Step 3 — Process Boundary Conditions</span>
          <span className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded text-xs font-bold font-mono">
            Live Removal Target: {computeRemovalLive()}
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">{"Inlet Gas Solute fraction (y_in)"}</label>
            <input type="number" step="0.001" value={formData.y_in} onChange={(e) => handleInputChange("y_in", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{"Outlet Gas Target (y_out)"}</label>
            <input type="number" step="0.001" value={formData.y_out} onChange={(e) => handleInputChange("y_out", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{"Lean Liquid Fraction (x_in)"}</label>
            <input type="number" step="0.001" value={formData.x_in} onChange={(e) => handleInputChange("x_in", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{"Gas Molar Velocity (G)"}</label>
            <input type="number" value={formData.G_mol_s} onChange={(e) => handleInputChange("G_mol_s", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{"Solvent Rate (L mol/s)"}</label>
            <input type="number" placeholder="Auto (Calculate Min)" value={formData.L_mol_s} onChange={(e) => handleInputChange("L_mol_s", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{"L/G_min Multiplier"}</label>
            <input type="number" step="0.1" value={formData.L_G_ratio_multiplier} onChange={(e) => handleInputChange("L_G_ratio_multiplier", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Temperature (°C)</label>
            <input type="number" value={formData.T_C} onChange={(e) => handleInputChange("T_C", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Pressure (kPa)</label>
            <input type="number" value={formData.P_kPa} onChange={(e) => handleInputChange("P_kPa", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
        </div>
      </div>

      {/* Step 4: Geometry Overrides (Collapsible) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <button 
          type="button"
          onClick={() => setShowOverrides(!showOverrides)}
          className="w-full flex justify-between items-center px-6 py-4 bg-slate-950/40 text-xs font-semibold text-slate-400 uppercase tracking-wider focus:outline-none"
        >
          <span>Step 4 — Column Physical Geometry Overrides</span>
          <span>{showOverrides ? "Hide ▲" : "Show ▼"}</span>
        </button>

        {showOverrides && (
          <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4 border-t border-slate-800 bg-slate-900/50">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Column Diameter Override [m]</label>
              <input type="number" step="0.1" placeholder="Auto" value={formData.column_diameter_m} onChange={(e) => handleInputChange("column_diameter_m", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none text-slate-300" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Tray Efficiency Fraction</label>
              <input type="number" step="0.05" value={formData.tray_efficiency} onChange={(e) => handleInputChange("tray_efficiency", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none text-slate-300" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Tray Plate Spacing [mm]</label>
              <input type="number" value={formData.tray_spacing_mm} onChange={(e) => handleInputChange("tray_spacing_mm", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none text-slate-300" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Design Flood Loading Fraction</label>
              <input type="number" step="0.05" value={formData.flood_fraction_design} onChange={(e) => handleInputChange("flood_fraction_design", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none text-slate-300" />
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-col items-end gap-2 pt-2">
        <button 
          onClick={handleSolve}
          disabled={solving}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold px-8 py-3 rounded-lg shadow-lg hover:shadow-emerald-500/20 transition-all text-sm"
        >
          {solving ? 'Solving...' : 'Execute Absorber Sizing Solve'}
        </button>
        {error && (
          <p className="text-red-400 text-xs">{error}</p>
        )}
      </div>

    </div>
  );
}