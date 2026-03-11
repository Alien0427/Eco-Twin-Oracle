import clsx from 'clsx';
import { RefreshCw, Database, AlertTriangle, CheckCircle, XCircle, Activity, ShieldCheck, ShieldAlert } from 'lucide-react';

// Maps to evaluate_batch_performance() / ledger_result dict from main.py
interface LedgerStatus {
  trigger_som_retraining: boolean;
  message: string;
  batch_id?: string;
  avg_power_kW?: number;
  peak_power_kW?: number;
  // Quality verdict fields from BatchQualityEvaluator (FIX-3)
  grade?: string;
  decision?: string;
  composite_score?: number;
  quality_score?: number;
  efficiency_score?: number;
  hard_gate_passed?: boolean;
  hard_gate_failures?: string[];
  per_param_scores?: Record<string, number>;
  primary_failure?: string;
}

// Maps to batch_summary dict from main.py WebSocket handler
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
  // FIX: renamed from normal_pct — this is LVQ process-telemetry stability, NOT quality grade
  process_stability_pct: number;
  // Authoritative quality verdict from BatchQualityEvaluator (FIX-3)
  quality_grade: string;
  quality_decision: string;
  quality_composite: number;
  quality_score: number;
  efficiency_score: number;
  hard_gate_passed: boolean;
  hard_gate_failures: string[];
  primary_failure: string;
  per_param_scores: Record<string, number>;
  avg_power_kW: number;
  peak_power_kW: number;
}

interface LedgerAlertProps {
  status: LedgerStatus | null;
  summary?: BatchSummary | null;
}

// Grade colour from the authoritative BatchQualityEvaluator grade (A/B/C/D/F)
function gradeStyle(grade: string): { color: string; label: string } {
  switch (grade) {
    case 'A': return { color: 'text-accent-emerald', label: 'Excellent' };
    case 'B': return { color: 'text-accent-teal',    label: 'Good' };
    case 'C': return { color: 'text-yellow-400',     label: 'Moderate' };
    case 'D': return { color: 'text-orange-400',     label: 'Review' };
    default:  return { color: 'text-accent-coral',   label: 'Critical' };
  }
}

// Decision badge colour
function decisionStyle(decision: string): { bg: string; text: string; border: string } {
  if (decision === 'ACCEPT_EXCELLENT' || decision === 'ACCEPT_GOOD') {
    return { bg: 'bg-accent-emerald/10', text: 'text-accent-emerald', border: 'border-accent-emerald/30' };
  }
  if (decision === 'CONDITIONAL') {
    return { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/30' };
  }
  if (decision === 'REVIEW') {
    return { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30' };
  }
  // REJECT / UNKNOWN
  return { bg: 'bg-accent-coral/10', text: 'text-accent-coral', border: 'border-accent-coral/30' };
}

function formatDecisionLabel(decision: string): string {
  switch (decision) {
    case 'ACCEPT_EXCELLENT': return 'ACCEPT — EXCELLENT';
    case 'ACCEPT_GOOD':      return 'ACCEPT — GOOD';
    case 'CONDITIONAL':      return 'CONDITIONAL RELEASE';
    case 'REVIEW':           return 'REVIEW REQUIRED';
    case 'REJECT':           return 'REJECT';
    default:                 return decision || 'UNKNOWN';
  }
}

export function LedgerAlert({ status, summary }: LedgerAlertProps) {
  if (!status) return null;

  const triggered = status.trigger_som_retraining;

  // Use authoritative quality grade from backend (BatchQualityEvaluator)
  // Fall back to summary.quality_grade, then status.grade
  const grade = summary?.quality_grade || status.grade || '?';
  const decision = summary?.quality_decision || status.decision || 'UNKNOWN';
  const composite = summary?.quality_composite ?? status.composite_score ?? null;
  const hardGatePassed = summary?.hard_gate_passed ?? status.hard_gate_passed ?? null;
  const hardGateFailures = summary?.hard_gate_failures || status.hard_gate_failures || [];
  const perParamScores = summary?.per_param_scores || status.per_param_scores || {};
  const primaryFailure = summary?.primary_failure || status.primary_failure || 'None';

  const isRejected = decision === 'REJECT' || grade === 'F';
  const isAccepted = decision === 'ACCEPT_EXCELLENT' || decision === 'ACCEPT_GOOD';
  const { color: gradeColor, label: gradeLabel } = gradeStyle(grade);
  const decStyle = decisionStyle(decision);

  const panelBorderClass = triggered
    ? 'border-accent-teal/40 shadow-[0_0_30px_-8px_rgba(45,212,168,0.2)]'
    : isRejected
    ? 'border-accent-coral/40 shadow-[0_0_20px_-8px_rgba(240,100,73,0.2)]'
    : isAccepted
    ? 'border-accent-emerald/30 shadow-[0_0_20px_-8px_rgba(16,185,129,0.15)]'
    : 'border-oracle-border';

  return (
    <div className={clsx('w-full glass-panel mt-4 p-5 flex flex-col items-center justify-center flex-shrink-0 z-50 transition-all duration-700', panelBorderClass)}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <h2 className={clsx(
        'font-display text-lg font-bold flex items-center gap-3 uppercase tracking-[0.12em]',
        triggered ? 'text-accent-teal' : isRejected ? 'text-accent-coral' : isAccepted ? 'text-accent-emerald' : 'text-oracle-muted'
      )}>
        {triggered ? (
          <><RefreshCw className="animate-spin text-accent-teal" size={20} /> Continuous Learning Triggered</>
        ) : isRejected ? (
          <><ShieldAlert className="text-accent-coral" size={20} /> Batch Rejected — USP/ICH Spec Failure</>
        ) : isAccepted ? (
          <><ShieldCheck className="text-accent-emerald" size={20} /> Batch Accepted — Quality Verified</>
        ) : (
          <><Database className="text-oracle-muted/40" size={20} /> Batch Historian Committed</>
        )}
      </h2>

      <p className={clsx(
        'mt-2 text-sm font-body max-w-2xl text-center leading-relaxed',
        triggered ? 'text-accent-teal/60' : 'text-oracle-muted/60'
      )}>
        {triggered
          ? 'Recursive Bayesian Update written to ledger for Edge-Cloud sync. Target weights shifted to mirror Golden Signature.'
          : status.message}
      </p>

      {/* ── Decision badge ─────────────────────────────────────────────── */}
      <div className={clsx(
        'mt-3 px-5 py-2 rounded-lg border text-sm font-display font-bold tracking-widest uppercase flex items-center gap-2',
        decStyle.bg, decStyle.text, decStyle.border
      )}>
        {isAccepted ? <CheckCircle size={16} /> : isRejected ? <XCircle size={16} /> : <Activity size={16} />}
        {formatDecisionLabel(decision)}
      </div>

      {/* ── Hard gate failure list ─────────────────────────────────────── */}
      {hardGateFailures.length > 0 && (
        <div className="mt-3 w-full max-w-3xl rounded-lg bg-accent-coral/5 border border-accent-coral/20 p-3">
          <p className="text-[10px] font-mono text-accent-coral/70 uppercase tracking-wider mb-1.5 flex items-center gap-1">
            <AlertTriangle size={11} /> USP/ICH Spec Failures
          </p>
          <ul className="space-y-0.5">
            {hardGateFailures.map((f, i) => (
              <li key={i} className="text-[11px] font-mono text-accent-coral/80 flex items-start gap-1.5">
                <XCircle size={10} className="mt-[2px] flex-shrink-0" />
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Metric cards ──────────────────────────────────────────────── */}
      {summary && (
        <div className="mt-4 w-full max-w-3xl grid grid-cols-2 md:grid-cols-4 gap-3">

          {/* USP Quality Grade — from BatchQualityEvaluator */}
          <div className="glass-panel p-3 flex flex-col items-center border-oracle-border/30">
            <span className="text-[10px] font-mono text-oracle-muted uppercase tracking-wider">USP Quality Grade</span>
            <span className={clsx('text-3xl font-display font-bold mt-1', gradeColor)}>{grade}</span>
            <span className={clsx('text-[10px] font-mono mt-0.5', gradeColor)}>{gradeLabel}</span>
          </div>

          {/* Composite Score */}
          <div className="glass-panel p-3 flex flex-col items-center border-oracle-border/30">
            <span className="text-[10px] font-mono text-oracle-muted uppercase tracking-wider">Composite Score</span>
            <span className={clsx(
              'text-2xl font-display font-bold mt-1',
              composite != null && composite >= 88 ? 'text-accent-emerald'
                : composite != null && composite >= 68 ? 'text-yellow-400'
                : 'text-accent-coral'
            )}>
              {composite != null ? composite.toFixed(1) : '—'}
            </span>
            <span className="text-[10px] font-mono text-oracle-muted/50 mt-0.5">/ 100</span>
          </div>

          {/* Total Alerts */}
          <div className="glass-panel p-3 flex flex-col items-center border-oracle-border/30">
            <span className="text-[10px] font-mono text-oracle-muted uppercase tracking-wider">Process Alerts</span>
            <span className={clsx(
              'text-2xl font-display font-bold mt-1',
              summary.total_alerts > 150 ? 'text-accent-coral' : summary.total_alerts > 100 ? 'text-yellow-400' : 'text-accent-emerald'
            )}>
              {summary.total_alerts}
            </span>
            <span className="text-[10px] font-mono text-oracle-muted/50 mt-0.5">of {summary.total_rows} ticks</span>
          </div>

          {/* Primary Quality Issue */}
          <div className="glass-panel p-3 flex flex-col items-center border-oracle-border/30">
            <span className="text-[10px] font-mono text-oracle-muted uppercase tracking-wider">Primary Issue</span>
            <span className={clsx(
              'text-sm font-display font-bold mt-1 text-center leading-tight',
              primaryFailure === 'None' ? 'text-accent-emerald' : 'text-accent-coral'
            )}>
              {primaryFailure === 'None' ? (
                <span className="flex items-center gap-1"><CheckCircle size={14} /> None</span>
              ) : (
                <span className="flex items-center gap-1 flex-wrap justify-center">
                  <Activity size={14} />
                  {primaryFailure.replace(/_/g, ' ')}
                </span>
              )}
            </span>
            <span className="text-[10px] font-mono text-oracle-muted/50 mt-0.5">
              {primaryFailure !== 'None' && perParamScores[primaryFailure] != null
                ? `score: ${perParamScores[primaryFailure]}`
                : hardGatePassed === false ? 'hard gate fail' : 'all clear'}
            </span>
          </div>
        </div>
      )}

      {/* ── Per-parameter scores row ──────────────────────────────────── */}
      {Object.keys(perParamScores).length > 0 && (
        <div className="mt-3 w-full max-w-3xl">
          <p className="text-[10px] font-mono text-oracle-muted/50 uppercase tracking-wider mb-1.5">Parameter Scores (0–100)</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(perParamScores).map(([param, score]) => (
              <span
                key={param}
                className={clsx(
                  'px-2 py-0.5 rounded text-[10px] font-mono border',
                  score >= 85 ? 'bg-accent-emerald/10 text-accent-emerald/80 border-accent-emerald/20'
                    : score >= 60 ? 'bg-yellow-500/10 text-yellow-400/80 border-yellow-500/20'
                    : 'bg-accent-coral/10 text-accent-coral/80 border-accent-coral/20'
                )}
              >
                {param.replace(/_/g, ' ')}: <strong>{score}</strong>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Power + BMU stat line ──────────────────────────────────────── */}
      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-[11px] font-mono text-oracle-muted/40 justify-center">
        {(status.avg_power_kW != null || summary?.avg_power_kW != null) && (
          <span>Avg Power: <strong className="text-oracle-muted/60">{(summary?.avg_power_kW ?? status.avg_power_kW)?.toFixed(2)} kW</strong></span>
        )}
        {(status.peak_power_kW != null || summary?.peak_power_kW != null) && (
          <span>Peak Power: <strong className="text-oracle-muted/60">{(summary?.peak_power_kW ?? status.peak_power_kW)?.toFixed(2)} kW</strong></span>
        )}
        {summary && (
          <>
            <span>Avg BMU Dist: <strong className="text-oracle-muted/60">{summary.avg_bmu_distance}</strong></span>
            <span>Max BMU Dist: <strong className="text-oracle-muted/60">{summary.max_bmu_distance}</strong></span>
            <span>Process Stability: <strong className={
              summary.process_stability_pct >= 80 ? 'text-accent-emerald/70'
                : summary.process_stability_pct >= 60 ? 'text-yellow-400/70'
                : 'text-accent-coral/70'
            }>{summary.process_stability_pct}%</strong></span>
          </>
        )}
      </div>
    </div>
  );
}
