import clsx from 'clsx';
import { Thermometer, Gauge, Zap, Settings, Activity, Target, AlignCenterVertical, ShieldCheck } from 'lucide-react';

interface Telemetry {
  Temperature_C: number;
  Pressure_Bar: number;
  Power_Consumption_kW: number;
  Motor_Speed_RPM: number;
  Vibration_mm_s: number;
}

interface MetricsGridProps {
  telemetry: Telemetry | null;
  bmuDistance: number;
  qualityMargin: number;
}

function MetricCard({ 
  label, value, icon: Icon, unit, highlight = false, valueClass = "" 
}: { 
  label: string; value: string | number; icon: any; unit?: string; highlight?: boolean; valueClass?: string 
}) {
  return (
    <div className={clsx(
      "bg-[#0F1A2E] border border-slate-800 rounded-xl p-4 transition-all duration-300",
      highlight ? "border-cyan-500/50 shadow-[0_0_15px_rgba(0,212,255,0.15)]" : "hover:border-slate-600"
    )}>
      <div className="flex items-center gap-2 mb-2 text-slate-400 text-xs uppercase tracking-[0.1em] font-medium">
        <Icon size={14} className={highlight ? "text-cyan-400" : ""} />
        {label}
      </div>
      <div className={clsx("font-mono font-bold text-2xl truncate", valueClass || "text-slate-100")}>
        {value} {unit && <span className="text-sm text-slate-500 font-sans ml-1">{unit}</span>}
      </div>
    </div>
  );
}

export function MetricsGrid({ telemetry, bmuDistance, qualityMargin }: MetricsGridProps) {
  if (!telemetry) return null;

  const t = telemetry;
  const pvr = t.Power_Consumption_kW / (t.Vibration_mm_s + 0.001);
  const pvrHigh = pvr > 15.0;
  const qmHigh = qualityMargin >= 5.0;

  return (
    <div className="grid grid-cols-4 gap-4 mb-4">
      <MetricCard label="Temperature" value={t.Temperature_C.toFixed(1)} unit="°C" icon={Thermometer} />
      <MetricCard label="Pressure" value={t.Pressure_Bar.toFixed(2)} unit="bar" icon={Gauge} />
      <MetricCard label="Power" value={t.Power_Consumption_kW.toFixed(3)} unit="kW" icon={Zap} valueClass="text-cyan-400" highlight />
      <MetricCard label="Motor Speed" value={t.Motor_Speed_RPM} unit="RPM" icon={Settings} />
      
      <MetricCard label="Vibration" value={t.Vibration_mm_s.toFixed(3)} unit="mm/s" icon={Activity} />
      <MetricCard label="BMU Distance" value={bmuDistance.toFixed(3)} icon={Target} />
      <MetricCard 
        label="PVR Index" 
        value={pvr.toFixed(1)} 
        icon={AlignCenterVertical} 
        valueClass={pvrHigh ? "text-amber-400" : "text-slate-100"}
        highlight={pvrHigh}
      />
      <MetricCard 
        label="Excess Quality Margin" 
        value={`+${qualityMargin.toFixed(1)}`}
        unit="%"
        icon={ShieldCheck} 
        valueClass={qmHigh ? "text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.8)]" : "text-slate-100"}
      />
    </div>
  );
}
