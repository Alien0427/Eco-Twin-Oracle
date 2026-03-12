import { useState, useEffect, useRef } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { Loader2 } from 'lucide-react';
import { LandingPage } from './components/LandingPage';
import { Sidebar } from './components/Sidebar';
import { PhaseStepper } from './components/PhaseStepper';
import { MetricsGrid } from './components/MetricsGrid';
import { PowerChart } from './components/PowerChart';
import { SomHeatmap } from './components/SomHeatmap';
import { XaiGraph } from './components/XaiGraph';
import { LedgerAlert } from './components/LedgerAlert';

export default function App() {
  const [isSystemActive, setIsSystemActive] = useState(false);
  const [batchId, setBatchId] = useState('T060');
  const [isStreaming, setIsStreaming] = useState(false);
  const [shouldConnect, setShouldConnect] = useState(false);
  
  const [telemetry, setTelemetry] = useState(null);
  const [dfaState, setDfaState] = useState('PREPARATION');
  const [prescription, setPrescription] = useState<any>(null);
  const [xaiData, setXaiData] = useState(null);
  const [qualityMargin, setQualityMargin] = useState(0);
  const [bmuDistance, setBmuDistance] = useState(0);
  
  const [timeSeries, setTimeSeries] = useState<any[]>([]);
  const [bmuHistory, setBmuHistory] = useState<[number, number][]>([]);
  const [stats, setStats] = useState({ rows: 0, alerts: 0 });
  const [ledgerStatus, setLedgerStatus] = useState(null);
  const [batchSummary, setBatchSummary] = useState<any>(null);
  const [anomalyHistory, setAnomalyHistory] = useState<Record<string, number>>({});
  const wakeAbortRef = useRef<AbortController | null>(null);
  // Stable ref so the shouldReconnect callback always sees the latest value
  const shouldConnectRef = useRef(false);
  shouldConnectRef.current = shouldConnect;

  // Dynamic backend URL: uses env var in production, localhost for dev
  const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
  const wsProtocol = backendUrl.startsWith('https') ? 'wss' : 'ws';
  const wsHost = backendUrl.replace(/^https?:\/\//, '');
  const socketUrl = shouldConnect ? `${wsProtocol}://${wsHost}/ws/live-batch/${batchId}` : null;
  
  const { lastMessage, readyState } = useWebSocket(socketUrl, {
    // Retry up to 5 times (2 s apart) when mobile carriers/proxies drop the connection
    shouldReconnect: () => shouldConnectRef.current,
    reconnectAttempts: 5,
    reconnectInterval: 2000,
  });

  const handleStart = async () => {
    // Reset state
    setTimeSeries([]);
    setBmuHistory([]);
    setStats({ rows: 0, alerts: 0 });
    setLedgerStatus(null);
    setBatchSummary(null);
    setAnomalyHistory({});
    setTelemetry(null);
    setPrescription(null);
    setXaiData(null);
    // Mark as streaming immediately (disables Start button, shows waking-up state)
    setIsStreaming(true);
    setShouldConnect(false);

    // Wake up the Render backend before opening WebSocket.
    // Render free tier sleeps after inactivity; mobile browsers time out WebSocket
    // connections in ~5-10s while Render can take ~50s to cold-start.
    // An HTTP request waits patiently for the server to wake up.
    const ctrl = new AbortController();
    wakeAbortRef.current = ctrl;
    try {
      const tid = setTimeout(() => ctrl.abort(), 65000);
      await fetch(`${backendUrl}/docs`, { mode: 'no-cors', signal: ctrl.signal });
      clearTimeout(tid);
    } catch (_) {
      // Timed out or aborted — attempt WebSocket anyway
    }
    wakeAbortRef.current = null;

    // If user hit Stop during wakeup, abort signal is set — don't open socket
    if (!ctrl.signal.aborted) {
      setShouldConnect(true);
    }
  };

  const handleStop = () => {
    // Cancel any in-progress wakeup HTTP request
    wakeAbortRef.current?.abort();
    wakeAbortRef.current = null;
    setIsStreaming(false);
    setShouldConnect(false);
  };

  useEffect(() => {
    if (lastMessage !== null) {
      const data = JSON.parse(lastMessage.data);
      
      if (data.event === "batch_complete") {
        setIsStreaming(false);
        setShouldConnect(false);
        setLedgerStatus(data.ledger_status);
        setBatchSummary(data.batch_summary || null);
        return;
      }
      
      if (data.event === "telemetry" || data.event === "phantom_energy" || data.event === "anomaly_detected" || data.event === "process_alert") {
        const t = data.telemetry;
        const p = data.prescription;
        
        setTelemetry(t);
        setDfaState(data.dfa_state);
        setPrescription(p);
        setXaiData(data.xai_data);
        setQualityMargin(data.quality_margin);
        
        if (p?.bmu_distance !== undefined) {
          setBmuDistance(p.bmu_distance);
        }

        if (p?.bmu_index) {
          setBmuHistory(prev => [...prev, [p.bmu_index[0], p.bmu_index[1]]]);
        }
        
        const recKw = p?.parameter_recommendations?.Power_Consumption_kW || 0;
        setTimeSeries(prev => [...prev, {
          time: t.Time_Minutes,
          actual_kw: t.Power_Consumption_kW,
          ghost_kw: t.Power_Consumption_kW + recKw
        }]);
        
        // Count alerts from ALL sources: phantom, anomaly, PVR, arbitrage
        const alertCount = (data.has_phantom ? 1 : 0)
          + (data.has_anomaly ? 1 : 0)
          + (data.has_pvr_alert ? 1 : 0)
          + (data.has_arbitrage_alert ? 1 : 0);
        
        setStats(prev => ({
          rows: prev.rows + 1,
          alerts: prev.alerts + alertCount
        }));
        
        // Track anomaly class distribution
        const cls = p?.anomaly_class || 'Normal';
        setAnomalyHistory(prev => ({ ...prev, [cls]: (prev[cls] || 0) + 1 }));
      }
    }
  }, [lastMessage, setTimeSeries, setBmuHistory, setStats, setTelemetry, setDfaState, setPrescription, setXaiData, setQualityMargin, setIsStreaming, setShouldConnect, setLedgerStatus, setBatchSummary, setAnomalyHistory]);

  useEffect(() => {
    // Only reset UI when the socket closes because the user hit Stop.
    // If shouldConnect is still true the close was unexpected (mobile network
    // drop, carrier proxy, Render busy) — leave isStreaming=true so the
    // shouldReconnect callback above gets to retry.
    if (readyState === ReadyState.CLOSED && !shouldConnect) {
      setIsStreaming(false);
    }
  }, [readyState, shouldConnect]);

  // Phase states for the mobile button label
  const isWakingUp  = isStreaming && !shouldConnect;
  const isConnecting = !isWakingUp && readyState === ReadyState.CONNECTING;
  const isRetrying   = !isWakingUp && shouldConnect && readyState === ReadyState.CLOSED;

  if (!isSystemActive) {
    return <LandingPage onEnter={() => setIsSystemActive(true)} />;
  }

  return (
    <div className="flex flex-col md:flex-row h-screen w-screen overflow-hidden bg-oracle-deep text-oracle-text">

      {/* ── Mobile-only top control bar ── */}
      <div className="flex md:hidden items-center gap-2 px-3 py-2.5 border-b border-oracle-border/50 bg-oracle-base shrink-0 z-20">
        <div className="flex flex-col min-w-0 shrink-0">
          <span className="font-display text-sm font-bold text-accent-teal">Eco-Twin</span>
          <span className="font-mono text-[9px] text-oracle-muted/40 uppercase tracking-wider">Oracle</span>
        </div>
        <select
          value={batchId}
          onChange={e => setBatchId(e.target.value)}
          disabled={isStreaming}
          className="flex-1 mx-2 bg-oracle-deep border border-oracle-border rounded px-2 py-1.5 text-xs font-mono text-oracle-text focus:outline-none focus:border-accent-teal/50 disabled:opacity-40 transition-all"
        >
          {Array.from({ length: 61 }).map((_, i) => {
            const id = `T${String(i + 1).padStart(3, '0')}`;
            return <option key={id} value={id}>{id}</option>;
          })}
        </select>
        <button
          onClick={isStreaming ? handleStop : handleStart}
          className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-display font-semibold uppercase tracking-wider border transition-all ${
            isStreaming
              ? 'bg-accent-coral/10 border-accent-coral/30 text-accent-coral hover:bg-accent-coral/20'
              : 'bg-accent-teal/10 border-accent-teal/30 text-accent-teal hover:bg-accent-teal/20'
          }`}
        >
          {isWakingUp
            ? <><Loader2 size={12} className="animate-spin" />Waking up…</>
            : isRetrying
            ? <><Loader2 size={12} className="animate-spin" />Retrying…</>
            : isConnecting
            ? <><Loader2 size={12} className="animate-spin" />Connecting…</>
            : isStreaming ? 'Stop' : 'Start'
          }
        </button>
      </div>

      {/* ── Desktop sidebar — hidden on mobile ── */}
      <div className="hidden md:flex">
        <Sidebar
          batchId={batchId}
          setBatchId={setBatchId}
          isStreaming={isStreaming}
          onStart={handleStart}
          onStop={handleStop}
          stats={stats}
        />
      </div>

      <div className="flex-1 flex flex-col p-3 md:p-6 overflow-y-auto min-h-0">
        <PhaseStepper currentPhase={dfaState} />
        <MetricsGrid telemetry={telemetry} bmuDistance={bmuDistance} qualityMargin={qualityMargin} />
        
        <div className="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-4 flex-1 mb-4 h-full min-h-0 min-w-0">
          <div className="h-full flex flex-col">
            <PowerChart data={timeSeries} />
          </div>
          <div className="h-full flex flex-col">
            <SomHeatmap bmuHistory={bmuHistory} anomalyClass={prescription?.anomaly_class || ''} anomalyHistory={anomalyHistory} />
          </div>
          <div className="h-full flex flex-col xl:col-span-2 2xl:col-span-1">
            <XaiGraph xaiData={xaiData} />
          </div>
        </div>
        
        {ledgerStatus && <LedgerAlert status={ledgerStatus} summary={batchSummary} />}
      </div>
    </div>
  );
}
