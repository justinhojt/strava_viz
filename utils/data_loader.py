import pandas as pd
import gpxpy
import gzip
import os

csv = os.path.join('data', 'activities.csv')

def load_summary_data():
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

def parse_raw_gpx(relative_filename_path):
    """Parses second-by-second streams from a local GPX or GPX.GZ file."""
    full_path = os.path.join(DATA_DIR, relative_filename_path)
    
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")
        
    # Open normally if it's raw XML, or use gzip if it's compressed
    if full_path.endswith('.gz'):
        with gzip.open(full_path, 'rt', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)
    else:
        with open(full_path, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)
            
    track_data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                hr = None
                # Safely extract heart rate data from XML extensions if available
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
