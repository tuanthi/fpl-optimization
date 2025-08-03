#!/usr/bin/env python3
"""
Fixed version with proper captain selection:
- Captain is always the highest scoring player in the team
- Maintains 3 player per team constraint
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
        minutes_dict[row['player_name']] = row['total_minutes']
    
    return minutes_dict


def get_known_main_gks():
    """Get list of known main GKs"""
    return {
        'Arsenal': 'David Raya Martín',
        'Aston Villa': 'Emiliano Martínez Romero',
        'Bournemouth': 'Norberto Murara Neto',
        'Brentford': 'Caoimhín Kelleher',
        'Brighton': 'Bart Verbruggen',
        'Burnley': 'Max Weiß',
        'Chelsea': 'Robert Lynch Sánchez',
        'Crystal Palace': 'Dean Henderson',
        'Everton': 'Jordan Pickford',
        'Fulham': 'Bernd Leno',
        'Leeds': 'Illan Meslier',
        'Liverpool': 'Alisson Becker',
        'Man City': 'Ederson Santana de Moraes',
        'Man Utd': 'André Onana',
        'Newcastle': 'Nick Pope',
        "Nott'm Forest": 'Matz Sels',
        'Southampton': 'Aaron Ramsdale',
        'Spurs': 'Guglielmo Vicario',
        'Sunderland': 'Robin Roefs',
        'West Ham': 'Alphonse Areola',
        'Wolves': 'José Malheiro de Sá'
    }


def is_valid_player(player_name, player_club, player_score, role, minutes_dict=None, is_backup_gk=False):
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
        # For starting GKs, ensure minimum score of 2.0
        if not is_backup_gk:
            if player_score < 2.0 or player_score > 6.0:
                return False
        else:
            # Backup GKs can have lower scores (0.2-2.0)
            if player_score < 0.2 or player_score > 2.0:
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


def find_backup_gk(starting_gk, all_gks, team_counts, max_price=4.5, minutes_dict=None):
    """
    Find the best backup GK, considering 3 player per team limit
    
    Strategy:
    1. First try to find backup from same team IF we have less than 3 players from that team
    2. If not available or would exceed limit, find cheapest valid GK from another team
    """
    starting_team = starting_gk['club']
    
    # Check if we can add another player from starting GK's team
    can_add_same_team = team_counts.get(starting_team, 0) < 3
    
    if can_add_same_team:
        # Try to find backup from same team
        same_team_backups = [
            gk for gk in all_gks 
            if gk['club'] == starting_team 
            and gk['name'] != starting_gk['name']
            and gk['price'] <= max_price
            and gk['price'] >= 4.0  # Not too cheap (might be 3rd choice)
            and gk['score'] < 2.0  # Ensure it's a backup (low score)
        ]
        
        # Sort by price descending (higher price = more likely to be 2nd choice)
        same_team_backups.sort(key=lambda x: x['price'], reverse=True)
        
        if same_team_backups:
            # Found a backup from same team
            backup = same_team_backups[0]
            return backup
    
    # If no same-team backup available or would exceed limit, find cheapest backup from another team
    other_backups = [
        gk for gk in all_gks
        if gk['club'] != starting_team
        and gk['price'] <= max_price
        and team_counts.get(gk['club'], 0) < 3
        and gk['score'] < 2.0  # Ensure it's a backup
    ]
    
    # Sort by price (cheapest first) then by score
    other_backups.sort(key=lambda x: (x['price'], -x['score']))
    
    if other_backups:
        return other_backups[0]
    
    return None


def find_best_captain(players):
    """Find the highest scoring player in the team to be captain"""
    # Exclude GKs from captaincy (not common in FPL)
    non_gk_players = [p for p in players if p['role'] != 'GK']
    if non_gk_players:
        return max(non_gk_players, key=lambda x: x['score'])
    # Fallback to any player if all are GKs (shouldn't happen)
    return max(players, key=lambda x: x['score'])


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
    """Build teams with proper captain selection and 3 player constraint"""
    
    # Load predictions (using v4 with fixed GK scores)
    df = pd.read_csv(predictions_file)
    
    # Load minutes data
    print("Loading player minutes data...")
    minutes_dict = load_player_minutes()
    print(f"Loaded minutes data for {len(minutes_dict)} players")
    
    # Get known main GKs
    main_gks = get_known_main_gks()
    
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
        
        # For GKs, check if they're a main GK
        if row['role'] == 'GK':
            is_main_gk = player_name == main_gks.get(row['club'], '')
            # Only validate as starting GK if they're the main GK
            if is_valid_player(player_name, row['club'], row['weighted_score'], row['role'], 
                             minutes_dict, is_backup_gk=not is_main_gk):
                if is_main_gk or row['weighted_score'] >= 2.0:  # Double check for starting GKs
                    players.append(player_info)
                else:
                    # Backup GKs with very low scores
                    players.append(player_info)
            else:
                skipped_players.append((player_name, row['club'], row['role'], 
                                      row['weighted_score'], 'Invalid GK score/minutes'))
        else:
            # Non-GK players
            if is_valid_player(player_name, row['club'], row['weighted_score'], row['role'], minutes_dict):
                players.append(player_info)
            else:
                skipped_players.append((player_name, row['club'], row['role'], 
                                      row['weighted_score'], 'Invalid score/minutes'))
    
    print(f"\nSkipped {len(skipped_players)} invalid players")
    
    # Sort players by score within each position
    positions = {
        'GK': sorted([p for p in players if p['role'] == 'GK'], key=lambda x: x['score'], reverse=True),
        'DEF': sorted([p for p in players if p['role'] == 'DEF'], key=lambda x: x['score'], reverse=True),
        'MID': sorted([p for p in players if p['role'] == 'MID'], key=lambda x: x['score'], reverse=True),
        'FWD': sorted([p for p in players if p['role'] == 'FWD'], key=lambda x: x['score'], reverse=True)
    }
    
    # Get all GKs for backup selection (both main and backup GKs)
    all_gks_for_backup = [p for p in players if p['role'] == 'GK']
    
    # Separate main GKs from backup GKs for starting XI
    main_gks_only = [p for p in positions['GK'] if p['score'] >= 2.0]
    
    print(f"\nPlayers by position (validated):")
    print(f"GK: {len(main_gks_only)} main GKs, {len(all_gks_for_backup)} total")
    print(f"DEF: {len(positions['DEF'])}")
    print(f"MID: {len(positions['MID'])}")
    print(f"FWD: {len(positions['FWD'])}")
    
    # Define formations
    formations = [
        {'name': '3-4-3', 'GK': 1, 'DEF': 3, 'MID': 4, 'FWD': 3},
        {'name': '3-5-2', 'GK': 1, 'DEF': 3, 'MID': 5, 'FWD': 2},
        {'name': '4-4-2', 'GK': 1, 'DEF': 4, 'MID': 4, 'FWD': 2},
        {'name': '4-3-3', 'GK': 1, 'DEF': 4, 'MID': 3, 'FWD': 3},
        {'name': '5-3-2', 'GK': 1, 'DEF': 5, 'MID': 3, 'FWD': 2}
    ]
    
    teams = []
    teams_set = set()  # Track unique teams
    
    # We'll build teams with different player combinations
    # Then select the best captain from each team
    
    print(f"\nGenerating teams with optimal captain selection...")
    
    # Try different combinations
    for formation in formations:
        # Try different GK options
        for gk_idx, starting_gk in enumerate(main_gks_only[:15]):
            
            # Try with different defensive combinations
            for def_start in range(0, min(10, len(positions['DEF']) - formation['DEF'])):
                
                # Try different midfield starts
                for mid_start in range(0, min(10, len(positions['MID']) - formation['MID'])):
                    
                    # Try different forward starts
                    for fwd_start in range(0, min(5, len(positions['FWD']) - formation['FWD'])):
                        
                        # Initialize team
                        team = {
                            'players': [],
                            'bench': [],
                            'formation': formation['name'],
                            'cost': 0
                        }
                        
                        team_counts = {}
                        
                        # Add GK
                        team['players'].append(starting_gk)
                        team['cost'] += starting_gk['price']
                        team_counts[starting_gk['club']] = 1
                        
                        # Fill remaining positions
                        for pos_name, needed in formation.items():
                            if pos_name == 'name' or pos_name == 'GK':
                                continue
                            
                            # Get candidates for this position
                            if pos_name == 'DEF':
                                candidates = positions[pos_name][def_start:def_start+30]
                            elif pos_name == 'MID':
                                candidates = positions[pos_name][mid_start:mid_start+30]
                            elif pos_name == 'FWD':
                                candidates = positions[pos_name][fwd_start:fwd_start+30]
                            else:
                                candidates = positions[pos_name][:40]
                            
                            added = 0
                            for player in candidates:
                                if added >= needed:
                                    break
                                
                                # Skip if already in team
                                if any(p['name'] == player['name'] for p in team['players']):
                                    continue
                                
                                # Check team limit (strict 3 player limit)
                                if team_counts.get(player['club'], 0) >= 3:
                                    continue
                                
                                # Check budget (leave room for bench)
                                if team['cost'] + player['price'] > 82:
                                    continue
                                
                                team['players'].append(player)
                                team['cost'] += player['price']
                                team_counts[player['club']] = team_counts.get(player['club'], 0) + 1
                                added += 1
                        
                        # Check if valid starting XI
                        if len(team['players']) != 11:
                            continue
                        
                        # Build bench (1 GK + 3 outfield)
                        bench_added = 0
                        bench_gk = None
                        
                        # First, try to find backup GK
                        if starting_gk:
                            backup_gk = find_backup_gk(starting_gk, all_gks_for_backup, team_counts, minutes_dict=minutes_dict)
                            if backup_gk:
                                bench_gk = backup_gk
                                team['bench'].append(backup_gk)
                                team['cost'] += backup_gk['price']
                                # ALWAYS increment team count
                                team_counts[backup_gk['club']] = team_counts.get(backup_gk['club'], 0) + 1
                                bench_added += 1
                        
                        # Cheap outfield players for rest of bench
                        all_cheap = []
                        for role in ['DEF', 'MID', 'FWD']:
                            cheap_players = [p for p in positions[role] if p['price'] <= 5.5]
                            all_cheap.extend(cheap_players)
                        
                        # Sort by price (cheapest first)
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
                        
                        # Verify 3 player per team constraint
                        constraint_violated = False
                        for club, count in team_counts.items():
                            if count > 3:
                                constraint_violated = True
                                break
                        
                        if constraint_violated:
                            continue
                        
                        # Find the best captain (highest scorer in the team)
                        best_captain = find_best_captain(team['players'])
                        team['captain'] = best_captain['name']
                        
                        # Calculate scores with the optimal captain
                        team['starting_score'] = calculate_team_score(team['players'], best_captain['name'])
                        team['total_score'] = team['starting_score']
                        
                        # Create a unique identifier for the team
                        player_names = sorted([p['name'] for p in team['players']])
                        team_id = '-'.join(player_names)
                        
                        # Only add if this is a unique team
                        if team_id not in teams_set:
                            teams_set.add(team_id)
                            teams.append(team)
                        
                        if len(teams) >= num_teams:
                            break
                    
                    if len(teams) >= num_teams:
                        break
                
                if len(teams) >= num_teams:
                    break
            
            if len(teams) >= num_teams:
                break
        
        if len(teams) >= num_teams:
            break
    
    print(f"\nGenerated {len(teams)} valid teams with optimal captains")
    
    # Convert to DataFrame with standardized output format
    rows = []
    for team in teams:
        row = {
            'captain': team['captain'],
            'formation': team['formation'],
            'budget': round(team['cost'], 1),
            'gw1_score': round(team['starting_score'], 1),
            '5gw_estimated': round(team['starting_score'] * 5.15, 1)  # Rough estimate
        }
        
        # Add starting XI
        pos_counts = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
        for player in team['players']:
            pos = player['role']
            pos_counts[pos] += 1
            idx = pos_counts[pos]
            
            row[f'{pos}{idx}'] = player['name']
            row[f'{pos}{idx}_role'] = pos
            row[f'{pos}{idx}_selected'] = 1
            row[f'{pos}{idx}_price'] = player['price']
            row[f'{pos}{idx}_score'] = player['score']
            row[f'{pos}{idx}_club'] = player['club']
        
        # Add bench
        for i, player in enumerate(team['bench']):
            row[f'BENCH{i+1}'] = player['name']
            row[f'BENCH{i+1}_role'] = player['role']
            row[f'BENCH{i+1}_selected'] = 0
            row[f'BENCH{i+1}_price'] = player['price']
            row[f'BENCH{i+1}_score'] = player['score']
            row[f'BENCH{i+1}_club'] = player['club']
        
        rows.append(row)
    
    result_df = pd.DataFrame(rows)
    
    # Sort by projected score
    result_df = result_df.sort_values('5gw_estimated', ascending=False)
    
    # Show captain distribution
    captain_counts = result_df['captain'].value_counts()
    print(f"\nCaptain distribution in top teams:")
    for captain, count in captain_counts.head(5).items():
        print(f"  {captain}: {count} teams")
    
    return result_df


if __name__ == "__main__":
    import os
    
    # Use the v4 predictions with fixed GK scores
    predictions_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/predictions_gw39_proper_v4.csv"
    
    if not os.path.exists(predictions_file):
        print(f"Error: Predictions file not found: {predictions_file}")
        exit(1)
    
    print("Building optimal FPL teams with correct captain selection...")
    teams_df = build_optimal_teams(predictions_file, num_teams=200)
    
    # Save results
    output_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v2/top_200_teams_final_v10.csv"
    teams_df.to_csv(output_file, index=False)
    print(f"\nSaved {len(teams_df)} teams to {output_file}")
    
    # Display top teams
    print("\nTop 10 teams:")
    display_cols = ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated']
    print(teams_df.head(10)[display_cols])
    
    # Show which players are captained in top teams
    print("\nTop 10 teams captain details:")
    for idx in range(min(10, len(teams_df))):
        team = teams_df.iloc[idx]
        captain_name = team['captain']
        
        # Find captain's score
        captain_score = None
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for i in range(1, 6):
                if f'{pos}{i}' in team and team[f'{pos}{i}'] == captain_name:
                    captain_score = team[f'{pos}{i}_score']
                    break
            if captain_score:
                break
        
        print(f"  Team {idx+1}: Captain = {captain_name} (score: {captain_score:.2f})")