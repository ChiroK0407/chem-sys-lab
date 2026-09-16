import { useState } from "react";
import { Play, RotateCcw, Loader2 } from "lucide-react";
import StreamInputPanel from "../shared/StreamInputPanel";
import { useMutation } from "@tanstack/react-query";
import { solveHX } from "../../api/units";
import client from "../../api/client";

// Paste this at the absolute top of the file, above your component function
const INDUSTRIAL_PUMP_STANDARDS = {
  API_610_OH2: {
    name: "API 610 OH2 (Overhung Centerline Process)",
    maxPressure: 40.0,
    maxTemp: 400.0,
    defaultEff: 75.0,
    speedRpm: 1450
  },
  API_610_BB2: {
    name: "API 610 BB2 (Between Bearings High P/Q)",
    maxPressure: 100.0,
    maxTemp: 450.0,
    defaultEff: 79.0,
    speedRpm: 1450
  },
  ASME_B73_1: {
    name: "ASME B73.1 (Foot-Mounted Chemical)",
    maxPressure: 19.0,
    maxTemp: 260.0,
    defaultEff: 66.0,
    speedRpm: 1750
  }
};

async function solvePump(payload, includeLog = true) {
  const { data } = await client.post(
    `/solve/pump?include_log=${includeLog}`,
    payload
  );
  return data;
}

const defaultStream = () => ({
  name: "feed",
  fluid_id: null,
  temperature_c: 25,
  pressure_kpa: 150,
  mass_flowrate_kg_s: 5.0,
  cp_J_kgK: 4182,
  density_kg_m3: 997,
  viscosity_Pa_s: 0.00089,
  thermal_conductivity: 0.607,
  phase: "liquid",
});

export default function PumpForm({ onResult }) {
  const [unitId, setUnitId]           = useState("P-101");
  const [feed, setFeed]               = useState(defaultStream());
  const [dischP, setDischP]           = useState(400);
  const [dischElev, setDischElev]     = useState(0);
  const [suctElev, setSuctElev]       = useState(0);
  const [suctVel, setSuctVel]         = useState(1.5);
  const [dischVel, setDischVel]       = useState(2.5);
  const [etaPump, setEtaPump]         = useState(0.75);
  const [etaMotor, setEtaMotor]       = useState(0.92);
  const [npshReq, setNpshReq]         = useState(2.0);
  const [vapP, setVapP]               = useState("");
  const [speedRpm, setSpeedRpm]       = useState(1450);

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: ({ payload }) => solvePump(payload, true),
  });

  function handleSolve() {
    const stream = { ...feed };
    delete stream.fluid_id;

    const payload = {
      unit_id: unitId,
      feed_stream: stream,
      discharge_pressure_kPa: dischP,
      discharge_elevation_m: dischElev,
      suction_elevation_m: suctElev,
      suction_velocity_m_s: suctVel,
      discharge_velocity_m_s: dischVel,
      eta_pump: etaPump,
      eta_motor: etaMotor,
      npsh_required_m: npshReq,
      speed_rpm: speedRpm,
      ...(vapP !== "" && { vapour_pressure_kPa: parseFloat(vapP) }),
    };

    mutate({ payload }, { onSuccess: (data) => onResult(data) });
  }

  function handleReset() {
    setFeed(defaultStream());
    onResult(null);
  }

  const num = (set) => (e) => set(parseFloat(e.target.value) || 0);

  return (
    <div className="space-y-5">

      {/* Config */}
      <div className="card p-5 space-y-4">
        <p className="section-title">Pump Configuration</p>

        {/* --- DESIGN STANDARDS DROPDOWN SECTION --- */}
        <div className="border-b border-gray-700 pb-3">
          <label className="label">Design Standard Template</label>
          <select
            className="input w-full mt-1 bg-slate-900 text-slate-200 border border-gray-700 rounded p-2 text-sm"
            onChange={(e) => {
              const selectedKey = e.target.value;
              const presets = {
                API_610_OH2: { speed: 1450, pressure: 4000, etaP: 0.75, etaM: 0.92, npsh: 2.0 }, // 40 bar = 4000 kPa
                API_610_BB2: { speed: 1450, pressure: 10000, etaP: 0.79, etaM: 0.95, npsh: 2.5 }, // 100 bar = 10000 kPa
                ASME_B73_1:  { speed: 1750, pressure: 1900,  etaP: 0.66, etaM: 0.90, npsh: 1.5 }  // 19 bar = 1900 kPa
              };

              if (presets[selectedKey]) {
                const preset = presets[selectedKey];
                // Macro macro typing action across your existing React state parameters
                setSpeedRpm(preset.speed);
                setDischP(preset.pressure);
                setEtaPump(preset.etaP);
                setEtaMotor(preset.etaM);
                setNpshReq(preset.npsh);
              }
            }}
          >
            <option value="">-- Manual Configuration (No Template) --</option>
            <option value="API_610_OH2">API 610 OH2 (Overhung Centerline Process)</option>
            <option value="API_610_BB2">API 610 BB2 (Between Bearings High Pressure)</option>
            <option value="ASME_B73_1">ASME B73.1 (Foot-Mounted Chemical Process)</option>
          </select>
        </div>

        {/* --- EXISTING PARAMETER GRIDS (UNTOUCHED STYLING) --- */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div>
            <label className="label">Unit ID</label>
            <input className="input" value={unitId}
              onChange={(e) => setUnitId(e.target.value)} />
          </div>
          <div>
            <label className="label">Speed (rpm)</label>
            <input type="number" className="input" value={speedRpm}
              onChange={num(setSpeedRpm)} step="50" />
          </div>
          <div>
            <label className="label">Discharge P (kPa)</label>
            <input type="number" className="input" value={dischP}
              onChange={num(setDischP)} step="10" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div>
            <label className="label">η pump</label>
            <input type="number" className="input" value={etaPump}
              onChange={num(setEtaPump)} step="0.01" min="0.1" max="1" />
          </div>
          <div>
            <label className="label">η motor</label>
            <input type="number" className="input" value={etaMotor}
              onChange={num(setEtaMotor)} step="0.01" min="0.1" max="1" />
          </div>
          <div>
            <label className="label">NPSHr (m)</label>
            <input type="number" className="input" value={npshReq}
              onChange={num(setNpshReq)} step="0.5" />
          </div>
          <div>
            <label className="label">Vapour P (kPa) <span className="text-gray-400 font-normal">optional</span></label>
            <input type="number" className="input" value={vapP}
              onChange={(e) => setVapP(e.target.value)}
              placeholder="auto (water)" />
          </div>
        </div>

        {/* Elevation and velocity */}
        <div>
          <p className="section-title mb-2">Head components</p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div>
              <label className="label">Suction elev. (m)</label>
              <input type="number" className="input" value={suctElev}
                onChange={num(setSuctElev)} step="0.5" />
            </div>
            <div>
              <label className="label">Discharge elev. (m)</label>
              <input type="number" className="input" value={dischElev}
                onChange={num(setDischElev)} step="0.5" />
            </div>
            <div>
              <label className="label">Suction vel. (m/s)</label>
              <input type="number" className="input" value={suctVel}
                onChange={num(setSuctVel)} step="0.1" />
            </div>
            <div>
              <label className="label">Discharge vel. (m/s)</label>
              <input type="number" className="input" value={dischVel}
                onChange={num(setDischVel)} step="0.1" />
            </div>
          </div>
        </div>
      </div>

      {/* Feed stream */}
      <div className="card p-5">
        <StreamInputPanel label="Feed stream" value={feed} onChange={setFeed} />
      </div>

      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3
                        text-sm text-red-800">
          {error?.message ?? "An error occurred. Check your inputs."}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button className="btn-primary" onClick={handleSolve} disabled={isPending}>
          {isPending
            ? <Loader2 size={15} className="animate-spin" />
            : <Play size={15} />}
          {isPending ? "Solving…" : "Solve"}
        </button>
        <button className="btn-secondary" onClick={handleReset}>
          <RotateCcw size={15} />
          Reset
        </button>
      </div>

    </div>
  );
}
