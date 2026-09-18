import { useState } from "react";
import { Play, RotateCcw, Loader2, Plus, Trash2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import client from "../../api/client";
import SectionedForm from "../common/SectionedForm";

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

const DEFAULT_VALUES = {
  unit_id: "T-101",
  F_mol_s: 100.0,
  q: 1.0,
  R_Rmin_ratio: 1.5,
  tray_efficiency: 0.70,
  condenser_type: "total",
  latent_heat_J_mol: 33000,
  components: defaultComponents(),
};

function ComponentRow({ comp, onChange, onRemove, canRemove }) {
  const set = (f) => (e) => onChange({ ...comp, [f]: e.target.value });
  const num = (f) => (e) => onChange({ ...comp, [f]: parseFloat(e.target.value) || 0 });
  const bool = (f) => (e) => onChange({ ...comp, [f]: e.target.checked });
  const isKey = comp.is_light_key || comp.is_heavy_key;

  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="py-2 pr-2"><input className="input text-xs py-1.5" value={comp.name} onChange={set("name")} /></td>
      <td className="py-2 pr-2"><input type="number" className="input text-xs py-1.5 w-20" value={comp.z} onChange={num("z")} step="0.01" min="0" max="1" /></td>
      <td className="py-2 pr-2"><input type="number" className="input text-xs py-1.5 w-20" value={comp.alpha} onChange={num("alpha")} step="0.1" min="0.01" /></td>
      <td className="py-2 pr-2 text-center"><input type="checkbox" checked={comp.is_light_key} onChange={bool("is_light_key")} className="rounded text-green-600" /></td>
      <td className="py-2 pr-2 text-center"><input type="checkbox" checked={comp.is_heavy_key} onChange={bool("is_heavy_key")} className="rounded text-green-600" /></td>
      <td className="py-2 pr-2">
        {isKey
          ? <input type="number" className="input text-xs py-1.5 w-20" value={comp.x_distillate ?? ""} onChange={num("x_distillate")} step="0.01" min="0" max="1" />
          : <span className="text-xs text-gray-400 px-2">auto</span>}
      </td>
      <td className="py-2 pr-2"><input type="number" className="input text-xs py-1.5 w-20" value={comp.T_boil_K ?? ""} onChange={set("T_boil_K")} placeholder="optional" /></td>
      <td className="py-2 pr-2"><input type="number" className="input text-xs py-1.5 w-16" value={comp.MW ?? ""} onChange={set("MW")} placeholder="opt" /></td>
      <td className="py-2">{canRemove && (
        <button type="button" onClick={onRemove} className="text-gray-400 hover:text-red-500"><Trash2 size={13} /></button>
      )}</td>
    </tr>
  );
}

function FeedComponentsSection(draft, setField) {
  const comps = draft.components ?? [];
  const zSum = comps.reduce((s, c) => s + (parseFloat(c.z) || 0), 0);
  const zOk = Math.abs(zSum - 1.0) < 0.005;

  function updateComp(i, updated) { setField("components", comps.map((c, idx) => (idx === i ? updated : c))); }
  function addComp() { setField("components", [...comps, { name:`comp_${comps.length + 1}`, z:0.0, alpha:1.0, is_light_key:false, is_heavy_key:false, x_distillate:null, T_boil_K:"", MW:"" }]); }
  function removeComp(i) { if (comps.length > 2) setField("components", comps.filter((_, idx) => idx !== i)); }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${zOk ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
          Σz = {zSum.toFixed(4)}
        </span>
        <button type="button" onClick={() => setField("components", CRUDE_PRESET.map((c) => ({ ...c })))} className="btn-secondary text-xs py-1.5">
          Load crude preset
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              {["Name","z (feed)","α (rel. vol.)","LK","HK","x_distillate","T_b (K)","MW",""].map((h) => (
                <th key={h} className="pb-2 text-left text-xs font-medium text-gray-500 pr-2">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {comps.map((c, i) => (
              <ComponentRow key={i} comp={c} onChange={(u) => updateComp(i, u)} onRemove={() => removeComp(i)} canRemove={comps.length > 2} />
            ))}
          </tbody>
        </table>
      </div>
      <button type="button" onClick={addComp} className="btn-secondary text-xs py-1.5 mt-3"><Plus size={13} /> Add component</button>
      <p className="text-xs text-gray-400 mt-2">
        LK = light key, HK = heavy key. x_distillate required for key components only. Non-keys are auto-distributed by relative volatility.
      </p>
    </div>
  );
}

const SCHEMA = [
  {
    id: "config",
    label: "Column Configuration",
    description: "Feed rate, reflux policy, and condenser type.",
    fields: [
      { key: "unit_id", label: "Unit ID", type: "text", required: true },
      { key: "F_mol_s", label: "Feed F", category: "molarFlow", required: true },
      {
        key: "q", label: "Feed condition q", type: "select", parse: parseFloat,
        options: [
          { value: 1.0, label: "q = 1.0  (bubble point)" },
          { value: 0.0, label: "q = 0.0  (dew point)" },
          { value: 0.5, label: "q = 0.5  (50% vapour)" },
          { value: 1.2, label: "q = 1.2  (subcooled)" },
        ],
      },
      { key: "R_Rmin_ratio", label: "R / R_min", category: "dimensionless", step: 0.1, min: 1.01, required: true },
      { key: "tray_efficiency", label: "Tray efficiency", category: "fraction", step: 0.05 },
      {
        key: "condenser_type", label: "Condenser", type: "select",
        options: [
          { value: "total", label: "Total (liquid)" },
          { value: "partial", label: "Partial (vapour)" },
        ],
      },
      { key: "latent_heat_J_mol", label: "Latent heat λ", category: "molarEnergy", step: 1000 },
    ],
  },
  {
    id: "components",
    label: "Feed Components",
    description: "One row per component. Exactly one light key and one heavy key required.",
    keys: ["components"],
    custom: FeedComponentsSection,
    validate: (draft) => {
      const comps = draft.components ?? [];
      const zSum = comps.reduce((s, c) => s + (parseFloat(c.z) || 0), 0);
      if (Math.abs(zSum - 1.0) > 0.005) return `Feed mole fractions sum to ${zSum.toFixed(4)}, not 1.0.`;
      const lk = comps.filter((c) => c.is_light_key).length;
      const hk = comps.filter((c) => c.is_heavy_key).length;
      if (lk !== 1 || hk !== 1) return "Exactly one light key and one heavy key component are required.";
      return true;
    },
  },
];

export default function DistillationForm({ onResult }) {
  const [values, setValues] = useState(DEFAULT_VALUES);
  const [activeSectionId, setActiveSectionId] = useState(SCHEMA[0].id);
  const [savedSectionIds, setSavedSectionIds] = useState(new Set());

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: (payload) => client.post("/solve/distillation?include_log=true", payload).then((r) => r.data),
  });

  function handleChange(key, val) {
    setValues((v) => ({ ...v, [key]: val }));
  }

  function handleSectionSaved(id) {
    setSavedSectionIds((prev) => new Set(prev).add(id));
  }

  const allSaved = savedSectionIds.size === SCHEMA.length;

  function handleSolve() {
    const components = values.components.map((c) => ({
      name: c.name,
      z: parseFloat(c.z) || 0,
      alpha: parseFloat(c.alpha) || 1,
      is_light_key: c.is_light_key,
      is_heavy_key: c.is_heavy_key,
      x_distillate: (c.is_light_key || c.is_heavy_key) ? parseFloat(c.x_distillate) : null,
      T_boil_K: c.T_boil_K ? parseFloat(c.T_boil_K) : null,
      MW: c.MW ? parseFloat(c.MW) : null,
    }));
    mutate({
      unit_id: values.unit_id, components, F_mol_s: values.F_mol_s, q: values.q,
      R_Rmin_ratio: values.R_Rmin_ratio, tray_efficiency: values.tray_efficiency,
      condenser_type: values.condenser_type, latent_heat_J_mol: values.latent_heat_J_mol,
    }, { onSuccess: onResult });
  }

  function handleResetAll() {
    setValues(DEFAULT_VALUES);
    setSavedSectionIds(new Set());
    setActiveSectionId(SCHEMA[0].id);
    onResult(null);
  }

  return (
    <div className="space-y-4">
      <SectionedForm
        schema={SCHEMA}
        values={values}
        onChange={handleChange}
        activeId={activeSectionId}
        onActiveChange={setActiveSectionId}
        savedSectionIds={savedSectionIds}
        onSectionSaved={handleSectionSaved}
      />

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error?.message ?? "An error occurred."}
        </div>
      )}

      <div className="flex gap-3">
        <button className="btn-primary" onClick={handleSolve} disabled={isPending || !allSaved}>
          {isPending ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          {isPending ? "Solving…" : allSaved ? "Solve" : "Save all sections to solve"}
        </button>
        <button className="btn-secondary" onClick={handleResetAll}>
          <RotateCcw size={15} /> Reset all
        </button>
      </div>
    </div>
  );
}
