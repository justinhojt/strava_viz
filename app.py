import streamlit as st
import altair as alt
from utils.data_loader import parse_csv, parse_gpx, parse_fit
from utils.functions import parse_granular, calc_trimps, classify_workout_style
from utils.plots import plot_fitness_fatigue, plot_tsb_zones

st.set_page_config(layout='wide')
st.title('Strava Archive Analytics Dashboard')

# Load macro data
try:
    summary_df = parse_csv()

    # Page Navigation Router
    st.sidebar.title('Navigation')
    page = st.sidebar.radio('Go to', ['Activity Viewer', 'Aerobic Efficiency Trends', 'Fitness, Fatigue and Form'])
    
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
        
        # Key Performance Indicators
        selected_row = filtered_summary[filtered_summary['Filename'] == target_filename].iloc[0]
    
        time = f'{selected_row['Moving Time'] // 60:.0f}m {selected_row['Moving Time'] % 60:.0f}s'
        dist_m = f'{selected_row['Distance']:.0f} m'
        dist_km = f'{selected_row['Distance'] / 1000:.2f} km'
        avg_hr = f'{selected_row['Average Heart Rate']:.0f} bpm'
        max_hr = f'{selected_row['Max Heart Rate']:.0f} bpm'
        cal = f'{selected_row['Calories']:.0f} cal'
        trimp = f'{calc_trimps(time_series_df):.2f}'

        seconds_100m = selected_row['Moving Time'] / (selected_row['Distance'] / 100)
        pace_100m = f'{seconds_100m // 60:.0f}m {seconds_100m % 60:.0f}s/100m'

        seconds_km = selected_row['Moving Time'] / (selected_row['Distance'] / 1000)
        pace_km = f'{seconds_km // 60:.0f}m {seconds_km % 60:.0f}s/km'
       
        if selected_row['Activity Type'] == 'Workout':
            r1_col1, r1_col2, r1_col3 = st.columns(3)
            r1_col1.metric('Moving Time', time)
            r1_col2.metric('Average Heart Rate', avg_hr)
            r1_col3.metric('Maximum Heart Rate', max_hr)
            
            r2_col1 = st.columns(3)
            r1_col1.metric('Training Intensity Score', trimp)
            
        elif selected_row['Activity Type'] == 'Swim':
            r1_col1, r1_col2, r1_col3 = st.columns(3)
            r1_col1.metric('Distance', dist_m)
            r1_col2.metric('Moving Time', time)
            r1_col3.metric('Pace', pace_100m)
            
            r2_col1, r2_col2, r2_col3 = st.columns(3)
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
        st.subheader('Aerobic efficiency') 
        st.write('A rising trendline mathematically demonstrates cardiovascular adaptation (moving faster at a lower metabolic cost).')

        runs = summary_df[summary_df['Activity Type'] == 'Run'].copy()
        runs['Workout Style'] = runs.apply(classify_workout_style, axis=1)
        steady_runs = runs[runs['Workout Style'] == 'Steady State'].copy()

        # Avoid division by zero and short distances
        steady_runs = steady_runs[(steady_runs['Average Grade Adjusted Pace'] > 0) & (runs['Distance'] >= 1000)]
        steady_runs['aero_ratio'] = steady_runs['Average Grade Adjusted Pace'] / steady_runs['Average Heart Rate']

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
                y=alt.Y('aero_ratio:Q', title='Ratio (Speed/Heart Rate)', scale=alt.Scale(zero=False))
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
            height=500  
            )

            st.subheader('Running') 
            st.altair_chart(aero_chart, width='stretch')

        walks = summary_df[summary_df['Activity Type'] == 'Walk'].copy()
        
        # Avoid division by zero and exclude short distances
        walks = walks[(walks['Average Speed'] > 0) & (walks['Distance'] >= 1000)]
        walks['aero_ratio'] = walks['Average Speed'] / walks['Average Heart Rate']

        # Drop missing data and sort chronologically
        chart_data = (
            walks.dropna(subset=['Activity Date', 'aero_ratio'])
            .sort_values('Activity Date')
            .copy()
        )

        if not chart_data.empty:
            chart_data['graph_date'] = chart_data['Activity Date'].dt.strftime('%Y-%m-%dT%H:%M:%S')

            base = alt.Chart(chart_data).encode(
                x=alt.X('graph_date:T', title='Date'),
                y=alt.Y('aero_ratio:Q', title='Ratio (Speed/Heart Rate)', scale=alt.Scale(zero=False))
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
            height=500  
            )

            st.subheader('Walking') 
            st.altair_chart(aero_chart, width='stretch')

        else:
            st.warning('No valid rows containing both Heart Rate and Speed data were found to plot.')

    elif page == 'Fitness, Fatigue and Form':
        trimps = parse_granular(summary_df.copy())

        st.subheader('Historical Performance Analysis')

        # Date slider
        min_date = trimps['Date'].min().to_pydatetime()
        max_date = summary_df['Activity Date'].max().to_pydatetime()
        
        selected_date = st.slider(
            '📅 Scrub through training history to view stats for that day:',
            min_value=min_date,
            max_value=max_date,
            value=max_date,  
            format='YYYY-MM-DD'
        )
        
        # Filter the metrics down to the single selected day
        matched_row = trimps[trimps['Date'] == pd.Timestamp(selected_date)]
        
        if not matched_row.empty:
            metrics = matched_row.iloc[0]
            ctl = metrics['CTL']
            atl = metrics['ATL']
            tsb = metrics['TSB']
            
            # Dynamic KPI cards
            col1, col2, col3 = st.columns(3)
            col1.metric('Fitness (CTL)', f'{ctl:.2f} pts')
            col2.metric('Fatigue (ATL)', f'{atl:.2f} pts')
            
            if tsb < -30:
                status, color = 'Overtraining Risk', 'inverse'
            elif -30 <= tsb < -10:
                status, color = 'Optimal Training', 'normal'
            elif -10 <= tsb <= 0 :
                status, color = 'Maintenance Zone', 'normal'
            else:
                status, color = 'Fresh / Recovery', 'normal'
                
            col3.metric('Form (TSB)', f'{tsb:.2f} pts', delta=status, delta_color=color)

        st.markdown('---')

        # Charts and documentation
        chart_tab1, chart_tab2 = st.tabs(['📊 Fitness & Fatigue Dynamics', '🚦 Training Stress Balance (TSB)'])
        
        with chart_tab1:
            st.altair_chart(plot_fitness_fatigue(trimps), width='stretch') 
            
        with chart_tab2:
            st.altair_chart(plot_tsb_zones(trimps), width='stretch') 
            
        with st.expander('🔬 View Physiological Model Methodology'):
            st.markdown("""
            ## 📊 Understanding Your Fitness, Fatigue, and Form
    
            Training effectively requires balancing hard work with structured recovery. These metrics—derived from the Banister Impulse-Response model—transform raw workout data into a predictive view of your physiology.
            
            ---
            
            ### 📈 The Core Metrics
            At the heart of the graphs are three primary metrics that track your training load:
            
            | Metric | Full Name | Time Horizon | What it tells you |
            | :--- | :--- | :--- | :--- |
            | **CTL** | Chronic Training Load | ~42 Days | Your **Fitness** (long-term adaptation) |
            | **ATL** | Acute Training Load | ~7 Days | Your **Fatigue** (short-term exhaustion) |
            | **TSB** | Training Stress Balance | Daily | Your **Form** (readiness to perform) |
            
            ---
            
            ### 🔄 How They Interact
            The charts visualize the continuous tug-of-war between fitness and fatigue:
            
            #### 1. Fitness (CTL)
            CTL represents the long-term trend of your training volume and intensity. Because it is calculated as a 42-day moving average, it changes slowly. It won't drop significantly if you take a few days off, reflecting the reality that your aerobic engine doesn't vanish overnight.
            
            #### 2. Fatigue (ATL)
            ATL is highly volatile. Representing a short 7-day window, it reacts immediately to hard workouts or back-to-back training days. If your ATL line climbs sharply above your CTL, you are accumulating fatigue rapidly.
            
            """)
            st.altair_chart(plot_fitness_fatigue(trimps), width='stretch')
    
            st.markdown("""
            #### 3. Form (TSB)
            Form is the mathematical difference between your fitness and your current fatigue:
            
            $$TSB = CTL - ATL$$
            
            * **When TSB > 0 (Freshness):** You have shed the fatigue of recent training, and your fitness is unmasked. This is your ideal state for a race or performance test.
            * **When TSB < 0 (Overreaching):** You are accumulating training stress. A negative number isn't bad—it's required to stimulate adaptation and build fitness. However, staying deeply negative for too long risks injury or burnout.
            
            ### 🚦 Reading the Training Zones
            The colored backgrounds on the Form chart provide a quick decision-support framework to manage your training:
            
            * **🟢 Freshness (Above 0):** Minimal fatigue; peak state for racing or performance testing.
            * **⚫ Grey Zone (0 to -10):** Neutral zone; fitness is maintained but not actively building.
            * **🟠 Optimal Training (-10 to -30):** Productive training stress with managed fatigue. The "sweet spot" for building fitness safely.
            * **🔴 Overtraining (Below -30):** High risk of injury, illness, or chronic fatigue. Time to prioritize active recovery.
            
            """)
            
        st.altair_chart(plot_tsb_zones(trimps), width='stretch')
        
except Exception as e:
    st.error(f'Data Pipeline Error: {e}')
    st.info('Ensure your extracted Strava data folder is structured correctly in the root directory.')
