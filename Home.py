import streamlit as st
import altair as alt
from utils.data_loader import parse_csv
import config

st.set_page_config(layout='wide', page_title='Strava Analytics')
st.title('Strava Archive Analytics Dashboard')

# Load data into session state so other pages can see it
if 'summary_df' not in st.session_state:
    st.session_state['summary_df'] = parse_csv()

summary_df = st.session_state['summary_df']

# Summary page
st.subheader('Lifetime Training Overview')

# Activity Filter
st.sidebar.header('Activity Filter')
activity_types = ['All'] + list(summary_df['Activity Type'].unique())
selected_type = st.sidebar.selectbox('Select Activity Type', activity_types)

if selected_type != 'All':
    filtered_df = summary_df[summary_df['Activity Type'] == selected_type]
else:
    filtered_df = summary_df
    
# Core KPI Calculations
total_activities = len(filtered_df)

dist_df = filtered_df[~filtered_df['Activity Type'].isin(['Workout', 'Weight Training'])]
total_distance_km = dist_df['Distance'].sum() / 1000

total_seconds = filtered_df['Moving Time'].sum()
total_hours = total_seconds // 3600
total_minutes = (total_seconds % 3600) // 60

total_calories = filtered_df['Calories'].sum()

total_elevation = filtered_df['Elevation Gain'].sum() if 'Elevation Gain' in filtered_df.columns else 0
max_distance_km = dist_df['Distance'].max() / 1000 if not dist_df.empty else 0

# Calculate consistency metrics per week
if not filtered_df.empty and len(filtered_df) > 1:
    min_date = filtered_df['Activity Date'].min()
    max_date = filtered_df['Activity Date'].max()
    weeks_active = (max_date - min_date).days / 7
    
    # Activities per week
    weekly_avg = total_activities / weeks_active if weeks_active > 0 else total_activities
    
    # Moving time per week
    avg_seconds_per_week = total_seconds / weeks_active if weeks_active > 0 else total_seconds
    avg_weekly_hours = avg_seconds_per_week // 3600
    avg_weekly_minutes = (avg_seconds_per_week % 3600) // 60
else:
    weekly_avg = 0
    avg_weekly_hours = 0
    avg_weekly_minutes = 0

st.markdown('### ⚡ Core Metrics')

# 60/40 split for the metrics and the chart
top_left, top_right = st.columns([1.5, 1])

with top_left:
    row1_col1, row1_col2 = st.columns(2)
    row1_col1.metric('🏃‍♂️ Total Activities', f'{total_activities}')
    row1_col2.metric('📏 Total Distance', f'{total_distance_km:,.1f} km')
    
    row2_col1, row2_col2 = st.columns(2)
    row2_col1.metric('⏱️ Moving Time', f'{total_hours:.0f}h {total_minutes:.0f}m')
    row2_col2.metric('🔥 Calories Burned', f'{total_calories:,.0f} kcal')
    
with top_right:
    if selected_type == 'All' and not filtered_df.empty:
        # Group data for the donut chart
        breakdown = filtered_df['Activity Type'].value_counts().reset_index()
        breakdown.columns = ['Activity', 'Count']
        
        # Dynamically align the palette with the activities present in the current dataframe using config
        present_activities = breakdown['Activity'].tolist()
        chart_range = [config.ACTIVITY_COLORS.get(act, config.ACTIVITY_COLORS['Default']) for act in present_activities]
        
        # Build donut chart
        donut_chart = alt.Chart(breakdown).mark_arc(innerRadius=60).encode(
            theta=alt.Theta(field='Count', type='quantitative'),
            color=alt.Color(
                field='Activity', 
                type='nominal', 
                scale=alt.Scale(domain=present_activities, range=chart_range),
                legend=alt.Legend(title='Activity Breakdown', orient='right')
            ),
            tooltip=['Activity', 'Count']
        ).properties(height=220)
        
        st.altair_chart(donut_chart, width='stretch')
    else:
        st.info(f'Viewing filtered data for: **{selected_type}**.\n\nSelect "All" in the sidebar to view activity composition chart.')

st.markdown('---')

st.markdown('### ⭐ Performance Highs & Consistency')
ext_col1, ext_col2, ext_col3, ext_col4 = st.columns(4)

ext_col1.metric('⛰️ Total Elevation Gain', f'{total_elevation:,.0f} m')
ext_col2.metric('🗺️ Longest Activity Distance', f'{max_distance_km:,.1f} km')

# Updated from Historical Avg HR to Avg Moving Time / Week
ext_col3.metric('⏱️ Avg Moving Time / Week', f'{avg_weekly_hours:.0f}h {avg_weekly_minutes:.0f}m')
    
ext_col4.metric('📅 Activities / Week', f'{weekly_avg:.1f}')
