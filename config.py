import os

DATA_DIR = 'data'
ACTIVITIES_CSV = os.path.join(DATA_DIR, 'activities.csv')

# UI colour hex codes
COLOR_STRAVA_ORANGE = '#fc5200'
COLOR_MUTED_GREY = '#808080'
COLOR_PURE_WHITE = '#ffffff'

# Activity composition breakdown (donut chart)
ACTIVITY_COLORS = {
    'Run': '#fc5200',              
    'Walk': '#ee9f28',             
    'Swim': '#f9dcb0',             
    'Workout': '#e17602',
    'Default': '#808080'         
}

# TSB training zones
ZONE_COLORS = {
    'Freshness': '#6cf7a1',          # TSB > 0 (Green)
    'Maintenance': '#808080',        # TSB 0 to -10 (Grey)
    'Optimal_Training': '#ff9955',   # TSB -10 to -30 (Orange)
    'Overtraining': '#f44e65'        # TSB < -30 (Red)
}

# Default cardiovascular metrics
DEFAULT_HR_MAX = 200
DEFAULT_HR_REST = 75
DEFAULT_GENDER = 'male'

# Banister Impulse-Response Model Constants (Rolling window spans in days)
CTL_DAY_SPAN = 42   # Chronic Training Load (Fitness)
ATL_DAY_SPAN = 7    # Acute Training Load (Fatigue)

TIMEZONE_TARGET = 'Asia/Singapore'
TIMEZONE_OFFSET_HOURS = 8
