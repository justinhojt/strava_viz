import altair as alt
import pandas as pd

def plot_form_fitness(df):
    if df.empty:
        return alt.Chart(df).mark_blank()

    max_tsb = float(max(df['TSB'].max(), 15) + 10)
    min_tsb = float(min(df['TSB'].min(), -35) - 10)

    zone_data = pd.DataFrame([
        {'y1': 0, 'y2': max_tsb, 'color': '#6cf7a1', 'name': 'Freshness'},        
        {'y1': -10, 'y2': 0, 'color': '#808080', 'name': 'Grey Zone'},        
        {'y1': -30, 'y2': -10, 'color': '#ff9955', 'name': 'Optimal Training'},   
        {'y1': min_tsb, 'y2': -30, 'color': '#f44e65', 'name': 'Overtraining'}     
    ])

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

    # Assign labels to each row for the legend
    base = alt.Chart(df).transform_fold(
        ['CTL', 'ATL', 'TSB'],
        as_=['Legend', 'Value']
    ).transform_calculate(
        Metric_Label="datum.Metric == 'CTL' ? 'Fitness (CTL)' : (datum.Metric == 'ATL' ? 'Fatigue (ATL)' : 'Form (TSB)')"
    ).encode(
        x=alt.X('Date:T', title='Date')
    )

    lines = base.mark_line(strokeWidth=1.5).encode(
        y=alt.Y('Value:Q'),
        color=alt.Color('Metric_Label:N', scale=metrics_scale, title='Metrics'),
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

    return alt.layer(background_zones, lines, baseline).properties(height=500).interactive(bind_y=False)
