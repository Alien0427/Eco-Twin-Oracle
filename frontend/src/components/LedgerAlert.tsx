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

  return (
    <div className={clsx(
      "w-full glass-panel mt-4 border-2 p-6 flex flex-col items-center justify-center transition-all duration-700 animate-in slide-in-from-bottom flex-shrink-0 z-50",
      status.trigger_som_retraining 
        ? "bg-[#0A1F0D] border-green-500 shadow-[0_0_30px_rgba(34,197,94,0.3)] shadow-green-500/50" 
        : "bg-slate-900 border-slate-700 shadow-md"
    )}>
      <h2 className={clsx(
        "text-2xl font-bold flex items-center gap-3 uppercase tracking-[0.15em] whitespace-nowrap",
        status.trigger_som_retraining ? "text-green-400 drop-shadow-[0_0_8px_rgba(34,197,94,0.8)] animate-pulse" : "text-slate-100"
      )}>
        {status.trigger_som_retraining ? (
          <><RefreshCw className="animate-spin text-green-400" size={28} /> CONTINUOUS LEARNING TRIGGERED</>
        ) : (
          <><Database className="text-slate-500" size={28} /> BATCH HISTORIAN COMMITTED</>
        )}
      </h2>
      <p className={clsx(
        "mt-3 text-lg font-mono font-medium max-w-3xl text-center",
        status.trigger_som_retraining ? "text-green-300" : "text-slate-400"
      )}>
        {status.trigger_som_retraining 
          ? "Recursive Bayesian Update written to ledger for Edge-Cloud sync. Target weights shifted to mirror Golden Signature."
          : "Performance recorded. Batch energy draw aligned nominally. No architecture update triggered."}
      </p>
    </div>
  );
}
