#!/usr/bin/env python3
"""Check GK pairings in teams - version 2"""

import pandas as pd

# Check top teams to see GK pairings
df = pd.read_csv('../data/cached_merged_2024_2025_v2/top_200_teams_final_v6.csv')

print('GK Pairings Analysis:')
print('='*100)

same_team_count = 0
nottm_forest_count = 0
chelsea_starting_count = 0

pairing_details = []

for idx in range(min(164, len(df))):
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
        
        # Check specific teams
        if "Nott'm Forest" in starting_gk:
            nottm_forest_count += 1
            
        if "Chelsea" in starting_gk:
            chelsea_starting_count += 1
            
        # Check if same team
        same_team = start_team == bench_team
        if same_team:
            same_team_count += 1
            pairing_details.append({
                'team_idx': idx + 1,
                'starting_gk': starting_gk,
                'bench_gk': bench_gk,
                'team': start_team
            })

print(f'\nStatistics for all {len(df)} teams:')
print(f'- Teams with Nottm Forest starting GK: {nottm_forest_count}')
print(f'- Teams with Chelsea starting GK: {chelsea_starting_count}')
print(f'- Same team GK pairings: {same_team_count}')
print(f'- Different team pairings: {len(df) - same_team_count}')

if pairing_details:
    print(f'\nDetailed same-team pairings ({len(pairing_details)} found):')
    print('-'*100)
    for detail in pairing_details[:20]:  # Show first 20
        print(f"Team {detail['team_idx']:3d}: {detail['starting_gk']:35s} | Bench: {detail['bench_gk']:35s}")
        
    # Group by club
    by_club = {}
    for detail in pairing_details:
        club = detail['team']
        if club not in by_club:
            by_club[club] = 0
        by_club[club] += 1
    
    print(f'\nSame-team pairings by club:')
    for club, count in sorted(by_club.items(), key=lambda x: x[1], reverse=True):
        print(f"  {club}: {count} teams")
else:
    print("\nNo same-team GK pairings found!")

# Check specific cases
print('\n\nSpecific GK analysis:')
print('-'*50)

# Check Matt Turner situation
print('\nNottm Forest GK situation:')
predictions = pd.read_csv('../data/cached_merged_2024_2025_v2/predictions_gw39_proper_v3.csv')
nottm_gks = predictions[(predictions['role'] == 'GK') & (predictions['club'] == "Nott'm Forest")]
for _, gk in nottm_gks.iterrows():
    print(f"  {gk['first_name']} {gk['last_name']}: £{gk['price']}m, score: {gk['weighted_score']:.2f}")

# Check Chelsea GK situation  
print('\nChelsea GK situation:')
chelsea_gks = predictions[(predictions['role'] == 'GK') & (predictions['club'] == "Chelsea")]
for _, gk in chelsea_gks.iterrows():
    print(f"  {gk['first_name']} {gk['last_name']}: £{gk['price']}m, score: {gk['weighted_score']:.2f}")

# Check if any teams have Filip Jörgensen as starting GK
filip_starting = df[df['GK1'].str.contains('Filip Jörgensen', na=False)]
print(f'\nTeams with Filip Jörgensen as starting GK: {len(filip_starting)}')
if len(filip_starting) > 0:
    print('  These teams should have Mike Penders as backup')