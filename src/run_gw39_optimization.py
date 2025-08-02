#!/usr/bin/env python3
"""
Run optimization specifically for gameweek 39 cached data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from pred_optimized_fixed import Player, OptimizedFantasyOptimizer


def load_gw39_predictions(pred_file):
    """Load gameweek 39 predictions"""
    print(f"Loading predictions from {pred_file}...")
    df = pd.read_csv(pred_file)
    
    # Group by player to get aggregated data
    player_data = df.groupby(['first_name', 'last_name', 'club', 'role']).agg({
        'average_score': 'mean',
        'price': 'first'
    }).reset_index()
    
    # Create player ID
    player_data['player_id'] = player_data.index
    player_data['full_name'] = player_data['first_name'] + ' ' + player_data['last_name']
    
    print(f"Loaded {len(player_data)} unique players")
    print(f"\nRole distribution:")
    print(player_data['role'].value_counts())
    
    return player_data


def create_players(player_data, top_n_per_role=20):
    """Create Player objects"""
    players = []
    
    for role in ['GK', 'DEF', 'MID', 'FWD']:
        role_players = player_data[player_data['role'] == role].copy()
        
        # Sort by score and take top N
        role_players = role_players.nlargest(top_n_per_role, 'average_score')
        
        for _, row in role_players.iterrows():
            if pd.notna(row['average_score']) and pd.notna(row['price']) and row['price'] > 0:
                player = Player(
                    id=row['player_id'],
                    score=row['average_score'],
                    price=row['price'],
                    role=row['role'],
                    team=row['club']
                )
                players.append(player)
    
    return players


def format_results(results, player_data):
    """Format optimization results"""
    formatted_results = []
    player_lookup = player_data.set_index('player_id').to_dict('index')
    
    for result in results[:50]:  # Top 50 teams
        row = {}
        
        # Group by role
        team_by_role = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
        for player in result['team_15']:
            team_by_role[player.role].append(player)
        
        # Sort each role by score
        for role in team_by_role:
            team_by_role[role].sort(key=lambda p: p.score, reverse=True)
        
        best_11_ids = {p.id for p in result['best_11']}
        
        # Add players
        for i, player in enumerate(team_by_role['GK'][:2], 1):
            player_info = player_lookup[player.id]
            row[f'GK{i}'] = f"{player_info['full_name']} ({player_info['club']})"
            row[f'GK{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'GK{i}_price'] = round(player.price, 1)
            row[f'GK{i}_score'] = round(player.score, 4)
        
        for i, player in enumerate(team_by_role['DEF'][:5], 1):
            player_info = player_lookup[player.id]
            row[f'DEF{i}'] = f"{player_info['full_name']} ({player_info['club']})"
            row[f'DEF{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'DEF{i}_price'] = round(player.price, 1)
            row[f'DEF{i}_score'] = round(player.score, 4)
        
        for i, player in enumerate(team_by_role['MID'][:5], 1):
            player_info = player_lookup[player.id]
            row[f'MID{i}'] = f"{player_info['full_name']} ({player_info['club']})"
            row[f'MID{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'MID{i}_price'] = round(player.price, 1)
            row[f'MID{i}_score'] = round(player.score, 4)
        
        for i, player in enumerate(team_by_role['FWD'][:3], 1):
            player_info = player_lookup[player.id]
            row[f'FWD{i}'] = f"{player_info['full_name']} ({player_info['club']})"
            row[f'FWD{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'FWD{i}_price'] = round(player.price, 1)
            row[f'FWD{i}_score'] = round(player.score, 4)
        
        row['11_selected_total_scores'] = round(result['best_11_score'], 2)
        row['15_total_price'] = round(result['total_cost'], 1)
        
        formatted_results.append(row)
    
    return pd.DataFrame(formatted_results)


def main():
    import sys
    if len(sys.argv) != 3:
        print("Usage: python run_gw39_optimization.py <predictions.csv> <output.csv>")
        sys.exit(1)
    
    pred_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Load predictions
    player_data = load_gw39_predictions(pred_file)
    
    # Create players
    players = create_players(player_data, top_n_per_role=40)
    print(f"\nCreated {len(players)} Player objects for optimization")
    
    if len(players) == 0:
        print("Error: No valid players for optimization")
        return
    
    # Run optimization
    print("\nRunning optimization...")
    optimizer = OptimizedFantasyOptimizer(
        players=players,
        budget=100.0
    )
    
    results = optimizer.find_top_combinations_optimized(top_k=50)
    
    if results:
        print(f"\nFound {len(results)} valid teams")
        
        # Format and save results
        df = format_results(results, player_data)
        df.to_csv(output_file, index=False)
        print(f"Saved results to {output_file}")
        
        # Show top team
        print("\nTop team:")
        for col in ['GK1', 'GK2', 'DEF1', 'MID1', 'FWD1']:
            if col in df.columns:
                print(f"  {col}: {df.iloc[0][col]} - £{df.iloc[0][f'{col}_price']:.1f}m")
        print(f"\nTotal value: £{df.iloc[0]['15_total_price']:.1f}m")
    else:
        print("No valid teams found!")


if __name__ == "__main__":
    main()