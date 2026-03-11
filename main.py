"""
main.py
=======
Phase F: Eco-Twin Oracle — FastAPI Interoperability Layer

Exposes the full Oracle pipeline via:
  • WebSocket  /ws/live-batch/{batch_id}   — real-time streaming inference
  • REST GET   /api/v1/active-prescriptions — latest validated setpoints (Swagger)
  • REST GET   /api/v1/dfa-state            — current DFA state for any active batch
  • REST GET   /health                      — liveness probe

Bug fixes vs. original
-----------------------
FIX-1  _identify_golden_batches() used Dissolution_Rate >= 95% as the sole
       criterion. All 13 batches it selected are Grade-F USP rejects (Friability
       > 1.0%, CU out of spec). Now imports GOLDEN_BATCH_IDS directly from
       analytics_engine — the 9 batches that pass ALL hard gates AND score >= 88.

FIX-2  evaluate_batch_performance() was called with only (batch_id, avg, max) —
       quality_params=None triggered degraded energy-only mode. Now pre-loads the
       production dataset at startup and passes the full quality_params dict plus
       duration_minutes at batch_complete time.

FIX-3  Health Grade on the frontend was derived from batch_summary["normal_pct"]
       (% of ticks where LVQ said "Normal"). T060 had 99.2% Normal ticks → Grade A
       despite failing USP Friability and CU. The batch_complete payload now carries
       the authoritative quality verdict (grade, decision, composite_score,
       hard_gate_failures) from BatchQualityEvaluator so the frontend can display
       the correct grade.

FIX-4  _build_lvq_labels() thresholds were magic numbers uncalibrated to the data.
       Updated to dataset-derived values: Vib > 7.762, Power > 55.92, Temp > 61.50,
       Pressure > 1.247, Flow stagnation < 0.50 LPM when RPM > 0.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any, Optional

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from analytics_engine import (
    FEATURE_COLUMNS,
    GOLDEN_BATCH_IDS,           # FIX-1: import correct golden set, not Dissolution >= 95%
    LVQ_VIB_THRESH,             # FIX-4: calibrated LVQ thresholds from analytics_engine
    LVQ_POWER_THRESH,
    LVQ_TEMP_THRESH,
    LVQ_PRESS_THRESH,
    LVQ_FLOW_STAG,
    KohonenSOM,
    LVQClassifier,
    PhantomEnergyAlert,
    Prescription,
    _telemetry_to_vector,
    detect_phantom_energy,
    generate_prescription,
    analyze_spectral_friction,
    detect_inter_phase_arbitrage,
    generate_xai_reasoning,
    evaluate_batch_performance,
    auto_calibrate_thresholds,
)
from schemas import BatchTelemetry
from state_machine import DFAStateMachine, ManufacturingPhase
from stream_simulator import EXCEL_PATH, PHASE_STRING_TO_ENUM, stream_batch_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("eco_twin_oracle")

# Fleet-wide normalisation bounds — computed once at startup from full dataset.
# Used by BatchQualityEvaluator inside evaluate_batch_performance().
# Hardcoded here as safe constants verified against the 60-batch dataset.
FLEET_POWER_MIN: float = 19.74
FLEET_POWER_MAX: float = 26.63
FLEET_DUR_MIN: float = 193.0
FLEET_DUR_MAX: float = 284.0


# ===========================================================================
# Pydantic Response Models
# ===========================================================================

class PrescriptionResponse(BaseModel):
    batch_id: str = Field(..., description="Batch identifier, e.g. T060")
    time_minutes: int = Field(..., ge=0, description="Elapsed minutes in batch lifecycle")
    dfa_state: str = Field(..., description="Current DFA phase name")
    bmu_index: list[int] = Field(..., description="[row, col] of Best Matching Unit on SOM lattice")
    bmu_distance: float = Field(..., ge=0.0, description="Euclidean distance from live vector to BMU")
    anomaly_class: str = Field(..., description="LVQ anomaly classification label")
    parameter_recommendations: dict[str, float] = Field(..., description="DFA-validated parameter deltas")
    dfa_guardrail_passed: bool = Field(..., description="True if no parameters were blocked by DFA")
    blocked_parameters: list[str] = Field(default_factory=list)

    @classmethod
    def from_dataclass(cls, p: Prescription) -> "PrescriptionResponse":
        return cls(
            batch_id=p.batch_id,
            time_minutes=p.time_minutes,
            dfa_state=p.dfa_state,
            bmu_index=list(p.bmu_index),
            bmu_distance=p.bmu_distance,
            anomaly_class=p.anomaly_class,
            parameter_recommendations=p.parameter_recommendations,
            dfa_guardrail_passed=p.dfa_guardrail_passed,
            blocked_parameters=p.blocked_parameters,
        )


class PhantomAlertResponse(BaseModel):
    batch_id: str
    time_minutes: int
    dfa_state: str
    motor_speed_rpm: int
    power_consumption_kw: float
    message: str
    severity: str

    @classmethod
    def from_dataclass(cls, a: PhantomEnergyAlert) -> "PhantomAlertResponse":
        return cls(**asdict(a))


class DFAStateResponse(BaseModel):
    batch_id: str
    dfa_state: str
    dfa_phase_number: int
    is_terminal: bool


class HealthResponse(BaseModel):
    status: str
    som_trained: bool
    lvq_trained: bool
    uptime_seconds: float


# ===========================================================================
# Startup Training Helpers
# ===========================================================================

def _build_dummy_training_data(n_samples: int = 50) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic fallback so the server boots without the Excel file (e.g., CI)."""
    rng = np.random.default_rng(0)
    X = rng.uniform(
        low=[20, 1.0, 30, 0, 0, 0, 1.0, 0.05],
        high=[80, 5.0, 70, 300, 50, 20, 8.0, 0.5],
        size=(n_samples, len(FEATURE_COLUMNS)),
    )
    y = np.array(["Normal"] * n_samples)
    return X, y


async def _train_from_excel() -> tuple[np.ndarray, np.ndarray]:
    """
    Load telemetry from the process Excel workbook.

    SOM training data  — ONLY rows from GOLDEN_BATCH_IDS (9 batches that pass
                         ALL USP/ICH hard gates AND composite score >= 88).
                         This ensures the Golden Signature topology represents
                         truly excellent process patterns, not averages.

    LVQ training data  — ALL 60 batches so the classifier sees the full
                         spectrum of process anomaly patterns.

    FIX vs. original: removed _identify_golden_batches() which used
    Dissolution >= 95% and selected 13 Grade-F reject batches as "golden".
    """
    import os
    if not os.path.exists(EXCEL_PATH):
        logger.warning("Excel file not found at '%s'. Using dummy training data.", EXCEL_PATH)
        return _build_dummy_training_data()

    def _read_excel_sync() -> tuple[np.ndarray, np.ndarray]:
        import pandas as pd
        xl = pd.ExcelFile(EXCEL_PATH)
        golden_rows, all_rows = [], []

        for sheet in xl.sheet_names:
            try:
                df = xl.parse(sheet).sort_values("Time_Minutes")
                batch_id = str(df["Batch_ID"].iloc[0]).strip()
                is_golden = batch_id in GOLDEN_BATCH_IDS

                for _, row in df.iterrows():
                    vec = [float(row.get(col, 0.0)) for col in FEATURE_COLUMNS]
                    all_rows.append(vec)
                    if is_golden:
                        golden_rows.append(vec)

            except Exception as exc:
                logger.debug("Skipping sheet '%s': %s", sheet, exc)

        som_data = (
            np.array(golden_rows, dtype=np.float64) if golden_rows
            else np.array(all_rows, dtype=np.float64)
        )
        lvq_data = np.array(all_rows, dtype=np.float64)
        logger.info(
            "Training corpus: SOM=%d golden rows (%d batches), LVQ=%d total rows.",
            len(som_data), len(GOLDEN_BATCH_IDS), len(lvq_data),
        )
        return som_data, lvq_data

    som_X, lvq_X = await asyncio.to_thread(_read_excel_sync)
    global _lvq_training_data
    _lvq_training_data = lvq_X
    return som_X, np.array(["Normal"] * len(som_X))


# Module-level storage for LVQ training data
_lvq_training_data: np.ndarray | None = None


def _build_lvq_labels(X: np.ndarray) -> np.ndarray:
    """
    Heuristically label training data for LVQ using physical rules.

    FIX vs. original: thresholds now calibrated from actual dataset statistics
    (mean + 2*std), not arbitrary magic numbers.

    Dataset calibration (all 60 batches, ~14,500 rows):
      Vibration: mean=3.002, std=2.380  =>  anomaly threshold = 7.762 mm/s
      Power:     mean=23.14, std=16.39  =>  Mechanical Friction threshold = 55.92 kW
      Temp:      mean=35.25, std=13.12  =>  Thermal Drift threshold = 61.50 C
      Pressure:  mean=0.978, std=0.135  =>  Pressure Surge threshold = 1.247 bar
      Flow:      stagnation < 0.50 LPM when RPM > 0

    Column order (FEATURE_COLUMNS):
      [0] Temperature_C  [1] Pressure_Bar  [2] Humidity_Percent  [3] Motor_Speed_RPM
      [4] Compression_Force_kN  [5] Flow_Rate_LPM  [6] Power_Consumption_kW  [7] Vibration_mm_s
    """
    TEMP_IDX, PRESS_IDX = 0, 1
    RPM_IDX, FLOW_IDX, POWER_IDX, VIB_IDX = 3, 5, 6, 7

    labels = []
    for row in X:
        if row[VIB_IDX] > LVQ_VIB_THRESH and row[POWER_IDX] > LVQ_POWER_THRESH:
            labels.append("Mechanical Friction")
        elif row[VIB_IDX] > LVQ_VIB_THRESH:
            labels.append("Vibration Fatigue")
        elif row[TEMP_IDX] > LVQ_TEMP_THRESH:
            labels.append("Thermal Drift")
        elif row[PRESS_IDX] > LVQ_PRESS_THRESH:
            labels.append("Pressure Surge")
        elif row[RPM_IDX] > 0 and row[FLOW_IDX] < LVQ_FLOW_STAG:
            labels.append("Flow Stagnation")
        else:
            labels.append("Normal")
    return np.array(labels)


# ===========================================================================
# Production data cache — pre-loaded at startup for batch_complete lookup
# ===========================================================================

# Populated during lifespan startup. Maps batch_id to quality_params dict.
# Allows the WebSocket handler to call evaluate_batch_performance() with full
# quality data rather than falling back to degraded energy-only mode.
_production_quality_cache: dict[str, dict] = {}
_production_duration_cache: dict[str, float] = {}


def _load_production_cache() -> None:
    """
    Pre-load production data from the Excel file into memory at startup.
    Stores quality parameters and duration for each batch_id so they are
    immediately available at batch_complete time inside the WebSocket handler.
    """
    import os
    import pandas as pd
    prod_path = "_h_batch_production_data.xlsx"
    proc_path = "_h_batch_process_data.xlsx"

    if not os.path.exists(prod_path) or not os.path.exists(proc_path):
        logger.warning("Production/process data not found — quality verdict will use degraded mode.")
        return

    try:
        prod_df = pd.read_excel(prod_path, sheet_name=0)
        proc_df = pd.read_excel(proc_path, sheet_name="Summary")
        merged = prod_df.merge(proc_df, on="Batch_ID")

        quality_cols = [
            "Dissolution_Rate", "Content_Uniformity", "Disintegration_Time",
            "Hardness", "Friability", "Moisture_Content", "Tablet_Weight",
        ]
        for _, row in merged.iterrows():
            bid = str(row["Batch_ID"])
            _production_quality_cache[bid] = {
                col: float(row[col]) for col in quality_cols if col in row
            }
            _production_duration_cache[bid] = float(row["Duration_Minutes"])

        logger.info(
            "Production cache loaded: %d batches with quality params and duration.",
            len(_production_quality_cache),
        )
    except Exception as e:
        logger.warning("Failed to load production cache: %s", e)


# ===========================================================================
# FastAPI Lifespan
# ===========================================================================

_server_start_time = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  Eco-Twin Oracle — Initialising AI Engine")
    logger.info("=" * 60)

    # Calibrate thresholds from correctly-identified golden batches
    await asyncio.to_thread(auto_calibrate_thresholds)
    import analytics_engine as ae
    logger.info(
        "Thresholds calibrated: AVG=%.2f kW, PEAK=%.2f kW",
        ae.GOLDEN_AVG_POWER_THRESHOLD, ae.GOLDEN_PEAK_POWER_THRESHOLD,
    )

    # Pre-load production quality cache
    await asyncio.to_thread(_load_production_cache)
    logger.info(
        "Golden Batch IDs (from analytics_engine): %s", sorted(GOLDEN_BATCH_IDS)
    )

    # Load training data
    X_som, _ = await _train_from_excel()
    X_lvq = _lvq_training_data if _lvq_training_data is not None else X_som
    y_train = _build_lvq_labels(X_lvq)

    # Train SOM on golden batches only
    som = KohonenSOM(grid_h=10, grid_w=10, n_iterations=800, seed=42)
    t0 = time.monotonic()
    await asyncio.to_thread(som.fit, X_som)
    logger.info(
        "KohonenSOM trained in %.2fs on %d GOLDEN rows (10x10 grid).",
        time.monotonic() - t0, len(X_som),
    )

    # Train LVQ on all batches
    label_counts = {lbl: int(np.sum(y_train == lbl)) for lbl in np.unique(y_train)}
    logger.info("LVQ label distribution: %s", label_counts)
    lvq = LVQClassifier(n_prototypes_per_class=3, learning_rate=0.05, n_epochs=400, seed=42)
    t0 = time.monotonic()
    await asyncio.to_thread(lvq.fit, X_lvq, y_train)
    logger.info(
        "LVQClassifier trained in %.2fs on %d rows. Classes: %s",
        time.monotonic() - t0, len(X_lvq), list(np.unique(y_train)),
    )

    # Attach to app state
    app.state.som = som
    app.state.lvq = lvq
    app.state.active_prescriptions = {}
    app.state.active_dfa_states = {}

    logger.info("Oracle engine ready. Swagger UI: http://localhost:8000/docs")
    logger.info("=" * 60)

    yield

    logger.info("Eco-Twin Oracle shutting down gracefully.")


# ===========================================================================
# FastAPI Application
# ===========================================================================

app = FastAPI(
    title="Eco-Twin Oracle API",
    description=(
        "**Prescriptive Manufacturing Intelligence** — AVEVA Hackathon Track B.\n\n"
        "Real-time batch process optimisation powered by:\n"
        "- Kohonen Self-Organising Maps for Golden Signature topology\n"
        "- Learning Vector Quantisation for anomaly classification\n"
        "- Deterministic Finite Automaton (DFA) as mathematical guardrail\n"
        "- Phantom Energy Detection for idle-phase waste identification\n"
        "- USP/ICH-compliant BatchQualityEvaluator for Accept/Reject decisions\n\n"
        "Stream live telemetry via WebSocket `/ws/live-batch/{batch_id}` or query "
        "the latest optimal setpoints via the REST endpoints below."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# REST Endpoints
# ===========================================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        som_trained=app.state.som.is_trained,
        lvq_trained=app.state.lvq.is_trained,
        uptime_seconds=round(time.monotonic() - _server_start_time, 2),
    )


@app.get(
    "/api/v1/active-prescriptions",
    response_model=list[PrescriptionResponse],
    tags=["Optimization Engine"],
    summary="Get latest optimal machine setpoints for all active batches",
)
async def get_active_prescriptions() -> list[PrescriptionResponse]:
    return list(app.state.active_prescriptions.values())


@app.get(
    "/api/v1/dfa-state/{batch_id}",
    response_model=DFAStateResponse,
    tags=["DFA State Machine"],
    summary="Query the current DFA phase for a streaming batch",
)
async def get_dfa_state(batch_id: str) -> DFAStateResponse:
    from fastapi import HTTPException
    state = app.state.active_dfa_states.get(batch_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Batch '{batch_id}' is not currently active.",
        )
    return state


@app.get(
    "/api/v1/phases",
    response_model=list[dict],
    tags=["DFA State Machine"],
    summary="List all 8 manufacturing phases in DFA transition order",
)
async def get_phases() -> list[dict]:
    return [
        {
            "phase_number": phase.value,
            "phase_name": phase.name,
            "csv_label": csv_key,
            "is_terminal": phase == ManufacturingPhase.QUALITY_TESTING,
        }
        for csv_key, phase in PHASE_STRING_TO_ENUM.items()
    ]


# ===========================================================================
# WebSocket — Real-Time Streaming Pipeline
# ===========================================================================

@app.websocket("/ws/live-batch/{batch_id}")
async def websocket_live_batch(websocket: WebSocket, batch_id: str):
    """
    WebSocket endpoint for real-time batch telemetry streaming.

    batch_complete payload carries the authoritative quality verdict:
      ledger_status.grade          — A / B / C / D / F
      ledger_status.decision       — ACCEPT_EXCELLENT / ACCEPT_GOOD / CONDITIONAL / REVIEW / REJECT
      ledger_status.composite_score
      ledger_status.hard_gate_failures  — list of specific USP spec breaches
      ledger_status.hard_gate_passed
    """
    await websocket.accept()
    logger.info("[WS] Client connected for batch '%s'.", batch_id)

    som: KohonenSOM = app.state.som
    lvq: LVQClassifier = app.state.lvq
    dfa = DFAStateMachine()

    power_history: list[float] = []
    bmu_distances: list[float] = []
    anomaly_classes: list[str] = []
    total_phantom = 0
    total_pvr = 0
    total_arbitrage = 0

    try:
        async for telemetry, current_phase, quality_margin in stream_batch_data(batch_id, tick_delay=0.0):
            power_history.append(telemetry.Power_Consumption_kW)

            pvr_alert = analyze_spectral_friction(telemetry)
            arbitrage_alert = detect_inter_phase_arbitrage(telemetry, current_phase)
            phantom_alert: Optional[PhantomEnergyAlert] = detect_phantom_energy(telemetry, current_phase)

            prescription: Prescription = generate_prescription(
                telemetry, current_phase, som, lvq, dfa, quality_margin
            )
            prescription_resp = PrescriptionResponse.from_dataclass(prescription)
            xai_data = generate_xai_reasoning(telemetry, prescription.anomaly_class, current_phase)

            app.state.active_prescriptions[batch_id] = prescription_resp
            app.state.active_dfa_states[batch_id] = DFAStateResponse(
                batch_id=batch_id,
                dfa_state=current_phase.name,
                dfa_phase_number=current_phase.value,
                is_terminal=(current_phase == ManufacturingPhase.QUALITY_TESTING),
            )

            has_anomaly = prescription.anomaly_class != "Normal"
            has_phantom = phantom_alert is not None
            has_pvr = pvr_alert is not None
            has_arbitrage = arbitrage_alert is not None

            bmu_distances.append(prescription.bmu_distance)
            anomaly_classes.append(prescription.anomaly_class)
            if has_phantom: total_phantom += 1
            if has_pvr: total_pvr += 1
            if has_arbitrage: total_arbitrage += 1

            if has_phantom:
                event_type = "phantom_energy"
            elif has_anomaly:
                event_type = "anomaly_detected"
            elif has_pvr or has_arbitrage:
                event_type = "process_alert"
            else:
                event_type = "telemetry"

            payload = {
                "event": event_type,
                "telemetry": telemetry.model_dump(),
                "dfa_state": current_phase.name,
                "prescription": prescription_resp.model_dump(),
                "phantom_alert": (
                    PhantomAlertResponse.from_dataclass(phantom_alert).model_dump()
                    if phantom_alert else None
                ),
                "pvr_alert": pvr_alert,
                "arbitrage_alert": arbitrage_alert,
                "xai_data": xai_data,
                "quality_margin": quality_margin,
                "has_anomaly": has_anomaly,
                "has_phantom": has_phantom,
                "has_pvr_alert": has_pvr,
                "has_arbitrage_alert": has_arbitrage,
                "timestamp_ms": int(time.time() * 1000),
            }

            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(1.5)

        # batch_complete: compute authoritative quality verdict
        avg_batch_power = sum(power_history) / len(power_history) if power_history else 0.0
        max_batch_power = max(power_history) if power_history else 0.0

        # FIX-2 + FIX-3: look up full quality params from the pre-loaded cache
        # and pass them to evaluate_batch_performance() so it uses
        # BatchQualityEvaluator (hard gates + quality score), not energy-only mode.
        quality_params = _production_quality_cache.get(batch_id)
        duration_minutes = _production_duration_cache.get(batch_id)

        import analytics_engine as ae
        ledger_result = evaluate_batch_performance(
            batch_id=batch_id,
            avg_power=avg_batch_power,
            max_power=max_batch_power,
            quality_params=quality_params,
            duration_minutes=duration_minutes,
            fleet_power_min=FLEET_POWER_MIN,
            fleet_power_max=FLEET_POWER_MAX,
            fleet_dur_min=FLEET_DUR_MIN,
            fleet_dur_max=FLEET_DUR_MAX,
        )

        # Anomaly summary
        anomaly_count = sum(1 for c in anomaly_classes if c != "Normal")
        class_counts: dict[str, int] = {}
        for c in anomaly_classes:
            class_counts[c] = class_counts.get(c, 0) + 1
        non_normal = {k: v for k, v in class_counts.items() if k != "Normal"}
        dominant_anomaly = max(non_normal, key=non_normal.get) if non_normal else "Normal"

        avg_bmu = float(np.mean(bmu_distances)) if bmu_distances else 0.0
        max_bmu = float(np.max(bmu_distances)) if bmu_distances else 0.0
        normal_pct = round(class_counts.get("Normal", 0) / len(anomaly_classes) * 100, 1) if anomaly_classes else 0.0

        batch_summary = {
            "total_rows": len(power_history),
            "total_alerts": anomaly_count + total_phantom + total_pvr + total_arbitrage,
            "anomaly_detections": anomaly_count,
            "phantom_alerts": total_phantom,
            "pvr_alerts": total_pvr,
            "arbitrage_alerts": total_arbitrage,
            "dominant_anomaly": dominant_anomaly,
            "anomaly_class_counts": class_counts,
            "avg_bmu_distance": round(avg_bmu, 4),
            "max_bmu_distance": round(max_bmu, 4),
            # process_stability_pct measures how often LVQ said "Normal" during streaming
            # This is NOT the quality grade — it's process telemetry similarity to golden
            "process_stability_pct": normal_pct,
            # FIX-3: authoritative quality fields for frontend grade display
            "quality_grade": ledger_result.get("grade", "?"),
            "quality_decision": ledger_result.get("decision", "UNKNOWN"),
            "quality_composite": ledger_result.get("composite_score", 0.0),
            "quality_score": ledger_result.get("quality_score", 0.0),
            "efficiency_score": ledger_result.get("efficiency_score", 0.0),
            "hard_gate_passed": ledger_result.get("hard_gate_passed", False),
            "hard_gate_failures": ledger_result.get("hard_gate_failures", []),
            "primary_failure": ledger_result.get("primary_failure", "None"),
            "per_param_scores": ledger_result.get("per_param_scores", {}),
            "avg_power_kW": round(avg_batch_power, 2),
            "peak_power_kW": round(max_batch_power, 2),
        }

        await websocket.send_json({
            "event": "batch_complete",
            "ledger_status": ledger_result,
            "batch_summary": batch_summary,
        })

        logger.info(
            "[WS] Batch '%s' complete | Grade=%s | Decision=%s | Composite=%.2f | "
            "HardGate=%s | SOM_retraining=%s",
            batch_id,
            ledger_result.get("grade", "?"),
            ledger_result.get("decision", "UNKNOWN"),
            ledger_result.get("composite_score", 0.0),
            "PASS" if ledger_result.get("hard_gate_passed") else "FAIL",
            ledger_result.get("trigger_som_retraining"),
        )

    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected from batch '%s'.", batch_id)

    except FileNotFoundError as exc:
        await websocket.send_text(json.dumps({
            "event": "error",
            "detail": str(exc),
            "timestamp_ms": int(time.time() * 1000),
        }))
        logger.error("[WS] Batch '%s' not found: %s", batch_id, exc)

    except Exception as exc:
        logger.exception("[WS] Unhandled error for batch '%s': %s", batch_id, exc)
        try:
            await websocket.send_text(json.dumps({
                "event": "error",
                "detail": f"Internal Oracle error: {type(exc).__name__}: {exc}",
                "timestamp_ms": int(time.time() * 1000),
            }))
        except Exception:
            pass

    finally:
        app.state.active_prescriptions.pop(batch_id, None)
        app.state.active_dfa_states.pop(batch_id, None)


# ===========================================================================
# Dev server entry point
# ===========================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
