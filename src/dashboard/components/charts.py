import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Minimal clear layout template for Dark SOC theme
SOC_TEMPLATE = "plotly_dark"

def render_rl_vs_system_chart(df: pd.DataFrame):
    """Bar chart comparing the RL intent vs the Final Executed Action."""
    st.markdown("### 🧠 Decision Authority")
    
    if df.empty: return
    
    rl_counts = df['rl_action_name'].value_counts().rename('RL Agent')
    final_counts = df['final_action_name'].value_counts().rename('System Final')
    count_df = pd.concat([rl_counts, final_counts], axis=1).fillna(0).reset_index()
    count_df.rename(columns={'index': 'Action'}, inplace=True)
    count_df = count_df.melt(id_vars='Action', var_name='Decision Type', value_name='Count')
    
    fig = px.bar(count_df, x='Action', y='Count', color='Decision Type', barmode='group',
                 color_discrete_map={'RL Agent': '#facc15', 'System Final': '#38bdf8'},
                 template=SOC_TEMPLATE)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250)
    st.plotly_chart(fig, use_container_width=True)

def render_severity_over_time(df: pd.DataFrame):
    """Smooth line chart tracking severity over the timeline."""
    st.markdown("### 📈 Live Severity Tracker")
    if df.empty: return
    
    chart_data = df[['timestamp', 'severity_score', 'final_action_name']].copy()
    
    fig = px.line(chart_data, x='timestamp', y='severity_score', color_discrete_sequence=['#ef4444'], template=SOC_TEMPLATE)
    # Add scatter overlay for context
    fig.add_trace(go.Scatter(x=chart_data['timestamp'], y=chart_data['severity_score'], mode='markers',
                             marker=dict(size=4, color='#fca5a5'), hoverinfo='none', showlegend=False))
                             
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250, xaxis_title=None, yaxis_title="Severity")
    fig.update_yaxes(range=[0, 1.05])
    st.plotly_chart(fig, use_container_width=True)

def render_latency_tracking(df: pd.DataFrame):
    """Moving window latency tracking."""
    st.markdown("### ⚡ Micro-Latency (ms)")
    if df.empty: return
    
    chart_data = df[['timestamp','latency_ms']].copy()
    # Last 50 events moving window
    chart_data = chart_data.tail(50)
    chart_data['Rolling Avg'] = chart_data['latency_ms'].rolling(window=5, min_periods=1).mean()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=chart_data['timestamp'], y=chart_data['latency_ms'], name='Raw Latency', marker_color='#3f3f46'))
    fig.add_trace(go.Scatter(x=chart_data['timestamp'], y=chart_data['Rolling Avg'], name='5-Tick Avg', line=dict(color='#00e6ff', width=2)))
    
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250, template=SOC_TEMPLATE, xaxis_title=None, yaxis_title="ms")
    st.plotly_chart(fig, use_container_width=True)

def render_event_timeline(df: pd.DataFrame):
    """Horizontal flowing timeline of actions."""
    if df.empty: return
    st.markdown("### 🌊 Operational Flow")
    
    plot_df = df.tail(30).copy()
    plot_df['y_fixed'] = 0  # Flat line
    
    color_map = {
        "MONITOR": "#10b981",
        "ALERT": "#f59e0b",
        "BLOCK_IP": "#ef4444",
        "ISOLATE_USER": "#a855f7"
    }
    
    fig = px.scatter(plot_df, x="timestamp", y="y_fixed", color="final_action_name",
                     color_discrete_map=color_map, hover_data=["user_id", "severity_score"],
                     template=SOC_TEMPLATE)
                     
    fig.update_traces(marker=dict(size=14, line=dict(width=2, color='DarkSlateGrey')))
    fig.update_layout(height=120, margin=dict(l=0, r=0, t=0, b=0), yaxis_visible=False, xaxis_title=None, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def render_downgrade_analysis(df: pd.DataFrame):
    """Donut chart of downgrade reasons."""
    st.markdown("### ⚠️ Intervention Drivers")
    if df.empty: return
    
    downgrades = df[df['was_downgraded'] == True]
    if downgrades.empty:
        st.info("System is aligned with RL Agent.")
        return
        
    reason_counts = downgrades['downgrade_reason'].value_counts().reset_index()
    reason_counts.columns = ['Reason', 'Count']
    
    fig = px.pie(reason_counts, values='Count', names='Reason', hole=0.6, template=SOC_TEMPLATE,
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250, showlegend=False)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)
