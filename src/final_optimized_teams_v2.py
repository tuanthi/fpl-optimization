#!/usr/bin/env python3
"""
Improved team optimization with better player filtering:
1. Minimum minutes requirement
2. Exclude loan players
3. Realistic score thresholds
"""

import pandas as pd
import numpy as np
from pathlib import Path


def load_player_minutes():
    """Load player minutes data from 2024 season"""
    player_gw_file = "/Users/huetuanthi/dev/dokeai/fpl/data/2024/2024_player_gameweek.csv"
    if not Path(player_gw_file).exists():
        print("Warning: No minutes data available")
        return {}
    
    gw_df = pd.read_csv(player_gw_file)
    
    # Calculate total minutes per player
    minutes_df = gw_df.groupby(['name', 'team'])['minutes'].sum().reset_index()
    minutes_df.columns = ['player_name', 'team', 'total_minutes']
    
    # Create a dictionary for lookup
    minutes_dict = {}
    for _, row in minutes_df.iterrows():
        # Use just the player name without team for matching
        minutes_dict[row['player_name']] = row['total_minutes']
    
    return minutes_dict


def is_valid_player(player_name, player_club, player_score, role, minutes_dict=None):
    """Check if a player is valid for selection"""
    
    # Known loan/invalid players (manual list - should be expanded)
    invalid_players = [
        'Antoñito Cordero Campillo',  # On loan
        'Carlos Alcaraz',  # Southampton player, not Bournemouth
        # Add more as discovered
    ]
    
    if player_name in invalid_players:
        return False
    
    # Check minutes threshold (at least 500 minutes in previous season)
    if minutes_dict and player_name in minutes_dict:
        if minutes_dict[player_name] < 500:
            return False
    
    # Score sanity checks by position
    if role == 'GK':
        # GK scores should be between 2-6 typically
        if player_score < 2.0 or player_score > 6.0:
            return False
    elif role == 'DEF':
        # DEF scores should be between 2-5 typically
        if player_score < 2.0 or player_score > 5.5:
            return False
    elif role == 'MID':
        # MID scores should be between 2-10 typically
        if player_score < 2.0 or player_score > 10.0:
            return False
    elif role == 'FWD':
        # FWD scores should be between 2-8 typically
        if player_score < 2.0 or player_score > 8.0:
            return False
    
    return True


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
    """Build teams with improved filtering"""
    
    # Load predictions
    df = pd.read_csv(predictions_file)
    
    # Load minutes data
    print("Loading player minutes data...")
    minutes_dict = load_player_minutes()
    print(f"Loaded minutes data for {len(minutes_dict)} players")
    
    # Create unique player list with validation
    players = []
    skipped_players = []
    
    for _, row in df.iterrows():
        player_name = f"{row['first_name']} {row['last_name']}"
        player_info = {
            'name': player_name,
            'full_id': f"{player_name} ({row['club']})",
            'club': row['club'],
            'role': row['role'],
            'price': row['price'],
            'score': row['weighted_score']
        }
        
        # Validate player
        if is_valid_player(player_name, row['club'], row['weighted_score'], row['role'], minutes_dict):
            players.append(player_info)
        else:
            skipped_players.append((player_name, row['club'], row['weighted_score']))
    
    print(f"\nFiltered out {len(skipped_players)} invalid players")
    if len(skipped_players) > 0:
        print("Examples of filtered players:")
        for name, club, score in skipped_players[:10]:
            print(f"  - {name} ({club}): {score:.2f}")
    
    # Sort by score
    players.sort(key=lambda x: x['score'], reverse=True)
    
    # Group by position
    positions = {
        'GK': [p for p in players if p['role'] == 'GK'],
        'DEF': [p for p in players if p['role'] == 'DEF'],
        'MID': [p for p in players if p['role'] == 'MID'],
        'FWD': [p for p in players if p['role'] == 'FWD']
    }
    
    print(f"\nAvailable players after filtering:")
    for role, role_players in positions.items():
        print(f"  {role}: {len(role_players)} players")
        if len(role_players) > 0:
            print(f"    Top 3: {', '.join([p['name'] for p in role_players[:3]])}")
    
    teams = []
    
    # Get top scorers for captaincy
    top_scorers = []
    for role in ['MID', 'FWD']:
        role_players = [p for p in players if p['role'] == role]
        top_scorers.extend(role_players[:25])  # Top 25 from each
    
    # Also add some top defenders
    def_players = [p for p in players if p['role'] == 'DEF']
    top_scorers.extend(def_players[:10])
    
    # Sort by score and get unique captains
    top_scorers.sort(key=lambda x: x['score'], reverse=True)
    seen = set()
    priority_captains = []
    for p in top_scorers:
        if p['name'] not in seen and p['score'] > 4.0:  # Higher threshold
            priority_captains.append(p['name'])
            seen.add(p['name'])
            if len(priority_captains) >= 40:
                break
    
    print(f"\nIdentified {len(priority_captains)} valid captain options")
    
    formations = [
        {'name': '3-5-2', 'gk': 1, 'def': 3, 'mid': 5, 'fwd': 2},
        {'name': '3-4-3', 'gk': 1, 'def': 3, 'mid': 4, 'fwd': 3},
        {'name': '4-4-2', 'gk': 1, 'def': 4, 'mid': 4, 'fwd': 2},
        {'name': '4-3-3', 'gk': 1, 'def': 4, 'mid': 3, 'fwd': 3},
        {'name': '5-3-2', 'gk': 1, 'def': 5, 'mid': 3, 'fwd': 2}
    ]
    
    print("\nBuilding teams with captain optimization...")
    
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
        
        if captain_idx % 10 == 0:
            print(f"\nBuilding teams with captain: {captain['name']} (score: {captain['score']:.2f})")
        
        # Try each formation with variations
        for formation_idx, formation in enumerate(formations):
            for variation in range(2):  # 2 variations per formation
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
                    # Add variation by starting at different positions
                    start_idx = variation * 3
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
                        if team['cost'] + player['price'] > 82:  # Stricter budget
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
                            # Check if valid even for bench
                            if is_valid_player(gk['name'], gk['club'], gk['score'], 'GK', minutes_dict):
                                team['bench'].append(gk)
                                team['cost'] += gk['price']
                                bench_added += 1
                                break
                
                # Cheap outfield players for bench
                all_cheap = []
                for role in ['DEF', 'MID', 'FWD']:
                    cheap_players = [p for p in positions[role] if p['price'] <= 5.0]
                    # Still validate bench players
                    cheap_valid = [p for p in cheap_players if 
                                 is_valid_player(p['name'], p['club'], p['score'], role, minutes_dict)]
                    all_cheap.extend(cheap_valid)
                
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
                
                # Estimate 5GW score
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
    
    # Convert to DataFrame format
    rows = []
    for i, team in enumerate(teams[:num_teams]):
        row = {}
        
        # Key info columns
        row['captain'] = team['captain']
        row['formation'] = team['formation']
        row['budget'] = round(team['cost'], 1)
        row['gw1_score'] = round(team['captain_score'], 1)
        row['5gw_estimated'] = round(team['5gw_score'], 1)
        
        # Separate players by position
        selected_players = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
        bench_players = []
        
        # Categorize starting XI
        for player in team['players']:
            selected_players[player['role']].append(player)
        
        # Categorize bench
        for player in team['bench']:
            bench_players.append(player)
        
        # Add selected players in position order
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for i, player in enumerate(selected_players[pos], 1):
                key = f'{pos}{i}'
                row[key] = player['full_id']
                row[f'{key}_role'] = pos
                row[f'{key}_selected'] = 1
                row[f'{key}_price'] = player['price']
                row[f'{key}_score'] = player['score']
        
        # Add bench players
        bench_gks = [p for p in bench_players if p['role'] == 'GK']
        bench_others = [p for p in bench_players if p['role'] != 'GK']
        bench_others.sort(key=lambda x: x['score'], reverse=True)
        
        sorted_bench = bench_gks + bench_others
        
        for i, player in enumerate(sorted_bench, 1):
            row[f'BENCH{i}'] = player['full_id']
            row[f'BENCH{i}_role'] = player['role']
            row[f'BENCH{i}_selected'] = 0
            row[f'BENCH{i}_price'] = player['price']
            row[f'BENCH{i}_score'] = player['score']
        
        rows.append(row)
    
    # Create DataFrame
    if rows:
        df = pd.DataFrame(rows)
        
        # Define column order - natural order, not sorted
        key_cols = ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated']
        
        # Get all columns in natural order (GK1, GK2, DEF1, DEF2, etc.)
        ordered_cols = key_cols.copy()
        
        # Add columns in position order
        positions = ['GK', 'DEF', 'MID', 'FWD', 'BENCH']
        for pos in positions:
            # Find max number for this position
            max_num = 0
            for col in df.columns:
                if col.startswith(pos) and col[len(pos):].isdigit():
                    max_num = max(max_num, int(col[len(pos):]))
            
            # Add all columns for each position number
            for i in range(1, max_num + 1):
                base_col = f'{pos}{i}'
                if base_col in df.columns:
                    ordered_cols.append(base_col)
                    # Add associated columns
                    for suffix in ['_role', '_selected', '_price', '_score']:
                        col = f'{base_col}{suffix}'
                        if col in df.columns:
                            ordered_cols.append(col)
        
        # Add any remaining columns
        remaining = [col for col in df.columns if col not in ordered_cols]
        ordered_cols.extend(remaining)
        
        df = df[ordered_cols]
        
        return df
    else:
        return pd.DataFrame()


def main():
    predictions_file = "../data/cached_merged_2024_2025_v2/predictions_gw39_proper_v3.csv"
    output_file = "../data/cached_merged_2024_2025_v2/top_200_teams_final_v4.csv"
    
    print("Creating optimized teams with improved player filtering...")
    
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