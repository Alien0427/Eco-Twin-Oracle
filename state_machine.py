from enum import IntEnum
from typing import Dict

class PhysicalViolationError(Exception):
    """Exception raised for logically/physically impossible parameter tuning across DFA states."""
    pass

class ManufacturingPhase(IntEnum):
    PREPARATION = 1
    GRANULATION = 2
    DRYING = 3
    MILLING = 4
    BLENDING = 5
    COMPRESSION = 6
    COATING = 7
    QUALITY_TESTING = 8

class DFAStateMachine:
    def __init__(self):
        self.current_state = ManufacturingPhase.PREPARATION
        
        # Define strict, unidirectional forward transitions.
        # Format: {Current_State: Next_Valid_State | None (terminal)}
        self._valid_transitions: Dict[ManufacturingPhase, ManufacturingPhase | None] = {
            ManufacturingPhase.PREPARATION: ManufacturingPhase.GRANULATION,
            ManufacturingPhase.GRANULATION: ManufacturingPhase.DRYING,
            ManufacturingPhase.DRYING: ManufacturingPhase.MILLING,
            ManufacturingPhase.MILLING: ManufacturingPhase.BLENDING,
            ManufacturingPhase.BLENDING: ManufacturingPhase.COMPRESSION,
            ManufacturingPhase.COMPRESSION: ManufacturingPhase.COATING,
            ManufacturingPhase.COATING: ManufacturingPhase.QUALITY_TESTING,
            ManufacturingPhase.QUALITY_TESTING: None  # Terminal state
        }
        
        # Mapping parameters specifically locked out based on the phase.
        # For simplicity in this engine, we lock parameters inherently tied to PAST phases
        # or specific machines that are no longer active in the physical process.
        # This mapping links the phase when the parameter was relevant.
        self._parameter_phase_mapping = {
            "Binder_Amount": ManufacturingPhase.GRANULATION,
            "Granulation_Time": ManufacturingPhase.GRANULATION,
            "Drying_Temp": ManufacturingPhase.DRYING,
            "Drying_Time": ManufacturingPhase.DRYING,
            "Compression_Force": ManufacturingPhase.COMPRESSION,
            "Machine_Speed": ManufacturingPhase.COMPRESSION,
            # Continuous telemetry specific metrics
            # E.g., You can't change early phase motor speed when you are in Coating
            "Motor_Speed_RPM": None, # Complex: depends on exact phase interpretation, but let's assume it's dynamic per phase.
        }

    def transition_to(self, target_state: ManufacturingPhase) -> bool:
        """Attempt to transition to a new physical state in the DFA."""
        valid_next = self._valid_transitions.get(self.current_state)
        if valid_next == target_state:
            self.current_state = target_state
            return True
        else:
            raise PhysicalViolationError(
                f"Invalid physical transition from {self.current_state.name} to {target_state.name}. "
                f"Expected {valid_next.name if valid_next else 'None (Terminal)'}"
            )

    def validate_prescription(self, current_state: ManufacturingPhase, parameter_to_change: str):
        """
        DFA mathematical guardrail against AI hallucination.
        Prevents AI from suggesting changes to parameters associated with states 
        that have already passed chronologically.
        """
        # Check if the parameter specifically belongs to a known historical phase
        param_native_phase = self._parameter_phase_mapping.get(parameter_to_change)
        
        if param_native_phase:
            # IntEnum members are int subclasses — direct > comparison is type-safe.
            if current_state > param_native_phase:
                raise PhysicalViolationError(
                    f"[Guardrail Block] AI Hallucination detected. "
                    f"AI attempted to optimize '{parameter_to_change}' "
                    f"(native to {param_native_phase.name}) while physical machine is in state {current_state.name}. "
                    f"Retrospective physical changes are impossible."
                )
        
        # If it passes checks, or is a globally dynamic parameter, it is physically valid
        return True
