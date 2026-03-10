import clsx from 'clsx';
import { RefreshCw, Database } from 'lucide-react';

interface LedgerStatus {
  trigger_som_retraining: boolean;
  message: string;
}

interface LedgerAlertProps {
  status: LedgerStatus | null;
}

export function LedgerAlert({ status }: LedgerAlertProps) {
  if (!status) return null;
  const triggered = status.trigger_som_retraining;

  return (
    <div className={clsx(
      "w-full glass-panel mt-4 p-5 flex flex-col items-center justify-center flex-shrink-0 z-50 transition-all duration-700",
      triggered 
        ? "border-accent-teal/40 shadow-[0_0_30px_-8px_rgba(45,212,168,0.2)]" 
        : "border-oracle-border"
    )}>
      <h2 className={clsx(
        "font-display text-lg font-bold flex items-center gap-3 uppercase tracking-[0.12em]",
        triggered ? "text-accent-teal" : "text-oracle-muted"
      )}>
        {triggered ? (
          <><RefreshCw className="animate-spin text-accent-teal" size={20} /> Continuous Learning Triggered</>
        ) : (
          <><Database className="text-oracle-muted/40" size={20} /> Batch Historian Committed</>
        )}
      </h2>
      <p className={clsx(
        "mt-2 text-sm font-body max-w-2xl text-center leading-relaxed",
        triggered ? "text-accent-teal/60" : "text-oracle-muted/40"
      )}>
        {triggered 
          ? "Recursive Bayesian Update written to ledger for Edge-Cloud sync. Target weights shifted to mirror Golden Signature."
          : "Performance recorded. Batch energy draw aligned nominally."}
      </p>
    </div>
  );
}
