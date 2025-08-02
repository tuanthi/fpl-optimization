#!/usr/bin/env python3
"""
Optimized approach to create top teams for gameweek 39 WITH CAPTAINCY
- Uses weighted score with captain selection (2x points for captain)
- Optimizes for 11 players with cheap bench
- Generates top 200 teams considering captain choice
"""

import pandas as pd
from pathlib import Path
import numpy as np


def calculate_team_score_with_captain(team_players, captain_idx=None):
    """Calculate team score with captain getting 2x points"""
    total_score = 0
    
    for i, player in enumerate(team_players):
        if captain_idx is not None and i == captain_idx:
            total_score += player['weighted_score'] * 2  # Captain gets double
        else:
            total_score += player['weighted_score']
    
    return total_score


def find_best_captain(team_players):
    """Find the best captain choice from starting XI"""
    best_idx = 0
    best_score = 0
    
    for i, player in enumerate(team_players):
        if player['weighted_score'] > best_score:
            best_score = player['weighted_score']
            best_idx = i
    
    return best_idx


def create_optimized_teams_with_captain(pred_file, output_file, num_teams=200):
    """Create top teams considering captaincy"""
    
    # Load predictions
    df = pd.read_csv(pred_file)
    
    # Get unique players
    df['player_key'] = df['first_name'] + ' ' + df['last_name'] + ' (' + df['club'] + ')'
    df_unique = df.sort_values('weighted_score', ascending=False).drop_duplicates(['player_key'], keep='first')
    
    players = df_unique.groupby(['first_name', 'last_name', 'club', 'role']).agg({
        'weighted_score': 'mean',
        'price': 'first'
    }).reset_index()
    
    players['full_name'] = players['first_name'] + ' ' + players['last_name']
    
    # Separate by position
    gks = players[players['role'] == 'GK'].to_dict('records')
    defs = players[players['role'] == 'DEF'].to_dict('records') 
    mids = players[players['role'] == 'MID'].to_dict('records')
    fwds = players[players['role'] == 'FWD'].to_dict('records')
    
    # Sort by score
    gks.sort(key=lambda x: x['weighted_score'], reverse=True)
    defs.sort(key=lambda x: x['weighted_score'], reverse=True)
    mids.sort(key=lambda x: x['weighted_score'], reverse=True)
    fwds.sort(key=lambda x: x['weighted_score'], reverse=True)
    
    teams = []
    team_signatures = set()
    
    # Formations to try
    formations = [
        (1, 3, 5, 2),  # 3-5-2 (good for premium mids like Salah)
        (1, 3, 4, 3),  # 3-4-3 (balanced)
        (1, 4, 4, 2),  # 4-4-2 (classic)
        (1, 4, 3, 3),  # 4-3-3 (forward heavy)
        (1, 5, 3, 2),  # 5-3-2 (defensive)
    ]
    
    # Strategy 1: Build around premium captains (50% of teams)
    premium_captains = []
    
    # Get top scorers from each position who could be captains
    premium_captains.extend([(p, 'MID') for p in mids[:10] if p['weighted_score'] > 5.0])
    premium_captains.extend([(p, 'FWD') for p in fwds[:8] if p['weighted_score'] > 5.0])
    premium_captains.extend([(p, 'DEF') for p in defs[:5] if p['weighted_score'] > 3.5])
    
    # Sort by score
    premium_captains.sort(key=lambda x: x[0]['weighted_score'], reverse=True)
    
    print(f"Found {len(premium_captains)} premium captain options")
    print("Top 5 captain choices:")
    for i, (player, pos) in enumerate(premium_captains[:5]):
        print(f"  {i+1}. {player['full_name']} ({player['club']}, {pos}): {player['weighted_score']:.2f}")
    
    # Build teams around each premium captain
    for captain_idx, (captain, captain_pos) in enumerate(premium_captains[:num_teams // 2]):
        for formation_idx, formation in enumerate(formations):
            if len(teams) >= num_teams:
                break
            
            team_players = []
            team_cost = 0
            team_counts = {}
            
            # Add captain first
            team_players.append(captain)
            team_cost += captain['price']
            team_counts[captain['club']] = 1
            
            # Determine how many more of each position we need
            gk_needed = formation[0]
            def_needed = formation[1]
            mid_needed = formation[2] - (1 if captain_pos == 'MID' else 0)
            fwd_needed = formation[3] - (1 if captain_pos == 'FWD' else 0)
            
            # Helper function to add players
            def add_players_from_pool(pool, needed, max_budget_per_player):
                added = []
                for player in pool:
                    if len(added) >= needed:
                        break
                    
                    # Skip if same as captain
                    if player['full_name'] == captain['full_name']:
                        continue
                    
                    # Check constraints
                    if team_counts.get(player['club'], 0) >= 3:
                        continue
                    
                    if team_cost + player['price'] > 85:  # Leave room for bench
                        continue
                    
                    if player['price'] > max_budget_per_player:
                        continue
                    
                    added.append(player)
                    team_counts[player['club']] = team_counts.get(player['club'], 0) + 1
                
                return added
            
            # Add players prioritizing value around the premium captain
            selected_gks = add_players_from_pool(gks, gk_needed, 6.0)
            selected_defs = add_players_from_pool(defs, def_needed, 6.5)
            selected_mids = add_players_from_pool(mids, mid_needed, 9.0)
            selected_fwds = add_players_from_pool(fwds, fwd_needed, 9.0)
            
            # Check if we have enough players
            if (len(selected_gks) < gk_needed or len(selected_defs) < def_needed or
                len(selected_mids) < mid_needed or len(selected_fwds) < fwd_needed):
                continue
            
            # Build starting XI
            starting_xi = []
            if captain_pos != 'GK':
                starting_xi.extend(selected_gks[:gk_needed])
            starting_xi.extend(selected_defs[:def_needed])
            if captain_pos != 'MID':
                starting_xi.extend(selected_mids[:mid_needed])
            if captain_pos != 'FWD':
                starting_xi.extend(selected_fwds[:fwd_needed])
            
            # Add captain to starting XI
            starting_xi.append(captain)
            
            # Calculate cost
            starting_cost = sum(p['price'] for p in starting_xi)
            
            # Add cheap bench
            bench = []
            bench_budget = 100 - starting_cost - 5  # Reserve 5m for flexibility
            
            # Need: 1 GK, 1-2 DEF, 0-1 MID, 0-1 FWD (total 4 bench)
            cheap_gks = [g for g in gks if g['price'] <= 4.5 and g not in starting_xi]
            cheap_defs = [d for d in defs if d['price'] <= 4.5 and d not in starting_xi]
            cheap_mids = [m for m in mids if m['price'] <= 5.0 and m not in starting_xi]
            cheap_fwds = [f for f in fwds if f['price'] <= 5.0 and f not in starting_xi]
            
            # Add bench GK
            for gk in cheap_gks:
                if team_counts.get(gk['club'], 0) < 3:
                    bench.append(gk)
                    team_counts[gk['club']] = team_counts.get(gk['club'], 0) + 1
                    break
            
            # Add bench players to reach 15
            bench_needed = 4
            for pool in [cheap_defs, cheap_mids, cheap_fwds, cheap_defs]:  # Prioritize defenders
                for player in pool:
                    if len(bench) >= bench_needed:
                        break
                    if team_counts.get(player['club'], 0) < 3 and player not in bench:
                        bench.append(player)
                        team_counts[player['club']] = team_counts.get(player['club'], 0) + 1
            
            if len(bench) < 4:
                continue
            
            # Calculate total cost
            total_cost = starting_cost + sum(p['price'] for p in bench[:4])
            
            if total_cost > 100:
                continue
            
            # Find best captain in starting XI
            captain_idx = len(starting_xi) - 1  # Captain is last in list
            
            # Calculate score with captain
            total_score = calculate_team_score_with_captain(starting_xi, captain_idx)
            
            # Build team dict
            team = {
                'formation': f"{formation[1]}-{formation[2]}-{formation[3]}",
                'captain': f"{captain['full_name']} ({captain['club']})",
                'captain_score': captain['weighted_score'],
                '11_selected_total_scores': round(total_score, 2),
                '15_total_price': round(total_cost, 1)
            }
            
            # Add players to team dict
            pos_counts = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
            
            # Starting XI
            for player in starting_xi:
                role = player['role']
                pos_counts[role] += 1
                key = f"{role}{pos_counts[role]}"
                team[key] = f"{player['full_name']} ({player['club']})"
                team[f"{key}_selected"] = 1
                team[f"{key}_price"] = player['price']
                team[f"{key}_score"] = player['weighted_score']
            
            # Bench
            for player in bench[:4]:
                role = player['role']
                pos_counts[role] += 1
                key = f"{role}{pos_counts[role]}"
                team[key] = f"{player['full_name']} ({player['club']})"
                team[f"{key}_selected"] = 0
                team[f"{key}_price"] = player['price']
                team[f"{key}_score"] = player['weighted_score']
            
            # Create signature
            all_players = [team[k] for k in team if k.startswith(('GK', 'DEF', 'MID', 'FWD')) and not k.endswith(('_selected', '_price', '_score'))]
            signature = '|'.join(sorted(all_players))
            
            if signature not in team_signatures:
                teams.append(team)
                team_signatures.add(signature)
    
    # Strategy 2: Balanced teams without specific captain focus
    attempts = 0
    while len(teams) < num_teams and attempts < 1000:
        attempts += 1
        
        # Random formation
        formation = formations[attempts % len(formations)]
        
        # Build team
        team_players = []
        team_cost = 0
        team_counts = {}
        
        # Select players with some randomness
        offset = attempts % 10
        
        selected_gks = []
        selected_defs = []
        selected_mids = []
        selected_fwds = []
        
        # Add top players with offset
        for i in range(formation[0]):
            for gk in gks[offset:]:
                if team_counts.get(gk['club'], 0) < 3 and gk not in selected_gks:
                    selected_gks.append(gk)
                    team_counts[gk['club']] = team_counts.get(gk['club'], 0) + 1
                    break
        
        for i in range(formation[1]):
            for df in defs[offset:]:
                if team_counts.get(df['club'], 0) < 3 and df not in selected_defs:
                    selected_defs.append(df)
                    team_counts[df['club']] = team_counts.get(df['club'], 0) + 1
                    break
        
        for i in range(formation[2]):
            for mid in mids[offset:]:
                if team_counts.get(mid['club'], 0) < 3 and mid not in selected_mids:
                    selected_mids.append(mid)
                    team_counts[mid['club']] = team_counts.get(mid['club'], 0) + 1
                    break
        
        for i in range(formation[3]):
            for fwd in fwds[offset:]:
                if team_counts.get(fwd['club'], 0) < 3 and fwd not in selected_fwds:
                    selected_fwds.append(fwd)
                    team_counts[fwd['club']] = team_counts.get(fwd['club'], 0) + 1
                    break
        
        # Check if we have enough
        if (len(selected_gks) < formation[0] or len(selected_defs) < formation[1] or
            len(selected_mids) < formation[2] or len(selected_fwds) < formation[3]):
            continue
        
        # Build starting XI
        starting_xi = selected_gks + selected_defs + selected_mids + selected_fwds
        
        # Find best captain
        captain_idx = find_best_captain(starting_xi)
        captain = starting_xi[captain_idx]
        
        # Calculate cost and score
        starting_cost = sum(p['price'] for p in starting_xi)
        
        if starting_cost > 90:  # Leave room for bench
            continue
        
        # Add bench (similar to above)
        bench = []
        
        # Cheap options
        cheap_gks = [g for g in gks if g['price'] <= 4.5 and g not in starting_xi][:2]
        cheap_defs = [d for d in defs if d['price'] <= 4.5 and d not in starting_xi][:3]
        cheap_mids = [m for m in mids if m['price'] <= 5.0 and m not in starting_xi][:2]
        cheap_fwds = [f for f in fwds if f['price'] <= 5.0 and f not in starting_xi][:2]
        
        # Need bench GK
        bench_added = False
        for gk in cheap_gks:
            if team_counts.get(gk['club'], 0) < 3:
                bench.append(gk)
                bench_added = True
                break
        
        if not bench_added:
            continue
        
        # Add 3 more bench players
        all_cheap = cheap_defs + cheap_mids + cheap_fwds
        all_cheap.sort(key=lambda x: x['price'])
        
        for player in all_cheap:
            if len(bench) >= 4:
                break
            if team_counts.get(player['club'], 0) < 3:
                bench.append(player)
        
        if len(bench) < 4:
            continue
        
        # Total cost
        total_cost = starting_cost + sum(p['price'] for p in bench)
        
        if total_cost > 100:
            continue
        
        # Calculate score with captain
        total_score = calculate_team_score_with_captain(starting_xi, captain_idx)
        
        # Build team dict (same as above)
        team = {
            'formation': f"{formation[1]}-{formation[2]}-{formation[3]}",
            'captain': f"{captain['full_name']} ({captain['club']})",
            'captain_score': captain['weighted_score'],
            '11_selected_total_scores': round(total_score, 2),
            '15_total_price': round(total_cost, 1)
        }
        
        # Add all 15 players
        all_players = starting_xi + bench
        pos_counts = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
        
        for i, player in enumerate(all_players):
            role = player['role']
            pos_counts[role] += 1
            key = f"{role}{pos_counts[role]}"
            team[key] = f"{player['full_name']} ({player['club']})"
            team[f"{key}_selected"] = 1 if i < 11 else 0
            team[f"{key}_price"] = player['price']
            team[f"{key}_score"] = player['weighted_score']
        
        # Signature
        all_player_names = [team[k] for k in team if k.startswith(('GK', 'DEF', 'MID', 'FWD')) and not k.endswith(('_selected', '_price', '_score'))]
        signature = '|'.join(sorted(all_player_names))
        
        if signature not in team_signatures:
            teams.append(team)
            team_signatures.add(signature)
    
    # Sort by score
    teams_df = pd.DataFrame(teams)
    teams_df = teams_df.sort_values('11_selected_total_scores', ascending=False)
    teams_df = teams_df.head(num_teams)
    
    # Save
    teams_df.to_csv(output_file, index=False)
    
    print(f"\nCreated {len(teams_df)} teams with captaincy consideration")
    print(f"Score range: {teams_df['11_selected_total_scores'].min():.1f} - {teams_df['11_selected_total_scores'].max():.1f}")
    print(f"Budget range: £{teams_df['15_total_price'].min():.1f}m - £{teams_df['15_total_price'].max():.1f}m")
    
    # Show top teams
    print("\nTop 5 teams:")
    for idx, team in teams_df.head(5).iterrows():
        print(f"\n{idx+1}. Score: {team['11_selected_total_scores']:.1f}, "
              f"Budget: £{team['15_total_price']:.1f}m, "
              f"Formation: {team['formation']}")
        print(f"   Captain: {team['captain']} ({team['captain_score']:.2f} x 2 = {team['captain_score']*2:.2f})")
    
    return teams_df


def main():
    import sys
    
    pred_file = "data/cached_merged_2024_2025_v2/predictions_gw39_proper.csv"
    output_file = "data/cached_merged_2024_2025_v2/top_200_teams_gw39_with_captain.csv"
    
    create_optimized_teams_with_captain(pred_file, output_file, num_teams=200)


if __name__ == "__main__":
    main()