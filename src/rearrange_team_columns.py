#!/usr/bin/env python3
"""
Rearrange columns in the top 200 teams CSV for better readability
"""

import pandas as pd
import numpy as np


def rearrange_team_columns(input_file, output_file):
    """Rearrange columns in team CSV"""
    
    # Load the teams
    df = pd.read_csv(input_file)
    
    # Define column order
    # 1. Key info columns
    key_cols = ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated']
    
    # 2. Selected players (in position order)
    selected_cols = []
    
    # Selected GKs
    for i in range(1, 3):
        if f'GK{i}' in df.columns and f'GK{i}_selected' in df.columns:
            # Only include if selected
            mask = df[f'GK{i}_selected'] == 1
            if mask.any():
                selected_cols.append(f'GK{i}')
    
    # Selected DEFs
    for i in range(1, 8):
        if f'DEF{i}' in df.columns and f'DEF{i}_selected' in df.columns:
            mask = df[f'DEF{i}_selected'] == 1
            if mask.any():
                selected_cols.append(f'DEF{i}')
    
    # Selected MIDs
    for i in range(1, 6):
        if f'MID{i}' in df.columns and f'MID{i}_selected' in df.columns:
            mask = df[f'MID{i}_selected'] == 1
            if mask.any():
                selected_cols.append(f'MID{i}')
    
    # Selected FWDs
    for i in range(1, 4):
        if f'FWD{i}' in df.columns and f'FWD{i}_selected' in df.columns:
            mask = df[f'FWD{i}_selected'] == 1
            if mask.any():
                selected_cols.append(f'FWD{i}')
    
    # 3. Bench players (GK first, then by score)
    bench_players = []
    
    # Collect all bench players with their scores
    for pos in ['GK', 'DEF', 'MID', 'FWD']:
        for i in range(1, 8):
            col = f'{pos}{i}'
            if col in df.columns and f'{col}_selected' in df.columns:
                # Check if this is a bench player
                mask = df[f'{col}_selected'] == 0
                if mask.any():
                    # Get average score for sorting
                    if f'{col}_score' in df.columns:
                        avg_score = df[df[f'{col}_selected'] == 0][f'{col}_score'].mean()
                    else:
                        avg_score = 0
                    bench_players.append((col, pos, avg_score))
    
    # Sort bench players: GKs first, then by score descending
    bench_players.sort(key=lambda x: (x[1] != 'GK', -x[2]))
    bench_cols = [p[0] for p in bench_players]
    
    # Build final column order
    final_cols = []
    
    # Add key columns that exist
    for col in key_cols:
        if col in df.columns:
            final_cols.append(col)
    
    # Add selected players
    final_cols.extend(selected_cols)
    
    # Add bench players
    final_cols.extend(bench_cols)
    
    # Create new dataframe with rearranged columns
    df_new = df[final_cols].copy()
    
    # Save to new file
    df_new.to_csv(output_file, index=False)
    
    print(f"Rearranged {len(df)} teams")
    print(f"Columns: {len(final_cols)}")
    print("\nColumn order:")
    print("- Key info:", key_cols)
    print("- Selected players:", len(selected_cols))
    print("- Bench players:", len(bench_cols))
    
    # Show sample
    print("\nSample of top 3 teams:")
    for idx, row in df_new.head(3).iterrows():
        print(f"\nTeam {idx + 1}:")
        print(f"  Captain: {row['captain']}")
        print(f"  Formation: {row['formation']}")
        print(f"  Budget: £{row['budget']}m")
        print(f"  GW1: {row['gw1_score']} pts")
        print(f"  5GW: {row['5gw_estimated']} pts")
        
        print("\n  Starting XI:")
        for col in selected_cols:
            if col in row and pd.notna(row[col]):
                print(f"    {col}: {row[col]}")
        
        print("\n  Bench:")
        for col in bench_cols[:4]:  # Show first 4 bench players
            if col in row and pd.notna(row[col]):
                print(f"    {col}: {row[col]}")


def main():
    input_file = "data/cached_merged_2024_2025_v2/top_200_teams_final.csv"
    output_file = "data/cached_merged_2024_2025_v2/top_200_teams_final_sorted.csv"
    
    rearrange_team_columns(input_file, output_file)


if __name__ == "__main__":
    main()