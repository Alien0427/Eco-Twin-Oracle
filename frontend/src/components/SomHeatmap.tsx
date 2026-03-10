import clsx from 'clsx';
import { Network } from 'lucide-react';

interface SomHeatmapProps {
  bmuHistory: [number, number][];
  anomalyClass: string;
}

export function SomHeatmap({ bmuHistory, anomalyClass }: SomHeatmapProps) {
  const isAnomaly = anomalyClass && anomalyClass !== "Normal";
  
  // Create a 10x10 grid dynamically for SOM
  const gridSize = 10;
  const grid = Array.from({ length: gridSize }, () => Array(gridSize).fill(0));
  
  bmuHistory.forEach(([x, y]) => {
    if (x >= 0 && x < gridSize && y >= 0 && y < gridSize) {
      grid[y][x] += 1;
    }
  });

  const maxDensity = Math.max(1, ...grid.flat());

  return (
    <div className="glass-panel p-4 h-80 flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest text-cyan-400/80">
          Visual 2 · Kohonen LVQ Classification
        </h3>
        <Network size={16} className="text-cyan-400" />
      </div>

      <div className={clsx(
        "px-4 py-2 border rounded-full text-sm font-bold w-max mx-auto mb-4 tracking-widest uppercase transition-all duration-300",
        isAnomaly 
          ? "bg-red-900/30 text-red-400 border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.4)]"
          : "bg-green-900/30 text-green-400 border-green-500/50 shadow-[0_0_15px_rgba(34,197,94,0.4)]"
      )}>
        {anomalyClass || "INITIALIZING..."}
      </div>

      <div className="flex-1 min-h-0 flex items-center justify-center">
        <div className="grid grid-cols-10 gap-1 p-2 bg-slate-900/50 border border-slate-800 rounded-lg aspect-square h-full max-h-full">
          {grid.map((row, y) => 
            row.map((val, x) => {
              const intensity = val / maxDensity;
              
              return (
                <div 
                  key={`${x}-${y}`} 
                  className="rounded-sm w-full h-full transition-colors duration-500"
                  style={{
                    backgroundColor: val > 0 
                      ? (isAnomaly ? `rgba(239,68,68,${intensity * 0.8 + 0.2})` : `rgba(34,197,94,${intensity * 0.8 + 0.2})`)
                      : 'rgba(15, 23, 42, 0.5)',
                    border: val > 0 ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(30,30,40,0.5)'
                  }}
                  title={`[${x}, ${y}]: ${val} hits`}
                />
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
