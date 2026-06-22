import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from utils.data_loader import parse_csv, parse_gpx, parse_fit

st.set_page_config(layout='wide')
st.title('Strava Archive Analytics Dashboard')

# Calculates cumulative Banister TRIMP score from second-by-second time-series data.
def calc_trimp(df, hr_max=200, hr_rest=80, gender='male'):
    if df.empty or 'heart_rate' not in df.columns or 'timestamp' not in df.columns:
        return 0.0
    
    # Calculate time delta between points in minutes (handling variable sampling rates)
    delta_t_minutes = (df['timestamp']).diff().dt.total_seconds().fillna(1.0) / 60.0
    
    # Clean heart rate data
    hr = pd.to_numeric(df['heart_rate'], errors='coerce').ffill().bfill()
    
    # Calculate HR Reserve Fraction (clipped between 0 and 1 to prevent data anomalies)
    delta_hr = (hr - hr_rest) / (hr_max - hr_rest)
    delta_hr = delta_hr.clip(0.0, 1.0)
    
    # Compute the exponential weighting factor
    if gender.lower() == 'male':
        y = 0.64 * np.exp(1.92 * delta_hr)
    else:
        y = 0.86 * np.exp(1.67 * delta_hr)
        
    # Calculate instantaneous TRIMP per row: Time * Intensity * Weight
    row_trimp = delta_t_minutes * delta_hr * y
    
    # Return the cumulative sum of the workout
    return float(row_trimp.sum())

# Load macro data
try:
    summary_df = parse_csv()

    # Filters out interval training
    def classify_workout_style(row):
        # Prevent division by zero
        if pd.isna(row['Average Speed']) or row['Average Speed'] == 0:
            return 'Unknown'
            
        moving_ratio = row['Moving Time']/row['Elapsed Time']
        
        if moving_ratio < 0.75:
            return 'Interval'
        else:
            return 'Steady State'
    
    runs_df = summary_df[summary_df['Activity Type'] == 'Run'].copy()
    runs_df['Workout Style'] = runs_df.apply(classify_workout_style, axis=1)
    steady_runs = runs_df[runs_df['Workout Style'] == 'Steady State'].copy()

    # Page Navigation Router
    st.sidebar.title('Navigation')
    page = st.sidebar.radio("Go to", ['Activity Viewer', 'Aerobic Efficiency Trends'])
    
    if page == 'Activity Viewer':
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
        
        # Key Performance Indicator Blocks
        selected_row = filtered_summary[filtered_summary['Filename'] == target_filename].iloc[0]
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
    
        time = f'{selected_row['Moving Time'] // 60:.0f}m {selected_row['Moving Time'] % 60:.0f}s'
        dist_m = f'{selected_row['Distance']:.0f} m'
        dist_km = f'{selected_row['Distance']/1000:.2f} km'
        avg_hr = f'{selected_row["Average Heart Rate"]:.0f} bpm'
        max_hr = f'{selected_row["Max Heart Rate"]:.0f} bpm'
        cal = f'{selected_row['Calories']:.0f} cal'
        trimp = f'{calc_trimp(time_series_df):.2f}'
    
        if selected_row['Activity Type'] == 'Workout':
            col1.metric('Moving Time', time)
            col2.metric('Average Heart Rate', avg_hr)
            col3.metric('Maximum Heart Rate', max_hr)
            col4.metric('Calories Burned', cal)
            col5.metric('Training Intensity Score', trimp)
            
        elif selected_row['Activity Type'] == 'Swim':
            col1.metric('Distance', dist_m)
            col2.metric('Moving Time', time)
            col3.metric('Average Heart Rate', avg_hr)
            col4.metric('Maximum Heart Rate', max_hr)
            col5.metric('Calories Burned', cal)
            col6.metric('Training Intensity Score', trimp)
    
        else:
            col1.metric('Distance', dist_km)
            col2.metric('Moving Time', time)
            col3.metric('Average Heart Rate', avg_hr)
            col4.metric('Maximum Heart Rate', max_hr)
            col5.metric('Calories Burned', cal)
            col6.metric('Training Intensity Score', trimp)
            
        # PLot heart rate and elevation data 
        if time_series_df['heart_rate'].notna().any():
            st.subheader('Heart Rate')
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
            st.subheader('Elevation')
            elevation_chart = (
                alt.Chart(time_series_df)
                .mark_line(color='#fc5200')
                .encode(
                    x=alt.X('graph_timestamp:T', title='Time'),
                    y=alt.Y('elevation:Q', title='Elevation (m)', scale=alt.Scale(zero=False))
                )
            )
            st.altair_chart(elevation_chart, width='stretch')

    elif page == 'Aerobic Efficiency Trends':
        st.subheader('Aerobic Efficiency')

        steady_runs['Average Heart Rate'] = pd.to_numeric(steady_runs['Average Heart Rate'], errors='coerce')
        steady_runs['Average Speed'] = pd.to_numeric(steady_runs['Average Speed'], errors='coerce')
        
        # Avoid division by zero
        steady_runs = steady_runs[steady_runs['Average Speed'] > 0]
        steady_runs['aero_ratio'] = steady_runs['Average Speed'] / steady_runs['Average Heart Rate']

        # Drop missing data and sort chronologically
        chart_data = (
            steady_runs.dropna(subset=['Activity Date', 'aero_ratio'])
            .sort_values('Activity Date')
            .copy()
        )

        if not chart_data.empty:
            chart_data['graph_date'] = chart_data['Activity Date'].dt.strftime('%Y-%m-%dT%H:%M:%S')

            base = alt.Chart(chart_data).encode(
                x=alt.X('graph_date:T', title='Date'),
                y=alt.Y('aero_ratio:Q', title='Ratio (Heart Rate / Speed)', scale=alt.Scale(zero=False))
            )

            # 2. White scatter points layer with orange stroke edges
            points = base.mark_circle(
                size=60, 
                fill='white', 
                stroke='#fc5200', 
                strokeWidth=1.5, 
                opacity=0.8
            ).encode(
                tooltip=[alt.Tooltip('graph_date:T', title='Date', format='%Y-%m-%d'), 'aero_ratio:Q']
            )

            # 3. Orange Trend Line layer mapping trajectory over time
            trend_line = base.transform_regression(
                'graph_date', 'aero_ratio'
            ).mark_line(color='#fc5200', size=3)

            # 4. Layer both charts on top of each other
            aero_chart = alt.layer(points, trend_line).properties(
            height=450  
            )

            st.altair_chart(aero_chart, use_container_width=True)

        else:
            st.warning('No valid rows containing both Heart Rate and Speed data were found to plot.')
        
except Exception as e:
    st.error(f'Data Pipeline Error: {e}')
    st.info('Ensure your extracted Strava data folder is structured correctly in the root directory.')
