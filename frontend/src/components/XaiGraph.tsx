import { useEffect, useState } from 'react';
import { ReactFlow, Background, MarkerType } from '@xyflow/react';
import type { Edge, Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { BrainCircuit } from 'lucide-react';

interface XaiData {
  explanation: string;
  kg_nodes: { source: string; target: string }[];
}

interface XaiGraphProps {
  xaiData: XaiData | null;
}

export function XaiGraph({ xaiData }: XaiGraphProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  useEffect(() => {
    if (!xaiData?.kg_nodes?.length) return;

    const s = xaiData.kg_nodes[0]?.source || "Symptom";
    const r = xaiData.kg_nodes[0]?.target || "Root Cause";
    const a = xaiData.kg_nodes[1]?.target || "Action";
    const isNormal = r === "Normal";

    const base = {
      padding: '10px 14px', borderRadius: '10px', color: '#fff',
      fontWeight: '600', fontSize: '11px', fontFamily: 'Space Grotesk, sans-serif',
      letterSpacing: '0.05em', textAlign: 'center' as const,
    };

    setNodes([
      { id: '1', position: { x: 50, y: 100 }, data: { label: s },
        style: { ...base, background: '#92400e', border: '1px solid #E8B931' } },
      { id: '2', position: { x: 250, y: 100 }, data: { label: r },
        style: { ...base, 
          background: isNormal ? '#064e3b' : '#7f1d1d', 
          border: isNormal ? '1px solid #10B981' : '1px solid #F06449' } },
      { id: '3', position: { x: 450, y: 100 }, data: { label: a },
        style: { ...base, background: '#134e4a', border: '1px solid #2DD4A8' } },
    ]);

    const lineColor = isNormal ? '#10B981' : '#F06449';
    setEdges([
      { id: 'e1-2', source: '1', target: '2', animated: true,
        style: { stroke: lineColor, strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: lineColor } },
      { id: 'e2-3', source: '2', target: '3', animated: true,
        style: { stroke: '#2DD4A8', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#2DD4A8' } },
    ]);
  }, [xaiData]);

  return (
    <div className="glass-panel p-4 h-80 flex flex-col">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-mono text-[10px] text-oracle-muted uppercase tracking-[0.15em]">
          XAI Causal Knowledge Graph
        </h3>
        <BrainCircuit size={14} className="text-accent-teal/40" />
      </div>

      {xaiData ? (
        <div className="bg-oracle-deep/50 border border-oracle-border/30 rounded-lg p-2.5 text-[11px] text-oracle-text/70 mb-3 font-mono leading-relaxed">
          <span className="text-accent-teal font-bold tracking-wider">XAI: </span>{xaiData.explanation}
        </div>
      ) : (
        <div className="bg-oracle-deep/50 border border-oracle-border/30 rounded-lg p-2.5 text-[11px] text-oracle-muted/30 mb-3 font-mono animate-pulse">
          AWAITING CAUSAL INITIATION...
        </div>
      )}

      <div className="flex-1 w-full bg-oracle-deep/30 border border-oracle-border/20 rounded-lg overflow-hidden">
        <ReactFlow nodes={nodes} edges={edges} fitView minZoom={0.5} maxZoom={2} proOptions={{ hideAttribution: true }}>
          <Background color="#1A2D52" gap={20} size={1} />
        </ReactFlow>
      </div>
    </div>
  );
}
