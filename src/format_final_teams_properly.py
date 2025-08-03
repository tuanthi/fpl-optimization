#!/usr/bin/env python3
"""
Properly format the final selected teams with correct column structure
"""

import pandas as pd
import json


def format_final_teams_correctly():
    """Create a properly formatted CSV of the final selected teams"""
    
    # Read the LLM analysis results
    with open("../data/cached_merged_2024_2025_v2/final_selected_teams_llm_v3.json", "r") as f:
        data = json.load(f)
    
    # Read the original teams CSV for complete data
    teams_df = pd.read_csv("../data/cached_merged_2024_2025_v2/top_200_teams_final_v11.csv")
    
    rows = []
    for i, team_selection in enumerate(data['selected_teams']):
        # Find matching team
        matching_teams = teams_df[
            (teams_df['captain'] == team_selection['captain']) & 
            (teams_df['formation'] == team_selection['formation']) &
            (abs(teams_df['budget'] - team_selection['budget']) < 0.1) &
            (abs(teams_df['gw1_score'] - team_selection['gw1_score']) < 0.1)
        ]
        
        if len(matching_teams) == 0:
            print(f"Warning: Could not find matching team for selection {i+1}")
            continue
            
        team = matching_teams.iloc[0]
        
        # Initialize row with basic info
        row = {
            'rank': i + 1,
            'captain': team['captain'],
            'formation': team['formation'],
            'budget': team['budget'],
            'gw1_score': team['gw1_score'],
            '5gw_estimated': team['5gw_estimated']
        }
        
        # Parse formation to understand expected counts
        formation_parts = team['formation'].split('-')
        expected_def = int(formation_parts[0])
        expected_mid = int(formation_parts[1])
        expected_fwd = int(formation_parts[2])
        
        # Collect all players by position
        starting_xi = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
        bench = []
        
        # Process all columns to find players
        for col in team.index:
            if col.endswith('_role') or col.endswith('_selected') or col.endswith('_price') or col.endswith('_score') or col.endswith('_club'):
                continue
                
            # Check if this is a player column (GK1, DEF1, MID1, FWD1, BENCH1, etc.)
            if any(col.startswith(pos) for pos in ['GK', 'DEF', 'MID', 'FWD', 'BENCH']):
                player_name = team[col]
                
                # Skip empty entries
                if pd.isna(player_name) or player_name == '':
                    continue
                
                # Get player details
                player_data = {
                    'name': player_name,
                    'club': team.get(f'{col}_club', ''),
                    'role': team.get(f'{col}_role', ''),
                    'price': team.get(f'{col}_price', 0),
                    'score': team.get(f'{col}_score', 0),
                    'selected': team.get(f'{col}_selected', 0)
                }
                
                # Categorize player
                if col.startswith('BENCH'):
                    bench.append(player_data)
                elif player_data['selected'] == 1:
                    role = player_data['role']
                    if role in starting_xi:
                        starting_xi[role].append(player_data)
        
        # Add starting XI to row
        # GK (only 1 in starting XI)
        if starting_xi['GK']:
            gk = starting_xi['GK'][0]
            row['GK'] = f"{gk['name']} ({gk['club']})"
            row['GK_price'] = gk['price']
            row['GK_score'] = gk['score']
        
        # DEF (3-5 players)
        for idx, defender in enumerate(starting_xi['DEF'][:5], 1):
            row[f'DEF{idx}'] = f"{defender['name']} ({defender['club']})"
            row[f'DEF{idx}_price'] = defender['price']
            row[f'DEF{idx}_score'] = defender['score']
        
        # MID (2-5 players)
        for idx, midfielder in enumerate(starting_xi['MID'][:5], 1):
            row[f'MID{idx}'] = f"{midfielder['name']} ({midfielder['club']})"
            row[f'MID{idx}_price'] = midfielder['price']
            row[f'MID{idx}_score'] = midfielder['score']
        
        # FWD (1-3 players)
        for idx, forward in enumerate(starting_xi['FWD'][:3], 1):
            row[f'FWD{idx}'] = f"{forward['name']} ({forward['club']})"
            row[f'FWD{idx}_price'] = forward['price']
            row[f'FWD{idx}_score'] = forward['score']
        
        # Bench (4 players: 1 GK + 3 outfield)
        bench_gk = [p for p in bench if p['role'] == 'GK']
        bench_outfield = [p for p in bench if p['role'] != 'GK']
        
        if bench_gk:
            row['BENCH_GK'] = f"{bench_gk[0]['name']} ({bench_gk[0]['club']})"
            row['BENCH_GK_price'] = bench_gk[0]['price']
        
        for idx, player in enumerate(bench_outfield[:3], 1):
            row[f'BENCH{idx}'] = f"{player['name']} ({player['club']})"
            row[f'BENCH{idx}_role'] = player['role']
            row[f'BENCH{idx}_price'] = player['price']
        
        # Add analysis info
        row['confidence'] = team_selection.get('confidence', 0)
        row['risk_assessment'] = team_selection.get('risk_assessment', '')
        row['key_strengths'] = '; '.join(team_selection.get('key_strengths', []))
        row['selection_reason'] = team_selection.get('selection_reason', '')
        
        rows.append(row)
    
    # Create DataFrame with ordered columns
    column_order = [
        'rank', 'captain', 'formation', 'budget', 'gw1_score', '5gw_estimated',
        'GK', 'GK_price', 'GK_score',
        'DEF1', 'DEF1_price', 'DEF1_score',
        'DEF2', 'DEF2_price', 'DEF2_score',
        'DEF3', 'DEF3_price', 'DEF3_score',
        'DEF4', 'DEF4_price', 'DEF4_score',
        'DEF5', 'DEF5_price', 'DEF5_score',
        'MID1', 'MID1_price', 'MID1_score',
        'MID2', 'MID2_price', 'MID2_score',
        'MID3', 'MID3_price', 'MID3_score',
        'MID4', 'MID4_price', 'MID4_score',
        'MID5', 'MID5_price', 'MID5_score',
        'FWD1', 'FWD1_price', 'FWD1_score',
        'FWD2', 'FWD2_price', 'FWD2_score',
        'FWD3', 'FWD3_price', 'FWD3_score',
        'BENCH_GK', 'BENCH_GK_price',
        'BENCH1', 'BENCH1_role', 'BENCH1_price',
        'BENCH2', 'BENCH2_role', 'BENCH2_price',
        'BENCH3', 'BENCH3_role', 'BENCH3_price',
        'confidence', 'risk_assessment', 'key_strengths', 'selection_reason'
    ]
    
    final_df = pd.DataFrame(rows)
    
    # Add missing columns with empty values
    for col in column_order:
        if col not in final_df.columns:
            final_df[col] = ''
    
    # Reorder columns
    final_df = final_df[column_order]
    
    # Save to CSV
    output_file = "../data/cached_merged_2024_2025_v2/final_selected_teams_clean.csv"
    final_df.to_csv(output_file, index=False)
    
    print(f"Saved properly formatted teams to: {output_file}")
    
    # Display summary
    print("\n" + "="*80)
    print("FINAL SELECTED TEAMS - PROPERLY FORMATTED")
    print("="*80)
    
    for idx, row in final_df.iterrows():
        print(f"\n{row['rank']}. {row['captain']} - {row['formation']} (£{row['budget']}m)")
        print(f"   Projected Points: GW1={row['gw1_score']:.1f}, 5GW={row['5gw_estimated']:.1f}")
        print(f"   Risk: {row['risk_assessment']} | Confidence: {row['confidence']}%")
        
        print("\n   Starting XI:")
        print(f"   GK: {row['GK']}")
        
        # Defenders
        defs = []
        for i in range(1, 6):
            if row[f'DEF{i}'] and pd.notna(row[f'DEF{i}']):
                defs.append(str(row[f'DEF{i}']))
        if defs:
            print(f"   DEF ({len(defs)}): {', '.join(defs)}")
        
        # Midfielders
        mids = []
        for i in range(1, 6):
            if row[f'MID{i}']:
                mids.append(row[f'MID{i}'])
        if mids:
            print(f"   MID ({len(mids)}): {', '.join(mids)}")
        
        # Forwards
        fwds = []
        for i in range(1, 4):
            if row[f'FWD{i}']:
                fwds.append(row[f'FWD{i}'])
        if fwds:
            print(f"   FWD ({len(fwds)}): {', '.join(fwds)}")
        
        # Bench
        print(f"\n   Bench:")
        print(f"   GK: {row['BENCH_GK']}")
        bench_players = []
        for i in range(1, 4):
            if row[f'BENCH{i}'] and pd.notna(row[f'BENCH{i}']):
                bench_players.append(f"{row[f'BENCH{i}']} ({row[f'BENCH{i}_role']})")
        if bench_players:
            print(f"   Outfield: {', '.join(bench_players)}")
        
        print(f"\n   Key Strengths: {row['key_strengths']}")
        print(f"   Analysis: {row['selection_reason']}")
        print("-" * 80)


if __name__ == "__main__":
    format_final_teams_correctly()