import altair as alt
import pandas as pd

def plot_form_fitness(df):
    if df.empty:
        return alt.Chart(df).mark_blank()

    # 1. Calculate min/max boundaries from original dataframe columns
    max_tsb = float(max(df['TSB'].max(), 15) + 10)
    min_tsb = float(min(df['TSB'].min(), -35) - 10)

    zone_data = pd.DataFrame([
        {'y1': 0, 'y2': max_tsb, 'color': '#6cf7a1', 'name': 'Freshness'},        
        {'y1': -10, 'y2': 0, 'color': '#808080', 'name': 'Grey Zone'},        
        {'y1': -30, 'y2': -10, 'color': '#ff9955', 'name': 'Optimal Training'},   
        {'y1': min_tsb, 'y2': -30, 'color': '#f44e65', 'name': 'Overtraining'}     
    ])

    # 2. Transform data in Pandas instead of Altair to guarantee clean legend interactions
    df_melted = df.melt(
        id_vars=['Date', 'CTL', 'ATL', 'TSB'],  # Keep original columns so tooltips still work flawlessly
        value_vars=['CTL', 'ATL', 'TSB'],
        var_name='Metric',
        value_name='Value'
    )
    
    # Map the metrics to clean, readable labels
    label_map = {
        'CTL': 'Fitness (CTL)',
        'ATL': 'Fatigue (ATL)',
        'TSB': 'Form (TSB)'
    }
    df_melted['Metric_Label'] = df_melted['Metric'].map(label_map)

    metrics_scale = alt.Scale(
        domain=['Fitness (CTL)', 'Fatigue (ATL)', 'Form (TSB)'],
        range=['#00f2fe', '#ff4b4b', '#ffffff']
    )

    background_zones = alt.Chart(zone_data).mark_rect(opacity=0.3).encode(
        y=alt.Y('y1:Q', title='Stress Units / Load'),
        y2='y2:Q',
        color=alt.Color('color:N', scale=None),
        tooltip=alt.value(None)
    )

    # 3. Explicitly target the native Pandas column with the legend selection
    legend_selection = alt.selection_point(fields=['Metric_Label'], bind='legend')
    zoom_pan_x = alt.selection_interval(bind='scales', encodings=['x'])

    lines = alt.Chart(df_melted).mark_line(strokeWidth=1.5).encode(
        x=alt.X('Date:T', title='Date'),
        y=alt.Y('Value:Q'),
        color=alt.Color('Metric_Label:N', scale=metrics_scale, title='Legend'),
        # Toggles smoothly: full opacity by default, fades out unselected items on click
        opacity=alt.condition(legend_selection, alt.value(1), alt.value(0.1)),
        tooltip=[
            alt.Tooltip('Date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip('CTL:Q', title='Fitness (CTL)', format='.1f'),
            alt.Tooltip('ATL:Q', title='Fatigue (ATL)', format='.1f'),
            alt.Tooltip('TSB:Q', title='Form (TSB)', format='.1f')
        ]
    )

    baseline = alt.Chart(pd.DataFrame([{'y': 0}])).mark_rule(
        color='#7f8c8d', strokeWidth=1.5, strokeDash=[4, 4]
    ).encode(y='y:Q')

    # 4. Bind parameters globally to the parent layered chart
    final_chart = alt.layer(
        background_zones, 
        lines, 
        baseline
    ).properties(
        height=500
    ).add_params(
        legend_selection,
        zoom_pan_x
    )

    return final_chart
