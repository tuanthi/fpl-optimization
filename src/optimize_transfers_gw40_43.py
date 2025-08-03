#!/usr/bin/env python3
"""
Optimize FPL transfers for GW40-43 with transfer rules:
- 1 free transfer per gameweek
- Additional transfers cost -4 points each
- Must maintain all FPL squad rules
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from copy import deepcopy
import random


class TransferOptimizer:
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
        
        # FPL constraints
        self.squad_size = 15
        self.position_limits = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
        self.max_from_club = 3
        self.budget_limit = 100.0
        
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
        
        # Ensure valid formation (3-5-2, 3-4-3, 4-4-2, 4-3-3, 4-5-1, 5-4-1, 5-3-2)
        if len(starting_xi) < 11:
            # Fill remaining spots
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
    
    def find_best_transfer(self, current_squad, gw, budget_available):
        """Find the best single transfer for a gameweek"""
        best_transfer = None
        best_improvement = 0
        
        current_score, _ = self.calculate_team_score(current_squad, gw)
        
        # Try each player as potential out
        for out_player in current_squad:
            # Find potential replacements
            out_pos = out_player['position']
            out_price = out_player['price']
            
            # Get all players of same position not in squad
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
                
                # Calculate improvement
                new_score, _ = self.calculate_team_score(new_squad, gw)
                improvement = new_score - current_score
                
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_transfer = {
                        'out': out_player,
                        'in': in_player,
                        'improvement': improvement,
                        'cost': in_player['price'] - out_player['price']
                    }
        
        return best_transfer
    
    def optimize_gameweek_transfers(self, current_squad, gw, free_transfers=1, budget=100):
        """Optimize transfers for a single gameweek"""
        transfers_made = []
        squad = deepcopy(current_squad)
        transfer_cost = 0
        
        # Keep making transfers while beneficial
        while True:
            # Calculate current budget
            squad_value = sum(p['price'] for p in squad)
            budget_available = budget - squad_value
            
            # Find best transfer
            best_transfer = self.find_best_transfer(squad, gw, budget_available)
            
            if not best_transfer:
                break
                
            # Check if transfer is worth the cost
            cost_threshold = 0 if len(transfers_made) < free_transfers else self.transfer_cost
            
            if best_transfer['improvement'] <= cost_threshold:
                break
            
            # Make the transfer
            squad = [p for p in squad if p['name'] != best_transfer['out']['name']]
            squad.append(best_transfer['in'])
            transfers_made.append(best_transfer)
            
            # Add transfer cost if beyond free transfers
            if len(transfers_made) > free_transfers:
                transfer_cost += self.transfer_cost
        
        return squad, transfers_made, transfer_cost
    
    def optimize_all_gameweeks(self, start_gw=40, end_gw=43):
        """Optimize transfers across multiple gameweeks"""
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
                    # Clean player name if it has club in parentheses
                    if '(' in player_name:
                        player_name = player_name.split(' (')[0]
                    
                    player_data = self.get_player_data(player_name, start_gw)
                    if player_data:
                        current_squad.append(player_data)
        
        # Also add bench players
        for i in range(1, 5):
            bench_key = f'BENCH{i}'
            if bench_key in self.initial_team:
                player_name = self.initial_team[bench_key]
                if '(' in player_name:
                    player_name = player_name.split(' (')[0]
                    
                player_data = self.get_player_data(player_name, start_gw)
                if player_data:
                    current_squad.append(player_data)
        
        # Optimize each gameweek
        for gw in range(start_gw, end_gw + 1):
            print(f"\nOptimizing GW{gw}...")
            
            # Update player scores for this GW
            for player in current_squad:
                updated = self.get_player_data(player['name'], gw)
                if updated:
                    player['score'] = updated['score']
            
            # Optimize transfers
            new_squad, transfers, transfer_cost = self.optimize_gameweek_transfers(
                current_squad, gw, free_transfers=1
            )
            
            # Calculate final score
            gw_score, starting_xi = self.calculate_team_score(new_squad, gw)
            gw_score -= transfer_cost
            
            # Store results
            results['gameweeks'][f'GW{gw}'] = {
                'transfers': [
                    {
                        'out': t['out']['name'],
                        'in': t['in']['name'],
                        'improvement': t['improvement']
                    } for t in transfers
                ],
                'transfer_cost': transfer_cost,
                'squad': [p['name'] for p in new_squad],
                'starting_xi': [p['name'] for p in starting_xi],
                'captain': max(starting_xi, key=lambda x: x['score'])['name'] if starting_xi else None,
                'score': gw_score,
                'formation': self.get_formation(starting_xi)
            }
            
            results['total_score'] += gw_score
            results['total_transfer_cost'] += transfer_cost
            
            # Update squad for next GW
            current_squad = new_squad
            
            # Print summary
            print(f"  Transfers: {len(transfers)} (cost: -{transfer_cost})")
            for t in transfers:
                print(f"    OUT: {t['out']['name']} -> IN: {t['in']['name']} (+{t['improvement']:.1f})")
            print(f"  Score: {gw_score:.1f}")
        
        return results
    
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
        print(f"Processing Team {idx + 1} (5GW Score: {team['5gw_estimated']})")
        print(f"{'='*80}")
        
        # Convert team to dict format
        team_dict = team.to_dict()
        
        # Run optimization
        optimizer = TransferOptimizer(team_dict, predictions_df)
        results = optimizer.optimize_all_gameweeks(start_gw=40, end_gw=43)
        results['team_rank'] = idx + 1
        
        all_results.append(results)
        
        # Print summary
        print(f"\nTeam {idx + 1} Summary:")
        print(f"  Total Score (GW40-43): {results['total_score']:.1f}")
        print(f"  Total Transfer Cost: -{results['total_transfer_cost']}")
        print(f"  Net Score: {results['total_score'] - results['total_transfer_cost']:.1f}")
    
    # Save results
    output_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/transfer_optimization_gw40_43.json")
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n\nResults saved to: {output_file}")
    
    # Create summary CSV
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
                'formation': gw_data['formation']
            })
    
    summary_df = pd.DataFrame(summary_data)
    summary_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/transfer_summary_gw40_43.csv")
    summary_df.to_csv(summary_file, index=False)
    print(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()