import { Terminal, Database, Server } from 'lucide-react';

interface SidebarProps {
  batchId: string;
  setBatchId: (id: string) => void;
  isStreaming: boolean;
  onStart: () => void;
  onStop: () => void;
  stats: { rows: number; alerts: number };
}

export function Sidebar({ batchId, setBatchId, isStreaming, onStart, onStop, stats }: SidebarProps) {
  return (
    <div className="w-80 h-screen glass-panel rounded-none border-y-0 border-l-0 border-slate-700/50 flex flex-col pt-6 bg-slate-900 shadow-[2px_0_15px_rgba(0,0,0,0.5)] z-20 overflow-y-auto shrink-0">
      <div className="px-6 pb-6 border-b border-slate-800">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-cyan-400 to-green-400 bg-clip-text text-transparent flex items-center gap-2">
          <Terminal className="text-cyan-400" /> ECO-TWIN ORACLE
        </h1>
        <p className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-semibold">AVEVA Hackathon · Track B</p>
      </div>

      <div className="p-6 space-y-6 flex-1">
        <div className="space-y-3">
          <label className="text-xs text-slate-400 font-semibold uppercase tracking-wider flex items-center gap-2">
            <Database size={14} /> Select Batch ID
          </label>
          <select 
            value={batchId}
            onChange={(e) => setBatchId(e.target.value)}
            disabled={isStreaming}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 disabled:opacity-50 transition-colors"
          >
            {Array.from({ length: 61 }).map((_, i) => {
              const id = `T${String(i + 1).padStart(3, '0')}`;
              return <option key={id} value={id}>{id}</option>;
            })}
          </select>
        </div>

        <div className="space-y-3">
          <button 
            onClick={onStart}
            disabled={isStreaming}
            className="w-full bg-slate-800 hover:bg-slate-700 hover:border-green-400/50 border border-slate-700 text-slate-200 py-3 rounded-lg font-medium transition-all duration-300 disabled:opacity-50 disabled:hover:border-slate-700 hover:shadow-[0_0_15px_rgba(34,197,94,0.2)] flex justify-center items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            Start Simulation
          </button>
          
          <button 
            onClick={onStop}
            disabled={!isStreaming}
            className="w-full bg-slate-800 hover:bg-slate-700 hover:border-red-400/50 border border-slate-700 text-slate-200 py-3 rounded-lg font-medium transition-all duration-300 disabled:opacity-50 disabled:hover:border-slate-700 hover:shadow-[0_0_15px_rgba(239,68,68,0.2)] flex justify-center items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
            Stop / Reset
          </button>
        </div>

        <div className="pt-4 border-t border-slate-800">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Session Stats</h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-center">
              <div className="text-xl font-bold font-mono text-cyan-400">{stats.rows}</div>
              <div className="text-[10px] text-slate-500 uppercase mt-1">Rows Processed</div>
            </div>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-center">
              <div className="text-xl font-bold font-mono text-amber-400">{stats.alerts}</div>
              <div className="text-[10px] text-slate-500 uppercase mt-1">Alerts</div>
            </div>
          </div>
        </div>

        <details className="mt-4 group border border-slate-700/50 rounded-lg bg-slate-900/50">
          <summary className="flex items-center cursor-pointer p-4 select-none list-none text-sm font-semibold text-slate-300 hover:text-cyan-400 transition-colors">
            <Server size={16} className="mr-2 text-cyan-500" />
            Enterprise Architecture & Compliance
            <span className="ml-auto transition group-open:rotate-180">▾</span>
          </summary>
          <div className="p-4 pt-0 text-xs text-slate-400 space-y-4 leading-relaxed">
            <div>
              <b className="text-cyan-400 block mb-1">1. USP Regulatory Baseline:</b>
              Excess Quality Margin is strictly calculated against <b>USP Acceptance Criteria (Q = 85.0%)</b> for immediate-release solid dosage forms. No arbitrary thresholds.
            </div>
            <div>
              <b className="text-cyan-400 block mb-1">2. Production Ingestion:</b>
              Streaming via simulated WebSockets for demo purposes. Production-ready <code className="bg-slate-800 px-1 py-0.5 rounded text-slate-300">opc_ua_mqtt_gateway.py</code> adapter is configured for live PLC integration.
            </div>
            <div>
              <b className="text-cyan-400 block mb-1">3. Edge-Cloud Hybrid:</b>
              Inference runs on local Edge. Kohonen SOM weights are updated asynchronously via Cloud-Sync to prevent catastrophic forgetting.
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}
