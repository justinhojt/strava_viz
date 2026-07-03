import streamlit as st
import numpy as np
from scikit-learn.linear_model import LinearRegression

from utils.data_loader import parse_csv
from utils.plots import plot_aero
from utils.functions import classify_workout_style

# Fetch the shared dataset from session state
if 'summary_df' in st.session_state:
    summary_df = st.session_state['summary_df']
else:
    # Fallback just in case someone refreshes this page directly
    summary_df = parse_csv()

st.subheader('🫀 Aerobic Efficiency Trends')

runs = summary_df[summary_df['Activity Type'] == 'Run'].copy()
steady_runs = runs[runs['Workout Style'] == 'Steady State'].copy()

# Filter for valid pacing/HR and minimum distance
steady_runs = steady_runs[(steady_runs['Average Grade Adjusted Pace'] > 0) & 
                          (steady_runs['Average Heart Rate'] > 0) & 
                          (steady_runs['Distance'] >= 1000)]

# Calculate standard Raw Efficiency
steady_runs['aero_ratio'] = steady_runs['Average Grade Adjusted Pace'] / steady_runs['Average Heart Rate']

# Filter out runs missing weather data for the ML model
ml_df = steady_runs.dropna(subset=['Average Grade Adjusted Pace', 'Average Heart Rate', 'temperature_2m', 'relative_humidity_2m']).copy()

# Initialize ML state variables
has_enough_data = len(ml_df) >= 15
model_trained = False
coef_temp = 0.0
coef_hum = 0.0

if has_enough_data:
    # Oredict Heart Rate based on how fast you were going and the weather
    X = ml_df[['Average Grade Adjusted Pace', 'temperature_2m', 'relative_humidity_2m']]
    y = ml_df['Average Heart Rate']
    
    model = LinearRegression()
    model.fit(X, y)
    
    coef_temp = model.coef_[1]
    coef_hum = model.coef_[2]
    
    # Define standard environmental baseline (28°C and 80% Humidity)
    standard_temp = 28.0
    standard_hum = 80.0
    
    # Create a hypothetical feature set: Actual Pace, but Perfect Weather
    X_standard = X.copy()
    X_standard['temperature_2m'] = standard_temp
    X_standard['relative_humidity_2m'] = standard_hum
    
    # Predict hypothetical HR in standard conditions
    ml_df['adjusted_hr'] = model.predict(X_standard)
    
    # Recalculate efficiency using the normalized HR
    ml_df['adjusted_aero_ratio'] = ml_df['Average Grade Adjusted Pace'] / ml_df['adjusted_hr']
    model_trained = True

st.write('Running')

# Only show the ML toggle if we actually have enough data to train the model safely
use_ml = False
if model_trained:
    use_ml = st.checkbox("🔮 **Show Weather-Adjusted True Fitness** (Normalized to Singapore Baseline 28°C / 80% Humidity)", value=False)
elif len(steady_runs) > 0:
    st.info(f"Keep running! You need at least 15 steady-state runs with weather data to unlock ML True Fitness tracking. (Currently have {len(ml_df)})")

# Determine which data to plot based on the user's toggle
if use_ml and model_trained:
    # Swap the metric temporarily for the plotting function
    plot_df = ml_df.copy()
    plot_df['aero_ratio'] = plot_df['adjusted_aero_ratio'] 
else:
    plot_df = steady_runs.copy()

run_chart_data = (
    plot_df.dropna(subset=['Activity Date', 'aero_ratio'])
    .sort_values('Activity Date')
    .copy()
)

if not run_chart_data.empty:
    st.altair_chart(plot_aero(run_chart_data), width='stretch')
else:
    st.warning('⚠️ No valid running rows containing both Heart Rate and Speed data were found to plot.')


# Personal Heat Penalty
if model_trained:
    st.markdown("### 🧬 Your Personal Environmental Profile")
    st.write("Using Multiple Linear Regression, we analyzed how your specific physiology reacts to the elements.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="🌡️ Heat Penalty (per 1°C)", 
                  value=f"{coef_temp:+.2f} bpm",
                  delta="Heart Rate Impact", delta_color="inverse")
    with col2:
        st.metric(label="💧 Humidity Penalty (per 1%)", 
                  value=f"{coef_hum:+.2f} bpm",
                  delta="Heart Rate Impact", delta_color="inverse")
        
    st.caption("*Metrics indicate how much your heart rate increases to maintain the same pace as weather worsens.*")

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
    
    ### 🔮 True Fitness (Weather Normalization)
    If you live in an environment with distinct seasons or high heat, your raw efficiency will artificially drop in the summer due to cardiac drift, masking your actual fitness gains.
    
    When **True Fitness** is enabled, a machine learning model isolates your pace and calculates what your heart rate *would have been* if the run occurred in an optimal 15°C environment at 50% humidity.
    
    ---
    
    ### 📊 How to Read the Chart
    
    * **Upward Trend ↗️:** Cardiovascular adaptation is occurring. You are getting fitter and can hold the same pace at a lower heart rate.
    * **Downward Trend ↘️:** This can indicate accumulated fatigue, a loss of fitness, or external environmental factors like severe heat stress.
    * **Daily Variance 📉📈:** Factors like sleep quality, caffeine intake, ambient temperature, and hydration will cause daily fluctuations. Focus on the long-term trendline rather than the individual dots!
    """)
