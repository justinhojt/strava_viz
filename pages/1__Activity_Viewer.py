import streamlit as st
import pandas as pd
import altair as alt

from utils.data_loader import parse_csv, parse_gpx, parse_fit
from utils.functions import parse_granular, classify_workout_style

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

# Key Performance Indicators
selected_row = filtered_summary[filtered_summary['Filename'] == target_filename].iloc[0]

time = f'{selected_row["Moving Time"] // 60:.0f}m {selected_row["Moving Time"] % 60:.0f}s'
dist_m = f'{selected_row["Distance"]:.0f} m'
dist_km = f'{selected_row["Distance"] / 1000:.2f} km'
avg_hr = f'{selected_row["Average Heart Rate"]:.0f} bpm'
max_hr = f'{selected_row["Max Heart Rate"]:.0f} bpm'
cal = f'{selected_row["Calories"]:.0f} cal'

adjusted_trimp = get_trimp_for_row(selected_row, time_series_df)
trimp = f'{adjusted_trimp:.2f}'

seconds_100m = selected_row['Moving Time'] / (selected_row['Distance'] / 100) if selected_row['Distance'] > 0 else 0
pace_100m = f'{seconds_100m // 60:.0f}m {seconds_100m % 60:.0f}s/100m'

seconds_km = selected_row['Moving Time'] / (selected_row['Distance'] / 1000) if selected_row['Distance'] > 0 else 0
pace_km = f'{seconds_km // 60:.0f}m {seconds_km % 60:.0f}s/km'

st.markdown('### ⚡ Session Overview')
top_left, top_right = st.columns([1.5, 1])

with top_left:
    if selected_row['Activity Type'] in ['Workout', 'Weight Training']:
        r1_col1, r1_col2, r1_col3 = st.columns(3)
        r1_col1.metric('Moving Time', time)
        r1_col2.metric('Average Heart Rate', avg_hr)
        r1_col3.metric('Maximum Heart Rate', max_hr)
        
        r2_col1, r2_col2, r2_col3 = st.columns(3)
        r2_col1.metric('Training Intensity Score', trimp)
        
    elif selected_row['Activity Type'] == 'Swim':
        r1_col1, r1_col2, r1_col3 = st.columns([1, 1, 1.3])
        r1_col1.metric('Distance', dist_m)
        r1_col2.metric('Moving Time', time)
        r1_col3.metric('Pace', pace_100m)
        
        r2_col1, r2_col2, r2_col3 = st.columns([1, 1, 1.3])
        r2_col1.metric('Average Heart Rate', avg_hr)
        r2_col2.metric('Maximum Heart Rate', max_hr)
        r2_col3.metric('Training Intensity Score', trimp)

    else:
        r1_col1, r1_col2, r1_col3 = st.columns(3)
        r1_col1.metric('Distance', dist_km)
        r1_col2.metric('Moving Time', time)
        r1_col3.metric('Pace', pace_km)
        
        r2_col1, r2_col2, r2_col3 = st.columns(3)
        r2_col1.metric('Average Heart Rate', avg_hr)
        r2_col2.metric('Maximum Heart Rate', max_hr)
        r2_col3.metric('Training Intensity Score', trimp)

with top_right:
    # Heart Rate Zone Composition Chart
    if 'heart_rate' in time_series_df.columns and time_series_df['heart_rate'].notna().any():
        
        act_max_hr = 200.0
            
        # Calculate standard personalized zones based on % of Max HR
        bins = [0, act_max_hr * 0.60, act_max_hr * 0.70, act_max_hr * 0.80, act_max_hr * 0.90, 300]
        labels = ['Z1 Recovery', 'Z2 Aerobic', 'Z3 Tempo', 'Z4 Threshold', 'Z5 Anaerobic']
        
        # Map each second of data to a zone
        time_series_df['HR_Zone'] = pd.cut(time_series_df['heart_rate'], bins=bins, labels=labels)
        
        # Aggregate time (Assuming 1 row = 1 second for standard GPS files)
        zone_counts = time_series_df['HR_Zone'].value_counts().reset_index()
        zone_counts.columns = ['Zone', 'Time (s)']
        zone_counts['Minutes'] = zone_counts['Time (s)'] / 60
        
        # Define zone colors
        zone_colors = alt.Scale(
            domain=labels,
            range=['#95a5a6', '#3498db', '#2ecc71', '#f1c40f', '#e74c3c'] 
        )
        
        # Build horizontal bar chart
        hr_bar = alt.Chart(zone_counts).mark_bar(cornerRadiusEnd=2, height=18).encode(
            y=alt.Y('Zone:N', sort=labels, title=None, axis=alt.Axis(labelAngle=0, grid=False)),
            x=alt.X('Minutes:Q', title='Time (Minutes)'),
            color=alt.Color('Zone:N', scale=zone_colors, legend=None),
            tooltip=[
                alt.Tooltip('Zone:N', title='Zone'),
                alt.Tooltip('Minutes:Q', title='Minutes', format='.1f')
            ]
        ).properties(height=200)
        
        st.altair_chart(hr_bar, width='stretch')
    else:
        st.info("No Heart Rate data recorded for this session.")
        
st.markdown('---')
    
# Plot heart rate and elevation data 
if time_series_df['heart_rate'].notna().any():
    st.subheader('❤️ Heart Rate')
    hr_chart = (
        alt.Chart(time_series_df)
        .mark_line(color='#fc5200')  
        .encode(
            x=alt.X('graph_timestamp:T', title='Time'),
            y=alt.Y('heart_rate:Q', title='Heart Rate (bpm)', scale=alt.Scale(zero=False))
        )
    )
    st.altair_chart(hr_chart, width='stretch')

if time_series_df['elevation'].notna().any():
    st.subheader('⛰️ Elevation')
    elevation_chart = (
        alt.Chart(time_series_df)
        .mark_line(color='#fc5200')
        .encode(
            x=alt.X('graph_timestamp:T', title='Time'),
            y=alt.Y('elevation:Q', title='Elevation (m)', scale=alt.Scale(zero=False))
        )
    )
    st.altair_chart(elevation_chart, width='stretch')
