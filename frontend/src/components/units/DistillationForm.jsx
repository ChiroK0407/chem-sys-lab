import { useState } from "react";
import { Play, RotateCcw, Loader2, Plus, Trash2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import client from "../../api/client";

const defaultComponents = () => ([
  { name:"benzene", z:0.40, alpha:2.5, is_light_key:true,  is_heavy_key:false, x_distillate:0.95, T_boil_K:"", MW:"" },
  { name:"toluene", z:0.60, alpha:1.0, is_light_key:false, is_heavy_key:true,  x_distillate:0.05, T_boil_K:"", MW:"" },
]);

const CRUDE_PRESET = [
  { name:"lpg",      z:0.05, alpha:8.0,  is_light_key:false, is_heavy_key:false, x_distillate:null, T_boil_K:310, MW:50  },
  { name:"naphtha",  z:0.20, alpha:3.5,  is_light_key:true,  is_heavy_key:false, x_distillate:0.90, T_boil_K:390, MW:110 },
  { name:"kerosene", z:0.25, alpha:1.0,  is_light_key:false, is_heavy_key:true,  x_distillate:0.05, T_boil_K:510, MW:165 },
  { name:"gas_oil",  z:0.30, alpha:0.3,  is_light_key:false, is_heavy_key:false, x_distillate:null, T_boil_K:620, MW:240 },
  { name:"residue",  z:0.20, alpha:0.05, is_light_key:false, is_heavy_key:false, x_distillate:null, T_boil_K:750, MW:400 },
];

function ComponentRow({ comp, idx, onChange, onRemove, canRemove }) {
  const set = (f) => (e) => onChange({ ...comp, [f]: e.target.value });
  const num = (f) => (e) => onChange({ ...comp, [f]: parseFloat(e.target.value) || 0 });
  const bool = (f) => (e) => onChange({ ...comp, [f]: e.target.checked });

  const isKey = comp.is_light_key || comp.is_heavy_key;

  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="py-2 pr-2">
        <input className="input text-xs py-1.5" value={comp.name} onChange={set("name")} />
      </td>
      <td className="py-2 pr-2">
        <input type="number" className="input text-xs py-1.5 w-20" value={comp.z}
          onChange={num("z")} step="0.01" min="0" max="1" />
      </td>
      <td className="py-2 pr-2">
        <input type="number" className="input text-xs py-1.5 w-20" value={comp.alpha}
          onChange={num("alpha")} step="0.1" min="0.01" />
      </td>
      <td className="py-2 pr-2 text-center">
        <input type="checkbox" checked={comp.is_light_key} onChange={bool("is_light_key")}
          className="rounded text-green-600" />
      </td>
      <td className="py-2 pr-2 text-center">
        <input type="checkbox" checked={comp.is_heavy_key} onChange={bool("is_heavy_key")}
          className="rounded text-green-600" />
      </td>
      <td className="py-2 pr-2">
        {isKey
          ? <input type="number" className="input text-xs py-1.5 w-20" value={comp.x_distillate ?? ""}
              onChange={num("x_distillate")} step="0.01" min="0" max="1" />
          : <span className="text-xs text-gray-400 px-2">auto</span>
        }
      </td>
      <td className="py-2 pr-2">
        <input type="number" className="input text-xs py-1.5 w-20" value={comp.T_boil_K ?? ""}
          onChange={set("T_boil_K")} placeholder="optional" />
      </td>
      <td className="py-2 pr-2">
        <input type="number" className="input text-xs py-1.5 w-16" value={comp.MW ?? ""}
          onChange={set("MW")} placeholder="opt" />
      </td>
      <td className="py-2">
        {canRemove && (
          <button onClick={onRemove} className="text-gray-400 hover:text-red-500">
            <Trash2 size={13} />
          </button>
        )}
      </td>
    </tr>
  );
}

export default function DistillationForm({ onResult }) {
  const [unitId, setUnitId]       = useState("T-101");
  const [comps, setComps]         = useState(defaultComponents());
  const [F, setF]                 = useState(100.0);
  const [q, setQ]                 = useState(1.0);
  const [ratio, setRatio]         = useState(1.5);
  const [eff, setEff]             = useState(0.70);
  const [condType, setCondType]   = useState("total");
  const [lambda_, setLambda]      = useState(33000);

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: (payload) => client.post("/solve/distillation?include_log=true", payload).then(r => r.data),
  });

  const zSum = comps.reduce((s, c) => s + (parseFloat(c.z) || 0), 0);
  const zOk  = Math.abs(zSum - 1.0) < 0.005;

  function updateComp(i, updated) { setComps(comps.map((c, idx) => idx === i ? updated : c)); }
  function addComp() { setComps([...comps, { name:`comp_${comps.length+1}`, z:0.0, alpha:1.0, is_light_key:false, is_heavy_key:false, x_distillate:null, T_boil_K:"", MW:"" }]); }
  function removeComp(i) { if (comps.length > 2) setComps(comps.filter((_, idx) => idx !== i)); }

  function handleSolve() {
    const components = comps.map(c => ({
      name: c.name,
      z: parseFloat(c.z) || 0,
      alpha: parseFloat(c.alpha) || 1,
      is_light_key: c.is_light_key,
      is_heavy_key: c.is_heavy_key,
      x_distillate: (c.is_light_key || c.is_heavy_key) ? parseFloat(c.x_distillate) : null,
      T_boil_K: c.T_boil_K ? parseFloat(c.T_boil_K) : null,
      MW: c.MW ? parseFloat(c.MW) : null,
    }));
    mutate({ unit_id:unitId, components, F_mol_s:F, q, R_Rmin_ratio:ratio,
             tray_efficiency:eff, condenser_type:condType, latent_heat_J_mol:lambda_ },
           { onSuccess: onResult });
  }

  return (
    <div className="space-y-4">

      {/* Config */}
      <div className="card p-4 space-y-3">
        <p className="section-title">Column Configuration</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div><label className="label">Unit ID</label>
            <input className="input" value={unitId} onChange={e => setUnitId(e.target.value)} /></div>
          <div><label className="label">Feed F (mol/s)</label>
            <input type="number" className="input" value={F} onChange={e => setF(parseFloat(e.target.value)||100)} /></div>
          <div><label className="label">Feed condition q</label>
            <select className="select" value={q} onChange={e => setQ(parseFloat(e.target.value))}>
              <option value={1.0}>q = 1.0  (bubble point)</option>
              <option value={0.0}>q = 0.0  (dew point)</option>
              <option value={0.5}>q = 0.5  (50% vapour)</option>
              <option value={1.2}>q = 1.2  (subcooled)</option>
            </select></div>
          <div><label className="label">R / R_min</label>
            <input type="number" className="input" value={ratio} onChange={e => setRatio(parseFloat(e.target.value)||1.5)} step="0.1" min="1.01" /></div>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div><label className="label">Tray efficiency</label>
            <input type="number" className="input" value={eff} onChange={e => setEff(parseFloat(e.target.value)||0.7)} step="0.05" min="0.1" max="1" /></div>
          <div><label className="label">Condenser</label>
            <select className="select" value={condType} onChange={e => setCondType(e.target.value)}>
              <option value="total">Total (liquid)</option>
              <option value="partial">Partial (vapour)</option>
            </select></div>
          <div><label className="label">λ (J/mol)</label>
            <input type="number" className="input" value={lambda_} onChange={e => setLambda(parseFloat(e.target.value)||30000)} step="1000" /></div>
          <div className="flex items-end">
            <button onClick={() => setComps(CRUDE_PRESET.map(c => ({...c})))}
              className="btn-secondary text-xs py-1.5 w-full">
              Load crude preset
            </button>
          </div>
        </div>
      </div>

      {/* Component table */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <p className="section-title">Feed components</p>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full
            ${zOk ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
            Σz = {zSum.toFixed(4)}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                {["Name","z (feed)","α (rel. vol.)","LK","HK","x_distillate","T_b (K)","MW",""].map(h => (
                  <th key={h} className="pb-2 text-left text-xs font-medium text-gray-500 pr-2">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comps.map((c, i) => (
                <ComponentRow key={i} comp={c} idx={i}
                  onChange={(u) => updateComp(i, u)}
                  onRemove={() => removeComp(i)}
                  canRemove={comps.length > 2} />
              ))}
            </tbody>
          </table>
        </div>
        <button onClick={addComp} className="btn-secondary text-xs py-1.5 mt-3">
          <Plus size={13} /> Add component
        </button>
        <p className="text-xs text-gray-400 mt-2">
          LK = light key, HK = heavy key. x_distillate required for key components only.
          Non-keys are auto-distributed by relative volatility.
        </p>
      </div>

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error?.message ?? "An error occurred."}
        </div>
      )}

      <div className="flex gap-3">
        <button className="btn-primary" onClick={handleSolve}
          disabled={isPending || !zOk}>
          {isPending ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          {isPending ? "Solving…" : "Solve"}
        </button>
        <button className="btn-secondary" onClick={() => { setComps(defaultComponents()); onResult(null); }}>
          <RotateCcw size={15} /> Reset
        </button>
      </div>
    </div>
  );
}
