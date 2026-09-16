import os
import json
import math
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from simulation.core.stream import ProcessStream, UtilityStream
from simulation.core.exceptions import StreamError, InfeasibleDesignError
from simulation.units.column_base import ColumnBase


@dataclass
class Stripper(ColumnBase):
    """
    Gas Stripping / Solvent Regeneration Column Module.
    Models the counter-current mass transfer of a solute out of a rich liquid solvent 
    into a stripping gas or vapor medium (e.g., steam).
    """
    # Additional dataclass fields beyond ColumnBase
    stripping_agent: str = "steam"  # "steam" / "air" / "nitrogen" / "inert_gas"
    gas_component: str = "CO2"       # Solute being stripped
    solvent_id: str = "MEA_30wt%"
    x_in: float = 0.05               # Solute mole fraction in rich solvent feed
    x_out: float = 0.005             # Target solute mole fraction in lean solvent outlet
    y_in: float = 0.0                # Solute mole fraction in stripping gas feed
    L_mol_s: float = 150.0           # Total rich solvent liquid molar flow rate (mol/s)
    G_mol_s: Optional[float] = None  # Stripping gas flow rate (mol/s), None = calculate min
    T_K: float = 393.15              # Stripping operating temperature (K) - typically high
    L_G_ratio_multiplier: float = 1.5  # Safety factor multiplier above minimum stripping gas rate

    # Computed attributes
    regeneration_steam_kg_s: float = field(default=0.0, init=False)
    
    # Class-level type description required by UnitOperation infrastructure
    unit_type: str = field(default="Stripper", init=False)

    def solve(self) -> None:
        """
        Executes first-principles mass transfer stripping design, column sizing,
        reboiler/condenser thermal duty integration, and mechanical thickness validation.
        """
        self.log_section(f"Gas Stripping Simulation: Unit {self.unit_id}")
        
        # Universal Constants
        R_gas_constant = 8.31446  # J/(mol*K)
        P_atm = self.operating_pressure_Pa / 101325.0
        lambda_steam_J_kg = 2257000.0  # Latent heat of vaporization of water/steam at 100°C [J/kg]

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
                
        MW_solvent = solvent_props.get("MW", 18.02 if "water" in self.solvent_id.lower() else 61.08)
        rho_L = solvent_props.get("density_kg_m3", 1000.0 if "water" in self.solvent_id.lower() else 960.0)  # Lower density at high T
        surface_tension = solvent_props.get("surface_tension_N_m", 0.072 if "water" in self.solvent_id.lower() else 0.045)
        cp_liquid_J_mol_K = solvent_props.get("cp_J_mol_K", 75.3 if "water" in self.solvent_id.lower() else 145.0)

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

        H_ref = solubility_data.get("H_ref", 30.0)       # Henry's constant at reference temp (atm / mole fraction)
        T_ref = solubility_data.get("T_ref", 298.15)     # Reference temperature (K)
        dH_sol_J_mol = solubility_data.get("dH_sol", -25000.0)  # Heat of solution (exothermic, J/mol)
        MW_gas = solubility_data.get("MW_gas", 44.01 if self.gas_component == "CO2" else 28.97)

        # --- Step 1: Equilibrium Analysis at Stripper Temperature ---
        # Temperature-correct Henry's constant via Van't Hoff relationship
        vant_hoff_exponent = -(dH_sol_J_mol / R_gas_constant) * ((1.0 / self.T_K) - (1.0 / T_ref))
        H_T = H_ref * math.exp(vant_hoff_exponent)
        
        # Equilibrium Ratio K = y*/x = H(T) / P_total_atm
        K_strip = H_T / P_atm
        
        self.log(f"Van't Hoff Thermodynamic Shift:")
        self.log(f"  H_ref = {H_ref:.2f} atm, H(T_strip) at {self.T_K:.2f} K = {H_T:.2f} atm")
        self.log(f"  K_strip (y*/x) = {K_strip:.4f} at total stripping pressure {self.operating_pressure_Pa/1000.0:.1f} kPa")

        # --- Step 2: Minimum Gas Rate & Stripping Factor ---
        # At minimum stripping vapor flow, the overhead gas is in absolute equilibrium with the incoming rich solvent feed
        y_out_max = K_strip * self.x_in
        
        if y_out_max <= self.y_in:
            raise InfeasibleDesignError(
                f"Thermodynamic stripping boundary constraint violation: Gas feed y_in ({self.y_in:.3f}) "
                f"is already above or at equilibrium limit with rich inlet liquid x_in ({self.x_in:.3f})."
            )
            
        # Slope of operating line at absolute mass balance minimum limit
        gl_min = (self.x_in - self.x_out) / (y_out_max - self.y_in)
        G_min = gl_min * self.L_mol_s
        
        if self.G_mol_s is not None:
            G_operating = self.G_mol_s
            self.log(f"Operating stripping agent feed set by override configuration: G = {G_operating:.2f} mol/s")
        else:
            G_operating = self.L_G_ratio_multiplier * G_min
            self.log(f"Solver solved minimum stripping gas: G_min = {G_min:.2f} mol/s (Multiplier = {self.L_G_ratio_multiplier:.2f}x)")
            
        self.G_mol_s = G_operating
        self.log(f"Design Operating Stripping Rate: G_operating = {G_operating:.2f} mol/s")

        # Stripping Factor (S) = K * G / L (Inverse of absorption factor)
        stripping_factor_S = (K_strip * G_operating) / self.L_mol_s
        self.log(f"Computed Column Stripping Factor (S) = {stripping_factor_S:.4f}")
        
        if stripping_factor_S < 1.2:
            self.warn(f"Poor stripping performance envelope (S = {stripping_factor_S:.2f} < 1.2). Tower requires significant gas addition or higher temperature.")

        # --- Step 3: Number of Theoretical Stages (Kremser Equation for Stripping) ---
        # N = ln[(x_in - y_in/K) / (x_out - y_in/K) * (1 - 1/S) + 1/S] / ln(S)
        numerator_term = (self.x_in - (self.y_in / K_strip)) / (self.x_out - (self.y_in / K_strip))
        
        if abs(stripping_factor_S - 1.0) > 1e-4:
            kremser_inside = numerator_term * (1.0 - (1.0 / stripping_factor_S)) + (1.0 / stripping_factor_S)
            if kremser_inside <= 0:
                raise InfeasibleDesignError("Kremser stripping matrix parameter went non-positive. Regeneration target is mathematically unreachable.")
            N_theo = math.log(kremser_inside) / math.log(stripping_factor_S)
        else:
            N_theo = (self.x_in - self.x_out) / (self.x_out - (self.y_in / K_strip))
            
        self.n_theoretical_stages = max(0.1, N_theo)
        self.log(f"Separation Core Stage Metrics: N_theoretical = {self.n_theoretical_stages:.3f} stages")

        # --- Step 4: Column Sizing & Hydraulics ---
        entry = self._load_internal()
        
        # Determine average molecular weight of gas phase based on stripping agent selection
        if self.stripping_agent == "steam":
            MW_agent = 18.02
        elif self.stripping_agent == "nitrogen":
            MW_agent = 28.01
        elif self.stripping_agent == "air":
            MW_agent = 28.97
        else:
            MW_agent = 30.0  # Generic inert fallback
            
        # Combine gas properties accounting for raw overhead mass load estimation
        G_kg_s = (G_operating * MW_agent) / 1000.0
        L_kg_s = (self.L_mol_s * MW_solvent) / 1000.0
        
        # Gas Density via Ideal Gas Law
        rho_V = (self.operating_pressure_Pa * (MW_agent / 1000.0)) / (R_gas_constant * self.T_K)
        
        # Call base hydraulic helpers
        Fp = entry.get("packing_factor_sm1", entry.get("packing_factor", 65.0))
        u_flood = self._calc_flooding_velocity(rho_V, rho_L, surface_tension, Fp, L_kg_s, G_kg_s)
        
        if self.column_diameter_m is None:
            self.column_diameter_m = self._calc_column_diameter(G_kg_s, rho_V, u_flood, flood_fraction=0.75)
            self.log(f"Hydraulic sizing module auto-calculated tower standard TEMA shell diameter: D = {self.column_diameter_m:.2f} m")
        else:
            self.log(f"Using fixed column diameter override: D = {self.column_diameter_m:.2f} m")
            
        cross_sectional_area = (math.pi / 4.0) * (self.column_diameter_m ** 2)
        u_actual = (G_kg_s / rho_V) / cross_sectional_area
        self.flood_fraction = self._check_flooding(u_actual, u_flood)
        
        # Structural height calculations
        if self.internal_type in ("random_packing", "structured_packing"):
            self.HETP_m = entry.get("typical_h_etp_m", entry.get("typical_HETP", 0.5))
            self.column_height_m = self._calc_packed_height(self.n_theoretical_stages, self.HETP_m)
            self.n_actual_trays = None
        elif self.internal_type == "tray":
            tray_efficiency = entry.get("typical_tray_efficiency", 0.70)
            typical_spacing = entry.get("typical_tray_spacing_mm", [450, 600])
            tray_spacing_mm = typical_spacing[0] if isinstance(typical_spacing, list) else typical_spacing
            
            self.n_actual_trays = int(math.ceil(self.n_theoretical_stages / tray_efficiency))
            self.HETP_m = tray_spacing_mm / 1000.0
            self.column_height_m = self._calc_tray_height(self.n_actual_trays, tray_spacing_mm)
            self.log(f"Trayed geometry array: N_actual = {self.n_actual_trays} plates (Efficiency = {tray_efficiency:.1%})")

        # --- Step 5: ASME Wall Thickness Verification ---
        self.wall_thickness_mm = self._asme_wall_thickness(self.operating_pressure_Pa, self.column_diameter_m)

        # --- Step 6: Thermal Reboiler & Steam Sizing Duties ---
        Q_reb = 0.0
        Q_condenser = 0.0
        self.regeneration_steam_kg_s = 0.0
        
        if self.stripping_agent == "steam":
            # Approximated reboiler thermal requirement: Sensible heat addition + latent vaporization tracking
            T_feed_assumed = self.T_K - 40.0  # Assumes cold cross-exchanger inlet layout fallback boundary
            sensible_heat_W = self.L_mol_s * cp_liquid_J_mol_K * (self.T_K - T_feed_assumed)
            latent_heat_W = G_operating * (lambda_steam_J_kg * (18.02 / 1000.0))  # Convert latent load to mol scale
            Q_reb = sensible_heat_W + latent_heat_W
            
            self.regeneration_steam_kg_s = Q_reb / lambda_steam_J_kg
            
            reboiler_utility = UtilityStream(
                stream_id=f"{self.unit_id}_reboiler",
                utility_type="low_pressure_steam",
                flowrate_kg_s=self.regeneration_steam_kg_s,
                heat_duty_W=Q_reb
            )
            self.utility_streams.append(reboiler_utility)
            
            # Condenser Overhead Configuration
            Q_condenser = G_operating * (lambda_steam_J_kg * (18.02 / 1000.0))
            condenser_utility = UtilityStream(
                stream_id=f"{self.unit_id}_condenser",
                utility_type="cooling_water",
                flowrate_kg_s=0.0,
                heat_duty_W=Q_condenser
            )
            self.utility_streams.append(condenser_utility)
            
            self.log(f"Steam Thermal Load Sizing Summary:")
            self.log(f"  Q_reboiler  = {Q_reb/1e3:.2f} kW (Vaporization rate = {self.regeneration_steam_kg_s:.3f} kg/s)")
            self.log(f"  Q_condenser = {Q_condenser/1e3:.2f} kW")

        # --- Step 7: Material Balance Outlet Stream Production ---
        delta_x = self.x_in - self.x_out
        y_out = self.y_in + (self.L_mol_s * delta_x) / G_operating
        self.y_out_calculated = y_out

        # Generate output process streams
        self.outlet_streams["liquid_out"] = ProcessStream(
            stream_id=f"{self.unit_id}_liquid_out",
            temperature_K=self.T_K,
            pressure_Pa=self.operating_pressure_Pa,
            total_molar_flow_mol_s=self.L_mol_s,
            mole_fractions={self.gas_component: self.x_out, "solvent": 1.0 - self.x_out}
        )
        
        self.outlet_streams["gas_out"] = ProcessStream(
            stream_id=f"{self.unit_id}_gas_out",
            temperature_K=self.T_K if self.stripping_agent != "steam" else 373.15,  # Approaching condensation exit boundary
            pressure_Pa=self.operating_pressure_Pa,
            total_molar_flow_mol_s=G_operating,
            mole_fractions={self.gas_component: y_out, "stripping_medium": 1.0 - y_out}
        )

        self.is_solved = True
        self.log_section("Stripper Regeneration Sizing Convergence Complete")

    def summary(self) -> dict:
        """
        Flattens multi-stage stripping design outputs into a UI-compliant schema structure.
        """
        base = self.base_summary()
        extended = {
            "stripping_agent": self.stripping_agent,
            "gas_component": self.gas_component,
            "solvent_id": self.solvent_id,
            "K_value": 1.0,  # Updated safely below post-solve
            "H_at_T": 0.0,
            "x_in": round(self.x_in, 4),
            "x_out": round(self.x_out, 4),
            "y_in": round(self.y_in, 4),
            "y_out": round(getattr(self, "y_out_calculated", 0.0), 4),
            "L_mol_s": round(self.L_mol_s, 2),
            "G_mol_s": round(self.G_mol_s, 2) if self.G_mol_s else 0.0,
            "stripping_factor_S": 0.0,
            "N_theoretical": round(self.n_theoretical_stages, 2),
            "column_diameter_m": round(self.column_diameter_m, 2) if self.column_diameter_m else None,
            "column_height_m": round(self.column_height_m, 2),
            "HETP_m": round(self.HETP_m, 3),
            "flood_fraction": round(getattr(self, "flood_fraction", 0.0), 4),
            "wall_thickness_mm": round(getattr(self, "wall_thickness_mm", 0.0), 2),
            "Q_reboiler_kW": 0.0,
            "Q_condenser_kW": 0.0,
            "steam_rate_kg_s": round(self.regeneration_steam_kg_s, 4),
            "internal_type": self.internal_type,
            "internal_key": self.internal_key,
            "operating_pressure_kPa": round(self.operating_pressure_Pa / 1000.0, 1),
            "operating_T_C": round(self.T_K - 273.15, 1)
        }

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
            
            extended["H_at_T"] = round(H_T, 2)
            extended["K_value"] = round(K_val, 4)
            extended["stripping_factor_S"] = round((K_val * self.G_mol_s) / self.L_mol_s, 4)
            
            if self.stripping_agent == "steam" and len(self.utility_streams) >= 2:
                extended["Q_reboiler_kW"] = round(self.utility_streams[0].heat_duty_W / 1000.0, 2)
                extended["Q_condenser_kW"] = round(self.utility_streams[1].heat_duty_W / 1000.0, 2)
                
            if self.internal_type == "tray" and hasattr(self, "n_actual_trays"):
                extended["N_actual"] = self.n_actual_trays

        return {**base, **extended}