import clsx from 'clsx';
import { Network } from 'lucide-react';

interface SomHeatmapProps {
  bmuHistory: [number, number][];
  anomalyClass: string;
  anomalyHistory?: Record<string, number>;
}

export function SomHeatmap({ bmuHistory, anomalyClass, anomalyHistory }: SomHeatmapProps) {
  // Determine overall session health from anomaly history
  const totalTicks = anomalyHistory ? Object.values(anomalyHistory).reduce((a, b) => a + b, 0) : 0;
  const normalCount = anomalyHistory?.['Normal'] || 0;
  const normalPct = totalTicks > 0 ? (normalCount / totalTicks * 100) : 100;
  
  // Find dominant non-Normal class for display
  const nonNormalEntries = anomalyHistory 
    ? Object.entries(anomalyHistory).filter(([k]) => k !== 'Normal').sort((a, b) => b[1] - a[1])
    : [];
  const dominantAnomaly = nonNormalEntries.length > 0 ? nonNormalEntries[0][0] : null;
  const anomalyCount = nonNormalEntries.reduce((sum, [, v]) => sum + v, 0);
  
  // Use real-time for current tick, but show session summary badge
  const currentIsAnomaly = anomalyClass && anomalyClass !== "Normal";
  const sessionHasIssues = normalPct < 80 && totalTicks > 10;
  
  const gridSize = 10;
  const grid = Array.from({ length: gridSize }, () => Array(gridSize).fill(0));
  
  bmuHistory.forEach(([x, y]) => {
    if (x >= 0 && x < gridSize && y >= 0 && y < gridSize) grid[y][x] += 1;
  });

  const maxDensity = Math.max(1, ...grid.flat());

  // Badge display: show session summary when complete, real-time during stream
  const showSessionSummary = totalTicks > 10;
  let badgeText = anomalyClass || "INITIALIZING...";
  let badgeIsAnomaly = currentIsAnomaly;
  
  if (showSessionSummary && !currentIsAnomaly && sessionHasIssues && dominantAnomaly) {
    // If last tick is Normal but session had issues, show the dominant issue
    badgeText = dominantAnomaly;
    badgeIsAnomaly = true;
  }

  return (
    <div className="glass-panel p-4 h-80 flex flex-col">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-mono text-[10px] text-oracle-muted uppercase tracking-[0.15em]">
          Kohonen LVQ Classification
        </h3>
        <Network size={14} className="text-accent-teal/40" />
      </div>

      {/* Main badge */}
      <div className={clsx(
        "px-3 py-1.5 border rounded-lg text-xs font-display font-bold w-max mx-auto mb-1 tracking-[0.1em] uppercase transition-all",
        badgeIsAnomaly 
          ? "bg-accent-coral/10 text-accent-coral border-accent-coral/30 shadow-[0_0_12px_-2px_rgba(240,100,73,0.3)]"
          : "bg-accent-emerald/10 text-accent-emerald border-accent-emerald/30 shadow-[0_0_12px_-2px_rgba(16,185,129,0.3)]"
      )}>
        {badgeText}
      </div>
      
      {/* Session stats mini-bar */}
      {totalTicks > 5 && (
        <div className="flex justify-center gap-3 mb-2 text-[9px] font-mono">
          <span className="text-accent-emerald/60">{normalPct.toFixed(0)}% normal</span>
          {anomalyCount > 0 && (
            <span className="text-accent-coral/60">{anomalyCount} anomalies</span>
          )}
        </div>
      )}

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
                      ? (sessionHasIssues 
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
