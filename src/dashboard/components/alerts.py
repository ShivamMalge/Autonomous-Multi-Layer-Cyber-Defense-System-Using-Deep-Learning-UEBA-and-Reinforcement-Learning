import streamlit as st
import pandas as pd
import json

def get_severity_bar(score: float) -> str:
    """Returns a visual ASCII block bar based on severity."""
    total_blocks = 10
    filled = int(round(score * total_blocks))
    empty = total_blocks - filled
    
    color = "green"
    if score >= 0.75: color = "red"
    elif score >= 0.4: color = "orange"
    
    bar = f"<span style='color:{color};'>{'█' * filled}</span><span style='color:grey;'>{'░' * empty}</span>"
    return bar

def render_live_event_stream(df: pd.DataFrame, limit: int = 50):
    """Renders the live event stream feed with expanders."""
    st.markdown("### 📡 Live Threat Feed")
    
    if df.empty:
        st.write("Waiting for telemetry...")
        return
        
    # Get latest N events and reverse to show newest first
    feed_df = df.tail(limit).iloc[::-1]

    for _, row in feed_df.iterrows():
        # Color coding
        action = row['final_action_name']
        color = "#10B981" # Green Monitor
        icon = "🟢"
        if action == "ALERT":
            color = "#F59E0B" # Yellow/Orange
            icon = "⚠️"
        elif action == "BLOCK_IP":
            color = "#EF4444" # Red
            icon = "🔴"
        elif action == "ISOLATE_USER":
            color = "#8B5CF6" # Purple
            icon = "☣️"
            
        time_str = row['timestamp'][11:19]
        sev_bar = get_severity_bar(row['severity_score'])
        
        # Build the Markdown CARD
        card_html = f"""
        <div class="event-card" style="border-left: 6px solid {color};">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size: 1.1em;">{icon} <b>[{time_str}]</b> {row['user_id']} | IP: {row['ip']}</span>
                <span style="background-color: #374151; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">{row['latency_ms']:.2f}ms</span>
            </div>
            <div style="margin-top: 6px; font-size: 0.9em;">
                <b>Sev:</b> {sev_bar} {row['severity_score']:.2f}
            </div>
        </div>
        """
        
        # Display the custom card
        st.markdown(card_html, unsafe_allow_html=True)
        
        # Add a collapsible drill-down underneath
        with st.expander(f"Inspect Intelligence 🔍"):
            st.markdown(f"**Anomaly Score:** {row['anomaly_score']:.3f} | **User Risk:** {row['user_risk_score']:.3f}")
            
            c1, c2 = st.columns(2)
            c1.info(f"**RL Agent Proposed:**\n\n{row['rl_action_name']}")
            c2.warning(f"**Final System Action:**\n\n{row['final_action_name']}")
                
            if row['was_downgraded']:
                st.error(f"**Override Reason:** {row['downgrade_reason']}")
                
            st.json(row.to_dict())
