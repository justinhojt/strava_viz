# Strava Archive Analytics Dashboard
https://justinhojt-stravaviz.streamlit.app/

A comprehensive, locally-hosted Streamlit dashboard designed to process, analyze, and visualize your lifetime Strava bulk export data. This dashboard goes beyond basic metrics, offering deep, individualized insights into cardiovascular adaptation, aerobic efficiency, and long-term physiological trends.

## Key Features

This application is divided into a modular, multi-page Streamlit architecture:

* **Home (Lifetime Overview):** A high-level macro view of your training history. Includes KPI aggregations, activity composition breakdowns (interactive donut charts), and total metric summaries.
  
* **Activity Viewer:** Dive into second-by-second granular data for individual sessions. Parses `.gpx` and `.fit` files to plot heart rate zones, elevation profiles, and time-in-zone histograms.
 
* **Aerobic Efficiency Trends:** Tracks your cardiovascular adaptation over time. Specifically isolates "Steady State" runs and calculates the $\text{Efficiency} = \frac{\text{Speed}}{\text{Heart Rate}}$ ratio to visualize how your body adapts to sustained efforts.
  * **True Fitness (ML Integration):** Utilizes multiple linear regression to build a Personal Environmental Profile. Calculates your unique "Heat Penalty" and "Humidity Penalty" to normalize performance data against a standard baseline (e.g., 28°C / 80% Humidity), revealing true fitness adaptations masked by cardiac drift.
  
* **Fitness, Fatigue & Form:** Implements the Banister TRIMP (Training Impulse) model to calculate and visualize your physiological state:
  * **Fitness (CTL):** 42-day rolling average of training load.
  * **Fatigue (ATL):** 7-day acute rolling average.
  * **Form (TSB):** Calculated as $\text{TSB} = \text{CTL} - \text{ATL}$, plotted against custom training zones (Freshness, Maintenance, Optimal Training, Overtraining).

---

## Repository Structure

All UI styling and constants are managed centrally, and frontend pages are decoupled from backend calculations and charting logic.

```text
├── data/                               # Local Strava export data
│   ├── activities/                     # Individual gpx/fit files
│   ├── activities.csv                  # Raw Strava bulk export summary
│   └── activities_refined.csv          # Cleaned dataset with weather & localized timezones
├── pages/                              # Frontend Streamlit sub-pages
│   ├── 1_Activity_Viewer.py           
│   ├── 2_Aerobic_Efficiency_Trends.py  
│   └── 3_Fitness_Fatigue_Form.py       
├── utils/                              # Core pipeline logic
│   ├── data_loader.py                  # gpx/fit parsing
│   ├── functions.py                    # TRIMP score calculations and data transformations
│   └── plots.py                        # Centralized Altair charting components
├── .gitignore
├── Home.py                             # Main Streamlit entry point
├── README.md
├── config.py                           # Centralized configuration for UI colors, HR zones, and other constants
├── refine_dataset.py                   # Pre-processing script: cleans data, standardizes timezones, and fetches historical weather
└── requirements.txt                    # Python dependencies
