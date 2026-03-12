import { useState, useRef, useEffect, useCallback } from 'react';

interface LandingPageProps {
  onEnter: () => void;
}

/* ── Interactive Constellation Canvas ────────────────────────── */
interface Particle {
  x: number; y: number; vx: number; vy: number; r: number; o: number;
}

function useConstellationCanvas(canvasRef: React.RefObject<HTMLCanvasElement | null>) {
  const mouseRef = useRef({ x: -1000, y: -1000 });
  const particles = useRef<Particle[]>([]);
  const raf = useRef<number>(0);

  const init = useCallback((w: number, h: number) => {
    const count = Math.floor((w * h) / 6000);
    particles.current = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.8 + 0.6,
      o: Math.random() * 0.6 + 0.25,
    }));
  }, []);

  useEffect(() => {
    const cvs = canvasRef.current;
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      cvs.width = window.innerWidth;
      cvs.height = window.innerHeight;
      init(cvs.width, cvs.height);
    };

    const onMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };

    resize();
    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', onMove);

    const draw = () => {
      const w = cvs.width, h = cvs.height;
      ctx.clearRect(0, 0, w, h);
      const pts = particles.current;
      const mouse = mouseRef.current;

      for (const p of pts) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = w; if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h; if (p.y > h) p.y = 0;

        // Mouse repulsion
        const dx = p.x - mouse.x, dy = p.y - mouse.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 200) {
          const force = (200 - dist) / 200 * 0.012;
          p.vx += dx * force; p.vy += dy * force;
        }

        // Dampen
        p.vx *= 0.998; p.vy *= 0.998;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(45, 212, 168, ${p.o})`;
        ctx.fill();
      }

      // Connection lines
      const maxDist = 150;
      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const dx = pts[i].x - pts[j].x;
          const dy = pts[i].y - pts[j].y;
          const d = dx * dx + dy * dy;
          if (d < maxDist * maxDist) {
            const alpha = (1 - Math.sqrt(d) / maxDist) * 0.22;
            ctx.beginPath();
            ctx.moveTo(pts[i].x, pts[i].y);
            ctx.lineTo(pts[j].x, pts[j].y);
            ctx.strokeStyle = `rgba(45, 212, 168, ${alpha})`;
            ctx.lineWidth = 0.7;
            ctx.stroke();
          }
        }
      }

      raf.current = requestAnimationFrame(draw);
    };

    draw();
    return () => {
      cancelAnimationFrame(raf.current);
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', onMove);
    };
  }, [canvasRef, init]);
}

/* ── Live Timestamp Hook ─────────────────────────────────────── */
function useLiveTimestamp() {
  const [ts, setTs] = useState('');
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const pad = (n: number, d = 2) => String(n).padStart(d, '0');
      setTs(
        `${pad(now.getDate())}/${pad(now.getMonth() + 1)}/${now.getFullYear()} ` +
        `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}.${pad(now.getMilliseconds(), 3)}`
      );
    };
    tick();
    const id = setInterval(tick, 47); // ~21fps for ms resolution
    return () => clearInterval(id);
  }, []);
  return ts;
}

/* ── 3D Wireframe Cube ───────────────────────────────────────── */
function WireframeCube() {
  const faces = ['front', 'back', 'right', 'left', 'top', 'bottom'];
  return (
    <div className="cube-scene mb-12">
      <div className="cube-body">
        {faces.map(f => (
          <div key={f} className={`cube-face cube-face-${f}`}>
            {/* Corner markers */}
            <div className="absolute top-1 left-1 w-2 h-2 border-t border-l border-[#22d3ee]/30" />
            <div className="absolute top-1 right-1 w-2 h-2 border-t border-r border-[#22d3ee]/30" />
            <div className="absolute bottom-1 left-1 w-2 h-2 border-b border-l border-[#22d3ee]/30" />
            <div className="absolute bottom-1 right-1 w-2 h-2 border-b border-r border-[#22d3ee]/30" />
          </div>
        ))}
        {/* Inner wireframe cross */}
        <div className="absolute inset-0 flex items-center justify-center" style={{ transformStyle: 'preserve-3d' }}>
          <div className="w-px h-[140px] bg-[#22d3ee]/10 absolute" style={{ transform: 'translateZ(0)' }} />
          <div className="h-px w-[140px] bg-[#22d3ee]/10 absolute" style={{ transform: 'translateZ(0)' }} />
        </div>
      </div>
    </div>
  );
}

/* ── Landing Page Component ──────────────────────────────────── */
export function LandingPage({ onEnter }: LandingPageProps) {
  const [exiting, setExiting] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [displayedTitle, setDisplayedTitle] = useState('');
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useConstellationCanvas(canvasRef);
  const timestamp = useLiveTimestamp();

  const fullTitle = 'ECO-TWIN ORACLE';
  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      i++;
      setDisplayedTitle(fullTitle.slice(0, i));
      if (i >= fullTitle.length) clearInterval(interval);
    }, 100);
    return () => clearInterval(interval);
  }, []);

  const handleEnter = () => {
    setExiting(true);
    setTimeout(onEnter, 800);
  };

  return (
    <div
      className="min-h-screen relative overflow-hidden flex flex-col items-center justify-center select-none"
      style={{
        background: 'linear-gradient(170deg, #020617 0%, #030a1a 40%, #0a1128 100%)',
        ...(exiting ? { animation: 'hero-exit 0.8s ease-in-out forwards' } : {}),
      }}
    >
      {/* ── Canvas (UNTOUCHED) ─── */}
      <canvas ref={canvasRef} className="absolute inset-0 z-0" />

      {/* ── Ambient Gradients (UNTOUCHED) ─── */}
      <div className="absolute inset-0 pointer-events-none z-[1]">
        <div className="absolute top-[30%] left-[20%] w-[500px] h-[500px] rounded-full opacity-[0.035]"
          style={{ background: 'radial-gradient(circle, #2DD4A8, transparent 70%)' }} />
        <div className="absolute bottom-[20%] right-[15%] w-[400px] h-[400px] rounded-full opacity-[0.025]"
          style={{ background: 'radial-gradient(circle, #E8B931, transparent 70%)' }} />
      </div>

      {/* ── Grid Overlay ─── */}
      <div className="absolute inset-0 z-[2] pointer-events-none opacity-[0.025]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(34,211,238,0.4) 1px, transparent 1px),
            linear-gradient(90deg, rgba(34,211,238,0.4) 1px, transparent 1px)
          `,
          backgroundSize: '80px 80px',
        }}
      />

      {/* ── Top-Left Build Info ─── */}
      <div className="absolute top-5 left-6 z-10 flex items-center gap-3" style={{ fontFamily: "'Space Mono', monospace" }}>
        <span className="text-[10px] text-slate-600 tracking-[0.08em]">v2.6.1-rc</span>
        <span className="text-slate-800">|</span>
        <span className="text-[10px] text-slate-600 tracking-[0.08em]">AVEVA_TRACK_B</span>
        <span className="text-slate-800">|</span>
        <span className="flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full bg-[#22d3ee]/50 animate-pulse" />
          <span className="text-[10px] text-[#22d3ee]/40 tracking-[0.08em]">CONNECTED</span>
        </span>
      </div>

      {/* ── Bottom-Right Live Timestamp ─── */}
      <div className="absolute bottom-5 right-6 z-10" style={{ fontFamily: "'Space Mono', monospace" }}>
        <span className="text-[10px] text-slate-700 tracking-[0.05em]">[ {timestamp} ]</span>
      </div>

      {/* ── Center Content ─── */}
      <div className="relative z-10 flex flex-col items-center text-center px-6 max-w-3xl">

        {/* 3D Wireframe Cube */}
        <WireframeCube />

        {/* Main Title — Typewriter */}
        <h1
          className="text-6xl md:text-7xl font-extrabold tracking-[0.15em] uppercase mb-5 leading-none"
          style={{
            fontFamily: "Inter, 'DM Sans', system-ui, sans-serif",
            background: 'linear-gradient(135deg, #22d3ee 0%, #3b82f6 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            filter: 'drop-shadow(0 0 15px rgba(34,211,238,0.4))',
          }}
        >
          {displayedTitle}
          {displayedTitle.length < fullTitle.length && (
            <span className="animate-pulse text-cyan-400" style={{ WebkitTextFillColor: '#22d3ee' }}>|</span>
          )}
        </h1>

        {/* Primary Subtitle — New */}
        <p className="text-2xl md:text-3xl font-semibold text-slate-200 tracking-wide mb-4" style={{ fontFamily: "Inter, 'DM Sans', system-ui, sans-serif" }}>
          A Prescriptive Cyber-Physical System
        </p>

        {/* Trilemma Tagline */}
        <p className="text-lg text-slate-300/80 max-w-2xl mb-10 leading-relaxed" style={{ fontFamily: "Inter, 'DM Sans', system-ui, sans-serif" }}>
          Solving the Manufacturing Trilemma of{' '}
          <span className="text-[#22d3ee] font-medium">Throughput</span>,{' '}
          <span className="text-[#22d3ee] font-medium">Quality</span>, and{' '}
          <span className="text-[#fbbf24] font-medium">Carbon Intensity</span>.
        </p>

        {/* Horizontal Rule */}
        <div className="w-24 h-px bg-gradient-to-r from-transparent via-[#22d3ee]/25 to-transparent mb-10" />

        {/* CTA Button */}
        <button
          onClick={handleEnter}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          className="group relative px-14 py-5 rounded-lg cursor-pointer overflow-hidden transition-all duration-300 ease-out border border-[#164e63] bg-[#020617]/60 backdrop-blur-sm hover:border-[#22d3ee]/50 hover:scale-[1.05] hover:shadow-[0_0_40px_-8px_rgba(34,211,238,0.35)] active:scale-[0.98]"
          style={{ fontFamily: "Inter, 'DM Sans', system-ui, sans-serif" }}
        >
          {/* Scanline effect */}
          <div
            className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300"
            style={{
              background: 'linear-gradient(to bottom, transparent 0%, rgba(34,211,238,0.04) 50%, transparent 100%)',
              backgroundSize: '100% 200%',
              animation: hovered ? 'scanline-sweep 1.5s linear infinite' : 'none',
            }}
          />

          <span className="relative z-10 text-lg text-white font-bold tracking-[0.12em] uppercase group-hover:text-[#22d3ee] transition-colors duration-300">
            Access Oracle
          </span>
        </button>

        {/* Sub-CTA detail */}
        <p className="mt-4 text-[9px] text-slate-600 tracking-[0.15em] uppercase" style={{ fontFamily: "'Space Mono', monospace" }}>
          Initialize Edge Connection · ws://localhost:8000
        </p>
      </div>

      {/* ── Bottom-Left: System Markers ─── */}
      <div className="absolute bottom-5 left-6 z-10 flex items-center gap-4" style={{ fontFamily: "'Space Mono', monospace" }}>
        <span className="text-[9px] text-slate-700 tracking-[0.1em]">SOM:10×10</span>
        <span className="text-slate-800">·</span>
        <span className="text-[9px] text-slate-700 tracking-[0.1em]">LVQ:9P</span>
        <span className="text-slate-800">·</span>
        <span className="text-[9px] text-slate-700 tracking-[0.1em]">DFA:8Φ</span>
      </div>
    </div>
  );
}

