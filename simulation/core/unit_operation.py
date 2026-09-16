"""
simulation/core/unit_operation.py

Abstract base class for every unit operation in the platform.

Contract every subclass must honour
─────────────────────────────────────
1. solve() populates self.outlet_streams and self.utility_streams,
   then sets self.is_solved = True.
2. summary() returns a flat dict of key results for UI rendering
   and API responses — no ProcessStream objects inside it.
3. Inlet streams are added via add_inlet() before solve() is called.
4. Never mutate inlet streams — always produce new outlet streams
   via stream.copy_with().
5. Log every intermediate result to self.calculation_log so the
   frontend can render a transparent step-by-step working panel.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from simulation.core.stream import ProcessStream, UtilityStream
from simulation.core.exceptions import StreamNotFoundError, UnitNotSolvedError


@dataclass
class UnitOperation(ABC):
    """
    Abstract base for all unit operations.

    Subclasses add their own design parameters as dataclass fields
    and implement solve() + summary().

    Attributes
    ----------
    unit_id : str
        Unique identifier within a ProcessNetwork. Used as node ID
        in the React Flow PFD and as the key in network.units dict.
    unit_type : str
        Human-readable type label. Set as a class-level default in
        each subclass (e.g. "HeatExchanger", "Pump").
    inlet_streams : dict
        Keyed by role name (e.g. "hot", "cold", "feed").
        Populated by add_inlet() or by the network solver.
    outlet_streams : dict
        Keyed by role name. Populated by solve().
        Values must be ProcessStream objects.
    utility_streams : list
        UtilityStream objects created by solve().
        Consumed by UtilityTracker for dashboard aggregation.
    calculation_log : list[str]
        Every intermediate result logged by solve().
        Rendered in the frontend CalcLog component.
    is_solved : bool
        Set True by solve() on success. Guards get_outlet().
    warnings : list[str]
        Non-fatal design warnings (e.g. F-factor < 0.75).
        Displayed as yellow alerts in the UI.
    """

    unit_id: str
    unit_type: str = field(default="UnitOperation", init=False)

    # I/O
    inlet_streams: Dict[str, ProcessStream] = field(
        default_factory=dict, init=False
    )
    outlet_streams: Dict[str, ProcessStream] = field(
        default_factory=dict, init=False
    )
    utility_streams: List[UtilityStream] = field(
        default_factory=list, init=False
    )

    # Transparency
    calculation_log: List[str] = field(default_factory=list, init=False)
    warnings: List[str] = field(default_factory=list, init=False)

    # State
    is_solved: bool = field(default=False, init=False)

    # ── Logging helpers ───────────────────────────────────────────────────────

    def log(self, message: str) -> None:
        """Append a step to the calculation log."""
        self.calculation_log.append(message)

    def log_section(self, title: str) -> None:
        """Append a section header to the calculation log."""
        separator = "─" * max(4, 50 - len(title))
        self.calculation_log.append(f"\n── {title} {separator}")

    def warn(self, message: str) -> None:
        """Append a non-fatal design warning."""
        self.warnings.append(message)
        self.calculation_log.append(f"⚠  WARNING: {message}")

    # ── Stream management ─────────────────────────────────────────────────────

    def add_inlet(self, key: str, stream: ProcessStream) -> None:
        """
        Register an inlet stream under the given role key.

        Called by the user (single-unit mode) or by ProcessNetwork.solve()
        when propagating outlets from upstream units.
        """
        self.inlet_streams[key] = stream

    def get_inlet(self, key: str) -> ProcessStream:
        """
        Retrieve an inlet stream, raising StreamNotFoundError if missing.

        Use this inside solve() instead of direct dict access — it gives
        a clear, actionable error message to the user.
        """
        if key not in self.inlet_streams:
            raise StreamNotFoundError(self.unit_id, key)
        return self.inlet_streams[key]

    def get_outlet(self, key: str) -> ProcessStream:
        """
        Retrieve an outlet stream after solving.

        Called by ProcessNetwork to propagate streams to downstream units.
        """
        if not self.is_solved:
            raise UnitNotSolvedError(self.unit_id)
        if key not in self.outlet_streams:
            raise StreamNotFoundError(self.unit_id, key)
        return self.outlet_streams[key]

    # ── Energy balance verification ───────────────────────────────────────────

    def check_energy_balance(
        self,
        q_hot: float,
        q_cold: float,
        tolerance: float = 0.01
    ) -> None:
        """
        Verify |Q_hot - Q_cold| / Q_hot < tolerance.

        Call this at the end of solve() in heat transfer units.
        A failed check indicates a programming error in the equations,
        not a user input error.

        Parameters
        ----------
        q_hot  : heat lost by hot side [W]
        q_cold : heat gained by cold side [W]
        tolerance : relative tolerance (default 1%)
        """
        if q_hot == 0:
            return
        relative_error = abs(q_hot - q_cold) / abs(q_hot)
        self.log(
            f"Energy balance check: Q_hot={q_hot/1000:.3f} kW, "
            f"Q_cold={q_cold/1000:.3f} kW, "
            f"relative error={relative_error:.2e}"
        )
        if relative_error > tolerance:
            self.warn(
                f"Energy balance error {relative_error:.2%} exceeds "
                f"tolerance {tolerance:.2%}. Check equations."
            )

    # ── Reset ─────────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """
        Clear all results so the unit can be re-solved with new parameters.

        Called by ProcessNetwork when operating conditions change
        (e.g. scenario sweep).
        """
        self.outlet_streams.clear()
        self.utility_streams.clear()
        self.calculation_log.clear()
        self.warnings.clear()
        self.is_solved = False

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def solve(self) -> None:
        """
        Perform design calculations.

        Requirements
        ------------
        - Call get_inlet() to retrieve inlet streams.
        - Populate self.outlet_streams with ProcessStream objects.
        - Populate self.utility_streams with UtilityStream objects.
        - Log every intermediate step via self.log().
        - Set self.is_solved = True on successful completion.
        """
        pass

    @abstractmethod
    def summary(self) -> dict:
        """
        Return key results as a flat dict.

        Requirements
        ------------
        - All values must be JSON-serialisable (float, int, str, list, dict).
        - No ProcessStream or UtilityStream objects.
        - Include unit_id, unit_type, is_solved, and warnings.
        - Round floats to a sensible number of decimal places.
        """
        pass

    # ── Shared result helpers ─────────────────────────────────────────────────

    def base_summary(self) -> dict:
        """
        Common fields included in every unit's summary().

        Subclasses call this and merge their own fields:
            return {**self.base_summary(), "area_m2": ..., ...}
        """
        return {
            "unit_id": self.unit_id,
            "unit_type": self.unit_type,
            "is_solved": self.is_solved,
            "warnings": self.warnings,
            "inlet_streams": [
                s.to_dict() for s in self.inlet_streams.values()
            ],
            "outlet_streams": [
                s.to_dict() for s in self.outlet_streams.values()
                if isinstance(s, ProcessStream)
            ],
            "utility_streams": [
                u.to_dict() for u in self.utility_streams
            ],
        }

    def __repr__(self) -> str:
        status = "solved" if self.is_solved else "unsolved"
        return (
            f"{self.unit_type}(id='{self.unit_id}' | "
            f"inlets={list(self.inlet_streams.keys())} | "
            f"status={status})"
        )