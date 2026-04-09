import streamlit as st
import time

from styles import load_css
from utils import load_all_events, apply_filters
from components.metrics import render_top_metrics
from components.alerts import render_live_event_stream
from components.charts import (
    render_rl_vs_system_chart, render_severity_over_time,
    render_latency_tracking, render_event_timeline,
    render_downgrade_analysis
)

# Page Configuration
st.set_page_config(
    page_title="SOC War Room", 
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)
load_css()

# Session State for Playback
if 'playing' not in st.session_state:
    st.session_state.playing = False
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# --- CONTROL PANEL (SIDEBAR) ---
st.sidebar.markdown("<h2 style='text-align: center;'>⚡ SOC CONTROLS</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

col1, col2, col3, col4 = st.sidebar.columns(4)
if col1.button("▶️"): 
    st.session_state.playing = True
    st.rerun()
if col2.button("⏸️"): 
    st.session_state.playing = False
    st.rerun()
if col3.button("⏮️"): 
    st.session_state.current_index = 0
    st.session_state.playing = False
    if "prev_metrics" in st.session_state:
        del st.session_state["prev_metrics"]
    st.rerun()
if col4.button("⏭️"): 
    st.session_state.playing = False
    st.session_state.current_index += 1
    st.rerun()

st.sidebar.markdown(f"**State:** {'🟢 PLAYING' if st.session_state.playing else '⏸️ PAUSED'}")

speed_str = st.sidebar.select_slider("Playback Speed", options=["0.5x", "1x", "2x", "5x"], value="1x")
speed_map = {"0.5x": 1.0, "1x": 0.5, "2x": 0.1, "5x": 0.02}
delay_sec = speed_map[speed_str]

st.sidebar.markdown("---")
st.sidebar.subheader("Filters")
actions = ["MONITOR", "ALERT", "BLOCK_IP", "ISOLATE_USER"]
selected_actions = st.sidebar.multiselect("Action Types:", ["ALL"] + actions, default=["ALL"])
min_severity = st.sidebar.slider("Min Severity:", 0.0, 1.0, 0.0, 0.05)
show_only_interventions = st.sidebar.toggle("Show Interventions Only")

# --- DATA LOADING & PROGRESSION ---
full_df = load_all_events(max_events=2000)

if not full_df.empty:
    if st.session_state.current_index == 0 and not st.session_state.playing:
        st.session_state.current_index = min(100, len(full_df)) # Start with some data natively
        
    if st.session_state.current_index > len(full_df):
        st.session_state.current_index = len(full_df)
        st.session_state.playing = False
        
    # Slice the frame up to the current pointer
    display_df = full_df.iloc[:st.session_state.current_index]
else:
    display_df = full_df

filtered_df = apply_filters(display_df, selected_actions, min_severity, show_only_interventions)

# --- LAYOUT HEADER ---
st.title("🛡️ WAR ROOM: Autonomous Defense Interface")
render_event_timeline(filtered_df)
render_top_metrics(filtered_df)

st.markdown("---")

# --- MAIN DASHBOARD AREA ---
col_main, col_side = st.columns([1.5, 2])

with col_main:
    render_live_event_stream(filtered_df, limit=100)

with col_side:
    r1c1, r1c2 = st.columns(2)
    with r1c1: render_rl_vs_system_chart(filtered_df)
    with r1c2: render_downgrade_analysis(filtered_df)
    
    st.markdown("<br>", unsafe_allow_html=True)
    render_severity_over_time(filtered_df)
    
    st.markdown("<br>", unsafe_allow_html=True)
    render_latency_tracking(filtered_df)

# --- PLAYBACK TICKER ---
if st.session_state.playing and st.session_state.current_index < len(full_df):
    time.sleep(delay_sec)
    st.session_state.current_index += 1
    st.rerun()
elif st.session_state.playing and st.session_state.current_index >= len(full_df):
    st.session_state.playing = False
    st.toast("End of telemetry feed reached. 🚦")
