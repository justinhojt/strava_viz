import pandas as pd
import logging
import time
import os
import gzip
import io
from tqdm import tqdm
from fitparse import FitFile
import gpxpy

# Globally disable logging warnings to keep our progress bar clean
logging.disable(logging.WARNING)

# Import your weather function
from utils.functions import get_historical_weather

CSV_PATH = 'data/activities.csv'
OUTPUT_PATH = 'data/activities_ml_ready.csv'

def extract_start_coords(filename):
    """Instantly grabs the very first GPS coordinate and exits to avoid freezing."""
    file_path = os.path.join('data', filename)
    if not os.path.exists(file_path):
        return None, None
        
    try:
        if filename.endswith('.gpx') or filename.endswith('.gpx.gz'):
            if filename.endswith('.gz'):
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    gpx = gpxpy.parse(f)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    gpx = gpxpy.parse(f)
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        if point.latitude and point.longitude:
                            return point.latitude, point.longitude

        elif filename.endswith('.fit') or filename.endswith('.fit.gz'):
            if filename.endswith('.gz'):
                with gzip.open(file_path, 'rb') as f:
                    fitfile = FitFile(io.BytesIO(f.read()))
            else:
                with open(file_path, 'rb') as f:
                    fitfile = FitFile(f)
            for record in fitfile.get_messages('record'):
                values = record.get_values()
                if 'position_lat' in values and 'position_long' in values:
                    lat, lon = values['position_lat'], values['position_long']
                    if lat and lon:
                        # Convert Garmin semicircles to standard degrees
                        if abs(lat) > 180: lat = lat * (180 / 2**31)
                        if abs(lon) > 180: lon = lon * (180 / 2**31)
                        return lat, lon
    except Exception:
        pass
    return None, None

def main():
    print(f"Loading {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    df = df.dropna(subset=['Filename'])
    
    # --- FILTER FOR RUNS ONLY ---
    activity_type_col = 'Activity Type' if 'Activity Type' in df.columns else 'type'
    if activity_type_col in df.columns:
        df = df[df[activity_type_col].astype(str).str.lower() == 'run']
        print(f"Successfully filtered dataset down to {df.shape[0]} Running activities.")
    else:
        print("Warning: Could not find an Activity Type column to filter runs.")
        
    df['temperature_2m'] = None
    df['relative_humidity_2m'] = None
    df['wind_speed_10m'] = None
    
    has_csv_coords = 'Start Latitude' in df.columns and 'Start Longitude' in df.columns
    if has_csv_coords:
        print("Found native GPS coordinates in CSV! Bypassing raw file parsing entirely...")
    else:
        print("Extracting starting coordinates from raw files (optimized mode)...")

    for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing Runs"):
        filename = row['Filename']
        date_str = pd.to_datetime(row['Activity Date']).strftime('%Y-%m-%d')
        
        # Diagnostic logging: prints out before the work happens
        tqdm.write(f" → Processing file: {filename} ({date_str})")
        
        try:
            if has_csv_coords and pd.notna(row['Start Latitude']):
                lat, lon = row['Start Latitude'], row['Start Longitude']
            else:
                lat, lon = extract_start_coords(filename)
                
            if lat is None or lon is None:
                continue
                
            # Fetch the weather data
            weather = get_historical_weather(lat, lon, date_str)
            
            df.at[index, 'temperature_2m'] = weather['temp']
            df.at[index, 'relative_humidity_2m'] = weather['humidity']
            df.at[index, 'wind_speed_10m'] = weather['wind']
            
            time.sleep(0.5)
            
        except Exception:
            pass
        
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSuccess! Dataset safely saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
