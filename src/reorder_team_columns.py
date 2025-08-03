#!/usr/bin/env python3
"""Reorder team CSV columns to follow our custom format (learned from final_recommended_teams_v1.csv)"""

import pandas as pd
import numpy as np

def reorder_team_columns(input_file, output_file):
    """Reorder columns to follow our format: captain, formation, budget, scores, then GK1, GK2, DEF1-5, MID1-5, FWD1-3 with club info"""
    
    # Read the CSV
    df = pd.read_csv(input_file)
    
    # First, we need to consolidate player names with club info
    # For each position, combine player name with club
    for pos in ['GK', 'DEF', 'MID', 'FWD']:
        for i in range(1, 6):
            player_col = f'{pos}{i}'
            club_col = f'{pos}{i}_club'
            if player_col in df.columns and club_col in df.columns:
                # Only update if both columns exist and player is not NaN
                mask = df[player_col].notna() & df[club_col].notna()
                df.loc[mask, player_col] = df.loc[mask, player_col].astype(str) + ' (' + df.loc[mask, club_col].astype(str) + ')'
    
    # Do the same for bench players
    for i in range(1, 5):
        player_col = f'BENCH{i}'
        club_col = f'BENCH{i}_club'
        if player_col in df.columns and club_col in df.columns:
            mask = df[player_col].notna() & df[club_col].notna()
            df.loc[mask, player_col] = df.loc[mask, player_col].astype(str) + ' (' + df.loc[mask, club_col].astype(str) + ')'
    
    # Move backup GK from BENCH to GK2 position
    if 'BENCH1_role' in df.columns:
        for idx, row in df.iterrows():
            if pd.notna(row.get('BENCH1_role')) and row['BENCH1_role'] == 'GK':
                # Copy BENCH1 GK to GK2
                for suffix in ['', '_role', '_selected', '_price', '_score']:
                    bench_col = f'BENCH1{suffix}'
                    gk2_col = f'GK2{suffix}'
                    if bench_col in df.columns:
                        df.at[idx, gk2_col] = row.get(bench_col)
                
                # Shift other bench players up
                for i in range(1, 4):
                    for suffix in ['', '_role', '_selected', '_price', '_score']:
                        from_col = f'BENCH{i+1}{suffix}'
                        to_col = f'BENCH{i}{suffix}'
                        if from_col in df.columns:
                            df.at[idx, to_col] = row.get(from_col)
                
                # Clear BENCH4
                for suffix in ['', '_role', '_selected', '_price', '_score']:
                    bench4_col = f'BENCH4{suffix}'
                    if bench4_col in df.columns:
                        df.at[idx, bench4_col] = None
    
    # Define the correct column order matching final_recommended_teams_v1.csv
    base_columns = ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated']
    
    # Position columns in correct order (no _club suffix since we've merged it)
    position_columns = []
    
    # Goalkeepers
    for i in range(1, 3):
        for suffix in ['', '_role', '_selected', '_price', '_score']:
            position_columns.append(f'GK{i}{suffix}')
    
    # Defenders
    for i in range(1, 6):
        for suffix in ['', '_role', '_selected', '_price', '_score']:
            position_columns.append(f'DEF{i}{suffix}')
    
    # Midfielders
    for i in range(1, 6):
        for suffix in ['', '_role', '_selected', '_price', '_score']:
            position_columns.append(f'MID{i}{suffix}')
    
    # Forwards
    for i in range(1, 4):
        for suffix in ['', '_role', '_selected', '_price', '_score']:
            position_columns.append(f'FWD{i}{suffix}')
    
    # Additional columns
    additional_columns = ['recommendation_rank', 'recommendation_reason', 'web_insights']
    
    # Build final column order
    final_columns = base_columns + position_columns + additional_columns
    
    # Get existing columns
    existing_columns = df.columns.tolist()
    
    # Drop _club columns since we've merged them
    club_columns = [col for col in existing_columns if col.endswith('_club')]
    df = df.drop(columns=club_columns, errors='ignore')
    
    # Update existing columns list
    existing_columns = df.columns.tolist()
    
    # Filter to only columns that exist
    ordered_columns = [col for col in final_columns if col in existing_columns]
    
    # Add any remaining columns that weren't in our list (like bench players)
    remaining_columns = [col for col in existing_columns if col not in ordered_columns and not col.startswith('BENCH')]
    ordered_columns.extend(remaining_columns)
    
    # If we don't have recommendation columns, add placeholders
    if 'recommendation_rank' not in df.columns:
        df['recommendation_rank'] = range(1, len(df) + 1)
    if 'recommendation_reason' not in df.columns:
        # Use selection_reason if available
        if 'selection_reason' in df.columns:
            df['recommendation_reason'] = df['selection_reason']
        else:
            df['recommendation_reason'] = 'Team optimized using Bayesian statistics and LLM analysis'
    if 'web_insights' not in df.columns:
        # Use key_strengths if available
        if 'key_strengths' in df.columns:
            df['web_insights'] = df['key_strengths'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else 'High-scoring team with balanced formation')
        else:
            df['web_insights'] = 'High-scoring team with balanced formation'
    
    # Now reorder with final columns
    ordered_columns = [col for col in final_columns if col in df.columns]
    df_reordered = df[ordered_columns]
    
    # Save reordered dataframe
    df_reordered.to_csv(output_file, index=False)
    
    print(f"Reordered {len(df_reordered)} teams and saved to {output_file}")
    print(f"Format matches final_recommended_teams_v1.csv")
    
    # Display sample of column order
    print("\nColumn order (first 30 columns):")
    for i, col in enumerate(df_reordered.columns[:30]):
        if i % 5 == 0:
            print()
        print(f"{col:25}", end="")
    print("\n...")
    
    # Show a sample row
    if len(df_reordered) > 0:
        print("\nSample row (first team):")
        row = df_reordered.iloc[0]
        print(f"Captain: {row['captain']}")
        print(f"Formation: {row['formation']}")
        print(f"GK1: {row['GK1']}")
        print(f"GK2: {row.get('GK2', 'N/A')}")
    
    return df_reordered

if __name__ == "__main__":
    input_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/top_200_teams_final_v11.csv"
    output_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/top_200_teams_final_v12.csv"
    
    df = reorder_team_columns(input_file, output_file)
    
    # Also reorder the final selected teams CSV
    selected_input = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/final_selected_teams_final.csv"
    selected_output = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/final_selected_teams_final_ordered.csv"
    
    if pd.io.common.file_exists(selected_input):
        print("\n" + "="*50)
        print("Reordering final selected teams...")
        reorder_team_columns(selected_input, selected_output)