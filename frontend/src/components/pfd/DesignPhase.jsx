import React, { useState, useMemo, useEffect } from "react";
import ReactFlow, { Background, Controls, Handle, Position, useReactFlow } from "reactflow";
import { Plus, Link, Layers } from "lucide-react";
import { COMPONENT_REGISTRY } from "../../constants/componentRegistry";
import "reactflow/dist/style.css";

const GenericStaticNode = ({ data }) => {
  const meta = COMPONENT_REGISTRY[data.type] || { label: "Unknown Node", category: "Core Operations" };
  const inlets = data.ports?.inlets || ["feed"];
  const outlets = data.ports?.outlets || ["outlet"];

  return (
    <div className="border-2 border-slate-300 bg-white rounded-xl p-3.5 min-w-[200px] shadow-md font-sans border-t-slate-600 relative">
      {/* Inlet ports */}
      <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-around pointer-events-none my-4">
        {inlets.map(p => (
          <div key={p} className="relative flex items-center">
            <Handle type="target" position={Position.Left} id={p} className="w-2 h-2 bg-slate-400 border border-white" style={{ left: "-5px", top: "auto" }} isConnectable={false} />
            <span className="text-[7px] font-mono ml-1.5 bg-white/80 px-0.5 text-slate-400">{p}</span>
          </div>
        ))}
      </div>

      <div className="px-2">
        <div className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">{meta.category}</div>
        <div className="text-xs font-bold text-slate-800 mt-0.5">{data.name}</div>
        <div className="text-[10px] text-brand-600 font-mono font-bold mt-1 bg-slate-50 px-2 py-0.5 rounded border border-slate-100 inline-block">
          {data.nodeId}
        </div>
      </div>

      {/* Outlet ports */}
      <div className="absolute right-0 top-0 bottom-0 flex flex-col justify-around pointer-events-none my-4">
        {outlets.map(p => (
          <div key={p} className="relative flex items-center justify-end">
            <span className="text-[7px] font-mono mr-1.5 bg-white/80 px-0.5 text-slate-400">{p}</span>
            <Handle type="source" position={Position.Right} id={p} className="w-2 h-2 bg-slate-700 border border-white" style={{ right: "-5px", top: "auto" }} isConnectable={false} />
          </div>
        ))}
      </div>
    </div>
  );
};

const nodeTypes = { unit: GenericStaticNode };

export default function DesignPhase({ canvasState, updateCanvasState }) {
  const [activeMenu, setActiveMenu] = useState("ADD");
  const registryKeys = useMemo(() => Object.keys(COMPONENT_REGISTRY), []);
  const [selectedRegistryKey, setSelectedRegistryKey] = useState(registryKeys[0] || "PUMP");
  const [newCompName, setNewCompName] = useState("");

  // Connection selections configuration state hooks
  const [linkSource, setLinkSource] = useState("");
  const [linkSourcePort, setLinkSourcePort] = useState("");
  const [linkTarget, setLinkTarget] = useState("");
  const [linkTargetPort, setLinkTargetPort] = useState("");

  const reactFlowInstance = useReactFlow();
  const comps = canvasState.components || [];
  const conns = canvasState.connections || [];

  const flowNodes = useMemo(() => {
    return comps.map((c, idx) => {
      const colIdx = idx % 3;
      const rowIdx = Math.floor(idx / 3);
      const persistentPosition = c.position || { x: 60 + colIdx * 260, y: 60 + rowIdx * 160 };
      return {
        id: c.id,
        type: "unit",
        position: persistentPosition,
        data: { name: c.name, type: c.type, nodeId: c.id, ports: c.ports },
        draggable: false
      };
    });
  }, [comps]);

  const flowEdges = useMemo(() => {
    return conns.map(c => ({
      id: c.id,
      source: c.sourceId,
      sourceHandle: c.sourcePort,
      target: c.targetId,
      targetHandle: c.targetPort,
      animated: true,
      label: c.streamName, // Displays stream name overlay right onto line pipes layout
      labelStyle: { fill: "#0369a1", fontWeight: 700, fontSize: "10px", fontFamily: "monospace" },
      style: { stroke: "#0284c7", strokeWidth: 2.5 }
    }));
  }, [conns]);

  useEffect(() => {
    if (flowNodes.length > 0) {
      setTimeout(() => reactFlowInstance.fitView({ padding: 0.2, duration: 150 }), 50);
    }
  }, [flowNodes.length, reactFlowInstance]);

  const handleAddComponent = (e) => {
    e?.preventDefault();
    if (!newCompName.trim()) return;
    const blueprint = COMPONENT_REGISTRY[selectedRegistryKey];
    if (!blueprint) return;

    const id = blueprint.idPrefix + (comps.length + 101);
    const newComponent = {
      id,
      type: selectedRegistryKey,
      name: newCompName.trim(),
      ports: blueprint.ports,
      specifications: { parameters: {} }
    };

    updateCanvasState(prev => ({ ...prev, components: [...(prev.components || []), newComponent] }));
    setNewCompName("");
  };

  const handleCreateConnection = () => {
    if (!linkSource || !linkTarget || !linkSourcePort || !linkTargetPort) return;
    
    // Serialized stream index names allocation mapping pattern (S-101, S-102...)
    const streamNumber = conns.length + 101;
    const streamName = `S-${streamNumber}`;
    const edgeId = `edge_stream_${streamName}`;

    const newLink = {
      id: edgeId,
      streamName, // Persistent named label used in next phase forms
      sourceId: linkSource,
      sourcePort: linkSourcePort,
      targetId: linkTarget,
      targetPort: linkTargetPort,
      specifications: { temperature_C: "", pressure_kPa: "", mass_flow_kg_s: "" } // Attached text properties placeholder
    };

    updateCanvasState(prev => ({ ...prev, connections: [...(prev.connections || []), newLink] }));
    
    setLinkSource("");
    setLinkSourcePort("");
    setLinkTarget("");
    setLinkTargetPort("");
  };

  const activeSourceComponent = comps.find(c => c.id === linkSource);
  const activeTargetComponent = comps.find(c => c.id === linkTarget);

  return (
    <div className="flex-1 flex h-full overflow-hidden">
      <div className="flex-1 h-full relative bg-slate-50">
        <ReactFlow nodes={flowNodes} edges={flowEdges} nodeTypes={nodeTypes} fitView>
          <Background color="#cbd5e1" gap={18} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>

      <div className="w-80 border-l border-gray-200 bg-white flex flex-col h-full z-10 shadow-lg overflow-hidden">
        <div className="grid grid-cols-2 border-b border-gray-200 bg-gray-50 p-1 text-xs font-semibold flex-shrink-0">
          <button onClick={() => setActiveMenu("ADD")} className={`py-2 text-center rounded-md transition-all ${activeMenu === "ADD" ? "bg-white shadow-sm text-brand-600" : "text-gray-500 hover:text-gray-700"}`}>
            Add Component
          </button>
          <button onClick={() => setActiveMenu("CONNECT")} className={`py-2 text-center rounded-md transition-all ${activeMenu === "CONNECT" ? "bg-white shadow-sm text-brand-600" : "text-gray-500 hover:text-gray-700"}`}>
            Connect Streams
          </button>
        </div>

        <div className="p-4 flex-1 overflow-y-auto min-h-0 space-y-4">
          {activeMenu === "ADD" && (
            <div className="space-y-3.5">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Deploy Equipment Node</p>
              <div>
                <label className="label">Operation Class</label>
                <select className="input text-xs" value={selectedRegistryKey} onChange={e => setSelectedRegistryKey(e.target.value)}>
                  {registryKeys.map(k => (
                    <option key={k} value={k}>{COMPONENT_REGISTRY[k].label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Component Label</label>
                <input type="text" className="input text-xs" value={newCompName} onChange={e => setNewCompName(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAddComponent(e)} />
              </div>
              <button type="button" onClick={handleAddComponent} disabled={!newCompName.trim()} className="btn-primary w-full text-xs font-bold py-2.5">
                Add Block
              </button>
            </div>
          )}

          {activeMenu === "CONNECT" && (
            <div className="space-y-4">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Stream Connection Matrix</p>
              
              <div className="p-3 border border-slate-100 bg-slate-50 rounded-xl space-y-2">
                <label className="label">Source Component</label>
                <select className="input text-xs bg-white" value={linkSource} onChange={e => { setLinkSource(e.target.value); setLinkSourcePort(""); }}>
                  <option value="">-- Choose Source --</option>
                  {comps.map(c => <option key={c.id} value={c.id}>{c.name} [{c.id}]</option>)}
                </select>
                {activeSourceComponent && (
                  <select className="input text-xs bg-white mt-2" value={linkSourcePort} onChange={e => setLinkSourcePort(e.target.value)}>
                    <option value="">-- Choose Outlet Port --</option>
                    {(activeSourceComponent.ports?.outlets || []).map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                )}
              </div>

              <div className="p-3 border border-slate-100 bg-slate-50 rounded-xl space-y-2">
                <label className="label">Destination Component</label>
                <select className="input text-xs bg-white" value={linkTarget} onChange={e => { setLinkTarget(e.target.value); setLinkTargetPort(""); }}>
                  <option value="">-- Choose Destination --</option>
                  {comps.filter(c => c.id !== linkSource).map(c => <option key={c.id} value={c.id}>{c.name} [{c.id}]</option>)}
                </select>
                {activeTargetComponent && (
                  <select className="input text-xs bg-white mt-2" value={linkTargetPort} onChange={e => setLinkTargetPort(e.target.value)}>
                    <option value="">-- Choose Target Inlet Port --</option>
                    {(activeTargetComponent.ports?.inlets || []).map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                )}
              </div>

              <button onClick={handleCreateConnection} disabled={!linkSource || !linkTarget || !linkSourcePort || !linkTargetPort} className="btn-primary w-full text-xs font-bold py-2.5 disabled:opacity-40">
                Establish Serialized Stream Line
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}