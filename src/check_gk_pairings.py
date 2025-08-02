#!/usr/bin/env python3
"""Check GK pairings in teams"""

import pandas as pd

# Check top teams to see GK pairings
df = pd.read_csv('../data/cached_merged_2024_2025_v2/top_200_teams_final_v5.csv')

print('GK Pairings in teams:')
print('='*80)

nottm_forest_count = 0
same_team_count = 0

for idx in range(min(30, len(df))):
    team = df.iloc[idx]
    
    # Get starting GK
    starting_gk = team.get('GK1', 'N/A')
    
    # Find bench GK
    bench_gk = None
    for i in range(1, 5):
        if team.get(f'BENCH{i}_role') == 'GK':
            bench_gk = team.get(f'BENCH{i}')
            break
    
    if pd.notna(starting_gk) and bench_gk:
        # Extract team names
        start_team = starting_gk.split('(')[1].split(')')[0] if '(' in starting_gk else ''
        bench_team = bench_gk.split('(')[1].split(')')[0] if '(' in bench_gk else ''
        
        # Check if Nottm Forest
        if "Nott'm Forest" in starting_gk:
            nottm_forest_count += 1
            
        # Check if same team
        same_team = start_team == bench_team
        if same_team:
            same_team_count += 1
            
        # Print interesting cases
        if idx < 10 or "Nott'm Forest" in starting_gk or same_team:
            status = '✓ SAME TEAM' if same_team else 'Different teams'
            print(f'Team {idx+1:3d}: {starting_gk:35s} | Bench: {bench_gk:35s} [{status}]')

print(f'\nStatistics:')
print(f'- Teams checked: {min(30, len(df))}')
print(f'- Teams with Nottm Forest starting GK: {nottm_forest_count}')
print(f'- Same team GK pairings: {same_team_count}')
print(f'- Different team pairings: {min(30, len(df)) - same_team_count}')

# Also check why Matt Turner might not be selected
print('\n\nChecking Matt Turner availability:')
predictions = pd.read_csv('../data/cached_merged_2024_2025_v2/predictions_gw39_proper_v3.csv')
turner = predictions[(predictions['last_name'] == 'Turner') & (predictions['club'] == "Nott'm Forest")]
if not turner.empty:
    t = turner.iloc[0]
    print(f"Matt Turner found: £{t['price']}m, score: {t['weighted_score']:.2f}")
else:
    print("Matt Turner not found in predictions!")