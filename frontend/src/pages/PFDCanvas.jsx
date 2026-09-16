import React, { useState, useEffect } from "react";
import { BookOpen, Plus, Upload, Download, ArrowRight, Save } from "lucide-react";
import { ReactFlowProvider } from "reactflow";
import DesignPhase from "../components/pfd/DesignPhase";
import SpecificationPhase from "../components/pfd/SpecificationPhase";
import SimulationPhase from "../components/pfd/SimulationPhase";

export default function PFDCanvas() {
  const [activeSimbook, setActiveSimbook] = useState(null);
  const [recentSimbooks, setRecentSimbooks] = useState([]);

  // Fetch past simbooks history logs from client local cache on mount
  useEffect(() => {
    const cached = localStorage.getItem("che_simbooks_history");
    if (cached) setRecentSimbooks(JSON.parse(cached));
  }, []);

  const saveToHistory = (simbookObj) => {
    const updated = [simbookObj, ...recentSimbooks.filter((s) => s.id !== simbookObj.id)].slice(0, 5);
    setRecentSimbooks(updated);
    localStorage.setItem("che_simbooks_history", JSON.stringify(updated));
  };

  const handleCreateNew = () => {
    const newSimbook = {
      id: "sb_" + Math.random().toString(36).substr(2, 9),
      meta: { name: "Untitled Refinery Simulation Book", lastModified: new Date().toISOString() },
      canvasState: { activePhase: "DESIGN", isDofFullyDefined: false, components: [], connections: [] }
    };
    setActiveSimbook(newSimbook);
  };

  const handleLocalUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const parsed = JSON.parse(evt.target.result);
        if (parsed.id && parsed.canvasState) {
          if (!parsed.canvasState.components) parsed.canvasState.components = [];
          if (!parsed.canvasState.connections) parsed.canvasState.connections = [];
          setActiveSimbook(parsed);
          saveToHistory(parsed);
        } else {
          alert("Invalid Simbook structural data layout.");
        }
      } catch (err) {
        alert("Error parsing .simbook data matrix blueprint.");
      }
    };
    reader.readAsText(file);
  };

  const handleDownloadFile = () => {
    if (!activeSimbook) return;
    const jsonString = JSON.stringify(activeSimbook, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = `${activeSimbook.meta.name.replace(/\s+/g, "_")}.simbook`;
    link.click();
  };

  const updateCanvasState = (updater) => {
    setActiveSimbook((prev) => {
      if (!prev) return prev;
      const nextCanvasState = updater(prev.canvasState);
      const nextState = {
        ...prev,
        canvasState: {
          ...nextCanvasState,
          components: nextCanvasState.components || [],
          connections: nextCanvasState.connections || []
        }
      };
      nextState.meta.lastModified = new Date().toISOString();
      return nextState;
    });
  };

  // ── LANDING VIEW DASHBOARD RENDERING TIER ──
  if (!activeSimbook) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] bg-gray-50 font-sans">
        <div className="w-1/2 p-12 flex flex-col justify-center border-r border-gray-200 bg-white">
          <div className="max-w-md mx-auto space-y-6">
            <div className="flex items-center gap-3 text-brand-600">
              <BookOpen size={36} className="stroke-[2]" />
              <h1 className="text-2xl font-black tracking-tight text-gray-900">Simbook Engine Workspace</h1>
            </div>
            <p className="text-sm text-gray-500 leading-relaxed">
              Design multi-unit process systems. Map out plant topology, balance degrees of freedom, and run first-principles steady-state simulations.
            </p>
            <div className="pt-4 space-y-3">
              <button onClick={handleCreateNew} className="w-full flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-700 text-white rounded-lg py-3 text-sm font-semibold shadow-sm transition-all">
                <Plus size={16} /> Create New Simbook
              </button>
              <label className="w-full flex items-center justify-center gap-2 border border-gray-300 hover:border-gray-400 text-gray-700 bg-white rounded-lg py-3 text-sm font-semibold shadow-sm cursor-pointer transition-all">
                <Upload size={16} /> Open Local .simbook File
                <input type="file" accept=".simbook" onChange={handleLocalUpload} className="hidden" />
              </label>
            </div>
          </div>
        </div>

        <div className="w-1/2 p-12 flex flex-col justify-center">
          <div className="max-w-md mx-auto w-full space-y-4">
            <h2 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Recent Simulation Project Books</h2>
            {recentSimbooks.length === 0 ? (
              <div className="border border-dashed border-gray-300 rounded-xl p-8 text-center text-gray-400 text-xs">
                No recent workspace cache discovered. Create a workflow parameters set to begin tracking.
              </div>
            ) : (
              <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                {recentSimbooks.map((sb) => (
                  <div key={sb.id} onClick={() => setActiveSimbook(sb)} className="group border border-gray-200 bg-white hover:border-brand-500 rounded-xl p-4 flex items-center justify-between cursor-pointer shadow-sm transition-all">
                    <div>
                      <h4 className="text-sm font-bold text-gray-800 group-hover:text-brand-600 transition-colors">{sb.meta.name}</h4>
                      <span className="text-[10px] text-gray-400 font-mono block mt-0.5">Modified: {new Date(sb.meta.lastModified).toLocaleDateString()}</span>
                    </div>
                    <ArrowRight size={14} className="text-gray-300 group-hover:text-brand-500 transition-colors transform group-hover:translate-x-0.5" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ── ACTIVE WORKSPACE WORKBENCH INTERFACE ──
  const { canvasState } = activeSimbook;

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden bg-gray-50">
      
      {/* Optimized Top Bar Controls Panel */}
      <div className="h-14 border-b border-gray-200 bg-white px-6 flex items-center justify-between z-30 flex-shrink-0">
        
        {/* Left: Dedicated Title Space */}
        <div className="flex-1 max-w-xl pr-4">
          <input
            type="text"
            className="w-full text-sm font-bold text-gray-900 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-brand-600 focus:outline-none py-0.5 truncate transition-all"
            value={activeSimbook.meta.name}
            onChange={(e) => setActiveSimbook({ ...activeSimbook, meta: { ...activeSimbook.meta, name: e.target.value } })}
            title="Click to rename Simbook"
          />
        </div>

        {/* Right: Consolidated Action & Phase Controls Cluster */}
        <div className="flex items-center gap-4">
          
          {/* Step-by-Step Flow Phase Toggle Tabs */}
          <div className="flex bg-gray-100 rounded-lg p-0.5 border border-gray-200 shadow-inner">
            {["DESIGN", "SPECIFICATION", "SIMULATION"].map((phase) => (
              <button
                key={phase}
                disabled={
                  (phase === "SPECIFICATION" && (!canvasState.components || canvasState.components.length === 0)) ||
                  (phase === "SIMULATION" && !canvasState.isDofFullyDefined)
                }
                onClick={() => updateCanvasState((c) => ({ ...c, activePhase: phase }))}
                className={`text-[11px] uppercase tracking-wider px-3 py-1 rounded-md font-semibold transition-all ${
                  canvasState.activePhase === phase
                    ? "bg-white text-brand-600 shadow-sm"
                    : "text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                }`}
              >
                {phase}
              </button>
            ))}
          </div>

          {/* Vertical Separator Divide */}
          <div className="h-6 w-px bg-gray-200" />

          {/* Operational Save/File Streaming Buttons Panel */}
          <div className="flex items-center gap-2">
            <button 
              onClick={() => { saveToHistory(activeSimbook); alert("State saved successfully."); }} 
              className="btn-secondary flex items-center gap-1.5 py-1.5 px-3 text-xs font-medium"
            >
              Save Cache
            </button>
            <button 
              onClick={handleDownloadFile} 
              className="btn-primary flex items-center gap-1.5 py-1.5 px-3 text-xs font-semibold shadow-xs"
            >
              Download File
            </button>
            
            <button 
              onClick={() => setActiveSimbook(null)} 
              className="btn-secondary py-1.5 px-3 text-xs font-medium text-red-600 border-red-100 hover:bg-red-50/60 ml-2"
            >
              Exit
            </button>
          </div>

        </div>
      </div>

      {/* Target Workspace Viewport Mounting Tier */}
      <div className="flex-1 flex overflow-hidden">
        <ReactFlowProvider>
          {canvasState.activePhase === "DESIGN" && (
            <DesignPhase canvasState={canvasState} updateCanvasState={updateCanvasState} />
          )}
          {canvasState.activePhase === "SPECIFICATION" && (
            <SpecificationPhase canvasState={canvasState} updateCanvasState={updateCanvasState} />
          )}
          {canvasState.activePhase === "SIMULATION" && (
            <SimulationPhase canvasState={canvasState} updateCanvasState={updateCanvasState} />
          )}
        </ReactFlowProvider>
      </div>

    </div>
  );
}