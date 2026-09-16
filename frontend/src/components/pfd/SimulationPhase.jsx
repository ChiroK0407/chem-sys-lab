import React, { useState, useMemo } from "react";
import { Activity, Sliders, RefreshCw, AlertTriangle, CheckCircle } from "lucide-react";
import client from "../../api/client";
import { COMPONENT_REGISTRY } from "../../constants/componentRegistry";

export default function SimulationPhase({ canvasState, updateCanvasState }) {
  const [selectedUnitId, setSelectedUnitId] = useState(null);
  const [isSolving, setIsSolving] = useState(false);
  const [solverLogs, setSolverLogs] = useState([]);

  const selectedUnit = useMemo(() => {
    return canvasState.components.find((c) => c.id === selectedUnitId);
  }, [canvasState.components, selectedUnitId]);

  // ── 1. DYNAMIC EQUIPMENT PROPERTY SCHEMA SPECIFICATION FOR EACH OPERATIONS ──
  const renderUnitConfigInputs = () => {
    if (!selectedUnit) return null;

    const currentParams = selectedUnit.specifications.parameters || {};

    const handleParamChange = (field, value) => {
      updateCanvasState((prev) => ({
        ...prev,
        components: prev.components.map((c) =>
          c.id === selectedUnit.id
            ? {
                ...c,
                specifications: {
                  ...c.specifications,
                  parameters: { ...c.specifications.parameters, [field]: parseFloat(value) || 0 }
                }
              }
            : c
        )
      }));
    };

    switch (selectedUnit.type) {
      case "PUMP":
        return (
          <div className="space-y-3">
            <div>
              <label className="label">Target Discharge Pressure (kPa)</label>
              <input type="number" className="input text-xs" value={currentParams.discharge_pressure_kPa ?? 300} onChange={(e) => handleParamChange("discharge_pressure_kPa", e.target.value)} />
            </div>
            <div>
              <label className="label">Isentropic Efficiency (η)</label>
              <input type="number" step="0.01" max="1" className="input text-xs" value={currentParams.eta_pump ?? 0.75} onChange={(e) => handleParamChange("eta_pump", e.target.value)} />
            </div>
          </div>
        );
      case "CSTR":
      case "PFR":
        return (
          <div className="space-y-3">
            <div>
              <label className="label">Reactor Volume (m³)</label>
              <input type="number" className="input text-xs" value={currentParams.volume_m3 ?? 5.0} onChange={(e) => handleParamChange("volume_m3", e.target.value)} />
            </div>
            <div>
              <label className="label">Arrhenius Activation Energy (Ea - kJ/mol)</label>
              <input type="number" className="input text-xs" value={currentParams.activation_energy ?? 75} onChange={(e) => handleParamChange("activation_energy", e.target.value)} />
            </div>
          </div>
        );
      case "SPLITTER":
        return (
          <div>
            <label className="label">Overhead Split Fraction (0 - 1)</label>
            <input type="number" step="0.05" min="0" max="1" className="input text-xs" value={currentParams.split_fraction ?? 0.5} onChange={(e) => handleParamChange("split_fraction", e.target.value)} />
          </div>
        );
      case "HEAT_EXCHANGER":
        return (
          <div className="space-y-3">
            <div>
              <label className="label">Overall Heat Transfer Coeff (W/m²K)</label>
              <input type="number" className="input text-xs" value={currentParams.U_W_m2K ?? 600} onChange={(e) => handleParamChange("U_W_m2K", e.target.value)} />
            </div>
            <div>
              <label className="label">Required Heat Exchange Area (m²)</label>
              <input type="number" className="input text-xs" value={currentParams.area_m2 ?? 12.5} onChange={(e) => handleParamChange("area_m2", e.target.value)} />
            </div>
          </div>
        );
      default:
        return <p className="text-[11px] text-gray-400 italic">No customizable operating constraints needed for this operation.</p>;
    }
  };

  // ── 2. FIRST-PRINCIPLES CASCADING DOWNSTREAM TREE PROPAGATOR ENGINE ──
  const triggerSimulationCascade = async () => {
    if (!selectedUnit) return;
    setIsSolving(true);
    setSolverLogs(["Initializing flowsheet sequential modular solver..."]);

    try {
      let componentMap = { ...canvasState.components.reduce((acc, curr) => ({ ...acc, [curr.id]: { ...curr } }), {}) };
      
      // Topological sequence calculation queue execution loop
      let processingQueue = [selectedUnit.id];
      let solvedUnits = new Set();

      while (processingQueue.length > 0) {
        const currentId = processingQueue.shift();
        if (solvedUnits.has(currentId)) continue;

        const activeUnit = componentMap[currentId];
        const registryInfo = COMPONENT_REGISTRY[activeUnit.type];
        
        setSolverLogs(prev => [...prev, `Calling first-principles solver for unit operation: ${currentId}...`]);

        // Gather inlet properties from manual specifications or upstream connections
        const incomingConnections = canvasState.connections.filter(conn => conn.targetId === currentId);
        let integratedStreams = { ...activeUnit.specifications.streams };

        incomingConnections.forEach(conn => {
          const upstreamUnit = componentMap[conn.sourceId];
          if (upstreamUnit && upstreamUnit.specifications.simulatedResults?.outlet_stream) {
            // Overwrite inlet stream vector properties dynamically from calculated upstream outcome
            integratedStreams[conn.targetPort] = upstreamUnit.specifications.simulatedResults.outlet_stream;
          }
        });

        // Structure the precise request payload required by unit_schemas.py
        const requestPayload = {
          unit_id: activeUnit.id,
          parameters: activeUnit.parameters || {},
          config: activeUnit.specifications.parameters,
          streams: integratedStreams
        };

        // Post parameters vector to absolute backend endpoints
        const response = await client.post(`${registryInfo.endpoint}?include_log=true`, requestPayload);
        
        // Embed outcome variables inside calculation map context
        componentMap[currentId].specifications.simulatedResults = response.data;
        solvedUnits.add(currentId);

        // Find immediately linked downstreams to append into computing cascade queue
        const downstreamLinks = canvasState.connections.filter(conn => conn.sourceId === currentId);
        downstreamLinks.forEach(link => {
          if (!solvedUnits.has(link.targetId)) {
            processingQueue.push(link.targetId);
          }
        });
      }

      // Commit fully computed flowsheet back into parent Simbook array context
      updateCanvasState((prev) => ({
        ...prev,
        components: Object.values(componentMap)
      }));
      setSolverLogs(prev => [...prev, "✓ Flowsheet state tracking re-balanced successfully."]);

    } catch (err) {
      setSolverLogs(prev => [...prev, `❌ Solver Failure Exception: ${err.response?.data?.detail || err.message}`]);
    } finally {
      setIsSolving(false);
    }
  };

  return (
    <div className="flex-1 flex h-full bg-gray-50 font-sans">
      {/* Central Frozen View Framework Monitor Grid */}
      <div className="flex-1 p-6 space-y-4 overflow-y-auto">
        <div className="flex items-center justify-between border-b border-gray-200 pb-3">
          <div>
            <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wider">Flowsheet Sandbox Terminal</h2>
            <p className="text-xs text-gray-400 mt-0.5">Topological structures fixed. Click elements to alter design specifications.</p>
          </div>
          {isSolving && (
            <div className="flex items-center gap-1.5 text-xs font-semibold text-brand-600 bg-brand-50 border border-brand-100 rounded-full px-3 py-1 animate-pulse">
              <RefreshCw size={12} className="animate-spin" /> Executing Sequential Modular Cascade...
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          {canvasState.components.map((unit) => {
            const hasResults = !!unit.specifications.simulatedResults;
            return (
              <div key={unit.id} onClick={() => setSelectedUnitId(unit.id)} className={`p-4 rounded-xl border bg-white cursor-pointer transition-all ${
                selectedUnitId === unit.id ? "border-brand-500 ring-2 ring-brand-50" : "border-gray-200 hover:border-gray-300 shadow-sm"
              }`}>
                <div className="flex justify-between items-center">
                  <span className="text-[9px] font-mono font-bold bg-gray-100 px-2 py-0.5 rounded text-gray-500">{unit.id}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${hasResults ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                    {hasResults ? "Calculated" : "Idle"}
                  </span>
                </div>
                <h4 className="text-sm font-bold text-gray-800 mt-2">{unit.name}</h4>
                
                {unit.specifications.simulatedResults?.results && (
                  <div className="mt-3 pt-2.5 border-t border-gray-100 grid grid-cols-2 gap-2 text-[10px] font-mono text-gray-500">
                    {Object.entries(unit.specifications.simulatedResults.results).slice(0, 2).map(([k, v]) => (
                      <div key={k} className="bg-gray-50 p-1.5 rounded border border-gray-100">
                        <span className="block uppercase text-[8px] text-gray-400 font-sans">{k.replace("_"," ")}</span>
                        <span className="font-bold text-gray-700">{Number(v).toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Runtime Mathematical Convergence Output Logs console */}
        {solverLogs.length > 0 && (
          <div className="bg-gray-900 rounded-xl p-4 font-mono text-[11px] text-emerald-400 space-y-1 shadow-inner max-h-48 overflow-y-auto">
            <p className="text-gray-400 border-b border-gray-800 pb-1 mb-2 font-sans font-bold">Flowsheet Solver Console Logger</p>
            {solverLogs.map((log, index) => (
              <p key={index} className={log.includes("❌") ? "text-red-400" : log.includes("✓") ? "text-emerald-300 font-bold" : ""}>{log}</p>
            ))}
          </div>
        )}
      </div>

      {/* Right Core Property Tuning Config sheet */}
      <div className="w-96 border-l border-gray-200 bg-white p-5 flex flex-col h-full shadow-md">
        {selectedUnit ? (
          <div className="flex flex-col h-full justify-between">
            <div className="space-y-4">
              <div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-gray-400">Tuning Sheet</span>
                <h3 className="text-base font-bold text-gray-900">{selectedUnit.name}</h3>
                <p className="text-xs text-brand-600 font-mono mt-0.5">Model Blueprint Class: {selectedUnit.type}</p>
              </div>

              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3">
                <p className="text-xs font-bold text-gray-700 uppercase tracking-wide">Adjust Equipment Boundaries</p>
                {renderUnitConfigInputs()}
              </div>
            </div>

            <button onClick={triggerSimulationCascade} disabled={isSolving} className="btn-primary w-full py-2.5 text-xs font-bold tracking-wide flex items-center justify-center gap-2 mt-6">
              {isSolving ? <RefreshCw size={14} className="animate-spin" /> : <Activity size={14} />}
              Compute Steady-State Sequence
            </button>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center text-gray-400 text-xs">
            <Activity size={24} className="text-gray-300 mb-1 animate-pulse" />
            Click an engineering unit block to tune boundary specifications.
          </div>
        )}
      </div>
    </div>
  );
}