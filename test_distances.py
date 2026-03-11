"""
test_distances.py
=================
Validates that the SOM trained on the correct golden batch set produces
clearly separated BMU distances for golden vs. reject batches.

FIX vs. original
-----------------
BUG-1: golden_ids was ['T050', 'T041', 'T048', 'T033', 'T019']
       T050 (Grade B), T048 (Grade B), T033 (Grade B) are not truly golden.
       Only T041 and T019 are in the real golden set.
       Fixed: imports GOLDEN_BATCH_IDS from analytics_engine.

BUG-2: from main import _train_from_excel, KohonenSOM
       main._train_from_excel() internally calls _identify_golden_batches()
       which uses Dissolution >= 95% — selecting 13 Grade-F reject batches.
       So the SOM was trained on wrong data, and the "golden" distances
       were meaninglessly low because bad batches were in the training set.
       Fixed: _train_from_excel() is now defined here using GOLDEN_BATCH_IDS.

Expected result after fix:
  Golden batches (T001, T006, T010, T019, T024, T027, T041, T044, T055):
    mean BMU distance << ANOMALY_DISTANCE_THRESHOLD (1.8)
  Reject batches (T051, T020, T056, T031, T036, T060):
    mean BMU distance > ANOMALY_DISTANCE_THRESHOLD (1.8)
"""

import asyncio
import numpy as np
import pandas as pd

from analytics_engine import (
    FEATURE_COLUMNS,
    GOLDEN_BATCH_IDS,           # FIX-1: correct set, not hardcoded list
    ANOMALY_DISTANCE_THRESHOLD,
    KohonenSOM,
    auto_calibrate_thresholds,
)
from stream_simulator import stream_batch_data

PROC_PATH = "_h_batch_process_data.xlsx"


def _build_som_training_data() -> np.ndarray:
    """
    Load telemetry ONLY from GOLDEN_BATCH_IDS for SOM training.
    Sync blocking function — called via asyncio.to_thread.
    FIX-2: no longer imports _train_from_excel from main.py.
    """
    xl = pd.ExcelFile(PROC_PATH)
    rows = []
    for sheet in xl.sheet_names:
        if not sheet.startswith("Batch_T"):
            continue
        try:
            df = xl.parse(sheet).sort_values("Time_Minutes")
            batch_id = str(df["Batch_ID"].iloc[0]).strip()
            if batch_id not in GOLDEN_BATCH_IDS:
                continue
            for _, row in df.iterrows():
                vec = [float(row.get(col, 0.0)) for col in FEATURE_COLUMNS]
                rows.append(vec)
        except Exception as e:
            print(f"Skipping {sheet}: {e}")

    X = np.array(rows, dtype=np.float64)
    print(f"SOM training data: {len(X)} rows from {len(GOLDEN_BATCH_IDS)} golden batches: {sorted(GOLDEN_BATCH_IDS)}")
    return X


async def analyze():
    # Calibrate thresholds first
    auto_calibrate_thresholds()

    print("\nBuilding SOM training data from golden batches...")
    # Run blocking pandas I/O in thread pool (correct: _build_som_training_data is sync)
    X_train = await asyncio.to_thread(_build_som_training_data)

    print(f"Training SOM on {len(X_train)} golden rows...")
    som = KohonenSOM(grid_h=10, grid_w=10, n_iterations=800, seed=42)
    som.fit(X_train)
    print(f"SOM trained. Anomaly distance threshold: {ANOMALY_DISTANCE_THRESHOLD}")

    # True golden batches (Grade A, pass all USP gates)
    golden_ids = sorted(GOLDEN_BATCH_IDS)

    # True reject batches (Grade F, hard gate failures)
    reject_ids = ["T051", "T020", "T056", "T031", "T036", "T060"]

    print("\n--- TRUE GOLDEN BATCHES (Grade A, all USP gates pass) ---")
    print(f"  {'Batch':<8} {'mean':>8} {'p95':>8} {'max':>8}  {'Anomalous?'}")
    print("  " + "-" * 50)
    for bid in golden_ids:
        dists = []
        try:
            async for t, _, _ in stream_batch_data(bid, 0):
                _, d = som.calculate_bmu(t)
                dists.append(d)
        except Exception as e:
            print(f"  {bid}: ERROR — {e}")
            continue
        if dists:
            mean_d = np.mean(dists)
            p95_d = np.percentile(dists, 95)
            max_d = np.max(dists)
            flag = "✗ ANOMALOUS (should be Normal)" if mean_d > ANOMALY_DISTANCE_THRESHOLD else "✓ Normal"
            print(f"  {bid:<8} {mean_d:>8.3f} {p95_d:>8.3f} {max_d:>8.3f}  {flag}")

    print("\n--- REJECT BATCHES (Grade F, USP hard gate failures) ---")
    print(f"  {'Batch':<8} {'mean':>8} {'p95':>8} {'max':>8}  {'Detected as Anomaly?'}")
    print("  " + "-" * 50)
    for bid in reject_ids:
        dists = []
        try:
            async for t, _, _ in stream_batch_data(bid, 0):
                _, d = som.calculate_bmu(t)
                dists.append(d)
        except Exception as e:
            print(f"  {bid}: ERROR — {e}")
            continue
        if dists:
            mean_d = np.mean(dists)
            p95_d = np.percentile(dists, 95)
            max_d = np.max(dists)
            flag = "✓ Detected (high BMU distance)" if mean_d > ANOMALY_DISTANCE_THRESHOLD else "✗ MISSED (should be anomalous)"
            print(f"  {bid:<8} {mean_d:>8.3f} {p95_d:>8.3f} {max_d:>8.3f}  {flag}")

    print(f"\n  Threshold: ANOMALY_DISTANCE_THRESHOLD = {ANOMALY_DISTANCE_THRESHOLD}")
    print("  Golden batches should have mean < threshold.")
    print("  Reject batches should have mean > threshold.")


if __name__ == "__main__":
    asyncio.run(analyze())