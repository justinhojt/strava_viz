import streamlit as st
import pandas as pd
import os
from utils.data_loader import parse_csv, parse_gpx, parse_fit

st.set_page_config(layout='wide')
st.title('Strava Archive Analytics Dashboard')

# Load macro data
try:
    summary_df = parse_csv()
    
    # Sidebar navigation/filtering
    st.sidebar.header('Activity Filter')
    activity_types = summary_df['Activity Type'].unique()
    selected_type = st.sidebar.selectbox('Select Activity Type', activity_types)
    
    # Filter summary data based on selection
    filtered_summary = summary_df[summary_df['Activity Type'] == selected_type]
    
    # Create an activity selector dropdown
    activity_map = {f'{row['Activity Date'].strftime('%Y-%m-%d')} - {row['Activity Name']}': row['Filename'] 
                    for _, row in filtered_summary.iterrows()}
    
    selected_activity_label = st.sidebar.selectbox('Select Specific Session', list(activity_map.keys()))
    target_filename = activity_map[selected_activity_label]
    
    # Key Performance Indicator Blocks
    selected_row = filtered_summary[filtered_summary['Filename'] == target_filename].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric('Distance', f'{selected_row['Distance']:.1f} m')
    col2.metric('Moving Time', f'{selected_row['Moving Time'] / 60:.1f} mins')
    if 'Average Heart Rate' in selected_row and pd.notna(selected_row['Average Heart Rate']):
        col3.metric('Avg Heart Rate', f'{int(selected_row["Average Heart Rate"])} bpm')
        
    # Load and parse the second-by-second granular details
    with st.spinner('Parsing data...'):
        if target_filename.endswith('.gpx') or target_filename.endswith('.gpx.gz'):
            time_series_df = parse_gpx(target_filename)
        elif target_filename.endswith('.fit') or target_filename.endswith('.fit.gz'):
            time_series_df = parse_fit(target_filename) 
        else:
            st.error('Unsupported file format.')
        
    if not time_series_df.empty:
        st.subheader('Granular Activity Stream')
        # Plot elevation profile or heart rate over time
        st.line_chart(time_series_df.set_index('timestamp')[['elevation']])
        st.line_chart(time_series_df.set_index('timestamp')[['hr']])
    else:
        st.warning('This specific activity has a file entry but contains no coordinate data streams.')

except Exception as e:
    st.error(f'Data Pipeline Error: {e}')
    st.info('Ensure your extracted Strava data folder is structured correctly in the root directory.')
