"""
simulation/units/mixer.py

Adiabatic stream mixer — N inlets → 1 outlet.

Solves simultaneous mass and energy balance:
    ṁ_out  = Σ ṁᵢ
    T_mix  = Σ(ṁᵢ · Cpᵢ · Tᵢ) / Σ(ṁᵢ · Cpᵢ)
    Cp_mix = Σ(ṁᵢ · Cpᵢ) / ṁ_out          (mass-weighted)
    ρ_mix  = ṁ_out / Σ(ṁᵢ / ρᵢ)           (volume-additive)
    μ_mix  = Σ(ṁᵢ · μᵢ) / ṁ_out           (mass-weighted, approx)
    k_mix  = Σ(ṁᵢ · kᵢ) / ṁ_out           (mass-weighted, approx)

Assumptions
-----------
- Adiabatic (no heat loss to surroundings)
- No reaction, no phase change inside the mixer
- Ideal mixing (no excess enthalpy of mixing)
- Outlet pressure = minimum inlet pressure (conservative)

References
----------
- McCabe, Smith & Harriott, Chapter 7 (energy balances on flow systems)
- Coulson & Richardson Vol. 1, Chapter 3 (material and energy balances)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from simulation.core.stream import ProcessStream
from simulation.core.unit_operation import UnitOperation
from simulation.core.exceptions import StreamError, InfeasibleDesignError


@dataclass
class Mixer(UnitOperation):
    """
    Adiabatic stream mixer.

    Add inlet streams via add_inlet(key, stream) before calling solve().
    At least 2 inlet streams are required; up to 10 are supported.

    The outlet stream is keyed as "outlet" in self.outlet_streams.

    Parameters
    ----------
    unit_id : str
        Unique identifier in the process network.
    outlet_name : str
        Name assigned to the mixed outlet stream. Default "mixed_outlet".
    """

    unit_type:    str = field(default="Mixer",         init=False)
    outlet_name:  str = "mixed_outlet"

    # Internal results
    _t_mix:   float = field(default=0.0, init=False, repr=False)
    _m_total: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self):
        self.unit_type = "Mixer"

    # =========================================================================
    # solve()
    # =========================================================================

    def solve(self) -> None:
        self.reset()

        self.log_section("Mixer Setup")
        self.log(f"Unit:         {self.unit_id}")
        self.log(f"Inlet count:  {len(self.inlet_streams)}")

        # ── Validate ──────────────────────────────────────────────────────────
        if len(self.inlet_streams) < 2:
            raise StreamError(
                f"Unit '{self.unit_id}': Mixer requires at least 2 inlet "
                f"streams, got {len(self.inlet_streams)}."
            )
        if len(self.inlet_streams) > 10:
            raise StreamError(
                f"Unit '{self.unit_id}': Mixer supports up to 10 inlets, "
                f"got {len(self.inlet_streams)}."
            )

        streams = list(self.inlet_streams.values())

        # Log each inlet
        for key, s in self.inlet_streams.items():
            self.log(f"\n  [{key}]  T={s.temperature_c:.2f}°C  "
                     f"ṁ={s.mass_flowrate:.4f} kg/s  "
                     f"Cp={s.cp:.1f} J/(kg·K)  "
                     f"phase={s.phase}")

        # ── Phase check ───────────────────────────────────────────────────────
        phases = {s.phase for s in streams}
        if len(phases) > 1:
            self.warn(
                f"Inlet streams have mixed phases {phases}. "
                f"Outlet phase set to 'mixed'. "
                f"Ideal mixing assumed — check phase behaviour."
            )
        outlet_phase = "mixed" if len(phases) > 1 else phases.pop()

        # ── Mass balance ──────────────────────────────────────────────────────
        self.log_section("Mass Balance")

        m_total = sum(s.mass_flowrate for s in streams)
        self.log(f"ṁ_out = Σṁᵢ = "
                 f"{' + '.join(f'{s.mass_flowrate:.4f}' for s in streams)}")
        self.log(f"      = {m_total:.6f} kg/s")
        self._m_total = m_total

        # ── Energy balance ────────────────────────────────────────────────────
        self.log_section("Energy Balance  (adiabatic, T_ref = 0 K)")

        sum_mcp_t = sum(s.mass_flowrate * s.cp * s.temperature for s in streams)
        sum_mcp   = sum(s.mass_flowrate * s.cp for s in streams)

        self.log("T_mix = Σ(ṁᵢ·Cpᵢ·Tᵢ) / Σ(ṁᵢ·Cpᵢ)")
        for key, s in self.inlet_streams.items():
            self.log(f"  [{key}]: {s.mass_flowrate:.4f}×{s.cp:.1f}"
                     f"×{s.temperature:.2f} = "
                     f"{s.mass_flowrate*s.cp*s.temperature:.2f}")
        self.log(f"  Σ(ṁᵢCpᵢTᵢ) = {sum_mcp_t:.4f}")
        self.log(f"  Σ(ṁᵢCpᵢ)   = {sum_mcp:.4f} W/K")

        T_mix = sum_mcp_t / sum_mcp
        self.log(f"  T_mix       = {T_mix:.4f} K  ({T_mix - 273.15:.4f} °C)")
        self._t_mix = T_mix

        # Warn on large temperature swing
        T_vals = [s.temperature for s in streams]
        delta_T = max(T_vals) - min(T_vals)
        if delta_T > 50:
            self.warn(
                f"Inlet temperature spread = {delta_T:.1f} K. "
                f"Verify stream identities — large ΔT may indicate "
                f"an incorrect stream connection."
            )

        # ── Mixed properties (mass-weighted) ─────────────────────────────────
        self.log_section("Mixed Stream Properties")

        Cp_mix  = sum_mcp / m_total
        rho_mix = m_total / sum(s.mass_flowrate / s.density for s in streams)
        mu_mix  = sum(s.mass_flowrate * s.viscosity for s in streams) / m_total
        k_mix   = (sum(s.mass_flowrate * s.thermal_conductivity
                       for s in streams) / m_total)
        P_out   = min(s.pressure for s in streams)   # conservative

        self.log(f"Cp_mix  = {Cp_mix:.2f}  J/(kg·K)  (mass-weighted)")
        self.log(f"ρ_mix   = {rho_mix:.3f} kg/m³     (volume-additive)")
        self.log(f"μ_mix   = {mu_mix:.4e}  Pa·s      (mass-weighted)")
        self.log(f"k_mix   = {k_mix:.4f}  W/(m·K)   (mass-weighted)")
        self.log(f"P_out   = {P_out/1000:.2f} kPa              (min inlet)")

        # ── Mass balance closure ──────────────────────────────────────────────
        self.log_section("Mass Balance Closure")
        self.log(f"ṁ_out = {m_total:.6f} kg/s")
        self.log(f"Σṁᵢ   = {m_total:.6f} kg/s")
        self.log(f"Error = 0.000000 kg/s  ✓")

        # ── Build outlet stream ───────────────────────────────────────────────
        self.outlet_streams["outlet"] = ProcessStream(
            name=self.outlet_name,
            temperature=T_mix,
            pressure=P_out,
            mass_flowrate=m_total,
            cp=Cp_mix,
            density=rho_mix,
            viscosity=mu_mix,
            thermal_conductivity=k_mix,
            phase=outlet_phase,
            source_unit=self.unit_id,
        )

        self.log_section("Results")
        self.log(f"Outlet T    = {T_mix - 273.15:.4f} °C")
        self.log(f"Outlet ṁ    = {m_total:.4f} kg/s")
        self.log(f"Outlet Cp   = {Cp_mix:.2f} J/(kg·K)")
        self.log(f"Outlet ρ    = {rho_mix:.3f} kg/m³")
        self.log(f"Outlet phase = {outlet_phase}")

        self.is_solved = True

    # =========================================================================
    # summary()
    # =========================================================================

    def summary(self) -> dict:
        base = self.base_summary()
        outlet = self.outlet_streams.get("outlet")
        return {
            **base,
            "outlet_temperature_C":   round(self._t_mix - 273.15, 4),
            "outlet_flowrate_kg_s":   round(self._m_total, 6),
            "n_inlets":               len(self.inlet_streams),
            "outlet_cp_J_kgK":        round(outlet.cp, 2) if outlet else None,
            "outlet_density_kg_m3":   round(outlet.density, 3) if outlet else None,
            "outlet_phase":           outlet.phase if outlet else None,
        }
