from fitparse import FitFile
import streamlit as st
import pandas as pd
import config
import gpxpy
import gzip
import os
import io

csv = config.ACTIVITIES_CSV

def process_timestamps(df):
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        if df['timestamp'].dt.tz is not None:
            df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Singapore').dt.tz_localize(None)
        else:
            df['timestamp'] = df['timestamp'] + pd.Timedelta(hours=8)
        df['graph_timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    return df

@st.cache_data
def parse_csv():
    if not os.path.exists(csv):
        raise FileNotFoundError(f'Could not find activities.csv at {csv}')
        
    df = pd.read_csv(csv)
    df['Activity Date'] = pd.to_datetime(df['Activity Date'])
    return df

@st.cache_data
def parse_gpx(gpx_filename):
    gpx_file = os.path.join('data', gpx_filename)
    
    if not os.path.exists(gpx_file):
        raise FileNotFoundError(f"File not found: {gpx_file}")
        
    open_func = gzip.open if gpx_file.endswith('.gz') else open
    mode = 'rt' if gpx_file.endswith('.gz') else 'r'
    
    with open_func(gpx_file, mode, encoding='utf-8') as f:
        gpx = gpxpy.parse(f)
            
    track_data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                hr = None
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
                
    return process_timestamps(pd.DataFrame(track_data))

@st.cache_data
def parse_fit(fit_filename):
    fit_file = os.path.join('data', fit_filename)
    
    if not os.path.exists(fit_file):
        raise FileNotFoundError(f"File not found: {fit_file}")
        
    open_func = gzip.open if fit_file.endswith('.gz') else open
    with open_func(fit_file, 'rb') as f:
        fitfile = FitFile(io.BytesIO(f.read()) if fit_file.endswith('.gz') else f)
            
    track_data = []
    for record in fitfile.get_messages('record'):
        values = record.get_values()
        
        ele = values.get('enhanced_altitude', values.get('altitude'))
        
        lat = values.get('position_lat')
        lon = values.get('position_long')
        if lat is not None and lon is not None:
            lat = lat * (180.0 / 2**31)
            lon = lon * (180.0 / 2**31)
            
        if 'timestamp' in values:
            track_data.append({
                'timestamp': values.get('timestamp'),
                'latitude': lat,
                'longitude': lon,
                'elevation': ele,
                'heart_rate': values.get('heart_rate')
            })
                
    return process_timestamps(pd.DataFrame(track_data))
