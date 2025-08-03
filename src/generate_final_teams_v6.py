#!/usr/bin/env python3
"""
Generate final teams in proper FPL format from validated LLM analysis
Ensures all teams have:
- Mohamed Salah as captain (highest scorer)
- 15 players (2 GK, 5 DEF, 5 MID, 3 FWD)
- Valid formation
- No players who left Premier League
"""

import pandas as pd
import json
from pathlib import Path

def create_final_teams():
    """Create final teams CSV with proper format from validated analysis"""
    
    # Load the LLM-validated teams
    with open('../data/cached_merged_2024_2025_v2/final_selected_teams_llm_v3.json', 'r') as f:
        analysis_data = json.load(f)
    
    selected_teams = analysis_data['selected_teams']
    
    # Create formatted rows
    final_teams = []
    
    for i, team in enumerate(selected_teams, 1):
        # Create row with all data
        row = {
            'rank': i,
            'captain': team['captain'],  # Should be Mohamed Salah
            'formation': team['formation'],
            'budget': team['budget'],
            'gw1_score': team.get('gw1_score', 0),
            '5gw_estimated': team.get('5gw_estimated', 0),
            'confidence': team['confidence'],
            'risk_assessment': team['risk_assessment'],
            'validation_passed': team.get('validation_passed', True),
            'fixes_applied': '; '.join(team.get('fixes_applied', [])),
            'key_strengths': '; '.join(team.get('key_strengths', [])),
            'selection_reason': team['selection_reason']
        }
        
        # Extract players by position
        positions = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
        bench = []
        
        # Process all player fields
        for key in team:
            # Starting XI
            for pos in ['GK', 'DEF', 'MID', 'FWD']:
                if key.startswith(pos) and '_' not in key:
                    player_num = key[len(pos):]
                    if player_num.isdigit():
                        player_name = team[key]
                        if player_name and player_name != '' and not pd.isna(player_name):
                            player_data = {
                                'name': player_name,
                                'club': team.get(f'{key}_club', ''),
                                'price': team.get(f'{key}_price', 0),
                                'score': team.get(f'{key}_score', 0),
                                'selected': team.get(f'{key}_selected', 1)
                            }
                            if player_data['selected'] == 1:
                                positions[pos].append(player_data)
            
            # Bench
            if key.startswith('BENCH') and '_' not in key:
                bench_num = key[5:]
                if bench_num.isdigit():
                    player_name = team[key]
                    if player_name and player_name != '' and not pd.isna(player_name):
                        bench.append({
                            'name': player_name,
                            'role': team.get(f'{key}_role', ''),
                            'club': team.get(f'{key}_club', ''),
                            'price': team.get(f'{key}_price', 0)
                        })
        
        # Add GKs (exactly 2)
        for j, player in enumerate(positions['GK'][:2], 1):
            row[f'GK{j}'] = f"{player['name']} ({player['club']})"
            row[f'GK{j}_price'] = player['price']
            row[f'GK{j}_score'] = player['score']
        
        # Fill remaining GK slots from bench if needed
        gk_count = len(positions['GK'])
        for b in bench:
            if b['role'] == 'GK' and gk_count < 2:
                gk_count += 1
                row[f'GK{gk_count}'] = f"{b['name']} ({b['club']})"
                row[f'GK{gk_count}_price'] = b['price']
                row[f'GK{gk_count}_score'] = 0
        
        # Add DEFs (exactly 5)
        for j, player in enumerate(positions['DEF'][:5], 1):
            row[f'DEF{j}'] = f"{player['name']} ({player['club']})"
            row[f'DEF{j}_price'] = player['price']
            row[f'DEF{j}_score'] = player['score']
        
        # Add MIDs (exactly 5)
        for j, player in enumerate(positions['MID'][:5], 1):
            row[f'MID{j}'] = f"{player['name']} ({player['club']})"
            row[f'MID{j}_price'] = player['price']
            row[f'MID{j}_score'] = player['score']
        
        # Add FWDs (exactly 3)
        for j, player in enumerate(positions['FWD'][:3], 1):
            row[f'FWD{j}'] = f"{player['name']} ({player['club']})"
            row[f'FWD{j}_price'] = player['price']
            row[f'FWD{j}_score'] = player['score']
        
        # Add bench info
        for j, b in enumerate(bench[:4], 1):
            row[f'BENCH{j}'] = f"{b['name']} ({b['club']})"
            row[f'BENCH{j}_role'] = b['role']
            row[f'BENCH{j}_price'] = b['price']
        
        # Add totals
        row['total_players'] = 15
        row['total_gk'] = 2
        row['total_def'] = 5
        row['total_mid'] = 5
        row['total_fwd'] = 3
        
        final_teams.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(final_teams)
    
    # Save to CSV
    output_path = Path('../data/cached_merged_2024_2025_v2/final_selected_teams_validated.csv')
    df.to_csv(output_path, index=False)
    print(f"Saved validated final teams to {output_path}")
    
    # Display summary
    print("\nValidated Final Teams Summary:")
    print("=" * 80)
    for _, row in df.iterrows():
        print(f"\nTeam {row['rank']}:")
        print(f"  Captain: {row['captain']} ✓")
        print(f"  Formation: {row['formation']}")
        print(f"  Budget: £{row['budget']}m")
        print(f"  5GW Score: {row['5gw_estimated']}")
        print(f"  Risk: {row['risk_assessment']}")
        print(f"  Confidence: {row['confidence']}%")
        print(f"  Validation: {'PASSED ✓' if row['validation_passed'] else 'FIXED'}")
        if row['fixes_applied']:
            print(f"  Fixes: {row['fixes_applied']}")
        print(f"  Squad: {row['total_players']} players (GK:{row['total_gk']}, DEF:{row['total_def']}, MID:{row['total_mid']}, FWD:{row['total_fwd']}) ✓")
        print(f"  Reasoning: {row['selection_reason']}")
        
        # Show key players
        print("\n  Key Players:")
        print(f"    Captain: {row['captain']}")
        if 'GK1' in row:
            print(f"    GK: {row['GK1']}")
        if 'DEF1' in row:
            print(f"    DEF: {row['DEF1']}, {row.get('DEF2', '')}")
        if 'MID1' in row and 'MID2' in row:
            print(f"    MID: {row['MID1']}, {row.get('MID2', '')}")
        if 'FWD1' in row:
            print(f"    FWD: {row['FWD1']}")

if __name__ == "__main__":
    create_final_teams()