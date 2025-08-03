#!/usr/bin/env python3
"""
Generate FPL teams with EXACTLY 15 players: 2 GK, 5 DEF, 5 MID, 3 FWD
Following official FPL squad requirements
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
        'Joe Hodge',  # Transferred to CD Tondela
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
    """Build teams ensuring EXACTLY 15 players with correct distribution"""
    
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
    
    # Show top players
    print("\nTop players by position:")
    for pos in ['MID', 'FWD']:
        print(f"\n{pos}:")
        for i, player in enumerate(positions[pos][:5]):
            print(f"  {i+1}. {player['name']} ({player['club']}): {player['score']:.2f} - £{player['price']}m")
    
    # Define formations
    formations = [
        {'name': '3-4-3', 'GK': 1, 'DEF': 3, 'MID': 4, 'FWD': 3},
        {'name': '3-5-2', 'GK': 1, 'DEF': 3, 'MID': 5, 'FWD': 2},
        {'name': '4-4-2', 'GK': 1, 'DEF': 4, 'MID': 4, 'FWD': 2},
        {'name': '4-3-3', 'GK': 1, 'DEF': 4, 'MID': 3, 'FWD': 3},
        {'name': '5-3-2', 'GK': 1, 'DEF': 5, 'MID': 3, 'FWD': 2},
        {'name': '5-2-3', 'GK': 1, 'DEF': 5, 'MID': 2, 'FWD': 3},
        {'name': '4-5-1', 'GK': 1, 'DEF': 4, 'MID': 5, 'FWD': 1},
    ]
    
    teams = []
    teams_set = set()  # Track unique teams
    
    # Identify must-have players (top scorers that should be in most teams)
    must_have_players = []
    
    # Get top MID (likely Salah)
    if positions['MID'] and positions['MID'][0]['score'] > 8.0:
        must_have_players.append(positions['MID'][0])
    
    print(f"\nGenerating teams with must-have players: {[p['name'] for p in must_have_players]}")
    
    # Try different combinations
    for formation in formations:
        # Try different GK options
        for gk_idx, starting_gk in enumerate(main_gks_only[:15]):
            
            # Try including/excluding second best MID
            for include_second_mid in [True, False]:
                
                # Try different defensive combinations
                for def_start in range(0, min(10, len(positions['DEF']) - 5)):  # Need at least 5 DEF total
                    
                    # Initialize team
                    team = {
                        'players': [],
                        'bench': [],
                        'formation': formation['name'],
                        'cost': 0
                    }
                    
                    team_counts = {}
                    positions_filled = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
                    
                    # Add starting GK
                    team['players'].append(starting_gk)
                    team['cost'] += starting_gk['price']
                    team_counts[starting_gk['club']] = 1
                    positions_filled['GK'] = 1
                    
                    # Add must-have players first
                    for must_have in must_have_players:
                        if team_counts.get(must_have['club'], 0) < 3:
                            team['players'].append(must_have)
                            team['cost'] += must_have['price']
                            team_counts[must_have['club']] = team_counts.get(must_have['club'], 0) + 1
                            positions_filled[must_have['role']] += 1
                    
                    # Fill remaining starting XI positions
                    for pos_name, needed in formation.items():
                        if pos_name == 'name' or pos_name == 'GK':
                            continue
                        
                        # Account for must-have players already added
                        already_added = positions_filled[pos_name]
                        needed_for_xi = needed - already_added
                        
                        # Get candidates for this position
                        if pos_name == 'DEF':
                            candidates = positions[pos_name][def_start:def_start+30]
                        elif pos_name == 'MID':
                            # Start from different points to get variety
                            if include_second_mid and len(positions[pos_name]) > 1:
                                candidates = [positions[pos_name][1]] + positions[pos_name][2:30]
                            else:
                                candidates = positions[pos_name][1:30]  # Skip first as it's must-have
                        else:
                            candidates = positions[pos_name][:30]
                        
                        added = 0
                        for player in candidates:
                            if added >= needed_for_xi:
                                break
                            
                            # Skip if already in team
                            if any(p['name'] == player['name'] for p in team['players']):
                                continue
                            
                            # Check team limit (strict 3 player limit)
                            if team_counts.get(player['club'], 0) >= 3:
                                continue
                            
                            # Check budget (leave room for bench - at least 17m)
                            if team['cost'] + player['price'] > 83:
                                continue
                            
                            team['players'].append(player)
                            team['cost'] += player['price']
                            team_counts[player['club']] = team_counts.get(player['club'], 0) + 1
                            positions_filled[pos_name] += 1
                            added += 1
                    
                    # Check if valid starting XI
                    if len(team['players']) != 11:
                        continue
                    
                    # Build bench to complete squad (15 players total)
                    # Need: 1 more GK, and enough players to make 5 DEF, 5 MID, 3 FWD total
                    
                    # First, find backup GK
                    backup_gk = find_backup_gk(starting_gk, all_gks_for_backup, team_counts, minutes_dict=minutes_dict)
                    if backup_gk:
                        team['bench'].append(backup_gk)
                        team['cost'] += backup_gk['price']
                        team_counts[backup_gk['club']] = team_counts.get(backup_gk['club'], 0) + 1
                        positions_filled['GK'] = 2  # Now have 2 GKs
                    else:
                        continue  # Can't find backup GK, skip this team
                    
                    # Calculate how many more of each position we need
                    def_needed = 5 - positions_filled['DEF']
                    mid_needed = 5 - positions_filled['MID']
                    fwd_needed = 3 - positions_filled['FWD']
                    
                    # Get cheap players for bench
                    bench_candidates = []
                    
                    # Add required DEFs
                    if def_needed > 0:
                        cheap_defs = [p for p in positions['DEF'] if p['price'] <= 5.0 
                                     and not any(tp['name'] == p['name'] for tp in team['players'])
                                     and team_counts.get(p['club'], 0) < 3]
                        cheap_defs.sort(key=lambda x: x['price'])
                        bench_candidates.extend(cheap_defs[:def_needed * 2])  # Get extras in case some don't fit
                    
                    # Add required MIDs
                    if mid_needed > 0:
                        cheap_mids = [p for p in positions['MID'] if p['price'] <= 5.5 
                                     and not any(tp['name'] == p['name'] for tp in team['players'])
                                     and team_counts.get(p['club'], 0) < 3]
                        cheap_mids.sort(key=lambda x: x['price'])
                        bench_candidates.extend(cheap_mids[:mid_needed * 2])
                    
                    # Add required FWDs
                    if fwd_needed > 0:
                        cheap_fwds = [p for p in positions['FWD'] if p['price'] <= 5.5 
                                     and not any(tp['name'] == p['name'] for tp in team['players'])
                                     and team_counts.get(p['club'], 0) < 3]
                        cheap_fwds.sort(key=lambda x: x['price'])
                        bench_candidates.extend(cheap_fwds[:fwd_needed * 2])
                    
                    # Sort all bench candidates by price
                    bench_candidates.sort(key=lambda x: x['price'])
                    
                    # Add bench players to meet position requirements
                    for player in bench_candidates:
                        if len(team['bench']) >= 4:  # 1 GK + 3 outfield = 4 bench
                            break
                        
                        role = player['role']
                        
                        # Check if we need this position
                        if role == 'DEF' and positions_filled['DEF'] >= 5:
                            continue
                        if role == 'MID' and positions_filled['MID'] >= 5:
                            continue
                        if role == 'FWD' and positions_filled['FWD'] >= 3:
                            continue
                        
                        # Check team limit
                        if team_counts.get(player['club'], 0) >= 3:
                            continue
                        
                        # Check budget
                        if team['cost'] + player['price'] > 100:
                            continue
                        
                        team['bench'].append(player)
                        team['cost'] += player['price']
                        team_counts[player['club']] = team_counts.get(player['club'], 0) + 1
                        positions_filled[role] += 1
                    
                    # Verify we have exactly 15 players with correct distribution
                    if len(team['players']) + len(team['bench']) != 15:
                        continue
                    
                    if positions_filled['GK'] != 2 or positions_filled['DEF'] != 5 or \
                       positions_filled['MID'] != 5 or positions_filled['FWD'] != 3:
                        continue
                    
                    # Verify budget
                    if team['cost'] > 100:
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
    
    print(f"\nGenerated {len(teams)} valid teams with correct 15-player squads")
    
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
        
        # Count positions in starting XI and bench
        pos_counts = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
        bench_pos_counts = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
        
        # Add starting XI
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
            bench_pos_counts[player['role']] += 1
        
        # Add total player counts for verification
        row['total_gk'] = pos_counts['GK'] + bench_pos_counts['GK']
        row['total_def'] = pos_counts['DEF'] + bench_pos_counts['DEF']
        row['total_mid'] = pos_counts['MID'] + bench_pos_counts['MID']
        row['total_fwd'] = pos_counts['FWD'] + bench_pos_counts['FWD']
        
        rows.append(row)
    
    result_df = pd.DataFrame(rows)
    
    # Sort by projected score
    result_df = result_df.sort_values('5gw_estimated', ascending=False)
    
    # Show captain distribution
    captain_counts = result_df['captain'].value_counts()
    print(f"\nCaptain distribution in top teams:")
    for captain, count in captain_counts.head(5).items():
        print(f"  {captain}: {count} teams")
    
    # Verify all teams have correct player counts
    print("\nVerifying player counts:")
    print(f"All teams have 2 GKs: {all(result_df['total_gk'] == 2)}")
    print(f"All teams have 5 DEFs: {all(result_df['total_def'] == 5)}")
    print(f"All teams have 5 MIDs: {all(result_df['total_mid'] == 5)}")
    print(f"All teams have 3 FWDs: {all(result_df['total_fwd'] == 3)}")
    
    return result_df


if __name__ == "__main__":
    import os
    
    # Use the v4 predictions with fixed GK scores
    predictions_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/predictions_gw39_proper_v3.csv"
    
    if not os.path.exists(predictions_file):
        print(f"Error: Predictions file not found: {predictions_file}")
        exit(1)
    
    print("Building optimal FPL teams with EXACTLY 15 players (2 GK, 5 DEF, 5 MID, 3 FWD)...")
    teams_df = build_optimal_teams(predictions_file, num_teams=200)
    
    # Save results
    output_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/top_200_teams_final_v15.csv"
    teams_df.to_csv(output_file, index=False)
    print(f"\nSaved {len(teams_df)} teams to {output_file}")
    
    # Display top teams
    print("\nTop 10 teams:")
    display_cols = ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated', 
                    'total_gk', 'total_def', 'total_mid', 'total_fwd']
    print(teams_df.head(10)[display_cols])