#!/usr/bin/env python3
"""
Generate final teams in proper FPL format with 15 players (2 GK, 5 DEF, 5 MID, 3 FWD)
"""

import pandas as pd
import json
from pathlib import Path

def create_final_teams():
    """Create final teams CSV with proper format"""
    
    # Load the LLM-selected teams
    with open('../data/cached_merged_2024_2025_v2/final_selected_teams_llm_v2.json', 'r') as f:
        selected_teams = json.load(f)
    
    # Create new rows with proper formatting
    final_teams = []
    
    for i, team in enumerate(selected_teams['selected_teams'], 1):
        team_data = team
        
        # Extract players by position
        gks = []
        defs = []
        mids = []
        fwds = []
        bench = []
        
        # Process starting XI
        for j in range(1, 12):
            for pos in ['GK', 'DEF', 'MID', 'FWD']:
                if f'{pos}{j}' in team_data:
                    player_name = team_data[f'{pos}{j}']
                    player_price = team_data.get(f'{pos}{j}_price', 0)
                    player_score = team_data.get(f'{pos}{j}_score', 0)
                    player_club = team_data.get(f'{pos}{j}_club', '')
                    
                    if player_name:
                        player_info = f"{player_name} ({player_club})"
                        if pos == 'GK':
                            gks.append((player_info, player_price, player_score))
                        elif pos == 'DEF':
                            defs.append((player_info, player_price, player_score))
                        elif pos == 'MID':
                            mids.append((player_info, player_price, player_score))
                        elif pos == 'FWD':
                            fwds.append((player_info, player_price, player_score))
        
        # Process bench
        for j in range(1, 5):
            if f'BENCH{j}' in team_data:
                player_name = team_data[f'BENCH{j}']
                player_role = team_data.get(f'BENCH{j}_role', '')
                player_price = team_data.get(f'BENCH{j}_price', 0)
                player_club = team_data.get(f'BENCH{j}_club', '')
                
                if player_name:
                    bench.append({
                        'name': f"{player_name} ({player_club})",
                        'role': player_role,
                        'price': player_price
                    })
        
        # Ensure we have exactly 15 players
        total_gk = len(gks)
        total_def = len(defs)
        total_mid = len(mids)
        total_fwd = len(fwds)
        
        # Add bench players to complete positions if needed
        for b in bench:
            if b['role'] == 'GK' and total_gk < 2:
                gks.append((b['name'], b['price'], 0))
                total_gk += 1
            elif b['role'] == 'DEF' and total_def < 5:
                defs.append((b['name'], b['price'], 0))
                total_def += 1
            elif b['role'] == 'MID' and total_mid < 5:
                mids.append((b['name'], b['price'], 0))
                total_mid += 1
            elif b['role'] == 'FWD' and total_fwd < 3:
                fwds.append((b['name'], b['price'], 0))
                total_fwd += 1
        
        # Create row data
        row = {
            'rank': i,
            'captain': team_data.get('captain', ''),
            'formation': team_data.get('formation', ''),
            'budget': team_data.get('budget', 0),
            'gw1_score': team_data.get('gw1_score', 0),
            '5gw_estimated': team_data.get('5gw_estimated', 0)
        }
        
        # Add GKs (ensure exactly 2)
        for j, (name, price, score) in enumerate(gks[:2], 1):
            row[f'GK{j}'] = name
            row[f'GK{j}_price'] = price
            row[f'GK{j}_score'] = score
        
        # Add DEFs (ensure exactly 5)
        for j, (name, price, score) in enumerate(defs[:5], 1):
            row[f'DEF{j}'] = name
            row[f'DEF{j}_price'] = price
            row[f'DEF{j}_score'] = score
        
        # Add MIDs (ensure exactly 5)
        for j, (name, price, score) in enumerate(mids[:5], 1):
            row[f'MID{j}'] = name
            row[f'MID{j}_price'] = price
            row[f'MID{j}_score'] = score
        
        # Add FWDs (ensure exactly 3)
        for j, (name, price, score) in enumerate(fwds[:3], 1):
            row[f'FWD{j}'] = name
            row[f'FWD{j}_price'] = price
            row[f'FWD{j}_score'] = score
        
        # Add bench info
        for j, b in enumerate(bench[:4], 1):
            row[f'BENCH{j}'] = b['name']
            row[f'BENCH{j}_role'] = b['role']
            row[f'BENCH{j}_price'] = b['price']
        
        # Add analysis data
        row['confidence'] = team.get('confidence', 0)
        row['risk_assessment'] = team.get('risk_assessment', '')
        row['key_strengths'] = team.get('key_strengths', '')
        row['selection_reason'] = team.get('selection_reason', '')
        
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
    output_path = Path('../data/cached_merged_2024_2025_v2/final_selected_teams_proper_15_v2.csv')
    df.to_csv(output_path, index=False)
    print(f"Saved final teams to {output_path}")
    
    # Display summary
    print("\nFinal Teams Summary:")
    print("=" * 80)
    for i, row in df.iterrows():
        print(f"\nTeam {row['rank']}:")
        print(f"  Captain: {row['captain']}")
        print(f"  Formation: {row['formation']}")
        print(f"  Budget: £{row['budget']}m")
        print(f"  5GW Score: {row['5gw_estimated']}")
        print(f"  Risk: {row['risk_assessment']}")
        print(f"  Confidence: {row['confidence']}%")
        print(f"  Total Players: {row['total_players']} (GK:{row['total_gk']}, DEF:{row['total_def']}, MID:{row['total_mid']}, FWD:{row['total_fwd']})")

if __name__ == "__main__":
    create_final_teams()