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
def parse_granular(csv):
    index_df = pd.read_csv(csv)
    all_activity_frames = []

    for index, row in index_df.iterrows():
 
        target_filename = row.get('Filename') 
        activity_id = row.get('Activity ID')
        
        if pd.isna(target_filename):
            continue 
            
        try:
            # 3. Route to your existing parsing functions based on extension
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
        return pd.concat(all_activity_frames, ignore_index=True)
    return pd.DataFrame()
