import { useState } from "react";
import { Ruler, ChevronDown, ChevronUp } from "lucide-react";

// ── Standard TEMA tube dimensions ─────────────────────────────────────────────
// Source: TEMA Standards (9th ed.) Table RGP-T-2.4
// OD in mm, BWG gauge, wall thickness in mm, ID in mm
const STANDARD_TUBES = [
  { od_mm: 19.05, bwg: 16, wall_mm: 1.65,  id_mm: 15.75, label: "¾\" OD  BWG 16" },
  { od_mm: 19.05, bwg: 14, wall_mm: 2.11,  id_mm: 14.83, label: "¾\" OD  BWG 14" },
  { od_mm: 25.40, bwg: 16, wall_mm: 1.65,  id_mm: 22.10, label: "1\"  OD  BWG 16" },
  { od_mm: 25.40, bwg: 14, wall_mm: 2.11,  id_mm: 21.18, label: "1\"  OD  BWG 14" },
  { od_mm: 25.40, bwg: 12, wall_mm: 2.77,  id_mm: 19.86, label: "1\"  OD  BWG 12" },
  { od_mm: 31.75, bwg: 16, wall_mm: 1.65,  id_mm: 28.45, label: "1¼\" OD  BWG 16" },
  { od_mm: 31.75, bwg: 14, wall_mm: 2.11,  id_mm: 27.53, label: "1¼\" OD  BWG 14" },
  { od_mm: 38.10, bwg: 16, wall_mm: 1.65,  id_mm: 34.80, label: "1½\" OD  BWG 16" },
  { od_mm: 38.10, bwg: 14, wall_mm: 2.11,  id_mm: 33.88, label: "1½\" OD  BWG 14" },
];

// Standard tube lengths per TEMA (ft converted to m)
const STANDARD_LENGTHS_M = [
  { m: 1.83, label: "6 ft  (1.83 m)"  },
  { m: 2.44, label: "8 ft  (2.44 m)"  },
  { m: 3.66, label: "12 ft (3.66 m)"  },
  { m: 4.88, label: "16 ft (4.88 m)"  },
  { m: 6.10, label: "20 ft (6.10 m)"  },
];

// Typical tube pitch ratios (pitch / OD) — triangular and square
const PITCH_TYPES = [
  { ratio: 1.25, layout: "triangular", label: "Triangular  PT/OD = 1.25  (most common)" },
  { ratio: 1.33, layout: "triangular", label: "Triangular  PT/OD = 1.33" },
  { ratio: 1.25, layout: "square",     label: "Square      PT/OD = 1.25" },
  { ratio: 1.50, layout: "square",     label: "Square      PT/OD = 1.50  (easy cleaning)" },
];

function calcTubes(areaMm2, tube, lengthM) {
  // External area per tube
  const areaPerTube = Math.PI * (tube.od_mm / 1000) * lengthM; // m²
  const nTubes = Math.ceil(areaMm2 / areaPerTube);
  return { areaPerTube, nTubes };
}

function shellDiameter(nTubes, tube, pitch) {
  // Approximate shell ID using bundle diameter correlation
  // Ds ≈ Do * (N/K1)^(1/n1)   — from C&R Vol.1 Table 12.4
  // For simplicity use: bundle area method
  // Bundle cross-section ≈ N * (pitch²) / packing factor
  const pitchMm = tube.od_mm * pitch.ratio;
  // Triangular packing factor ~0.866, square ~1.0
  const packFactor = pitch.layout === "triangular" ? 0.866 : 1.0;
  const bundleArea = nTubes * pitchMm * pitchMm / packFactor; // mm²
  const bundleDia  = 2 * Math.sqrt(bundleArea / Math.PI);      // mm
  // Add clearance for shell (~40mm typical for fixed tubesheet)
  const shellId = bundleDia + 40;
  return { bundleDia: Math.round(bundleDia), shellId: Math.round(shellId) };
}

function nearestShell(shellIdMm) {
  // TEMA standard shell IDs (mm)
  const stdShells = [
    150, 180, 205, 230, 255, 280, 305, 330, 355, 380,
    405, 435, 460, 485, 510, 535, 560, 590, 615, 640,
    665, 690, 715, 740, 770, 795, 820, 870, 920, 970, 1020,
  ];
  return stdShells.find((s) => s >= shellIdMm) ?? shellIdMm;
}

export default function TubeSizer({ areaMm2 }) {
  const [open, setOpen]           = useState(false);
  const [tubeIdx, setTubeIdx]     = useState(0);   // index into STANDARD_TUBES
  const [lengthIdx, setLengthIdx] = useState(2);   // default 12 ft
  const [pitchIdx, setPitchIdx]   = useState(0);   // default triangular 1.25

  if (!areaMm2 || areaMm2 <= 0) return null;

  const tube   = STANDARD_TUBES[tubeIdx];
  const length = STANDARD_LENGTHS_M[lengthIdx];
  const pitch  = PITCH_TYPES[pitchIdx];

  const { areaPerTube, nTubes } = calcTubes(areaMm2, tube, length.m);
  const { bundleDia, shellId }  = shellDiameter(nTubes, tube, pitch);
  const stdShellId              = nearestShell(shellId);

  const totalArea = nTubes * areaPerTube;
  const overDesign = ((totalArea / areaMm2) - 1) * 100;

  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden">

      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3
                   bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
          <Ruler size={15} className="text-green-700" />
          Tube sizing  
          <span className="inline-flex items-center rounded-full px-2.5 py-0.5
                           text-xs font-medium bg-gray-100 text-gray-600">
            TEMA standards
          </span>
        </div>
        {open
          ? <ChevronUp   size={15} className="text-gray-400" />
          : <ChevronDown size={15} className="text-gray-400" />
        }
      </button>

      {open && (
        <div className="bg-white border-t border-gray-100 p-4 space-y-5">

          {/* Required area display */}
          <div className="rounded-lg bg-green-50 border border-green-200
                          px-4 py-2.5 flex items-center justify-between">
            <span className="text-sm text-green-800 font-medium">
              Required heat transfer area
            </span>
            <span className="text-lg font-semibold text-green-900">
              {areaMm2.toFixed(3)} m²
            </span>
          </div>

          {/* Selectors */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label className="label">Tube size (OD / BWG)</label>
              <select
                className="select"
                value={tubeIdx}
                onChange={(e) => setTubeIdx(Number(e.target.value))}
              >
                {STANDARD_TUBES.map((t, i) => (
                  <option key={i} value={i}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Tube length</label>
              <select
                className="select"
                value={lengthIdx}
                onChange={(e) => setLengthIdx(Number(e.target.value))}
              >
                {STANDARD_LENGTHS_M.map((l, i) => (
                  <option key={i} value={i}>{l.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Tube pitch / layout</label>
              <select
                className="select"
                value={pitchIdx}
                onChange={(e) => setPitchIdx(Number(e.target.value))}
              >
                {PITCH_TYPES.map((p, i) => (
                  <option key={i} value={i}>{p.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Tube dimensions display */}
          <div className="rounded-lg bg-gray-50 border border-gray-200
                          px-4 py-3 grid grid-cols-4 gap-4 text-center">
            {[
              { label: "OD",   value: `${tube.od_mm} mm` },
              { label: "ID",   value: `${tube.id_mm} mm` },
              { label: "Wall", value: `${tube.wall_mm} mm` },
              { label: "Area/tube", value: `${areaPerTube.toFixed(4)} m²` },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-xs text-gray-400 mb-0.5">{label}</p>
                <p className="text-sm font-semibold text-gray-800">{value}</p>
              </div>
            ))}
          </div>

          {/* Results */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-green-200 bg-green-50 p-4">
              <p className="text-xs font-medium text-gray-500 mb-1">
                Number of tubes
              </p>
              <p className="text-2xl font-semibold text-green-800">{nTubes}</p>
              <p className="text-xs text-gray-400 mt-0.5">tubes</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <p className="text-xs font-medium text-gray-500 mb-1">
                Tube length
              </p>
              <p className="text-2xl font-semibold text-gray-900">
                {length.m.toFixed(2)}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">m</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <p className="text-xs font-medium text-gray-500 mb-1">
                Bundle diameter
              </p>
              <p className="text-2xl font-semibold text-gray-900">{bundleDia}</p>
              <p className="text-xs text-gray-400 mt-0.5">mm (approx)</p>
            </div>
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
              <p className="text-xs font-medium text-gray-500 mb-1">
                Std shell ID
              </p>
              <p className="text-2xl font-semibold text-blue-800">{stdShellId}</p>
              <p className="text-xs text-gray-400 mt-0.5">mm TEMA</p>
            </div>
          </div>

          {/* Over-design and total area */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-gray-200 bg-gray-50
                            px-4 py-3">
              <p className="text-xs text-gray-500 mb-1">Total provided area</p>
              <p className="text-sm font-semibold text-gray-800">
                {totalArea.toFixed(3)} m²
              </p>
            </div>
            <div className={`rounded-lg border px-4 py-3
              ${overDesign > 20
                ? "border-amber-200 bg-amber-50"
                : "border-gray-200 bg-gray-50"
              }`}
            >
              <p className="text-xs text-gray-500 mb-1">Over-design</p>
              <p className={`text-sm font-semibold
                ${overDesign > 20 ? "text-amber-700" : "text-gray-800"}`}
              >
                {overDesign.toFixed(1)}%
                {overDesign > 20 && " ⚠ consider shorter tube or fewer passes"}
              </p>
            </div>
          </div>

          {/* Reference note */}
          <p className="text-xs text-gray-400">
            Tube dimensions per TEMA RGP-T-2.4. Shell ID rounded up to nearest
            standard TEMA size. Bundle diameter estimated from tube count and
            pitch geometry — verify with mechanical drawing.
          </p>

        </div>
      )}
    </div>
  );
}
