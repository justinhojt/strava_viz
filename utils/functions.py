import pandas as pd
import numpy as np
import altair as alt
from utils.data_loader import parse_gpx, parse_fit

# Calculates cumulative Banister TRIMP score from second-by-second time-series data.
def calc_trimps(df, hr_max=200, hr_rest=75, gender='male'):
    if df.empty or 'heart_rate' not in df or 'timestamp' not in df:
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
    workout_records = []

    for index, row in df.iterrows():
        target_filename = row.get('Filename') 
        activity_date = row.get('Date')       
        
        if pd.isna(target_filename): 
            continue
            
        try:
            if target_filename.endswith('.gpx') or target_filename.endswith('.gpx.gz'):
                time_series_df = parse_gpx(target_filename)
            elif target_filename.endswith('.fit') or target_filename.endswith('.fit.gz'):
                time_series_df = parse_fit(target_filename)
            else: 
                continue
 
            if not time_series_df.empty:
                trimp_score = calc_trimps(time_series_df)  
            else:
                trimp_score = 0
                
            workout_records.append({
                'Date': activity_date,
                'trimps': trimp_score
            })
            
        except Exception as e:
            print(f"Skipping {target_filename} due to error: {e}")
            continue

    if not workout_records:
        return pd.DataFrame(columns=['Date', 'trimps', 'CTL', 'ATL', 'TSB'])
        
    summary_df = pd.DataFrame(workout_records)
    daily_stress = summary_df.groupby('Date')['trimps'].sum().reset_index()

    daily_stress['Date'] = pd.to_datetime(daily_stress['Date'])
    daily_stress.set_index('Date', inplace=True)
    
    full_range = pd.date_range(start=daily_stress.index.min(), end=pd.to_datetime('today'), freq='D')
    trimps = daily_stress.reindex(full_range, fill_value=0).reset_index()
    trimps.rename(columns={'index': 'Date'}, inplace=True)
    
    trimps['CTL'] = trimps['trimps'].ewm(alpha=1/42, adjust=False).mean()
    trimps['ATL'] = trimps['trimps'].ewm(alpha=1/7, adjust=False).mean()
    trimps['TSB'] = trimps['CTL'].shift(1) - trimps['ATL'].shift(1)
    trimps['TSB'] = trimps['TSB'].fillna(0)
    
    return trimps
