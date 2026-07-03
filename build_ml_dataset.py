import pandas as pd
import requests
import time
import os
import gzip
import io
import re
import logging
from tqdm import tqdm
from fitparse import FitFile

# Globally disable logging warnings to keep our progress bar clean
logging.disable(logging.WARNING)

CSV_PATH = 'data/activities.csv'
OUTPUT_PATH = 'data/activities_ml_ready.csv'

def get_weather_with_timeout(lat, lon, activity_date):
    """Fetches weather data with a strict 10-second timeout."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": activity_date,
        "end_date": activity_date,
        "hourly": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
        "timezone": "auto"
    }
    try:
        # THE CRITICAL TIMEOUT
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 429:
            tqdm.write(" ⚠️ API Rate Limit Hit! Sleeping for 60 seconds...")
            time.sleep(60)
            return get_weather_with_timeout(lat, lon, activity_date)
            
        response.raise_for_status()
        data = response.json()
        return {
            "temp": data['hourly']['temperature_2m'][0],
            "humidity": data['hourly']['relative_humidity_2m'][0],
            "wind": data['hourly']['wind_speed_10m'][0]
        }
    except Exception as e:
        return {"temp": None, "humidity": None, "wind": None}

def extract_start_coords(filename):
    """Instantly rips the first GPS coordinate out of files without loading the whole file into memory."""
    file_path = os.path.join('data', filename)
    if not os.path.exists(file_path):
        return None, None
        
    try:
        if filename.endswith('.gpx') or filename.endswith('.gpx.gz'):
            # Bypass gpxpy. Read raw text to find the first <trkpt> instantly.
            open_func = gzip.open if filename.endswith('.gz') else open
            mode = 'rt' if filename.endswith('.gz') else 'r'
            
            with open_func(file_path, mode, encoding='utf-8') as f:
                for line in f:
                    if '<trkpt' in line or '<wpt' in line:
                        lat_match = re.search(r'lat="([^"]+)"', line)
                        lon_match = re.search(r'lon="([^"]+)"', line)
                        if lat_match and lon_match:
                            return float(lat_match.group(1)), float(lon_match.group(1))
            return None, None

        elif filename.endswith('.fit') or filename.endswith('.fit.gz'):
            open_func = gzip.open if filename.endswith('.gz') else open
            with open_func(file_path, 'rb') as f:
                fitfile = FitFile(io.BytesIO(f.read()) if filename.endswith('.gz') else f)
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
        
    df['temperature_2m'] = None
    df['relative_humidity_2m'] = None
    df['wind_speed_10m'] = None

    for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing Runs"):
        filename = row['Filename']
        date_str = pd.to_datetime(row['Activity Date']).strftime('%Y-%m-%d')
        
        tqdm.write(f" → Processing file: {filename}")
        
        lat, lon = extract_start_coords(filename)
            
        if lat is None or lon is None:
            tqdm.write(f"   [Skipped] No GPS data found.")
            continue
            
        # Fetch weather using the SAFE function with a timeout
        weather = get_weather_with_timeout(lat, lon, date_str)
        
        df.at[index, 'temperature_2m'] = weather['temp']
        df.at[index, 'relative_humidity_2m'] = weather['humidity']
        df.at[index, 'wind_speed_10m'] = weather['wind']
        
        time.sleep(0.5)
        
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSuccess! Dataset safely saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
