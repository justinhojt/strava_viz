import pandas as pd

# Calculates cumulative Banister TRIMP score from second-by-second time-series data.
def calc_trimp(df, hr_max=200, hr_rest=80, gender='male'):
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
