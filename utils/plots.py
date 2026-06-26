import altair as alt
import pandas as pd

# Plots Fitness (Chronic Training Load) and Fatigue (Acute Training Load)
def plot_fitness_fatigue(df):
    base = df.melt(id_vars=['Date'], value_vars=['CTL', 'ATL'], 
                   var_name='Metric', value_name='Value')

    base['Metric_Label'] = base['Metric'].map({'CTL': 'Fitness (CTL)', 'ATL': 'Fatigue (ATL)'})

    return alt.Chart(base).mark_line(strokeWidth=2).encode(
        x=alt.X('Date:T', title='Date'),
        y=alt.Y('Value:Q', title='Stress Units', scale=alt.Scale(zero=False)),
        color=alt.Color('Metric_Label:N', 
                        scale=alt.Scale(domain=['Fitness (CTL)', 'Fatigue (ATL)'], 
                                        range=['#1f77b4', '#ff7f0e']),
                        title='Metric'),
        tooltip=['Date:T', 'Value:Q', 'Metric_Label:N']
    ).properties(height=250)

# Plots Training Stress Balance with training zones
def plot_tsb_zones(df):
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

    return alt.layer(zones, tsb_line, baseline).properties(height=250)
