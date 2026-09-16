import { useState } from "react";
import { Play, RotateCcw, Loader2, Plus, Trash2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import client from "../../api/client";

async function solveMixer(payload, includeLog = true) {
  const { data } = await client.post(`/solve/mixer?include_log=${includeLog}`, payload);
  return data;
}

const defaultStream = (n) => ({
  name: `inlet_${n}`,
  fluid_id: null,
  temperature_c: 60,
  pressure_kpa: 200,
  mass_flowrate_kg_s: 2.0,
  cp_J_kgK: 4182,
  density_kg_m3: 997,
  viscosity_Pa_s: 0.00089,
  thermal_conductivity: 0.607,
  phase: "liquid",
});

function StreamRow({ index, stream, onChange, onRemove, canRemove }) {
  const set = (f) => (e) => onChange({ ...stream, [f]: e.target.value });
  const num = (f) => (e) => onChange({ ...stream, [f]: parseFloat(e.target.value) || 0 });

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Inlet {index + 1}
        </p>
        {canRemove && (
          <button onClick={onRemove} className="text-gray-400 hover:text-red-500 transition-colors">
            <Trash2 size={14} />
          </button>
        )}
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div>
          <label className="label">Name</label>
          <input className="input" value={stream.name} onChange={set("name")} />
        </div>
        <div>
          <label className="label">T (°C)</label>
          <input type="number" className="input" value={stream.temperature_c} onChange={num("temperature_c")} />
        </div>
        <div>
          <label className="label">Flow (kg/s)</label>
          <input type="number" className="input" value={stream.mass_flowrate_kg_s} onChange={num("mass_flowrate_kg_s")} step="0.1" />
        </div>
        <div>
          <label className="label">Cp (J/kg·K)</label>
          <input type="number" className="input" value={stream.cp_J_kgK} onChange={num("cp_J_kgK")} step="10" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="label">Density (kg/m³)</label>
          <input type="number" className="input" value={stream.density_kg_m3} onChange={num("density_kg_m3")} />
        </div>
        <div>
          <label className="label">Viscosity (Pa·s)</label>
          <input type="number" className="input" value={stream.viscosity_Pa_s} onChange={num("viscosity_Pa_s")} step="0.0001" />
        </div>
        <div>
          <label className="label">k (W/m·K)</label>
          <input type="number" className="input" value={stream.thermal_conductivity} onChange={num("thermal_conductivity")} step="0.01" />
        </div>
      </div>
    </div>
  );
}

export default function MixerForm({ onResult }) {
  const [unitId, setUnitId]       = useState("MX-101");
  const [outName, setOutName]     = useState("mixed_outlet");
  const [streams, setStreams]     = useState([defaultStream(1), defaultStream(2)]);

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: ({ payload }) => solveMixer(payload, true),
  });

  function addStream() {
    if (streams.length < 10)
      setStreams([...streams, defaultStream(streams.length + 1)]);
  }

  function removeStream(i) {
    if (streams.length > 2)
      setStreams(streams.filter((_, idx) => idx !== i));
  }

  function updateStream(i, updated) {
    setStreams(streams.map((s, idx) => idx === i ? updated : s));
  }

  function handleSolve() {
    const payload = {
      unit_id: unitId,
      outlet_name: outName,
      inlet_streams: streams.map(s => {
        const copy = { ...s };
        delete copy.fluid_id;
        return copy;
      }),
    };
    mutate({ payload }, { onSuccess: onResult });
  }

  return (
    <div className="space-y-4">
      <div className="card p-4 space-y-3">
        <p className="section-title">Mixer Configuration</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Unit ID</label>
            <input className="input" value={unitId} onChange={e => setUnitId(e.target.value)} />
          </div>
          <div>
            <label className="label">Outlet stream name</label>
            <input className="input" value={outName} onChange={e => setOutName(e.target.value)} />
          </div>
        </div>
      </div>

      {streams.map((s, i) => (
        <StreamRow key={i} index={i} stream={s}
          onChange={(u) => updateStream(i, u)}
          onRemove={() => removeStream(i)}
          canRemove={streams.length > 2} />
      ))}

      {streams.length < 10 && (
        <button onClick={addStream} className="btn-secondary w-full">
          <Plus size={14} /> Add inlet stream
        </button>
      )}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error?.message ?? "An error occurred."}
        </div>
      )}

      <div className="flex gap-3">
        <button className="btn-primary" onClick={handleSolve} disabled={isPending}>
          {isPending ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          {isPending ? "Solving…" : "Solve"}
        </button>
        <button className="btn-secondary" onClick={() => { setStreams([defaultStream(1), defaultStream(2)]); onResult(null); }}>
          <RotateCcw size={15} /> Reset
        </button>
      </div>
    </div>
  );
}
