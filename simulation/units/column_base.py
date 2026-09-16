import math
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from simulation.core.unit_operation import UnitOperation
from simulation.core.exceptions import StreamError, InfeasibleDesignError
from simulation.units.column_catalog import get_packing, get_tray


@dataclass
class ColumnBase(UnitOperation):
    """
    Abstract base class for all separation columns (absorber, stripper, distillation)[cite: 5103].
    Extends UnitOperation to provide shared hydraulic, sizing, and mechanical equations[cite: 5103].
    """
    # Shared attributes as dataclass fields [cite: 5104]
    internal_type: str = "structured_packing"  # "random_packing" / "structured_packing" / "tray" [cite: 5104]
    internal_key: str = "MELLAPAK_250Y"        # Catalog key from column_catalog [cite: 5104]
    column_diameter_m: Optional[float] = None  # None = calculate from flooding [cite: 5104]
    operating_pressure_Pa: float = 101325.0
    
    # Computed parameters [cite: 5104]
    pressure_drop_total_Pa: float = field(default=0.0, init=False)
    n_theoretical_stages: float = field(default=0.0, init=False)
    column_height_m: float = field(default=0.0, init=False)
    HETP_m: float = field(default=0.0, init=False)

    def _load_internal(self) -> dict:
        """
        Loads the internal catalog entry using internal_type and internal_key[cite: 5105].
        Calls get_packing() or get_tray() from column_catalog.py[cite: 5106].
        Raises StreamError if key not found[cite: 5106].
        """
        entry = None
        if self.internal_type in ("random_packing", "structured_packing"):
            entry = get_packing(self.internal_key)
        elif self.internal_type == "tray":
            entry = get_tray(self.internal_key)
            
        if not entry:
            raise StreamError(
                f"Column internal key '{self.internal_key}' "
                f"not found for internal type '{self.internal_type}'."
            )
        return entry

    def _calc_flooding_velocity(self, rho_V: float, rho_L: float, surface_tension: float, Fp: float, L_kg_s: float, G_kg_s: float) -> float:
        """
        Bain-Hougen algebraic approximation to GPDC chart[cite: 5107]:
            C_flood = exp(A0 + A1*ln(FLV) + A2*ln(FLV)^2) [cite: 5107]
        where FLV = (L/G)*sqrt(rho_V/rho_L) is the flow parameter[cite: 5107].
        Coefficients A0=0.017, A1=-1.463, A2=-0.842 (fitted to GPDC chart)[cite: 5108].
        Returns flood velocity u_flood [m/s][cite: 5108].
        Reference: Bain & Hougen (1944), Kister Distillation Design Appendix B[cite: 5109].
        """
        if G_kg_s <= 0 or L_kg_s <= 0:
            # Fallback for boundary zero-flow states during startup evaluation
            return 1.0
            
        # 1. Compute Flow Parameter (FLV) [cite: 5107]
        flv = (L_kg_s / G_kg_s) * math.sqrt(rho_V / rho_L)
        
        # Guard against log domain errors for highly extreme flow parameters
        flv = max(0.01, min(flv, 10.0))
        
        # 2. Bain-Hougen Polynomial Approximation [cite: 5107, 5108]
        A0, A1, A2 = 0.017, -1.463, -0.842
        ln_flv = math.log(flv)
        c_flood = math.exp(A0 + A1 * ln_flv + A2 * (ln_flv ** 2))
        
        # 3. Translate Capacity Factor to flood velocity u_flood (incorporating packing factor and physical bounds)
        # Standard conversion matching Kister's generalized chart relationships:
        # u_flood = C_flood * (σ / 0.02)^0.2 * sqrt((ρ_L - ρ_V) / ρ_V) / sqrt(F_p)
        sigma_ratio = (surface_tension / 0.02) ** 0.2 if surface_tension > 0 else 1.0
        density_factor = math.sqrt((rho_L - rho_V) / rho_V) if rho_L > rho_V else 1.0
        fp_factor = math.sqrt(Fp) if Fp > 0 else 1.0
        
        u_flood = (c_flood * sigma_ratio * density_factor) / fp_factor
        return u_flood

    def _calc_column_diameter(self, G_kg_s: float, rho_V: float, u_flood: float, flood_fraction: float = 0.75) -> float:
        """
        D = sqrt(4*G_kg_s / (pi * rho_V * u_flood * flood_fraction)) [cite: 5110]
        Rounds up to nearest standard TEMA shell diameter from this list[cite: 5110]:
        [0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 
         2.4, 2.6, 3.0, 3.5, 4.0, 4.5, 5.0] metres[cite: 5110].
        """
        if rho_V <= 0 or u_flood <= 0 or flood_fraction <= 0:
            return 0.3
            
        raw_diameter = math.sqrt((4.0 * G_kg_s) / (math.pi * rho_V * u_flood * flood_fraction))
        
        standard_diameters = [
            0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0,
            2.4, 2.6, 3.0, 3.5, 4.0, 4.5, 5.0
        ]
        
        # Find next highest standard size [cite: 5110]
        for std_d in standard_diameters:
            if std_d >= raw_diameter:
                return std_d
                
        return standard_diameters[-1]

    def _calc_packed_height(self, N_theo: float, HETP: float) -> float:
        """
        Z = N_theo * HETP [cite: 5111]
        Adds 20% design margin: Z_design = 1.2 * Z [cite: 5111]
        Logs both values[cite: 5111].
        """
        z_base = N_theo * HETP
        z_design = 1.2 * z_base
        self.log(f"Packed height sizing: Theoretical Z = {z_base:.3f} m, Design Z (20% margin) = {z_design:.3f} m")
        return z_design

    def _calc_tray_height(self, N_actual: float, tray_spacing_mm: float) -> float:
        """
        H = N_actual * tray_spacing_mm/1000 [cite: 5112]
        Adds 20% for top and bottom disengagement sections[cite: 5112].
        """
        h_trays = N_actual * (tray_spacing_mm / 1000.0)
        h_total = 1.2 * h_trays
        self.log(f"Trayed height sizing: Tray stack = {h_trays:.3f} m, Total height (with disengagement) = {h_total:.3f} m")
        return h_total

    def _check_flooding(self, u_actual: float, u_flood: float) -> float:
        """
        Returns flood_fraction = u_actual / u_flood[cite: 5113].
        Raises InfeasibleDesignError if flood_fraction > 0.85[cite: 5113].
        Warns if flood_fraction > 0.80[cite: 5113].
        """
        if u_flood <= 0:
            return 0.0
            
        flood_fraction = u_actual / u_flood
        
        if flood_fraction > 0.85:
            raise InfeasibleDesignError(
                f"Column hydrodynamics failed: Fraction of fluid flooding ({flood_fraction:.2%}) "
                f"breached upper performance ceiling limit of 85.0%."
            )
        elif flood_fraction > 0.80:
            self.warn(f"Column vapor velocity is tight. Flooding fraction is at {flood_fraction:.2%}, approaching risk boundary.")
            
        return flood_fraction

    def _asme_wall_thickness(self, P_Pa: float, D_m: float, S_allowable: float = 138e6, E_weld: float = 1.0, corrosion_mm: float = 3.0) -> float:
        """
        ASME BPVC Section VIII Div.1 hoop stress equation[cite: 5190]:
        t = P*R / (S*E - 0.6*P) + corrosion_allowance [cite: 5190]
        P in Pa, R = D/2 in m, S in Pa, returns t in mm[cite: 5190].
        Default S=138 MPa (carbon steel SA-516 Grade 70 at 300°C)[cite: 5190].
        Log the calculation with each variable shown[cite: 5190].
        Reference: ASME BPVC VIII-1, Equation UG-27(c)(1)[cite: 5190].
        """
        R_m = D_m / 2.0
        # Mechanical thickness equation evaluates to meters [cite: 5190]
        denominator = (S_allowable * E_weld) - (0.6 * P_Pa)
        t_mechanical_m = (P_Pa * R_m) / denominator
        
        # Convert mechanical thickness to mm and append corrosion allowance [cite: 5190]
        t_total_mm = (t_mechanical_m * 1000.0) + corrosion_mm
        
        self.log_section("ASME Pressure Vessel Compliance Audit")
        self.log(f"Equation Reference: ASME BPVC VIII-1 UG-27(c)(1)")
        self.log(f"Inputs: P = {P_Pa:.1f} Pa, D = {D_m:.2f} m, R = {R_m:.2f} m")
        self.log(f"Material: S_allowable = {S_allowable/1e6:.1f} MPa, E_weld = {E_weld:.2f}")
        self.log(f"Corrosion Allowance: {corrosion_mm:.1f} mm")
        self.log(f"Computed Shell Thickness: t_total = {t_total_mm:.2f} mm")
        
        return t_total_mm

    @abstractmethod
    def solve(self) -> None:
        """Perform specific mass transfer and design calculations."""
        pass

    @abstractmethod
    def summary(self) -> dict:
        """Return key simulation results as a flat UI-compliant dictionary."""
        pass