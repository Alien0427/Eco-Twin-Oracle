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
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest text-cyan-400/80">
          Visual 1 · Golden Signature Power Trace
        </h3>
        <div className="flex items-center gap-4 text-[10px] uppercase font-mono text-slate-400">
          <span className="flex items-center gap-1">
            <div className="w-3 h-1 bg-cyan-500 border-dashed"></div> Golden Target
          </span>
          <span className="flex items-center gap-1">
            <div className="w-3 h-1 bg-green-500 shadow-[0_0_8px_#22c55e]"></div> Live Draw
          </span>
          <span className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-red-500 border-dashed"></div> Phantom Threshold
          </span>
        </div>
      </div>
      
      <div className="flex-1 w-full min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis 
              dataKey="time" 
              stroke="#64748b" 
              tick={{ fontSize: 10, fill: '#64748b' }} 
              tickFormatter={(val) => val.toFixed(0)} 
            />
            <YAxis 
              stroke="#64748b" 
              domain={[0, 45]} 
              tick={{ fontSize: 10, fill: '#64748b' }} 
            />
            <Tooltip 
              contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }}
              itemStyle={{ fontFamily: 'monospace' }}
            />
            
            <ReferenceLine y={2.5} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1} />
            
            {/* Ghost KW (Golden Target) */}
            <Line 
              type="monotone" 
              dataKey="ghost_kw" 
              stroke="#06b6d4" 
              strokeWidth={1.5} 
              strokeDasharray="5 5"
              dot={false}
              isAnimationActive={false}
            />
            
            {/* Actual KW (Live Draw) */}
            <Line 
              type="monotone" 
              dataKey="actual_kw" 
              stroke="#22c55e" 
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#22c55e', stroke: '#0f172a', strokeWidth: 2 }}
              isAnimationActive={false}
              style={{ filter: 'drop-shadow(0px 0px 4px rgba(34, 197, 94, 0.5))' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
