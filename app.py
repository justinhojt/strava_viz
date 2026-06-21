import streamlit as st
import altair as alt
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
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    time = f'{selected_row['Moving Time'] // 60:.0f}m {selected_row['Moving Time'] % 60:.0f}s'
    dist_m = f'{selected_row['Distance']:.0f} m'
    dist_km = f'{selected_row['Distance']/1000:.2f} km'
    avg_hr = f'{selected_row["Average Heart Rate"]:.0f} bpm'
    max_hr = f'{selected_row["Max Heart Rate"]:.0f} bpm'
    cal = f'{selected_row['Calories']:.0f} cal'
    #pace_100m = f'{selected_row['Moving Time']/(selected_row['Distance']/100):.2f} 

    if selected_row['Activity Type'] == 'Workout':
        col1.metric('Moving Time', time)
        col2.metric('Average Heart Rate', avg_hr)
        col3.metric('Maximum Heart Rate', max_hr)
        col4.metric('Calories Burned', cal)
        
    elif selected_row['Activity Type'] == 'Swim':
        col1.metric('Distance', dist_m)
        col2.metric('Moving Time', time)
        col3.metric('Average Heart Rate', avg_hr)
        col4.metric('Maximum Heart Rate', max_hr)
        col5.metric('Calories Burned', cal)

    else:
        col1.metric('Distance', dist_km)
        col2.metric('Moving Time', time)
        col3.metric('Average Heart Rate', avg_hr)
        col4.metric('Maximum Heart Rate', max_hr)
        col5.metric('Calories Burned', cal)
        
    # Load and parse the second-by-second granular details
    with st.spinner('Parsing data...'):
        if target_filename.endswith('.gpx') or target_filename.endswith('.gpx.gz'):
            time_series_df = parse_gpx(target_filename)
        elif target_filename.endswith('.fit') or target_filename.endswith('.fit.gz'):
            time_series_df = parse_fit(target_filename) 
        else:
            st.error('Unsupported file format.')

    if time_series_df.empty:
        st.warning('This specific activity has a file entry but contains no coordinate data streams.')
        
    if time_series_df['heart_rate'].notna().any():
        st.subheader('Heart Rate')
        hr_chart = (
            alt.Chart(time_series_df)
            .mark_line(color='#fc5200')  
            .encode(
                x=alt.X('timestamp:T', title='Time', scale=alt.Scale(type='utc')),
                y=alt.Y('heart_rate:Q', title='Heart Rate (bpm)', scale=alt.Scale(zero=False))
            )
        )
        st.altair_chart(hr_chart, use_container_width=True)

    if time_series_df['elevation'].notna().any():
        st.subheader('Elevation')
        elevation_chart = (
            alt.Chart(time_series_df)
            .mark_line(color='#fc5200')
            .encode(
                x=alt.X('timestamp:T', title='Time', scale=alt.Scale(type='utc')),
                y=alt.Y('elevation:Q', title='Elevation (m)', scale=alt.Scale(zero=False))
            )
        )
        st.altair_chart(elevation_chart, use_container_width=True)

except Exception as e:
    st.error(f'Data Pipeline Error: {e}')
    st.info('Ensure your extracted Strava data folder is structured correctly in the root directory.')
