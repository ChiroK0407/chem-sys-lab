/**
 * frontend/src/components/common/SectionedForm.jsx
 *
 * Generic, schema-driven replacement for "one long scrolling form".
 * Renders a SectionSidebar + the currently active section only.
 *
 * A `schema` is just data: an ordered array of sections, each either a
 * plain list of fields (rendered automatically via UnitField / native
 * select / text) or a `custom` render function for anything that doesn't
 * fit the flat label/value/unit pattern (e.g. Distillation's feed
 * component table).
 *
 * Behaviour:
 *  - Only the first section starts unlocked. Section i unlocks once
 *    section i-1 has been saved.
 *  - Each section edits a local "draft" (seeded from the parent's
 *    committed `values` whenever you open/re-open it, or hit Reset).
 *    Nothing reaches the parent's `values` — and nothing is sent to the
 *    backend — until you hit Save on that section.
 *  - Save validates required fields (+ an optional custom `validate` on
 *    the section), commits the draft up via onSectionSave, marks the
 *    section saved, and auto-advances to the next section if it just
 *    became unlocked.
 *
 * This file is the ONLY place the sidebar/section/lock/save mechanics
 * live — every unit form just supplies a schema + values + onChange.
 */

import { useEffect, useState } from "react";
import { Save, RotateCcw, AlertCircle } from "lucide-react";
import SectionSidebar from "./SectionSidebar";
import UnitField from "./UnitField";

function fieldsToDraft(fields, values) {
  const draft = {};
  for (const f of fields) draft[f.key] = values[f.key];
  return draft;
}

export default function SectionedForm({
  schema,             // [{ id, label, fields?: [...], keys?: [...], custom?: (draft, setField) => JSX, validate?: (draft) => true | string }]
  values,             // full committed values object, owned by the caller
  onChange,           // (key, value) => void — called once per key on Save
  activeId,
  onActiveChange,
  savedSectionIds,    // Set<string>
  onSectionSaved,      // (sectionId) => void — caller should also mark savedSectionIds
}) {
  const section = schema.find((s) => s.id === activeId) ?? schema[0];
  const sectionKeys = section.fields ? section.fields.map((f) => f.key) : (section.keys ?? []);

  const [draft, setDraft] = useState(() => pickKeys(values, sectionKeys));
  const [error, setError] = useState(null);

  // Re-seed draft whenever the active section changes.
  useEffect(() => {
    setDraft(pickKeys(values, sectionKeys));
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  function pickKeys(src, keys) {
    const out = {};
    for (const k of keys) out[k] = src[k];
    return out;
  }

  function setField(key, val) {
    setDraft((d) => ({ ...d, [key]: val }));
  }

  function handleReset() {
    setDraft(pickKeys(values, sectionKeys));
    setError(null);
  }

  function handleSave() {
    // Required-field check (auto-generated fields only; custom sections
    // supply their own validate()).
    if (section.fields) {
      for (const f of section.fields) {
        if (f.required && (draft[f.key] === "" || draft[f.key] == null)) {
          setError(`${f.label} is required.`);
          return;
        }
      }
    }
    if (section.validate) {
      const result = section.validate(draft);
      if (result !== true) {
        setError(typeof result === "string" ? result : "Please check the values in this section.");
        return;
      }
    }
    setError(null);
    for (const k of sectionKeys) onChange(k, draft[k]);
    onSectionSaved(section.id);

    // Auto-advance to the next section once it's just been unlocked.
    const idx = schema.findIndex((s) => s.id === section.id);
    if (idx >= 0 && idx + 1 < schema.length) {
      onActiveChange(schema[idx + 1].id);
    }
  }

  const unlockedIds = new Set(
    schema.filter((s, i) => i === 0 || savedSectionIds.has(schema[i - 1].id)).map((s) => s.id)
  );

  return (
    <div className="card p-0 overflow-hidden">
      <div className="flex">
        <div className="p-4">
          <SectionSidebar
            sections={schema}
            activeId={section.id}
            unlockedIds={unlockedIds}
            savedIds={savedSectionIds}
            onSelect={onActiveChange}
          />
        </div>

        <div className="flex-1 p-5 min-w-0">
          <div className="mb-3">
            <p className="section-title">{section.label}</p>
            {section.description && <p className="text-xs text-gray-400 mt-0.5">{section.description}</p>}
          </div>

          <div className="divide-y divide-gray-50">
            {section.custom
              ? section.custom(draft, setField)
              : section.fields.map((f) => (
                  <FieldRenderer key={f.key} field={f} value={draft[f.key]} onChange={(v) => setField(f.key, v)} />
                ))}
          </div>

          {section.extra && (
            <div className="mt-3 pt-3 border-t border-gray-50">
              {section.extra(draft, setField)}
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 mt-3 text-xs text-red-700">
              <AlertCircle size={13} className="flex-shrink-0" /> {error}
            </div>
          )}

          <div className="flex gap-2 mt-4 pt-3 border-t border-gray-100">
            <button type="button" onClick={handleSave} className="btn-primary text-xs py-1.5">
              <Save size={13} /> Save section
            </button>
            <button type="button" onClick={handleReset} className="btn-secondary text-xs py-1.5">
              <RotateCcw size={13} /> Reset section
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function FieldRenderer({ field, value, onChange }) {
  if (field.type === "select") {
    return (
      <div className="grid grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,0.8fr)] gap-3 items-start py-2">
        <div className="pt-2">
          <p className="text-sm font-medium text-gray-700">
            {field.label}{field.required && <span className="text-red-500 ml-0.5">*</span>}
          </p>
          {field.description && <p className="text-xs text-gray-400 mt-0.5">{field.description}</p>}
        </div>
        <select className="select w-full" value={value} onChange={(e) => onChange(field.parse ? field.parse(e.target.value) : e.target.value)}>
          {field.options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <div />
      </div>
    );
  }

  if (field.type === "text") {
    return (
      <div className="grid grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,0.8fr)] gap-3 items-start py-2">
        <div className="pt-2">
          <p className="text-sm font-medium text-gray-700">
            {field.label}{field.required && <span className="text-red-500 ml-0.5">*</span>}
          </p>
          {field.description && <p className="text-xs text-gray-400 mt-0.5">{field.description}</p>}
        </div>
        <input className="input w-full" value={value ?? ""} onChange={(e) => onChange(e.target.value)} placeholder={field.placeholder} />
        <div />
      </div>
    );
  }

  // Default: unit-aware numeric field.
  return (
    <UnitField
      label={field.label}
      description={field.description}
      category={field.category}
      value={value}
      onChange={onChange}
      placeholder={field.placeholder}
      step={field.step}
      min={field.min}
      max={field.max}
      required={field.required}
    />
  );
}
