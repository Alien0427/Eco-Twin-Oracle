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
  label, value, icon: Icon, unit, valueClass = "" 
}: { 
  label: string; value: string | number; icon: any; unit?: string; valueClass?: string 
}) {
  return (
    <div className="bg-oracle-card/60 border border-oracle-border/40 rounded-xl p-3.5 transition-all duration-300 hover:border-oracle-border-light/50 group">
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon size={14} className="text-oracle-muted/70 group-hover:text-accent-teal/90 transition-colors" />
        <span className="font-mono text-xs text-oracle-muted/90 font-semibold uppercase tracking-[0.1em]">{label}</span>
      </div>
      <div className={clsx("font-mono font-bold text-xl truncate", valueClass || "text-oracle-text")}>
        {value}
        {unit && <span className="text-[11px] text-oracle-muted/30 font-body ml-1">{unit}</span>}
      </div>
    </div>
  );
}

export function MetricsGrid({ telemetry, bmuDistance, qualityMargin }: MetricsGridProps) {
  if (!telemetry) return null;

  const t = telemetry;
  const pvr = t.Power_Consumption_kW / (t.Vibration_mm_s + 0.001);

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      <MetricCard label="Temperature" value={t.Temperature_C.toFixed(1)} unit="°C" icon={Thermometer} />
      <MetricCard label="Pressure" value={t.Pressure_Bar.toFixed(2)} unit="bar" icon={Gauge} />
      <MetricCard label="Power Draw" value={t.Power_Consumption_kW.toFixed(2)} unit="kW" icon={Zap} valueClass="text-accent-teal" />
      <MetricCard label="Motor Speed" value={t.Motor_Speed_RPM} unit="RPM" icon={Settings} />
      
      <MetricCard label="Vibration" value={t.Vibration_mm_s.toFixed(3)} unit="mm/s" icon={Activity} />
      <MetricCard label="BMU Distance" value={bmuDistance.toFixed(3)} icon={Target} />
      <MetricCard label="PVR Index" value={pvr.toFixed(1)} icon={AlignCenterVertical}
        valueClass={pvr > 15.0 ? "text-accent-gold" : "text-oracle-text"} />
      <MetricCard label="Quality Margin" value={`+${qualityMargin.toFixed(1)}`} unit="%" icon={ShieldCheck}
        valueClass="text-accent-emerald" />
    </div>
  );
}
