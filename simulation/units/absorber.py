import os
import json
import math
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from simulation.core.stream import ProcessStream, UtilityStream
from simulation.core.exceptions import StreamError, InfeasibleDesignError
from simulation.units.column_base import ColumnBase


@dataclass
class Absorber(ColumnBase):
    """
    Gas Absorption Column (Scrubber) Module.
    Models the counter-current mass transfer of a solute from a gas stream into a liquid solvent.
    """
    # Dataclass fields beyond ColumnBase
    gas_component: str = "CO2"
    solvent_id: str = "MEA_30wt%"
    y_in: float = 0.12            # Solute mole fraction in gas feed
    y_out: float = 0.01           # Target solute mole fraction in gas outlet
    x_in: float = 0.0             # Solute mole fraction in lean solvent feed
    G_mol_s: float = 100.0         # Total gas molar flow rate (mol/s)
    L_mol_s: Optional[float] = None  # Operating solvent molar flow rate (mol/s), None = calculate min
    T_K: float = 313.15           # Operating temperature (K)
    L_G_ratio_multiplier: float = 1.5  # Multiplier over minimum solvent rate (L/G_min multiplier)

    # Class-level type description required by UnitOperation infrastructure
    unit_type: str = field(default="Absorber", init=False)

    def solve(self) -> None:
        """
        Executes first-principles mass transfer sizing, hydraulic column diameter scaling,
        and ASME mechanical thickness validation.
        """
        self.log_section(f"Gas Absorption Simulation: Unit {self.unit_id}")
        
        # Universal Constants
        R_gas_constant = 8.31446  # J/(mol*K)
        P_atm = self.operating_pressure_Pa / 101325.0

        # --- Physical Property Data Loading Lookup ---
        base_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        
        # 1. Load Solvent Properties
        solvent_props = {}
        solvent_file = os.path.join(base_data_path, "solvent_properties.json")
        if os.path.exists(solvent_file):
            try:
                with open(solvent_file, "r") as f:
                    solvent_props = json.load(f).get(self.solvent_id, {})
            except Exception:
                pass
                
        # Heuristic fallbacks if JSON registry is completely empty or missing keys
        MW_solvent = solvent_props.get("MW", 18.02 if "water" in self.solvent_id.lower() else 61.08)
        rho_L = solvent_props.get("density_kg_m3", 1000.0 if "water" in self.solvent_id.lower() else 1010.0)
        surface_tension = solvent_props.get("surface_tension_N_m", 0.072 if "water" in self.solvent_id.lower() else 0.055)

        # 2. Load Solubility (Henry's Law) Constants
        solubility_data = {}
        solubility_file = os.path.join(base_data_path, "solubility_data.json")
        pair_key = f"{self.gas_component}_{self.solvent_id}"
        if os.path.exists(solubility_file):
            try:
                with open(solubility_file, "r") as f:
                    solubility_data = json.load(f).get(pair_key, {})
            except Exception:
                pass

        # Load reference constants or pull thermodynamic defaults
        H_ref = solubility_data.get("H_ref", 30.0)       # Henry's constant at reference temp (atm / mole fraction)
        T_ref = solubility_data.get("T_ref", 298.15)     # Reference temperature (K)
        dH_sol_J_mol = solubility_data.get("dH_sol", -25000.0)  # Heat of solution (exothermic, J/mol)
        MW_gas = solubility_data.get("MW_gas", 44.01 if self.gas_component == "CO2" else 28.97)

        # --- Temperature-Correct Henry's Constant using Van't Hoff ---
        # H(T) = H_ref * exp(-dH_sol/R * (1/T - 1/T_ref))
        vant_hoff_exponent = -(dH_sol_J_mol / R_gas_constant) * ((1.0 / self.T_K) - (1.0 / T_ref))
        H_T = H_ref * math.exp(vant_hoff_exponent)
        
        # Equilibrium Ratio K = y*/x = H(T) / P_total_atm
        K_value = H_T / P_atm
        
        self.log(f"Vant Hoff Thermo Sync: H_ref = {H_ref:.2f} atm, H(T) at {self.T_K:.2f} K = {H_T:.2f} atm")
        self.log(f"Equilibrium Distribution Ratio K (y*/x) = {K_value:.4f} at total pressure {P_atm:.3f} atm")

        # --- Step 1: Minimum Liquid Rate (Kremser Boundary) ---
        # At minimum L/G, the liquid exiting the column bottom is in perfect equilibrium with the rich inlet gas
        x_out_max = self.y_in / K_value
        
        if x_out_max <= self.x_in:
            raise InfeasibleDesignError(
                f"Thermodynamic operating constraint violation: Rich gas inlet y_in ({self.y_in:.3f}) "
                f"is already below or at equilibrium with the lean solvent input x_in ({self.x_in:.3f})."
            )
            
        lg_min = (self.y_in - self.y_out) / (x_out_max - self.x_in)
        L_min = lg_min * self.G_mol_s
        
        if self.L_mol_s is not None:
            L_operating = self.L_mol_s
            self.log(f"Operating solvent feed supplied explicitly by process configuration: L = {L_operating:.2f} mol/s")
        else:
            L_operating = self.L_G_ratio_multiplier * L_min
            self.log(f"Solver solved minimum solvent rate: L_min = {L_min:.2f} mol/s (Multiplier = {self.L_G_ratio_multiplier:.2f}x)")
            
        self.log(f"Design Operating Solvent Rate: L_operating = {L_operating:.2f} mol/s")

        # --- Step 2: Absorption Factor Evaluation ---
        # A = L / (K * G)
        absorption_factor_A = L_operating / (K_value * self.G_mol_s)
        self.log(f"Computed Column Absorption Factor (A) = {absorption_factor_A:.4f}")
        
        if absorption_factor_A < 1.2:
            self.warn(f"Poor absorption factor (A = {absorption_factor_A:.2f} < 1.2). Tower requires a large number of theoretical stages.")
        elif absorption_factor_A > 5.0:
            self.warn(f"Excessive solvent circulation rate (A = {absorption_factor_A:.2f} > 5.0). High operating cost predicted for stripping/regeneration.")

        # --- Step 3: Number of Theoretical Stages (Kremser Equation) ---
        # N = ln[(y_in - K*x_in)/(y_out - K*x_in) * (1 - 1/A) + 1/A] / ln(A)
        numerator_term = (self.y_in - K_value * self.x_in) / (self.y_out - K_value * self.x_in)
        
        if abs(absorption_factor_A - 1.0) > 1e-4:
            kremser_inside = numerator_term * (1.0 - (1.0 / absorption_factor_A)) + (1.0 / absorption_factor_A)
            if kremser_inside <= 0:
                raise InfeasibleDesignError("Kremser separation parameter constraints went non-positive. Separation target is mathematically unreachable.")
            N_theo = math.log(kremser_inside) / math.log(absorption_factor_A)
        else:
            # Special limit case when A strictly equals 1.0
            N_theo = (self.y_in - self.y_out) / (self.y_out - K_value * self.x_in)
            
        self.n_theoretical_stages = max(0.1, N_theo)
        self.log(f"Separation Core Stage Metrics: N_theoretical = {self.n_theoretical_stages:.3f} stages")

        # --- Step 4: Column Sizing & Hydraulics ---
        entry = self._load_internal()
        
        # Calculate mass flows for flooding evaluation
        G_kg_s = (self.G_mol_s * MW_gas) / 1000.0
        L_kg_s = (L_operating * MW_solvent) / 1000.0
        
        # Gas Density via Ideal Gas Law
        rho_V = (self.operating_pressure_Pa * (MW_gas / 1000.0)) / (R_gas_constant * self.T_K)
        
        # Call base hydraulic helpers
        Fp = entry.get("packing_factor_sm1", entry.get("packing_factor", 65.0))
        u_flood = self._calc_flooding_velocity(rho_V, rho_L, surface_tension, Fp, L_kg_s, G_kg_s)
        
        if self.column_diameter_m is None:
            self.column_diameter_m = self._calc_column_diameter(G_kg_s, rho_V, u_flood, flood_fraction=0.75)
            self.log(f"Hydraulic sizing module auto-calculated tower standard TEMA shell diameter: D = {self.column_diameter_m:.2f} m")
        else:
            self.log(f"Using fixed column diameter override: D = {self.column_diameter_m:.2f} m")
            
        # Verify operating flooding limitations
        cross_sectional_area = (math.pi / 4.0) * (self.column_diameter_m ** 2)
        u_actual = (G_kg_s / rho_V) / cross_sectional_area
        self.flood_fraction = self._check_flooding(u_actual, u_flood)
        
        # Structural height sizing evaluation
        if self.internal_type in ("random_packing", "structured_packing"):
            self.HETP_m = entry.get("typical_h_etp_m", entry.get("typical_HETP", 0.5))
            self.column_height_m = self._calc_packed_height(self.n_theoretical_stages, self.HETP_m)
            self.n_actual_trays = None
        elif self.internal_type == "tray":
            tray_efficiency = entry.get("typical_tray_efficiency", 0.70)
            typical_spacing = entry.get("typical_tray_spacing_mm", [450, 600])
            tray_spacing_mm = typical_spacing[0] if isinstance(typical_spacing, list) else typical_spacing
            
            self.n_actual_trays = int(math.ceil(self.n_theoretical_stages / tray_efficiency))
            self.HETP_m = tray_spacing_mm / 1000.0  # Maps metric context fields
            self.column_height_m = self._calc_tray_height(self.n_actual_trays, tray_spacing_mm)
            self.log(f"Trayed geometry array: N_actual = {self.n_actual_trays} plates (Efficiency = {tray_efficiency:.1%})")

        # --- Step 5: ASME Wall Thickness Verification ---
        self.wall_thickness_mm = self._asme_wall_thickness(self.operating_pressure_Pa, self.column_diameter_m)

        # --- Step 6: Heat Duty Evaluation ---
        # Q_abs = G * delta_y * dH_sol
        delta_y = self.y_in - self.y_out
        moles_absorbed_s = self.G_mol_s * delta_y
        Q_abs = moles_absorbed_s * abs(dH_sol_J_mol)  # Watts
        
        cooling_stream = UtilityStream(
            stream_id=f"{self.unit_id}_cooling",
            utility_type="cooling_water",
            flowrate_kg_s=0.0,  # Placeholder handled by platform trackers
            heat_duty_W=Q_abs
        )
        self.utility_streams.append(cooling_stream)
        self.log(f"Isothermal thermal load audit: Exothermic release Q_abs = {Q_abs/1000.0:.3f} kW")

        # --- Step 7: Material Balance Outlet Stream Production ---
        # Gas outlet solute calculation
        gas_out_flow = self.G_mol_s  # Kremser dilution approximation
        liquid_out_flow = L_operating
        
        # Moles component balance: x_out = (L*x_in + G*(y_in - y_out)) / L
        x_out = (L_operating * self.x_in + self.G_mol_s * delta_y) / L_operating
        self.x_out_calculated = x_out

        # Generate output stream mappings matching platform contracts
        self.outlet_streams["gas_out"] = ProcessStream(
            stream_id=f"{self.unit_id}_gas_out",
            temperature_K=self.T_K,
            pressure_Pa=self.operating_pressure_Pa,
            total_molar_flow_mol_s=gas_out_flow,
            mole_fractions={self.gas_component: self.y_out, "inert_gas": 1.0 - self.y_out}
        )
        
        self.outlet_streams["liquid_out"] = ProcessStream(
            stream_id=f"{self.unit_id}_liquid_out",
            temperature_K=self.T_K,
            pressure_Pa=self.operating_pressure_Pa,
            total_molar_flow_mol_s=liquid_out_flow,
            mole_fractions={self.gas_component: x_out, "solvent": 1.0 - x_out}
        )

        self.is_solved = True
        self.log_section("Absorber Design Convergence Complete")

    def summary(self) -> dict:
        """
        Flattens multi-stage design outputs into a UI-compliant schema structure.
        """
        base = self.base_summary()
        extended = {
            "gas_component": self.gas_component,
            "solvent_id": self.solvent_id,
            "K_value": round(self.L_mol_s / (self.y_in / self.x_out_calculated) if hasattr(self, 'x_out_calculated') and self.x_out_calculated > 0 else 0.0, 4) if not self.is_solved else round(1.0, 4), # dynamic fallback safe
            "H_at_T": 0.0,  # Updated below
            "y_in": round(self.y_in, 4),
            "y_out": round(self.y_out, 4),
            "x_in": round(self.x_in, 4),
            "x_out": round(getattr(self, "x_out_calculated", 0.0), 4),
            "L_min_mol_s": round(0.0, 2),  # Filled post-solve
            "L_operating_mol_s": round(0.0, 2),
            "G_mol_s": round(self.G_mol_s, 2),
            "absorption_factor_A": round(0.0, 4),
            "N_theoretical": round(self.n_theoretical_stages, 2),
            "column_diameter_m": round(self.column_diameter_m, 2) if self.column_diameter_m else None,
            "column_height_m": round(self.column_height_m, 2),
            "HETP_m": round(self.HETP_m, 3),
            "flood_fraction": round(getattr(self, "flood_fraction", 0.0), 4),
            "wall_thickness_mm": round(getattr(self, "wall_thickness_mm", 0.0), 2),
            "Q_absorption_kW": round(0.0, 2),
            "internal_type": self.internal_type,
            "internal_key": self.internal_key,
            "operating_pressure_kPa": round(self.operating_pressure_Pa / 1000.0, 1),
            "operating_T_C": round(self.T_K - 273.15, 1)
        }

        # Safe attribute recovery if the simulation model hit a fatal constraint
        if self.is_solved:
            P_atm = self.operating_pressure_Pa / 101325.0
            base_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            solubility_file = os.path.join(base_data_path, "solubility_data.json")
            pair_key = f"{self.gas_component}_{self.solvent_id}"
            
            H_ref, T_ref, dH_sol = 30.0, 298.15, -25000.0
            if os.path.exists(solubility_file):
                try:
                    with open(solubility_file, "r") as f:
                        data = json.load(f).get(pair_key, {})
                        H_ref = data.get("H_ref", 30.0)
                        T_ref = data.get("T_ref", 298.15)
                        dH_sol = data.get("dH_sol", -25000.0)
                except Exception:
                    pass
            
            H_T = H_ref * math.exp(-(dH_sol / 8.31446) * ((1.0 / self.T_K) - (1.0 / T_ref)))
            K_val = H_T / P_atm
            x_out_max = self.y_in / K_val
            lg_min = (self.y_in - self.y_out) / (x_out_max - self.x_in) if x_out_max > self.x_in else 0.0
            l_min_calc = lg_min * self.G_mol_s
            l_op_calc = self.L_mol_s if self.L_mol_s is not None else self.L_G_ratio_multiplier * l_min_calc
            
            extended["H_at_T"] = round(H_T, 2)
            extended["K_value"] = round(K_val, 4)
            extended["L_min_mol_s"] = round(l_min_calc, 2)
            extended["L_operating_mol_s"] = round(l_op_calc, 2)
            extended["absorption_factor_A"] = round(l_op_calc / (K_val * self.G_mol_s), 4)
            extended["Q_absorption_kW"] = round((self.G_mol_s * (self.y_in - self.y_out) * abs(dH_sol)) / 1000.0, 2)
            
            if self.internal_type == "tray" and hasattr(self, "n_actual_trays"):
                extended["N_actual"] = self.n_actual_trays

        return {**base, **extended}