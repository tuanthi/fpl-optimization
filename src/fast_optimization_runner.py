#!/usr/bin/env python3
"""
Fast FPL Team Optimization Runner
Optimized version for large datasets
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from pred_optimized_fixed import Player, OptimizedFantasyOptimizer


def load_and_filter_players(pred_csv_path, min_gameweeks=5):
    """Load prediction data and filter to reliable players"""
    print("Loading prediction data...")
    df = pd.read_csv(pred_csv_path)
    
    # Remove unknown roles
    df = df[df['role'].isin(['GK', 'DEF', 'MID', 'FWD'])]
    
    # Count gameweeks per player
    player_gameweeks = df.groupby(['first_name', 'last_name']).size()
    
    # Filter to players who played at least min_gameweeks
    reliable_players = player_gameweeks[player_gameweeks >= min_gameweeks].index
    df = df[df.set_index(['first_name', 'last_name']).index.isin(reliable_players)]
    
    print(f"Filtered to {len(df.groupby(['first_name', 'last_name']))} players with >= {min_gameweeks} gameweeks")
    
    # Aggregate player data
    player_data = df.groupby(['first_name', 'last_name', 'club', 'role']).agg({
        'average_score': 'mean',
        'price': 'last'
    }).reset_index()
    
    # Filter out low-scoring players to reduce search space
    player_data = player_data[player_data['average_score'] > -0.5]
    
    # Create player ID and full name
    player_data['player_id'] = player_data.index
    player_data['full_name'] = player_data['first_name'] + ' ' + player_data['last_name']
    
    return player_data


def create_top_players_only(player_data, top_n_per_role=50):
    """Create Player objects for only the top N players per role"""
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


def format_results_simple(results, player_data):
    """Convert results to dataframe format"""
    formatted_results = []
    player_lookup = player_data.set_index('player_id').to_dict('index')
    
    for result in results[:50]:  # Only top 50
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
        row['15_total_price'] = round(result['total_price'], 2)
        
        formatted_results.append(row)
    
    # Create dataframe
    columns = []
    for i in range(1, 3):
        columns.extend([f'GK{i}', f'GK{i}_selected', f'GK{i}_price', f'GK{i}_score'])
    for i in range(1, 6):
        columns.extend([f'DEF{i}', f'DEF{i}_selected', f'DEF{i}_price', f'DEF{i}_score'])
    for i in range(1, 6):
        columns.extend([f'MID{i}', f'MID{i}_selected', f'MID{i}_price', f'MID{i}_score'])
    for i in range(1, 4):
        columns.extend([f'FWD{i}', f'FWD{i}_selected', f'FWD{i}_price', f'FWD{i}_score'])
    columns.extend(['11_selected_total_scores', '15_total_price'])
    
    return pd.DataFrame(formatted_results, columns=columns)


def main():
    if len(sys.argv) < 3:
        print("Usage: python src/fast_optimization_runner.py [PRED_CSV] [OUTPUT_CSV]")
        sys.exit(1)
    
    pred_csv_path = sys.argv[1]
    output_csv_path = sys.argv[2]
    
    # Load and filter players
    player_data = load_and_filter_players(pred_csv_path, min_gameweeks=10)
    
    print(f"\nRole distribution after filtering:")
    print(player_data['role'].value_counts())
    
    # Create top players only
    players = create_top_players_only(player_data, top_n_per_role=40)
    print(f"\nOptimizing with {len(players)} top players")
    
    # Run optimization with smaller search space
    budget = 100.0
    optimizer = OptimizedFantasyOptimizer(players, budget)
    
    print("\nRunning optimization (this may take a minute)...")
    results = []
    
    try:
        # Use much smaller beam width for faster results
        candidate_teams = optimizer._generate_top_teams_beam_search(beam_width=200, max_results=200)
        
        if candidate_teams:
            print(f"Found {len(candidate_teams)} candidate teams, evaluating...")
            
            for i, (team_15, total_price) in enumerate(candidate_teams):
                if i % 50 == 0:
                    print(f"  Evaluated {i}/{len(candidate_teams)} teams...")
                    
                best_11, best_score = optimizer._find_best_11_from_15_optimized(team_15)
                
                results.append({
                    'team_15': team_15,
                    'best_11': best_11,
                    'best_11_score': best_score,
                    'total_price': total_price
                })
            
            results.sort(key=lambda x: x['best_11_score'], reverse=True)
            
    except Exception as e:
        print(f"Error during optimization: {e}")
        import traceback
        traceback.print_exc()
    
    if results:
        print(f"\nFormatting {len(results)} results...")
        results_df = format_results_simple(results, player_data)
        results_df.to_csv(output_csv_path, index=False)
        print(f"\nSaved top teams to {output_csv_path}")
        print(f"\nTop 5 teams:")
        print(results_df[['11_selected_total_scores', '15_total_price']].head())
    else:
        print("No valid teams found!")


if __name__ == "__main__":
    main()