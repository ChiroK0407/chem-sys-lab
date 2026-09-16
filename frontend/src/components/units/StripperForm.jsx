import React, { useState, useEffect } from 'react';
import client from '../../api/client';
import ColumnInternalsPanel from './ColumnInternalsPanel';

export default function StripperForm({ onResult, initialData = {} }) {
  const [showOverrides, setShowOverrides] = useState(false);
  const [pairs, setPairs] = useState({});
  const [solvents, setSolvents] = useState({});
  const [solving, setSolving] = useState(false);
  const [error, setError] = useState(null);

  const [formData, setFormData] = useState({
    unit_id: initialData.unit_id || "STR-001",
    internal_type: initialData.internal_type || "structured_packing",
    internal_key: initialData.internal_key || "MELLAPAK_250Y",
    gas_component: initialData.gas_component || "CO2",
    solvent_id: initialData.solvent_id || "MEA_30wt%",
    x_in: initialData.x_in || 0.05,
    x_out: initialData.x_out || 0.005,
    y_in: initialData.y_in || 0.0,
    L_mol_s: initialData.L_mol_s || 150.0,
    G_mol_s: initialData.G_mol_s || "",
    L_G_ratio_multiplier: initialData.L_G_ratio_multiplier || 1.5,
    stripping_agent: initialData.stripping_agent || "steam",
    T_C: initialData.T_C || 120.0, // Elevated baseline for solvent boiling/stripping
    P_kPa: initialData.P_kPa || 101.325,
    column_diameter_m: initialData.column_diameter_m || "",
    tray_efficiency: initialData.tray_efficiency || 0.70,
    tray_spacing_mm: initialData.tray_spacing_mm || 600,
    flood_fraction_design: initialData.flood_fraction_design || 0.75
  });

  useEffect(() => {
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
      .catch(() => {});

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

    client.post('/solve/stripper', formData)
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

  return (
    <div className="max-w-5xl mx-auto space-y-8 text-slate-200">
      
      {/* Step 1: Desorption Mass Balance Pairing */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Step 1 — Desorption Mass Balance Pairing</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 uppercase mb-2">Gas Matrix Component</label>
            <select value={formData.gas_component} onChange={(e) => handleInputChange("gas_component", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-slate-300 focus:outline-none text-sm">
              {Object.keys(pairs).length > 0 ? (
                Object.keys(pairs).map(g => <option key={g} value={g}>{g}</option>)
              ) : (
                <option value="CO2">CO2</option>
              )}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 uppercase mb-2">Rich Absorbent Solvent Pool</label>
            <select value={formData.solvent_id} onChange={(e) => handleInputChange("solvent_id", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-slate-300 focus:outline-none text-sm">
              {Object.keys(solvents).length > 0 ? (
                Object.keys(solvents).map(s => <option key={s} value={s}>{s}</option>)
              ) : (
                <option value="MEA_30wt%">MEA_30wt%</option>
              )}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 uppercase mb-2">Vapor Stripping Carrier Medium</label>
            <select value={formData.stripping_agent} onChange={(e) => handleInputChange("stripping_agent", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-slate-300 focus:outline-none text-sm">
              <option value="steam">Live Saturated Steam</option>
              <option value="air">Stripping Air Medium</option>
              <option value="nitrogen">{"Inert Nitrogen (N_2)"}</option>
              <option value="inert_gas">Generic Inert Matrix</option>
            </select>
          </div>
        </div>
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
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Step 3 — Thermal Desorption Boundaries</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">{"Rich Inlet Liquid (x_in)"}</label>
            <input type="number" step="0.001" value={formData.x_in} onChange={(e) => handleInputChange("x_in", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{"Lean Target Outlet (x_out)"}</label>
            <input type="number" step="0.001" value={formData.x_out} onChange={(e) => handleInputChange("x_out", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{"Inlet Gas Contamination (y_in)"}</label>
            <input type="number" step="0.001" value={formData.y_in} onChange={(e) => handleInputChange("y_in", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{"Liquid Molar Rate (L mol/s)"}</label>
            <input type="number" value={formData.L_mol_s} onChange={(e) => handleInputChange("L_mol_s", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">{"Stripping Gas (G mol/s)"}</label>
            <input type="number" placeholder="Auto (Calculate Min)" value={formData.G_mol_s} onChange={(e) => handleInputChange("G_mol_s", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Design Multiplier Factor</label>
            <input type="number" step="0.1" value={formData.L_G_ratio_multiplier} onChange={(e) => handleInputChange("L_G_ratio_multiplier", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Stripping Temp (°C)</label>
            <input type="number" value={formData.T_C} onChange={(e) => handleInputChange("T_C", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Stripping Pressure (kPa)</label>
            <input type="number" value={formData.P_kPa} onChange={(e) => handleInputChange("P_kPa", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500 text-slate-300" />
          </div>
        </div>
      </div>

      {/* Step 4: Mechanical Geometry Overrides */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <button type="button" onClick={() => setShowOverrides(!showOverrides)} className="w-full flex justify-between items-center px-6 py-4 bg-slate-950/40 text-xs font-semibold text-slate-400 uppercase tracking-wider focus:outline-none">
          <span>Step 4 — Sizing Geometry Overrides</span>
          <span>{showOverrides ? "Hide ▲" : "Show ▼"}</span>
        </button>

        {showOverrides && (
          <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-900/50 border-t border-slate-800">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Diameter Override [m]</label>
              <input type="number" step="0.1" placeholder="Auto" value={formData.column_diameter_m} onChange={(e) => handleInputChange("column_diameter_m", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none text-slate-300" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Tray Efficiency</label>
              <input type="number" step="0.05" value={formData.tray_efficiency} onChange={(e) => handleInputChange("tray_efficiency", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none text-slate-300" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Tray Plate Spacing [mm]</label>
              <input type="number" value={formData.tray_spacing_mm} onChange={(e) => handleInputChange("tray_spacing_mm", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none text-slate-300" />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Flood Margin Target</label>
              <input type="number" step="0.05" value={formData.flood_fraction_design} onChange={(e) => handleInputChange("flood_fraction_design", e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs focus:outline-none text-slate-300" />
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-col items-end gap-2 pt-2">
        <button onClick={handleSolve} disabled={solving} className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold px-8 py-3 rounded-lg shadow-lg text-sm">
          {solving ? 'Solving...' : 'Run Solvent Regenerator Simulation'}
        </button>
        {error && (
          <p className="text-red-400 text-xs">{error}</p>
        )}
      </div>

    </div>
  );
}