import clsx from 'clsx';
import { RefreshCw, Database, AlertTriangle, CheckCircle, Activity } from 'lucide-react';

interface LedgerStatus {
  trigger_som_retraining: boolean;
  message: string;
  avg_power_kW?: number;
  peak_power_kW?: number;
}

interface BatchSummary {
  total_rows: number;
  total_alerts: number;
  anomaly_detections: number;
  phantom_alerts: number;
  pvr_alerts: number;
  arbitrage_alerts: number;
  dominant_anomaly: string;
  anomaly_class_counts: Record<string, number>;
  avg_bmu_distance: number;
  max_bmu_distance: number;
  normal_pct: number;
}

interface LedgerAlertProps {
  status: LedgerStatus | null;
  summary?: BatchSummary | null;
}

function getHealthGrade(summary: BatchSummary): { grade: string, color: string, label: string } {
  const pct = summary.normal_pct;
  if (pct >= 85) return { grade: 'A', color: 'text-accent-emerald', label: 'Excellent' };
  if (pct >= 70) return { grade: 'B', color: 'text-accent-teal', label: 'Good' };
  if (pct >= 55) return { grade: 'C', color: 'text-yellow-400', label: 'Moderate' };
  if (pct >= 40) return { grade: 'D', color: 'text-orange-400', label: 'Poor' };
  return { grade: 'F', color: 'text-accent-coral', label: 'Critical' };
}

export function LedgerAlert({ status, summary }: LedgerAlertProps) {
  if (!status) return null;
  const triggered = status.trigger_som_retraining;
  const health = summary ? getHealthGrade(summary) : null;

  return (
    <div className={clsx(
      "w-full glass-panel mt-4 p-5 flex flex-col items-center justify-center flex-shrink-0 z-50 transition-all duration-700",
      triggered 
        ? "border-accent-teal/40 shadow-[0_0_30px_-8px_rgba(45,212,168,0.2)]" 
        : summary && summary.normal_pct < 60
          ? "border-accent-coral/30 shadow-[0_0_20px_-8px_rgba(240,100,73,0.15)]"
          : "border-oracle-border"
    )}>
      <h2 className={clsx(
        "font-display text-lg font-bold flex items-center gap-3 uppercase tracking-[0.12em]",
        triggered ? "text-accent-teal" : summary && summary.normal_pct < 60 ? "text-accent-coral" : "text-oracle-muted"
      )}>
        {triggered ? (
          <><RefreshCw className="animate-spin text-accent-teal" size={20} /> Continuous Learning Triggered</>
        ) : summary && summary.normal_pct < 60 ? (
          <><AlertTriangle className="text-accent-coral" size={20} /> Batch Performance Below Threshold</>
        ) : (
          <><Database className="text-oracle-muted/40" size={20} /> Batch Historian Committed</>
        )}
      </h2>
      
      <p className={clsx(
        "mt-2 text-sm font-body max-w-2xl text-center leading-relaxed",
        triggered ? "text-accent-teal/60" : "text-oracle-muted/60"
      )}>
        {triggered 
          ? "Recursive Bayesian Update written to ledger for Edge-Cloud sync. Target weights shifted to mirror Golden Signature."
          : status.message}
      </p>

      {summary && (
        <div className="mt-4 w-full max-w-3xl grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Health Grade */}
          <div className="glass-panel p-3 flex flex-col items-center border-oracle-border/30">
            <span className="text-[10px] font-mono text-oracle-muted uppercase tracking-wider">Health Grade</span>
            <span className={clsx("text-3xl font-display font-bold mt-1", health?.color)}>
              {health?.grade}
            </span>
            <span className={clsx("text-[10px] font-mono mt-0.5", health?.color)}>
              {health?.label}
            </span>
          </div>
          
          {/* Total Alerts */}
          <div className="glass-panel p-3 flex flex-col items-center border-oracle-border/30">
            <span className="text-[10px] font-mono text-oracle-muted uppercase tracking-wider">Total Alerts</span>
            <span className={clsx(
              "text-2xl font-display font-bold mt-1",
              summary.total_alerts > 150 ? "text-accent-coral" : summary.total_alerts > 100 ? "text-yellow-400" : "text-accent-emerald"
            )}>
              {summary.total_alerts}
            </span>
            <span className="text-[10px] font-mono text-oracle-muted/50 mt-0.5">
              of {summary.total_rows} ticks
            </span>
          </div>
          
          {/* Normal % */}
          <div className="glass-panel p-3 flex flex-col items-center border-oracle-border/30">
            <span className="text-[10px] font-mono text-oracle-muted uppercase tracking-wider">Normal Rate</span>
            <span className={clsx(
              "text-2xl font-display font-bold mt-1",
              summary.normal_pct >= 80 ? "text-accent-emerald" : summary.normal_pct >= 60 ? "text-yellow-400" : "text-accent-coral"
            )}>
              {summary.normal_pct}%
            </span>
            <span className="text-[10px] font-mono text-oracle-muted/50 mt-0.5">
              healthy ticks
            </span>
          </div>
          
          {/* Dominant Issue */}
          <div className="glass-panel p-3 flex flex-col items-center border-oracle-border/30">
            <span className="text-[10px] font-mono text-oracle-muted uppercase tracking-wider">Primary Issue</span>
            <span className={clsx(
              "text-sm font-display font-bold mt-1 text-center leading-tight",
              summary.dominant_anomaly === "Normal" ? "text-accent-emerald" : "text-accent-coral"
            )}>
              {summary.dominant_anomaly === "Normal" ? (
                <span className="flex items-center gap-1"><CheckCircle size={14} /> None</span>
              ) : (
                <span className="flex items-center gap-1"><Activity size={14} /> {summary.dominant_anomaly}</span>
              )}
            </span>
            <span className="text-[10px] font-mono text-oracle-muted/50 mt-0.5">
              {summary.dominant_anomaly !== "Normal" 
                ? `${summary.anomaly_class_counts[summary.dominant_anomaly]} occurrences` 
                : "all clear"}
            </span>
          </div>
        </div>
      )}

      {/* Power stats row */}
      {status.avg_power_kW != null && (
        <div className="mt-3 flex gap-6 text-[11px] font-mono text-oracle-muted/40">
          <span>Avg Power: <strong className="text-oracle-muted/60">{status.avg_power_kW} kW</strong></span>
          <span>Peak Power: <strong className="text-oracle-muted/60">{status.peak_power_kW} kW</strong></span>
          {summary && <>
            <span>Avg BMU Dist: <strong className="text-oracle-muted/60">{summary.avg_bmu_distance}</strong></span>
            <span>Max BMU Dist: <strong className="text-oracle-muted/60">{summary.max_bmu_distance}</strong></span>
          </>}
        </div>
      )}
    </div>
  );
}
