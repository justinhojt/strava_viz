import config
import pandas as pd
import numpy as np
import streamlit as st
from utils.data_loader import parse_gpx, parse_fit

# Calculates cumulative Banister TRIMP score from second-by-second time-series data
def calc_trimps(df, hr_max=config.DEFAULT_HR_MAX, hr_rest=config.DEFAULT_HR_REST, gender=config.DEFAULT_GENDER):
    if df.empty or 'heart_rate' not in df or 'timestamp' not in df:
        return 0.0
    
    delta_t_minutes = pd.to_datetime(df['timestamp']).diff().dt.total_seconds().fillna(1.0) / 60.0
    
    hr = pd.to_numeric(df['heart_rate'], errors='coerce').ffill().bfill()
    
    delta_hr = (hr - hr_rest) / (hr_max - hr_rest)
    delta_hr = delta_hr.clip(0.0, 1.0)
    
    # Compute the exponential weighting factor
    if gender.lower() == 'male':
        y = 0.64 * np.exp(1.92 * delta_hr)
    else:
        y = 0.86 * np.exp(1.67 * delta_hr)
        
    row_trimp = delta_t_minutes * delta_hr * y
    
    return float(row_trimp.sum())

# TRIMP score fetcher, adjusts for workout
def get_trimp_for_row(row, time_series_df=None):
    trimp = 0.0
    
    if time_series_df is not None and not time_series_df.empty:
        trimp = calc_trimps(time_series_df)
        
    # Default to 40 TRIMP score/h as heart rate data underestimates weightlifting efforts
    if row['Activity Type'] in ['Workout', 'Weight Training']:
        return (row['Moving Time']/3600) * 40 
            
    return trimp

# Filters out interval training
def classify_workout_style(row):
    if pd.isna(row['Average Speed']) or row['Average Speed'] == 0:
        return 'Unknown'

    if row['Moving Time']/row['Elapsed Time'] < 0.75:
        return 'Interval'
    else:
        return 'Steady State'

# Parses all granular data
@st.cache_data
def parse_granular(df):
    workout_records = []

    for index, row in df.iterrows():
        target_filename = row.get('Filename') 
        activity_date = row.get('Activity Date')       
        activity_type = row.get('Activity Type') 
        
        trimp_score = 0
        file_parsed_successfully = False
        
        if not pd.isna(target_filename): 
            try:
                if target_filename.endswith('.gpx') or target_filename.endswith('.gpx.gz'):
                    time_series_df = parse_gpx(target_filename)
                elif target_filename.endswith('.fit') or target_filename.endswith('.fit.gz'):
                    time_series_df = parse_fit(target_filename)
                
                trimp_score = get_trimp_for_row(row, time_series_df)
                
            except Exception as e:
                trimp_score = get_trimp_for_row(row, None)

        if trimp_score > 0 or file_parsed_successfully:
            workout_records.append({
                'Date': activity_date,
                'trimps': trimp_score
            })
            
    if not workout_records:
        return pd.DataFrame(columns=['Date', 'trimps', 'CTL', 'ATL', 'TSB'])
        
    summary_df = pd.DataFrame(workout_records)
    summary_df['Date'] = pd.to_datetime(summary_df['Date']).dt.normalize()
    
    daily_stress = summary_df.groupby('Date')['trimps'].sum().reset_index()
    daily_stress.set_index('Date', inplace=True)
    
    active_days = daily_stress[daily_stress['trimps'] > 0]
    if not active_days.empty:
        start_date = active_days.index.min()
    else:
        start_date = daily_stress.index.min()
        
    if pd.isna(start_date):
        return pd.DataFrame(columns=['Date', 'trimps', 'CTL', 'ATL', 'TSB'])
        
    end_date = pd.to_datetime('today').normalize()
    full_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    trimps = daily_stress.reindex(full_range, fill_value=0).reset_index()
    trimps.rename(columns={'index': 'Date'}, inplace=True)
    
    trimps['CTL'] = trimps['trimps'].ewm(alpha=1/42, adjust=False).mean()
    trimps['ATL'] = trimps['trimps'].ewm(alpha=1/7, adjust=False).mean()
    trimps['TSB'] = trimps['CTL'].shift(1) - trimps['ATL'].shift(1)
    trimps['TSB'] = trimps['TSB'].fillna(0)
    
    return trimps
