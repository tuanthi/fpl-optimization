#!/usr/bin/env python3
"""Debug team mapping issue"""

import pandas as pd

# Load players
players_df = pd.read_csv("data/9999/9999_players.csv")
teams_df = pd.read_csv("data/9999/9999_teams.csv")
gameweek_df = pd.read_csv("data/9999/9999_player_gameweek.csv")

# Check team mapping
print("Teams in teams file:")
print(teams_df[['id', 'name']].head(10))
print()

# Check specific players
print("Checking specific players:")
meslier = players_df[players_df['second_name'] == 'Meslier']
if len(meslier) > 0:
    print(f"Meslier: ID={meslier.iloc[0]['id']}, Team={meslier.iloc[0]['team']}")
    
trafford = players_df[players_df['second_name'] == 'Trafford']
if len(trafford) > 0:
    print(f"Trafford: ID={trafford.iloc[0]['id']}, Team={trafford.iloc[0]['team']}")

# Check in gameweek data
print("\nIn gameweek data:")
gw_meslier = gameweek_df[gameweek_df['element'] == 339]
if len(gw_meslier) > 0:
    print(f"Meslier (339) plays for: {gw_meslier.iloc[0]['team']}")
    
gw_trafford = gameweek_df[gameweek_df['element'] == 182]
if len(gw_trafford) > 0:
    print(f"Trafford (182) plays for: {gw_trafford.iloc[0]['team']}")

# Check what string 'Liverpool' maps to
print("\nChecking team name 'Liverpool':")
liverpool_team = teams_df[teams_df['name'] == 'Liverpool']
if len(liverpool_team) > 0:
    print(f"Liverpool has ID: {liverpool_team.iloc[0]['id']}")
    
# Check Meslier in gameweek - what team ID?
print("\nChecking Meslier gameweek entries:")
meslier_gw = gameweek_df[gameweek_df['name'].str.contains('Meslier', na=False)]
if len(meslier_gw) > 0:
    print(f"Found {len(meslier_gw)} entries")
    print(f"First entry: element={meslier_gw.iloc[0]['element']}, team={meslier_gw.iloc[0]['team']}")