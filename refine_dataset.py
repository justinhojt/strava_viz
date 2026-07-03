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
def get_weather_with_timeout(session, lat, lon, activity_timestamp, retries=3):
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
    
    for attempt in range(retries):
        try:
            # Use session instead of requests, and increase timeout to 15s
            response = session.get(url, params=params, timeout=15)
            
            if response.status_code == 429:
                tqdm.write(' ⚠️ API Rate Limit Hit! Sleeping for 60 seconds...')
                time.sleep(60)
                return get_weather_with_timeout(session, lat, lon, activity_timestamp, retries)
                
            response.raise_for_status()
            data = response.json()
            
            return {
                'temp': data['hourly']['temperature_2m'][hour_index],
                'humidity': data['hourly']['relative_humidity_2m'][hour_index],
                'wind': data['hourly']['wind_speed_10m'][hour_index]
            }
            
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                tqdm.write(f"   ⏳ Read timeout on attempt {attempt + 1}. Retrying in 2 seconds...")
                time.sleep(2)
            else:
                tqdm.write(f"   ❌ API Timeout failed after {retries} attempts for {date_str}.")
        except Exception as e:
            tqdm.write(f"   ❌ Weather API Fetch Failed for {date_str}: {e}")
            break
            
    return {'temp': None, 'humidity': None, 'wind': None}

# Instantly extracts the first GPS coordinate without loading the whole file into memory
def extract_start_coords(filename):
    file_path = os.path.join('data', filename)
    if not os.path.exists(file_path):
        tqdm.write(f'   ⚠️ [File Missing] Cannot find file at: {file_path}')
        return None, None
        
    try:
        if filename.endswith('.gpx') or filename.endswith('.gpx.gz'):
            open_func = gzip.open if filename.endswith('.gz') else open
            mode = 'rt' if filename.endswith('.gz') else 'r'
            
            with open_func(file_path, mode, encoding='utf-8') as f:
                for line in f:
                    if '<trkpt' in line or '<wpt' in line:
                        lat_match = re.search(r'lat=["\']([^"\']+)["\']', line)
                        lon_match = re.search(r'lon=["\']([^"\']+)["\']', line)
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
    except Exception as e:
        tqdm.write(f'   ❌ [Parsing Error] Failed to read {filename}: {e}')
    return None, None

def main():
    df = clean_csv(CSV_PATH)
    
    # Ensure weather destination properties exist
    for col in ['temperature_2m', 'relative_humidity_2m', 'wind_speed_10m']:
        if col not in df.columns:
            df[col] = None
            
    tzf = TimezoneFinder()
    
    # Establish single persistent networking layer session
    with requests.Session() as session:
        for index, row in tqdm(df.iterrows(), total=df.shape[0], desc='Processing Activities'):
            filename = row['Filename']
            
            lat, lon = extract_start_coords(filename)
            
            if lat is None or lon is None:
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
            
            # Fetch weather using the optimized signature mapping parameters
            weather = get_weather_with_timeout(session, lat, lon, localized_date)
            
            df.at[index, 'temperature_2m'] = weather['temp']
            df.at[index, 'relative_humidity_2m'] = weather['humidity']
            df.at[index, 'wind_speed_10m'] = weather['wind']
            
            time.sleep(0.1)
            
    print(f' Saving complete refined csv back to database path: {OUTPUT_PATH}...')
    df.to_csv(OUTPUT_PATH, index=False)

if __name__ == '__main__':
    main()
