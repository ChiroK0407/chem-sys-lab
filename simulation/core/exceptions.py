"""
simulation/core/exceptions.py

Custom exception hierarchy for the ChE simulation platform.
All simulation errors inherit from SimulationError so callers
can catch the whole family with a single except clause.
"""


class SimulationError(Exception):
    """Base class for all simulation exceptions."""
    pass


# ── Stream errors ─────────────────────────────────────────────────────────────

class StreamError(SimulationError):
    """Raised when a stream has invalid or inconsistent state."""
    pass


class StreamNotFoundError(StreamError):
    """Raised when a required inlet/outlet stream key is missing."""
    def __init__(self, unit_id: str, key: str):
        super().__init__(
            f"Unit '{unit_id}': stream key '{key}' not found. "
            f"Did you forget to call add_inlet('{key}', stream)?"
        )
        self.unit_id = unit_id
        self.key = key


class PhaseError(StreamError):
    """
    Raised when an operation is invalid for the stream's phase.
    Example: applying sensible-heat-only LMTD to a condensing stream.
    """
    def __init__(self, unit_id: str, phase: str, message: str):
        super().__init__(
            f"Unit '{unit_id}': phase '{phase}' — {message}"
        )
        self.unit_id = unit_id
        self.phase = phase


# ── Unit operation errors ─────────────────────────────────────────────────────

class UnitNotSolvedError(SimulationError):
    """Raised when get_outlet() is called before solve()."""
    def __init__(self, unit_id: str):
        super().__init__(
            f"Unit '{unit_id}' has not been solved yet. Call solve() first."
        )
        self.unit_id = unit_id


class InfeasibleDesignError(SimulationError):
    """
    Raised when the design specification is physically impossible.
    Examples:
      - Cold stream outlet T > hot stream inlet T (temperature cross)
      - Required area is negative (energy balance violated)
      - NPSH available < NPSH required
    """
    def __init__(self, unit_id: str, message: str):
        super().__init__(f"Unit '{unit_id}': infeasible design — {message}")
        self.unit_id = unit_id


class ConvergenceError(SimulationError):
    """
    Raised when an iterative solver fails to converge.
    Relevant for: flash drum (Rachford-Rice), recycle tear streams.
    """
    def __init__(self, unit_id: str, iterations: int, residual: float):
        super().__init__(
            f"Unit '{unit_id}': solver did not converge after {iterations} "
            f"iterations. Final residual = {residual:.3e}. "
            f"Check feed conditions and initial guess."
        )
        self.unit_id = unit_id
        self.iterations = iterations
        self.residual = residual


# ── Network errors ────────────────────────────────────────────────────────────

class NetworkError(SimulationError):
    """Base class for process network errors."""
    pass


class CycleDetectedError(NetworkError):
    """
    Raised when topological sort detects a cycle (recycle loop).
    The sequential-modular solver cannot handle cycles without
    a tear-stream strategy.
    """
    def __init__(self, cycle_hint: str = ""):
        msg = (
            "Cycle detected in process network. "
            "Recycle streams require a tear-stream solver (not yet implemented). "
        )
        if cycle_hint:
            msg += f"Hint: {cycle_hint}"
        super().__init__(msg)


class DisconnectedNetworkError(NetworkError):
    """Raised when a unit has no inlet streams and is not a feed unit."""
    def __init__(self, unit_id: str):
        super().__init__(
            f"Unit '{unit_id}' has no inlet streams and is not marked as a "
            f"feed unit. Did you forget a connect() call?"
        )
        self.unit_id = unit_id


# ── Thermodynamic errors ──────────────────────────────────────────────────────

class ThermodynamicError(SimulationError):
    """Raised when a thermodynamic calculation is out of valid range."""
    def __init__(self, correlation: str, variable: str, value: float, valid_range: tuple):
        super().__init__(
            f"Correlation '{correlation}': {variable} = {value:.4g} is outside "
            f"valid range [{valid_range[0]:.4g}, {valid_range[1]:.4g}]."
        )
        self.correlation = correlation
        self.variable = variable
        self.value = value
        self.valid_range = valid_range

# ── HC Recovery errors ────────────────────────────────────────────────────────

class HCRecoveryError(SimulationError):
    """Base class for all HC recovery simulation errors."""
    
    def __init__(self, message: str, detail: dict[str, any] | None = None) -> None:
        super().__init__(message)
        self.detail: dict[str, any] = detail or {}

    def __str__(self) -> str:
        base_message = super().__str__()
        if self.detail:
            return f"{base_message} | Context Details: {self.detail}"
        return base_message


class FeedValidationError(HCRecoveryError):
    """
    Raised when feed stream inputs are invalid.

    Examples:
      - Stream compositions don't sum to 100% (or mole fraction 1.0)
      - Negative operating pressure
      - Operating temperature outside valid thermodynamic limits
    """
    pass


class DataLoadError(HCRecoveryError):
    """
    Raised when component constants JSON or adsorbent/membrane parameter
    files are missing, unreadable, or structurally malformed.
    """
    pass


class OutOfRangeError(HCRecoveryError):
    """
    Raised when a numerical input falls outside model validity bounds.

    Example:
      - Operating temperature falls below the dew point range
      - System pressure exceeds structural membrane operating limits
    """
    
    def __init__(
        self, 
        parameter: str, 
        value: float, 
        valid_min: float, 
        valid_max: float, 
        unit: str = ""
    ) -> None:
        unit_str = f" {unit}".rstrip()
        message = (
            f"'{parameter}' = {value}{unit_str} is outside valid model "
            f"operational range [{valid_min}, {valid_max}]{unit_str}."
        )
        super().__init__(message, detail={
            "parameter": parameter,
            "value": value,
            "valid_min": valid_min,
            "valid_max": valid_max,
            "unit": unit
        })
        self.parameter = parameter
        self.value = value
        self.valid_min = valid_min
        self.valid_max = valid_max
        self.unit = unit