#!/usr/bin/env python3
"""
FPL Actual Top 50 Teams Based on Historical Data
Finds the best team combinations based on actual historical points

Usage: python src/actual_50_teams_with_scores.py [YEAR] [LAST_OBSERVABLE_WEEK] [TOP_K] [DISPLAY_WEEK]
Example: python src/actual_50_teams_with_scores.py 2024 9 50 10
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from pred_optimized_fixed import Player, OptimizedFantasyOptimizer


def load_actual_player_data(season_year, last_observable_week, display_week=None):
    """Load actual player performance data
    
    Args:
        season_year: Year of the season
        last_observable_week: Last week to use for optimization (average performance)
        display_week: Week to display scores from (if None, uses last_observable_week)
    """
    data_dir = Path("data") / f"{season_year}"
    
    # Load player metadata
    players_df = pd.read_csv(data_dir / f"{season_year}_players.csv")
    
    # Load gameweek data
    gameweek_df = pd.read_csv(data_dir / f"{season_year}_player_gameweek.csv")
    
    # Calculate average points for optimization (weeks 1 to last_observable_week)
    optimization_data = gameweek_df[gameweek_df['GW'] <= last_observable_week]
    player_avg_data = optimization_data.groupby('element').agg({
        'total_points': 'mean',  # Average points for optimization
        'price': 'last',         # Last known price
        'team': 'last'           # Last known team
    }).reset_index()
    
    # Get display week scores (if different from optimization)
    if display_week is not None:
        display_data = gameweek_df[gameweek_df['GW'] == display_week]
        display_scores = display_data.groupby('element')['total_points'].first().to_dict()
    else:
        # Use last_observable_week for display
        display_data = gameweek_df[gameweek_df['GW'] == last_observable_week]
        display_scores = display_data.groupby('element')['total_points'].first().to_dict()
    
    # Use player avg data as base
    player_data = player_avg_data.copy()
    
    # Add display scores as a separate column
    player_data['display_score'] = player_data['element'].map(display_scores).fillna(0)
    
    # Merge with player metadata to get names and positions
    player_data = player_data.merge(
        players_df[['id', 'first_name', 'second_name', 'web_name', 'element_type']],
        left_on='element',
        right_on='id',
        how='inner'
    )
    
    # Create full name and map positions
    # Use second_name if available, otherwise use web_name
    player_data['full_name'] = player_data.apply(
        lambda row: row['first_name'] + ' ' + (row['second_name'] if pd.notna(row['second_name']) and row['second_name'] != '' else row['web_name']),
        axis=1
    )
    position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    player_data['role'] = player_data['element_type'].map(position_map)
    
    # Use average points as the score for optimization
    player_data['score'] = player_data['total_points']
    
    return player_data


def create_optimizer_players(player_data):
    """Convert dataframe to Player objects for optimizer"""
    players = []
    
    for _, row in player_data.iterrows():
        # Skip players with invalid data
        if pd.isna(row['score']) or pd.isna(row['price']) or row['price'] <= 0:
            continue
            
        player = Player(
            id=row['element'],
            score=row['score'],  # Using average points as score
            price=row['price'],
            role=row['role'],
            team=row['team']
        )
        players.append(player)
    
    return players


def format_results_to_dataframe(results, player_data):
    """Convert optimizer results to requested dataframe format"""
    formatted_results = []
    
    # Create player lookup
    player_lookup = player_data.set_index('element').to_dict('index')
    
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
            row[f'GK{i}'] = f"{player_info['full_name']} ({player_info['team']})"
            row[f'GK{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'GK{i}_price'] = round(player.price, 1)
            row[f'GK{i}_score'] = int(player_info['display_score'])  # Use display score
        
        # Add defenders
        for i, player in enumerate(team_by_role['DEF'][:5], 1):
            player_info = player_lookup[player.id]
            row[f'DEF{i}'] = f"{player_info['full_name']} ({player_info['team']})"
            row[f'DEF{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'DEF{i}_price'] = round(player.price, 1)
            row[f'DEF{i}_score'] = int(player_info['display_score'])
        
        # Add midfielders
        for i, player in enumerate(team_by_role['MID'][:5], 1):
            player_info = player_lookup[player.id]
            row[f'MID{i}'] = f"{player_info['full_name']} ({player_info['team']})"
            row[f'MID{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'MID{i}_price'] = round(player.price, 1)
            row[f'MID{i}_score'] = int(player_info['display_score'])
        
        # Add forwards
        for i, player in enumerate(team_by_role['FWD'][:3], 1):
            player_info = player_lookup[player.id]
            row[f'FWD{i}'] = f"{player_info['full_name']} ({player_info['team']})"
            row[f'FWD{i}_selected'] = 1 if player.id in best_11_ids else 0
            row[f'FWD{i}_price'] = round(player.price, 1)
            row[f'FWD{i}_score'] = int(player_info['display_score'])
        
        # Calculate total display score for best 11
        best_11_display_score = sum(player_lookup[p.id]['display_score'] for p in result['best_11'])
        
        # Add totals
        row['11_selected_total_scores'] = int(best_11_display_score)
        row['15_total_price'] = round(result['total_price'], 2)
        
        formatted_results.append(row)
    
    # Create dataframe with proper column order (without games columns)
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
        print("Usage: python src/actual_50_teams_with_scores.py [YEAR] [LAST_OBSERVABLE_WEEK] [TOP_K] [DISPLAY_WEEK]")
        print("Example: python src/actual_50_teams_with_scores.py 2024 9 50 10")
        print("\nIf DISPLAY_WEEK is not specified, uses LAST_OBSERVABLE_WEEK")
        sys.exit(1)
    
    season_year = int(sys.argv[1])
    last_observable_week = int(sys.argv[2])
    top_k = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    display_week = int(sys.argv[4]) if len(sys.argv) > 4 else None
    
    # Check if data exists
    data_dir = Path("data") / f"{season_year}"
    if not data_dir.exists():
        print(f"Error: No data found for {season_year}. Run fpl_download.py first.")
        sys.exit(1)
    
    print(f"Loading actual player data for {season_year}/{season_year+1} season")
    print(f"Using gameweeks 1-{last_observable_week} for optimization")
    if display_week:
        print(f"Displaying scores from gameweek {display_week}")
    else:
        print(f"Displaying scores from gameweek {last_observable_week}")
    
    # Load player data
    player_data = load_actual_player_data(season_year, last_observable_week, display_week)
    
    print(f"Found {len(player_data)} players with data")
    print(f"Role distribution:")
    print(player_data['role'].value_counts())
    
    # Show top scorers for display week
    display_week_label = display_week if display_week else last_observable_week
    print(f"\nTop 10 scorers in gameweek {display_week_label}:")
    top_scorers = player_data.nlargest(10, 'display_score')[['full_name', 'team', 'role', 'display_score', 'price']]
    for _, player in top_scorers.iterrows():
        print(f"  {player['full_name']} ({player['team']}, {player['role']}): "
              f"{int(player['display_score'])} pts, £{player['price']}m")
    
    # Create Player objects
    players = create_optimizer_players(player_data)
    print(f"\nCreated {len(players)} Player objects for optimization")
    
    # Set budget (standard FPL budget)
    budget = 100.0
    
    print(f"\nRunning optimization with budget: £{budget}m")
    print(f"Finding top {top_k} teams based on average performance from weeks 1-{last_observable_week}")
    print("Team requirements: 15 players (2 GK, 5 DEF, 5 MID, 3 FWD)")
    
    # Run optimizer with reduced beam width for faster processing
    optimizer = OptimizedFantasyOptimizer(players, budget)
    results = []
    
    try:
        # Generate candidate teams with smaller beam width
        candidate_teams = optimizer._generate_top_teams_beam_search(beam_width=200, max_results=500)
        
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
            results = results[:top_k]
    except Exception as e:
        print(f"Error during optimization: {e}")
        results = []
    
    print(f"\nFound {len(results)} valid team combinations")
    
    if results:
        # Format results
        results_df = format_results_to_dataframe(results, player_data)
        
        # Save to CSV
        suffix = f"_display_week_{display_week}" if display_week else ""
        output_file = data_dir / f"actual_top_{top_k}_teams_week_{last_observable_week}{suffix}.csv"
        results_df.to_csv(output_file, index=False)
        print(f"\nSaved top {top_k} teams to {output_file}")
        
        # Show top 5 teams
        print(f"\nTop 5 teams by gameweek {display_week_label} points:")
        print(results_df[['11_selected_total_scores', '15_total_price']].head())
        
        # Show best team details
        print("\n" + "="*60)
        print(f"BEST TEAM DETAILS (Gameweek {display_week_label} scores):")
        print("="*60)
        best_team = results_df.iloc[0]
        
        print(f"Best 11 Gameweek {display_week_label} Points: {int(best_team['11_selected_total_scores'])}")
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
                    print(f"  {pos}: {best_team[f'{pos}{i}']} - {int(best_team[f'{pos}{i}_score'])} pts")
        
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
                    print(f"  {pos}: {best_team[f'{pos}{i}']} - {int(best_team[f'{pos}{i}_score'])} pts")
    else:
        print("No valid teams found within budget!")


if __name__ == "__main__":
    main()