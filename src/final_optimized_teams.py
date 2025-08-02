#!/usr/bin/env python3
"""
Final team optimization combining:
1. Captain selection (2x points)
2. Transfer planning over 5 gameweeks
3. Budget and team constraints
"""

import pandas as pd
import numpy as np
from pathlib import Path


def calculate_team_score(players, captain_name=None):
    """Calculate team score with captain bonus"""
    total = 0
    for p in players:
        score = p['score']
        if captain_name and p['name'] == captain_name:
            score *= 2  # Captain bonus
        total += score
    return total


def build_optimal_teams(predictions_file, num_teams=200):
    """Build teams optimized for captaincy and transfers"""
    
    # Load predictions
    df = pd.read_csv(predictions_file)
    
    # Create unique player list
    players = []
    for _, row in df.iterrows():
        players.append({
            'name': f"{row['first_name']} {row['last_name']}",
            'full_id': f"{row['first_name']} {row['last_name']} ({row['club']})",
            'club': row['club'],
            'role': row['role'],
            'price': row['price'],
            'score': row['weighted_score']
        })
    
    # Sort by score
    players.sort(key=lambda x: x['score'], reverse=True)
    
    # Group by position
    positions = {
        'GK': [p for p in players if p['role'] == 'GK'],
        'DEF': [p for p in players if p['role'] == 'DEF'],
        'MID': [p for p in players if p['role'] == 'MID'],
        'FWD': [p for p in players if p['role'] == 'FWD']
    }
    
    teams = []
    
    # Key insight: Teams with high-scoring captains perform best
    # Priority captains (must be in starting XI)
    # Get top scorers from each position
    top_scorers = []
    for role in ['MID', 'FWD']:
        role_players = [p for p in players if p['role'] == role]
        top_scorers.extend(role_players[:30])
    
    # Also add some top defenders
    def_players = [p for p in players if p['role'] == 'DEF']
    top_scorers.extend(def_players[:10])
    
    # Sort by score and take unique names
    top_scorers.sort(key=lambda x: x['score'], reverse=True)
    seen = set()
    priority_captains = []
    for p in top_scorers:
        if p['name'] not in seen and p['score'] > 3.5:  # Lower threshold
            priority_captains.append(p['name'])
            seen.add(p['name'])
            if len(priority_captains) >= 50:  # More captains
                break
    
    formations = [
        {'name': '3-5-2', 'gk': 1, 'def': 3, 'mid': 5, 'fwd': 2},
        {'name': '3-4-3', 'gk': 1, 'def': 3, 'mid': 4, 'fwd': 3},
        {'name': '4-4-2', 'gk': 1, 'def': 4, 'mid': 4, 'fwd': 2},
        {'name': '4-3-3', 'gk': 1, 'def': 4, 'mid': 3, 'fwd': 3},
        {'name': '5-3-2', 'gk': 1, 'def': 5, 'mid': 3, 'fwd': 2}
    ]
    
    print("Building teams with captain optimization...")
    
    # Build teams around each captain
    for captain_idx, captain_name in enumerate(priority_captains):
        # Find captain
        captain = None
        captain_pos = None
        
        for pos, pool in positions.items():
            for p in pool:
                if captain_name in p['name']:
                    captain = p
                    captain_pos = pos
                    break
            if captain:
                break
        
        if not captain:
            continue
        
        if captain_idx % 10 == 0:  # Print less frequently
            print(f"\nBuilding teams with captain: {captain['name']} (score: {captain['score']:.2f})")
        
        # Try each formation with variations
        for formation_idx, formation in enumerate(formations):
            # Try multiple variations for each captain/formation combo
            for variation in range(3):
                # Build team
                team = {
                    'players': [],
                    'bench': [],
                    'captain': captain['name'],
                    'formation': formation['name'],
                    'cost': 0
                }
                
                team_counts = {}
                
                # Add captain first
                team['players'].append(captain)
                team['cost'] += captain['price']
                team_counts[captain['club']] = 1
            
                # Fill remaining positions
                for pos_name, needed in formation.items():
                    if pos_name == 'name':
                        continue
                    
                    role = pos_name.upper()
                    if role == captain_pos:
                        needed -= 1  # Already have captain
                    
                    added = 0
                    # Add variation by starting at different positions in the player pool
                    start_idx = variation * 2
                    player_pool = positions[role][start_idx:] + positions[role][:start_idx]
                    
                    for player in player_pool:
                        if added >= needed:
                            break
                        
                        # Skip if already in team
                        if any(p['name'] == player['name'] for p in team['players']):
                            continue
                        
                        # Check team limit
                        if team_counts.get(player['club'], 0) >= 3:
                            continue
                        
                        # Check budget (leave room for bench)
                        if team['cost'] + player['price'] > 84:
                            continue
                        
                        team['players'].append(player)
                        team['cost'] += player['price']
                        team_counts[player['club']] = team_counts.get(player['club'], 0) + 1
                        added += 1
            
                # Check if valid starting XI
                if len(team['players']) != 11:
                    continue
            
                # Add cheap bench (1 GK + 3 outfield)
                bench_added = 0
                
                # Bench GK
                for gk in positions['GK']:
                    if gk['price'] <= 4.5 and not any(p['name'] == gk['name'] for p in team['players']):
                        if team_counts.get(gk['club'], 0) < 3:
                            team['bench'].append(gk)
                            team['cost'] += gk['price']
                            bench_added += 1
                            break
            
                # Cheap outfield players
                all_cheap = []
                for role in ['DEF', 'MID', 'FWD']:
                    all_cheap.extend([p for p in positions[role] if p['price'] <= 5.0])
                
                all_cheap.sort(key=lambda x: x['price'])
                
                for player in all_cheap:
                    if bench_added >= 4:
                        break
                    
                    if not any(p['name'] == player['name'] for p in team['players'] + team['bench']):
                        if team_counts.get(player['club'], 0) < 3:
                            team['bench'].append(player)
                            team['cost'] += player['price']
                            team_counts[player['club']] = team_counts.get(player['club'], 0) + 1
                            bench_added += 1
            
                # Check if valid
                if len(team['bench']) < 4 or team['cost'] > 100:
                    continue
                
                # Calculate scores
                base_score = calculate_team_score(team['players'])
                
                # Find actual best captain (highest scorer in starting XI)
                actual_best_captain = max(team['players'], key=lambda x: x['score'])
                captain_score = calculate_team_score(team['players'], actual_best_captain['name'])
                
                # Update captain to the actual best player
                team['captain'] = actual_best_captain['name']
                
                # Estimate 5GW score (captain bonus + potential for 1 transfer per GW)
                # Assume each transfer improves team by 0.5 points per GW
                transfer_improvement = 0.5 * 4  # 4 transfers over 5 GWs
                five_gw_score = captain_score * 5 + transfer_improvement * 5
                
                team['base_score'] = base_score
                team['captain_score'] = captain_score
                team['5gw_score'] = five_gw_score
                
                teams.append(team)
                
                if len(teams) >= num_teams:
                    break
            
            if len(teams) >= num_teams:
                break
        
        if len(teams) >= num_teams:
            break
    
    # Sort by 5GW score
    teams.sort(key=lambda x: x['5gw_score'], reverse=True)
    
    # Convert to DataFrame format with proper column ordering
    rows = []
    for i, team in enumerate(teams[:num_teams]):
        row = {}
        
        # 1. Key info columns (in specific order)
        row['captain'] = team['captain']
        row['formation'] = team['formation']
        row['budget'] = round(team['cost'], 1)
        row['gw1_score'] = round(team['captain_score'], 1)
        row['5gw_estimated'] = round(team['5gw_score'], 1)
        
        # Separate players by position and selection status
        selected_players = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
        bench_players = []
        
        # Categorize starting XI
        for player in team['players']:
            selected_players[player['role']].append(player)
        
        # Categorize bench
        for player in team['bench']:
            bench_players.append(player)
        
        # 2. Add selected players in position order
        # GKs
        for i, gk in enumerate(selected_players['GK'], 1):
            row[f'GK{i}'] = gk['full_id']
            row[f'GK{i}_role'] = 'GK'
            row[f'GK{i}_selected'] = 1
            row[f'GK{i}_price'] = gk['price']
            row[f'GK{i}_score'] = gk['score']
        
        # DEFs
        for i, defender in enumerate(selected_players['DEF'], 1):
            row[f'DEF{i}'] = defender['full_id']
            row[f'DEF{i}_role'] = 'DEF'
            row[f'DEF{i}_selected'] = 1
            row[f'DEF{i}_price'] = defender['price']
            row[f'DEF{i}_score'] = defender['score']
        
        # MIDs
        for i, mid in enumerate(selected_players['MID'], 1):
            row[f'MID{i}'] = mid['full_id']
            row[f'MID{i}_role'] = 'MID'
            row[f'MID{i}_selected'] = 1
            row[f'MID{i}_price'] = mid['price']
            row[f'MID{i}_score'] = mid['score']
        
        # FWDs
        for i, fwd in enumerate(selected_players['FWD'], 1):
            row[f'FWD{i}'] = fwd['full_id']
            row[f'FWD{i}_role'] = 'FWD'
            row[f'FWD{i}_selected'] = 1
            row[f'FWD{i}_price'] = fwd['price']
            row[f'FWD{i}_score'] = fwd['score']
        
        # 3. Add bench players (GKs first, then by score)
        # Sort bench: GKs first, then others by score descending
        bench_gks = [p for p in bench_players if p['role'] == 'GK']
        bench_others = [p for p in bench_players if p['role'] != 'GK']
        bench_others.sort(key=lambda x: x['score'], reverse=True)
        
        sorted_bench = bench_gks + bench_others
        
        # Add bench players
        for i, player in enumerate(sorted_bench, 1):
            row[f'BENCH{i}'] = player['full_id']
            row[f'BENCH{i}_role'] = player['role']
            row[f'BENCH{i}_selected'] = 0
            row[f'BENCH{i}_price'] = player['price']
            row[f'BENCH{i}_score'] = player['score']
        
        rows.append(row)
    
    # Create DataFrame with columns in desired order
    if rows:
        df = pd.DataFrame(rows)
        
        # Define column order
        key_cols = ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated']
        
        # Get all other columns
        player_cols = [col for col in df.columns if col not in key_cols]
        
        # Reorder columns
        ordered_cols = key_cols + player_cols
        df = df[ordered_cols]
        
        return df
    else:
        return pd.DataFrame()


def main():
    predictions_file = "../data/cached_merged_2024_2025_v2/predictions_gw39_proper.csv"
    output_file = "../data/cached_merged_2024_2025_v2/top_200_teams_final.csv"
    
    print("Creating final optimized teams with captaincy and transfer planning...")
    
    teams_df = build_optimal_teams(predictions_file, num_teams=200)
    
    if teams_df is not None and not teams_df.empty:
        teams_df.to_csv(output_file, index=False)
        
        print(f"\nSaved {len(teams_df)} teams to {output_file}")
        print("\nTop 10 teams:")
        print("-" * 90)
        print(f"{'Rank':<6} {'Captain':<25} {'Formation':<10} {'Budget':<8} {'GW1':<8} {'5GW Est':<10}")
        print("-" * 90)
        
        for idx, team in teams_df.head(10).iterrows():
            print(f"{idx+1:<6} {team['captain']:<25} {team['formation']:<10} "
                  f"£{team['budget']:<7.1f} {team['gw1_score']:<8.1f} {team['5gw_estimated']:<10.1f}")
    else:
        print("Failed to create teams!")


if __name__ == "__main__":
    main()