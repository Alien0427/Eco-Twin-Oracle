import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine 
} from 'recharts';

interface TimeSeriesData {
  time: number;
  actual_kw: number;
  ghost_kw: number;
}

interface PowerChartProps {
  data: TimeSeriesData[];
}

export function PowerChart({ data }: PowerChartProps) {
  return (
    <div className="glass-panel p-4 h-80 flex flex-col">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-mono text-[10px] text-oracle-muted uppercase tracking-[0.15em]">
          Golden Signature Power Trace
        </h3>
        <div className="flex items-center gap-4 font-mono text-[9px] uppercase text-oracle-muted/40 tracking-wider">
          <span className="flex items-center gap-1.5">
            <div className="w-4 h-[2px] bg-accent-ice rounded-full opacity-60" /> Target
          </span>
          <span className="flex items-center gap-1.5">
            <div className="w-4 h-[2px] bg-accent-teal rounded-full shadow-[0_0_6px_rgba(45,212,168,0.5)]" /> Live
          </span>
          <span className="flex items-center gap-1.5">
            <div className="w-4 h-[1px] bg-accent-coral/60 rounded-full" /> Phantom
          </span>
        </div>
      </div>
      
      <div className="flex-1 w-full min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1A2D52" strokeOpacity={0.4} vertical={false} />
            <XAxis 
              dataKey="time" stroke="#1A2D52"
              tick={{ fontSize: 9, fill: '#5B7BA5', fontFamily: 'IBM Plex Mono' }} 
              tickFormatter={(val) => val.toFixed(0)} 
            />
            <YAxis 
              stroke="#1A2D52" domain={[0, 45]}
              tick={{ fontSize: 9, fill: '#5B7BA5', fontFamily: 'IBM Plex Mono' }} 
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#0F1A33', border: '1px solid #1A2D52', borderRadius: '8px', 
                fontSize: '11px', fontFamily: 'IBM Plex Mono', color: '#C8DAF0'
              }}
            />
            <ReferenceLine y={2.5} stroke="#F06449" strokeDasharray="6 3" strokeWidth={1} strokeOpacity={0.5} />
            <Line type="monotone" dataKey="ghost_kw" stroke="#7DD3FC" strokeWidth={1.2} 
              strokeDasharray="6 4" dot={false} isAnimationActive={false} strokeOpacity={0.5} />
            <Line type="monotone" dataKey="actual_kw" stroke="#2DD4A8" strokeWidth={2}
              dot={false} isAnimationActive={false}
              activeDot={{ r: 3, fill: '#2DD4A8', stroke: '#0A1128', strokeWidth: 2 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
