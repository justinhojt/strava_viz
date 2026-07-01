import streamlit as st
import pandas as pd

from utils.data_loader import parse_csv
from utils.functions import parse_granular
from utils.plots import plot_fitness_fatigue, plot_tsb_zones

# Fetch the shared dataset from session state
if 'summary_df' in st.session_state:
    summary_df = st.session_state['summary_df']
else:
    # Fallback just in case someone refreshes this page directly
    from utils.data_loader import parse_csv
    summary_df = parse_csv()

trimps = parse_granular(summary_df.copy())

st.subheader('Historical Performance Analysis')

# Date slider
min_date = trimps['Date'].min().to_pydatetime()
max_date = summary_df['Activity Date'].max().to_pydatetime()

selected_date = st.slider(
    '📅 Use the slider to view stats for that day:',
    min_value=min_date,
    max_value=max_date,
    value=max_date,  
    format='YYYY-MM-DD'
)

# Filter the metrics down to the single selected day
matched_row = trimps[trimps['Date'] == pd.Timestamp(selected_date)]

if not matched_row.empty:
    metrics = matched_row.iloc[0]
    ctl = metrics['CTL']
    atl = metrics['ATL']
    tsb = metrics['TSB']
    
    # Dynamic KPI cards
    col1, col2, col3 = st.columns(3)
    col1.metric('Fitness (CTL)', f'{ctl:.2f}')
    col2.metric('Fatigue (ATL)', f'{atl:.2f}')
    
    if tsb < -30:
        status, color = 'Overtraining Risk', 'inverse'
    elif -30 <= tsb < -10:
        status, color = 'Optimal Training', 'normal'
    elif -10 <= tsb <= 0 :
        status, color = 'Maintenance Zone', 'normal'
    else:
        status, color = 'Fresh / Recovery', 'normal'
        
    col3.metric('Form (TSB)', f'{tsb:.2f}', delta=status, delta_color=color)

st.markdown('---')

# Charts and documentation
chart_tab1, chart_tab2 = st.tabs(['📊 Fitness & Fatigue Dynamics', '🚦 Training Stress Balance (TSB)'])

with chart_tab1:
    st.altair_chart(plot_fitness_fatigue(trimps, selected_date), width='stretch') 
    
with chart_tab2:
    st.altair_chart(plot_tsb_zones(trimps, selected_date), width='stretch')
    
with st.expander('🔬 View Physiological Model Methodology'):
    st.markdown("""
    ## 📊 Understanding Fitness, Fatigue, and Form

    Training effectively requires balancing hard work with structured recovery. These metrics, derived from the Banister Impulse-Response model, transform raw workout data into a predictive view of an individual's physiology.
    
    ---
    
    ### 📈 The Core Metrics
    At the heart of the graphs are three primary metrics that track training load:
    
    | Metric | Full Name | Time Horizon | What it means |
    | :--- | :--- | :--- | :--- |
    | **CTL** | Chronic Training Load | ~42 Days | Fitness (long-term adaptation) |
    | **ATL** | Acute Training Load | ~7 Days | Fatigue (short-term exhaustion) |
    | **TSB** | Training Stress Balance | Daily | Form (readiness to perform) |
    
    ---
    
    ### 🔄 How They Interact
    The charts visualize the continuous tug-of-war between fitness and fatigue, with form informing us of the current dominating side.
    
    #### 1. Fitness (CTL)
    CTL represents the long-term trend of training volume and intensity. Because it is calculated as a 42-day exponentially weighted moving average (EWMA), it changes slowly.
    
    #### 2. Fatigue (ATL)
    ATL is highly volatile. Representing a short 7-day EWMA, it reacts immediately to hard workouts or back-to-back training days. If ATL climbs sharply above CTL, fatigue is accumulating rapidly.
    
    #### 3. Form (TSB)
    Form is the mathematical difference between current fitness and current fatigue:
    
    $$TSB = CTL - ATL$$
    
    * **When TSB > 0:** State of freshness; ideal for a race or performance test.
    * **When TSB < 0:** Accumulating training stress. While a negative number is required to stimulate adaptation and build fitness, staying deeply negative for too long risks injury or burnout.
    
    ### 🚦 Reading the Training Zones
    
    * **🟢 Freshness (Above 0):** Minimal fatigue; peak state for racing or performance testing.
    * **⚫ Maintenance Zone (0 to -10):** Fitness is maintained but not actively building.
    * **🟠 Optimal Training (-10 to -30):** Productive training stress with managed fatigue. The "sweet spot" for building fitness safely.
    * **🔴 Overtraining (Below -30):** High risk of injury, illness, or chronic fatigue. 
    
    """)
