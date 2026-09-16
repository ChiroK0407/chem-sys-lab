/**
 * frontend/src/components/units/HXForm.jsx
 * * Re-architected intent-first simulation control matrix for chemsyslab.
 * Implements a strict 5-step mathematical verification canvas to ensure correct 
 * degrees-of-freedom mapping prior to firing model convergence calculations.
 */

import { useState } from "react";
import { Loader2, Play, RotateCcw, ArrowRight, Activity } from "lucide-react";
import StreamInputPanel from "../shared/StreamInputPanel";
import HXTypeSelector from "./HXTypeSelector";
import { useSolveHX } from "../../hooks/useSolveHX";

const FLOW_CONFIGS = [
  { value: "counterflow",    label: "Counterflow Arrangement" },
  { value: "parallelflow",   label: "Parallel Flow Arrangement" },
  { value: "shell_tube_1_2", label: "TEMA Shell & Tube 1-2 Pass" },
];

const defaultStream = (name) => ({
  name,
  fluid_id: null,
  temperature_c: 80,
  pressure_kpa: 200,
  mass_flowrate_kg_s: 2.0,
  cp_J_kgK: 4200,
  density_kg_m3: 950,
  viscosity_Pa_s: 0.0003,
  thermal_conductivity: 0.65,
  phase: "liquid",
});

export default function HXForm({ onResult }) {
  // --- Core Lifecycle States ---
  const [intent, setIntent]           = useState("cooling"); // cooling | heating | process
  const [selectedTypeKey, setTypeKey] = useState(null);
  const [mode, setMode]               = useState("sizing"); // sizing | rating
  
  const [unitId, setUnitId]           = useState("HX-101");
  const [flowConfig, setFlowConfig]   = useState("counterflow");
  const [utilityFluid, setUtility]    = useState("cooling_water");
  const [U, setU]                     = useState(600);
  
  const [hotStream, setHot]           = useState(defaultStream("process_hot"));
  const [coldStream, setCold]         = useState(defaultStream("cold_process"));
  
  const [hotOutletT, setHotOut]       = useState(50);
  const [coldOutletT, setColdOut]     = useState(null);
  const [area, setArea]               = useState(25);
  const [cwSupply, setCwSupply]       = useState(30);
  const [cwReturn, setCwReturn]       = useState(45);

  const { mutate, isPending, isError, error } = useSolveHX();

  const isSteam = ["lp_steam", "mp_steam", "hp_steam"].includes(utilityFluid);
  const isProcess = utilityFluid === "process";
  const isCW = utilityFluid === "cooling_water";

  // --- Intent Macro Dispatches ---
  const handleIntentChange = (targetIntent) => {
    setIntent(targetIntent);
    if (targetIntent === "cooling") {
      setUtility("cooling_water");
    } else if (targetIntent === "heating") {
      setUtility("lp_steam");
    } else if (targetIntent === "process") {
      setUtility("process");
    }
  };

  // --- Mechanical Template Hook ---
  const handleTypeChange = (presetObject) => {
    if (!presetObject) {
      setTypeKey(null);
      return;
    }
    setTypeKey(presetObject.key);
    setU(presetObject.typical_u_mid);
  };

  // --- Backend Pipeline Formulation ---
  function buildPayload() {
    const base = {
      unit_id: unitId,
      mode,
      flow_config: flowConfig,
      utility_fluid: utilityFluid,
      U_W_m2K: U,
      hot_stream: { ...hotStream },
    };

    if (isProcess) base.cold_stream = { ...coldStream };
    if (isCW) { 
      base.cw_supply_T_c = cwSupply; 
      base.cw_return_T_c = cwReturn;
    }

    if (mode === "sizing") {
      if (isSteam) { 
        base.cold_outlet_T_c = coldOutletT ?? 110; 
      } else { 
        base.hot_outlet_T_c = hotOutletT; 
      }
    } else {
      base.area_m2 = area;
    }

    delete base.hot_stream.fluid_id;
    if (base.cold_stream) delete base.cold_stream.fluid_id;

    return base;
  }

  function handleSolve() {
    mutate(
      { payload: buildPayload(), includeLog: true },
      { onSuccess: (data) => onResult(data) }
    );
  }

  function handleReset() {
    setIntent("cooling");
    setTypeKey(null);
    setMode("sizing");
    setUnitId("HX-101");
    setFlowConfig("counterflow");
    setUtility("cooling_water");
    setU(600);
    setHot(defaultStream("process_hot"));
    setCold(defaultStream("cold_process"));
    setHotOut(50);
    setColdOut(null);
    setArea(25);
    setCwSupply(30);
    setCwReturn(45);
    onResult(null);
  }

  return (
    <div className="space-y-6 text-slate-200">
      
      {/* STEP 1: Process Thermodynamic Intent Card Array */}
      <div className="space-y-2">
        <label className="label block text-xs font-bold text-slate-400 tracking-wider uppercase">
          Step 1 — Define Process Operational Intent
        </label>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          
          {/* Card 1: Cooling */}
          <button
            type="button"
            onClick={() => handleIntentChange("cooling")}
            className={`p-4 rounded-xl border text-left transition-all outline-none ${
              intent === "cooling"
                ? "border-emerald-500 bg-emerald-950/80 shadow-lg shadow-emerald-950/40 ring-2 ring-emerald-500/50"
                : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
            }`}
          >
            <span className={`block text-sm font-bold transition-colors ${
              intent === "cooling" ? "text-white" : "text-slate-200"
            }`}>
              Cool a stream
            </span>
            <span className={`block text-xs mt-1 transition-colors ${
              intent === "cooling" ? "text-slate-100 font-medium" : "text-slate-400"
            }`}>
              Rejects heat to industrial cooling water networks.
            </span>
          </button>

          {/* Card 2: Heating */}
          <button
            type="button"
            onClick={() => handleIntentChange("heating")}
            className={`p-4 rounded-xl border text-left transition-all outline-none ${
              intent === "heating"
                ? "border-emerald-500 bg-emerald-950/80 shadow-lg shadow-emerald-950/40 ring-2 ring-emerald-500/50"
                : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
            }`}
          >
            <span className={`block text-sm font-bold transition-colors ${
              intent === "heating" ? "text-white" : "text-slate-200"
            }`}>
              Heat a stream
            </span>
            <span className={`block text-xs mt-1 transition-colors ${
              intent === "heating" ? "text-slate-100 font-medium" : "text-slate-400"
            }`}>
              Utilizes condensing saturated plant steam grades.
            </span>
          </button>

          {/* Card 3: Process-to-Process */}
          <button
            type="button"
            onClick={() => handleIntentChange("process")}
            className={`p-4 rounded-xl border text-left transition-all outline-none ${
              intent === "process"
                ? "border-emerald-500 bg-emerald-950/80 shadow-lg shadow-emerald-950/40 ring-2 ring-emerald-500/50"
                : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
            }`}
          >
            <span className={`block text-sm font-bold transition-colors ${
              intent === "process" ? "text-white" : "text-slate-200"
            }`}>
              Process-to-process
            </span>
            <span className={`block text-xs mt-1 transition-colors ${
              intent === "process" ? "text-slate-100 font-medium" : "text-slate-400"
            }`}>
              Thermal cross-integration between hot and cold runs.
            </span>
          </button>

        </div>
      </div>

      {/* STEP 2: Mechanical Catalog Core Integration Block */}
      <div className="card p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
        <label className="label block text-xs font-bold text-slate-400 tracking-wider uppercase">
          Step 2 — Structural Equipment Selection
        </label>
        <HXTypeSelector value={selectedTypeKey} onChange={handleTypeChange} />
      </div>

      {/* STEP 3: Aspen Degrees of Freedom Matrix */}
      <div className="card p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
        <label className="label block text-xs font-bold text-slate-400 tracking-wider uppercase">
          Step 3 — Operating Boundary & Simulation Profile
        </label>
        
        {/* Large Mode Toggles Selection Elements */}
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setMode("sizing")}
            className={`py-3 px-4 rounded-lg font-medium text-sm border transition-all ${
              mode === "sizing"
                ? "bg-slate-800 border-blue-500 text-blue-400 shadow-md"
                : "bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700"
            }`}
          >
            Sizing — find required area
          </button>
          <button
            type="button"
            onClick={() => setMode("rating")}
            className={`py-3 px-4 rounded-lg font-medium text-sm border transition-all ${
              mode === "rating"
                ? "bg-slate-800 border-blue-500 text-blue-400 shadow-md"
                : "bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700"
            }`}
          >
            Rating — find outlet temperature
          </button>
        </div>

        {/* Core Design Parameter Grid — Locked Row Alignment */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-4 pt-2">
          <div>
            <label className="label block text-xs font-medium text-slate-400 mb-1">Unit ID Tag</label>
            <input className="input w-full bg-slate-950/60 border border-slate-800 rounded p-2 text-sm font-mono text-slate-200 focus:border-slate-700 outline-none" value={unitId} onChange={(e) => setUnitId(e.target.value)} />
          </div>

          <div>
            <label className="label block text-xs font-medium text-slate-400 mb-1">Geometry Arrangement</label>
            <select className="select w-full bg-slate-950/60 border border-slate-800 rounded p-2 text-sm text-slate-200 focus:border-slate-700 outline-none" value={flowConfig} onChange={(e) => setFlowConfig(e.target.value)}>
              {FLOW_CONFIGS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
            </select>
          </div>

          <div>
            <label className="label block text-xs font-medium text-slate-400 mb-1">HTC U [W/(m²·K)]</label>
            <input type="number" className="input w-full bg-slate-950/60 border border-slate-800 rounded p-2 text-sm text-slate-200 font-mono outline-none focus:border-slate-700" value={U} onChange={(e) => setU(parseFloat(e.target.value))} step="10" />
          </div>

          {/* Target Parameter Slot — Stays structurally constant, switches dynamically inside */}
          <div>
            {mode === "sizing" ? (
              <>
                <label className="label block text-xs font-medium text-blue-400 mb-1">
                  {intent === "heating" ? "Target Cold Outlet T (°C)" : "Target Hot Outlet T (°C)"}
                </label>
                {intent === "heating" ? (
                  <input type="number" className="input w-full bg-slate-950/60 border border-blue-900/50 rounded p-2 text-sm text-slate-200 font-mono outline-none focus:border-blue-500" value={coldOutletT ?? 110} onChange={(e) => setColdOut(parseFloat(e.target.value))} />
                ) : (
                  <input type="number" className="input w-full bg-slate-950/60 border border-blue-900/50 rounded p-2 text-sm text-slate-200 font-mono outline-none focus:border-blue-500" value={hotOutletT ?? ""} onChange={(e) => setHotOut(parseFloat(e.target.value))} />
                )}
              </>
            ) : (
              <>
                <label className="label block text-xs font-medium text-blue-400 mb-1">Area (m²)</label>
                <input type="number" className="input w-full bg-slate-950/60 border border-blue-900/50 rounded p-2 text-sm text-slate-200 font-mono outline-none focus:border-blue-500" value={area} onChange={(e) => setArea(parseFloat(e.target.value))} step="0.5" />
              </>
            )}
          </div>
        </div>

        {/* Secondary Utility Controls — Rendered as a separate clean sub-row to preserve column boundaries */}
        {isCW && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4 pt-3 border-t border-slate-800/60 animate-fadeIn">
            <div>
              <label className="label block text-xs font-medium text-slate-400 mb-1">CW Supply Temp (°C)</label>
              <input type="number" className="input w-full bg-slate-950/60 border border-slate-800 rounded p-2 text-sm text-slate-200 font-mono outline-none focus:border-slate-700" value={cwSupply} onChange={(e) => setCwSupply(parseFloat(e.target.value))} />
            </div>
            <div>
              <label className="label block text-xs font-medium text-slate-400 mb-1">CW Return Temp (°C)</label>
              <input type="number" className="input w-full bg-slate-950/60 border border-slate-800 rounded p-2 text-sm text-slate-200 font-mono outline-none focus:border-slate-700" value={cwReturn} onChange={(e) => setCwReturn(parseFloat(e.target.value))} />
            </div>
            {/* Empty grid spacers keep the row structure perfectly balanced */}
            <div className="hidden sm:block"></div>
            <div className="hidden sm:block"></div>
          </div>
        )}
      </div>

      {/* STEP 4: Process Driving Core Fluid Panel */}
      <div className="card p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-2">
        <label className="label block text-xs font-bold text-slate-400 tracking-wider uppercase">
          Step 4 — Core Fluid Configuration
        </label>
        <StreamInputPanel
          label={
            intent === "cooling"
              ? "Process stream — being cooled"
              : intent === "heating"
              ? "Process stream — being heated"
              : "Hot stream"
          }
          value={hotStream}
          onChange={setHot}
        />
      </div>

      {/* STEP 5: Second Fluid Channel / Secondary Utility Monitor */}
      <div className="card p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
        <label className="label block text-xs font-bold text-slate-400 tracking-wider uppercase">
          Step 5 — Secondary Integration Channel
        </label>
        
        {intent === "process" ? (
          <StreamInputPanel label="Cold stream" value={coldStream} onChange={setCold} />
        ) : intent === "cooling" ? (
          <div className="p-4 rounded-xl border border-blue-900/40 bg-blue-950/10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-0.5">
              <span className="block text-xs font-bold tracking-wide text-blue-400 uppercase">Utility Network Assignment</span>
              <p className="text-sm font-medium text-slate-300">Cooling Water | Header Loop 30°C → 45°C Limit</p>
            </div>
            <div className="flex items-center gap-2 max-w-xs">
              <div>
                <span className="block text-[10px] text-slate-500 font-semibold uppercase mb-0.5">Supply (°C)</span>
                <input type="number" className="w-20 bg-slate-950 border border-slate-800 rounded p-1 text-xs font-mono text-center text-slate-300 outline-none" value={cwSupply} onChange={(e) => setCwSupply(parseFloat(e.target.value))} />
              </div>
              <div className="flex items-center pt-4 text-slate-600">
                <ArrowRight size={14} />
              </div>
              <div>
                <span className="block text-[10px] text-slate-500 font-semibold uppercase mb-0.5">Return (°C)</span>
                <input type="number" className="w-20 bg-slate-950 border border-slate-800 rounded p-1 text-xs font-mono text-center text-slate-300 outline-none" value={cwReturn} onChange={(e) => setCwReturn(parseFloat(e.target.value))} />
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-xl border border-orange-900/40 bg-orange-950/10">
            <span className="block text-xs font-bold tracking-wide text-orange-400 uppercase">Utility Network Assignment</span>
            <p className="text-sm font-medium text-slate-300 mt-0.5">LP Steam | 140°C Saturated Vapor Condensing Regime</p>
          </div>
        )}
      </div>

      {/* Solver Exception Alert Matrix */}
      {isError && (
        <div className="rounded-lg border border-red-900 bg-red-950/30 px-4 py-3 text-sm text-red-400 font-medium">
          {error?.message || "Convergence failure: check approach constraints."}
        </div>
      )}

      {/* Form Action Controls Execution Blocks */}
      <div className="flex items-center gap-3 pt-2">
        <button
          type="button"
          onClick={handleSolve}
          disabled={isPending}
          className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-semibold text-sm rounded-lg transition-all border border-blue-700 shadow shadow-blue-950/50"
        >
          {isPending ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
          {isPending ? "Converging..." : "Run Simulator"}
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 font-medium text-sm rounded-lg border border-slate-700/60 transition-all"
        >
          <RotateCcw size={15} />
          Reset Workspace
        </button>
      </div>

    </div>
  );
}