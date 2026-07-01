import streamlit as st

from utils.data_loader import parse_csv
from utils.plots import plot_aero

st.subheader('🫀 Aerobic Efficiency Trends')
st.write('Running')

# Isolate and calculate running data
runs = summary_df[summary_df['Activity Type'] == 'Run'].copy()
runs['Workout Style'] = runs.apply(classify_workout_style, axis=1)
steady_runs = runs[runs['Workout Style'] == 'Steady State'].copy()

steady_runs = steady_runs[(steady_runs['Average Grade Adjusted Pace'] > 0) & (steady_runs['Distance'] >= 1000)]
steady_runs['aero_ratio'] = steady_runs['Average Grade Adjusted Pace'] / steady_runs['Average Heart Rate']

run_chart_data = (
    steady_runs.dropna(subset=['Activity Date', 'aero_ratio'])
    .sort_values('Activity Date')
    .copy()
)

if not run_chart_data.empty:
    st.altair_chart(plot_aero(run_chart_data), width='stretch')
else:
    st.warning('⚠️ No valid running rows containing both Heart Rate and Speed data were found to plot.')

# Methodology Expander
with st.expander('🔬 View Aerobic Efficiency Methodology'):
    st.markdown("""
    ## 📈 Understanding Aerobic Efficiency

    Aerobic efficiency measures how much physical output (speed) your body can produce for a given cardiovascular input (heart rate).
    
    ---
    
    ### 🧮 The Calculation
    This dashboard calculates efficiency for steady-state runs using the following ratio:
    
    $$ \\text{Efficiency} = \\frac{\\text{Grade Adjusted Speed}}{\\text{Average Heart Rate}} $$
    
    *Note: We specifically filter for "Steady State" runs and use Grade Adjusted metrics to ensure elevation changes and interval spikes do not heavily skew the data.*
    
    ---
    
    ### 📊 How to Read the Chart
    
    * **Upward Trend ↗️:** Cardiovascular adaptation is occurring. You are getting fitter and can hold the same pace at a lower heart rate.
    * **Downward Trend ↘️:** This can indicate accumulated fatigue, a loss of fitness, or external environmental factors like severe heat stress (which causes your heart rate to spike for the same effort).
    * **Daily Variance 📉📈:** Factors like sleep quality, caffeine intake, ambient temperature, and hydration will cause daily fluctuations. Focus on the long-term trendline rather than the individual dots!
    """)
