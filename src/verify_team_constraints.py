#!/usr/bin/env python3
"""Verify all teams meet the 3 player per team constraint"""

import pandas as pd
import sys

def verify_team_constraints(teams_file):
    """Check all teams for 3 player per team constraint"""
    df = pd.read_csv(teams_file)
    
    violations = []
    
    for idx, team in df.iterrows():
        # Count players per club
        club_counts = {}
        
        # Count starting XI
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for i in range(1, 6):  # Max 5 of any position
                player_col = f'{pos}{i}'
                club_col = f'{pos}{i}_club'
                
                if player_col in team and pd.notna(team[player_col]):
                    if club_col in team and pd.notna(team[club_col]):
                        club = team[club_col]
                        club_counts[club] = club_counts.get(club, 0) + 1
        
        # Count bench
        for i in range(1, 5):
            player_col = f'BENCH{i}'
            club_col = f'BENCH{i}_club'
            
            if player_col in team and pd.notna(team[player_col]):
                if club_col in team and pd.notna(team[club_col]):
                    club = team[club_col]
                    club_counts[club] = club_counts.get(club, 0) + 1
        
        # Check for violations
        team_violations = []
        for club, count in club_counts.items():
            if count > 3:
                team_violations.append(f"{club}: {count} players")
        
        if team_violations:
            violations.append({
                'team_idx': idx + 1,
                'captain': team['captain'],
                'formation': team['formation'],
                'violations': team_violations
            })
    
    # Report results
    if violations:
        print(f"❌ Found {len(violations)} teams with constraint violations out of {len(df)} teams")
        print("\nViolations:")
        for v in violations[:10]:  # Show first 10
            print(f"\nTeam {v['team_idx']}: {v['captain']} ({v['formation']})")
            for violation in v['violations']:
                print(f"  - {violation}")
    else:
        print(f"✅ All {len(df)} teams satisfy the 3 player per team constraint!")
        
        # Show distribution of teams with 3 players from same club
        print("\nTeams with 3 players from same club:")
        triple_teams = {}
        
        for idx, team in df.iterrows():
            # Count players per club
            club_counts = {}
            
            # Count starting XI
            for pos in ['GK', 'DEF', 'MID', 'FWD']:
                for i in range(1, 6):
                    player_col = f'{pos}{i}'
                    club_col = f'{pos}{i}_club'
                    
                    if player_col in team and pd.notna(team[player_col]):
                        if club_col in team and pd.notna(team[club_col]):
                            club = team[club_col]
                            club_counts[club] = club_counts.get(club, 0) + 1
            
            # Count bench
            for i in range(1, 5):
                player_col = f'BENCH{i}'
                club_col = f'BENCH{i}_club'
                
                if player_col in team and pd.notna(team[player_col]):
                    if club_col in team and pd.notna(team[club_col]):
                        club = team[club_col]
                        club_counts[club] = club_counts.get(club, 0) + 1
            
            # Track teams with exactly 3 players
            for club, count in club_counts.items():
                if count == 3:
                    triple_teams[club] = triple_teams.get(club, 0) + 1
        
        # Show most common triple-ups
        sorted_triples = sorted(triple_teams.items(), key=lambda x: -x[1])
        for club, count in sorted_triples[:5]:
            print(f"  {club}: {count} teams")
    
    return len(violations) == 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        teams_file = sys.argv[1]
    else:
        teams_file = "data/cached_merged_2024_2025_v2/top_200_teams_final_v8.csv"
    
    verify_team_constraints(teams_file)