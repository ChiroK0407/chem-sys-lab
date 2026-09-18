/**
 * frontend/src/components/common/UnitField.jsx
 *
 * The fixed 3-column input row used across every unit form:
 *   [ label (left) ]   [ value input (middle) ]   [ unit dropdown (right) ]
 *
 * The field always stores/reports its value in the category's CANONICAL
 * unit (see utils/unitConversions.js) — switching the unit dropdown only
 * changes how the number is *displayed*, converting live, and re-converts
 * back to canonical before calling onChange.
 *
 * The unit dropdown auto-opens the moment the user focuses the value
 * input (per the "opens automatically on entry" spec), and can also be
 * toggled manually via the chevron.
 */

import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { toDisplay, toCanonical, defaultUnitFor, unitOptionsFor } from "../../utils/unitConversions";

export default function UnitField({
  label,
  description,
  category = "dimensionless",
  value,              // canonical-unit value (number or "")
  onChange,            // (canonicalValue) => void
  placeholder,
  step,
  min,
  max,
  required = false,
}) {
  const options = unitOptionsFor(category);
  const [displayUnit, setDisplayUnit] = useState(defaultUnitFor(category));
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    function onDocClick(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const displayValue = toDisplay(category, value, displayUnit);

  function handleValueChange(e) {
    const raw = e.target.value;
    if (raw === "") { onChange(""); return; }
    const num = parseFloat(raw);
    if (Number.isNaN(num)) return;
    onChange(toCanonical(category, num, displayUnit));
  }

  function handleUnitPick(unitKey) {
    setDisplayUnit(unitKey);
    setOpen(false);
  }

  const showUnitPicker = options.length > 1;

  return (
    <div className="grid grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,0.8fr)] gap-3 items-start py-2">
      {/* Left: label + optional description */}
      <div className="pt-2">
        <p className="text-sm font-medium text-gray-700">
          {label}{required && <span className="text-red-500 ml-0.5">*</span>}
        </p>
        {description && <p className="text-xs text-gray-400 mt-0.5">{description}</p>}
      </div>

      {/* Middle: value input */}
      <div>
        <input
          type="number"
          className="input w-full"
          value={displayValue}
          onChange={handleValueChange}
          onFocus={() => showUnitPicker && setOpen(true)}
          placeholder={placeholder}
          step={step ?? "any"}
          min={min}
          max={max}
        />
      </div>

      {/* Right: unit dropdown */}
      <div className="relative" ref={wrapRef}>
        {showUnitPicker ? (
          <>
            <button
              type="button"
              onClick={() => setOpen((o) => !o)}
              className="input w-full flex items-center justify-between text-left text-gray-600"
            >
              <span>{options.find((o) => o.key === displayUnit)?.label ?? displayUnit}</span>
              <ChevronDown size={14} className="text-gray-400 flex-shrink-0" />
            </button>
            {open && (
              <div className="absolute z-20 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg py-1 max-h-56 overflow-y-auto">
                {options.map((o) => (
                  <button
                    key={o.key}
                    type="button"
                    onClick={() => handleUnitPick(o.key)}
                    className={`w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50
                      ${o.key === displayUnit ? "text-brand-700 font-medium bg-brand-50" : "text-gray-700"}`}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="input w-full flex items-center text-gray-400 select-none">
            {options[0]?.label ?? "—"}
          </div>
        )}
      </div>
    </div>
  );
}
