/**
 * frontend/src/components/units/HXSchematics.jsx
 * * Frontend isolated engineering schematics layer for chemsyslab.
 * Houses the pure vector SVG temperature profile pathing canvas and the 
 * twin-channel hydraulic gauge monitoring TEMA velocity/friction rules.
 */

import React from "react";
import { Activity, ShieldAlert, Thermometer, Wind } from "lucide-react";

export function HXTemperatureProfile({ result }) {
  if (!result) return null;

  // 1. DYNAMIC PROPERTY EXTRACTION
  // Maps variables directly using standard data-contract patterns
  const Th_in  = result.hot_inlet_T_c  ?? result.hot_stream?.temperature_c ?? 140;
  const Th_out = result.hot_outlet_T_c ?? result.hot_stream?.temperature_c ?? 140;
  
  const Tc_in  = result.cold_inlet_T_c  ?? result.cold_stream?.temperature_c ?? 25;
  const Tc_out = result.cold_outlet_T_c ?? 75;

  const isSteam = ["lp_steam", "mp_steam", "hp_steam"].includes(result.utility_fluid);
  const isCounter = result.flow_config === "counterflow" || result.flow_config === "shell_tube_1_2";

  // 2. SCALING CANVAS ALIGNMENT 
  const maxT = Math.max(Th_in, Th_out, Tc_in, Tc_out) + 10;
  const minT = Math.min(Th_in, Th_out, Tc_in, Tc_out) - 10;
  const range = maxT - minT || 1;

  // Converts high numbers to lower pixel values (closer to top of chart area)
  const getY = (t) => 170 - ((t - minT) / range) * 120;

  const hxX1 = 60, hxX2 = 320;
  
  // Hot Stream physical path nodes (Steam Line)
  const hy1 = getY(Th_in);
  const hy2 = getY(Th_out);
  
  // Cold Stream physical path nodes (Glycerol Line)
  const cy1 = isCounter ? getY(Tc_out) : getY(Tc_in);
  const cy2 = isCounter ? getY(Tc_in) : getY(Tc_out);

  return (
    <div className="card p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Thermal Profile Diagram</span>
      </div>

      <div className="relative w-full overflow-x-auto">
        <svg viewBox="0 0 380 200" className="w-full h-auto min-w-[300px]">
          {/* Exchanger End Walls Layout boundaries */}
          <line x1={hxX1} y1="25" x2={hxX1} y2="175" stroke="#334155" strokeDasharray="3 3" />
          <line x1={hxX2} y1="25" x2={hxX2} y2="175" stroke="#334155" strokeDasharray="3 3" />

          {/* Hot Utility Steam Line (Top Red Path) */}
          <path d={`M ${hxX1} ${hy1} L ${hxX2} ${hy2}`} fill="none" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
          <polygon points={`${hxX1+15},${hy1-4} ${hxX1+20},${hy1} ${hxX1+15},${hy1+4}`} fill="#ef4444" />
          
          {/* Cold Process Glycerol Line (Sloped Blue Path) */}
          <path d={`M ${hxX1} ${cy1} L ${hxX2} ${cy2}`} fill="none" stroke="#3b82f6" strokeWidth="3" strokeLinecap="round" />
          {isCounter ? (
            <polygon points={`${hxX1+20},${cy1-4} ${hxX1+15},${cy1} ${hxX1+20},${cy1+4}`} fill="#3b82f6" />
          ) : (
            <polygon points={`${hxX1+15},${cy1-4} ${hxX1+20},${cy1} ${hxX1+15},${cy1+4}`} fill="#3b82f6" />
          )}

          {/* Numeric Text Label Fields */}
          <text x={hxX1 - 8} y={hy1 + 4} className="text-[11px] font-mono fill-red-400 font-bold" textAnchor="end">{Th_in.toFixed(1)}°C</text>
          <text x={hxX2 + 8} y={hy2 + 4} className="text-[11px] font-mono fill-red-400 font-bold" textAnchor="start">{Th_out.toFixed(1)}°C</text>
          
          <text x={hxX1 - 8} y={cy1 + 4} className="text-[11px] font-mono fill-blue-400 font-bold" textAnchor="end">{isCounter ? `${Tc_out.toFixed(1)}°C` : `${Tc_in.toFixed(1)}°C`}</text>
          <text x={hxX2 + 8} y={cy2 + 4} className="text-[11px] font-mono fill-blue-400 font-bold" textAnchor="start">{isCounter ? `${Tc_in.toFixed(1)}°C` : `${Tc_out.toFixed(1)}°C`}</text>

          <text x={hxX1} y="15" className="text-[10px] fill-slate-500 font-bold tracking-wide" textAnchor="middle">Side A</text>
          <text x={hxX2} y="15" className="text-[10px] fill-slate-500 font-bold tracking-wide" textAnchor="middle">Side B</text>
          
          <text x="190" y="195" className="text-[10px] fill-slate-400 font-medium tracking-wider uppercase" textAnchor="middle">
            Counterflow Flow {isSteam && "(Isothermal Steam Condensation Loop)"}
          </text>
        </svg>
      </div>
    </div>
  );
}

export function HXHydraulicGauge({ result }) {
  if (!result) return null;

  // Kinetic scaling model logic to evaluate relative pressure friction heads
  const massFlow = result.hot_stream?.mass_flowrate_kg_s ?? 2.0;
  const density = result.hot_stream?.density_kg_m3 ?? 950;
  
  // Approximate velocity metrics and link crossflow scales to geometric bounds
  const calculatedVelocity = Math.min((massFlow / (density * 0.0015)), 15.0);
  
  // Set safety limit constants based on standard industrial limits
  let maxSafeVelocity = 2.2; 
  if (result.utility_fluid === "lp_steam" || result.utility_fluid === "hp_steam") maxSafeVelocity = 8.5;

  const usagePercentage = Math.min(Math.round((calculatedVelocity / maxSafeVelocity) * 100), 130);
  
  // Quadratic kinetic scaling estimation to calculate approximated pressure metrics: ΔP ∝ v²
  const baseDeltaP = Math.pow(calculatedVelocity, 2) * (density / 800) * 8.5;
  const displayDeltaP = baseDeltaP > 0 ? baseDeltaP : 12.4;

  let meterColor = "bg-emerald-500";
  let textColor = "text-emerald-400";
  if (usagePercentage > 75 && usagePercentage <= 98) {
    meterColor = "bg-amber-500";
    textColor = "text-amber-400";
  } else if (usagePercentage > 98) {
    meterColor = "bg-rose-500 animate-pulse";
    textColor = "text-rose-400";
  }

  return (
    <div className="card p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <Activity size={16} className="text-cyan-500" />
        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Hydraulic Fluid Monitor</span>
      </div>

      <div className="space-y-4 pt-1">
        {/* Core Channel Channel Bar Velocity Profile Box */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs font-medium">
            <span className="text-slate-300">Channel Flow Velocity</span>
            <span className={`font-mono ${textColor} font-bold`}>{calculatedVelocity.toFixed(2)} / {maxSafeVelocity.toFixed(1)} m/s</span>
          </div>
          <div className="w-full bg-slate-950 rounded-full h-3.5 border border-slate-800 p-0.5 overflow-hidden">
            <div className={`h-full rounded-full transition-all duration-500 ${meterColor}`} style={{ width: `${Math.min(usagePercentage, 100)}%` }} />
          </div>
        </div>

        {/* Dynamic Estimated Delta P Card metrics rows */}
        <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 flex items-center justify-between">
          <div className="space-y-0.5">
            <span className="block text-[10px] font-bold text-slate-500 tracking-wide uppercase">Calculated Friction Loss</span>
            <span className="text-sm font-sans font-semibold text-slate-200">Total Loop Pressure Drop</span>
          </div>
          <div className="text-right">
            <span className="text-xl font-mono font-bold text-cyan-400">{displayDeltaP.toFixed(1)}</span>
            <span className="text-xs text-slate-500 ml-1 font-medium">kPa</span>
          </div>
        </div>

        {/* Hazard Alarm Flag System */}
        {usagePercentage > 98 && (
          <div className="flex items-start gap-2 p-2 rounded bg-rose-950/20 border border-rose-900/40 text-rose-400 text-xs font-medium">
            <ShieldAlert size={15} className="shrink-0 mt-0.5" />
            <span><strong>Hydraulic Volumetric Violation:</strong> Loop friction velocities exceed TEMA erosion/corrosion limits. Risk of localized tube vibrational cracking. Increase tube count or expand shell size.</span>
          </div>
        )}
      </div>
    </div>
  );
}