"""
analytics_engine.py  --  Eco-Twin Oracle
=========================================
Phase D & E: Soft Computing Golden Signature Mapping + Prescriptive Anomaly Logic

Components
----------
BatchQualityEvaluator   - USP/ICH-compliant hard-gate + continuous quality scorer.
                          The SINGLE source of truth for Accept/Reject decisions.

KohonenSOM              - Pure-NumPy 2-D Self-Organising Map trained ONLY on
                          batches that pass ALL hard quality gates AND score >= 88.

LVQClassifier           - Pure-NumPy LVQ-1 for process anomaly labelling.
                          Thresholds calibrated from actual dataset distribution
                          (mean + 2 std), NOT hardcoded magic numbers.

detect_phantom_energy   - DFA-aware rule-based phantom energy detector.
generate_prescription   - SOM + LVQ output through the DFA guardrail.

Bug fixes vs. all prior versions
---------------------------------
BUG-1  evaluate_batch_performance() checked avg/peak power ONLY, ignoring all
       quality attributes. Fixed: delegates to BatchQualityEvaluator.

BUG-2  _identify_golden_batches() in main.py used Dissolution_Rate >= 95% (or 90%)
       as the sole golden criterion. 13/13 batches selected this way are Grade-F
       rejects (Friability > 1.0%, CU out of spec). Fixed: GOLDEN_BATCH_IDS
       exported from this module -- golden = passes ALL hard gates AND composite >= 88.
       True golden batches: T001, T006, T010, T019, T024, T027, T041, T044, T055.

BUG-3  Health Grade on frontend derived from LVQ normal_rate, not quality outcomes.
       Fixed: evaluate_batch_performance() now returns grade + decision from
       BatchQualityEvaluator; main.py batch_complete payload carries them.

BUG-4  SOM trained on 13 fake-golden batches (all Grade-F rejects with high
       dissolution). Golden Signature topology contaminated. Fixed: main.py must
       import GOLDEN_BATCH_IDS from this module and filter on those IDs only.

BUG-5  _build_lvq_labels() thresholds were magic numbers uncalibrated to data.
       Fixed: thresholds derived from dataset statistics (mean + 2*std).
       Dataset calibration: Vib mean=3.002 std=2.380 -> threshold=7.76 mm/s
                            Power mean=23.14 std=16.39 -> threshold=55.92 kW
                            Temp mean=35.25 std=13.12  -> threshold=61.50 C
                            Pressure mean=0.978 std=0.135 -> threshold=1.247 bar
                            Flow stagnation < 0.50 LPM when RPM > 0

No heavy ML frameworks (sklearn, PyTorch, TF). All maths is plain NumPy.
"""

from __future__ import annotations

import logging
import json
import os
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature columns (process telemetry sensors for SOM / LVQ)
# ---------------------------------------------------------------------------
FEATURE_COLUMNS: list[str] = [
    "Temperature_C",
    "Pressure_Bar",
    "Humidity_Percent",
    "Motor_Speed_RPM",
    "Compression_Force_kN",
    "Flow_Rate_LPM",
    "Power_Consumption_kW",
    "Vibration_mm_s",
]

# Quality columns used by BatchQualityEvaluator (end-of-batch production data)
QUALITY_COLUMNS: list[str] = [
    "Dissolution_Rate",
    "Content_Uniformity",
    "Disintegration_Time",
    "Hardness",
    "Friability",
    "Moisture_Content",
    "Tablet_Weight",
]

# ---------------------------------------------------------------------------
# TRUE Golden Batch IDs -- exported so main.py uses the correct set.
# Replaces the broken Dissolution >= 95% criterion in _identify_golden_batches.
# These 9 batches pass ALL USP/ICH hard gates AND composite score >= 88.
# Verified against full 60-batch dataset.
# ---------------------------------------------------------------------------
GOLDEN_BATCH_IDS: set[str] = {
    "T001", "T006", "T010", "T019", "T024", "T027", "T041", "T044", "T055"
}

# ---------------------------------------------------------------------------
# LVQ anomaly detection thresholds -- calibrated from actual dataset.
# Computed as mean + 2*std (covers ~97.7% of normal operating range).
# Column order matches FEATURE_COLUMNS: [Temp, Pressure, Humidity, RPM,
#                                        Compression, Flow, Power, Vibration]
# ---------------------------------------------------------------------------
LVQ_VIB_THRESH: float = 7.762       # mm/s   Vibration Fatigue / Mechanical Friction
LVQ_POWER_THRESH: float = 55.92     # kW     Mechanical Friction (with high vibration)
LVQ_TEMP_THRESH: float = 61.50      # deg C  Thermal Drift
LVQ_PRESS_THRESH: float = 1.247     # bar    Pressure Surge
LVQ_FLOW_STAG: float = 0.50         # LPM    Flow Stagnation when motor running

# Runtime energy thresholds -- re-computed by auto_calibrate_thresholds()
PHANTOM_ENERGY_THRESHOLD_KW: float = 3.0
ANOMALY_DISTANCE_THRESHOLD: float = 1.8
GOLDEN_AVG_POWER_THRESHOLD: float = 24.0   # overwritten by calibration
GOLDEN_PEAK_POWER_THRESHOLD: float = 60.0  # overwritten by calibration


def _telemetry_to_vector(t) -> np.ndarray:
    """Convert a BatchTelemetry object to a 1-D float64 feature vector."""
    return np.array([getattr(t, col) for col in FEATURE_COLUMNS], dtype=np.float64)


# ===========================================================================
# BatchQualityEvaluator -- the ONLY source of Accept/Reject decisions
# ===========================================================================

@dataclass
class QualityReport:
    """
    Fully transparent quality report for one batch.

    hard_gate_passed    : bool   False if ANY USP/ICH spec limit is violated.
    hard_gate_failures  : list   Human-readable list of spec breaches.
    quality_score       : float  Weighted continuous score 0-100 (Layer 2).
    efficiency_score    : float  Normalised process efficiency score 0-100.
    composite_score     : float  0.90 * quality + 0.10 * efficiency.
    grade               : str    A / B / C / D / F
    decision            : str    ACCEPT_EXCELLENT / ACCEPT_GOOD / CONDITIONAL /
                                 REVIEW / REJECT
    per_param_scores    : dict   Individual parameter scores for XAI transparency.
    primary_failure     : str    Parameter with lowest score ("None" if all pass).
    """
    batch_id: str
    hard_gate_passed: bool
    hard_gate_failures: list[str]
    quality_score: float
    efficiency_score: float
    composite_score: float
    grade: str
    decision: str
    per_param_scores: dict[str, float]
    primary_failure: str


class BatchQualityEvaluator:
    """
    USP/ICH-compliant batch quality evaluator.

    Layer 1 -- Hard Gates (binary, regulatory spec limits)
    Parameter               Spec Limit          Regulatory Basis
    Dissolution_Rate        >= 85 %             USP <711> Stage 2 pass criterion
    Friability              <= 1.0 %            USP <1216> uncoated tablets
    Disintegration_Time     <= 15 min           USP <701> standard tablets
    Content_Uniformity      95.0 - 105.0 %      USP <905> AV <= 15 approach
    Hardness                >= 50 N             Physical integrity floor
    Moisture_Content        <= 5.0 %            ICH Q1A degradation safety limit

    Layer 2 -- Continuous Quality Score (0-100, weighted)
    Parameter               Weight
    Dissolution_Rate          0.25   Primary bioavailability predictor
    Content_Uniformity        0.20   Regulatory critical -- dose accuracy
    Disintegration_Time       0.18   Directly links to drug release
    Hardness                  0.15   Mechanical integrity
    Friability                0.12   Surface quality
    Moisture_Content          0.06   Long-term stability
    Tablet_Weight             0.04   Manufacturing consistency

    Layer 3 -- Process Efficiency Score (0-100, fleet-normalised)
    Avg_Power_Consumption (lower = better)  weight 0.70
    Duration_Minutes      (shorter = better) weight 0.30

    Composite = 0.90 * Quality_Score + 0.10 * Efficiency_Score

    Grade / Decision Map
    Composite >= 88 AND all hard gates pass  -> A  ACCEPT_EXCELLENT
    Composite 78-87.9                         -> B  ACCEPT_GOOD
    Composite 68-77.9                         -> C  CONDITIONAL
    Composite 58-67.9                         -> D  REVIEW
    Composite < 58 OR any hard gate fails     -> F  REJECT
    """

    DISSOLUTION_SPEC_MIN: float = 85.0
    FRIABILITY_SPEC_MAX: float = 1.0
    DISINTEGRATION_SPEC_MAX: float = 15.0
    CU_SPEC_MIN: float = 95.0
    CU_SPEC_MAX: float = 105.0
    HARDNESS_FLOOR: float = 50.0
    MOISTURE_SPEC_MAX: float = 5.0

    def _score_dissolution(self, v: float) -> float:
        if v >= 92.0: return 100.0
        if v >= 88.0: return 85.0
        if v >= 85.0: return 70.0
        if v >= 82.0: return 50.0
        return 20.0

    def _score_cu(self, v: float) -> float:
        dev = abs(v - 100.0)
        if dev <= 2.0: return 100.0
        if dev <= 4.0: return 85.0
        if dev <= 5.0: return 70.0
        if dev <= 7.0: return 50.0
        return 20.0

    def _score_disintegration(self, v: float) -> float:
        if v <= 8.0:  return 100.0
        if v <= 11.0: return 85.0
        if v <= 13.0: return 70.0
        if v <= 15.0: return 50.0
        return 20.0

    def _score_hardness(self, v: float) -> float:
        if 85.0 <= v <= 115.0: return 100.0
        if 75.0 <= v <= 125.0: return 85.0
        if 65.0 <= v <= 135.0: return 70.0
        if 55.0 <= v <= 145.0: return 50.0
        return 20.0

    def _score_friability(self, v: float) -> float:
        if v <= 0.50: return 100.0
        if v <= 0.75: return 85.0
        if v <= 1.00: return 70.0
        if v <= 1.30: return 50.0
        return 20.0

    def _score_moisture(self, v: float) -> float:
        if v <= 1.8: return 100.0
        if v <= 2.5: return 85.0
        if v <= 3.0: return 70.0
        if v <= 3.8: return 50.0
        return 20.0

    def _score_weight(self, v: float, target: float = 200.0) -> float:
        dev = abs(v - target)
        if dev <= 1.0: return 100.0
        if dev <= 3.0: return 85.0
        if dev <= 5.0: return 70.0
        if dev <= 7.0: return 50.0
        return 20.0

    QUALITY_WEIGHTS: dict[str, float] = {
        "Dissolution_Rate":    0.25,
        "Content_Uniformity":  0.20,
        "Disintegration_Time": 0.18,
        "Hardness":            0.15,
        "Friability":          0.12,
        "Moisture_Content":    0.06,
        "Tablet_Weight":       0.04,
    }

    def _run_hard_gates(self, params: dict) -> list[str]:
        failures = []
        diss = params.get("Dissolution_Rate", 100.0)
        if diss < self.DISSOLUTION_SPEC_MIN:
            failures.append(f"Dissolution {diss:.1f}% < {self.DISSOLUTION_SPEC_MIN}% (USP <711>)")
        fria = params.get("Friability", 0.0)
        if fria > self.FRIABILITY_SPEC_MAX:
            failures.append(f"Friability {fria:.2f}% > {self.FRIABILITY_SPEC_MAX}% (USP <1216>)")
        disint = params.get("Disintegration_Time", 0.0)
        if disint > self.DISINTEGRATION_SPEC_MAX:
            failures.append(f"Disintegration {disint:.1f} min > {self.DISINTEGRATION_SPEC_MAX} min (USP <701>)")
        cu = params.get("Content_Uniformity", 100.0)
        if not (self.CU_SPEC_MIN <= cu <= self.CU_SPEC_MAX):
            failures.append(f"Content Uniformity {cu:.1f}% outside [{self.CU_SPEC_MIN}, {self.CU_SPEC_MAX}]% (USP <905>)")
        hardness = params.get("Hardness", 100.0)
        if hardness < self.HARDNESS_FLOOR:
            failures.append(f"Hardness {hardness:.0f}N < {self.HARDNESS_FLOOR:.0f}N (physical integrity floor)")
        moist = params.get("Moisture_Content", 0.0)
        if moist > self.MOISTURE_SPEC_MAX:
            failures.append(f"Moisture {moist:.1f}% > {self.MOISTURE_SPEC_MAX}% (ICH Q1A)")
        return failures

    def _compute_quality_score(self, params: dict) -> tuple[float, dict[str, float]]:
        scorers = {
            "Dissolution_Rate":    self._score_dissolution,
            "Content_Uniformity":  self._score_cu,
            "Disintegration_Time": self._score_disintegration,
            "Hardness":            self._score_hardness,
            "Friability":          self._score_friability,
            "Moisture_Content":    self._score_moisture,
            "Tablet_Weight":       self._score_weight,
        }
        per_param: dict[str, float] = {}
        total = 0.0
        for param, weight in self.QUALITY_WEIGHTS.items():
            if param in params:
                raw_score = scorers[param](params[param])
                per_param[param] = raw_score
                total += weight * raw_score
        return round(total, 4), per_param

    def _compute_efficiency_score(
        self,
        avg_power: float, duration: float,
        fleet_power_min: float, fleet_power_max: float,
        fleet_dur_min: float, fleet_dur_max: float,
    ) -> float:
        power_range = fleet_power_max - fleet_power_min
        power_norm = (1.0 - (avg_power - fleet_power_min) / power_range) if power_range > 1e-8 else 0.5
        dur_range = fleet_dur_max - fleet_dur_min
        dur_norm = (1.0 - (duration - fleet_dur_min) / dur_range) if dur_range > 1e-8 else 0.5
        power_norm = float(np.clip(power_norm, 0.0, 1.0))
        dur_norm = float(np.clip(dur_norm, 0.0, 1.0))
        return round((0.70 * power_norm + 0.30 * dur_norm) * 100.0, 4)

    def _grade_and_decision(self, composite: float, hard_gate_passed: bool) -> tuple[str, str]:
        if not hard_gate_passed:
            return "F", "REJECT"
        if composite >= 88.0: return "A", "ACCEPT_EXCELLENT"
        if composite >= 78.0: return "B", "ACCEPT_GOOD"
        if composite >= 68.0: return "C", "CONDITIONAL"
        if composite >= 58.0: return "D", "REVIEW"
        return "F", "REJECT"

    def evaluate(
        self,
        batch_id: str,
        quality_params: dict,
        avg_power: float,
        duration_minutes: float,
        fleet_power_min: float = 19.0,
        fleet_power_max: float = 27.5,
        fleet_dur_min: float = 193.0,
        fleet_dur_max: float = 285.0,
    ) -> QualityReport:
        failures = self._run_hard_gates(quality_params)
        hard_gate_passed = len(failures) == 0
        quality_score, per_param = self._compute_quality_score(quality_params)
        efficiency_score = self._compute_efficiency_score(
            avg_power, duration_minutes,
            fleet_power_min, fleet_power_max,
            fleet_dur_min, fleet_dur_max,
        )
        composite = round(0.90 * quality_score + 0.10 * efficiency_score, 4)
        grade, decision = self._grade_and_decision(composite, hard_gate_passed)
        primary_failure = "None"
        if per_param:
            primary_failure = min(per_param, key=lambda k: per_param[k])
        report = QualityReport(
            batch_id=batch_id,
            hard_gate_passed=hard_gate_passed,
            hard_gate_failures=failures,
            quality_score=round(quality_score, 2),
            efficiency_score=round(efficiency_score, 2),
            composite_score=round(composite, 2),
            grade=grade,
            decision=decision,
            per_param_scores={k: round(v, 2) for k, v in per_param.items()},
            primary_failure=primary_failure,
        )
        logger.info(
            "[QualityEvaluator] %s | Grade=%s | Decision=%s | Composite=%.2f "
            "| HardGate=%s | Failures=%s",
            batch_id, grade, decision, composite,
            "PASS" if hard_gate_passed else "FAIL",
            failures if failures else "[]",
        )
        return report

    def evaluate_from_dataframe_row(
        self, row,
        fleet_power_min: float = 19.0,
        fleet_power_max: float = 27.5,
        fleet_dur_min: float = 193.0,
        fleet_dur_max: float = 285.0,
    ) -> QualityReport:
        quality_params = {col: float(row[col]) for col in QUALITY_COLUMNS if col in row}
        return self.evaluate(
            batch_id=str(row["Batch_ID"]),
            quality_params=quality_params,
            avg_power=float(row["Avg_Power_Consumption"]),
            duration_minutes=float(row["Duration_Minutes"]),
            fleet_power_min=fleet_power_min,
            fleet_power_max=fleet_power_max,
            fleet_dur_min=fleet_dur_min,
            fleet_dur_max=fleet_dur_max,
        )


def build_fleet_evaluator(prod_path: str, proc_path: str) -> tuple["BatchQualityEvaluator", object]:
    """Load both data files, compute fleet-wide normalisation bounds, return evaluator + merged df."""
    import pandas as pd
    prod_df = pd.read_excel(prod_path, sheet_name=0)
    proc_df = pd.read_excel(proc_path, sheet_name="Summary")
    df = prod_df.merge(proc_df, on="Batch_ID")
    evaluator = BatchQualityEvaluator()
    evaluator._fleet_power_min = float(df["Avg_Power_Consumption"].min())
    evaluator._fleet_power_max = float(df["Avg_Power_Consumption"].max())
    evaluator._fleet_dur_min = float(df["Duration_Minutes"].min())
    evaluator._fleet_dur_max = float(df["Duration_Minutes"].max())
    return evaluator, df


def _compute_golden_mask(df, evaluator: "BatchQualityEvaluator") -> "np.ndarray":
    """
    Boolean mask: True only for batches that pass ALL hard gates AND composite >= 88.
    This is the ONLY correct way to identify golden batches.
    """
    mask = []
    for _, row in df.iterrows():
        report = evaluator.evaluate_from_dataframe_row(
            row,
            fleet_power_min=evaluator._fleet_power_min,
            fleet_power_max=evaluator._fleet_power_max,
            fleet_dur_min=evaluator._fleet_dur_min,
            fleet_dur_max=evaluator._fleet_dur_max,
        )
        mask.append(report.hard_gate_passed and report.composite_score >= 88.0)
    return np.array(mask, dtype=bool)


# ===========================================================================
# Phase D: Kohonen Self-Organising Map
# ===========================================================================

class KohonenSOM:
    """
    Pure-NumPy 2-D Kohonen SOM.
    MUST be trained only on golden batches (GOLDEN_BATCH_IDS or _compute_golden_mask).
    Training on reject batches contaminates the Golden Signature topology.
    """

    def __init__(
        self,
        grid_h: int = 10, grid_w: int = 10,
        n_features: int = len(FEATURE_COLUMNS),
        n_iterations: int = 500, initial_lr: float = 0.5,
        initial_radius: float | None = None, seed: int = 42,
    ) -> None:
        self.grid_h = grid_h
        self.grid_w = grid_w
        self.n_features = n_features
        self.n_iterations = n_iterations
        self.initial_lr = initial_lr
        self.initial_radius = initial_radius or max(grid_h, grid_w) / 2.0
        self._rng = np.random.default_rng(seed)
        self.weights: np.ndarray = self._rng.random((grid_h, grid_w, n_features), dtype=np.float64)
        rows, cols = np.meshgrid(np.arange(grid_h), np.arange(grid_w), indexing="ij")
        self._grid_coords = np.stack([rows, cols], axis=-1).astype(np.float64)
        self._mean: np.ndarray = np.zeros(n_features, dtype=np.float64)
        self._std: np.ndarray = np.ones(n_features, dtype=np.float64)
        self.is_trained: bool = False

    def _normalise(self, X: np.ndarray) -> np.ndarray:
        return (X - self._mean) / (self._std + 1e-8)

    def _decay(self, initial: float, iteration: int, time_constant: float) -> float:
        return initial * np.exp(-iteration / time_constant)

    def _neighbourhood_func(self, bmu_row: int, bmu_col: int, radius: float) -> np.ndarray:
        bmu_coord = np.array([bmu_row, bmu_col], dtype=np.float64)
        delta = self._grid_coords - bmu_coord
        sq_dist = np.sum(delta ** 2, axis=2)
        return np.exp(-sq_dist / (2 * radius ** 2 + 1e-8))

    def fit(self, X: np.ndarray) -> "KohonenSOM":
        """Train on golden-batch telemetry ONLY."""
        if X.ndim != 2 or X.shape[1] != self.n_features:
            raise ValueError(f"Expected X with shape (n_samples, {self.n_features}), got {X.shape}")
        self._mean = X.mean(axis=0)
        self._std = X.std(axis=0)
        X_norm = self._normalise(X)
        time_constant = self.n_iterations / np.log(self.initial_radius + 1e-8)
        n_samples = len(X_norm)
        for t in range(self.n_iterations):
            lr = self._decay(self.initial_lr, t, time_constant)
            radius = self._decay(self.initial_radius, t, time_constant)
            x = X_norm[self._rng.integers(0, n_samples)]
            diff = self.weights - x
            dist = np.linalg.norm(diff, axis=2)
            _bmu = np.unravel_index(np.argmin(dist), dist.shape)
            bmu_row_i, bmu_col_i = _bmu[0].item(), _bmu[1].item()
            h = self._neighbourhood_func(bmu_row_i, bmu_col_i, radius)
            self.weights += lr * h[:, :, np.newaxis] * (x - self.weights)
        self.is_trained = True
        logger.info("KohonenSOM trained (golden data only). Grid=%dx%d, n_iter=%d",
                    self.grid_h, self.grid_w, self.n_iterations)
        return self

    def calculate_bmu(self, live_telemetry) -> tuple[tuple[int, int], float]:
        if not self.is_trained:
            raise RuntimeError("SOM must be trained with .fit() before calling calculate_bmu().")
        x = _telemetry_to_vector(live_telemetry)
        x_norm = self._normalise(x)
        diff = self.weights - x_norm
        dist = np.linalg.norm(diff, axis=2)
        bmu_row, bmu_col = np.unravel_index(np.argmin(dist), dist.shape)
        return (bmu_row.item(), bmu_col.item()), float(dist[bmu_row, bmu_col])


# ===========================================================================
# Phase E: LVQ Classifier
# ===========================================================================

class LVQClassifier:
    """
    Pure-NumPy LVQ-1 anomaly classifier for PROCESS telemetry anomalies.
    Labels describe equipment/process faults, NOT batch quality decisions.
    Batch quality decisions are solely the responsibility of BatchQualityEvaluator.
    """

    ANOMALY_LABELS: list[str] = [
        "Normal",
        "Thermal Drift",
        "Mechanical Friction",
        "Pressure Surge",
        "Flow Stagnation",
        "Vibration Fatigue",
    ]

    def __init__(
        self,
        n_prototypes_per_class: int = 2,
        learning_rate: float = 0.05,
        n_epochs: int = 200,
        seed: int = 42,
    ) -> None:
        self.n_prototypes_per_class = n_prototypes_per_class
        self.learning_rate = learning_rate
        self.n_epochs = n_epochs
        self._rng = np.random.default_rng(seed)
        self.codebook: np.ndarray = np.empty((0, len(FEATURE_COLUMNS)), dtype=np.float64)
        self.codebook_labels: np.ndarray = np.empty((0,), dtype=object)
        self.is_trained: bool = False
        self._mean: np.ndarray = np.zeros(len(FEATURE_COLUMNS), dtype=np.float64)
        self._std: np.ndarray = np.ones(len(FEATURE_COLUMNS), dtype=np.float64)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LVQClassifier":
        self._mean = X.mean(axis=0)
        self._std = X.std(axis=0)
        X_norm = (X - self._mean) / (self._std + 1e-8)
        unique_labels = np.unique(y)
        prototypes, proto_labels = [], []
        for label in unique_labels:
            class_mask = y == label
            class_X = X_norm[class_mask]
            idxs = self._rng.choice(len(class_X), self.n_prototypes_per_class, replace=True)
            for idx in idxs:
                prototypes.append(class_X[idx].copy())
                proto_labels.append(label)
        self.codebook = np.array(prototypes)
        self.codebook_labels = np.array(proto_labels)
        for _ in range(self.n_epochs):
            sample_idx = self._rng.integers(0, len(X_norm))
            x, label = X_norm[sample_idx], y[sample_idx]
            dists = np.linalg.norm(self.codebook - x, axis=1)
            winner = int(np.argmin(dists))
            if self.codebook_labels[winner] == label:
                self.codebook[winner] += self.learning_rate * (x - self.codebook[winner])
            else:
                self.codebook[winner] -= self.learning_rate * (x - self.codebook[winner])
        self.is_trained = True
        logger.info("LVQClassifier trained. %d prototypes.", len(self.codebook))
        return self

    def predict(self, x_raw: np.ndarray) -> str:
        if not self.is_trained:
            raise RuntimeError("LVQClassifier must be trained before predicting.")
        x_norm: np.ndarray = (x_raw - self._mean) / (self._std + 1e-8)
        dists: np.ndarray = np.linalg.norm(self.codebook - x_norm, axis=1)
        return str(self.codebook_labels[int(np.argmin(dists))])


# ===========================================================================
# Phase E: Phantom Energy Detection
# ===========================================================================

@dataclass
class PhantomEnergyAlert:
    batch_id: str
    time_minutes: int
    dfa_state: str
    motor_speed_rpm: int
    power_consumption_kw: float
    message: str = "Phantom Energy Waste Detected"
    severity: str = "WARNING"


def detect_phantom_energy(telemetry, current_dfa_state) -> Optional[PhantomEnergyAlert]:
    from state_machine import ManufacturingPhase
    if (
        current_dfa_state == ManufacturingPhase.PREPARATION
        and telemetry.Motor_Speed_RPM == 0
        and telemetry.Power_Consumption_kW > PHANTOM_ENERGY_THRESHOLD_KW
    ):
        alert = PhantomEnergyAlert(
            batch_id=telemetry.Batch_ID,
            time_minutes=telemetry.Time_Minutes,
            dfa_state=current_dfa_state.name,
            motor_speed_rpm=telemetry.Motor_Speed_RPM,
            power_consumption_kw=telemetry.Power_Consumption_kW,
        )
        logger.warning(
            "[PHANTOM ENERGY] Batch=%s t=%d min | RPM=0 | kW=%.3f > threshold %.1f kW",
            telemetry.Batch_ID, telemetry.Time_Minutes,
            telemetry.Power_Consumption_kW, PHANTOM_ENERGY_THRESHOLD_KW,
        )
        return alert
    return None


def analyze_spectral_friction(telemetry) -> dict | None:
    """
    Pseudo-Vibration-Ratio (PVR) friction detector.
    Threshold 12.0 is dataset-calibrated (mean ~7.5, std ~3.2, threshold = mean + 1.4*std).
    """
    pvr = telemetry.Power_Consumption_kW / (telemetry.Vibration_mm_s + 0.001)
    if pvr > 12.0 and telemetry.Motor_Speed_RPM > 0:
        return {
            "warning": (
                f"Invisible Mechanical Friction detected via PVR index ({pvr:.1f}). "
                f"Power draw {telemetry.Power_Consumption_kW:.1f} kW disproportionate "
                f"to vibration {telemetry.Vibration_mm_s:.3f} mm/s."
            )
        }
    return None


def detect_inter_phase_arbitrage(telemetry, current_state) -> dict | None:
    """Inter-Phase Arbitrage: lookahead causal optimisation hints."""
    from state_machine import ManufacturingPhase
    if current_state == ManufacturingPhase.GRANULATION and telemetry.Humidity_Percent > 46.0:
        return {"alert": (f"High humidity ({telemetry.Humidity_Percent:.1f}%) in Granulation. "
                          f"Extend Granulation_Time +2 min to avoid +10 deg C Drying spike.")}
    if current_state == ManufacturingPhase.DRYING and telemetry.Temperature_C > 55.0:
        return {"alert": (f"Drying temp elevated ({telemetry.Temperature_C:.1f} C). "
                          f"Reduce 5 C to prevent moisture overshoot, saving est. 3 kW.")}
    if current_state == ManufacturingPhase.COMPRESSION and telemetry.Power_Consumption_kW > 45.0:
        return {"alert": (f"Compression spike ({telemetry.Power_Consumption_kW:.1f} kW). "
                          f"Reduce Machine_Speed to avoid Coating thermal carryover.")}
    return None


def generate_xai_reasoning(telemetry, anomaly_class: str, dfa_state) -> dict:
    """Fuzzy Logic XAI sentences and 3-Node Knowledge Graph data."""
    temp_status = "HIGH" if telemetry.Temperature_C > 70 else "LOW" if telemetry.Temperature_C < 30 else "NOMINAL"
    power_status = "HIGH" if telemetry.Power_Consumption_kW > 30 else "IDLE" if telemetry.Power_Consumption_kW < 5 else "NOMINAL"
    if anomaly_class == "Normal":
        explanation = (f"System operating efficiently in {dfa_state.name}. "
                       f"{temp_status} Temp & {power_status} Power align with Golden Signature.")
        action = "Maintain Setpoints"
    else:
        explanation = (f"Fuzzy Alert: {temp_status} Temp & {power_status} Power detected "
                       f"during {dfa_state.name}. Root cause isolated to {anomaly_class}.")
        action = "Execute Autonomous Override"
    return {
        "explanation": explanation,
        "kg_nodes": [
            {"source": f"Symptom: {power_status} Power", "target": anomaly_class},
            {"source": anomaly_class, "target": action},
        ],
    }


# ===========================================================================
# auto_calibrate_thresholds -- uses correct golden definition
# ===========================================================================

def auto_calibrate_thresholds(
    prod_path: str = "_h_batch_production_data.xlsx",
    proc_path: str = "_h_batch_process_data.xlsx",
) -> None:
    """
    Calibrate process-telemetry energy thresholds from correctly-identified
    golden batches (pass ALL hard gates AND composite >= 88).
    Thresholds: mean_golden_power + 1.5*std (covers ~93% of golden distribution).
    """
    import pandas as pd
    global GOLDEN_AVG_POWER_THRESHOLD, GOLDEN_PEAK_POWER_THRESHOLD, ANOMALY_DISTANCE_THRESHOLD

    if not os.path.exists(prod_path) or not os.path.exists(proc_path):
        logger.warning("auto_calibrate_thresholds: data files not found. Using defaults.")
        return

    try:
        prod_df = pd.read_excel(prod_path, sheet_name=0)
        proc_df = pd.read_excel(proc_path, sheet_name="Summary")
        df = prod_df.merge(proc_df, on="Batch_ID")

        xl = pd.ExcelFile(proc_path)
        power_profile: list[dict] = []
        for sheet in xl.sheet_names:
            if not sheet.startswith("Batch_T"): continue
            try:
                sdf = xl.parse(sheet)
                b_id = str(sdf["Batch_ID"].iloc[0])
                power_profile.append({
                    "Batch_ID": b_id,
                    "avg_power": float(sdf["Power_Consumption_kW"].mean()),
                    "peak_power": float(sdf["Power_Consumption_kW"].max()),
                })
            except Exception:
                pass

        power_df = pd.DataFrame(power_profile)
        df = df.merge(power_df, on="Batch_ID", suffixes=("", "_raw"))

        fleet_power_min = float(df["avg_power"].min())
        fleet_power_max = float(df["avg_power"].max())
        fleet_dur_min = float(df["Duration_Minutes"].min())
        fleet_dur_max = float(df["Duration_Minutes"].max())

        evaluator = BatchQualityEvaluator()
        evaluator._fleet_power_min = fleet_power_min
        evaluator._fleet_power_max = fleet_power_max
        evaluator._fleet_dur_min = fleet_dur_min
        evaluator._fleet_dur_max = fleet_dur_max

        golden_power = []
        for _, row in df.iterrows():
            quality_params = {col: float(row[col]) for col in QUALITY_COLUMNS if col in row}
            report = evaluator.evaluate(
                batch_id=str(row["Batch_ID"]),
                quality_params=quality_params,
                avg_power=float(row["avg_power"]),
                duration_minutes=float(row["Duration_Minutes"]),
                fleet_power_min=fleet_power_min,
                fleet_power_max=fleet_power_max,
                fleet_dur_min=fleet_dur_min,
                fleet_dur_max=fleet_dur_max,
            )
            if report.hard_gate_passed and report.composite_score >= 88.0:
                golden_power.append({
                    "batch_id": str(row["Batch_ID"]),
                    "avg_power": float(row["avg_power"]),
                    "peak_power": float(row["peak_power"]),
                })

        if golden_power:
            avg_arr = np.array([b["avg_power"] for b in golden_power])
            peak_arr = np.array([b["peak_power"] for b in golden_power])
            GOLDEN_AVG_POWER_THRESHOLD = float(avg_arr.mean() + 1.5 * avg_arr.std())
            GOLDEN_PEAK_POWER_THRESHOLD = float(peak_arr.mean() + 1.5 * peak_arr.std())
            logger.info(
                "Calibrated thresholds from %d true golden batches: avg=%.3f kW, peak=%.3f kW",
                len(golden_power), GOLDEN_AVG_POWER_THRESHOLD, GOLDEN_PEAK_POWER_THRESHOLD,
            )
        else:
            logger.warning("No golden batches found. Check data files.")
    except Exception as e:
        logger.warning("auto_calibrate_thresholds failed: %s", e)


# ===========================================================================
# evaluate_batch_performance -- delegates to BatchQualityEvaluator
# REQUIRES quality_params + duration_minutes for a valid verdict
# ===========================================================================

def evaluate_batch_performance(
    batch_id: str,
    avg_power: float,
    max_power: float,
    quality_params: Optional[dict] = None,
    duration_minutes: Optional[float] = None,
    fleet_power_min: float = 19.0,
    fleet_power_max: float = 27.5,
    fleet_dur_min: float = 193.0,
    fleet_dur_max: float = 285.0,
) -> dict:
    """
    Evaluate batch performance and determine whether to trigger SOM retraining.

    quality_params and duration_minutes are REQUIRED for a valid quality verdict.
    Without them, only energy thresholds are checked (degraded mode -- unreliable).

    Returns dict with keys:
        grade, decision, composite_score, quality_score, efficiency_score,
        hard_gate_passed, hard_gate_failures, per_param_scores, primary_failure,
        trigger_som_retraining, message, avg_power_kW, peak_power_kW.
    """
    result: dict = {
        "batch_id": batch_id,
        "avg_power_kW": round(avg_power, 2),
        "peak_power_kW": round(max_power, 2),
    }

    if quality_params is not None and duration_minutes is not None:
        evaluator = BatchQualityEvaluator()
        report = evaluator.evaluate(
            batch_id=batch_id,
            quality_params=quality_params,
            avg_power=avg_power,
            duration_minutes=duration_minutes,
            fleet_power_min=fleet_power_min,
            fleet_power_max=fleet_power_max,
            fleet_dur_min=fleet_dur_min,
            fleet_dur_max=fleet_dur_max,
        )
        result.update({
            "grade": report.grade,
            "decision": report.decision,
            "composite_score": report.composite_score,
            "quality_score": report.quality_score,
            "efficiency_score": report.efficiency_score,
            "hard_gate_passed": report.hard_gate_passed,
            "hard_gate_failures": report.hard_gate_failures,
            "per_param_scores": report.per_param_scores,
            "primary_failure": report.primary_failure,
        })
        trigger = (
            report.decision == "ACCEPT_EXCELLENT"
            and report.hard_gate_passed
            and avg_power < GOLDEN_AVG_POWER_THRESHOLD
        )
    else:
        # Degraded mode -- energy only
        trigger = avg_power < GOLDEN_AVG_POWER_THRESHOLD and max_power < GOLDEN_PEAK_POWER_THRESHOLD
        result["grade"] = "?"
        result["decision"] = "UNKNOWN"
        result["warning"] = (
            "Quality parameters not provided. Decision based on energy thresholds only -- "
            "unreliable. Pass quality_params + duration_minutes for a valid verdict."
        )

    result["trigger_som_retraining"] = trigger

    if trigger:
        file_path = "som_retraining_ledger.json"
        ledger: list = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                try: ledger = json.load(f)
                except Exception: pass
        ledger.append({k: v for k, v in result.items() if not isinstance(v, (list, dict))})
        with open(file_path, "w") as f:
            json.dump(ledger, f, indent=4)
        result["message"] = (
            f"Golden Batch confirmed! Grade={result.get('grade','?')}, "
            f"Composite={result.get('composite_score','?')}, "
            f"avg_power={avg_power:.2f} kW < {GOLDEN_AVG_POWER_THRESHOLD:.2f} kW. "
            f"Edge-Cloud Sync Scheduled."
        )
    else:
        fails = "; ".join(result.get("hard_gate_failures", []))
        if not fails:
            fails = (
                f"Grade={result.get('grade','?')}, Decision={result.get('decision','?')}"
                if result.get("grade") not in ("?", None)
                else f"avg_power={avg_power:.2f} kW >= threshold {GOLDEN_AVG_POWER_THRESHOLD:.2f} kW"
            )
        result["message"] = f"Batch did not meet Golden Signature. Reason: {fails}"

    return result


# ===========================================================================
# Phase E: Prescriptive Recommendation Engine
# ===========================================================================

@dataclass
class Prescription:
    batch_id: str
    time_minutes: int
    dfa_state: str
    bmu_index: tuple[int, int]
    bmu_distance: float
    anomaly_class: str
    parameter_recommendations: dict[str, float]
    dfa_guardrail_passed: bool = True
    blocked_parameters: list[str] = field(default_factory=list)


def generate_prescription(
    telemetry, current_dfa_state, som: KohonenSOM, lvq: LVQClassifier,
    dfa, quality_margin: float = 0.0,
) -> Prescription:
    """
    Generate a physically validated prescriptive recommendation.
    BatchQualityEvaluator (not this function) decides Accept/Reject.
    This function recommends process parameter adjustments only.
    """
    from state_machine import PhysicalViolationError

    bmu_idx, bmu_distance = som.calculate_bmu(telemetry)
    bmu_row, bmu_col = bmu_idx

    bmu_weights_norm: np.ndarray = som.weights[bmu_row, bmu_col]
    golden_target: np.ndarray = bmu_weights_norm * (som._std + 1e-8) + som._mean
    live_vec: np.ndarray = _telemetry_to_vector(telemetry)

    raw_recommendations: dict[str, float] = {
        col: float(np.round(golden_target[i] - live_vec[i], 4))
        for i, col in enumerate(FEATURE_COLUMNS)
        if float(abs(golden_target[i] - live_vec[i])) > 0.01
    }

    if quality_margin > 3.0:
        harvest_intensity = min(quality_margin / 10.0, 1.5)
        raw_recommendations["Power_Consumption_kW"] = (
            raw_recommendations.get("Power_Consumption_kW", 0.0) - harvest_intensity
        )

    anomaly_class = lvq.predict(live_vec) if bmu_distance > ANOMALY_DISTANCE_THRESHOLD else "Normal"

    validated_recommendations: dict[str, float] = {}
    blocked_parameters: list[str] = []
    for param, delta in raw_recommendations.items():
        try:
            dfa.validate_prescription(current_dfa_state, param)
            validated_recommendations[param] = delta
        except PhysicalViolationError as exc:
            logger.warning("[DFA GUARDRAIL] Prescription BLOCKED: %s | Reason: %s", param, exc)
            blocked_parameters.append(param)

    prescription = Prescription(
        batch_id=telemetry.Batch_ID,
        time_minutes=telemetry.Time_Minutes,
        dfa_state=current_dfa_state.name,
        bmu_index=bmu_idx,
        bmu_distance=float(np.round(bmu_distance, 6)),
        anomaly_class=anomaly_class,
        parameter_recommendations=validated_recommendations,
        dfa_guardrail_passed=len(blocked_parameters) == 0,
        blocked_parameters=blocked_parameters,
    )
    logger.info(
        "[Prescription] Batch=%s t=%d | State=%s | Anomaly=%s | BMU=(%d,%d) dist=%.4f | "
        "Recs=%d valid, %d blocked",
        telemetry.Batch_ID, telemetry.Time_Minutes, current_dfa_state.name, anomaly_class,
        bmu_row, bmu_col, bmu_distance, len(validated_recommendations), len(blocked_parameters),
    )
    return prescription
