import pandas as pd
import numpy as np
from utils.data_loader import parse_gpx, parse_fit

# Calculates cumulative Banister TRIMP score from second-by-second time-series data.
def calc_trimps(df, hr_max=200, hr_rest=75, gender='male'):
    if df.empty or 'heart_rate' not in df.columns or 'timestamp' not in df.columns:
        return 0.0
    
    # Calculate time delta between points in minutes (handling variable sampling rates)
    delta_t_minutes = (df['timestamp']).diff().dt.total_seconds().fillna(1.0) / 60.0
    
    # Clean heart rate data
    hr = pd.to_numeric(df['heart_rate'], errors='coerce').ffill().bfill()
    
    # Calculate HR Reserve Fraction (clipped between 0 and 1 to prevent data anomalies)
    delta_hr = (hr - hr_rest) / (hr_max - hr_rest)
    delta_hr = delta_hr.clip(0.0, 1.0)
    
    # Compute the exponential weighting factor
    if gender.lower() == 'male':
        y = 0.64 * np.exp(1.92 * delta_hr)
    else:
        y = 0.86 * np.exp(1.67 * delta_hr)
        
    # Calculate instantaneous TRIMP per row: Time * Intensity * Weight
    row_trimp = delta_t_minutes * delta_hr * y
    
    # Return the cumulative sum of the workout
    return float(row_trimp.sum())

# Filters out interval training
def classify_workout_style(row):
    # Prevent division by zero
    if pd.isna(row['Average Speed']) or row['Average Speed'] == 0:
        return 'Unknown'
            
    moving_ratio = row['Moving Time']/row['Elapsed Time']
        
    if moving_ratio < 0.75:
        return 'Interval'
    else:
        return 'Steady State'

# Parses all granular data
def parse_granular(df):
    all_activity_frames = []

    for index, row in df.iterrows():
 
        target_filename = row.get('Filename') 
        activity_id = row.get('Activity ID')
        
        if pd.isna(target_filename):
            continue 
            
        try:
            if target_filename.endswith('.gpx') or target_filename.endswith('.gpx.gz'):
                time_series_df = parse_gpx(target_filename)
            elif target_filename.endswith('.fit') or target_filename.endswith('.fit.gz'):
                time_series_df = parse_fit(target_filename)
            else:
                continue
                
            time_series_df['Activity ID'] = activity_id
            all_activity_frames.append(time_series_df)
            
        except Exception as e:
            print(f"Error parsing file {target_filename}: {e}")
            continue

    if all_activity_frames:
        time_series_master = pd.concat(all_activity_frames, ignore_index=True)
        final_df = pd.merge(time_series_master, index_df, on='Activity ID', how='left')
        return final_df
        
    return pd.DataFrame()

# Fitness and Fatigue graph
def plot_form_fitness(df):
    fig = go.Figure()

    # Add Fatigue (ATL) Line
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['ATL'],
        name='Fatigue (7-day ATL)',
        line=dict(color='#ff4b4b', width=1.5),
        opacity=0.5
    ))

    # Add Fitness (CTL) Line filled to area
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['CTL'],
        name='Fitness (42-day CTL)',
        line=dict(color='#00f2fe', width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 242, 254, 0.1)'
    ))

    # Add Form (TSB) Line
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['TSB'],
        name='Form (TSB)',
        line=dict(color='#ffb300', width=2),
    ))

    # Add a baseline threshold line at 0 for TSB
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    # Styling for Dark Mode Dashboard compatibility
    fig.update_layout(
        title="Training Load Trends (Form & Fitness)",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, title="Date"),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', title="Stress Score / Load"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    return fig

# Display in Streamlit under your 'Aerobic Efficiency Trends' tab
st.plotly_chart(plot_form_fitness(daily_df), use_container_width=True)
