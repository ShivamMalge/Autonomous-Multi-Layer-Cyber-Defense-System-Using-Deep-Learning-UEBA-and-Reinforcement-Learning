import streamlit as st

def load_css():
    st.markdown("""
    <style>
    /* Dark Theme Core */
    .stApp {
        background-color: #0A0E17;
        color: #E2E8F0;
    }
    
    /* Neon Text Accents */
    h1, h2, h3 {
        color: #00E6FF !important;
        text-shadow: 0 0 10px rgba(0, 230, 255, 0.4);
        font-family: 'Courier New', Courier, monospace;
        letter-spacing: 1px;
    }
    
    /* Hide default streamlit decorations */
    header, #MainMenu, footer {visibility: hidden;}

    /* Sidebar Tweaks */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1F2937;
    }

    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        color: #10B981;
        font-size: 2rem !important;
        font-weight: 800;
        text-shadow: 0 0 8px rgba(16, 185, 129, 0.3);
    }
    div[data-testid="stMetricLabel"] {
        color: #9CA3AF;
        font-size: 1rem !important;
    }

    /* Delta Colors explicitly */
    div[data-testid="stMetricDelta"] svg {
        display: none; /* remove arrows */
    }

    /* Custom Event Cards Base */
    .event-card {
        background-color: #111827;
        border: 1px solid #374151;
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 12px;
        font-family: 'Courier New', Courier, monospace;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .event-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 15px rgba(0, 230, 255, 0.2);
    }
    
    /* Severity Bar Container */
    .severity-container {
        width: 100%;
        background-color: #374151;
        border-radius: 4px;
        height: 6px;
        margin-top: 8px;
        margin-bottom: 8px;
        overflow: hidden;
    }
    .severity-fill {
        height: 100%;
        border-radius: 4px;
    }

    </style>
    """, unsafe_allow_html=True)
