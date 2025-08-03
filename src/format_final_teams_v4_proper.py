#!/usr/bin/env python3
"""
Create final formatted output with exactly 15 players per team
"""

import pandas as pd
import json


def format_final_teams():
    """Create properly formatted final teams with player counts"""
    
    # Read the LLM analysis results
    with open("../data/cached_merged_2024_2025_v2/final_selected_teams_llm_v4.json", "r") as f:
        data = json.load(f)
    
    # Read the original teams CSV for complete data
    teams_df = pd.read_csv("../data/cached_merged_2024_2025_v2/top_200_teams_final_v15.csv")
    
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
        
        # Add all 15 players
        # Starting XI
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for j in range(1, 6):  # Up to 5 for each position
                col = f'{pos}{j}'
                if col in team and pd.notna(team[col]) and team[col]:
                    row[col] = f"{team[col]} ({team.get(f'{col}_club', '')})"
                    row[f'{col}_price'] = team.get(f'{col}_price', 0)
                    row[f'{col}_score'] = team.get(f'{col}_score', 0)
                else:
                    row[col] = ''
                    row[f'{col}_price'] = ''
                    row[f'{col}_score'] = ''
        
        # Bench
        for j in range(1, 5):
            bench_col = f'BENCH{j}'
            if bench_col in team and pd.notna(team[bench_col]) and team[bench_col]:
                row[bench_col] = f"{team[bench_col]} ({team.get(f'{bench_col}_club', '')})"
                row[f'{bench_col}_role'] = team.get(f'{bench_col}_role', '')
                row[f'{bench_col}_price'] = team.get(f'{bench_col}_price', 0)
            else:
                row[bench_col] = ''
                row[f'{bench_col}_role'] = ''
                row[f'{bench_col}_price'] = ''
        
        # Add analysis info
        row['confidence'] = team_selection.get('confidence', 0)
        row['risk_assessment'] = team_selection.get('risk_assessment', '')
        row['key_strengths'] = '; '.join(team_selection.get('key_strengths', []))
        row['selection_reason'] = team_selection.get('selection_reason', '')
        
        # Add player counts for verification
        row['total_players'] = team.get('total_gk', 0) + team.get('total_def', 0) + \
                              team.get('total_mid', 0) + team.get('total_fwd', 0)
        row['total_gk'] = team.get('total_gk', 0)
        row['total_def'] = team.get('total_def', 0)
        row['total_mid'] = team.get('total_mid', 0)
        row['total_fwd'] = team.get('total_fwd', 0)
        
        rows.append(row)
    
    # Create DataFrame
    final_df = pd.DataFrame(rows)
    
    # Save to CSV
    output_file = "../data/cached_merged_2024_2025_v2/final_selected_teams_proper_15.csv"
    final_df.to_csv(output_file, index=False)
    
    print(f"Saved properly formatted teams to: {output_file}")
    
    # Display summary
    print("\n" + "="*80)
    print("FINAL SELECTED TEAMS - EXACTLY 15 PLAYERS")
    print("="*80)
    
    for idx, row in final_df.iterrows():
        print(f"\n{row['rank']}. {row['captain']} - {row['formation']} (£{row['budget']}m)")
        print(f"   Projected Points: GW1={row['gw1_score']:.1f}, 5GW={row['5gw_estimated']:.1f}")
        print(f"   Risk: {row['risk_assessment']} | Confidence: {row['confidence']}%")
        print(f"   Total Players: {row['total_players']} (GK:{row['total_gk']}, DEF:{row['total_def']}, MID:{row['total_mid']}, FWD:{row['total_fwd']})")
        
        # Parse formation
        formation_parts = row['formation'].split('-')
        xi_def = int(formation_parts[0])
        xi_mid = int(formation_parts[1])
        xi_fwd = int(formation_parts[2])
        
        print("\n   Starting XI:")
        # GK
        if row['GK1']:
            print(f"   GK: {row['GK1']}")
        
        # Defenders
        defs = []
        for i in range(1, xi_def + 1):
            if row.get(f'DEF{i}', '') and pd.notna(row[f'DEF{i}']):
                defs.append(str(row[f'DEF{i}']))
        if defs:
            print(f"   DEF ({len(defs)}): {', '.join(defs)}")
        
        # Midfielders
        mids = []
        for i in range(1, xi_mid + 1):
            if row.get(f'MID{i}', '') and pd.notna(row[f'MID{i}']):
                mids.append(str(row[f'MID{i}']))
        if mids:
            print(f"   MID ({len(mids)}): {', '.join(mids)}")
        
        # Forwards
        fwds = []
        for i in range(1, xi_fwd + 1):
            if row.get(f'FWD{i}', '') and pd.notna(row[f'FWD{i}']):
                fwds.append(str(row[f'FWD{i}']))
        if fwds:
            print(f"   FWD ({len(fwds)}): {', '.join(fwds)}")
        
        # Bench
        print(f"\n   Bench (4 players):")
        bench_players = []
        for i in range(1, 5):
            if row.get(f'BENCH{i}', '') and pd.notna(row[f'BENCH{i}']):
                bench_players.append(f"{row[f'BENCH{i}']} ({row.get(f'BENCH{i}_role', '')})")
        
        # Group bench by position
        bench_gks = [p for p in bench_players if '(GK)' in p]
        bench_defs = [p for p in bench_players if '(DEF)' in p]
        bench_mids = [p for p in bench_players if '(MID)' in p]
        bench_fwds = [p for p in bench_players if '(FWD)' in p]
        
        if bench_gks:
            print(f"   GK: {', '.join(bench_gks)}")
        if bench_defs:
            print(f"   DEF: {', '.join(bench_defs)}")
        if bench_mids:
            print(f"   MID: {', '.join(bench_mids)}")
        if bench_fwds:
            print(f"   FWD: {', '.join(bench_fwds)}")
        
        print(f"\n   Key Strengths: {row['key_strengths']}")
        print(f"   Analysis: {row['selection_reason']}")
        print("-" * 80)


if __name__ == "__main__":
    format_final_teams()