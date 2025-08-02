#!/usr/bin/env python3
"""
Simple approach to create top teams for gameweek 39
"""

import pandas as pd
from pathlib import Path


def create_top_teams_simple(pred_file, output_file):
    """Create top teams using simple greedy approach"""
    
    # Load predictions
    df = pd.read_csv(pred_file)
    
    # Get unique players with their best stats
    players = df.groupby(['first_name', 'last_name', 'club', 'role']).agg({
        'average_score': 'mean',
        'price': 'first'
    }).reset_index()
    
    players['full_name'] = players['first_name'] + ' ' + players['last_name']
    
    # Sort by score within each role
    players['score_per_price'] = players['average_score'] / players['price']
    
    # Get top players by role - need more players for 50 variations
    top_gk = players[players['role'] == 'GK'].nlargest(20, 'average_score')
    top_def = players[players['role'] == 'DEF'].nlargest(50, 'average_score')
    top_mid = players[players['role'] == 'MID'].nlargest(50, 'average_score')
    top_fwd = players[players['role'] == 'FWD'].nlargest(30, 'average_score')
    
    # Convert to lists for easier indexing
    gk_list = top_gk.to_dict('records')
    def_list = top_def.to_dict('records')
    mid_list = top_mid.to_dict('records')
    fwd_list = top_fwd.to_dict('records')
    
    # Create 50 different teams with variations
    teams = []
    
    for i in range(50):
        # Use different selection strategies for variety
        if i < 10:
            # Top scorers
            gk_offset = i % 10
            def_offset = i % 20
            mid_offset = i % 20
            fwd_offset = i % 10
        elif i < 25:
            # Mix of top and value
            gk_offset = (i - 10) % 15
            def_offset = (i - 10) % 30
            mid_offset = (i - 10) % 30
            fwd_offset = (i - 10) % 15
        else:
            # More varied selections
            gk_offset = (i - 25) % len(gk_list) - 2
            def_offset = (i - 25) % (len(def_list) - 5)
            mid_offset = (i - 25) % (len(mid_list) - 5)
            fwd_offset = (i - 25) % (len(fwd_list) - 3)
        
        # Ensure we have valid indices
        gk_offset = max(0, min(gk_offset, len(gk_list) - 2))
        def_offset = max(0, min(def_offset, len(def_list) - 5))
        mid_offset = max(0, min(mid_offset, len(mid_list) - 5))
        fwd_offset = max(0, min(fwd_offset, len(fwd_list) - 3))
        
        # Select players
        gks = gk_list[gk_offset:gk_offset + 2]
        defs = def_list[def_offset:def_offset + 5]
        mids = mid_list[mid_offset:mid_offset + 5]
        fwds = fwd_list[fwd_offset:fwd_offset + 3]
        
        # Build team dictionary
        team = {}
        total_price = 0
        
        # Add GKs
        for j, gk in enumerate(gks, 1):
            team[f'GK{j}'] = f"{gk['full_name']} ({gk['club']})"
            team[f'GK{j}_selected'] = 1 if j == 1 else 0
            team[f'GK{j}_price'] = gk['price']
            team[f'GK{j}_score'] = gk['average_score']
            total_price += gk['price']
            
        # Add DEFs (select top 3-4 for starting 11)
        for j, df in enumerate(defs, 1):
            team[f'DEF{j}'] = f"{df['full_name']} ({df['club']})"
            team[f'DEF{j}_selected'] = 1 if j <= 4 else 0
            team[f'DEF{j}_price'] = df['price']
            team[f'DEF{j}_score'] = df['average_score']
            total_price += df['price']
            
        # Add MIDs (select top 3-4 for starting 11)
        for j, mid in enumerate(mids, 1):
            team[f'MID{j}'] = f"{mid['full_name']} ({mid['club']})"
            team[f'MID{j}_selected'] = 1 if j <= 3 else 0
            team[f'MID{j}_price'] = mid['price']
            team[f'MID{j}_score'] = mid['average_score']
            total_price += mid['price']
            
        # Add FWDs (select top 2 for starting 11)
        for j, fwd in enumerate(fwds, 1):
            team[f'FWD{j}'] = f"{fwd['full_name']} ({fwd['club']})"
            team[f'FWD{j}_selected'] = 1 if j <= 2 else 0
            team[f'FWD{j}_price'] = fwd['price']
            team[f'FWD{j}_score'] = fwd['average_score']
            total_price += fwd['price']
            
        # Calculate total score for selected 11
        total_score = 0
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for j in range(1, 6):
                if f'{pos}{j}_selected' in team and team[f'{pos}{j}_selected'] == 1:
                    total_score += team.get(f'{pos}{j}_score', 0)
                    
        team['11_selected_total_scores'] = round(total_score, 2)
        team['15_total_price'] = round(total_price, 1)
        
        # Only add teams that are within budget
        if total_price <= 100.0:
            teams.append(team)
    
    # If we don't have enough valid teams, create more with budget-conscious selections
    attempts = 0
    while len(teams) < 50 and attempts < 100:
        attempts += 1
        
        # Use more budget-friendly selections
        gk_offset = (50 + attempts) % len(gk_list) - 2
        def_offset = (50 + attempts * 2) % (len(def_list) - 5)
        mid_offset = (50 + attempts * 3) % (len(mid_list) - 5)
        fwd_offset = (50 + attempts * 2) % (len(fwd_list) - 3)
        
        # Ensure valid indices
        gk_offset = max(0, min(gk_offset, len(gk_list) - 2))
        def_offset = max(0, min(def_offset, len(def_list) - 5))
        mid_offset = max(0, min(mid_offset, len(mid_list) - 5))
        fwd_offset = max(0, min(fwd_offset, len(fwd_list) - 3))
        
        # Select cheaper players by going further down the list
        gks = gk_list[gk_offset:gk_offset + 2]
        defs = def_list[def_offset:def_offset + 5]
        mids = mid_list[mid_offset:mid_offset + 5]
        fwds = fwd_list[fwd_offset:fwd_offset + 3]
        
        # Build team
        team = {}
        total_price = 0
        
        # Add players (same as before)
        for j, gk in enumerate(gks, 1):
            team[f'GK{j}'] = f"{gk['full_name']} ({gk['club']})"
            team[f'GK{j}_selected'] = 1 if j == 1 else 0
            team[f'GK{j}_price'] = gk['price']
            team[f'GK{j}_score'] = gk['average_score']
            total_price += gk['price']
            
        for j, df in enumerate(defs, 1):
            team[f'DEF{j}'] = f"{df['full_name']} ({df['club']})"
            team[f'DEF{j}_selected'] = 1 if j <= 4 else 0
            team[f'DEF{j}_price'] = df['price']
            team[f'DEF{j}_score'] = df['average_score']
            total_price += df['price']
            
        for j, mid in enumerate(mids, 1):
            team[f'MID{j}'] = f"{mid['full_name']} ({mid['club']})"
            team[f'MID{j}_selected'] = 1 if j <= 3 else 0
            team[f'MID{j}_price'] = mid['price']
            team[f'MID{j}_score'] = mid['average_score']
            total_price += mid['price']
            
        for j, fwd in enumerate(fwds, 1):
            team[f'FWD{j}'] = f"{fwd['full_name']} ({fwd['club']})"
            team[f'FWD{j}_selected'] = 1 if j <= 2 else 0
            team[f'FWD{j}_price'] = fwd['price']
            team[f'FWD{j}_score'] = fwd['average_score']
            total_price += fwd['price']
        
        # Calculate score
        total_score = 0
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for j in range(1, 6):
                if f'{pos}{j}_selected' in team and team[f'{pos}{j}_selected'] == 1:
                    total_score += team.get(f'{pos}{j}_score', 0)
                    
        team['11_selected_total_scores'] = round(total_score, 2)
        team['15_total_price'] = round(total_price, 1)
        
        # Only add if within budget and not duplicate
        if total_price <= 100.0:
            teams.append(team)
    
    # Create dataframe
    teams_df = pd.DataFrame(teams)
    
    # Remove any duplicates based on the lineup
    if len(teams_df) > 0:
        # Create a signature for each team based on players
        team_signatures = []
        for idx, row in teams_df.iterrows():
            players = []
            for pos in ['GK', 'DEF', 'MID', 'FWD']:
                for i in range(1, 6):
                    if f'{pos}{i}' in row:
                        players.append(row[f'{pos}{i}'])
            team_signatures.append('|'.join(sorted(players)))
        
        teams_df['signature'] = team_signatures
        teams_df = teams_df.drop_duplicates(subset=['signature']).drop(columns=['signature'])
    
    # Sort by score
    teams_df = teams_df.sort_values('11_selected_total_scores', ascending=False)
    
    # Keep only top 50
    teams_df = teams_df.head(50)
    
    teams_df.to_csv(output_file, index=False)
    print(f"Created {len(teams_df)} teams")
    
    # Show top team
    if len(teams_df) > 0:
        print("\nTop team:")
        for col in ['GK1', 'DEF1', 'MID1', 'FWD1']:
            if col in teams_df.columns:
                print(f"  {col}: {teams_df.iloc[0][col]} - £{teams_df.iloc[0][f'{col}_price']:.1f}m")
        print(f"\nTotal: £{teams_df.iloc[0]['15_total_price']:.1f}m, Score: {teams_df.iloc[0]['11_selected_total_scores']}")


def main():
    import sys
    if len(sys.argv) != 3:
        pred_file = "data/cached_merged_2024_2025_v2/predictions_gw39.csv"
        output_file = "data/cached_merged_2024_2025_v2/top_50_teams_gw39.csv"
    else:
        pred_file = sys.argv[1]
        output_file = sys.argv[2]
        
    create_top_teams_simple(pred_file, output_file)


if __name__ == "__main__":
    main()