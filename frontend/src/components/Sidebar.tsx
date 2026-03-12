import { Terminal, Database, Server, Zap } from 'lucide-react';

interface SidebarProps {
  batchId: string;
  setBatchId: (id: string) => void;
  isStreaming: boolean;
  onStart: () => void;
  onStop: () => void;
  stats: { rows: number; alerts: number };
  speed: number;
  setSpeed: (s: number) => void;
}

export function Sidebar({ batchId, setBatchId, isStreaming, onStart, onStop, stats, speed, setSpeed }: SidebarProps) {
  return (
    <div className="w-72 h-screen flex flex-col pt-5 bg-oracle-base border-r border-oracle-border/50 shadow-[2px_0_20px_rgba(0,0,0,0.4)] z-20 overflow-y-auto shrink-0">

      {/* ── Brand ─── */}
      <div className="px-5 pb-5 border-b border-oracle-border/40">
        <h1 className="font-display font-bold text-xl tracking-tight text-white flex items-center gap-2">
          <Terminal size={18} className="text-accent-teal" />
          <span className="text-gradient-brand">Eco-Twin Oracle</span>
        </h1>
        <p className="font-mono text-[13px] text-oracle-muted/90 mt-1 uppercase tracking-[0.15em]">AVEVA Hackathon · Track B</p>
      </div>

      <div className="p-5 space-y-5 flex-1">
        {/* ── Batch Selector ─── */}
        <div className="space-y-2">
          <label className="font-mono text-[13px] text-oracle-muted uppercase tracking-[0.15em] flex items-center gap-1.5">
            <Database size={12} /> Batch ID
          </label>
          <select
            value={batchId}
            onChange={(e) => setBatchId(e.target.value)}
            disabled={isStreaming}
            className="w-full bg-oracle-deep border border-oracle-border rounded-lg px-3 py-2 text-sm font-mono text-oracle-text focus:outline-none focus:border-accent-teal/50 focus:ring-1 focus:ring-accent-teal/20 disabled:opacity-40 transition-all"
          >
            {Array.from({ length: 61 }).map((_, i) => {
              const id = `T${String(i + 1).padStart(3, '0')}`;
              return <option key={id} value={id}>{id}</option>;
            })}
          </select>
        </div>

        {/* ── Sim Speed ─── */}
        <div className="space-y-2">
          <label className="font-mono text-[13px] text-oracle-muted uppercase tracking-[0.15em] flex items-center gap-1.5">
            <Zap size={12} className="text-accent-gold" /> Sim Speed
          </label>
          <select
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            disabled={isStreaming}
            className="w-full bg-oracle-deep border border-oracle-border rounded-lg px-3 py-2 text-sm font-mono text-oracle-text focus:outline-none focus:border-accent-teal/50 focus:ring-1 focus:ring-accent-teal/20 disabled:opacity-40 transition-all"
          >
            <option value={1}>1x — Full detail</option>
            <option value={2}>2x — Fast</option>
            <option value={3}>3x — Faster</option>
            <option value={4}>4x — Very fast</option>
            <option value={5}>5x — Max speed</option>
          </select>
        </div>

        {/* ── Controls ─── */}
        <div className="space-y-2">
          <button
            onClick={onStart}
            disabled={isStreaming}
            className="w-full py-2.5 rounded-lg font-display font-semibold text-xs uppercase tracking-[0.1em] transition-all duration-300 border cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed bg-accent-teal/[0.08] border-accent-teal/25 text-accent-teal hover:bg-accent-teal/[0.15] hover:border-accent-teal/50 hover:shadow-[0_0_20px_-4px_rgba(45,212,168,0.25)] flex justify-center items-center gap-2"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-accent-teal animate-pulse" />
            Start Simulation
          </button>

          <button
            onClick={onStop}
            disabled={!isStreaming}
            className="w-full py-2.5 rounded-lg font-display font-semibold text-xs uppercase tracking-[0.1em] transition-all duration-300 border cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed bg-oracle-surface border-oracle-border text-oracle-muted hover:bg-accent-coral/[0.08] hover:border-accent-coral/30 hover:text-accent-coral flex justify-center items-center gap-2"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-accent-coral/60" />
            Stop / Reset
          </button>
        </div>

        {/* ── Stats ─── */}
        <div className="pt-4 border-t border-oracle-border/30">
          <h2 className="font-mono text-[10px] text-oracle-muted/90 uppercase tracking-[0.15em] mb-3">Session</h2>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-oracle-deep border border-oracle-border/60 rounded-lg p-2.5 text-center">
              <div className="text-lg font-mono font-bold text-accent-teal">{stats.rows}</div>
              <div className="font-mono text-[9px] text-oracle-muted/90 uppercase mt-0.5">Rows</div>
            </div>
            <div className="bg-oracle-deep border border-oracle-border/60 rounded-lg p-2.5 text-center">
              <div className="text-lg font-mono font-bold text-accent-gold">{stats.alerts}</div>
              <div className="font-mono text-[9px] text-oracle-muted/90 uppercase mt-0.5">Alerts</div>
            </div>
          </div>
        </div>

        {/* ── Compliance ─── */}
        <details className="group border border-oracle-border/30 rounded-lg bg-oracle-surface/30 transition-colors hover:border-oracle-border/50">
          <summary className="flex items-center cursor-pointer p-3 select-none list-none text-xs font-display font-medium text-oracle-muted hover:text-accent-teal transition-colors">
            <Server size={14} className="mr-2 text-accent-teal/50" />
            Enterprise Architecture
            <span className="ml-auto transition-transform duration-200 group-open:rotate-180 text-oracle-muted/30">▾</span>
          </summary>
          <div className="p-3 pt-0 text-[11px] font-body text-oracle-muted/60 space-y-3 leading-relaxed">
            <div>
              <b className="text-accent-teal/70 text-[10px] font-display uppercase tracking-wider">USP Regulatory Baseline</b>
              <p className="mt-0.5">Quality Margin calculated against <span className="font-mono text-oracle-text">Q = 85.0%</span> acceptance criteria.</p>
            </div>
            <div>
              <b className="text-accent-teal/70 text-[10px] font-display uppercase tracking-wider">Production Ingestion</b>
              <p className="mt-0.5">WebSocket simulation. OPC-UA gateway adapter ready for live PLC.</p>
            </div>
            <div>
              <b className="text-accent-teal/70 text-[10px] font-display uppercase tracking-wider">Edge-Cloud Hybrid</b>
              <p className="mt-0.5">Local edge inference. SOM weights updated via Cloud-Sync.</p>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}
