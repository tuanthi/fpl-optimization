#!/usr/bin/env python3
"""
Final version with fixed GK hierarchy:
- Uses corrected GK scores where backups are heavily penalized
- Ensures only main GKs can be selected as starting GKs
- Maintains GK pairing strategy for bench
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
    Find the best backup GK, preferring same team as starting GK
    
    Strategy:
    1. First try to find backup from same team (4.0-4.5m)
    2. If not available, find cheapest valid GK from another team
    """
    starting_team = starting_gk['club']
    
    # First, try to find backup from same team
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
        print(f"  GK Pairing: {starting_gk['name']} with backup {backup['name']} (same team: {starting_team})")
        return backup
    
    # If no same-team backup available, find cheapest backup from another team
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
    """Build teams with fixed GK hierarchy and standardized output format"""
    
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
                    skipped_players.append((player_name, row['club'], row['weighted_score'], 'Backup GK'))
            else:
                skipped_players.append((player_name, row['club'], row['weighted_score'], 'Invalid'))
        else:
            # Non-GK players
            if is_valid_player(player_name, row['club'], row['weighted_score'], row['role'], minutes_dict):
                players.append(player_info)
            else:
                skipped_players.append((player_name, row['club'], row['weighted_score'], 'Invalid'))
    
    print(f"\nFiltered out {len(skipped_players)} invalid/backup players")
    
    # Also create a list of ALL GKs (including low-scoring ones) for backup pairing
    all_gks_for_backup = []
    gk_rows = df[df['role'] == 'GK']
    for _, row in gk_rows.iterrows():
        player_name = f"{row['first_name']} {row['last_name']}"
        gk_info = {
            'name': player_name,
            'full_id': f"{player_name} ({row['club']})",
            'club': row['club'],
            'role': 'GK',
            'price': row['price'],
            'score': row['weighted_score']
        }
        all_gks_for_backup.append(gk_info)
    
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
    
    # Verify GK hierarchy
    print("\nTop GKs by score (should be main GKs only):")
    for i, gk in enumerate(positions['GK'][:10]):
        print(f"  {i+1}. {gk['name']} ({gk['club']}): £{gk['price']}m, score: {gk['score']:.2f}")
    
    teams = []
    
    # Get top scorers for captaincy
    top_scorers = []
    for role in ['MID', 'FWD']:
        role_players = [p for p in players if p['role'] == role]
        top_scorers.extend(role_players[:25])
    
    # Also add some top defenders
    def_players = [p for p in players if p['role'] == 'DEF']
    top_scorers.extend(def_players[:10])
    
    # Sort by score and get unique captains
    top_scorers.sort(key=lambda x: x['score'], reverse=True)
    seen = set()
    priority_captains = []
    for p in top_scorers:
        if p['name'] not in seen and p['score'] > 4.0:
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
    
    print("\nBuilding teams with captain optimization and GK pairing...")
    
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
                
                # Add captain first (unless captain is GK)
                if captain_pos != 'GK':
                    team['players'].append(captain)
                    team['cost'] += captain['price']
                    team_counts[captain['club']] = 1
                
                # Fill remaining positions
                for pos_name, needed in formation.items():
                    if pos_name == 'name':
                        continue
                    
                    role = pos_name.upper()
                    if role == captain_pos and captain_pos != 'GK':
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
                        if team['cost'] + player['price'] > 82:
                            continue
                        
                        team['players'].append(player)
                        team['cost'] += player['price']
                        team_counts[player['club']] = team_counts.get(player['club'], 0) + 1
                        added += 1
                
                # Check if valid starting XI
                if len(team['players']) != 11:
                    continue
                
                # Find the starting GK for pairing strategy
                starting_gk = None
                for player in team['players']:
                    if player['role'] == 'GK':
                        starting_gk = player
                        break
                
                # Add bench with GK pairing strategy
                bench_added = 0
                bench_gk = None
                
                # First, try to find backup GK from same team
                if starting_gk:
                    backup_gk = find_backup_gk(starting_gk, all_gks_for_backup, team_counts, minutes_dict=minutes_dict)
                    if backup_gk:
                        bench_gk = backup_gk
                        team['bench'].append(backup_gk)
                        team['cost'] += backup_gk['price']
                        if backup_gk['club'] == starting_gk['club']:
                            # Same team, don't increase team count
                            pass
                        else:
                            team_counts[backup_gk['club']] = team_counts.get(backup_gk['club'], 0) + 1
                        bench_added += 1
                
                # Cheap outfield players for rest of bench
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
                
                # Store bench GK separately for output formatting
                team['bench_gk'] = bench_gk
                
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
    
    # Convert to DataFrame format with standardized column order
    rows = []
    for i, team in enumerate(teams[:num_teams]):
        row = {}
        
        # Key info columns (exact order)
        row['captain'] = team['captain']
        row['formation'] = team['formation']
        row['budget'] = round(team['cost'], 1)
        row['gw1_score'] = round(team['captain_score'], 1)
        row['5gw_estimated'] = round(team['5gw_score'], 1)
        
        # Separate players by position
        selected_players = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
        
        # Categorize starting XI
        for player in team['players']:
            selected_players[player['role']].append(player)
        
        # Add GK1 (starting GK)
        if selected_players['GK']:
            gk1 = selected_players['GK'][0]
            row['GK1'] = gk1['full_id']
            row['GK1_role'] = 'GK'
            row['GK1_selected'] = 1
            row['GK1_price'] = gk1['price']
            row['GK1_score'] = gk1['score']
        
        # Add GK2 (bench GK)
        if team.get('bench_gk'):
            gk2 = team['bench_gk']
            row['GK2'] = gk2['full_id']
            row['GK2_role'] = 'GK'
            row['GK2_selected'] = 0
            row['GK2_price'] = gk2['price']
            row['GK2_score'] = gk2['score']
        
        # Add DEF1-DEF5
        for i in range(1, 6):
            if i <= len(selected_players['DEF']):
                player = selected_players['DEF'][i-1]
                row[f'DEF{i}'] = player['full_id']
                row[f'DEF{i}_role'] = 'DEF'
                row[f'DEF{i}_selected'] = 1
                row[f'DEF{i}_price'] = player['price']
                row[f'DEF{i}_score'] = player['score']
            else:
                row[f'DEF{i}'] = None
                row[f'DEF{i}_role'] = None
                row[f'DEF{i}_selected'] = None
                row[f'DEF{i}_price'] = None
                row[f'DEF{i}_score'] = None
        
        # Add MID1-MID5
        for i in range(1, 6):
            if i <= len(selected_players['MID']):
                player = selected_players['MID'][i-1]
                row[f'MID{i}'] = player['full_id']
                row[f'MID{i}_role'] = 'MID'
                row[f'MID{i}_selected'] = 1
                row[f'MID{i}_price'] = player['price']
                row[f'MID{i}_score'] = player['score']
            else:
                row[f'MID{i}'] = None
                row[f'MID{i}_role'] = None
                row[f'MID{i}_selected'] = None
                row[f'MID{i}_price'] = None
                row[f'MID{i}_score'] = None
        
        # Add FWD1-FWD3
        for i in range(1, 4):
            if i <= len(selected_players['FWD']):
                player = selected_players['FWD'][i-1]
                row[f'FWD{i}'] = player['full_id']
                row[f'FWD{i}_role'] = 'FWD'
                row[f'FWD{i}_selected'] = 1
                row[f'FWD{i}_price'] = player['price']
                row[f'FWD{i}_score'] = player['score']
            else:
                row[f'FWD{i}'] = None
                row[f'FWD{i}_role'] = None
                row[f'FWD{i}_selected'] = None
                row[f'FWD{i}_price'] = None
                row[f'FWD{i}_score'] = None
        
        rows.append(row)
    
    # Create DataFrame
    if rows:
        df = pd.DataFrame(rows)
        
        # Define exact column order
        column_order = ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated']
        
        # Add GK columns
        for i in range(1, 3):
            for suffix in ['', '_role', '_selected', '_price', '_score']:
                column_order.append(f'GK{i}{suffix}')
        
        # Add DEF columns
        for i in range(1, 6):
            for suffix in ['', '_role', '_selected', '_price', '_score']:
                column_order.append(f'DEF{i}{suffix}')
        
        # Add MID columns
        for i in range(1, 6):
            for suffix in ['', '_role', '_selected', '_price', '_score']:
                column_order.append(f'MID{i}{suffix}')
        
        # Add FWD columns
        for i in range(1, 4):
            for suffix in ['', '_role', '_selected', '_price', '_score']:
                column_order.append(f'FWD{i}{suffix}')
        
        # Ensure all columns exist
        for col in column_order:
            if col not in df.columns:
                df[col] = None
        
        # Reorder columns
        df = df[column_order]
        
        return df
    else:
        return pd.DataFrame()


def main():
    predictions_file = "../data/cached_merged_2024_2025_v2/predictions_gw39_proper_v4.csv"  # Using v4 with fixed GK scores
    output_file = "../data/cached_merged_2024_2025_v2/top_200_teams_final_v8.csv"
    
    print("Creating optimized teams with fixed GK hierarchy...")
    
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
        
        # Show GK pairings in top teams
        print("\nGK Pairings in top 10 teams:")
        same_team_count = 0
        for idx, team in teams_df.head(10).iterrows():
            gk1 = team['GK1'] if pd.notna(team['GK1']) else 'N/A'
            gk2 = team['GK2'] if pd.notna(team['GK2']) else 'N/A'
            
            # Check if same team
            if gk1 != 'N/A' and gk2 != 'N/A':
                gk1_team = gk1.split('(')[1].split(')')[0] if '(' in gk1 else ''
                gk2_team = gk2.split('(')[1].split(')')[0] if '(' in gk2 else ''
                same_team = "✓ Same team" if gk1_team == gk2_team else "Different teams"
                if gk1_team == gk2_team:
                    same_team_count += 1
                print(f"  Team {idx+1}: {gk1} | Bench: {gk2} - {same_team}")
        
        print(f"\nSame-team GK pairings: {same_team_count}/10")
    else:
        print("Failed to create teams!")


if __name__ == "__main__":
    main()