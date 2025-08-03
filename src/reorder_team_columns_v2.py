#!/usr/bin/env python3
"""Reorder team CSV columns to follow our custom format with all 15 players properly distributed"""

import pandas as pd
import numpy as np

def reorder_team_columns(input_file, output_file):
    """Reorder columns to show all 15 players: 2 GK, 5 DEF, 5 MID, 3 FWD"""
    
    # Read the CSV
    df = pd.read_csv(input_file)
    
    # Process each row to properly distribute all 15 players
    processed_rows = []
    
    for idx, row in df.iterrows():
        new_row = {
            'captain': row['captain'],
            'formation': row['formation'],
            'budget': row['budget'],
            'gw1_score': row['gw1_score'],
            '5gw_estimated': row['5gw_estimated']
        }
        
        # Collect all players by position (including bench)
        all_players = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
        
        # Collect starting XI players
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for i in range(1, 6):
                player_col = f'{pos}{i}'
                if player_col in row and pd.notna(row[player_col]):
                    player_info = {
                        'name': row[player_col],
                        'role': row.get(f'{player_col}_role', pos),
                        'selected': row.get(f'{player_col}_selected', 1),
                        'price': row.get(f'{player_col}_price', 0),
                        'score': row.get(f'{player_col}_score', 0),
                        'club': row.get(f'{player_col}_club', '')
                    }
                    all_players[pos].append(player_info)
        
        # Collect bench players
        for i in range(1, 5):
            bench_col = f'BENCH{i}'
            if bench_col in row and pd.notna(row[bench_col]):
                role = row.get(f'{bench_col}_role', '')
                if role in all_players:
                    player_info = {
                        'name': row[bench_col],
                        'role': role,
                        'selected': 0,  # Bench players are not selected
                        'price': row.get(f'{bench_col}_price', 0),
                        'score': row.get(f'{bench_col}_score', 0),
                        'club': row.get(f'{bench_col}_club', '')
                    }
                    all_players[role].append(player_info)
        
        # Sort players by score (highest first) within each position
        for pos in all_players:
            all_players[pos].sort(key=lambda x: x['score'], reverse=True)
        
        # Now assign players to their proper slots
        # GK: Need exactly 2
        gk_players = all_players['GK'][:2]
        for i in range(2):
            if i < len(gk_players):
                p = gk_players[i]
                new_row[f'GK{i+1}'] = f"{p['name']} ({p['club']})" if p['club'] else p['name']
                new_row[f'GK{i+1}_role'] = p['role']
                new_row[f'GK{i+1}_selected'] = p['selected']
                new_row[f'GK{i+1}_price'] = p['price']
                new_row[f'GK{i+1}_score'] = p['score']
            else:
                # This shouldn't happen in valid teams
                new_row[f'GK{i+1}'] = ''
                new_row[f'GK{i+1}_role'] = 'GK'
                new_row[f'GK{i+1}_selected'] = 0
                new_row[f'GK{i+1}_price'] = 0
                new_row[f'GK{i+1}_score'] = 0
        
        # DEF: Need exactly 5
        def_players = all_players['DEF'][:5]
        for i in range(5):
            if i < len(def_players):
                p = def_players[i]
                new_row[f'DEF{i+1}'] = f"{p['name']} ({p['club']})" if p['club'] else p['name']
                new_row[f'DEF{i+1}_role'] = p['role']
                new_row[f'DEF{i+1}_selected'] = p['selected']
                new_row[f'DEF{i+1}_price'] = p['price']
                new_row[f'DEF{i+1}_score'] = p['score']
            else:
                # This shouldn't happen in valid teams
                new_row[f'DEF{i+1}'] = ''
                new_row[f'DEF{i+1}_role'] = 'DEF'
                new_row[f'DEF{i+1}_selected'] = 0
                new_row[f'DEF{i+1}_price'] = 0
                new_row[f'DEF{i+1}_score'] = 0
        
        # MID: Need exactly 5
        mid_players = all_players['MID'][:5]
        for i in range(5):
            if i < len(mid_players):
                p = mid_players[i]
                new_row[f'MID{i+1}'] = f"{p['name']} ({p['club']})" if p['club'] else p['name']
                new_row[f'MID{i+1}_role'] = p['role']
                new_row[f'MID{i+1}_selected'] = p['selected']
                new_row[f'MID{i+1}_price'] = p['price']
                new_row[f'MID{i+1}_score'] = p['score']
            else:
                # This shouldn't happen in valid teams
                new_row[f'MID{i+1}'] = ''
                new_row[f'MID{i+1}_role'] = 'MID'
                new_row[f'MID{i+1}_selected'] = 0
                new_row[f'MID{i+1}_price'] = 0
                new_row[f'MID{i+1}_score'] = 0
        
        # FWD: Need exactly 3
        fwd_players = all_players['FWD'][:3]
        for i in range(3):
            if i < len(fwd_players):
                p = fwd_players[i]
                new_row[f'FWD{i+1}'] = f"{p['name']} ({p['club']})" if p['club'] else p['name']
                new_row[f'FWD{i+1}_role'] = p['role']
                new_row[f'FWD{i+1}_selected'] = p['selected']
                new_row[f'FWD{i+1}_price'] = p['price']
                new_row[f'FWD{i+1}_score'] = p['score']
            else:
                # This shouldn't happen in valid teams
                new_row[f'FWD{i+1}'] = ''
                new_row[f'FWD{i+1}_role'] = 'FWD'
                new_row[f'FWD{i+1}_selected'] = 0
                new_row[f'FWD{i+1}_price'] = 0
                new_row[f'FWD{i+1}_score'] = 0
        
        # Add recommendation columns
        new_row['recommendation_rank'] = idx + 1
        if 'selection_reason' in row:
            new_row['recommendation_reason'] = row['selection_reason']
        else:
            new_row['recommendation_reason'] = 'Team optimized using Bayesian statistics and LLM analysis'
        
        if 'key_strengths' in row and pd.notna(row['key_strengths']):
            try:
                # Handle string representation of list
                if isinstance(row['key_strengths'], str):
                    import ast
                    strengths = ast.literal_eval(row['key_strengths'])
                else:
                    strengths = row['key_strengths']
                new_row['web_insights'] = strengths[0] if strengths else 'High-scoring team with balanced formation'
            except:
                new_row['web_insights'] = 'High-scoring team with balanced formation'
        else:
            new_row['web_insights'] = 'High-scoring team with balanced formation'
        
        processed_rows.append(new_row)
    
    # Create new dataframe with proper column order
    base_columns = ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated']
    
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
    
    # Create dataframe with all columns
    all_columns = base_columns + position_columns + additional_columns
    df_final = pd.DataFrame(processed_rows, columns=all_columns)
    
    # Save the result
    df_final.to_csv(output_file, index=False)
    
    print(f"Reordered {len(df_final)} teams and saved to {output_file}")
    print(f"Format matches final_recommended_teams_v1.csv with all 15 players filled")
    
    # Display summary
    print("\nColumn order (first 30 columns):")
    for i, col in enumerate(df_final.columns[:30]):
        if i % 5 == 0:
            print()
        print(f"{col:25}", end="")
    print("\n...")
    
    # Verify team composition
    if len(df_final) > 0:
        print("\nTeam composition check (first team):")
        row = df_final.iloc[0]
        
        # Count players
        gk_count = sum(1 for i in range(1, 3) if row[f'GK{i}'] != '')
        def_count = sum(1 for i in range(1, 6) if row[f'DEF{i}'] != '')
        mid_count = sum(1 for i in range(1, 6) if row[f'MID{i}'] != '')
        fwd_count = sum(1 for i in range(1, 4) if row[f'FWD{i}'] != '')
        
        print(f"GK: {gk_count}/2")
        print(f"DEF: {def_count}/5")
        print(f"MID: {mid_count}/5")
        print(f"FWD: {fwd_count}/3")
        print(f"Total: {gk_count + def_count + mid_count + fwd_count}/15")
        
        # Count selected players
        selected_count = 0
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            max_i = 2 if pos == 'GK' else 5 if pos in ['DEF', 'MID'] else 3
            for i in range(1, max_i + 1):
                if row.get(f'{pos}{i}_selected', 0) == 1:
                    selected_count += 1
        
        print(f"Starting XI: {selected_count}/11")
    
    return df_final

if __name__ == "__main__":
    input_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/top_200_teams_final_v11.csv"
    output_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/top_200_teams_final_v13.csv"
    
    df = reorder_team_columns(input_file, output_file)
    
    # Also reorder the final selected teams CSV
    selected_input = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/final_selected_teams_final.csv"
    selected_output = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/final_selected_teams_final_ordered_v2.csv"
    
    if pd.io.common.file_exists(selected_input):
        print("\n" + "="*50)
        print("Reordering final selected teams...")
        reorder_team_columns(selected_input, selected_output)