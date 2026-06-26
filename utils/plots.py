import altair as alt
import pandas as pd

def plot_form_fitness(df):
    if df.empty:
        return alt.Chart(df).mark_blank()

    # --- Chart 1: Fitness (CTL) and Fatigue (ATL) ---
    base_fitness = alt.Chart(df).transform_fold(
        ['CTL', 'ATL'], as_=['Metric', 'Value']
    ).transform_calculate(
        Metric_Label="datum.Metric == 'CTL' ? 'Fitness (CTL)' : 'Fatigue (ATL)'"
    )

    fitness_chart = base_fitness.mark_line(strokeWidth=2).encode(
        x=alt.X('Date:T', title='Date'),
        y=alt.Y('Value:Q', title='Stress Units'),
        color=alt.Color('Metric_Label:N', scale=alt.Scale(domain=['Fitness (CTL)', 'Fatigue (ATL)'], range=['#00f2fe', '#ff4b4b'])),
        tooltip=['Date:T', 'CTL:Q', 'ATL:Q']
    ).properties(height=250)

    # --- Chart 2: TSB + Zones ---
    max_tsb = float(max(df['TSB'].max(), 15) + 10)
    min_tsb = float(min(df['TSB'].min(), -35) - 10)

    zone_data = pd.DataFrame([
        {'y1': 0, 'y2': max_tsb, 'color': '#6cf7a1'},        
        {'y1': -10, 'y2': 0, 'color': '#808080'},        
        {'y1': -30, 'y2': -10, 'color': '#ff9955'},   
        {'y1': min_tsb, 'y2': -30, 'color': '#f44e65'}     
    ])

    background_zones = alt.Chart(zone_data).mark_rect(opacity=0.3).encode(
        y=alt.Y('y1:Q', title='Form (TSB)'),
        y2='y2:Q',
        color=alt.Color('color:N', scale=None)
    )

    tsb_line = alt.Chart(df).mark_line(color='#ffffff', strokeWidth=2).encode(
        x=alt.X('Date:T', title='Date'),
        y=alt.Y('TSB:Q'),
        tooltip=['Date:T', 'TSB:Q']
    )

    baseline = alt.Chart(pd.DataFrame([{'y': 0}])).mark_rule(
        color='#7f8c8d', strokeDash=[4, 4]
    ).encode(y='y:Q')

    tsb_chart = alt.layer(background_zones, tsb_line, baseline).properties(height=250)

    # --- Return Vertical Stack ---
    return alt.vconcat(fitness_chart, tsb_chart).resolve_scale(x='shared')
