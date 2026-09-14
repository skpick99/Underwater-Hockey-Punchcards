import os
import pandas as pd
from datetime import datetime
from collections import Counter

# Read both files (from the data folder next to this script)
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
df1 = pd.read_csv(os.path.join(data_dir, 'punchcards.csv'), sep='\t', dtype=str, keep_default_na=False)
df2 = pd.read_csv(os.path.join(data_dir, 'punchcards_history.csv'), sep='\t', dtype=str, keep_default_na=False)

def get_all_dates(df):
    """Extract all dates from a dataframe"""
    date_cols = [c for c in df.columns if 'PlayDate' in c]
    all_dates = []
    for col in date_cols:
        dates = df[col].astype(str).str.strip()
        dates = dates[dates != '']
        dates = dates[dates != 'NULL']
        dates = dates[dates != 'nan']
        for d in dates:
            if len(d) == 8 and d.isdigit():
                try:
                    date_obj = datetime.strptime(d, '%Y%m%d')
                    if 2000 <= date_obj.year <= 2030:
                        all_dates.append(date_obj)
                except:
                    pass
    return all_dates

# Get all dates from both files
all_dates1 = get_all_dates(df1)
all_dates2 = get_all_dates(df2)
all_dates = all_dates1 + all_dates2

# Filter to Sundays and count occurrences per date
sunday_dates = [d for d in all_dates if d.weekday() == 6]
sunday_counter = Counter(sunday_dates)

# Get attendance counts (number of punches per Sunday)
attendance_counts = list(sunday_counter.values())

# Create histogram: count how many times each attendance count occurred
histogram = Counter(attendance_counts)

# Track dates by attendance count for low attendance reporting
dates_by_attendance = {}
for date, count in sunday_counter.items():
    if count not in dates_by_attendance:
        dates_by_attendance[count] = []
    dates_by_attendance[count].append(date)

# Find the range of attendance counts
if attendance_counts:
    min_attendance = min(attendance_counts)
    max_attendance = max(attendance_counts)
    
    # Print histogram for all attendance counts in range
    print("Sunday Practice Attendance Histogram")
    print("=" * 50)
    for players in range(min_attendance, max_attendance + 1):
        occurrences = histogram.get(players, 0)
        print(f"{occurrences} occurrences -- {players} players")
    
    # List dates with 6 or fewer players
    print("\n" + "=" * 50)
    print("Sundays with 6 or fewer players:")
    print("=" * 50)
    low_attendance_dates = []
    for players in range(min_attendance, 7):  # 6 or fewer
        if players in dates_by_attendance:
            for date in sorted(dates_by_attendance[players]):
                low_attendance_dates.append((date, players))
    
    if low_attendance_dates:
        for date, players in sorted(low_attendance_dates):
            print(f"{date.strftime('%Y-%m-%d')} -- {players} players")
    else:
        print("No Sundays with 6 or fewer players found")
else:
    print("No Sunday practices found")

