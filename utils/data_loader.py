from fitparse import FitFile
import pandas as pd
import gpxpy
import gzip
import os
import io

csv = os.path.join('data', 'activities.csv')

def parse_csv():
    if not os.path.exists(csv):
        raise FileNotFoundError(f'Could not find activities.csv at {csv}')
        
    df = pd.read_csv(csv)

    # Drop rows that don't have an associated raw data file
    df = df.dropna(subset=['Filename'])

    # Drop blank columns or columns that contain only 1 unique non-blank value 
    df = df.loc[:, df.nunique() > 1]

    # Drop unstandardized 'Distance' (mixed units) and use the 2nd standardized meter-based column instead
    df = df.drop(columns=['Distance'])
    df = df.rename(columns={'Distance.1': 'Distance'})

    # Drop duplicated columns
    df = df.drop(columns=[col for col in df.columns if '.1' in col])
  
    # Standardize date column to datetime data type
    df['Activity Date'] = pd.to_datetime(df['Activity Date'])
  
    return df

def parse_gpx(gpx_filename):
    gpx_file = os.path.join('data', gpx_filename)
    
    if not os.path.exists(gpx_file):
        raise FileNotFoundError(f"File not found: {gpx_file}")
        
    if gpx_file.endswith('.gz'):
        with gzip.open(gpx_file, 'rt', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)
    else:
        with open(gpx_file, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)
            
    track_data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                hr = None
                # Extract heart rate data if available
                if point.extensions:
                    for ext in point.extensions:
                        if 'hr' in ext.tag:
                            hr = int(ext.text)
                            
                track_data.append({
                    'timestamp': point.time,
                    'latitude': point.latitude,
                    'longitude': point.longitude,
                    'elevation': point.elevation,
                    'heart_rate': hr
                })
                
    df = pd.DataFrame(track_data)
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def parse_fit(fit_filename):
    fit_file = os.path.join('data', fit_filename)
    
    if not os.path.exists(fit_file):
        raise FileNotFoundError(f"File not found: {fit_file}")
        
    if fit_file.endswith('.gz'):
        with gzip.open(fit_file, 'rb') as f:
            fitfile = FitFile(io.BytesIO(f.read()))
    else:
        with open(fit_file, 'rb') as f:
            fitfile = FitFile(f)
            
    track_data = []
    sc_to_deg = 180.0 / (2**31)  # Factor to convert semicircles to degrees
    
    # Iterate over every second-by-second data point message
    for record in fitfile.get_messages('record'):
        values = record.get_values()
        
        # Extract and convert coordinates if they exist
        lat = values.get('position_lat')
        lon = values.get('position_long')
        if lat is not None: lat = lat * sc_to_deg
        if lon is not None: lon = lon * sc_to_deg
        
        # Garmin devices often use 'enhanced_altitude' for better precision
        ele = values.get('enhanced_altitude')
        if ele is None:
            ele = values.get('altitude')
            
        if 'timestamp' in values:
            track_data.append({
                'timestamp': values.get('timestamp'),
                'latitude': lat,
                'longitude': lon,
                'elevation': ele,
                'heart_rate': values.get('heart_rate')
            })
                
    df = pd.DataFrame(track_data)
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df
