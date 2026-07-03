import pandas as pd
import logging
import time
from tqdm import tqdm

logging.disable(logging.WARNING)

from utils.data_loader import parse_fit, parse_gpx
from utils.functions import get_historical_weather

CSV_PATH = 'data/activities.csv'
OUTPUT_PATH = 'data/activities_ml_ready.csv'

def main():
    print(f'Loading {CSV_PATH}...')
    df = pd.read_csv(CSV_PATH)

    df = df.dropna(subset=['Filename'])
    
    df['temperature_2m'] = None
    df['relative_humidity_2m'] = None
    df['wind_speed_10m'] = None
    
    print('Extracting coordinates and fetching weather data...')
    
    # Wrap df.iterrows() in tqdm for a progress bar
    for index, row in tqdm(df.iterrows(), total=df.shape[0], desc='Processing Activities'):
        filename = row['Filename']
        date_str = pd.to_datetime(row['Activity Date']).strftime('%Y-%m-%d')
        
        try:
            if filename.endswith('.fit') or filename.endswith('.fit.gz'):
                track_df = parse_fit(filename)
            elif filename.endswith('.gpx') or filename.endswith('.gpx.gz'):
                track_df = parse_gpx(filename)
            else:
                continue
                
            if track_df.empty or 'latitude' not in track_df.columns:
                continue
                
            start_coords = track_df[['latitude', 'longitude']].dropna().iloc[0]
            lat = start_coords['latitude']
            lon = start_coords['longitude']
            
            weather = get_historical_weather(lat, lon, date_str)
            
            df.at[index, 'temperature_2m'] = weather['temp']
            df.at[index, 'relative_humidity_2m'] = weather['humidity']
            df.at[index, 'wind_speed_10m'] = weather['wind']
            
            # Respect API Limits
            time.sleep(0.5) 
            
        except Exception as e:
            pass

    df.to_csv(OUTPUT_PATH, index=False)
    print(f'\nSuccess! ML-ready dataset saved to {OUTPUT_PATH}')

if __name__ == '__main__':
    main()
