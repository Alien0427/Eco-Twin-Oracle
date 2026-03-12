"""
extract_thresholds.py
=====================
Diagnostic script: compute and verify energy thresholds for the Oracle.

FIX vs. original
-----------------
Original used Dissolution_Rate >= 90 as the golden criterion, which selected
batches including T008, T014, T018, T025, T029, T034 etc — all Grade-F USP
rejects (Friability > 1.0%, CU outside 95-105%).

Fixed: imports GOLDEN_BATCH_IDS from analytics_engine — the 9 batches that pass
ALL USP/ICH hard gates AND score >= 88 (Grade A):
  T001, T006, T010, T019, T024, T027, T041, T044, T055

Run this script to verify the calibrated thresholds before server startup.
"""

import pandas as pd
import numpy as np
import json

# Import the correct golden set — never recompute it here with a simple criterion
from analytics_engine import GOLDEN_BATCH_IDS, BatchQualityEvaluator, QUALITY_COLUMNS

PROD_PATH = "_h_batch_production_data.xlsx"
PROC_PATH = "_h_batch_process_data.xlsx"

# ── Load and merge data ──────────────────────────────────────────────────────
prod = pd.read_excel(PROD_PATH, sheet_name=0)
xl = pd.ExcelFile(PROC_PATH)

power_stats = []
for sheet in xl.sheet_names:
    if not sheet.startswith("Batch_T"):
        continue
    try:
        df = xl.parse(sheet)
        batch_id = str(df["Batch_ID"].iloc[0])
        avg_power = float(df["Power_Consumption_kW"].mean())
        peak_power = float(df["Power_Consumption_kW"].max())
        power_stats.append({"Batch_ID": batch_id, "avg_power": avg_power, "peak_power": peak_power})
    except Exception as e:
        print(f"Skipping {sheet}: {e}")

power_df = pd.DataFrame(power_stats)
merged = prod.merge(power_df, on="Batch_ID")

# ── Identify golden and bad batches using correct criterion ──────────────────
# GOLDEN: passes ALL USP/ICH hard gates AND composite score >= 88 (Grade A)
# NOT: Dissolution_Rate >= 90 or >= 95 (single-parameter criterion is wrong —
#      it admits batches with Friability > 1.0% and CU outside 95-105%)
proc_summary = pd.read_excel(PROC_PATH, sheet_name="Summary")
merged_full = prod.merge(proc_summary, on="Batch_ID").merge(power_df, on="Batch_ID")

fleet_power_min = float(merged_full["Avg_Power_Consumption"].min())
fleet_power_max = float(merged_full["Avg_Power_Consumption"].max())
fleet_dur_min = float(merged_full["Duration_Minutes"].min())
fleet_dur_max = float(merged_full["Duration_Minutes"].max())

evaluator = BatchQualityEvaluator()
evaluator._fleet_power_min = fleet_power_min
evaluator._fleet_power_max = fleet_power_max
evaluator._fleet_dur_min = fleet_dur_min
evaluator._fleet_dur_max = fleet_dur_max

golden_power = []
bad_power = []
grade_map = {}

for _, row in merged_full.iterrows():
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
    grade_map[str(row["Batch_ID"])] = report.grade
    if report.grade == "A":
        golden_power.append({"batch_id": str(row["Batch_ID"]), "avg_power": float(row["avg_power"]), "peak_power": float(row["peak_power"])})
    else:
        bad_power.append({"batch_id": str(row["Batch_ID"]), "avg_power": float(row["avg_power"]), "peak_power": float(row["peak_power"])})

golden_df = pd.DataFrame(golden_power)
bad_df = pd.DataFrame(bad_power)

# ── Compute thresholds ───────────────────────────────────────────────────────
thresholds = {
    "golden_batch_count": len(golden_df),
    "golden_batch_ids": sorted([b["batch_id"] for b in golden_power]),
    "golden_avg_power_mean": round(float(golden_df["avg_power"].mean()), 4),
    "golden_avg_power_std": round(float(golden_df["avg_power"].std()), 4),
    "golden_avg_power_threshold_mean_plus_1_5std": round(float(golden_df["avg_power"].mean() + 1.5 * golden_df["avg_power"].std()), 4),
    "golden_avg_power_max": round(float(golden_df["avg_power"].max()), 4),
    "golden_peak_power_mean": round(float(golden_df["peak_power"].mean()), 4),
    "golden_peak_power_threshold_mean_plus_1_5std": round(float(golden_df["peak_power"].mean() + 1.5 * golden_df["peak_power"].std()), 4),
    "golden_peak_power_max": round(float(golden_df["peak_power"].max()), 4),
    "bad_avg_power_mean": round(float(bad_df["avg_power"].mean()), 4),
    "bad_peak_power_mean": round(float(bad_df["peak_power"].mean()), 4),
}

# ── Print results ────────────────────────────────────────────────────────────
print("=" * 60)
print("  TOP 10 BATCHES by Composite Quality Score")
print("=" * 60)
display_rows = []
for _, row in merged_full.iterrows():
    quality_params = {col: float(row[col]) for col in QUALITY_COLUMNS if col in row}
    r = evaluator.evaluate(
        batch_id=str(row["Batch_ID"]),
        quality_params=quality_params,
        avg_power=float(row["avg_power"]),
        duration_minutes=float(row["Duration_Minutes"]),
        fleet_power_min=fleet_power_min,
        fleet_power_max=fleet_power_max,
        fleet_dur_min=fleet_dur_min,
        fleet_dur_max=fleet_dur_max,
    )
    display_rows.append({"Batch_ID": str(row["Batch_ID"]), "Grade": r.grade,
                          "Composite": r.composite_score, "HardGate": "PASS" if r.hard_gate_passed else "FAIL",
                          "Dissolution": row["Dissolution_Rate"], "avg_power": round(float(row["avg_power"]), 2),
                          "peak_power": round(float(row["peak_power"]), 2)})

display_df = pd.DataFrame(display_rows).sort_values("Composite", ascending=False)
print(display_df.head(10).to_string(index=False))
print()
print("=" * 60)
print("  BOTTOM 10 BATCHES by Composite Quality Score")
print("=" * 60)
print(display_df.tail(10).to_string(index=False))
print()
print("=" * 60)
print("  CALIBRATED THRESHOLDS (from correct Grade-A golden set)")
print("=" * 60)
print(json.dumps(thresholds, indent=2))

# ── Verify the three key batches ─────────────────────────────────────────────
print()
print("=" * 60)
print("  KEY BATCH VERIFICATION")
print("=" * 60)
for bid in ["T001", "T051", "T060"]:
    row = merged_full[merged_full["Batch_ID"] == bid].iloc[0]
    quality_params = {col: float(row[col]) for col in QUALITY_COLUMNS if col in row}
    r = evaluator.evaluate(
        batch_id=bid, quality_params=quality_params,
        avg_power=float(row["avg_power"]), duration_minutes=float(row["Duration_Minutes"]),
        fleet_power_min=fleet_power_min, fleet_power_max=fleet_power_max,
        fleet_dur_min=fleet_dur_min, fleet_dur_max=fleet_dur_max,
    )
    print(f"  {bid}: Grade={r.grade} | Decision={r.decision} | Composite={r.composite_score}")
    if r.hard_gate_failures:
        for f in r.hard_gate_failures:
            print(f"    FAIL: {f}")
    else:
        print(f"    All hard gates: PASS")

print()
print("  Expected: T001=A/ACCEPT_EXCELLENT  T051=F/REJECT  T060=F/REJECT")