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
    <div className="glass-panel p-4 mb-4">
      <div className="flex items-center gap-2 mb-3">
        <Activity size={16} className="text-cyan-400" />
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest text-cyan-400/80">DFA Phase Lock</h2>
      </div>
      
      <div className="flex flex-wrap items-center gap-2">
        {DFA_PHASES.map((phase, i) => {
          const isActive = i === safeIndex;
          const isPast = i < safeIndex;
          
          return (
            <div key={phase} className="flex items-center">
              <span 
                className={clsx(
                  "px-3 py-1 text-xs font-bold rounded-md uppercase tracking-wider transition-all duration-300",
                  {
                    "bg-cyan-900/40 text-cyan-400 border border-cyan-400/50 shadow-[0_0_10px_rgba(34,211,238,0.3)] scale-105": isActive,
                    "bg-green-900/20 text-green-400 border border-green-500/30": isPast && !isActive,
                    "bg-slate-800/50 text-slate-500 border border-slate-700/50": !isActive && !isPast
                  }
                )}
              >
                {i + 1}. {phase}
              </span>
              {i < DFA_PHASES.length - 1 && (
                <span className="text-slate-600 text-xs font-bold ml-2">→</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
