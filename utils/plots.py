import altair as alt

# Form and Fitness graph
def plot_form_fitness(df):
    # 1. Base configuration with universal X-axis and tooltips
    base = alt.Chart(df).encode(
        x=alt.X('Date:T', title='Date'),
        tooltip=[
            alt.Tooltip('Date:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip('CTL:Q', title='🏋️ Fitness (CTL)', format='.1f'),
            alt.Tooltip('ATL:Q', title='🔥 Fatigue (ATL)', format='.1f'),
            alt.Tooltip('TSB:Q', title='📈 Form (TSB)', format='.1f')
        ]
    )

    # 2. Fitness (CTL) - Neon Blue Area + Solid Line
    ctl_area = base.mark_area(color='#00f2fe', opacity=0.08).encode(
        y=alt.Y('CTL:Q', title='Stress Units / Load')
    )
    ctl_line = base.mark_line(color='#00f2fe', strokeWidth=2.5).encode(y='CTL:Q')

    # 3. Fatigue (ATL) - Red Muted Line
    atl_line = base.mark_line(color='#ff4b4b', strokeWidth=1.5, opacity=0.6).encode(y='ATL:Q')

    # 4. Form (TSB) - Amber High-Contrast Line
    tsb_line = base.mark_line(color='#ffb300', strokeWidth=2).encode(y='TSB:Q')

    # 5. Static Dashed Baseline at 0 Balance
    baseline = alt.Chart(df).mark_rule(
        color='rgba(255, 255, 255, 0.25)', 
        strokeDash=[4, 4]
    ).encode(
        y=alt.datum(0)
    )

    # 6. Combine layers, apply titles, and make it interactive (pan/zoom)
    chart = alt.layer(
        ctl_area, ctl_line, atl_line, tsb_line, baseline
    ).properties(
        title="Training Load Trends (Form & Fitness)",
        height=400
    ).interactive(
        bind_y=False  # Only lock zoom/pan to the X-axis (Timeline)
    )

    return chart
