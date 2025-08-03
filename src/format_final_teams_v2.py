#!/usr/bin/env python3
"""
Format and display the final selected teams in a clean readable format
"""

import pandas as pd
import json


def format_final_teams():
    """Create a properly formatted CSV of the final selected teams"""
    
    # Read the LLM analysis results
    with open("../data/cached_merged_2024_2025_v2/final_selected_teams_llm_v3.json", "r") as f:
        data = json.load(f)
    
    # Read the original teams CSV for complete data
    teams_df = pd.read_csv("../data/cached_merged_2024_2025_v2/top_200_teams_final_v11.csv")
    
    rows = []
    for i, team_selection in enumerate(data['selected_teams']):
        # Get the original team from the CSV
        original_rank = team_selection.get('rank', team_selection.get('captain'))
        
        # Find matching team by captain, formation, budget and scores
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
        
        row = {
            'rank': i + 1,
            'captain': team['captain'],
            'formation': team['formation'],
            'budget': team['budget'],
            'gw1_score': team['gw1_score'],
            '5gw_estimated': team['5gw_estimated']
        }
        
        # Add players in order
        positions = ['GK', 'DEF', 'MID', 'FWD']
        for pos in positions:
            players_in_pos = []
            for j in range(1, 6):  # Max 5 per position
                col = f'{pos}{j}'
                if col in team and pd.notna(team[col]) and team[col] != '':
                    player_name = team[col]
                    club = team.get(f'{col}_club', '')
                    price = team.get(f'{col}_price', 0)
                    score = team.get(f'{col}_score', 0)
                    selected = team.get(f'{col}_selected', 0)
                    
                    if selected == 1:  # Starting XI
                        players_in_pos.append({
                            'name': player_name,
                            'club': club,
                            'price': price,
                            'score': score
                        })
            
            # Add to row - only add the actual players found
            for idx, player in enumerate(players_in_pos):
                row[f'{pos}{idx+1}'] = f"{player['name']} ({player['club']})"
                row[f'{pos}{idx+1}_role'] = pos
                row[f'{pos}{idx+1}_selected'] = 1
                row[f'{pos}{idx+1}_price'] = player['price']
                row[f'{pos}{idx+1}_score'] = player['score']
            
            # Fill empty slots with empty values
            for idx in range(len(players_in_pos), 5):
                row[f'{pos}{idx+1}'] = ''
                row[f'{pos}{idx+1}_role'] = ''
                row[f'{pos}{idx+1}_selected'] = ''
                row[f'{pos}{idx+1}_price'] = ''
                row[f'{pos}{idx+1}_score'] = ''
        
        # Add bench players
        bench_idx = 0
        for j in range(1, 5):  # 4 bench spots
            col = f'BENCH{j}'
            if col in team and pd.notna(team[col]) and team[col] != '':
                row[f'BENCH{j}'] = f"{team[col]} ({team.get(f'{col}_club', '')})"
                row[f'BENCH{j}_role'] = team.get(f'{col}_role', '')
                row[f'BENCH{j}_selected'] = 0
                row[f'BENCH{j}_price'] = team.get(f'{col}_price', 0)
                row[f'BENCH{j}_score'] = team.get(f'{col}_score', 0)
        
        # Add analysis info
        row['confidence'] = team_selection.get('confidence', 0)
        row['risk_assessment'] = team_selection.get('risk_assessment', '')
        row['key_strengths'] = '; '.join(team_selection.get('key_strengths', []))
        row['potential_weaknesses'] = '; '.join(team_selection.get('potential_weaknesses', []))
        row['selection_reason'] = team_selection.get('selection_reason', '')
        
        rows.append(row)
    
    # Create DataFrame
    final_df = pd.DataFrame(rows)
    
    # Save to CSV
    output_file = "../data/cached_merged_2024_2025_v2/final_selected_teams_final_ordered_v4.csv"
    final_df.to_csv(output_file, index=False)
    
    print(f"Saved final teams to: {output_file}")
    
    # Display summary
    print("\n" + "="*80)
    print("FINAL SELECTED TEAMS - UPDATED WITHOUT JOE HODGE")
    print("="*80)
    
    for idx, row in final_df.iterrows():
        print(f"\n{row['rank']}. {row['captain']} - {row['formation']} (£{row['budget']}m)")
        print(f"   Projected Points: GW1={row['gw1_score']:.1f}, 5GW={row['5gw_estimated']:.1f}")
        print(f"   Risk: {row['risk_assessment']} | Confidence: {row['confidence']}%")
        
        print("\n   Starting XI:")
        print(f"   GK: {row.get('GK1', 'N/A')}")
        
        # Defenders
        defs = [str(row.get(f'DEF{i}', '')) for i in range(1, 6) if row.get(f'DEF{i}', '') and pd.notna(row.get(f'DEF{i}'))]
        if defs:
            print(f"   DEF: {', '.join(defs)}")
        
        # Midfielders
        mids = [str(row.get(f'MID{i}', '')) for i in range(1, 6) if row.get(f'MID{i}', '') and pd.notna(row.get(f'MID{i}'))]
        if mids:
            print(f"   MID: {', '.join(mids)}")
        
        # Forwards
        fwds = [str(row.get(f'FWD{i}', '')) for i in range(1, 4) if row.get(f'FWD{i}', '') and pd.notna(row.get(f'FWD{i}'))]
        if fwds:
            print(f"   FWD: {', '.join(fwds)}")
        
        # Bench
        bench = [str(row.get(f'BENCH{i}', '')) for i in range(1, 5) if row.get(f'BENCH{i}', '') and pd.notna(row.get(f'BENCH{i}'))]
        if bench:
            print(f"\n   Bench: {', '.join(bench)}")
        
        print(f"\n   Key Strengths: {row['key_strengths']}")
        print(f"   Analysis: {row['selection_reason']}")
        print("-" * 80)


if __name__ == "__main__":
    format_final_teams()