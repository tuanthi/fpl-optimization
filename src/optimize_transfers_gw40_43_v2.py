#!/usr/bin/env python3
"""
Optimize FPL transfers for GW40-43 with enhanced transfer rules:
- 1 free transfer per gameweek (can be rolled over, max 5)
- Additional transfers cost -4 points each
- Avoid GK transfers unless absolutely necessary
- Must maintain all FPL squad rules
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from copy import deepcopy
import random


class EnhancedTransferOptimizer:
    def __init__(self, initial_team, player_predictions):
        """
        Initialize with starting team and player predictions
        
        Args:
            initial_team: Dict with squad info
            player_predictions: DataFrame with player scores for each GW
        """
        self.initial_team = deepcopy(initial_team)
        self.predictions = player_predictions
        self.transfer_cost = 4  # Points cost per extra transfer
        self.max_free_transfers = 5  # Maximum rolled over transfers
        
        # FPL constraints
        self.squad_size = 15
        self.position_limits = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
        self.max_from_club = 3
        self.budget_limit = 100.0
        
        # Transfer preferences
        self.gk_transfer_penalty = 0.5  # Reduce GK transfer value by 50%
        
    def get_player_data(self, player_name, gw):
        """Get player prediction for specific gameweek"""
        player_rows = self.predictions[
            self.predictions['player_name'] == player_name
        ]
        if len(player_rows) == 0:
            return None
            
        player = player_rows.iloc[0]
        # Use gameweek-specific score if available
        gw_col = f'gw{gw}_score'
        if gw_col in player:
            score = player[gw_col]
        else:
            score = player.get('weighted_score', 0)
        
        return {
            'name': player_name,
            'position': player['role'],
            'club': player['club'],
            'price': player['price'],
            'score': score
        }
    
    def validate_squad(self, squad):
        """Check if squad meets all FPL rules"""
        # Count positions
        position_count = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
        club_count = {}
        total_cost = 0
        
        for player in squad:
            position_count[player['position']] += 1
            club_count[player['club']] = club_count.get(player['club'], 0) + 1
            total_cost += player['price']
        
        # Check all constraints
        if len(squad) != self.squad_size:
            return False, "Wrong squad size"
            
        for pos, limit in self.position_limits.items():
            if position_count.get(pos, 0) != limit:
                return False, f"Wrong number of {pos}"
        
        for club, count in club_count.items():
            if count > self.max_from_club:
                return False, f"Too many from {club}"
        
        if total_cost > self.budget_limit:
            return False, f"Over budget: £{total_cost:.1f}m"
            
        return True, "Valid"
    
    def calculate_team_score(self, squad, gw):
        """Calculate score for a squad in a gameweek"""
        # Sort by score to find best 11
        sorted_squad = sorted(squad, key=lambda x: x['score'], reverse=True)
        
        # Pick best valid starting XI
        starting_xi = []
        positions_filled = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
        
        for player in sorted_squad:
            pos = player['position']
            
            # Check if we can add this player
            if pos == 'GK' and positions_filled['GK'] < 1:
                starting_xi.append(player)
                positions_filled['GK'] += 1
            elif pos == 'DEF' and positions_filled['DEF'] < 5 and len(starting_xi) < 11:
                starting_xi.append(player)
                positions_filled['DEF'] += 1
            elif pos == 'MID' and positions_filled['MID'] < 5 and len(starting_xi) < 11:
                starting_xi.append(player)
                positions_filled['MID'] += 1
            elif pos == 'FWD' and positions_filled['FWD'] < 3 and len(starting_xi) < 11:
                starting_xi.append(player)
                positions_filled['FWD'] += 1
        
        # Ensure valid formation
        if len(starting_xi) < 11:
            for player in sorted_squad:
                if player not in starting_xi and len(starting_xi) < 11:
                    pos = player['position']
                    if (pos == 'DEF' and positions_filled['DEF'] >= 3) or \
                       (pos == 'MID' and positions_filled['MID'] >= 2) or \
                       (pos == 'FWD' and positions_filled['FWD'] >= 1):
                        starting_xi.append(player)
                        positions_filled[pos] += 1
        
        # Calculate score
        total_score = sum(p['score'] for p in starting_xi)
        
        # Find captain (highest scorer in XI)
        if starting_xi:
            captain = max(starting_xi, key=lambda x: x['score'])
            total_score += captain['score']  # Double points
            
        return total_score, starting_xi
    
    def find_best_transfers(self, current_squad, gw, budget_available, num_transfers=1):
        """Find the best set of transfers for a gameweek"""
        best_transfers = []
        best_improvement = 0
        best_new_squad = current_squad
        
        current_score, _ = self.calculate_team_score(current_squad, gw)
        
        # For multiple transfers, we need to consider combinations
        if num_transfers == 1:
            # Single transfer logic (existing)
            for out_player in current_squad:
                # Apply GK penalty
                position_weight = self.gk_transfer_penalty if out_player['position'] == 'GK' else 1.0
                
                out_pos = out_player['position']
                out_price = out_player['price']
                
                # Get potential replacements
                current_names = [p['name'] for p in current_squad]
                potential_ins = self.predictions[
                    (self.predictions['role'] == out_pos) & 
                    (~self.predictions['player_name'].isin(current_names)) &
                    (self.predictions['price'] <= budget_available + out_price)
                ]
                
                for _, in_player_row in potential_ins.iterrows():
                    in_player = self.get_player_data(in_player_row['player_name'], gw)
                    if not in_player:
                        continue
                    
                    # Create new squad
                    new_squad = [p for p in current_squad if p['name'] != out_player['name']]
                    new_squad.append(in_player)
                    
                    # Validate
                    valid, _ = self.validate_squad(new_squad)
                    if not valid:
                        continue
                    
                    # Calculate improvement with position weight
                    new_score, _ = self.calculate_team_score(new_squad, gw)
                    improvement = (new_score - current_score) * position_weight
                    
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_transfers = [{
                            'out': out_player,
                            'in': in_player,
                            'improvement': new_score - current_score,  # Actual improvement
                            'cost': in_player['price'] - out_player['price']
                        }]
                        best_new_squad = new_squad
        
        else:
            # Multiple transfers - simplified approach
            # Find best individual transfers and combine them
            transfer_candidates = []
            
            for out_player in current_squad:
                position_weight = self.gk_transfer_penalty if out_player['position'] == 'GK' else 1.0
                out_pos = out_player['position']
                out_price = out_player['price']
                
                current_names = [p['name'] for p in current_squad]
                potential_ins = self.predictions[
                    (self.predictions['role'] == out_pos) & 
                    (~self.predictions['player_name'].isin(current_names)) &
                    (self.predictions['price'] <= budget_available + out_price)
                ]
                
                for _, in_player_row in potential_ins.iterrows():
                    in_player = self.get_player_data(in_player_row['player_name'], gw)
                    if not in_player:
                        continue
                    
                    # Calculate individual transfer value
                    value = (in_player['score'] - out_player['score']) * position_weight
                    
                    transfer_candidates.append({
                        'out': out_player,
                        'in': in_player,
                        'value': value,
                        'cost': in_player['price'] - out_player['price']
                    })
            
            # Sort by value and try combinations
            transfer_candidates.sort(key=lambda x: x['value'], reverse=True)
            
            # Try top combinations that don't conflict
            for i in range(min(num_transfers, len(transfer_candidates))):
                if i == 0:
                    temp_squad = current_squad.copy()
                    temp_transfers = []
                    used_players = set()
                    
                    for candidate in transfer_candidates:
                        if (candidate['out']['name'] not in used_players and 
                            candidate['in']['name'] not in used_players and
                            len(temp_transfers) < num_transfers):
                            
                            # Try transfer
                            new_temp_squad = [p for p in temp_squad if p['name'] != candidate['out']['name']]
                            new_temp_squad.append(candidate['in'])
                            
                            # Validate
                            valid, _ = self.validate_squad(new_temp_squad)
                            if valid:
                                temp_squad = new_temp_squad
                                temp_transfers.append({
                                    'out': candidate['out'],
                                    'in': candidate['in'],
                                    'improvement': candidate['value'],
                                    'cost': candidate['cost']
                                })
                                used_players.add(candidate['out']['name'])
                                used_players.add(candidate['in']['name'])
                    
                    # Check if this combination is better
                    if temp_transfers:
                        new_score, _ = self.calculate_team_score(temp_squad, gw)
                        total_improvement = new_score - current_score
                        
                        if total_improvement > best_improvement:
                            best_improvement = total_improvement
                            best_transfers = temp_transfers
                            best_new_squad = temp_squad
        
        return best_transfers, best_new_squad
    
    def optimize_all_gameweeks_with_rollover(self, start_gw=40, end_gw=43):
        """Optimize transfers with rollover capability"""
        results = {
            'initial_team': self.initial_team,
            'gameweeks': {},
            'total_score': 0,
            'total_transfer_cost': 0
        }
        
        # Convert initial team to squad format
        current_squad = []
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for i in range(1, 6):
                player_key = f'{pos}{i}'
                if player_key in self.initial_team:
                    player_name = self.initial_team[player_key]
                    if '(' in player_name:
                        player_name = player_name.split(' (')[0]
                    
                    player_data = self.get_player_data(player_name, start_gw)
                    if player_data:
                        current_squad.append(player_data)
        
        # Add bench players
        for i in range(1, 5):
            bench_key = f'BENCH{i}'
            if bench_key in self.initial_team:
                player_name = self.initial_team[bench_key]
                if '(' in player_name:
                    player_name = player_name.split(' (')[0]
                    
                player_data = self.get_player_data(player_name, start_gw)
                if player_data:
                    current_squad.append(player_data)
        
        # Track free transfers
        free_transfers_available = 1
        
        # Optimize each gameweek
        for gw in range(start_gw, end_gw + 1):
            print(f"\nOptimizing GW{gw} (Free transfers available: {free_transfers_available})...")
            
            # Update player scores for this GW
            for player in current_squad:
                updated = self.get_player_data(player['name'], gw)
                if updated:
                    player['score'] = updated['score']
            
            # Calculate budget
            squad_value = sum(p['price'] for p in current_squad)
            budget_available = 100 - squad_value
            
            # Decide transfer strategy
            # Look ahead: if we can benefit from saving transfers
            future_benefit = self.assess_future_transfer_value(current_squad, gw, end_gw)
            
            # Find best transfers for different numbers
            best_option = {'transfers': [], 'score': 0, 'num_transfers': 0}
            
            for num_transfers in range(min(free_transfers_available + 1, 4)):  # Try 0 to 3 transfers
                if num_transfers == 0:
                    # No transfers
                    score, _ = self.calculate_team_score(current_squad, gw)
                    if score > best_option['score']:
                        best_option = {
                            'transfers': [],
                            'squad': current_squad,
                            'score': score,
                            'num_transfers': 0,
                            'cost': 0
                        }
                else:
                    # Find best transfers
                    transfers, new_squad = self.find_best_transfers(
                        current_squad, gw, budget_available, num_transfers
                    )
                    
                    if transfers:
                        score, starting_xi = self.calculate_team_score(new_squad, gw)
                        
                        # Calculate transfer cost
                        transfer_cost = 0
                        if num_transfers > free_transfers_available:
                            transfer_cost = (num_transfers - free_transfers_available) * self.transfer_cost
                        
                        net_score = score - transfer_cost
                        
                        # Consider if it's worth it
                        if net_score > best_option['score']:
                            best_option = {
                                'transfers': transfers,
                                'squad': new_squad,
                                'score': net_score,
                                'num_transfers': num_transfers,
                                'cost': transfer_cost,
                                'starting_xi': starting_xi
                            }
            
            # Apply best option
            if best_option['num_transfers'] > 0:
                current_squad = best_option['squad']
                used_transfers = best_option['num_transfers']
                
                # Update free transfers
                if used_transfers <= free_transfers_available:
                    free_transfers_available = free_transfers_available - used_transfers + 1
                else:
                    free_transfers_available = 1
            else:
                # Rolled over
                free_transfers_available = min(free_transfers_available + 1, self.max_free_transfers)
            
            # Get final lineup
            final_score, starting_xi = self.calculate_team_score(current_squad, gw)
            
            # Store results
            results['gameweeks'][f'GW{gw}'] = {
                'transfers': [
                    {
                        'out': t['out']['name'],
                        'in': t['in']['name'],
                        'improvement': t['improvement']
                    } for t in best_option.get('transfers', [])
                ],
                'transfer_cost': best_option.get('cost', 0),
                'squad': [p['name'] for p in current_squad],
                'starting_xi': [p['name'] for p in starting_xi],
                'captain': max(starting_xi, key=lambda x: x['score'])['name'] if starting_xi else None,
                'score': best_option['score'],
                'formation': self.get_formation(starting_xi),
                'free_transfers_remaining': free_transfers_available
            }
            
            results['total_score'] += best_option['score']
            results['total_transfer_cost'] += best_option.get('cost', 0)
            
            # Print summary
            print(f"  Transfers: {best_option['num_transfers']} (cost: -{best_option.get('cost', 0)})")
            if best_option.get('transfers'):
                for t in best_option['transfers']:
                    print(f"    OUT: {t['out']['name']} -> IN: {t['in']['name']} (+{t['improvement']:.1f})")
            else:
                print("    Rolled over free transfer")
            print(f"  Score: {best_option['score']:.1f}")
            print(f"  Free transfers for next GW: {free_transfers_available}")
        
        return results
    
    def assess_future_transfer_value(self, squad, current_gw, end_gw):
        """Assess if saving transfers for future would be beneficial"""
        # Simplified: Check if any big upgrades are coming
        future_value = 0
        
        for future_gw in range(current_gw + 1, min(current_gw + 3, end_gw + 1)):
            # Check for potential high-value transfers
            for player in squad:
                if player['position'] != 'GK':  # Skip GKs
                    # Look for potential upgrades
                    avg_improvement = 2.0  # Placeholder
                    future_value += avg_improvement
        
        return future_value
    
    def get_formation(self, starting_xi):
        """Determine formation from starting XI"""
        pos_count = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
        for p in starting_xi:
            pos_count[p['position']] += 1
        
        return f"{pos_count['DEF']}-{pos_count['MID']}-{pos_count['FWD']}"


def main():
    # Load predictions with GW40-43 data
    predictions_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/predictions_gw40_43.csv")
    if not predictions_file.exists():
        print(f"Error: {predictions_file} not found")
        return
    
    predictions_df = pd.read_csv(predictions_file)
    predictions_df['player_name'] = predictions_df['first_name'] + ' ' + predictions_df['last_name']
    
    # Load best teams
    teams_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/final_selected_teams_proper.csv")
    if not teams_file.exists():
        print(f"Error: {teams_file} not found")
        return
    
    teams_df = pd.read_csv(teams_file)
    
    # Process each of the top 3 teams
    all_results = []
    
    for idx, team in teams_df.head(3).iterrows():
        print(f"\n{'='*80}")
        print(f"Processing Team {idx + 1} with ROLLOVER strategy")
        print(f"{'='*80}")
        
        # Convert team to dict format
        team_dict = team.to_dict()
        
        # Run optimization
        optimizer = EnhancedTransferOptimizer(team_dict, predictions_df)
        results = optimizer.optimize_all_gameweeks_with_rollover(start_gw=40, end_gw=43)
        results['team_rank'] = idx + 1
        
        all_results.append(results)
        
        # Print summary
        print(f"\nTeam {idx + 1} Summary:")
        print(f"  Total Score (GW40-43): {results['total_score']:.1f}")
        print(f"  Total Transfer Cost: -{results['total_transfer_cost']}")
        print(f"  Net Score: {results['total_score']:.1f}")
    
    # Save results
    output_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/transfer_optimization_v2_gw40_43.json")
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n\nResults saved to: {output_file}")
    
    # Create summary
    summary_data = []
    for result in all_results:
        for gw, gw_data in result['gameweeks'].items():
            summary_data.append({
                'team': result['team_rank'],
                'gameweek': gw,
                'transfers': len(gw_data['transfers']),
                'transfer_cost': gw_data['transfer_cost'],
                'score': gw_data['score'],
                'captain': gw_data['captain'],
                'formation': gw_data['formation'],
                'free_transfers_remaining': gw_data['free_transfers_remaining']
            })
    
    summary_df = pd.DataFrame(summary_data)
    summary_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/transfer_summary_v2_gw40_43.csv")
    summary_df.to_csv(summary_file, index=False)
    print(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()