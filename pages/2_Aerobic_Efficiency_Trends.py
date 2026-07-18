from sklearn.linear_model import LinearRegression
import streamlit as st

from utils.data_loader import parse_csv
from utils.functions import compute_heat_index
from utils.plots import plot_aero
import config

# Fetch the shared dataset from session state if available, else load it in
if 'summary_df' in st.session_state:
    summary_df = st.session_state['summary_df']
else:
    summary_df = parse_csv()

st.subheader('🫀 Aerobic Efficiency Trends')
st.write('Runs with over 15 minutes of moving time')

runs = summary_df[summary_df['Activity Type'] == 'Run'].copy()
steady_runs = runs[runs['workout_style'] == 'Steady State'].copy()

# Filter for valid pacing/HR and minimum moving time
steady_runs = steady_runs[(steady_runs['Average Grade Adjusted Pace'] > 0) & 
                          (steady_runs['Average Heart Rate'] > 0) & 
                          (steady_runs['Moving Time'] >= 900)]

# Heart Rate Reserve (HRR) corrects for resting HR offset so effort = 0 maps to denominator = 0,
# instead of dividing directly by raw avg_hr which has a nonzero floor at rest
hr_rest = config.DEFAULT_HR_REST
hr_max = config.DEFAULT_HR_MAX

steady_runs['hrr'] = (steady_runs['Average Heart Rate'] - hr_rest) / (hr_max - hr_rest)
steady_runs = steady_runs[steady_runs['hrr'] > 0]

# Calculate raw efficiency using %HRR instead of raw average heart rate
steady_runs['aero_ratio'] = steady_runs['Average Grade Adjusted Pace'] / steady_runs['hrr']

# Filter out runs missing weather data for the ML model
ml_df = steady_runs.dropna(subset=['Average Grade Adjusted Pace', 'hrr', 'temperature_2m', 'relative_humidity_2m']).copy()

ml_df['heat_index'] = compute_heat_index(ml_df['temperature_2m'], ml_df['relative_humidity_2m'])

# Initialize ML state variables
has_enough_data = len(ml_df) >= 50
model_trained = False
coef_heat = 0.0

if has_enough_data:
    X = ml_df[['Average Grade Adjusted Pace', 'heat_index']]
    y = ml_df['hrr']
    
    model = LinearRegression()
    model.fit(X, y)
    
    r_squared = model.score(X, y)
    n_samples = len(ml_df)
    
    coefs = dict(zip(X.columns, model.coef_))
    coef_heat = coefs['heat_index']
    coef_heat_bpm = coef_heat * (hr_max - hr_rest)
    
    # Define standard environmental baseline (28°C and 80% Humidity)
    standard_temp = 28.0
    standard_hum = 80.0
    standard_heat_index = compute_heat_index(standard_temp, standard_hum)
    
    # Create a hypothetical feature set: actual pace, but standard heat index
    X_standard = X.copy()
    X_standard['heat_index'] = standard_heat_index
    
    # Predict hypothetical %HRR in standard conditions
    ml_df['adjusted_hrr'] = model.predict(X_standard)
    
    # Recalculate efficiency using the normalized %HRR
    ml_df['adjusted_aero_ratio'] = ml_df['Average Grade Adjusted Pace'] / ml_df['adjusted_hrr']
    model_trained = True

# Only show the ML toggle if we actually have enough data to train the model safely
use_ml = False
if model_trained:
    use_ml = st.checkbox('🔮 **Show Weather-Adjusted True Fitness** (Normalized to Singapore Baseline 28°C / 80% Humidity)', value=False)
elif len(steady_runs) > 0:
    st.info(f'Keep running! You need at least 50 steady-state runs with weather data to unlock ML True Fitness tracking. (Currently have {len(ml_df)})')

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

# Personal environmental penalty
if model_trained:
    st.subheader('🧬 Personal Environmental Profile')
    st.write('Using linear regression against heat index (temperature + humidity combined), we can analyse how a specific body reacts to overall heat stress.')
    
    prof_col1, prof_col2, prof_col3 = st.columns(3)
    
    prof_col1.metric(label='🌡️ Heat Stress Penalty (per 1° Heat Index)', 
              value=f'{coef_heat_bpm:+.2f} bpm',
              delta='Heart Rate Impact', delta_color='inverse')
    
    prof_col2.metric(label='📊 Model Fit (R²)', value=f'{r_squared:.2f}')
    prof_col3.metric(label='🔢 Runs Used', value=f'{n_samples}')
        
    st.caption('*Heat index combines temperature and humidity into a single "feels like" value, since humidity\'s physiological cost scales with heat rather than adding independently. Metric indicates how much heart rate increases to maintain the same pace as heat stress worsens. R² shows how much of the heart-rate variance the model explains — closer to 1 means the two features (pace, heat index) are more reliably driving the prediction.*')
    
# Methodology Expander
with st.expander('🔬 View Aerobic Efficiency Methodology'):
    st.markdown("""
    ## 📈 Understanding Aerobic Efficiency

    Aerobic efficiency measures how much physical output (speed) your body can produce for a given cardiovascular input (heart rate).
    
    ---
    
    ### 🧮 The Calculation
    This dashboard calculates efficiency for steady-state runs using the following ratio:
    
    $$ \\text{Efficiency} = \\frac{\\text{Grade Adjusted Speed}}{\\text{Average Heart Rate}} $$
    
    *Note: We specifically filter for "Steady State" runs with over 15 minutes of moving time and use Grade Adjusted metrics to ensure elevation changes and interval spikes do not heavily skew the data.*
    
    ---
    
    ### 🔮 True Fitness (Weather Normalization)
    If you live in an environment with distinct seasons or high heat, your raw efficiency will artificially drop in the summer due to cardiac drift, masking your actual fitness gains.
    
    When **True Fitness** is enabled, a machine learning model isolates your pace and calculates what your heart rate *would have been* if the run occurred at a standard heat index equivalent to 28°C at 80% humidity — combining temperature and humidity into one "feels like" value rather than treating them as independent factors.
    
    ---
    
    ### 📊 How to Read the Chart
    
    * **Upward Trend ↗️:** Cardiovascular adaptation is occurring. You are getting fitter and can hold the same pace at a lower heart rate.
    * **Downward Trend ↘️:** This can indicate accumulated fatigue, a loss of fitness, or external environmental factors like severe heat stress.
    * **Daily Variance 📉📈:** Factors like sleep quality, caffeine intake, ambient temperature, and hydration will cause daily fluctuations.
    """)
