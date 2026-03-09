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
        animation: border-pulse 1.5s infinite; margin-top: 1rem;
    }}
    @keyframes border-pulse {{ 0%, 100% {{ border-color: {THEME["red"]}; box-shadow: 0 0 6px {THEME["red"]}44; }} 50% {{ border-color: {THEME["amber"]}; box-shadow: 0 0 20px {THEME["amber"]}66; }} }}
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

def render_metrics(t, presc):
    with metrics_ph.container():
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("🌡️ Temperature", f"{t.get('Temperature_C', 0):.1f} °C")
        c2.metric("🔵 Pressure", f"{t.get('Pressure_Bar', 0):.2f} bar")
        c3.metric("⚡ Power", f"{t.get('Power_Consumption_kW', 0):.3f} kW")
        c4.metric("🔄 Motor Speed", f"{t.get('Motor_Speed_RPM', 0)} RPM")
        c5.metric("📳 Vibration", f"{t.get('Vibration_mm_s', 0):.3f} mm/s")
        c6.metric("🎯 BMU Distance", f"{presc.get('bmu_distance', 0):.3f}")

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

def render_alert(payload):
    alert = payload.get("phantom_alert")
    if alert:
        recs = payload.get("prescription", {}).get("parameter_recommendations", {})
        blocked = payload.get("prescription", {}).get("blocked_parameters", [])
        
        rows_html = ""
        for p, d in recs.items():
            cls = "rec-positive" if d >= 0 else "rec-negative"
            rows_html += f'<div class="rec-row"><span style="color:{THEME["text"]}">{p}</span><span class="{cls}">{"▲" if d >= 0 else "▼"} {abs(d):.3f}</span></div>'
        for p in blocked:
            rows_html += f'<div class="rec-row"><span style="color:{THEME["muted"]}">{p}</span><span style="color:{THEME["red"]};font-size:0.75rem;">🔒 DFA BLOCKED</span></div>'

        with alert_ph.container():
            st.markdown(f"""
                <div class="phantom-alert-box">
                    <h4 style="color:{THEME['red']}; margin:0 0 10px 0;">⚡ PHANTOM ENERGY WASTE DETECTED</h4>
                    <p style="color:{THEME['muted']}; font-size:0.9rem; margin-bottom:15px;"><b>DFA Locked:</b> PREPARATION | <b>Motor:</b> 0 RPM | <b>Draw:</b> <span style="color:{THEME['red']}; font-weight:bold;">{alert.get('power_consumption_kw'):.3f} kW</span></p>
                    <p class="oracle-header">AI Prescriptions (DFA-Validated):</p>
                    <div style="background:{THEME['panel']}; padding:10px; border-radius:8px;">{rows_html}</div>
                </div>
            """, unsafe_allow_html=True)
            # Add buttons below alert
            c1, c2, c3 = st.columns([2,2,4])
            if c1.button("🤖 Autonomous Execute", key=f"auto_{time.time()}", type="primary"): 
                st.session_state.stats["auto"] += 1
                st.toast("Autonomous Optimization Dispatched!", icon="🤖")
            if c2.button("🛑 Manual Override", key=f"man_{time.time()}"):
                st.session_state.stats["manual"] += 1
                st.toast("Manual Override Recorded.", icon="🛑")
    else:
        alert_ph.empty() # Hide alert if not phantom phase

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
                    st.success(f"✅ Batch {batch_id} simulation complete.")
                    st.session_state.streaming = False
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
                render_metrics(t, presc)
                render_charts(presc)
                render_alert(payload)

    except Exception as e:
        st.error(f"WebSocket Error: {e}. Is FastAPI running on port 8000?")
        st.session_state.streaming = False

if st.session_state.streaming:
    asyncio.run(stream_data())
else:
    st.info("👈 Select Batch T060 from the sidebar and click 'Start Simulation'.")