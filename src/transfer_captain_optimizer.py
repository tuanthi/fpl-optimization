#!/usr/bin/env python3
"""
Transfer and Captain Optimizer for FPL

This script optimizes transfers and captaincy decisions over multiple gameweeks.
- Considers captain selection (2x points for captain)
- Allows 1 free transfer per gameweek
- Additional transfers cost 4 points each
- Transfers must be same position and maintain budget/team constraints
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict
import itertools
from typing import Dict, List, Tuple, Set


class TransferOptimizer:
    def __init__(self, predictions_file: str, initial_budget_remaining: float = 0.0):
        """Initialize optimizer with predictions and constraints"""
        self.predictions = pd.read_csv(predictions_file)
        self.initial_budget_remaining = initial_budget_remaining
        self.transfer_cost = 4  # Points deduction per extra transfer
        self.max_players_per_team = 3
        
        # Create player lookup by ID
        self.player_lookup = {}
        for _, player in self.predictions.iterrows():
            player_id = f"{player['first_name']} {player['last_name']} ({player['club']})"
            self.player_lookup[player_id] = player
    
    def get_player_score(self, player_id: str, gameweek: int) -> float:
        """Get expected score for a player in a specific gameweek"""
        if player_id not in self.player_lookup:
            return 0.0
        # For now, use weighted_score as expected score for all gameweeks
        # In reality, this would vary by fixture difficulty
        return self.player_lookup[player_id]['weighted_score']
    
    def calculate_team_score(self, team: Dict[str, str], captain: str, gameweek: int) -> float:
        """Calculate total score for a team with captain"""
        total_score = 0.0
        
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for i in range(1, 6):
                player_key = f'{pos}{i}'
                if player_key in team and team.get(f'{player_key}_selected', 0) == 1:
                    player_id = team[player_key]
                    score = self.get_player_score(player_id, gameweek)
                    
                    # Double captain's score
                    if player_id == captain:
                        score *= 2
                    
                    total_score += score
        
        return total_score
    
    def get_valid_transfers(self, current_player: str, budget: float, 
                          current_team: Dict[str, str]) -> List[Tuple[str, float]]:
        """Get all valid transfer targets for a player"""
        if current_player not in self.player_lookup:
            return []
        
        current = self.player_lookup[current_player]
        current_role = current['role']
        current_price = current['price']
        
        # Count players per team
        team_counts = defaultdict(int)
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for i in range(1, 6):
                player_key = f'{pos}{i}'
                if player_key in current_team:
                    player_id = current_team[player_key]
                    if player_id in self.player_lookup:
                        club = self.player_lookup[player_id]['club']
                        if player_id != current_player:  # Don't count the player being transferred out
                            team_counts[club] += 1
        
        valid_transfers = []
        
        for _, target in self.predictions.iterrows():
            target_id = f"{target['first_name']} {target['last_name']} ({target['club']})"
            
            # Skip if same player
            if target_id == current_player:
                continue
            
            # Must be same role
            if target['role'] != current_role:
                continue
            
            # Check budget constraint
            price_diff = target['price'] - current_price
            if price_diff > budget:
                continue
            
            # Check team constraint
            if team_counts[target['club']] >= self.max_players_per_team:
                continue
            
            # Check if player already in team
            player_in_team = False
            for pos in ['GK', 'DEF', 'MID', 'FWD']:
                for i in range(1, 6):
                    if current_team.get(f'{pos}{i}') == target_id:
                        player_in_team = True
                        break
                if player_in_team:
                    break
            
            if player_in_team:
                continue
            
            valid_transfers.append((target_id, price_diff))
        
        return valid_transfers
    
    def optimize_single_gameweek(self, team: Dict[str, str], budget: float, 
                               gameweek: int, transfers_used: int = 0) -> Tuple[Dict[str, str], str, float, int]:
        """Optimize transfers and captain for a single gameweek"""
        best_team = team.copy()
        best_captain = None
        best_score = -float('inf')
        best_transfers = 0
        
        # First, find best captain without transfers
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for i in range(1, 6):
                player_key = f'{pos}{i}'
                if player_key in team and team.get(f'{player_key}_selected', 0) == 1:
                    player_id = team[player_key]
                    score = self.calculate_team_score(team, player_id, gameweek)
                    if score > best_score:
                        best_score = score
                        best_captain = player_id
        
        # Consider transfers (0, 1, or 2 transfers)
        max_transfers = min(2, 11)  # Max 2 transfers to limit computation
        
        for num_transfers in range(1, max_transfers + 1):
            # Get all players in starting XI
            starting_players = []
            for pos in ['GK', 'DEF', 'MID', 'FWD']:
                for i in range(1, 6):
                    player_key = f'{pos}{i}'
                    if player_key in team and team.get(f'{player_key}_selected', 0) == 1:
                        starting_players.append((player_key, team[player_key]))
            
            # Try all combinations of transfers
            for players_to_transfer in itertools.combinations(starting_players, num_transfers):
                # Calculate transfer cost
                transfer_cost = 0 if num_transfers <= 1 - transfers_used else (num_transfers - max(0, 1 - transfers_used)) * self.transfer_cost
                
                # Try to find valid transfers for each player
                new_team = team.copy()
                new_budget = budget
                valid_transfer = True
                transfers = []
                
                for player_key, player_id in players_to_transfer:
                    valid_targets = self.get_valid_transfers(player_id, new_budget, new_team)
                    
                    if not valid_targets:
                        valid_transfer = False
                        break
                    
                    # Choose best target based on score improvement
                    best_target = None
                    best_improvement = -float('inf')
                    
                    for target_id, price_diff in valid_targets:
                        improvement = self.get_player_score(target_id, gameweek) - self.get_player_score(player_id, gameweek)
                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_target = (target_id, price_diff)
                    
                    if best_target:
                        new_team[player_key] = best_target[0]
                        new_budget -= best_target[1]
                        transfers.append((player_id, best_target[0]))
                
                if not valid_transfer or new_budget < 0:
                    continue
                
                # Find best captain for new team
                for pos in ['GK', 'DEF', 'MID', 'FWD']:
                    for i in range(1, 6):
                        player_key = f'{pos}{i}'
                        if player_key in new_team and new_team.get(f'{player_key}_selected', 0) == 1:
                            player_id = new_team[player_key]
                            score = self.calculate_team_score(new_team, player_id, gameweek) - transfer_cost
                            
                            if score > best_score:
                                best_score = score
                                best_captain = player_id
                                best_team = new_team.copy()
                                best_transfers = num_transfers
        
        return best_team, best_captain, best_score, best_transfers
    
    def optimize_multiple_gameweeks(self, initial_team: Dict[str, str], 
                                  start_gw: int, num_gameweeks: int = 5) -> Dict:
        """Optimize transfers and captains over multiple gameweeks"""
        results = {
            'gameweeks': [],
            'total_score': 0,
            'total_transfers': 0,
            'total_transfer_cost': 0
        }
        
        current_team = initial_team.copy()
        budget = self.initial_budget_remaining
        cumulative_transfers = 0
        
        for gw in range(start_gw, start_gw + num_gameweeks):
            # Optimize for current gameweek
            new_team, captain, score, transfers_made = self.optimize_single_gameweek(
                current_team, budget, gw, cumulative_transfers
            )
            
            # Calculate transfer cost
            transfer_cost = 0 if transfers_made <= 1 else (transfers_made - 1) * self.transfer_cost
            
            # Record results
            gw_result = {
                'gameweek': gw,
                'team': new_team.copy(),
                'captain': captain,
                'score': score,
                'transfers_made': transfers_made,
                'transfer_cost': transfer_cost,
                'net_score': score
            }
            
            results['gameweeks'].append(gw_result)
            results['total_score'] += score
            results['total_transfers'] += transfers_made
            results['total_transfer_cost'] += transfer_cost
            
            # Update for next gameweek
            current_team = new_team
            cumulative_transfers = transfers_made if transfers_made > 1 else 0
        
        results['net_total_score'] = results['total_score']
        
        return results


def analyze_top_teams(predictions_file: str, teams_file: str, start_gw: int = 39, 
                     num_gameweeks: int = 5, num_teams: int = 10):
    """Analyze top teams with transfer and captain optimization"""
    
    print(f"Loading top teams from {teams_file}...")
    teams_df = pd.read_csv(teams_file)
    
    # Take top N teams
    teams_df = teams_df.head(num_teams)
    
    results = []
    
    for idx, team_row in teams_df.iterrows():
        print(f"\nAnalyzing team {idx + 1}/{len(teams_df)}...")
        
        # Convert row to team dict
        team = {}
        for col in team_row.index:
            if col not in ['11_selected_total_scores', '15_total_price']:
                team[col] = team_row[col]
        
        # Calculate remaining budget
        budget_used = team_row['15_total_price']
        budget_remaining = 100.0 - budget_used
        
        # Optimize transfers and captains
        optimizer = TransferOptimizer(predictions_file, budget_remaining)
        optimization = optimizer.optimize_multiple_gameweeks(team, start_gw, num_gameweeks)
        
        # Summary
        result = {
            'team_index': idx,
            'initial_score': team_row['11_selected_total_scores'],
            'initial_budget': team_row['15_total_price'],
            'optimization': optimization
        }
        
        results.append(result)
        
        print(f"  Initial GW{start_gw} score: {team_row['11_selected_total_scores']:.1f}")
        print(f"  Optimized {num_gameweeks}-week score: {optimization['net_total_score']:.1f}")
        print(f"  Total transfers: {optimization['total_transfers']}")
        print(f"  Transfer cost: {optimization['total_transfer_cost']}")
        
        # Show gameweek breakdown
        for gw_data in optimization['gameweeks']:
            print(f"    GW{gw_data['gameweek']}: {gw_data['score']:.1f} pts, "
                  f"Captain: {gw_data['captain']}, "
                  f"Transfers: {gw_data['transfers_made']}")
    
    # Sort by total score
    results.sort(key=lambda x: x['optimization']['net_total_score'], reverse=True)
    
    print("\n" + "="*80)
    print("TOP TEAMS AFTER 5-GAMEWEEK OPTIMIZATION")
    print("="*80)
    
    for i, result in enumerate(results[:5]):
        print(f"\n{i+1}. Team {result['team_index']+1}")
        print(f"   5-week total: {result['optimization']['net_total_score']:.1f} points")
        print(f"   Transfers made: {result['optimization']['total_transfers']}")
        print(f"   Transfer cost: {result['optimization']['total_transfer_cost']} points")
        
        # Show optimal strategy
        print("\n   Optimal strategy:")
        for gw_data in result['optimization']['gameweeks']:
            print(f"   GW{gw_data['gameweek']}: Score {gw_data['score']:.1f}, "
                  f"Captain {gw_data['captain'][:20]}..., "
                  f"Transfers: {gw_data['transfers_made']}")
    
    return results


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python transfer_captain_optimizer.py <start_gameweek> [num_teams]")
        print("Example: python transfer_captain_optimizer.py 39 10")
        sys.exit(1)
    
    start_gw = int(sys.argv[1])
    num_teams = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    predictions_file = "data/cached_merged_2024_2025_v2/predictions_gw39_proper.csv"
    teams_file = "data/cached_merged_2024_2025_v2/top_200_teams_gw39.csv"
    
    results = analyze_top_teams(predictions_file, teams_file, start_gw, 
                               num_gameweeks=5, num_teams=num_teams)
    
    # Save detailed results
    output_file = f"data/cached_merged_2024_2025_v2/transfer_optimization_gw{start_gw}.json"
    import json
    
    # Convert results to JSON-serializable format
    json_results = []
    for result in results:
        json_result = {
            'team_index': result['team_index'],
            'initial_score': float(result['initial_score']),
            'initial_budget': float(result['initial_budget']),
            'total_score': float(result['optimization']['net_total_score']),
            'gameweeks': []
        }
        
        for gw in result['optimization']['gameweeks']:
            json_result['gameweeks'].append({
                'gameweek': gw['gameweek'],
                'score': float(gw['score']),
                'captain': gw['captain'],
                'transfers': gw['transfers_made'],
                'transfer_cost': gw['transfer_cost']
            })
        
        json_results.append(json_result)
    
    with open(output_file, 'w') as f:
        json.dump(json_results, f, indent=2)
    
    print(f"\nDetailed results saved to {output_file}")


if __name__ == "__main__":
    main()