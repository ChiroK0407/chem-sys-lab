"""
simulation/units/splitter.py

Stream splitter — 1 inlet → N outlets.

Each outlet stream is identical in composition, temperature, pressure,
and all physical properties to the inlet. Only mass flowrate differs,
scaled by the split fraction.

    ṁᵢ = fᵢ · ṁ_inlet      where Σfᵢ = 1.0

Usage modes
-----------
Mode A — explicit fractions:
    splitter.split_fractions = {"overhead": 0.6, "bottoms": 0.4}

Mode B — equal split by count:
    splitter.n_outlets = 3   (auto-assigns fractions of 1/3 each)
    splitter.outlet_names = ["A", "B", "C"]   (optional names)

References
----------
- Coulson & Richardson Vol. 1, Chapter 3
- McCabe, Smith & Harriott, Chapter 7
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from simulation.core.stream import ProcessStream
from simulation.core.unit_operation import UnitOperation
from simulation.core.exceptions import (
    StreamError,
    InfeasibleDesignError,
)


@dataclass
class Splitter(UnitOperation):
    """
    Stream splitter — 1 inlet keyed "feed" → N outlet streams.

    Parameters
    ----------
    unit_id : str
        Unique identifier in the process network.
    split_fractions : dict, optional
        {outlet_name: fraction}. Must sum to 1.0 ± 1e-4.
        Takes priority over n_outlets.
    n_outlets : int, optional
        Number of equal-fraction outlets. Used when split_fractions
        is not supplied. Default 2.
    outlet_names : list[str], optional
        Names for equal-split outlets. Defaults to
        ["outlet_1", "outlet_2", ...] if not supplied.
    """

    unit_type:        str                    = field(default="Splitter", init=False)
    split_fractions:  Optional[Dict[str, float]] = None
    n_outlets:        int                    = 2
    outlet_names:     Optional[List[str]]    = None

    def __post_init__(self):
        self.unit_type = "Splitter"

    # =========================================================================
    # solve()
    # =========================================================================

    def solve(self) -> None:
        self.reset()

        self.log_section("Splitter Setup")
        self.log(f"Unit: {self.unit_id}")

        # ── Get inlet ─────────────────────────────────────────────────────────
        feed = self.get_inlet("feed")
        self.log(f"\nInlet '{feed.name}':")
        self.log(f"  T   = {feed.temperature_c:.2f} °C")
        self.log(f"  P   = {feed.pressure_kpa:.2f} kPa")
        self.log(f"  ṁ   = {feed.mass_flowrate:.4f} kg/s")
        self.log(f"  Cp  = {feed.cp:.2f} J/(kg·K)")
        self.log(f"  phase = {feed.phase}")

        # ── Resolve split fractions ───────────────────────────────────────────
        fractions = self._resolve_fractions()

        self.log_section("Split Fractions")
        for name, frac in fractions.items():
            self.log(f"  {name}: {frac:.6f}  "
                     f"(ṁ = {frac * feed.mass_flowrate:.4f} kg/s)")

        # ── Validate sum ──────────────────────────────────────────────────────
        total_frac = sum(fractions.values())
        self.log(f"\n  Σfᵢ = {total_frac:.8f}  (must equal 1.0)")
        if abs(total_frac - 1.0) > 1e-4:
            raise InfeasibleDesignError(
                self.unit_id,
                f"Split fractions sum to {total_frac:.6f}, not 1.0. "
                f"Adjust fractions to sum to exactly 1."
            )

        # ── Build outlet streams ──────────────────────────────────────────────
        self.log_section("Outlet Streams")

        m_check = 0.0
        for name, frac in fractions.items():
            m_out = frac * feed.mass_flowrate
            m_check += m_out
            self.outlet_streams[name] = feed.copy_with(
                name=name,
                mass_flowrate=m_out,
                source_unit=self.unit_id,
            )
            self.log(f"  {name}: ṁ = {frac:.4f} × {feed.mass_flowrate:.4f}"
                     f" = {m_out:.4f} kg/s")

        # ── Mass balance closure ──────────────────────────────────────────────
        self.log_section("Mass Balance Closure")
        error = abs(m_check - feed.mass_flowrate)
        rel_error = error / feed.mass_flowrate if feed.mass_flowrate > 0 else 0
        self.log(f"ṁ_inlet  = {feed.mass_flowrate:.6f} kg/s")
        self.log(f"Σṁ_out   = {m_check:.6f} kg/s")
        self.log(f"Error    = {error:.2e} kg/s  "
                 f"(relative: {rel_error:.2e})")
        if rel_error > 1e-4:
            self.warn(
                f"Mass balance error {rel_error:.2e} exceeds 1e-4. "
                f"Check floating-point precision of split fractions."
            )
        else:
            self.log("✓ Mass balance closed")

        self.log_section("Results")
        self.log(f"N outlets = {len(fractions)}")
        self.log(f"Outlet T  = {feed.temperature_c:.2f} °C  (same as inlet)")
        self.log(f"Outlet P  = {feed.pressure_kpa:.2f} kPa  (same as inlet)")

        self.is_solved = True

    # =========================================================================
    # Helpers
    # =========================================================================

    def _resolve_fractions(self) -> Dict[str, float]:
        """
        Return the {name: fraction} dict to use.

        Priority:
        1. self.split_fractions (user-supplied explicit dict)
        2. Equal split using self.n_outlets + self.outlet_names
        """
        if self.split_fractions is not None:
            if len(self.split_fractions) < 2:
                raise StreamError(
                    f"Unit '{self.unit_id}': Splitter requires at least 2 "
                    f"outlets, got {len(self.split_fractions)}."
                )
            return dict(self.split_fractions)

        # Equal split
        if self.n_outlets < 2:
            raise StreamError(
                f"Unit '{self.unit_id}': n_outlets must be ≥ 2, "
                f"got {self.n_outlets}."
            )

        names = self.outlet_names or [
            f"outlet_{i+1}" for i in range(self.n_outlets)
        ]
        if len(names) != self.n_outlets:
            raise StreamError(
                f"Unit '{self.unit_id}': outlet_names length "
                f"({len(names)}) != n_outlets ({self.n_outlets})."
            )

        frac = 1.0 / self.n_outlets
        return {name: frac for name in names}

    # =========================================================================
    # summary()
    # =========================================================================

    def summary(self) -> dict:
        base = self.base_summary()
        fractions = self._resolve_fractions() if not self.is_solved else {
            k: v.mass_flowrate / self.inlet_streams["feed"].mass_flowrate
            for k, v in self.outlet_streams.items()
            if isinstance(v, ProcessStream)
        }
        return {
            **base,
            "n_outlets":       len(self.outlet_streams),
            "split_fractions": {
                k: round(v, 6) for k, v in fractions.items()
            },
            "inlet_flowrate_kg_s": (
                round(self.inlet_streams["feed"].mass_flowrate, 4)
                if "feed" in self.inlet_streams else None
            ),
        }
