import pandas as pd
import requests
import logging
import gzip
import time
import os
import io
import re

from timezonefinder import TimezoneFinder
from fitparse import FitFile
from tqdm import tqdm

# Globally disable logging warnings to keep our progress bar clean
logging.disable(logging.WARNING)

CSV_PATH = 'data/activities.csv'
OUTPUT_PATH = 'data/activities_refined.csv'

# Parses and cleans the initial activities CSV
def clean_csv(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'Could not find activities CSV at {file_path}')
        
    df = pd.read_csv(file_path)
    df = df.dropna(subset=['Filename'])
    
    # Drop columns with all identical values
    df = df.loc[:, df.nunique() > 1]

    df = df.drop(columns=['Distance'])
    df = df.rename(columns={'Distance.1': 'Distance'})
    
    # Drop duplicate columns
    df = df.drop(columns=[*[col for col in df.columns if '.1' in col]], errors='ignore')
        
    return df

# Fetches weather based on the exact hour of the localized timestamp
def get_weather_with_timeout(lat, lon, activity_timestamp):
    url = 'https://archive-api.open-meteo.com/v1/archive'
    
    date_str = activity_timestamp.strftime('%Y-%m-%d')
    hour_index = activity_timestamp.hour
    
    params = {
        'latitude': lat,
        'longitude': lon,
        'start_date': date_str,
        'end_date': date_str,
        'hourly': ['temperature_2m', 'relative_humidity_2m', 'wind_speed_10m'],
        'timezone': 'auto'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 429:
            tqdm.write(' ⚠️ API Rate Limit Hit! Sleeping for 60 seconds...')
            time.sleep(60)
            return get_weather_with_timeout(lat, lon, activity_timestamp)
            
        response.raise_for_status()
        data = response.json()
        
        return {
            'temp': data['hourly']['temperature_2m'][hour_index],
            'humidity': data['hourly']['relative_humidity_2m'][hour_index],
            'wind': data['hourly']['wind_speed_10m'][hour_index]
        }
    except Exception as e:
        return {'temp': None, 'humidity': None, 'wind': None}

# Instantly extracts the first GPS coordinate without loading the whole file into memory
def extract_start_coords(filename):
    file_path = os.path.join('data', filename)
    if not os.path.exists(file_path):
        return None, None
        
    try:
        if filename.endswith('.gpx') or filename.endswith('.gpx.gz'):
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
                        if abs(lat) > 180: lat = lat * (180.0 / 2**31)
                        if abs(lon) > 180: lon = lon * (180.0 / 2**31)
                        return lat, lon
    except Exception:
        pass
    return None, None

def main():
    print(f'Loading and cleaning {CSV_PATH}...')
    df = clean_csv(CSV_PATH)
    
    # Filter for runs only
    activity_type_col = 'Activity Type' if 'Activity Type' in df.columns else 'type'
    if activity_type_col in df.columns:
        df = df[df[activity_type_col].astype(str).str.lower() == 'run']
        print(f'Successfully filtered dataset down to {df.shape[0]} Running activities.')
        
    # Initialize new columns
    df['temperature_2m'] = None
    df['relative_humidity_2m'] = None
    df['wind_speed_10m'] = None
    df['workout_style'] = 'Unknown'
    
    # Cast column to object type to prevent PyArrow strict string assignment errors
    df['Activity Date'] = df['Activity Date'].astype(object)
    
    # Initialize the timezone finder
    tzf = TimezoneFinder()

    for index, row in tqdm(df.iterrows(), total=df.shape[0], desc='Processing Runs'):
        filename = row['Filename']
        tqdm.write(f' → Processing file: {filename}')
        
        # Classify workout style (interval vs steady state)
        avg_speed = row.get('Average Speed')
        moving_time = row.get('Moving Time')
        elapsed_time = row.get('Elapsed Time')
        
        if pd.isna(avg_speed) or avg_speed == 0 or not elapsed_time:
            style = 'Unknown'
        elif (moving_time / elapsed_time) < 0.7:
            style = 'Interval'
        else:
            style = 'Steady State'
            
        df.at[index, 'workout_style'] = style
        
        # Extract coordinates
        lat, lon = extract_start_coords(filename)
            
        if lat is None or lon is None:
            tqdm.write('   [Skipped] No GPS data found. Weather columns will remain empty.')
            continue
            
        # Find the local timezone
        tz_name = tzf.timezone_at(lng=lon, lat=lat) 
        
        # Convert the timestamp dynamically
        raw_date = pd.to_datetime(row['Activity Date'])
        
        if tz_name:
            if raw_date.tz is not None:
                localized_date = raw_date.tz_convert(tz_name).tz_localize(None)
            else:
                localized_date = raw_date.tz_localize('UTC').tz_convert(tz_name).tz_localize(None)
        else:
            if raw_date.tz is not None:
                localized_date = raw_date.tz_convert('Asia/Singapore').tz_localize(None)
            else:
                localized_date = raw_date + pd.Timedelta(hours=8)
            
        # Update the dataframe with the true local time
        df.at[index, 'Activity Date'] = localized_date
        
        # Fetch weather using the localized timestamp
        weather = get_weather_with_timeout(lat, lon, localized_date)
        
        df.at[index, 'temperature_2m'] = weather['temp']
        df.at[index, 'relative_humidity_2m'] = weather['humidity']
        df.at[index, 'wind_speed_10m'] = weather['wind']
        
        time.sleep(0.1)
        
    df.to_csv(OUTPUT_PATH, index=False)
    print(f'\nSuccess! Dataset safely saved to {OUTPUT_PATH}')

if __name__ == '__main__':
    main()
