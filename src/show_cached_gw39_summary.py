#!/usr/bin/env python3
"""
Show summary of cached gameweek 39 data
"""

import pandas as pd
from pathlib import Path
import json


def main():
    cache_dir = Path("data/cached_merged_2024_2025_v2")
    
    print("="*70)
    print("GAMEWEEK 39 CACHED DATA SUMMARY")
    print("="*70)
    
    # Show player mappings
    mapping_file = cache_dir / "player_mapping_gw39.csv"
    if mapping_file.exists():
        mapping_df = pd.read_csv(mapping_file)
        
        print("\n1. PLAYER TRANSFERS (2024 -> 2025):")
        print("-"*50)
        
        # Show players who changed clubs
        transfers = mapping_df[
            (mapping_df['team_2024'] != mapping_df['team_2025']) & 
            (mapping_df['mapping_type'] == 'direct_match')
        ]
        
        if len(transfers) > 0:
            print(f"Found {len(transfers)} players who changed clubs:\n")
            for _, row in transfers.head(15).iterrows():
                print(f"  • {row['player_2025']}: {row['team_2024']} → {row['team_2025']} "
                      f"({row['total_points_2024']} pts)")
            if len(transfers) > 15:
                print(f"  ... and {len(transfers) - 15} more")
        
        print(f"\n2. MAPPING SUMMARY:")
        print("-"*50)
        print("Mapping types:")
        print(mapping_df['mapping_type'].value_counts())
        
        print(f"\nTotal players mapped: {len(mapping_df)}")
        
    # Show top team
    teams_file = cache_dir / "top_50_teams_gw39.csv"
    if teams_file.exists():
        teams_df = pd.read_csv(teams_file)
        
        print("\n3. TOP TEAM FOR GAMEWEEK 39:")
        print("-"*50)
        
        if len(teams_df) > 0:
            top_team = teams_df.iloc[0]
            
            print("\nStarting XI:")
            for pos in ['GK', 'DEF', 'MID', 'FWD']:
                print(f"\n{pos}:")
                for i in range(1, 6):
                    col = f'{pos}{i}'
                    if col in top_team and pd.notna(top_team[col]):
                        if top_team.get(f'{col}_selected', 0) == 1:
                            print(f"  ★ {top_team[col]} - £{top_team[f'{col}_price']:.1f}m "
                                  f"({top_team[f'{col}_score']:.2f} pts)")
                        else:
                            print(f"    {top_team[col]} - £{top_team[f'{col}_price']:.1f}m")
            
            print(f"\nTotal Squad Value: £{top_team['15_total_price']:.1f}m")
            print(f"Predicted Score: {top_team['11_selected_total_scores']:.2f} pts")
    
    # Show cache info
    print("\n4. CACHED FILES:")
    print("-"*50)
    for file in cache_dir.glob("*.csv"):
        print(f"  • {file.name}")
    
    print(f"\n✓ All gameweek 39 data cached in: {cache_dir}")
    print("\nThis cached data can be reused for future gameweeks (40+)")


if __name__ == "__main__":
    main()