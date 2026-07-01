# Strava Archive Analytics Dashboard

A comprehensive, locally-hosted Streamlit dashboard designed to process, analyze, and visualize your lifetime Strava bulk export data. This dashboard goes beyond basic metrics, offering deep, individualized insights into cardiovascular adaptation, aerobic efficiency, and long-term physiological trends.

## Key Features

This application is divided into a modular, multi-page Streamlit architecture:

* **Home (Lifetime Overview):** A high-level macro view of your training history. Includes KPI aggregations, activity composition breakdowns (interactive donut charts), and total metric summaries.
* **Activity Viewer:** Dive into second-by-second granular data for individual sessions. Parses `.gpx` and `.fit` files to plot heart rate zones, elevation profiles, and time-in-zone histograms.
* **Aerobic Efficiency Trends:** Tracks your cardiovascular adaptation over time. Specifically isolates "Steady State" runs and calculates the $\text{Efficiency} = \frac{\text{Speed}}{\text{Heart Rate}}$ ratio to visualize how your body adapts to sustained efforts.
* **Fitness, Fatigue & Form:** Implements the Banister TRIMP (Training Impulse) model to calculate and visualize your physiological state:
  * **Fitness (CTL):** 42-day rolling average of training load.
  * **Fatigue (ATL):** 7-day acute rolling average.
  * **Form (TSB):** Calculated as $\text{TSB} = \text{CTL} - \text{ATL}$, plotted against custom training zones (Freshness, Maintenance, Optimal Training, Overtraining).

---

## Repository Structure

```text
├── Home.py                             # Main Streamlit entry point
├── config.py                           # Global constants, UI colors, and model parameters
├── data/                               # Place Strava export data here
│   ├── activities                      # Individual gpx/fit files
│   └── activities.csv                  # Strava bulk export summary
├── pages/                              # Streamlit sub-pages
│   ├── 1__Activity_Viewer.py           
│   ├── 2_Aerobic_Efficiency_Trends.py  
│   └── 3_Fitness_Fatigue_Form.py       
└── utils/                              # Core pipeline logic
    ├── data_loader.py                  # gpx/fit parsing and timezone standardization
    ├── functions.py                    # TRIMP score calculations and data transformations
    └── plots.py                        # Altair chart configurations
```
