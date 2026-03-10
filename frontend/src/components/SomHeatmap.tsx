import clsx from 'clsx';
import { Network } from 'lucide-react';

interface SomHeatmapProps {
  bmuHistory: [number, number][];
  anomalyClass: string;
}

export function SomHeatmap({ bmuHistory, anomalyClass }: SomHeatmapProps) {
  const isAnomaly = anomalyClass && anomalyClass !== "Normal";
  const gridSize = 10;
  const grid = Array.from({ length: gridSize }, () => Array(gridSize).fill(0));
  
  bmuHistory.forEach(([x, y]) => {
    if (x >= 0 && x < gridSize && y >= 0 && y < gridSize) grid[y][x] += 1;
  });

  const maxDensity = Math.max(1, ...grid.flat());

  return (
    <div className="glass-panel p-4 h-80 flex flex-col">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-mono text-[10px] text-oracle-muted uppercase tracking-[0.15em]">
          Kohonen LVQ Classification
        </h3>
        <Network size={14} className="text-accent-teal/40" />
      </div>

      <div className={clsx(
        "px-3 py-1.5 border rounded-lg text-xs font-display font-bold w-max mx-auto mb-3 tracking-[0.1em] uppercase transition-all",
        isAnomaly 
          ? "bg-accent-coral/10 text-accent-coral border-accent-coral/30 shadow-[0_0_12px_-2px_rgba(240,100,73,0.3)]"
          : "bg-accent-emerald/10 text-accent-emerald border-accent-emerald/30 shadow-[0_0_12px_-2px_rgba(16,185,129,0.3)]"
      )}>
        {anomalyClass || "INITIALIZING..."}
      </div>

      <div className="flex-1 min-h-0 flex items-center justify-center">
        <div className="grid grid-cols-10 gap-[3px] p-2 bg-oracle-deep/50 border border-oracle-border/30 rounded-lg aspect-square h-full max-h-full">
          {grid.map((row, y) => 
            row.map((val, x) => {
              const intensity = val / maxDensity;
              return (
                <div 
                  key={`${x}-${y}`} 
                  className="rounded-[2px] w-full h-full transition-colors duration-500"
                  style={{
                    backgroundColor: val > 0 
                      ? (isAnomaly 
                          ? `rgba(240,100,73,${intensity * 0.75 + 0.15})` 
                          : `rgba(45,212,168,${intensity * 0.75 + 0.15})`)
                      : 'rgba(10, 17, 40, 0.4)',
                    border: val > 0 ? '1px solid rgba(255,255,255,0.06)' : '1px solid rgba(26,45,82,0.25)'
                  }}
                  title={`[${x}, ${y}]: ${val}`}
                />
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
