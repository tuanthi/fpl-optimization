#!/usr/bin/env python3
"""
Optimized approach to create top teams for gameweek 39
- Uses weighted score: 1/3 * (player_score + 0.5 * team_score + role_score)
- Optimizes for 11 players with cheap bench
- Generates top 200 teams
"""

import pandas as pd
from pathlib import Path


def create_optimized_teams(pred_file, output_file, team_weight=0.5, num_teams=200):
    """Create top teams using optimized approach"""
    
    # Load predictions
    df = pd.read_csv(pred_file)
    
    # Weighted score already calculated: 1/3 * (player_score + 0.5 * team_score + role_score)
    
    # Get unique players with their best stats
    players = df.groupby(['first_name', 'last_name', 'club', 'role']).agg({
        'player_score': 'mean',
        'team_score': 'mean',
        'weighted_score': 'mean',
        'price': 'first'
    }).reset_index()
    
    players['full_name'] = players['first_name'] + ' ' + players['last_name']
    
    # Sort by weighted score within each role
    players['score_per_price'] = players['weighted_score'] / players['price']
    
    # For starting 11: Get top scorers
    # For bench: Get cheapest players
    top_gk = players[players['role'] == 'GK'].nlargest(15, 'weighted_score')
    cheap_gk = players[players['role'] == 'GK'].nsmallest(10, 'price')
    
    top_def = players[players['role'] == 'DEF'].nlargest(40, 'weighted_score')
    cheap_def = players[players['role'] == 'DEF'].nsmallest(20, 'price')
    
    top_mid = players[players['role'] == 'MID'].nlargest(40, 'weighted_score')
    cheap_mid = players[players['role'] == 'MID'].nsmallest(20, 'price')
    
    top_fwd = players[players['role'] == 'FWD'].nlargest(25, 'weighted_score')
    cheap_fwd = players[players['role'] == 'FWD'].nsmallest(15, 'price')
    
    # Create teams with different strategies
    teams = []
    team_signatures = set()
    
    # Strategy 1: Top scorers with cheap bench (50% of teams)
    for i in range(num_teams // 2):
        # Vary starting XI selection
        gk_offset = i % 10
        def_offset = (i * 2) % 25
        mid_offset = (i * 3) % 25
        fwd_offset = (i * 2) % 15
        
        # Starting XI: 1 GK, 4 DEF, 3-4 MID, 2-3 FWD
        formations = [
            (1, 4, 4, 2),  # 4-4-2
            (1, 4, 3, 3),  # 4-3-3
            (1, 5, 3, 2),  # 5-3-2
            (1, 3, 5, 2),  # 3-5-2
            (1, 3, 4, 3),  # 3-4-3
        ]
        formation = formations[i % len(formations)]
        
        # Select starting XI from top scorers
        starting_gk = top_gk.iloc[gk_offset:gk_offset + formation[0]].to_dict('records')
        starting_def = top_def.iloc[def_offset:def_offset + formation[1]].to_dict('records')
        starting_mid = top_mid.iloc[mid_offset:mid_offset + formation[2]].to_dict('records')
        starting_fwd = top_fwd.iloc[fwd_offset:fwd_offset + formation[3]].to_dict('records')
        
        # Select bench from cheap players
        bench_gk = cheap_gk.iloc[i % 5:i % 5 + 1].to_dict('records')
        bench_def = cheap_def.iloc[(i * 2) % 10:(i * 2) % 10 + (5 - formation[1])].to_dict('records')
        bench_mid = cheap_mid.iloc[(i * 3) % 10:(i * 3) % 10 + (5 - formation[2])].to_dict('records')
        bench_fwd = cheap_fwd.iloc[(i * 2) % 8:(i * 2) % 8 + (3 - formation[3])].to_dict('records')
        
        # Combine all players
        all_gk = starting_gk + bench_gk
        all_def = starting_def + bench_def
        all_mid = starting_mid + bench_mid
        all_fwd = starting_fwd + bench_fwd
        
        # Check team constraints (max 3 from same team)
        team_counts = {}
        valid_team = True
        
        for player_list in [all_gk, all_def, all_mid, all_fwd]:
            for player in player_list:
                team = player['club']
                team_counts[team] = team_counts.get(team, 0) + 1
                if team_counts[team] > 3:
                    valid_team = False
                    break
            if not valid_team:
                break
        
        if not valid_team:
            continue
        
        # Build team dictionary
        team = {}
        total_price = 0
        
        # Add GKs (1 starting, 1 bench)
        for j, gk in enumerate(all_gk[:2], 1):
            team[f'GK{j}'] = f"{gk['full_name']} ({gk['club']})"
            team[f'GK{j}_selected'] = 1 if j == 1 else 0
            team[f'GK{j}_price'] = gk['price']
            team[f'GK{j}_score'] = gk['weighted_score']
            total_price += gk['price']
        
        # Add DEFs (formation[1] starting, rest bench)
        for j, df in enumerate(all_def[:5], 1):
            team[f'DEF{j}'] = f"{df['full_name']} ({df['club']})"
            team[f'DEF{j}_selected'] = 1 if j <= formation[1] else 0
            team[f'DEF{j}_price'] = df['price']
            team[f'DEF{j}_score'] = df['weighted_score']
            total_price += df['price']
        
        # Add MIDs (formation[2] starting, rest bench)
        for j, mid in enumerate(all_mid[:5], 1):
            team[f'MID{j}'] = f"{mid['full_name']} ({mid['club']})"
            team[f'MID{j}_selected'] = 1 if j <= formation[2] else 0
            team[f'MID{j}_price'] = mid['price']
            team[f'MID{j}_score'] = mid['weighted_score']
            total_price += mid['price']
        
        # Add FWDs (formation[3] starting, rest bench)
        for j, fwd in enumerate(all_fwd[:3], 1):
            team[f'FWD{j}'] = f"{fwd['full_name']} ({fwd['club']})"
            team[f'FWD{j}_selected'] = 1 if j <= formation[3] else 0
            team[f'FWD{j}_price'] = fwd['price']
            team[f'FWD{j}_score'] = fwd['weighted_score']
            total_price += fwd['price']
        
        # Calculate total score for selected 11
        total_score = 0
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for j in range(1, 6):
                if f'{pos}{j}_selected' in team and team[f'{pos}{j}_selected'] == 1:
                    total_score += team.get(f'{pos}{j}_score', 0)
        
        team['11_selected_total_scores'] = round(total_score, 2)
        team['15_total_price'] = round(total_price, 1)
        
        # Create signature to avoid duplicates
        players_list = []
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for j in range(1, 6):
                if f'{pos}{j}' in team:
                    players_list.append(team[f'{pos}{j}'])
        signature = '|'.join(sorted(players_list))
        
        # Only add if within budget and not duplicate
        if total_price <= 100.0 and signature not in team_signatures:
            teams.append(team)
            team_signatures.add(signature)
    
    # Strategy 2: Balanced teams (remaining teams)
    attempts = 0
    while len(teams) < num_teams and attempts < 500:
        attempts += 1
        
        # Mix of top and value picks
        base_idx = len(teams) + attempts
        
        # Vary the balance between top scorers and value
        value_ratio = 0.3 + (attempts % 10) * 0.05  # 30% to 80% value picks
        
        # Select players with mixed strategy
        gk_list = pd.concat([
            top_gk.sample(min(2, int(2 * (1 - value_ratio)) + 1)),
            cheap_gk.sample(min(2, int(2 * value_ratio)))
        ]).drop_duplicates().head(2).to_dict('records')
        
        def_list = pd.concat([
            top_def.sample(min(5, int(5 * (1 - value_ratio)) + 1)),
            cheap_def.sample(min(5, int(5 * value_ratio)))
        ]).drop_duplicates().head(5).to_dict('records')
        
        mid_list = pd.concat([
            top_mid.sample(min(5, int(5 * (1 - value_ratio)) + 1)),
            cheap_mid.sample(min(5, int(5 * value_ratio)))
        ]).drop_duplicates().head(5).to_dict('records')
        
        fwd_list = pd.concat([
            top_fwd.sample(min(3, int(3 * (1 - value_ratio)) + 1)),
            cheap_fwd.sample(min(3, int(3 * value_ratio)))
        ]).drop_duplicates().head(3).to_dict('records')
        
        # Check team constraints
        team_counts = {}
        valid_team = True
        
        for player_list in [gk_list, def_list, mid_list, fwd_list]:
            for player in player_list:
                team = player['club']
                team_counts[team] = team_counts.get(team, 0) + 1
                if team_counts[team] > 3:
                    valid_team = False
                    break
            if not valid_team:
                break
        
        if not valid_team:
            continue
        
        # Sort by score to select best 11
        gk_list = sorted(gk_list, key=lambda x: x['weighted_score'], reverse=True)
        def_list = sorted(def_list, key=lambda x: x['weighted_score'], reverse=True)
        mid_list = sorted(mid_list, key=lambda x: x['weighted_score'], reverse=True)
        fwd_list = sorted(fwd_list, key=lambda x: x['weighted_score'], reverse=True)
        
        # Build team
        team = {}
        total_price = 0
        
        # Add players
        for j, gk in enumerate(gk_list[:2], 1):
            team[f'GK{j}'] = f"{gk['full_name']} ({gk['club']})"
            team[f'GK{j}_selected'] = 1 if j == 1 else 0
            team[f'GK{j}_price'] = gk['price']
            team[f'GK{j}_score'] = gk['weighted_score']
            total_price += gk['price']
        
        for j, df in enumerate(def_list[:5], 1):
            team[f'DEF{j}'] = f"{df['full_name']} ({df['club']})"
            team[f'DEF{j}_selected'] = 1 if j <= 4 else 0
            team[f'DEF{j}_price'] = df['price']
            team[f'DEF{j}_score'] = df['weighted_score']
            total_price += df['price']
        
        for j, mid in enumerate(mid_list[:5], 1):
            team[f'MID{j}'] = f"{mid['full_name']} ({mid['club']})"
            team[f'MID{j}_selected'] = 1 if j <= 3 else 0
            team[f'MID{j}_price'] = mid['price']
            team[f'MID{j}_score'] = mid['weighted_score']
            total_price += mid['price']
        
        for j, fwd in enumerate(fwd_list[:3], 1):
            team[f'FWD{j}'] = f"{fwd['full_name']} ({fwd['club']})"
            team[f'FWD{j}_selected'] = 1 if j <= 2 else 0
            team[f'FWD{j}_price'] = fwd['price']
            team[f'FWD{j}_score'] = fwd['weighted_score']
            total_price += fwd['price']
        
        # Calculate score
        total_score = 0
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for j in range(1, 6):
                if f'{pos}{j}_selected' in team and team[f'{pos}{j}_selected'] == 1:
                    total_score += team.get(f'{pos}{j}_score', 0)
        
        team['11_selected_total_scores'] = round(total_score, 2)
        team['15_total_price'] = round(total_price, 1)
        
        # Create signature
        players_list = []
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for j in range(1, 6):
                if f'{pos}{j}' in team:
                    players_list.append(team[f'{pos}{j}'])
        signature = '|'.join(sorted(players_list))
        
        # Only add if within budget and not duplicate
        if total_price <= 100.0 and signature not in team_signatures:
            teams.append(team)
            team_signatures.add(signature)
    
    # Create dataframe and sort by score
    teams_df = pd.DataFrame(teams)
    teams_df = teams_df.sort_values('11_selected_total_scores', ascending=False)
    
    # Keep only top N teams
    teams_df = teams_df.head(num_teams)
    
    teams_df.to_csv(output_file, index=False)
    print(f"Created {len(teams_df)} teams")
    
    # Show statistics
    if len(teams_df) > 0:
        print(f"\nBudget range: £{teams_df['15_total_price'].min():.1f}m - £{teams_df['15_total_price'].max():.1f}m")
        print(f"Score range: {teams_df['11_selected_total_scores'].min():.1f} - {teams_df['11_selected_total_scores'].max():.1f}")
        
        print("\nTop team:")
        top_team = teams_df.iloc[0]
        print("\nStarting XI:")
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for j in range(1, 6):
                col = f'{pos}{j}'
                if col in top_team and pd.notna(top_team[col]):
                    if top_team.get(f'{col}_selected', 0) == 1:
                        print(f"  {col}: {top_team[col]} - £{top_team[f'{col}_price']:.1f}m ({top_team[f'{col}_score']:.2f})")
        
        print("\nBench:")
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for j in range(1, 6):
                col = f'{pos}{j}'
                if col in top_team and pd.notna(top_team[col]):
                    if top_team.get(f'{col}_selected', 0) == 0:
                        print(f"  {col}: {top_team[col]} - £{top_team[f'{col}_price']:.1f}m")
        
        print(f"\nTotal: £{top_team['15_total_price']:.1f}m, Score: {top_team['11_selected_total_scores']:.2f}")


def main():
    import sys
    if len(sys.argv) != 3:
        pred_file = "data/cached_merged_2024_2025_v2/predictions_gw39_with_roles.csv"
        output_file = "data/cached_merged_2024_2025_v2/top_200_teams_gw39.csv"
    else:
        pred_file = sys.argv[1]
        output_file = sys.argv[2]
        
    create_optimized_teams(pred_file, output_file)


if __name__ == "__main__":
    main()