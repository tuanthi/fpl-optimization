#!/usr/bin/env python3
"""
Rearrange columns in top 200 teams CSV to natural order:
captain, formation, budget, gw1_score, 5gw_estimated, 
then GK1, GK2, DEF1, DEF2, ..., MID1, MID2, ..., FWD1, FWD2, ...
Each player with all their associated columns (_role, _selected, _price, _score)
"""

import pandas as pd
import re


def get_player_columns(df, prefix):
    """Get all columns for a specific player position"""
    base_col = prefix
    if base_col not in df.columns:
        return []
    
    # Get all associated columns for this player
    cols = [base_col]
    for suffix in ['_role', '_selected', '_price', '_score']:
        col = f"{prefix}{suffix}"
        if col in df.columns:
            cols.append(col)
    
    return cols


def rearrange_columns_natural(input_file, output_file):
    """Rearrange columns in natural order"""
    
    # Load the teams
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} teams with {len(df.columns)} columns")
    
    # Key info columns (always first)
    key_cols = ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated']
    
    # Collect all other columns in natural order
    ordered_cols = key_cols.copy()
    
    # Extract all player position columns
    player_positions = []
    
    # Find all player columns (format: ROLE + number)
    pattern = re.compile(r'^(GK|DEF|MID|FWD|BENCH)(\d+)$')
    
    for col in df.columns:
        match = pattern.match(col)
        if match:
            role = match.group(1)
            num = int(match.group(2))
            player_positions.append((role, num, col))
    
    # Sort by role order and number
    role_order = {'GK': 1, 'DEF': 2, 'MID': 3, 'FWD': 4, 'BENCH': 5}
    player_positions.sort(key=lambda x: (role_order.get(x[0], 99), x[1]))
    
    # Add player columns with their associated columns
    print("\nColumn order:")
    print("Key columns:", key_cols)
    
    for role, num, base_col in player_positions:
        player_cols = get_player_columns(df, base_col)
        if player_cols:
            ordered_cols.extend(player_cols)
            if len(player_cols) > 1:  # Only print if there are associated columns
                print(f"{base_col}: {len(player_cols)} columns")
    
    # Add any remaining columns that weren't captured
    remaining_cols = [col for col in df.columns if col not in ordered_cols]
    if remaining_cols:
        print(f"\nAdding {len(remaining_cols)} remaining columns")
        ordered_cols.extend(remaining_cols)
    
    # Reorder dataframe
    df_reordered = df[ordered_cols]
    
    # Save to new file
    df_reordered.to_csv(output_file, index=False)
    
    print(f"\nSaved reordered teams to {output_file}")
    print(f"Total columns: {len(ordered_cols)}")
    
    # Show sample of first team
    print("\nFirst team sample:")
    first_team = df_reordered.iloc[0]
    
    print(f"Captain: {first_team['captain']}")
    print(f"Formation: {first_team['formation']}")
    print(f"Budget: £{first_team['budget']}m")
    print(f"GW1 Score: {first_team['gw1_score']}")
    print(f"5GW Estimated: {first_team['5gw_estimated']}")
    
    # Show first few players
    print("\nFirst few players:")
    for role in ['GK', 'DEF', 'MID', 'FWD']:
        for i in range(1, 3):
            col = f"{role}{i}"
            if col in df_reordered.columns and pd.notna(first_team[col]):
                price_col = f"{col}_price"
                score_col = f"{col}_score"
                selected_col = f"{col}_selected"
                
                print(f"{col}: {first_team[col]}")
                if price_col in df_reordered.columns:
                    selected_status = "Starting" if first_team.get(selected_col, 0) == 1 else "Bench"
                    print(f"  {selected_status}, £{first_team[price_col]}m, Score: {first_team[score_col]:.2f}")


def main():
    # Can work with any of the top 200 teams files
    input_file = "../data/cached_merged_2024_2025_v2/top_200_teams_final_v3.csv"
    output_file = "../data/cached_merged_2024_2025_v2/top_200_teams_final_v3_ordered.csv"
    
    rearrange_columns_natural(input_file, output_file)


if __name__ == "__main__":
    main()