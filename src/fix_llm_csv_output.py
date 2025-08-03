#!/usr/bin/env python3
"""
Fix the LLM CSV output to include player names properly
"""

import pandas as pd
import json
from pathlib import Path

def fix_csv_output():
    """Convert JSON to properly formatted CSV with player names"""
    
    # Load JSON data
    json_path = Path("../data/cached_merged_2024_2025_v3/final_selected_teams_llm_v3.json")
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Process each team
    rows = []
    for i, team in enumerate(data['selected_teams'], 1):
        row = {
            'rank': i,
            'captain': team['captain'],
            'formation': team['formation'],
            'budget': team['budget'],
            'gw1_score': team['gw1_score'],
            '5gw_estimated': team['5gw_estimated'],
            'confidence': team['confidence'],
            'risk_assessment': team['risk_assessment'],
            'validation_passed': team['validation_passed'],
            'selection_reason': team['selection_reason']
        }
        
        # Add players with proper formatting
        # Track which positions are filled
        gk_players = []
        def_players = []
        mid_players = []
        fwd_players = []
        
        # Collect all players first (including from bench)
        for key in team:
            if key.startswith('GK') and not any(suffix in key for suffix in ['_role', '_selected', '_price', '_score', '_club']):
                if pd.notna(team[key]) and team[key] != 'nan':
                    gk_players.append((key, team[key], team.get(f'{key}_club', ''), 
                                     team.get(f'{key}_price', 0), team.get(f'{key}_score', 0)))
            elif key.startswith('DEF') and not any(suffix in key for suffix in ['_role', '_selected', '_price', '_score', '_club']):
                if pd.notna(team[key]) and team[key] != 'nan':
                    def_players.append((key, team[key], team.get(f'{key}_club', ''), 
                                      team.get(f'{key}_price', 0), team.get(f'{key}_score', 0)))
            elif key.startswith('MID') and not any(suffix in key for suffix in ['_role', '_selected', '_price', '_score', '_club']):
                if pd.notna(team[key]) and team[key] != 'nan':
                    mid_players.append((key, team[key], team.get(f'{key}_club', ''), 
                                      team.get(f'{key}_price', 0), team.get(f'{key}_score', 0)))
            elif key.startswith('FWD') and not any(suffix in key for suffix in ['_role', '_selected', '_price', '_score', '_club']):
                if pd.notna(team[key]) and team[key] != 'nan':
                    fwd_players.append((key, team[key], team.get(f'{key}_club', ''), 
                                      team.get(f'{key}_price', 0), team.get(f'{key}_score', 0)))
            elif key.startswith('BENCH') and not any(suffix in key for suffix in ['_role', '_selected', '_price', '_score', '_club']):
                if pd.notna(team[key]) and team[key] != 'nan':
                    # Determine position from bench player
                    role = team.get(f'{key}_role', '')
                    if role == 'GK':
                        gk_players.append((key, team[key], team.get(f'{key}_club', ''), 
                                         team.get(f'{key}_price', 0), team.get(f'{key}_score', 0)))
                    elif role == 'DEF':
                        def_players.append((key, team[key], team.get(f'{key}_club', ''), 
                                          team.get(f'{key}_price', 0), team.get(f'{key}_score', 0)))
                    elif role == 'MID':
                        mid_players.append((key, team[key], team.get(f'{key}_club', ''), 
                                          team.get(f'{key}_price', 0), team.get(f'{key}_score', 0)))
                    elif role == 'FWD':
                        fwd_players.append((key, team[key], team.get(f'{key}_club', ''), 
                                          team.get(f'{key}_price', 0), team.get(f'{key}_score', 0)))
        
        # Now add players to row in order
        # Goalkeepers (should be 2)
        for j, (key, name, club, price, score) in enumerate(gk_players[:2], 1):
            row[f'GK{j}'] = f"{name} ({club})"
            row[f'GK{j}_price'] = price
            row[f'GK{j}_score'] = score
        
        # Defenders (should be 5)
        for j, (key, name, club, price, score) in enumerate(def_players[:5], 1):
            row[f'DEF{j}'] = f"{name} ({club})"
            row[f'DEF{j}_price'] = price
            row[f'DEF{j}_score'] = score
        
        # Midfielders (should be 5)
        for j, (key, name, club, price, score) in enumerate(mid_players[:5], 1):
            row[f'MID{j}'] = f"{name} ({club})"
            row[f'MID{j}_price'] = price
            row[f'MID{j}_score'] = score
        
        # Forwards (should be 3)
        for j, (key, name, club, price, score) in enumerate(fwd_players[:3], 1):
            row[f'FWD{j}'] = f"{name} ({club})"
            row[f'FWD{j}_price'] = price
            row[f'FWD{j}_score'] = score
        
        # Count players
        total_gk = len(gk_players)
        total_def = len(def_players)
        total_mid = len(mid_players)
        total_fwd = len(fwd_players)
        
        row['total_players'] = total_gk + total_def + total_mid + total_fwd
        row['total_gk'] = total_gk
        row['total_def'] = total_def
        row['total_mid'] = total_mid
        row['total_fwd'] = total_fwd
        
        rows.append(row)
    
    # Create DataFrame and save
    df = pd.DataFrame(rows)
    
    # Reorder columns for better readability
    base_cols = ['rank', 'captain', 'formation', 'budget', 'gw1_score', '5gw_estimated', 
                 'confidence', 'risk_assessment', 'validation_passed', 'selection_reason']
    
    player_cols = []
    for pos in ['GK', 'DEF', 'MID', 'FWD']:
        num_players = 2 if pos == 'GK' else 5 if pos in ['DEF', 'MID'] else 3
        for i in range(1, num_players + 1):
            player_col = f'{pos}{i}'
            if player_col in df.columns:
                player_cols.extend([player_col, f'{player_col}_price', f'{player_col}_score'])
    
    count_cols = ['total_players', 'total_gk', 'total_def', 'total_mid', 'total_fwd']
    
    # Combine all columns
    all_cols = base_cols + player_cols + count_cols
    df = df[[col for col in all_cols if col in df.columns]]
    
    # Save fixed CSV
    output_path = Path("../data/cached_merged_2024_2025_v3/final_selected_teams_proper.csv")
    df.to_csv(output_path, index=False)
    print(f"Fixed CSV saved to: {output_path}")
    
    # Display summary
    print("\nTop 3 Teams Summary:")
    for idx, row in df.head(3).iterrows():
        print(f"\nTeam {idx+1}:")
        print(f"  Captain: {row['captain']}")
        print(f"  Formation: {row['formation']}")
        print(f"  Budget: £{row['budget']}m")
        print(f"  5GW Score: {row['5gw_estimated']}")
        print(f"  Confidence: {row['confidence']}%")
        print(f"  Player Count: {row['total_players']} (GK:{row['total_gk']}, DEF:{row['total_def']}, MID:{row['total_mid']}, FWD:{row['total_fwd']})")

if __name__ == "__main__":
    fix_csv_output()