import streamlit as st
import pandas as pd

def render_top_metrics(df: pd.DataFrame):
    """Renders the top overview metrics with dynamic delta changes."""
    if df.empty:
        st.warning("No events found.")
        return

    # Track previous values in session state for Deltas
    if "prev_metrics" not in st.session_state:
        st.session_state.prev_metrics = {
            "total": 0, "alert": 0, "block": 0, "isolate": 0, "interventions": 0
        }

    prev = st.session_state.prev_metrics

    # Calculate metrics
    total_events = len(df)
    alert_count = len(df[df['final_action_name'] == 'ALERT'])
    block_count = len(df[df['final_action_name'] == 'BLOCK_IP'])
    isolate_count = len(df[df['final_action_name'] == 'ISOLATE_USER'])
    interventions = len(df[df['was_downgraded'] == True])
    avg_latency = df['latency_ms'].mean() if 'latency_ms' in df.columns else 0.0

    # Determine Deltas
    d_tot = total_events - prev["total"]
    d_alr = alert_count - prev["alert"]
    d_blk = block_count - prev["block"]
    d_iso = isolate_count - prev["isolate"]
    d_int = interventions - prev["interventions"]

    # Display columns
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    col1.metric("Total Events", total_events, delta=f"+{d_tot}" if d_tot > 0 else "")
    col2.metric("Alerts ⚠️", alert_count, delta=f"+{d_alr}" if d_alr > 0 else "")
    col3.metric("Blocks 🛑", block_count, delta=f"+{d_blk}" if d_blk > 0 else "")
    col4.metric("Isolations ☣️", isolate_count, delta=f"+{d_iso}" if d_iso > 0 else "")
    col5.metric("System Interventions", interventions, delta=f"+{d_int}" if d_int > 0 else "", delta_color="off")
    col6.metric("Avg Latency", f"{avg_latency:.2f} ms")

    # Update state
    if st.session_state.get('playing', False):
        st.session_state.prev_metrics = {
            "total": total_events, "alert": alert_count, "block": block_count, 
            "isolate": isolate_count, "interventions": interventions
        }
