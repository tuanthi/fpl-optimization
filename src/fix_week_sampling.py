#!/usr/bin/env python3
"""
Fix the week sampling to use team names instead of IDs
"""

import pandas as pd
from pathlib import Path

# Load the prediction file
pred_file = Path("data/merged_2024_2025/pred_merged_week_sampling_1_to_38.csv")
if not pred_file.exists():
    # Check in temp location
    pred_file = Path("data/9999/pred_9999_week_sampling_1_to_38.csv")
    if not pred_file.exists():
        print("Prediction file not found")
        exit(1)

# Load teams
teams_file = Path("data/merged_2024_2025/merged_teams.csv")
if not teams_file.exists():
    teams_file = Path("data/2024/2024_teams.csv")

teams_df = pd.read_csv(teams_file)
team_id_to_name = dict(zip(teams_df['id'], teams_df['name']))

print(f"Team mapping sample:")
for tid, tname in list(team_id_to_name.items())[:5]:
    print(f"  {tid} -> {tname}")

# Load prediction data
pred_df = pd.read_csv(pred_file)
print(f"\nLoaded {len(pred_df)} prediction rows")
print(f"Sample before fixing:")
print(pred_df[['first_name', 'last_name', 'club']].head())

# Map team IDs to names
pred_df['club'] = pred_df['club'].map(team_id_to_name)

print(f"\nSample after fixing:")
print(pred_df[['first_name', 'last_name', 'club']].head())

# Check for any unmapped teams
unmapped = pred_df[pred_df['club'].isna()]
if len(unmapped) > 0:
    print(f"\nWarning: {len(unmapped)} rows with unmapped teams")
    print(unmapped['club'].value_counts())

# Save fixed file
output_file = Path("data/merged_2024_2025/pred_merged_week_sampling_1_to_38_fixed.csv")
pred_df.to_csv(output_file, index=False)
print(f"\nSaved fixed file to {output_file}")