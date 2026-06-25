import altair as alt
import pandas as pd

# Form and Fitness graph
def plot_form_fitness(df):
    if df.empty:
        return alt.Chart(df).mark_blank()

    # Calculate dynamic boundaries so the background zones don't blow out the Y-axis scale
    max_tsb = float(max(df['TSB'].max(), 15) + 10)
    min_tsb = float(min(df['TSB'].min(), -35) - 10)

    # Define the 4 discrete training zones based on your TSB guide
    zone_data = pd.DataFrame([
        {"y1": 0, "y2": max_tsb, "color": "#2ecc71", "name": "Freshness"},        # Green (> 0)
        {"y1": -30, "y2": -10, "color": "#f39c12", "name": "Optimal Training"}, # Amber (-30 to -10)
        {"y1": min_tsb, "y2": -30, "color": "#e74c3c", "name": "Overtraining"}   # Red (< -30)
    ])

    # 1. Background Zones Layer (Low opacity ensures line visibility)
    background_zones = alt.Chart(zone_data).mark_rect(opacity=0.15).encode(
        y=alt.Y('y1:Q', title='Stress Units / Load'),
        y2='y2:Q',
        color=alt.Color('color:N', scale=None)
    )

    # 2. Universal Base line mapping date and interactive tooltips
    base = alt.Chart(df).encode(
        x=alt.X('Date:T', title='Date'),
        tooltip=[
            alt.Tooltip('Date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip('CTL:Q', title='🏋️‍♂️ Fitness (CTL)', format='.1f'),
            alt.Tooltip('ATL:Q', title='🔥 Fatigue (ATL)', format='.1f'),
            alt.Tooltip('TSB:Q', title='📈 Form (TSB)', format='.1f')
        ]
    )

    # 3. Fitness (CTL) - Neon Blue Trend Line
    ctl_line = base.mark_line(color='#00f2fe', strokeWidth=1.5, opacity=0.5).encode(y='CTL:Q')

    # 4. Fatigue (ATL) - Red Muted Trend Line
    atl_line = base.mark_line(color='#ff4b4b', strokeWidth=1.5, opacity=0.5).encode(y='ATL:Q')

    # 5. Form (TSB) - Thick White Trend Line
    tsb_line = base.mark_line(color='#ffffff', strokeWidth=3.0).encode(y='TSB:Q')

    # 6. Sharp Solid Baseline at Exactly 0 Balance
    baseline = alt.Chart(pd.DataFrame([{'y': 0}])).mark_rule(
        color='#7f8c8d', 
        strokeWidth=1.5, 
        strokeDash=[4, 4]
    ).encode(y='y:Q')

    # Layer items sequentially: Background zones must render first to avoid masking line values
    chart = alt.layer(
        background_zones, 
        ctl_line, 
        atl_line, 
        tsb_line, 
        baseline
    ).properties(
        height=500
    ).interactive(
        bind_y=False # Locks vertical tracking so the structured bands remain stable
    )

    return chart
