import { useState, useEffect } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
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

  // Dynamic backend URL: uses env var in production, localhost for dev
  const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
  const wsProtocol = backendUrl.startsWith('https') ? 'wss' : 'ws';
  const wsHost = backendUrl.replace(/^https?:\/\//, '');
  const socketUrl = shouldConnect ? `${wsProtocol}://${wsHost}/ws/live-batch/${batchId}` : null;
  
  const { lastMessage, readyState } = useWebSocket(socketUrl, {
    shouldReconnect: () => false,
  });

  const handleStart = () => {
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
    setIsStreaming(true);
    setShouldConnect(true);
  };

  const handleStop = () => {
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
    if (readyState === ReadyState.CLOSED) {
      setIsStreaming(false);
      setShouldConnect(false);
    }
  }, [readyState]);

  if (!isSystemActive) {
    return <LandingPage onEnter={() => setIsSystemActive(true)} />;
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-oracle-deep text-oracle-text">
      <Sidebar 
        batchId={batchId}
        setBatchId={setBatchId}
        isStreaming={isStreaming}
        onStart={handleStart}
        onStop={handleStop}
        stats={stats}
      />

      <div className="flex-1 flex flex-col p-6 overflow-y-auto">
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
