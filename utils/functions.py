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

# Form and Fitness graph
def plot_form_fitness_altair(df):
    # 1. Base configuration with universal X-axis and tooltips
    base = alt.Chart(df).encode(
        x=alt.X('Date:T', title='Date'),
        tooltip=[
            alt.Tooltip('Date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip('CTL:Q', title='🏋️ Fitness (CTL)', format='.1f'),
            alt.Tooltip('ATL:Q', title='🔥 Fatigue (ATL)', format='.1f'),
            alt.Tooltip('TSB:Q', title='📈 Form (TSB)', format='.1f')
        ]
    )

    # 2. Fitness (CTL) - Neon Blue Area + Solid Line
    ctl_area = base.mark_area(color='#00f2fe', opacity=0.08).encode(
        y=alt.Y('CTL:Q', title='Stress Units / Load')
    )
    ctl_line = base.mark_line(color='#00f2fe', strokeWidth=2.5).encode(y='CTL:Q')

    # 3. Fatigue (ATL) - Red Muted Line
    atl_line = base.mark_line(color='#ff4b4b', strokeWidth=1.5, opacity=0.6).encode(y='ATL:Q')

    # 4. Form (TSB) - Amber High-Contrast Line
    tsb_line = base.mark_line(color='#ffb300', strokeWidth=2).encode(y='TSB:Q')

    # 5. Static Dashed Baseline at 0 Balance
    baseline = alt.Chart(df).mark_rule(
        color='rgba(255, 255, 255, 0.25)', 
        strokeDash=[4, 4]
    ).encode(
        y=alt.datum(0)
    )

    # 6. Combine layers, apply titles, and make it interactive (pan/zoom)
    chart = alt.layer(
        ctl_area, ctl_line, atl_line, tsb_line, baseline
    ).properties(
        title="Training Load Trends (Form & Fitness)",
        height=400
    ).interactive(
        bind_y=False  # Only lock zoom/pan to the X-axis (Timeline)
    )

    return chart
