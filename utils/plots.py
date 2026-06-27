import altair as alt
import pandas as pd

# Helper function to filter dataframe to the last recorded activity date
def filter_to_last_activity(df):
    if 'trimps' in df.columns:
        last_active_date = df[df['trimps'] > 0]['Date'].max()
        if pd.notna(last_active_date):
            return df[df['Date'] <= last_active_date]
    return df

# Plots aerobic efficiency chart
def plot_aero(df):
    df['graph_date'] = df['Activity Date'].dt.strftime('%Y-%m-%dT%H:%M:%S')

    base = alt.Chart(df).encode(
        # Updated X-axis format to "Jan '26"
        x=alt.X('graph_date:T', title='Date', axis=alt.Axis(format="%b '%y")),
        y=alt.Y('aero_ratio:Q', title='Ratio (Speed/Heart Rate)', scale=alt.Scale(zero=False))
    )

    points = base.mark_circle(
        size=60, 
        fill='white', 
        stroke='#fc5200', 
        strokeWidth=1.5, 
        opacity=0.7
    ).encode(
        tooltip=[alt.Tooltip('graph_date:T', title='Date', format='%Y-%m-%d'), 'aero_ratio:Q']
    )

    trend_line = base.transform_regression(
        'graph_date', 'aero_ratio'
    ).mark_line(color='#fc5200', size=3)

    return alt.layer(points, trend_line).properties(height=400)
    
# Plots Fitness (Chronic Training Load) and Fatigue (Acute Training Load)
def plot_fitness_fatigue(df, selected_date=None):
    df = filter_to_last_activity(df)

    base = df.melt(id_vars=['Date'], value_vars=['CTL', 'ATL'], 
                   var_name='Metric', value_name='Value')

    base['Metric_Label'] = base['Metric'].map({'CTL': 'Fitness (CTL)', 'ATL': 'Fatigue (ATL)'})

    chart = alt.Chart(base).mark_line(strokeWidth=2).encode(
        x=alt.X('Date:T', title='Date', axis=alt.Axis(format="%b '%y")),
        y=alt.Y('Value:Q', title='Stress Units', scale=alt.Scale(zero=False)),
        color=alt.Color('Metric_Label:N', 
                        scale=alt.Scale(domain=['Fitness (CTL)', 'Fatigue (ATL)'], 
                                        range=['#1f77b4', '#ff7f0e']),
                        title='Metric'),
        tooltip=[
            alt.Tooltip('Date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip('Metric_Label:N', title='Metric'),
            alt.Tooltip('Value:Q', title='Stress Units', format='.2f')
        ]
    )

    # Add vertical sync line if a date is provided
    if selected_date:
        vline = alt.Chart(pd.DataFrame({'Date': [pd.Timestamp(selected_date)]})).mark_rule(
            color='#ffffff', strokeWidth=1
        ).encode(x='Date:T')
        return alt.layer(chart, vline).properties(height=350)

    return chart.properties(height=350)

# Plots Training Stress Balance with training zones
def plot_tsb_zones(df, selected_date=None):
    df = filter_to_last_activity(df)

    max_tsb = float(max(df['TSB'].max(), 15) + 10)
    min_tsb = float(min(df['TSB'].min(), -35) - 10)

    zone_data = pd.DataFrame([
        {'y1': 0, 'y2': max_tsb, 'color': '#6cf7a1'},        
        {'y1': -10, 'y2': 0, 'color': '#808080'},        
        {'y1': -30, 'y2': -10, 'color': '#ff9955'},   
        {'y1': min_tsb, 'y2': -30, 'color': '#f44e65'}     
    ])

    zones = alt.Chart(zone_data).mark_rect(opacity=0.25).encode(
        y=alt.Y('y1:Q', title='Form (TSB)'),
        y2='y2:Q',
        color=alt.Color('color:N', scale=None),
        tooltip=alt.value(None)
    )

    tsb_line = alt.Chart(df).mark_line(color='#ffffff', strokeWidth=2).encode(
        x=alt.X('Date:T', title='Date', axis=alt.Axis(format="%b '%y")),
        y=alt.Y('TSB:Q'),
        tooltip=[
            alt.Tooltip('Date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip('TSB:Q', title='Form', format='.2f')
        ]
    )

    baseline = alt.Chart(pd.DataFrame([{'y': 0}])).mark_rule(
        color='#7f8c8d', strokeDash=[4, 4]
    ).encode(y='y:Q')

    layers = [zones, tsb_line, baseline]

    # Add vertical sync line if a date is provided
    if selected_date:
        vline = alt.Chart(pd.DataFrame({'Date': [pd.Timestamp(selected_date)]})).mark_rule(
            color='#ffffff', strokeWidth=1 
        ).encode(x='Date:T')
        layers.append(vline)

    return alt.layer(*layers).properties(height=350)
