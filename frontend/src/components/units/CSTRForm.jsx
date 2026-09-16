import { useState } from "react";
import { Play, RotateCcw, Loader2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import StreamInputPanel from "../shared/StreamInputPanel";
import ReactorKineticsPanel from "./ReactorKineticsPanel";
import client from "../../api/client";

const defaultKinetics = () => ({ k_ref:0.01, T_ref_C:25, Ea_J_mol:50000, n_order:1.0, delta_H_rxn:-50000, C_A0_mol_m3:1000, MW_A_g_mol:100 });
const defaultOperating = () => ({ mode:"design", thermal_mode:"isothermal", T_rxn_C:25, X_target:0.90, volume_m3:null });
const defaultFeed = () => ({ name:"feed", fluid_id:null, temperature_c:25, pressure_kpa:200, mass_flowrate_kg_s:1.0, cp_J_kgK:4000, density_kg_m3:1000, viscosity_Pa_s:0.00089, thermal_conductivity:0.607, phase:"liquid" });

export default function CSTRForm({ onResult }) {
  const [unitId, setUnitId]     = useState("R-101");
  const [feed, setFeed]         = useState(defaultFeed());
  const [kinetics, setKinetics] = useState(defaultKinetics());
  const [operating, setOp]      = useState(defaultOperating());

  const { mutate, isPending, isError, error } = useMutation({
    mutationFn: (payload) => client.post("/solve/cstr?include_log=true", payload).then(r => r.data),
  });

  function handleSolve() {
    const stream = { ...feed }; delete stream.fluid_id;
    mutate({ unit_id: unitId, feed_stream: stream, kinetics, operating },
           { onSuccess: onResult });
  }

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <label className="label">Unit ID</label>
        <input className="input w-40" value={unitId} onChange={e => setUnitId(e.target.value)} />
      </div>
      <div className="card p-5">
        <StreamInputPanel label="Feed stream" value={feed} onChange={setFeed} />
      </div>
      <ReactorKineticsPanel kinetics={kinetics} operating={operating}
        onKinetics={setKinetics} onOperating={setOp} />
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
        <button className="btn-secondary" onClick={() => { setFeed(defaultFeed()); setKinetics(defaultKinetics()); setOp(defaultOperating()); onResult(null); }}>
          <RotateCcw size={15} /> Reset
        </button>
      </div>
    </div>
  );
}
