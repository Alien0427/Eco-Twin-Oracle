import clsx from 'clsx';
import { Activity } from 'lucide-react';

const DFA_PHASES = [
  "PREPARATION", "GRANULATION", "DRYING", "MILLING", 
  "BLENDING", "COMPRESSION", "COATING", "QUALITY_TESTING"
];

interface PhaseStepperProps {
  currentPhase: string;
}

export function PhaseStepper({ currentPhase }: PhaseStepperProps) {
  const currentIndex = DFA_PHASES.indexOf(currentPhase);
  const safeIndex = currentIndex === -1 ? 0 : currentIndex;

  return (
    <div className="glass-panel p-3 mb-4">
      <div className="flex items-center gap-2 mb-2.5">
        <Activity size={14} className="text-accent-teal" />
        <h2 className="font-mono text-[10px] text-oracle-muted uppercase tracking-[0.15em]">DFA Phase Lock</h2>
      </div>
      
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
        {DFA_PHASES.map((phase, i) => {
          const isActive = i === safeIndex;
          const isPast = i < safeIndex;
          
          return (
            <div key={phase} className="flex items-center shrink-0">
              <span 
                className={clsx(
                  "px-2.5 py-1 text-[10px] font-display font-semibold rounded-md uppercase tracking-wider transition-all duration-300",
                  {
                    "bg-accent-teal/15 text-accent-teal border border-accent-teal/40 shadow-[0_0_12px_-2px_rgba(45,212,168,0.3)]": isActive,
                    "bg-accent-emerald/8 text-accent-emerald/60 border border-accent-emerald/20": isPast && !isActive,
                    "bg-oracle-surface/40 text-oracle-muted/40 border border-oracle-border/30": !isActive && !isPast
                  }
                )}
              >
                {phase.replace('_', ' ')}
              </span>
              {i < DFA_PHASES.length - 1 && (
                <span className={clsx("mx-1 text-[8px]", isPast ? "text-accent-emerald/30" : "text-oracle-border")}>→</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
