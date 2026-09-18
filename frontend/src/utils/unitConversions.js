/**
 * frontend/src/utils/unitConversions.js
 *
 * Central conversion registry for the unit-aware form fields (UnitField).
 * Every quantity category stores its CANONICAL unit — the one value that
 * actually gets sent to the backend and used in all calculations — plus a
 * list of alternate display units with toCanonical/fromCanonical converters.
 *
 * Per-app decision: canonical units are SI throughout —
 * °C, kPa, mol/s, kg/s, W (see category defs below for exceptions like
 * dimensionless fractions, which have no physical unit at all).
 *
 * Adding a new category or unit is the only thing a new field type needs;
 * UnitField, SectionedForm etc. never need to change.
 */

export const CONVERSIONS = {
  temperature: {
    canonical: "C",
    units: {
      C: { label: "°C", toCanonical: (v) => v, fromCanonical: (v) => v },
      K: { label: "K", toCanonical: (v) => v - 273.15, fromCanonical: (v) => v + 273.15 },
      F: { label: "°F", toCanonical: (v) => (v - 32) * (5 / 9), fromCanonical: (v) => v * (9 / 5) + 32 },
    },
  },

  pressure: {
    canonical: "kPa",
    units: {
      kPa: { label: "kPa", toCanonical: (v) => v, fromCanonical: (v) => v },
      Pa: { label: "Pa", toCanonical: (v) => v / 1000, fromCanonical: (v) => v * 1000 },
      bar: { label: "bar", toCanonical: (v) => v * 100, fromCanonical: (v) => v / 100 },
      atm: { label: "atm", toCanonical: (v) => v * 101.325, fromCanonical: (v) => v / 101.325 },
      psi: { label: "psi", toCanonical: (v) => v * 6.89476, fromCanonical: (v) => v / 6.89476 },
      mmHg: { label: "mmHg", toCanonical: (v) => v * 0.133322, fromCanonical: (v) => v / 0.133322 },
    },
  },

  molarFlow: {
    canonical: "mol_s",
    units: {
      mol_s: { label: "mol/s", toCanonical: (v) => v, fromCanonical: (v) => v },
      kmol_s: { label: "kmol/s", toCanonical: (v) => v * 1000, fromCanonical: (v) => v / 1000 },
      kmol_h: { label: "kmol/h", toCanonical: (v) => v * (1000 / 3600), fromCanonical: (v) => v * (3600 / 1000) },
      mol_h: { label: "mol/h", toCanonical: (v) => v / 3600, fromCanonical: (v) => v * 3600 },
      mol_min: { label: "mol/min", toCanonical: (v) => v / 60, fromCanonical: (v) => v * 60 },
      lbmol_h: { label: "lbmol/h", toCanonical: (v) => v * (453.592 / 3600), fromCanonical: (v) => v * (3600 / 453.592) },
    },
  },

  massFlow: {
    canonical: "kg_s",
    units: {
      kg_s: { label: "kg/s", toCanonical: (v) => v, fromCanonical: (v) => v },
      kg_h: { label: "kg/h", toCanonical: (v) => v / 3600, fromCanonical: (v) => v * 3600 },
      t_h: { label: "t/h", toCanonical: (v) => v * (1000 / 3600), fromCanonical: (v) => v * (3600 / 1000) },
      lb_h: { label: "lb/h", toCanonical: (v) => v * (0.453592 / 3600), fromCanonical: (v) => v * (3600 / 0.453592) },
    },
  },

  power: {
    canonical: "W",
    units: {
      W: { label: "W", toCanonical: (v) => v, fromCanonical: (v) => v },
      kW: { label: "kW", toCanonical: (v) => v * 1000, fromCanonical: (v) => v / 1000 },
      MW: { label: "MW", toCanonical: (v) => v * 1e6, fromCanonical: (v) => v / 1e6 },
      hp: { label: "hp", toCanonical: (v) => v * 745.7, fromCanonical: (v) => v / 745.7 },
      BTU_h: { label: "BTU/h", toCanonical: (v) => v * 0.293071, fromCanonical: (v) => v / 0.293071 },
    },
  },

  molarEnergy: {
    canonical: "J_mol",
    units: {
      J_mol: { label: "J/mol", toCanonical: (v) => v, fromCanonical: (v) => v },
      kJ_mol: { label: "kJ/mol", toCanonical: (v) => v * 1000, fromCanonical: (v) => v / 1000 },
      cal_mol: { label: "cal/mol", toCanonical: (v) => v * 4.184, fromCanonical: (v) => v / 4.184 },
      kcal_mol: { label: "kcal/mol", toCanonical: (v) => v * 4184, fromCanonical: (v) => v / 4184 },
      BTU_lbmol: { label: "BTU/lbmol", toCanonical: (v) => v * 2.326, fromCanonical: (v) => v / 2.326 },
    },
  },

  length: {
    canonical: "m",
    units: {
      m: { label: "m", toCanonical: (v) => v, fromCanonical: (v) => v },
      mm: { label: "mm", toCanonical: (v) => v / 1000, fromCanonical: (v) => v * 1000 },
      cm: { label: "cm", toCanonical: (v) => v / 100, fromCanonical: (v) => v * 100 },
      ft: { label: "ft", toCanonical: (v) => v * 0.3048, fromCanonical: (v) => v / 0.3048 },
      in: { label: "in", toCanonical: (v) => v * 0.0254, fromCanonical: (v) => v / 0.0254 },
    },
  },

  // A plain ratio/fraction (0–1), with "%" as the only alternate display.
  fraction: {
    canonical: "frac",
    units: {
      frac: { label: "fraction", toCanonical: (v) => v, fromCanonical: (v) => v },
      pct: { label: "%", toCanonical: (v) => v / 100, fromCanonical: (v) => v * 100 },
    },
  },

  // A bare dimensionless number (ratios like R/R_min) — one "unit" that's a no-op,
  // present mainly so every field can use the same UnitField component uniformly.
  dimensionless: {
    canonical: "x",
    units: {
      x: { label: "—", toCanonical: (v) => v, fromCanonical: (v) => v },
    },
  },
};

/** Convert a canonical-unit value into the given display unit. */
export function toDisplay(category, canonicalValue, displayUnitKey) {
  if (canonicalValue === "" || canonicalValue == null || Number.isNaN(canonicalValue)) return "";
  const unit = CONVERSIONS[category]?.units[displayUnitKey];
  if (!unit) return canonicalValue;
  return unit.fromCanonical(canonicalValue);
}

/** Convert a value entered in the given display unit back into the canonical unit. */
export function toCanonical(category, displayValue, displayUnitKey) {
  if (displayValue === "" || displayValue == null || Number.isNaN(displayValue)) return "";
  const unit = CONVERSIONS[category]?.units[displayUnitKey];
  if (!unit) return displayValue;
  return unit.toCanonical(displayValue);
}

export function defaultUnitFor(category) {
  return CONVERSIONS[category]?.canonical;
}

export function unitOptionsFor(category) {
  const cat = CONVERSIONS[category];
  if (!cat) return [];
  return Object.entries(cat.units).map(([key, u]) => ({ key, label: u.label }));
}
