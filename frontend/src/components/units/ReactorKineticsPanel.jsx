// Shared kinetics + operating spec panel used by both CSTR and PFR forms
export default function ReactorKineticsPanel({ kinetics, operating, onKinetics, onOperating, showVolume }) {
  const kn = (f) => (e) => onKinetics({ ...kinetics, [f]: parseFloat(e.target.value) || 0 });
  const op = (f) => (e) => onOperating({ ...operating, [f]: e.target.value });
  const opn = (f) => (e) => onOperating({ ...operating, [f]: parseFloat(e.target.value) || 0 });

  return (
    <div className="space-y-4">

      {/* Operating */}
      <div className="card p-4 space-y-3">
        <p className="section-title">Operating specification</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div>
            <label className="label">Mode</label>
            <select className="select" value={operating.mode} onChange={op("mode")}>
              <option value="design">Design (find V)</option>
              <option value="rating">Rating (find X)</option>
            </select>
          </div>
          <div>
            <label className="label">Thermal mode</label>
            <select className="select" value={operating.thermal_mode} onChange={op("thermal_mode")}>
              <option value="isothermal">Isothermal</option>
              <option value="adiabatic">Adiabatic</option>
            </select>
          </div>
          <div>
            <label className="label">T reaction (°C)</label>
            <input type="number" className="input" value={operating.T_rxn_C}
              onChange={opn("T_rxn_C")} step="5" />
          </div>
          {operating.mode === "design"
            ? <div>
                <label className="label">Target X</label>
                <input type="number" className="input" value={operating.X_target}
                  onChange={opn("X_target")} step="0.05" min="0.01" max="0.99" />
              </div>
            : <div>
                <label className="label">Volume (m³)</label>
                <input type="number" className="input" value={operating.volume_m3 ?? ""}
                  onChange={opn("volume_m3")} step="0.1" />
              </div>
          }
        </div>
      </div>

      {/* Kinetics */}
      <div className="card p-4 space-y-3">
        <p className="section-title">Kinetics  <span className="text-gray-400 font-normal normal-case tracking-normal ml-1">−r_A = k(T) · C_A^n</span></p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div>
            <label className="label">k_ref (at T_ref)</label>
            <input type="number" className="input" value={kinetics.k_ref}
              onChange={kn("k_ref")} step="0.001" />
          </div>
          <div>
            <label className="label">T_ref (°C)</label>
            <input type="number" className="input" value={kinetics.T_ref_C}
              onChange={kn("T_ref_C")} step="5" />
          </div>
          <div>
            <label className="label">Ea (J/mol)</label>
            <input type="number" className="input" value={kinetics.Ea_J_mol}
              onChange={kn("Ea_J_mol")} step="1000" />
          </div>
          <div>
            <label className="label">Reaction order n</label>
            <input type="number" className="input" value={kinetics.n_order}
              onChange={kn("n_order")} step="0.5" min="0.1" />
          </div>
          <div>
            <label className="label">C_A0 (mol/m³)</label>
            <input type="number" className="input" value={kinetics.C_A0_mol_m3}
              onChange={kn("C_A0_mol_m3")} step="100" />
          </div>
          <div>
            <label className="label">MW_A (g/mol)</label>
            <input type="number" className="input" value={kinetics.MW_A_g_mol}
              onChange={kn("MW_A_g_mol")} step="10" />
          </div>
        </div>
        <div>
          <label className="label">ΔH_rxn (J/mol_A) — negative = exothermic</label>
          <input type="number" className="input" value={kinetics.delta_H_rxn}
            onChange={kn("delta_H_rxn")} step="1000" />
        </div>
        <p className="text-xs text-gray-400">
          k(T) = k_ref · exp(−Ea/R · (1/T − 1/T_ref)) · Arrhenius  |  Ea = 0 → no temperature correction
        </p>
      </div>
    </div>
  );
}
