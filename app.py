"""
app.py
======
The Ultimate Eco-Twin Oracle Frontend.
Combines Antigravity's premium Series-A UI with a stable async WebSocket loop.
"""

import asyncio
import json
import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import websockets

# ──────────────────────────────────────────────────────────────────────────────
# Page configuration & Design System
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Eco-Twin Oracle", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

THEME = {
    "bg": "#0A0F1E", "panel": "#0D1528", "border": "#1C2E4A",
    "cyan": "#00D4FF", "neon": "#39FF14", "amber": "#FFB300",
    "red": "#FF4444", "text": "#E8F4FD", "muted": "#6B8CAE",
    "card_bg": "#0F1A2E"
}

DFA_PHASES = ["PREPARATION", "GRANULATION", "DRYING", "MILLING", "BLENDING", "COMPRESSION", "COATING", "QUALITY_TESTING"]

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; background-color: {THEME["bg"]} !important; color: {THEME["text"]} !important; }}
    [data-testid="stSidebar"] {{ background: linear-gradient(180deg, {THEME["bg"]} 0%, #0C1830 100%) !important; border-right: 1px solid {THEME["border"]} !important; }}
    .main .block-container {{ padding-top: 1rem !important; }}
    
    /* Premium Metric Cards */
    [data-testid="stMetric"] {{
        background: {THEME["card_bg"]} !important; border: 1px solid {THEME["border"]} !important;
        border-radius: 12px !important; padding: 1rem !important; transition: all 0.3s ease;
    }}
    [data-testid="stMetric"]:hover {{ border-color: {THEME["cyan"]} !important; box-shadow: 0 0 15px rgba(0, 212, 255, 0.15) !important; }}
    [data-testid="stMetricValue"] {{ font-family: 'JetBrains Mono', monospace !important; color: {THEME["cyan"]} !important; font-size: 1.8rem !important; }}
    [data-testid="stMetricLabel"] {{ color: {THEME["muted"]} !important; font-size: 0.75rem !important; text-transform: uppercase !important; letter-spacing: 0.1em !important; }}
    
    /* Custom HTML Panels */
    .oracle-panel {{ background: {THEME["panel"]}; border: 1px solid {THEME["border"]}; border-radius: 14px; padding: 1.2rem; margin-bottom: 0.8rem; }}
    .oracle-header {{ font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; color: {THEME["muted"]}; margin-bottom: 0.4rem; }}
    .title-gradient {{ background: linear-gradient(90deg, {THEME["cyan"]}, {THEME["neon"]}); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2rem; font-weight: 800; letter-spacing: -0.02em; margin:0; }}
    
    /* Badges & Alerts */
    .dfa-node {{ display: inline-flex; align-items: center; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.05em; }}
    .anomaly-badge {{ display: inline-block; padding: 0.3rem 1rem; border-radius: 20px; font-size: 0.82rem; font-weight: 700; animation: pulse-glow 2s infinite; }}
    @keyframes pulse-glow {{ 0% {{ box-shadow: 0 0 0px currentColor; }} 50% {{ box-shadow: 0 0 14px currentColor; }} 100% {{ box-shadow: 0 0 0px currentColor; }} }}
    
    .phantom-alert-box {{
        background: linear-gradient(135deg, rgba(255,68,68,0.1), rgba(255,179,0,0.05));
        border: 2px solid {THEME["red"]}; border-radius: 12px; padding: 1.5rem;
        animation: border-pulse-red 1.5s infinite; margin-top: 1rem;
    }}
    .arbitrage-alert-box {{
        background: linear-gradient(135deg, rgba(0,212,255,0.1), rgba(57,255,20,0.05));
        border: 2px solid {THEME["cyan"]}; border-radius: 12px; padding: 1.5rem;
        animation: border-pulse-cyan 2s infinite; margin-top: 1rem;
    }}
    .pvr-alert-box {{
        background: linear-gradient(135deg, rgba(255,179,0,0.1), rgba(255,68,68,0.05));
        border: 2px solid {THEME["amber"]}; border-radius: 12px; padding: 1.5rem;
        animation: border-pulse-amber 1.8s infinite; margin-top: 1rem;
    }}
    
    @keyframes border-pulse-red {{ 0%, 100% {{ border-color: {THEME["red"]}; box-shadow: 0 0 6px {THEME["red"]}44; }} 50% {{ border-color: {THEME["amber"]}; box-shadow: 0 0 20px {THEME["amber"]}66; }} }}
    @keyframes border-pulse-cyan {{ 0%, 100% {{ border-color: {THEME["cyan"]}; box-shadow: 0 0 6px {THEME["cyan"]}44; }} 50% {{ border-color: {THEME["neon"]}; box-shadow: 0 0 20px {THEME["neon"]}66; }} }}
    @keyframes border-pulse-amber {{ 0%, 100% {{ border-color: {THEME["amber"]}; box-shadow: 0 0 6px {THEME["amber"]}44; }} 50% {{ border-color: {THEME["red"]}; box-shadow: 0 0 20px {THEME["red"]}66; }} }}
    .rec-row {{ display: flex; justify-content: space-between; padding: 0.35rem 0; border-bottom: 1px solid {THEME["border"]}; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; }}
    .rec-positive {{ color: {THEME["neon"]}; }} .rec-negative {{ color: {THEME["red"]}; }}
    </style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Session State Initialization
# ──────────────────────────────────────────────────────────────────────────────
if "streaming" not in st.session_state: st.session_state.streaming = False
if "time_series" not in st.session_state: st.session_state.time_series = {"time": [], "actual_kw": [], "ghost_kw": []}
if "bmu_history" not in st.session_state: st.session_state.bmu_history = []
if "stats" not in st.session_state: st.session_state.stats = {"rows": 0, "alerts": 0, "auto": 0, "manual": 0}

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar & Header
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<p style="color:{THEME["cyan"]};font-size:1.2rem;font-weight:700;letter-spacing:0.1em;">ECO-TWIN ORACLE</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:{THEME["muted"]};font-size:0.8rem;">AVEVA Hackathon · Track B</p>', unsafe_allow_html=True)
    st.divider()
    
    batch_id = st.selectbox("📦 Select Batch ID", [f"T{str(i).zfill(3)}" for i in range(1, 62)], index=59)
    
    if st.button("▶ Start Simulation", type="primary", use_container_width=True):
        st.session_state.streaming = True
        st.session_state.time_series = {"time": [], "actual_kw": [], "ghost_kw": []}
        st.session_state.bmu_history = []
        st.session_state.stats = {"rows": 0, "alerts": 0, "auto": 0, "manual": 0}
    if st.button("⏹ Stop / Reset", use_container_width=True):
        st.session_state.streaming = False

    st.divider()
    st.markdown('<p class="oracle-header">Session Stats</p>', unsafe_allow_html=True)
    stats_ph = st.empty() # Placeholder for stats so they update live

    st.divider()
    with st.expander("🏛️ Enterprise Architecture & Compliance", expanded=False):
        st.markdown(f'''
            <div style="font-size: 0.8rem; color: {THEME["muted"]};">
                <b style="color: {THEME["cyan"]};">1. USP Regulatory Baseline:</b><br>
                Excess Quality Margin is strictly calculated against <b>USP Acceptance Criteria (Q = 85.0%)</b> for immediate-release solid dosage forms. No arbitrary thresholds.<br><br>
                <b style="color: {THEME["cyan"]};">2. Production Ingestion:</b><br>
                Streaming via simulated WebSockets for demo purposes. Production-ready <code>opc_ua_mqtt_gateway.py</code> adapter is configured for live PLC integration.<br><br>
                <b style="color: {THEME["cyan"]};">3. Edge-Cloud Hybrid:</b><br>
                Inference runs on local Edge. Kohonen SOM weights are updated asynchronously via Cloud-Sync to prevent catastrophic forgetting.
            </div>
        ''', unsafe_allow_html=True)
st.markdown('<p class="title-gradient">⚡ ECO-TWIN ORACLE</p>', unsafe_allow_html=True)
st.markdown(f'<p style="color:{THEME["muted"]};">Prescriptive Manufacturing Intelligence · Real-Time Telemetry Stream</p>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Layout Placeholders (The Secret to Flicker-Free Async)
# ──────────────────────────────────────────────────────────────────────────────
progress_ph = st.empty()
metrics_ph = st.empty()
st.markdown("<br>", unsafe_allow_html=True)
chart_col, heatmap_col = st.columns([3, 2], gap="medium")
with chart_col:
    st.markdown('<p class="oracle-header">Visual 1 · Golden Signature Power Trace</p>', unsafe_allow_html=True)
    chart_ph = st.empty()
with heatmap_col:
    anomaly_ph = st.empty()
    heatmap_ph = st.empty()

alert_ph = st.empty()
xai_ph = st.empty()

# ──────────────────────────────────────────────────────────────────────────────
# Render Functions (Premium UI Components)
# ──────────────────────────────────────────────────────────────────────────────
def render_progress(current_phase):
    idx = DFA_PHASES.index(current_phase) if current_phase in DFA_PHASES else 0
    nodes_html = ""
    for i, phase in enumerate(DFA_PHASES):
        color, bg = (THEME["cyan"], "rgba(0,212,255,0.18)") if i == idx else (THEME["neon"], "rgba(57,255,20,0.12)") if i < idx else (THEME["border"], THEME["bg"])
        nodes_html += f'<span class="dfa-node" style="color:{color};background:{bg};border:1px solid {color}40;">{i+1}. {phase}</span>'
        if i < len(DFA_PHASES) - 1: nodes_html += f'<span style="color:{THEME["border"]};font-size:0.75rem;"> → </span>'
    
    with progress_ph.container():
        st.markdown(f'<div class="oracle-panel"><p class="oracle-header">DFA Phase Lock</p><div style="display:flex;flex-wrap:wrap;gap:0.3rem;">{nodes_html}</div></div>', unsafe_allow_html=True)

def render_metrics(t, presc, q_margin):
    with metrics_ph.container():
        pvr = t.get('Power_Consumption_kW', 0) / (t.get('Vibration_mm_s', 0) + 0.001)
        r1_cols = st.columns(4)
        r1_cols[0].metric("🌡️ Temperature", f"{t.get('Temperature_C', 0):.1f} °C")
        r1_cols[1].metric("🔵 Pressure", f"{t.get('Pressure_Bar', 0):.2f} bar")
        r1_cols[2].metric("⚡ Power", f"{t.get('Power_Consumption_kW', 0):.3f} kW")
        r1_cols[3].metric("🔄 Motor Speed", f"{t.get('Motor_Speed_RPM', 0)} RPM")

        r2_cols = st.columns(4)
        r2_cols[0].metric("📳 Vibration", f"{t.get('Vibration_mm_s', 0):.3f} mm/s")
        r2_cols[1].metric("🎯 BMU Distance", f"{presc.get('bmu_distance', 0):.3f}")
        r2_cols[2].metric("⚙️ PVR Index", f"{pvr:.1f}")
        
        # Style Quality Margin explicitly to highlight harvesting availability
        qm_color = THEME["neon"] if q_margin >= 5.0 else THEME["text"]
        r2_cols[3].markdown(f"""
            <div data-testid="stMetric" style="text-align:center;">
                <div data-testid="stMetricLabel">Excess Quality Margin</div>
                <div data-testid="stMetricValue" style="color:{qm_color} !important;">+{q_margin:.1f}%</div>
            </div>
        """, unsafe_allow_html=True)

def render_charts(presc):
    # Line Chart
    df = pd.DataFrame(st.session_state.time_series)
    fig_line = go.Figure()
    if not df.empty:
        fig_line.add_trace(go.Scatter(x=df["time"], y=df["ghost_kw"], mode='lines', name='Golden Target', line={"color": THEME["cyan"], "width": 2, "dash": "dash"}))
        fig_line.add_trace(go.Scatter(x=df["time"], y=df["actual_kw"], mode='lines', name='Live Draw', line={"color": THEME["neon"], "width": 3}, fill='tozeroy', fillcolor='rgba(57, 255, 20, 0.08)'))
        fig_line.add_hline(y=1.5, line={"color": THEME["red"], "width": 1, "dash": "dot"}, annotation_text="Phantom Threshold", annotation_font_color=THEME["red"])
    fig_line.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin={"l": 10, "r": 10, "t": 10, "b": 10}, height=280, legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1})
    chart_ph.plotly_chart(fig_line, use_container_width=True)

    # Anomaly Badge
    anomaly = presc.get("anomaly_class", "Normal")
    col = THEME["neon"] if anomaly == "Normal" else THEME["red"]
    icon = "✅" if anomaly == "Normal" else "⚠️"
    anomaly_ph.markdown(f'<p class="oracle-header">LVQ Classification</p><span class="anomaly-badge" style="color:{col};border:1.5px solid {col};">{icon} {anomaly}</span>', unsafe_allow_html=True)

    # Heatmap
    grid = [[0] * 10 for _ in range(10)]
    for r, c in st.session_state.bmu_history:
        if 0 <= r < 10 and 0 <= c < 10: grid[r][c] += 1
    fig_hm = go.Figure(go.Heatmap(z=grid, colorscale=[[0, THEME["bg"]], [0.5, THEME["cyan"]], [1, THEME["neon"]]], showscale=False))
    fig_hm.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin={"l": 5, "r": 5, "t": 20, "b": 5}, height=200, title={"text": "SOM Lattice Density", "font": {"size": 11, "color": THEME["muted"]}}, xaxis={"showticklabels": False}, yaxis={"showticklabels": False})
    heatmap_ph.plotly_chart(fig_hm, use_container_width=True)

def render_knowledge_graph(payload):
    xai = payload.get("xai_data")
    if not xai: return
    nodes = xai.get("kg_nodes", [])
    if len(nodes) >= 2:
        labels = [nodes[0]["source"], nodes[0]["target"], nodes[1]["target"]]
        color_map = [THEME["amber"], THEME["neon"] if labels[1] == "Normal" else THEME["red"], THEME["cyan"]]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 1, None, 1, 2, None], y=[0, 0, None, 0, 0, None], mode="lines", line={"width": 4, "color": THEME["border"]}, hoverinfo="none"))
        fig.add_trace(go.Scatter(x=[0, 1, 2], y=[0, 0, 0], mode="markers+text", text=labels, textposition="top center", marker={"size": [35, 45, 35], "color": color_map, "line": {"width": 2, "color": "white"}}, textfont={"color": THEME["text"], "size": 13, "family": "Inter"}))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis={"showgrid": False, "zeroline": False, "showticklabels": False, "range": [-0.5, 2.5]}, yaxis={"showgrid": False, "zeroline": False, "showticklabels": False, "range": [-0.5, 0.8]}, margin={"l": 0, "r": 0, "t": 10, "b": 0}, height=180, showlegend=False)
        with xai_ph.container():
            st.markdown('<p class="oracle-header" style="margin-top:1rem;">Visual 3 · XAI Causal Knowledge Graph</p>', unsafe_allow_html=True)
            st.info(f"🧠 **XAI Reasoning Engine:** {xai['explanation']}")
            st.plotly_chart(fig, use_container_width=True)

def render_alert(payload):
    phantom = payload.get("phantom_alert")
    arbitrage = payload.get("arbitrage_alert")
    pvr_alert = payload.get("pvr_alert")
    
    # We clear the container initially, then conditionally block it out
    with alert_ph.container():
        alerts_rendered = False
        
        if arbitrage:
            alerts_rendered = True
            msg = arbitrage.get("alert", "Inter-phase arbitrage executed.")
            st.markdown(f"""
                <div class="arbitrage-alert-box">
                    <h4 style="color:{THEME['cyan']}; margin:0 0 10px 0;">🦋 INTER-PHASE ARBITRAGE EXECUTED</h4>
                    <p style="color:{THEME['text']}; font-size:0.9rem; margin:0;">{msg}</p>
                </div>
            """, unsafe_allow_html=True)

        if pvr_alert:
            alerts_rendered = True
            msg = pvr_alert.get("warning", "High PVR detected.")
            st.markdown(f"""
                <div class="pvr-alert-box">
                    <h4 style="color:{THEME['amber']}; margin:0 0 10px 0;">⚙️ INVISIBLE FRICTION DETECTED</h4>
                    <p style="color:{THEME['text']}; font-size:0.9rem; margin:0;">{msg}</p>
                </div>
            """, unsafe_allow_html=True)

        if phantom:
            alerts_rendered = True
            recs = payload.get("prescription", {}).get("parameter_recommendations", {})
            blocked = payload.get("prescription", {}).get("blocked_parameters", [])
            
            rows_html = ""
            for p, d in recs.items():
                cls = "rec-positive" if d >= 0 else "rec-negative"
                rows_html += f'<div class="rec-row"><span style="color:{THEME["text"]}">{p}</span><span class="{cls}">{"▲" if d >= 0 else "▼"} {abs(d):.3f}</span></div>'
            for p in blocked:
                rows_html += f'<div class="rec-row"><span style="color:{THEME["muted"]}">{p}</span><span style="color:{THEME["red"]};font-size:0.75rem;">🔒 DFA BLOCKED</span></div>'

            st.markdown(f"""
                <div class="phantom-alert-box">
                    <h4 style="color:{THEME['red']}; margin:0 0 10px 0;">⚡ PHANTOM ENERGY WASTE DETECTED</h4>
                    <p style="color:{THEME['muted']}; font-size:0.9rem; margin-bottom:15px;"><b>DFA Locked:</b> PREPARATION | <b>Motor:</b> 0 RPM | <b>Draw:</b> <span style="color:{THEME['red']}; font-weight:bold;">{phantom.get('power_consumption_kw'):.3f} kW</span></p>
                    <p class="oracle-header">AI Prescriptions (DFA-Validated):</p>
                    <div style="background:{THEME['panel']}; padding:10px; border-radius:8px;">{rows_html}</div>
                </div>
            """, unsafe_allow_html=True)

        if alerts_rendered:
            c1, c2, c3 = st.columns([2,2,4])
            if c1.button("🤖 Autonomous Execute", key=f"auto_{time.time()}", type="primary"): 
                st.session_state.stats["auto"] += 1
                st.toast("Autonomous Optimization Dispatched!", icon="🤖")
            if c2.button("🛑 Manual Override", key=f"man_{time.time()}"):
                st.session_state.stats["manual"] += 1
                st.toast("Manual Override Recorded.", icon="🛑")
        else:
            # Wipe the container transparent visually if nothing is firing
            st.empty()

# ──────────────────────────────────────────────────────────────────────────────
# Async WebSocket Engine
# ──────────────────────────────────────────────────────────────────────────────
async def stream_data():
    uri = f"ws://localhost:8000/ws/live-batch/{batch_id}"
    try:
        async with websockets.connect(uri) as ws:
            while st.session_state.streaming:
                raw_msg = await ws.recv()
                payload = json.loads(raw_msg)
                
                if payload["event"] == "batch_complete":
                    st.session_state.streaming = False
                    ledger = payload.get("ledger_status", {})
                    if ledger.get("trigger_som_retraining"):
                        st.success(f"✅ **Batch {batch_id} simulation complete.** \n\n 🔄 **CONTINUOUS LEARNING TRIGGERED:** Batch energy outperformed historical Golden Signature. Recursive Bayesian Update written to `som_retraining_ledger.json` for overnight Edge-Cloud sync.")
                    else:
                        st.success(f"✅ **Batch {batch_id} simulation complete.** Performance logged to historian.")
                    break
                
                t = payload.get("telemetry", {})
                presc = payload.get("prescription", {})
                state = payload.get("dfa_state", "UNKNOWN")
                
                # Update State Data
                st.session_state.stats["rows"] += 1
                st.session_state.time_series["time"].append(t.get("Time_Minutes", 0))
                st.session_state.time_series["actual_kw"].append(t.get("Power_Consumption_kW", 0.0))
                st.session_state.time_series["ghost_kw"].append(t.get("Power_Consumption_kW", 0.0) + presc.get("parameter_recommendations", {}).get("Power_Consumption_kW", 0.0))
                st.session_state.bmu_history.append(tuple(presc.get("bmu_index", [0,0])))
                if payload.get("event") == "phantom_energy": st.session_state.stats["alerts"] += 1

                # Update Sidebar Stats
                with stats_ph.container():
                    st.write(f"**Rows:** {st.session_state.stats['rows']} | **Alerts:** {st.session_state.stats['alerts']}")
                    st.write(f"**Auto Ops:** {st.session_state.stats['auto']} | **Overrides:** {st.session_state.stats['manual']}")

                # Fire Renderers
                render_progress(state)
                render_metrics(t, presc, payload.get("quality_margin", 0.0))
                render_charts(presc)
                render_alert(payload)
                render_knowledge_graph(payload)

    except Exception as e:
        st.error(f"WebSocket Error: {e}. Is FastAPI running on port 8000?")
        st.session_state.streaming = False

if st.session_state.streaming:
    asyncio.run(stream_data())
else:
    st.info("👈 Select Batch T060 from the sidebar and click 'Start Simulation'.")