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

    // We assume a 3-node causal structure mapping for Hackathon track
    const s = xaiData.kg_nodes[0]?.source || "Symptom";
    const r = xaiData.kg_nodes[0]?.target || "Root Cause";
    const a = xaiData.kg_nodes[1]?.target || "Action";

    const isNormal = r === "Normal";

    const baseNodeStyle = {
      padding: '10px',
      borderRadius: '8px',
      color: '#fff',
      fontWeight: 'bold',
      fontSize: '12px',
      border: '1px solid #334155',
      textAlign: 'center' as const,
      boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
    };

    setNodes([
      {
        id: '1',
        position: { x: 50, y: 100 },
        data: { label: s },
        style: { ...baseNodeStyle, background: '#b45309', border: '1px solid #f59e0b' }, // Amber
      },
      {
        id: '2',
        position: { x: 250, y: 100 },
        data: { label: r },
        style: { 
          ...baseNodeStyle, 
          background: isNormal ? '#166534' : '#991b1b', // Green or Red
          border: isNormal ? '1px solid #22c55e' : '1px solid #ef4444' 
        },
      },
      {
        id: '3',
        position: { x: 450, y: 100 },
        data: { label: a },
        style: { ...baseNodeStyle, background: '#0e7490', border: '1px solid #06b6d4' }, // Cyan
      },
    ]);

    setEdges([
      {
        id: 'e1-2',
        source: '1',
        target: '2',
        animated: true,
        style: { stroke: isNormal ? '#22c55e' : '#ef4444', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: isNormal ? '#22c55e' : '#ef4444' }
      },
      {
        id: 'e2-3',
        source: '2',
        target: '3',
        animated: true,
        style: { stroke: '#06b6d4', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#06b6d4' }
      },
    ]);
  }, [xaiData]);

  return (
    <div className="glass-panel p-4 h-80 flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest text-cyan-400/80">
          Visual 3 · XAI Causal Knowledge Graph
        </h3>
        <BrainCircuit size={16} className="text-cyan-400" />
      </div>

      {xaiData ? (
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-3 text-sm text-slate-300 mb-4 font-mono leading-relaxed shadow-inner">
          <span className="text-cyan-400 font-bold tracking-widest">XAI ENGINE: </span> 
          {xaiData.explanation}
        </div>
      ) : (
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-3 text-sm text-slate-500 mb-4 font-mono shadow-inner animate-pulse">
          AWAITING XAI CAUSAL INITIATION...
        </div>
      )}

      <div className="flex-1 w-full bg-[#0A0F1E] border border-slate-800 rounded-lg overflow-hidden relative">
        <ReactFlow nodes={nodes} edges={edges} fitView minZoom={0.5} maxZoom={2} proOptions={{ hideAttribution: true }}>
          <Background color="#1e293b" gap={16} size={1} />
        </ReactFlow>
      </div>
    </div>
  );
}
