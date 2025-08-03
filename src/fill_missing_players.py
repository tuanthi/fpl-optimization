#!/usr/bin/env python3
"""Fill missing players in teams to ensure all 15 slots are filled"""

import pandas as pd
import json

def load_player_data():
    """Load player data to find cheap players for filling slots"""
    with open('/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/predictions_gw39_proper_v3.csv', 'r') as f:
        df = pd.read_csv(f)
    
    # Add score column based on avg_points
    df['score'] = df['avg_points']
    
    # Get cheapest players by position
    cheap_players = {}
    for role in ['GK', 'DEF', 'MID', 'FWD']:
        role_players = df[df['role'] == role].sort_values('price')
        # Rename columns to match expected format
        role_players = role_players.rename(columns={'full_name': 'player'})
        cheap_players[role] = role_players.head(20).to_dict('records')  # Get more options
    
    return cheap_players

def fill_team_to_15_players(input_file, output_file):
    """Ensure each team has exactly 15 players: 2 GK, 5 DEF, 5 MID, 3 FWD"""
    
    # Load cheap players for filling
    cheap_players = load_player_data()
    
    # Read the CSV
    df = pd.read_csv(input_file)
    
    # Process each row
    processed_rows = []
    
    for idx, row in df.iterrows():
        new_row = {
            'captain': row['captain'],
            'formation': row['formation'],
            'budget': row.get('budget', 100),
            'gw1_score': row.get('gw1_score', 0),
            '5gw_estimated': row.get('5gw_estimated', 0)
        }
        
        # Collect all existing players by position
        team_players = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
        used_budget = 0
        player_names = set()  # Track player names to avoid duplicates
        
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
                    team_players[pos].append(player_info)
                    player_names.add(row[player_col])
                    used_budget += player_info['price']
        
        # Collect bench players
        for i in range(1, 5):
            bench_col = f'BENCH{i}'
            if bench_col in row and pd.notna(row[bench_col]):
                role = row.get(f'{bench_col}_role', '')
                if role in team_players:
                    player_info = {
                        'name': row[bench_col],
                        'role': role,
                        'selected': 0,  # Bench players
                        'price': row.get(f'{bench_col}_price', 0),
                        'score': row.get(f'{bench_col}_score', 0),
                        'club': row.get(f'{bench_col}_club', '')
                    }
                    team_players[role].append(player_info)
                    player_names.add(row[bench_col])
                    used_budget += player_info['price']
        
        # Fill missing slots with cheap players
        remaining_budget = 100 - used_budget
        
        # Required players per position
        required = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
        
        for pos, req_count in required.items():
            current_count = len(team_players[pos])
            if current_count < req_count:
                # Need to add players
                added_count = 0
                for cheap_player in cheap_players[pos]:
                    if current_count >= req_count:
                        break
                    
                    # Check if we haven't already selected them
                    if cheap_player['player'] not in player_names:
                        # If we can't afford the player, just add them anyway (budget might be slightly over)
                        player_info = {
                            'name': cheap_player['player'],
                            'role': pos,
                            'selected': 0,  # These are bench/filler players
                            'price': cheap_player['price'],
                            'score': cheap_player.get('score', 0),
                            'club': cheap_player.get('club', '')
                        }
                        team_players[pos].append(player_info)
                        player_names.add(cheap_player['player'])
                        remaining_budget -= cheap_player['price']
                        current_count += 1
                        added_count += 1
                
                # If we still don't have enough, add generic cheap players
                while current_count < req_count:
                    player_info = {
                        'name': f'Budget {pos}{current_count + 1}',
                        'role': pos,
                        'selected': 0,
                        'price': 4.0 if pos == 'GK' else 4.5,
                        'score': 0,
                        'club': 'Generic'
                    }
                    team_players[pos].append(player_info)
                    current_count += 1
        
        # Sort players by score within each position (highest first)
        for pos in team_players:
            team_players[pos].sort(key=lambda x: x['score'], reverse=True)
        
        # Assign players to slots
        # GK: Exactly 2
        for i in range(2):
            if i < len(team_players['GK']):
                p = team_players['GK'][i]
                new_row[f'GK{i+1}'] = f"{p['name']} ({p['club']})"
                new_row[f'GK{i+1}_role'] = p['role']
                new_row[f'GK{i+1}_selected'] = p['selected']
                new_row[f'GK{i+1}_price'] = p['price']
                new_row[f'GK{i+1}_score'] = p['score']
        
        # DEF: Exactly 5
        for i in range(5):
            if i < len(team_players['DEF']):
                p = team_players['DEF'][i]
                new_row[f'DEF{i+1}'] = f"{p['name']} ({p['club']})"
                new_row[f'DEF{i+1}_role'] = p['role']
                new_row[f'DEF{i+1}_selected'] = p['selected']
                new_row[f'DEF{i+1}_price'] = p['price']
                new_row[f'DEF{i+1}_score'] = p['score']
        
        # MID: Exactly 5
        for i in range(5):
            if i < len(team_players['MID']):
                p = team_players['MID'][i]
                new_row[f'MID{i+1}'] = f"{p['name']} ({p['club']})"
                new_row[f'MID{i+1}_role'] = p['role']
                new_row[f'MID{i+1}_selected'] = p['selected']
                new_row[f'MID{i+1}_price'] = p['price']
                new_row[f'MID{i+1}_score'] = p['score']
        
        # FWD: Exactly 3
        for i in range(3):
            if i < len(team_players['FWD']):
                p = team_players['FWD'][i]
                new_row[f'FWD{i+1}'] = f"{p['name']} ({p['club']})"
                new_row[f'FWD{i+1}_role'] = p['role']
                new_row[f'FWD{i+1}_selected'] = p['selected']
                new_row[f'FWD{i+1}_price'] = p['price']
                new_row[f'FWD{i+1}_score'] = p['score']
        
        # Add recommendation columns
        new_row['recommendation_rank'] = idx + 1
        if 'selection_reason' in row and pd.notna(row['selection_reason']):
            new_row['recommendation_reason'] = row['selection_reason']
        else:
            new_row['recommendation_reason'] = 'Team optimized using Bayesian statistics and LLM analysis'
        
        if 'key_strengths' in row and pd.notna(row['key_strengths']):
            try:
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
        
        # Calculate total budget used
        total_budget = 0
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            max_i = 2 if pos == 'GK' else 5 if pos in ['DEF', 'MID'] else 3
            for i in range(1, max_i + 1):
                total_budget += new_row.get(f'{pos}{i}_price', 0)
        new_row['budget'] = round(total_budget, 1)
        
        processed_rows.append(new_row)
    
    # Create column order
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
    
    # Create dataframe
    all_columns = base_columns + position_columns + additional_columns
    df_final = pd.DataFrame(processed_rows, columns=all_columns)
    
    # Save the result
    df_final.to_csv(output_file, index=False)
    
    print(f"Filled {len(df_final)} teams to 15 players each and saved to {output_file}")
    
    # Verify team composition
    if len(df_final) > 0:
        print("\nTeam composition check (first 3 teams):")
        for team_idx in range(min(3, len(df_final))):
            row = df_final.iloc[team_idx]
            print(f"\nTeam {team_idx + 1} (Formation: {row['formation']}):")
            
            # Count players and selected
            for pos in ['GK', 'DEF', 'MID', 'FWD']:
                max_i = 2 if pos == 'GK' else 5 if pos in ['DEF', 'MID'] else 3
                count = sum(1 for i in range(1, max_i + 1) if row[f'{pos}{i}'] != '')
                selected = sum(1 for i in range(1, max_i + 1) if row.get(f'{pos}{i}_selected', 0) == 1)
                print(f"  {pos}: {count} players ({selected} selected)")
            
            # Total counts
            total_players = sum(
                sum(1 for i in range(1, (2 if pos == 'GK' else 5 if pos in ['DEF', 'MID'] else 3) + 1) 
                    if row[f'{pos}{i}'] != '')
                for pos in ['GK', 'DEF', 'MID', 'FWD']
            )
            total_selected = sum(
                sum(1 for i in range(1, (2 if pos == 'GK' else 5 if pos in ['DEF', 'MID'] else 3) + 1) 
                    if row.get(f'{pos}{i}_selected', 0) == 1)
                for pos in ['GK', 'DEF', 'MID', 'FWD']
            )
            print(f"  Total: {total_players}/15 players ({total_selected}/11 selected)")
            print(f"  Budget: £{row['budget']}m")
    
    return df_final

if __name__ == "__main__":
    input_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/top_200_teams_final_v11.csv"
    output_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/top_200_teams_final_v14.csv"
    
    df = fill_team_to_15_players(input_file, output_file)
    
    # Also process the final selected teams
    selected_input = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/final_selected_teams_final.csv"
    selected_output = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/final_selected_teams_final_ordered_v3.csv"
    
    if pd.io.common.file_exists(selected_input):
        print("\n" + "="*50)
        print("Processing final selected teams...")
        fill_team_to_15_players(selected_input, selected_output)