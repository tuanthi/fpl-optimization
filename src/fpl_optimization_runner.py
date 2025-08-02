#!/usr/bin/env python3
"""
FPL Team Optimization Runner
Uses pred_optimized.py to find top 50 team combinations from prediction data

Usage: python src/fpl_optimization_runner.py [PRED_CSV_FILE] [OUTPUT_CSV]
Example: python src/fpl_optimization_runner.py data/2024/pred_2024_week_sampling_1_to_9.csv data/2024/top_50_teams.csv
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from pred_optimized_fixed import Player, OptimizedFantasyOptimizer


def load_prediction_data(pred_csv_path, max_gameweek=None):
    """Load prediction data and aggregate scores for gameweeks"""
    df = pd.read_csv(pred_csv_path)
    
    # Filter to max gameweek if specified
    if max_gameweek is not None:
        df = df[df['gameweek'] <= max_gameweek]
    
    # Group by player and aggregate
    player_data = df.groupby(['first_name', 'last_name', 'club', 'role']).agg({
        'average_score': 'mean',  # Average of the average scores
        'price': 'last'  # Last known price
    }).reset_index()
    
    # Create player ID from name combination
    player_data['player_id'] = player_data.index
    
    # Create full name for display
    player_data['full_name'] = player_data['first_name'] + ' ' + player_data['last_name']
    
    return player_data


def create_optimizer_players(player_data):
    """Convert dataframe to Player objects for optimizer"""
    players = []
    
    for _, row in player_data.iterrows():
        # Skip players with invalid data
        if pd.isna(row['average_score']) or pd.isna(row['price']) or row['price'] <= 0:
            continue
            
        player = Player(
            id=row['player_id'],
            score=row['average_score'],
            price=row['price'],
            role=row['role'],
            team=row['club']
        )
        players.append(player)
    
    return players


def format_results_to_dataframe(results, player_data):
    """Convert optimizer results to requested dataframe format"""
    formatted_results = []
    
    # Create player lookup
    player_lookup = player_data.set_index('player_id').to_dict('index')
    
    for result in results:
        row = {}
        
        # Group players by role in team_15
        team_by_role = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
        for player in result['team_15']:
            team_by_role[player.role].append(player)
        
        # Sort each role by score (best first)
        for role in team_by_role:
            team_by_role[role].sort(key=lambda p: p.score, reverse=True)
        
        # Check which players are in best 11
        best_11_ids = {p.id for p in result['best_11']}
        
        # Add goalkeepers
        for i, player in enumerate(team_by_role['GK'][:2], 1):
            player_info = player_lookup[player.id]
            row[f'GK{i}'] = f"{player_info['full_name']} ({player_info['club']})"
            row[f'GK{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'GK{i}_price'] = round(player.price, 1)
            row[f'GK{i}_score'] = round(player.score, 4)
        
        # Add defenders
        for i, player in enumerate(team_by_role['DEF'][:5], 1):
            player_info = player_lookup[player.id]
            row[f'DEF{i}'] = f"{player_info['full_name']} ({player_info['club']})"
            row[f'DEF{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'DEF{i}_price'] = round(player.price, 1)
            row[f'DEF{i}_score'] = round(player.score, 4)
        
        # Add midfielders
        for i, player in enumerate(team_by_role['MID'][:5], 1):
            player_info = player_lookup[player.id]
            row[f'MID{i}'] = f"{player_info['full_name']} ({player_info['club']})"
            row[f'MID{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'MID{i}_price'] = round(player.price, 1)
            row[f'MID{i}_score'] = round(player.score, 4)
        
        # Add forwards
        for i, player in enumerate(team_by_role['FWD'][:3], 1):
            player_info = player_lookup[player.id]
            row[f'FWD{i}'] = f"{player_info['full_name']} ({player_info['club']})"
            row[f'FWD{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'FWD{i}_price'] = round(player.price, 1)
            row[f'FWD{i}_score'] = round(player.score, 4)
        
        # Add totals
        row['11_selected_total_scores'] = round(result['best_11_score'], 2)
        row['15_total_price'] = round(result['total_price'], 2)
        
        formatted_results.append(row)
    
    # Create dataframe with proper column order
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
        print("Usage: python src/fpl_optimization_runner.py [PRED_CSV_FILE] [OUTPUT_CSV]")
        print("Example: python src/fpl_optimization_runner.py data/2024/pred_2024_week_sampling_1_to_9.csv data/2024/top_50_teams.csv")
        sys.exit(1)
    
    pred_csv_path = sys.argv[1]
    output_csv_path = sys.argv[2]
    
    # Check if input file exists
    if not Path(pred_csv_path).exists():
        print(f"Error: Input file {pred_csv_path} not found")
        sys.exit(1)
    
    print(f"Loading prediction data from {pred_csv_path}...")
    player_data = load_prediction_data(pred_csv_path)
    
    print(f"Found {len(player_data)} unique players")
    print(f"Role distribution:")
    print(player_data['role'].value_counts())
    
    # Filter out players with unknown role
    valid_roles = ['GK', 'DEF', 'MID', 'FWD']
    player_data = player_data[player_data['role'].isin(valid_roles)]
    
    print(f"\nAfter filtering: {len(player_data)} players with valid roles")
    
    # Create Player objects
    players = create_optimizer_players(player_data)
    print(f"Created {len(players)} Player objects")
    
    # Set budget (standard FPL budget)
    budget = 100.0
    
    print(f"\nRunning optimization with budget: £{budget}m")
    print("Team requirements: 15 players (2 GK, 5 DEF, 5 MID, 3 FWD)")
    print("Team constraint: Maximum 3 players from same team")
    
    # Run optimizer with reduced beam width for faster processing
    optimizer = OptimizedFantasyOptimizer(players, budget)
    # Override the beam search method to use smaller beam width
    results = []
    try:
        # Generate candidate teams with larger beam width to find valid teams with team constraint
        # Use smaller beam width for faster processing with large datasets
        candidate_teams = optimizer._generate_top_teams_beam_search(beam_width=500, max_results=1000)
        
        if candidate_teams:
            # Evaluate each team
            for team_15, total_price in candidate_teams:
                best_11, best_score = optimizer._find_best_11_from_15_optimized(team_15)
                
                results.append({
                    'team_15': team_15,
                    'best_11': best_11,
                    'best_11_score': best_score,
                    'total_price': total_price,
                    'price_margin': budget - total_price
                })
            
            # Sort by best 11 score
            results.sort(key=lambda x: x['best_11_score'], reverse=True)
            results = results[:50]
    except Exception as e:
        print(f"Error during optimization: {e}")
        results = []
    
    print(f"\nFound {len(results)} valid team combinations")
    
    if results:
        # Format results
        results_df = format_results_to_dataframe(results, player_data)
        
        # Save to CSV
        results_df.to_csv(output_csv_path, index=False)
        print(f"\nSaved top 50 teams to {output_csv_path}")
        
        # Show top 5 teams
        print("\nTop 5 teams by 11-player score:")
        print(results_df[['11_selected_total_scores', '15_total_price']].head())
        
        # Show best team details
        print("\n" + "="*60)
        print("BEST TEAM DETAILS:")
        print("="*60)
        best_team = results_df.iloc[0]
        
        print(f"Best 11 Score: {best_team['11_selected_total_scores']}")
        print(f"Total Price: £{best_team['15_total_price']}m")
        
        print("\nStarting 11:")
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            if pos == 'GK':
                count = 2
            elif pos == 'DEF':
                count = 5
            elif pos == 'MID':
                count = 5
            else:
                count = 3
                
            for i in range(1, count + 1):
                if best_team[f'{pos}{i}_selected'] == 1:
                    print(f"  {pos}: {best_team[f'{pos}{i}']}")
        
        print("\nBench:")
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            if pos == 'GK':
                count = 2
            elif pos == 'DEF':
                count = 5
            elif pos == 'MID':
                count = 5
            else:
                count = 3
                
            for i in range(1, count + 1):
                if best_team[f'{pos}{i}_selected'] == 0:
                    print(f"  {pos}: {best_team[f'{pos}{i}']}")
    else:
        print("No valid teams found within budget!")


if __name__ == "__main__":
    main()