/**
 * frontend/src/components/units/HXTypeSelector.jsx
 * * Provides an industrial-grade mechanical design template selector driven by useHXTypes.
 * Displays pressure-temperature envelopes, fluid phase permissions, and application badges 
 * before firing macro-typing parameters back up to the parent engineering form grid.
 */

import React from "react";
import { useHXTypes } from "../../hooks/useHXTypes";
import { Shield, Layers, CheckCircle2, AlertTriangle } from "lucide-react";

export default function HXTypeSelector({ value, onChange }) {
  const { data: hxTypes, isLoading, isError, error } = useHXTypes();

  // Extract currently active record from list catalog matrix to populate detail panel
  const activePreset = React.useMemo(() => {
    if (!hxTypes || !value || !Array.isArray(hxTypes)) return null;
    return hxTypes.find((item) => item.key === value) || null;
  }, [hxTypes, value]);

  const handleDropdownChange = (e) => {
    const selectedKey = e.target.value;
    if (selectedKey === "manual") {
      onChange(null);
      return;
    }

    if (!Array.isArray(hxTypes)) return;

    const targetRecord = hxTypes.find((item) => item.key === selectedKey);
    if (targetRecord) {
      // Dispatches complete boundary payload enabling automated macro calculations
      onChange({
        key: targetRecord.key,
        typical_u_mid: targetRecord.typical_u_mid,
        typical_u_min: targetRecord.typical_u_min,
        typical_u_max: targetRecord.typical_u_max,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-3 bg-slate-800 border border-slate-700 rounded-lg text-slate-400 text-sm">
        <Layers size={16} className="animate-spin text-blue-500" />
        <span>Syncing industrial mechanical equipment database...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 p-3 bg-red-950/40 border border-red-800 rounded-lg text-red-400 text-sm">
        <AlertTriangle size={16} />
        <span>Failed to sync equipment presets: {error?.message || "Internal Protocol Error"}</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Dropdown Container Element */}
      <div>
        <label className="label block text-xs font-semibold text-slate-400 mb-1 tracking-wide uppercase">
          TEMA Class / Mechanical Standard Template
        </label>
        <select
          className="select w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-lg p-2.5 text-sm font-medium focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all outline-none"
          value={value || "manual"}
          onChange={handleDropdownChange}
        >
          <option value="manual">— select type —</option>
          {/* Strict array check guard protects the render channel from breaking if response is malformed */}
          {Array.isArray(hxTypes) && hxTypes.map((type) => (
            <option key={type.key} value={type.key}>
              {type.extended_name}
            </option>
          ))}
        </select>
      </div>

      {/* Feature Specification Detail Panel Area */}
      {activePreset && (
        <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4 space-y-4 animate-fadeIn">
          
          {/* Row of 3 Engineering Design Metric Cards */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-center">
              <span className="block text-[10px] font-bold text-slate-500 tracking-wider uppercase mb-1">U Range</span>
              <span className="text-sm font-mono font-bold text-blue-400">
                {activePreset.typical_u_min}–{activePreset.typical_u_max}
              </span>
              <span className="block text-[9px] text-slate-400 mt-0.5 font-sans">W/(m²·K)</span>
            </div>
            
            <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-center">
              <span className="block text-[10px] font-bold text-slate-500 tracking-wider uppercase mb-1">Max Pressure</span>
              <span className="text-sm font-mono font-bold text-emerald-400">
                {activePreset.max_design_pressure_bar || activePreset.max_pressure_bar}
              </span>
              <span className="block text-[9px] text-slate-400 mt-0.5 font-sans">bar abs</span>
            </div>

            <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-center">
              <span className="block text-[10px] font-bold text-slate-500 tracking-wider uppercase mb-1">Max Temp</span>
              <span className="text-sm font-mono font-bold text-orange-400">
                {activePreset.max_design_temp_c || activePreset.max_temp_c}°
              </span>
              <span className="block text-[9px] text-slate-400 mt-0.5 font-sans">Celsius</span>
            </div>
          </div>

          {/* Core Optimization Suitability & Boundaries Matrices */}
          <div className="space-y-2.5 pt-1">
            {/* Best For / Recommended Applications */}
            {activePreset.best_for && activePreset.best_for.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs font-semibold text-slate-400 w-28 shrink-0">Optimal For:</span>
                <div className="flex flex-wrap gap-1">
                  {activePreset.best_for.map((item, idx) => (
                    <span key={idx} className="badge-green bg-emerald-950/50 text-emerald-400 text-[11px] px-2 py-0.5 rounded border border-emerald-900 font-medium">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Not Suitable For / Risk Matrices */}
            {activePreset.not_suitable_for && activePreset.not_suitable_for.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs font-semibold text-slate-400 w-28 shrink-0">Design Hazards:</span>
                <div className="flex flex-wrap gap-1">
                  {activePreset.not_suitable_for.map((item, idx) => (
                    <span key={idx} className="badge-amber bg-amber-950/40 text-amber-400 text-[11px] px-2 py-0.5 rounded border border-amber-900 font-medium">
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Fluid Phase Equilibrium Hint Strip */}
          <div className="flex items-center gap-2 pt-3 border-t border-slate-900 text-xs">
            {activePreset.allows_phase_change ? (
              <div className="flex items-center gap-1.5 text-cyan-400 bg-cyan-950/30 px-2 py-1 rounded w-full border border-cyan-900/50">
                <CheckCircle2 size={13} />
                <span><strong>Phase Change Allowed:</strong> Validated for Kettle boiling pool and condenser thermodynamic vapor fraction profiles.</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-slate-400 bg-slate-900/60 px-2 py-1 rounded w-full border border-slate-800">
                <Shield size={13} className="text-slate-500" />
                <span><strong>Single-Phase Only:</strong> Restricted strictly to liquid/gas sensible heat profiles. Condensation loops throw limits.</span>
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}