import os
import json
import logging
import pandas as pd
from typing import List
import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LOG_FILE_PATH = os.path.join(PROJECT_ROOT, "reports", "logs", "system_events.jsonl")

@st.cache_data(ttl=5) # Cache data slightly to prevent over-reading file during live playback loops
def load_all_events(max_events: int = 5000) -> pd.DataFrame:
    """Reads the JSONL log file into a DataFrame."""
    import streamlit as st # local import for cache
    if not os.path.exists(LOG_FILE_PATH):
        return pd.DataFrame()

    events = []
    try:
        with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines[-max_events:]:
            if line.strip():
                try:
                    events.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        
        df = pd.DataFrame(events)
        if not df.empty and 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        logging.error(f"Error loading events: {e}")
        return pd.DataFrame()

def apply_filters(df: pd.DataFrame, action_filter: List[str], min_severity: float, show_only_interventions: bool) -> pd.DataFrame:
    """Apply user filters to the event DataFrame."""
    if df.empty:
        return df

    filtered_df = df.copy()
    
    if action_filter and "ALL" not in action_filter:
        filtered_df = filtered_df[filtered_df['final_action_name'].isin(action_filter)]
        
    filtered_df = filtered_df[filtered_df['severity_score'] >= min_severity]
    
    if show_only_interventions:
        filtered_df = filtered_df[filtered_df['was_downgraded'] == True]
        
    return filtered_df
