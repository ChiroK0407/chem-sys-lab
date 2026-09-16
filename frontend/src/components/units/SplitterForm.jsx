import { useState } from "react";
import { Play, RotateCcw, Loader2, Plus, Trash2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import StreamInputPanel from "../shared/StreamInputPanel";
import client from "../../api/client";

async function solveSplitter(payload, includeLog = true) {
  const { data } = await client.post(`/solve/splitter?include_log=${includeLog}`, payload);
  return data;
}

const defaultFeed = () => ({
  name: "feed", fluid_id: null,
  temperature_c: 60, pressure_kpa: 200,
  mass_flowrate_kg_s: 10.0, cp_J_kgK: 4182,
  density_kg_m3: 997, viscosity_Pa_s: 0.00089,
  thermal_conductivity: 0.607, phase: "liquid",
});

export default function SplitterForm({ onResult }) {
  const [unitId, setUnitId]   = useState("SP-101");
  const [feed, setFeed]       = useState(defaultFeed());
  const [mode, setMode]       = useState("explicit");  // "explicit" | "equal"
  const [outlets, setOutlets] = useState([
    { name: "overhead", fraction: 0.6 },
    { name: "bottoms",  fraction: 0.4 },
  ]);
  const [nEqual, setNEqual]   = useState(2);

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: ({ payload }) => solveSplitter(payload, true),
  });

  function addOutlet() {
    if (outlets.length < 10)
      setOutlets([...outlets, { name: `outlet_${outlets.length + 1}`, fraction: 0 }]);
  }
  function removeOutlet(i) {
    if (outlets.length > 2) setOutlets(outlets.filter((_, idx) => idx !== i));
  }
  function updateOutlet(i, field, val) {
    setOutlets(outlets.map((o, idx) => idx === i ? { ...o, [field]: val } : o));
  }

  const totalFrac = outlets.reduce((s, o) => s + (parseFloat(o.fraction) || 0), 0);
  const fracOk    = Math.abs(totalFrac - 1.0) < 1e-4;

  function handleSolve() {
    const stream = { ...feed }; delete stream.fluid_id;
    const payload = { unit_id: unitId, feed_stream: stream };
    if (mode === "explicit") {
      payload.split_fractions = Object.fromEntries(
        outlets.map(o => [o.name, parseFloat(o.fraction) || 0])
      );
    } else {
      payload.n_outlets = nEqual;
    }
    mutate({ payload }, { onSuccess: onResult });
  }

  return (
    <div className="space-y-4">
      <div className="card p-4 space-y-3">
        <p className="section-title">Splitter Configuration</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Unit ID</label>
            <input className="input" value={unitId} onChange={e => setUnitId(e.target.value)} />
          </div>
          <div>
            <label className="label">Split mode</label>
            <select className="select" value={mode} onChange={e => setMode(e.target.value)}>
              <option value="explicit">Explicit fractions</option>
              <option value="equal">Equal split</option>
            </select>
          </div>
        </div>
      </div>

      <div className="card p-5">
        <StreamInputPanel label="Feed stream" value={feed} onChange={setFeed} />
      </div>

      {mode === "explicit" ? (
        <div className="card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="section-title">Outlet fractions</p>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full
              ${fracOk ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
              Σ = {totalFrac.toFixed(4)}
            </span>
          </div>
          {outlets.map((o, i) => (
            <div key={i} className="grid grid-cols-5 gap-2 items-end">
              <div className="col-span-3">
                <label className="label">Outlet name</label>
                <input className="input" value={o.name}
                  onChange={e => updateOutlet(i, "name", e.target.value)} />
              </div>
              <div>
                <label className="label">Fraction</label>
                <input type="number" className="input" value={o.fraction} step="0.05" min="0" max="1"
                  onChange={e => updateOutlet(i, "fraction", e.target.value)} />
              </div>
              <button onClick={() => removeOutlet(i)} disabled={outlets.length <= 2}
                className="text-gray-400 hover:text-red-500 disabled:opacity-30 pb-2">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          {outlets.length < 10 && (
            <button onClick={addOutlet} className="btn-secondary text-xs py-1.5">
              <Plus size={13} /> Add outlet
            </button>
          )}
        </div>
      ) : (
        <div className="card p-4">
          <label className="label">Number of equal outlets</label>
          <input type="number" className="input w-32" value={nEqual} min="2" max="10"
            onChange={e => setNEqual(parseInt(e.target.value) || 2)} />
          <p className="text-xs text-gray-400 mt-1">
            Each outlet receives {nEqual > 0 ? (100 / nEqual).toFixed(2) : 0}% of the feed
          </p>
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error?.message ?? "An error occurred."}
        </div>
      )}

      <div className="flex gap-3">
        <button className="btn-primary" onClick={handleSolve}
          disabled={isPending || (mode === "explicit" && !fracOk)}>
          {isPending ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          {isPending ? "Solving…" : "Solve"}
        </button>
        <button className="btn-secondary" onClick={() => { setFeed(defaultFeed()); onResult(null); }}>
          <RotateCcw size={15} /> Reset
        </button>
      </div>
    </div>
  );
}
