"""
stream_simulator.py
===================
Phase C: Chronological Data Stream Pipeline

Implements an async generator that reads a per-batch sheet from the process
Excel workbook and yields validated BatchTelemetry objects in strict
Time_Minutes order, keeping a DFAStateMachine in perfect sync with the
physical simulation as it runs.

Jackson Structured Design hierarchy
────────────────────────────────────
stream_batch_data (process body)
 ├── _load_and_sort_sheet     (input component)
 ├── _validate_row            (transform component)
 └── _sync_dfa_state          (output / state component)
"""

import asyncio
import logging
import pandas as pd
from typing import AsyncGenerator

from schemas import BatchTelemetry
from state_machine import DFAStateMachine, ManufacturingPhase, PhysicalViolationError

logger = logging.getLogger(__name__)

"""
Regulatory Baseline Config:
According to United States Pharmacopeia (USP) guidelines for immediate-release solid dosage forms, the baseline acceptance criteria (Q) is 80% - 85% dissolution.
We establish 85.0% as our strict quality floor. Any dissolution rate > 85.0% is treated as a harvestable quality buffer for carbon reduction.
"""
USP_ACCEPTANCE_CRITERIA_Q = 85.0

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXCEL_PATH = "_h_batch_process_data.xlsx"

# Maps the Phase string from CSV to its ManufacturingPhase enum value.
# Centralised here so a possible rename in future only needs one edit.
PHASE_STRING_TO_ENUM: dict[str, ManufacturingPhase] = {
    "Preparation":    ManufacturingPhase.PREPARATION,
    "Granulation":    ManufacturingPhase.GRANULATION,
    "Drying":         ManufacturingPhase.DRYING,
    "Milling":        ManufacturingPhase.MILLING,
    "Blending":       ManufacturingPhase.BLENDING,
    "Compression":    ManufacturingPhase.COMPRESSION,
    "Coating":        ManufacturingPhase.COATING,
    "Quality_Testing": ManufacturingPhase.QUALITY_TESTING,
}

# Simulated real-time tick delay between rows (seconds).
# Set to 0 for pure batch replay; raise for live-loop feel.
TICK_DELAY_SECONDS: float = 0.0


# ---------------------------------------------------------------------------
# JSD Input Component
# ---------------------------------------------------------------------------

def _load_and_sort_sheet(batch_id: str) -> pd.DataFrame:
    """
    Load the per-batch sheet for *batch_id* and return rows sorted
    strictly ascending by Time_Minutes (physical chronological order).
    """
    sheet_name = f"Batch_{batch_id}"
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
    except ValueError:
        raise FileNotFoundError(
            f"No sheet named '{sheet_name}' found in {EXCEL_PATH}. "
            f"Check that batch_id '{batch_id}' is valid."
        )
    if "Time_Minutes" not in df.columns:
        raise KeyError(f"Sheet '{sheet_name}' is missing the 'Time_Minutes' column.")
    
    # Sort ensures JSD chronological guarantee even if raw data is unordered.
    df = df.sort_values("Time_Minutes", ascending=True).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# JSD Transform Component
# ---------------------------------------------------------------------------

def _validate_row(row: pd.Series) -> BatchTelemetry:
    """
    Coerce a raw DataFrame row into a validated BatchTelemetry Pydantic model.
    Pydantic Field constraints (ge/le) act as the physics gate here.
    """
    return BatchTelemetry(
        Batch_ID=str(row["Batch_ID"]),
        Time_Minutes=int(row["Time_Minutes"]),
        Phase=str(row["Phase"]).strip(),
        Temperature_C=float(row["Temperature_C"]),
        Pressure_Bar=float(row["Pressure_Bar"]),
        Humidity_Percent=float(row["Humidity_Percent"]),
        Motor_Speed_RPM=int(row["Motor_Speed_RPM"]),
        Compression_Force_kN=int(row["Compression_Force_kN"]),
        Flow_Rate_LPM=int(row["Flow_Rate_LPM"]),
        Power_Consumption_kW=float(row["Power_Consumption_kW"]),
        Vibration_mm_s=max(0.0, float(row["Vibration_mm_s"])),
    )


# ---------------------------------------------------------------------------
# JSD State Component
# ---------------------------------------------------------------------------

def _sync_dfa_state(
    dfa: DFAStateMachine,
    telemetry: BatchTelemetry,
) -> ManufacturingPhase:
    """
    Compare the telemetry's Phase string against the DFA's current state.
    If the physical process has advanced to the next phase, trigger a
    DFA transition to keep the automaton perfectly synchronised.

    Returns the (possibly updated) current DFA state after sync.
    """
    csv_phase = PHASE_STRING_TO_ENUM.get(telemetry.Phase)
    if csv_phase is None:
        raise ValueError(
            f"Unknown phase '{telemetry.Phase}' in CSV row "
            f"(Batch={telemetry.Batch_ID}, t={telemetry.Time_Minutes} min). "
            f"Valid phases: {list(PHASE_STRING_TO_ENUM.keys())}"
        )

    # Phase has advanced in the physical data → trigger formal DFA transition.
    if csv_phase != dfa.current_state:
        try:
            dfa.transition_to(csv_phase)
        except PhysicalViolationError as exc:
            # Re-raise with richer context for debugging.
            raise PhysicalViolationError(
                f"[DFA Sync Error] at t={telemetry.Time_Minutes} min "
                f"for Batch {telemetry.Batch_ID}: {exc}"
            ) from exc

    return dfa.current_state


# ---------------------------------------------------------------------------
# JSD Process Body: Public Async Generator
# ---------------------------------------------------------------------------

async def stream_batch_data(
    batch_id: str,
    tick_delay: float = TICK_DELAY_SECONDS,
    stride: int = 1,
) -> AsyncGenerator[tuple[BatchTelemetry, ManufacturingPhase, float], None]:
    """
    Async generator (Jackson Structured Design process body) that:

    1. Loads and chronologically sorts the per-batch telemetry sheet.
    2. Initialises a fresh DFAStateMachine for this batch lifecycle.
    3. Yields (BatchTelemetry, current_dfa_state) tuples row-by-row.
    4. Synchronises the DFA state machine to the CSV's Phase column on every
       phase boundary, guaranteeing the automaton mirrors the physical machine.

    Usage
    -----
    async for telemetry, dfa_state in stream_batch_data("T060"):
        print(telemetry.Time_Minutes, dfa_state.name, telemetry.Power_Consumption_kW)
    """
    # ── Input ───────────────────────────────────────────────────────────────
    df = _load_and_sort_sheet(batch_id)
    dfa = DFAStateMachine()

    # ── Lookup Quality Margin from Production Data ────────────────────────
    try:
        prod_df = pd.read_excel("_h_batch_production_data.xlsx", sheet_name="BatchData")
        batch_row = prod_df[prod_df["Batch_ID"] == batch_id]
        if not batch_row.empty:
            dissolution_rate = float(batch_row.iloc[0]["Dissolution_Rate"])
        else:
            dissolution_rate = USP_ACCEPTANCE_CRITERIA_Q
    except Exception as e:
        print(f"[StreamSimulator] Warning: Could not read production data: {e}")
        dissolution_rate = USP_ACCEPTANCE_CRITERIA_Q
    
    quality_margin = dissolution_rate - USP_ACCEPTANCE_CRITERIA_Q
    logger.info(f"Loaded USP Baseline: {USP_ACCEPTANCE_CRITERIA_Q}%. Active Margin: {quality_margin}%")

    print(
        f"[StreamSimulator] Starting batch '{batch_id}' | "
        f"{len(df)} rows | "
        f"DFA initialised at state: {dfa.current_state.name} | "
        f"Quality Margin: {quality_margin:.2f}"
    )

    # ── Process ─────────────────────────────────────────────────────────────
    for idx, (_, row) in enumerate(df.iterrows()):
        # Transform: validate raw row through Pydantic physics constraints
        telemetry = _validate_row(row)

        # State: always sync DFA regardless of stride so phase transitions
        # are never missed and the automaton stays perfectly in step.
        current_phase = _sync_dfa_state(dfa, telemetry)

        # Only yield every stride-th row — skipped rows still advanced the
        # DFA above, so all phase boundaries remain correct.
        if idx % stride != 0:
            continue

        yield telemetry, current_phase, quality_margin

        # Simulated real-time tick (non-blocking)
        if tick_delay > 0:
            await asyncio.sleep(tick_delay)

    print(
        f"[StreamSimulator] Batch '{batch_id}' complete. "
        f"Final DFA state: {dfa.current_state.name}"
    )


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    async def _smoke_test():
        count = 0
        async for telemetry, phase, q_margin in stream_batch_data("T001"):
            if count < 5 or telemetry.Phase != (list(PHASE_STRING_TO_ENUM.keys())[count // 10]):
                print(
                    f"  t={telemetry.Time_Minutes:>4} min | "
                    f"DFA={phase.name:<16} | "
                    f"CSV={telemetry.Phase:<16} | "
                    f"RPM={telemetry.Motor_Speed_RPM:>5} | "
                    f"kW={telemetry.Power_Consumption_kW:.3f}"
                )
            count += 1
        print(f"  Total rows processed: {count}")

    asyncio.run(_smoke_test())
