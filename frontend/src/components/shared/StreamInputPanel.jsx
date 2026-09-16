import { useEffect } from "react";
import { Loader2 } from "lucide-react";
import { useFluids, useFluidDetail } from "../../hooks/useFluids";

const PHASES = ["liquid", "vapor", "mixed"];

export default function StreamInputPanel({ label, value, onChange, showPhase = true }) {
  const { data: fluids, isLoading: loadingFluids } = useFluids();

  // When a fluid is selected and temperature changes, auto-fetch properties
  const { data: fluidProps } = useFluidDetail(
    value.fluid_id || null,
    value.temperature_c
  );

  // Auto-fill properties when fluidProps comes back
  useEffect(() => {
    if (!fluidProps || !value.fluid_id) return;
    onChange({
      ...value,
      cp_J_kgK:             fluidProps.cp_J_kgK,
      density_kg_m3:        fluidProps.density_kg_m3,
      viscosity_Pa_s:       fluidProps.viscosity_Pa_s,
      thermal_conductivity: fluidProps.thermal_conductivity,
      phase:                fluidProps.phase,
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fluidProps]);

  const set = (field) => (e) => onChange({ ...value, [field]: e.target.value });
  const setNum = (field) => (e) => onChange({ ...value, [field]: parseFloat(e.target.value) || 0 });

  return (
    <div className="space-y-3">
      <p className="section-title">{label}</p>

      {/* Name + fluid selector */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Stream name</label>
          <input className="input" value={value.name} onChange={set("name")} placeholder="e.g. process_hot" />
        </div>
        <div>
          <label className="label">Fluid</label>
          <div className="relative">
            <select
              className="select pr-8"
              value={value.fluid_id || ""}
              onChange={(e) => onChange({ ...value, fluid_id: e.target.value || null })}
            >
              <option value="">— select fluid —</option>
              {loadingFluids
                ? <option disabled>Loading...</option>
                : fluids?.map((f) => (
                    <option key={f.fluid_id} value={f.fluid_id}>{f.name}</option>
                  ))
              }
            </select>
            {loadingFluids && (
              <Loader2 size={14} className="absolute right-8 top-2.5 animate-spin text-gray-400" />
            )}
          </div>
        </div>
      </div>

      {/* T, P, flowrate */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="label">Temperature (°C)</label>
          <input type="number" className="input" value={value.temperature_c} onChange={setNum("temperature_c")} step="1" />
        </div>
        <div>
          <label className="label">Pressure (kPa)</label>
          <input type="number" className="input" value={value.pressure_kpa} onChange={setNum("pressure_kpa")} step="10" />
        </div>
        <div>
          <label className="label">Flow (kg/s)</label>
          <input type="number" className="input" value={value.mass_flowrate_kg_s} onChange={setNum("mass_flowrate_kg_s")} step="0.1" />
        </div>
      </div>

      {/* Thermo properties */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Cp (J/kg·K)</label>
          <input type="number" className="input" value={value.cp_J_kgK} onChange={setNum("cp_J_kgK")} step="10" />
        </div>
        <div>
          <label className="label">Density (kg/m³)</label>
          <input type="number" className="input" value={value.density_kg_m3} onChange={setNum("density_kg_m3")} step="1" />
        </div>
        <div>
          <label className="label">Viscosity (Pa·s)</label>
          <input type="number" className="input" value={value.viscosity_Pa_s} onChange={setNum("viscosity_Pa_s")} step="0.0001" />
        </div>
        <div>
          <label className="label">Therm. cond. (W/m·K)</label>
          <input type="number" className="input" value={value.thermal_conductivity} onChange={setNum("thermal_conductivity")} step="0.01" />
        </div>
      </div>

      {showPhase && (
        <div>
          <label className="label">Phase</label>
          <select className="select" value={value.phase} onChange={set("phase")}>
            {PHASES.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
      )}

      {/* Auto-fill indicator */}
      {value.fluid_id && fluidProps && (
        <p className="text-xs text-brand-600">
          ✓ Properties auto-filled from {fluidProps.name} at {fluidProps.T_used_C.toFixed(0)}°C
        </p>
      )}
    </div>
  );
}
