import React, { useState, useMemo, useEffect } from "react";
import ReactFlow, { Background, Controls, Handle, Position, useReactFlow } from "reactflow";
import { Play, CheckCircle2, AlertCircle, HelpCircle, Sliders } from "lucide-react";
import "reactflow/dist/style.css";

const OperationalValidationNode = ({ data }) => {
  const inlets = data.ports?.inlets || [];
  const outlets = data.ports?.outlets || [];
  return (
    <div className="border-2 border-slate-400 bg-white rounded-xl p-3.5 min-w-[200px] shadow-lg font-sans border-t-slate-700 relative">
      <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-around pointer-events-none my-4">
        {inlets.map(p => (
          <div key={p} className="relative flex items-center">
            <Handle type="target" position={Position.Left} id={p} className="w-2 h-2 bg-slate-400 border border-white" style={{ left: "-5px" }} />
            <span className="text-[7px] font-mono ml-1.5 bg-white/80 px-0.5 text-slate-400">{p}</span>
          </div>
        ))}
      </div>
      <div className="px-2">
        <h4 className="text-xs font-bold text-slate-800">{data.name}</h4>
        <span className="text-[9px] font-mono text-brand-600 font-bold block mt-0.5">{data.id}</span>
      </div>
      <div className="absolute right-0 top-0 bottom-0 flex flex-col justify-around pointer-events-none my-4">
        {outlets.map(p => (
          <div key={p} className="relative flex items-center justify-end">
            <span className="text-[7px] font-mono mr-1.5 bg-white/80 px-0.5 text-slate-400">{p}</span>
            <Handle type="source" position={Position.Right} id={p} className="w-2 h-2 bg-slate-700 border border-white" style={{ right: "-5px" }} />
          </div>
        ))}
      </div>
    </div>
  );
};

const nodeTypes = { unit: OperationalValidationNode };

export default function SpecificationPhase({ canvasState, updateCanvasState }) {
  const [selectedStreamId, setSelectedStreamId] = useState(null);
  const [dofReport, setDofReport] = useState(null);
  const reactFlowInstance = useReactFlow();

  const comps = canvasState.components || [];
  const conns = canvasState.connections || [];

  const selectedStream = useMemo(() => {
    return conns.find(c => c.id === selectedStreamId);
  }, [conns, selectedStreamId]);

  const flowNodes = useMemo(() => {
    return comps.map(c => ({
      id: c.id,
      type: "unit",
      position: c.position,
      data: { name: c.name, type: c.type, id: c.id, ports: c.ports },
      draggable: false
    }));
  }, [comps]);

  const flowEdges = useMemo(() => {
    return conns.map(c => ({
      id: c.id,
      source: c.sourceId,
      sourceHandle: c.sourcePort,
      target: c.targetId,
      targetHandle: c.targetPort,
      animated: true,
      label: c.streamName,
      labelStyle: { fill: selectedStreamId === c.id ? "#0284c7" : "#475569", fontWeight: 700, fontSize: "11px" },
      style: { stroke: selectedStreamId === c.id ? "#0284c7" : "#94a3b8", strokeWidth: selectedStreamId === c.id ? 3.5 : 2.5 }
    }));
  }, [conns, selectedStreamId]);

  useEffect(() => {
    if (flowNodes.length > 0) {
      setTimeout(() => reactFlowInstance.fitView({ padding: 0.2, duration: 150 }), 50);
    }
  }, [flowNodes.length, reactFlowInstance]);

  const handleUpdateStreamProperty = (prop, val) => {
    updateCanvasState(prev => ({
      ...prev,
      connections: (prev.connections || []).map(c => {
        if (c.id !== selectedStreamId) return c;
        return {
          ...c,
          specifications: { ...c.specifications, [prop]: val === "" ? "" : parseFloat(val) }
        };
      })
    }));
  };

  const executeDOFBalancer = () => {
    let variablesCount = conns.length * 3; // T, P, F for each individual stream loop link
    let equationsCount = comps.length * 2; // Conservation constraints equations
    let manuallySpecified = 0;
    let gaps = [];

    conns.forEach(c => {
      const s = c.specifications || {};
      if (s.temperature_C !== undefined && s.temperature_C !== "") manuallySpecified++; else gaps.push(`${c.streamName} Temp`);
      if (s.pressure_kPa !== undefined && s.pressure_kPa !== "") manuallySpecified++; else gaps.push(`${c.streamName} Press`);
      if (s.mass_flow_kg_s !== undefined && s.mass_flow_kg_s !== "") manuallySpecified++; else gaps.push(`${c.streamName} Flow`);
    });

    const dof = variablesCount - equationsCount - manuallySpecified;
    const status = dof === 0 ? "FULLY_DEFINED" : dof < 0 ? "OVER_DEFINED" : "UNDER_DEFINED";

    setDofReport({ status, value: dof, suggestions: gaps.slice(0, 3) });
    updateCanvasState(c => ({ ...c, isDofFullyDefined: status === "FULLY_DEFINED" }));
  };

  return (
    <div className="flex-1 flex h-full overflow-hidden">
      <div className="flex-1 flex flex-col p-4 space-y-4">
        <div className="flex justify-between items-center flex-shrink-0">
          <div>
            <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Thermodynamic Stream Workbook</h3>
            <p className="text-xs text-slate-400">Click any colored pipeline connection link directly on the canvas to configure it.</p>
          </div>
          <button onClick={executeDOFBalancer} className="btn-primary text-xs font-bold py-2 px-4 shadow-sm flex items-center gap-1.5">
            Run DOF Analysis
          </button>
        </div>

        {dofReport && (
          <div className={`p-3.5 rounded-xl border flex gap-3 text-xs flex-shrink-0 ${dofReport.status === "FULLY_DEFINED" ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-amber-50 border-amber-200 text-amber-800"}`}>
            {dofReport.status === "FULLY_DEFINED" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
            <div>
              <span className="font-bold block">System Status: {dofReport.status.replace("_", " ")} (DOF = {dofReport.value})</span>
              {dofReport.status === "UNDER_DEFINED" && (
                <p className="mt-1 text-amber-700">Missing Stream Bounds: {dofReport.suggestions.join(", ")}</p>
              )}
            </div>
          </div>
        )}

        <div className="flex-1 border border-slate-200 rounded-2xl overflow-hidden relative">
          <ReactFlow 
            nodes={flowNodes} 
            edges={flowEdges} 
            nodeTypes={nodeTypes} 
            onEdgeClick={(_, edge) => setSelectedStreamId(edge.id)}
            fitView
          >
            <Background color="#cbd5e1" gap={18} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      </div>

      <div className="w-80 border-l border-gray-200 bg-white p-5 overflow-y-auto flex-shrink-0 shadow-xl">
        {selectedStream ? (
          <div className="space-y-4 font-sans">
            <div>
              {/* FIXED LINE BELOW: Removed the duplicate text-slate-400 color utility to fix conflict */}
              <span className="text-[10px] font-mono font-bold bg-sky-50 text-sky-700 px-2 py-0.5 rounded inline-block border border-sky-100">
                Line: {selectedStream.streamName}
              </span>
              <h3 className="text-sm font-bold text-slate-800 mt-2">
                Routing: {selectedStream.sourceId} → {selectedStream.targetId}
              </h3>
            </div>

            <div className="space-y-3.5 border-t border-slate-100 pt-3">
              <span className="text-[11px] font-bold text-slate-500 uppercase flex items-center gap-1.5">
                <Sliders size={13} className="text-slate-400" /> State Variables
              </span>
              
              <div className="space-y-3 bg-slate-50 p-4 border border-slate-100 rounded-xl">
                <div>
                  <label className="label">Temperature (°C)</label>
                  <input type="number" className="input text-xs bg-white" value={selectedStream.specifications?.temperature_C ?? ""} onChange={e => handleUpdateStreamProperty("temperature_C", e.target.value)} />
                </div>
                <div>
                  <label className="label">Pressure (kPa)</label>
                  <input type="number" className="input text-xs bg-white" value={selectedStream.specifications?.pressure_kPa ?? ""} onChange={e => handleUpdateStreamProperty("pressure_kPa", e.target.value)} />
                </div>
                <div>
                  <label className="label">Mass Flowrate (kg/s)</label>
                  <input type="number" className="input text-xs bg-white" value={selectedStream.specifications?.mass_flow_kg_s ?? ""} onChange={e => handleUpdateStreamProperty("mass_flow_kg_s", e.target.value)} />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center text-gray-400 text-xs">
            <HelpCircle size={24} className="text-gray-300 mb-1" />
            Click any labeled pipeline edge directly on the canvas to specify its values.
          </div>
        )}
      </div>
    </div>
  );
}