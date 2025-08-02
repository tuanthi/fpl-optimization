#!/usr/bin/env python3
"""
Multi-gameweek optimization with captaincy and transfers
Builds teams optimized for 5 gameweeks considering:
- Captain selection (2x points)
- 1 free transfer per gameweek
- Transfer strategy over time
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict
import itertools
from typing import Dict, List, Tuple


class MultiGWOptimizer:
    def __init__(self, predictions_file: str):
        self.predictions = pd.read_csv(predictions_file)
        self.transfer_cost = 4
        self.max_players_per_team = 3
        
        # Create player lookup
        self.players = {}
        for _, row in self.predictions.iterrows():
            player_id = f"{row['first_name']} {row['last_name']} ({row['club']})"
            self.players[player_id] = {
                'role': row['role'],
                'price': row['price'],
                'score': row['weighted_score'],
                'club': row['club']
            }
    
    def simulate_5_gameweeks(self, starting_xi: List[str], bench: List[str], 
                           budget_remaining: float) -> Dict:
        """Simulate 5 gameweeks with optimal transfers and captains"""
        
        results = {
            'gw_scores': [],
            'total_score': 0,
            'transfers_made': 0,
            'final_team_value': 0
        }
        
        current_xi = starting_xi.copy()
        current_bench = bench.copy()
        current_budget = budget_remaining
        
        for gw in range(1, 6):
            # Find best captain
            best_captain_idx = 0
            best_captain_score = 0
            
            for i, player_id in enumerate(current_xi):
                if player_id in self.players:
                    score = self.players[player_id]['score']
                    if score > best_captain_score:
                        best_captain_score = score
                        best_captain_idx = i
            
            # Calculate base score with captain
            gw_score = 0
            for i, player_id in enumerate(current_xi):
                if player_id in self.players:
                    score = self.players[player_id]['score']
                    if i == best_captain_idx:
                        gw_score += score * 2  # Captain bonus
                    else:
                        gw_score += score
            
            # Consider one free transfer
            if gw < 5:  # Don't transfer in last gameweek
                best_transfer = self.find_best_transfer(
                    current_xi, current_bench, current_budget
                )
                
                if best_transfer and best_transfer['improvement'] > 0.5:
                    # Make the transfer
                    idx = best_transfer['out_idx']
                    current_xi[idx] = best_transfer['in_player']
                    current_budget -= best_transfer['cost_diff']
                    results['transfers_made'] += 1
                    
                    # Recalculate score after transfer
                    gw_score = 0
                    best_captain_score = 0
                    best_captain_idx = 0
                    
                    for i, player_id in enumerate(current_xi):
                        if player_id in self.players:
                            score = self.players[player_id]['score']
                            if score > best_captain_score:
                                best_captain_score = score
                                best_captain_idx = i
                    
                    for i, player_id in enumerate(current_xi):
                        if player_id in self.players:
                            score = self.players[player_id]['score']
                            if i == best_captain_idx:
                                gw_score += score * 2
                            else:
                                gw_score += score
            
            results['gw_scores'].append(gw_score)
            results['total_score'] += gw_score
        
        # Calculate final team value
        for player_id in current_xi + current_bench:
            if player_id in self.players:
                results['final_team_value'] += self.players[player_id]['price']
        
        return results
    
    def find_best_transfer(self, current_xi: List[str], bench: List[str], 
                          budget: float) -> Dict:
        """Find the best single transfer"""
        best_transfer = None
        best_improvement = -float('inf')
        
        # Count current team distribution
        team_counts = defaultdict(int)
        for player_id in current_xi + bench:
            if player_id in self.players:
                team_counts[self.players[player_id]['club']] += 1
        
        # Try replacing each player
        for out_idx, out_player in enumerate(current_xi):
            if out_player not in self.players:
                continue
            
            out_data = self.players[out_player]
            out_role = out_data['role']
            out_price = out_data['price']
            out_score = out_data['score']
            out_club = out_data['club']
            
            # Find potential replacements
            for in_player, in_data in self.players.items():
                # Skip if same player or wrong role
                if in_player == out_player or in_data['role'] != out_role:
                    continue
                
                # Skip if already in team
                if in_player in current_xi or in_player in bench:
                    continue
                
                # Check budget
                cost_diff = in_data['price'] - out_price
                if cost_diff > budget:
                    continue
                
                # Check team constraint
                in_club = in_data['club']
                new_team_count = team_counts[in_club] + (0 if in_club == out_club else 1)
                if new_team_count > self.max_players_per_team:
                    continue
                
                # Calculate improvement
                score_improvement = in_data['score'] - out_score
                
                # Bonus if new player could be captain
                current_best_captain_score = max(
                    self.players[p]['score'] for p in current_xi if p in self.players
                )
                if in_data['score'] > current_best_captain_score:
                    # New captain would add extra value
                    captain_bonus = in_data['score'] - current_best_captain_score
                    score_improvement += captain_bonus
                
                if score_improvement > best_improvement:
                    best_improvement = score_improvement
                    best_transfer = {
                        'out_idx': out_idx,
                        'out_player': out_player,
                        'in_player': in_player,
                        'cost_diff': cost_diff,
                        'improvement': score_improvement
                    }
        
        return best_transfer


def build_team_for_multi_gw(players_df: pd.DataFrame, formation: Tuple[int, int, int, int],
                           must_have_players: List[str] = None) -> Dict:
    """Build a team optimized for multiple gameweeks"""
    
    # Separate by position
    gks = players_df[players_df['role'] == 'GK'].to_dict('records')
    defs = players_df[players_df['role'] == 'DEF'].to_dict('records')
    mids = players_df[players_df['role'] == 'MID'].to_dict('records')
    fwds = players_df[players_df['role'] == 'FWD'].to_dict('records')
    
    # Sort by score
    for pool in [gks, defs, mids, fwds]:
        pool.sort(key=lambda x: x['weighted_score'], reverse=True)
    
    # Build team
    team_counts = defaultdict(int)
    starting_xi = []
    total_cost = 0
    
    # Add must-have players first
    if must_have_players:
        for player_name in must_have_players:
            # Try different matching approaches
            player_data = players_df[players_df['full_name'].str.contains(player_name, case=False, na=False)]
            if len(player_data) == 0:
                # Try partial match
                player_data = players_df[players_df['last_name'].str.contains(player_name.split()[-1], case=False, na=False)]
            
            if len(player_data) > 0:
                player = player_data.iloc[0]
                player_id = f"{player['full_name']} ({player['club']})"
                starting_xi.append(player_id)
                total_cost += player['price']
                team_counts[player['club']] += 1
            else:
                print(f"Warning: Could not find player {player_name}")
    
    # Fill remaining positions
    positions_needed = {
        'GK': formation[0],
        'DEF': formation[1], 
        'MID': formation[2],
        'FWD': formation[3]
    }
    
    # Count what we already have
    for player_id in starting_xi:
        for _, player in players_df.iterrows():
            if f"{player['full_name']} ({player['club']})" == player_id:
                positions_needed[player['role']] -= 1
                break
    
    # Add players by position
    for role, pool in [('GK', gks), ('DEF', defs), ('MID', mids), ('FWD', fwds)]:
        added = 0
        for player in pool:
            if added >= positions_needed[role]:
                break
            
            player_id = f"{player['full_name']} ({player['club']})"
            
            # Skip if already in team
            if player_id in starting_xi:
                continue
            
            # Check constraints
            if team_counts[player['club']] >= 3:
                continue
            
            if total_cost + player['price'] > 85:  # Leave room for bench
                continue
            
            starting_xi.append(player_id)
            total_cost += player['price']
            team_counts[player['club']] += 1
            added += 1
    
    # Add cheap bench
    bench = []
    bench_pools = {
        'GK': [p for p in gks if p['price'] <= 4.5],
        'DEF': [p for p in defs if p['price'] <= 4.5],
        'MID': [p for p in mids if p['price'] <= 5.0],
        'FWD': [p for p in fwds if p['price'] <= 5.0]
    }
    
    # Need 1 GK, then 3 outfield
    for role in ['GK', 'DEF', 'DEF', 'MID']:
        for player in bench_pools[role]:
            player_id = f"{player['full_name']} ({player['club']})"
            
            if player_id not in starting_xi and player_id not in bench:
                if team_counts[player['club']] < 3:
                    bench.append(player_id)
                    total_cost += player['price']
                    team_counts[player['club']] += 1
                    break
    
    if total_cost > 100 or len(starting_xi) != 11 or len(bench) < 4:
        return None
    
    return {
        'starting_xi': starting_xi,
        'bench': bench[:4],
        'total_cost': total_cost,
        'budget_remaining': 100 - total_cost
    }


def create_top_teams_multi_gw(predictions_file: str, output_file: str, num_teams: int = 200):
    """Create top teams optimized for 5 gameweeks"""
    
    # Load predictions
    df = pd.read_csv(predictions_file)
    df['full_name'] = df['first_name'] + ' ' + df['last_name']
    
    # Get unique players
    players_df = df.drop_duplicates(subset=['full_name', 'club']).copy()
    
    optimizer = MultiGWOptimizer(predictions_file)
    
    formations = [
        (1, 3, 5, 2),  # 3-5-2 
        (1, 3, 4, 3),  # 3-4-3
        (1, 4, 4, 2),  # 4-4-2
        (1, 4, 3, 3),  # 4-3-3
        (1, 5, 3, 2),  # 5-3-2
    ]
    
    # Key players to build around
    key_players = [
        'Mohamed Salah',
        'Bryan Mbeumo', 
        'Cole Palmer',
        'Alexander Isak',
        'Chris Wood',
        'Erling Haaland'
    ]
    
    all_teams = []
    team_signatures = set()
    
    print("Building teams optimized for 5 gameweeks...")
    
    # Strategy 1: Build around key players
    for key_player in key_players:
        print(f"Building teams around {key_player}...")
        for formation in formations:
            team_data = build_team_for_multi_gw(
                players_df, formation, must_have_players=[key_player]
            )
            
            if team_data:
                # Simulate 5 gameweeks
                results = optimizer.simulate_5_gameweeks(
                    team_data['starting_xi'],
                    team_data['bench'],
                    team_data['budget_remaining']
                )
                
                # Create team record
                team = {
                    'key_player': key_player,
                    'formation': f"{formation[1]}-{formation[2]}-{formation[3]}",
                    'gw1_score': results['gw_scores'][0],
                    '5gw_total_score': results['total_score'],
                    'transfers_made': results['transfers_made'],
                    'initial_cost': team_data['total_cost']
                }
                
                # Add player details
                for i, player_id in enumerate(team_data['starting_xi']):
                    if player_id in optimizer.players:
                        player = optimizer.players[player_id]
                        role = player['role']
                        # Find position number
                        role_count = sum(1 for j in range(i) if 
                                       team_data['starting_xi'][j] in optimizer.players and
                                       optimizer.players[team_data['starting_xi'][j]]['role'] == role) + 1
                        
                        key = f"{role}{role_count}"
                        team[key] = player_id
                        team[f"{key}_selected"] = 1
                        team[f"{key}_price"] = player['price']
                        team[f"{key}_score"] = player['score']
                
                # Add bench
                pos_counts = {'GK': 2, 'DEF': 6, 'MID': 6, 'FWD': 4}
                for player_id in team_data['bench']:
                    if player_id in optimizer.players:
                        player = optimizer.players[player_id]
                        role = player['role']
                        key = f"{role}{pos_counts[role]}"
                        team[key] = player_id
                        team[f"{key}_selected"] = 0
                        team[f"{key}_price"] = player['price']
                        team[f"{key}_score"] = player['score']
                        pos_counts[role] += 1
                
                # Create signature
                all_players = sorted(team_data['starting_xi'] + team_data['bench'])
                signature = '|'.join(all_players)
                
                if signature not in team_signatures:
                    all_teams.append(team)
                    team_signatures.add(signature)
    
    # Strategy 2: Balanced teams
    attempts = 0
    while len(all_teams) < num_teams and attempts < 500:
        attempts += 1
        
        formation = formations[attempts % len(formations)]
        team_data = build_team_for_multi_gw(players_df, formation)
        
        if team_data:
            results = optimizer.simulate_5_gameweeks(
                team_data['starting_xi'],
                team_data['bench'], 
                team_data['budget_remaining']
            )
            
            # Find best player in team
            best_player = max(team_data['starting_xi'], 
                            key=lambda p: optimizer.players.get(p, {}).get('score', 0))
            
            team = {
                'key_player': best_player.split(' (')[0],
                'formation': f"{formation[1]}-{formation[2]}-{formation[3]}",
                'gw1_score': results['gw_scores'][0],
                '5gw_total_score': results['total_score'],
                'transfers_made': results['transfers_made'],
                'initial_cost': team_data['total_cost']
            }
            
            # Add players (same as above)
            pos_counts = defaultdict(int)
            for i, player_id in enumerate(team_data['starting_xi'] + team_data['bench']):
                if player_id in optimizer.players:
                    player = optimizer.players[player_id]
                    role = player['role']
                    pos_counts[role] += 1
                    
                    key = f"{role}{pos_counts[role]}"
                    team[key] = player_id
                    team[f"{key}_selected"] = 1 if i < 11 else 0
                    team[f"{key}_price"] = player['price']
                    team[f"{key}_score"] = player['score']
            
            signature = '|'.join(sorted(team_data['starting_xi'] + team_data['bench']))
            if signature not in team_signatures:
                all_teams.append(team)
                team_signatures.add(signature)
    
    # Convert to DataFrame and sort
    if not all_teams:
        print("No valid teams found!")
        return None
    
    teams_df = pd.DataFrame(all_teams)
    teams_df = teams_df.sort_values('5gw_total_score', ascending=False)
    teams_df = teams_df.head(num_teams)
    
    # Save
    teams_df.to_csv(output_file, index=False)
    
    print(f"\nCreated {len(teams_df)} teams optimized for 5 gameweeks")
    print(f"\nTop 10 teams:")
    print("-" * 100)
    print(f"{'Rank':<5} {'Key Player':<20} {'Formation':<10} {'GW1 Score':<10} {'5GW Total':<10} {'Transfers':<10}")
    print("-" * 100)
    
    for idx, team in teams_df.head(10).iterrows():
        print(f"{idx+1:<5} {team['key_player']:<20} {team['formation']:<10} "
              f"{team['gw1_score']:<10.1f} {team['5gw_total_score']:<10.1f} "
              f"{team['transfers_made']:<10}")
    
    return teams_df


def main():
    predictions_file = "data/cached_merged_2024_2025_v2/predictions_gw39_proper.csv"
    output_file = "data/cached_merged_2024_2025_v2/top_200_teams_multi_gw.csv"
    
    create_top_teams_multi_gw(predictions_file, output_file, num_teams=200)


if __name__ == "__main__":
    main()