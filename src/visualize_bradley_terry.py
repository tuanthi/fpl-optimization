#!/usr/bin/env python3
"""
Visualize Bradley-Terry matrix results

Usage: python src/visualize_bradley_terry.py [YEAR] [WEEK_SUFFIX]
Example: python src/visualize_bradley_terry.py 2024 weeks_1_to_9
"""

import sys
import numpy as np
import pandas as pd
import json
from pathlib import Path


def load_bradley_terry_data(season_year, suffix="all_weeks"):
    """Load Bradley-Terry matrix and related data"""
    
    bt_dir = Path("data") / f"{season_year}" / "bradley_terry"
    
    # Load matrix
    matrix_file = bt_dir / f"bt_matrix_{suffix}.npy"
    bt_matrix = np.load(matrix_file)
    
    # Load mappings
    mappings_file = bt_dir / f"player_mappings_{suffix}.json"
    with open(mappings_file, 'r') as f:
        mappings = json.load(f)
    
    # Load analysis
    analysis_file = bt_dir / f"matrix_analysis_{suffix}.csv"
    analysis_df = pd.read_csv(analysis_file)
    
    # Load player stats
    stats_file = bt_dir / f"player_stats_{suffix}.csv"
    stats_df = pd.read_csv(stats_file)
    
    return bt_matrix, mappings, analysis_df, stats_df


def analyze_player_matchups(bt_matrix, mappings, player_name):
    """Analyze a specific player's matchups"""
    
    # Find player ID
    player_names = mappings['player_names']
    player_id = None
    
    for pid, name in player_names.items():
        if player_name.lower() in name.lower():
            player_id = pid
            player_name = name
            break
    
    if player_id is None:
        print(f"Player '{player_name}' not found")
        return
    
    # Get player index
    player_to_idx = mappings['player_to_idx']
    if player_id not in player_to_idx:
        print(f"Player '{player_name}' not in matrix")
        return
        
    idx = player_to_idx[player_id]
    idx_to_player = mappings['idx_to_player']
    
    print(f"\nMatchup analysis for {player_name}:")
    print("="*50)
    
    # Get all matchups
    matchups = []
    for opp_idx in range(len(bt_matrix)):
        if opp_idx == idx:
            continue
            
        wins = bt_matrix[idx, opp_idx]
        losses = bt_matrix[opp_idx, idx]
        total = wins + losses
        
        if total > 0:
            opp_id = str(idx_to_player[str(opp_idx)])
            opp_name = player_names.get(opp_id, "Unknown")
            
            matchups.append({
                'opponent': opp_name,
                'wins': wins,
                'losses': losses,
                'total': total,
                'win_rate': wins / total if total > 0 else 0
            })
    
    # Sort by total games
    matchups.sort(key=lambda x: x['total'], reverse=True)
    
    # Show best matchups
    print("\nBest matchups (min 5 games):")
    best = [m for m in matchups if m['total'] >= 5 and m['win_rate'] >= 0.8]
    best.sort(key=lambda x: x['win_rate'], reverse=True)
    
    for m in best[:10]:
        print(f"  vs {m['opponent']}: {m['wins']}-{m['losses']} "
              f"({m['win_rate']:.1%})")
    
    # Show worst matchups
    print("\nWorst matchups (min 5 games):")
    worst = [m for m in matchups if m['total'] >= 5 and m['win_rate'] <= 0.2]
    worst.sort(key=lambda x: x['win_rate'])
    
    for m in worst[:10]:
        print(f"  vs {m['opponent']}: {m['wins']}-{m['losses']} "
              f"({m['win_rate']:.1%})")
    
    # Overall stats
    total_wins = sum(m['wins'] for m in matchups)
    total_games = sum(m['total'] for m in matchups)
    
    print(f"\nOverall: {total_wins}-{total_games-total_wins} "
          f"({total_wins/total_games:.1%} win rate)")


def find_similar_players(bt_matrix, mappings, analysis_df, player_name, top_n=10):
    """Find players with similar performance patterns"""
    
    # Find player
    player_names = mappings['player_names']
    player_id = None
    
    for pid, name in player_names.items():
        if player_name.lower() in name.lower():
            player_id = pid
            player_name = name
            break
    
    if player_id is None:
        print(f"Player '{player_name}' not found")
        return
    
    # Get player's win vector
    player_to_idx = mappings['player_to_idx']
    if player_id not in player_to_idx:
        print(f"Player '{player_name}' not in matrix")
        return
        
    idx = player_to_idx[player_id]
    player_wins = bt_matrix[idx, :]
    player_losses = bt_matrix[:, idx]
    
    # Calculate similarity with other players
    similarities = []
    
    for other_idx in range(len(bt_matrix)):
        if other_idx == idx:
            continue
            
        other_wins = bt_matrix[other_idx, :]
        other_losses = bt_matrix[:, other_idx]
        
        # Cosine similarity of win patterns
        dot_product = np.dot(player_wins, other_wins)
        norm1 = np.linalg.norm(player_wins)
        norm2 = np.linalg.norm(other_wins)
        
        if norm1 > 0 and norm2 > 0:
            similarity = dot_product / (norm1 * norm2)
            
            other_id = mappings['idx_to_player'][str(other_idx)]
            other_name = player_names.get(str(other_id), "Unknown")
            
            similarities.append({
                'player': other_name,
                'similarity': similarity,
                'win_rate': analysis_df[analysis_df['player_id'] == int(other_id)]['win_rate'].values[0]
                if not analysis_df[analysis_df['player_id'] == int(other_id)].empty else 0
            })
    
    # Sort by similarity
    similarities.sort(key=lambda x: x['similarity'], reverse=True)
    
    print(f"\nPlayers most similar to {player_name}:")
    print("="*50)
    
    for sim in similarities[:top_n]:
        print(f"  {sim['player']}: {sim['similarity']:.3f} similarity, "
              f"{sim['win_rate']:.1%} win rate")


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/visualize_bradley_terry.py [YEAR] [WEEK_SUFFIX]")
        print("Example: python src/visualize_bradley_terry.py 2024 weeks_1_to_9")
        print("\nDefault suffix is 'all_weeks'")
        sys.exit(1)
    
    season_year = int(sys.argv[1])
    suffix = sys.argv[2] if len(sys.argv) > 2 else "all_weeks"
    
    # Load data
    try:
        bt_matrix, mappings, analysis_df, stats_df = load_bradley_terry_data(season_year, suffix)
    except FileNotFoundError as e:
        print(f"Error: Could not find Bradley-Terry data for {season_year} with suffix '{suffix}'")
        print("Run fpl_player_prep.py first")
        sys.exit(1)
    
    print(f"Bradley-Terry Analysis for {season_year}/{season_year+1}")
    print(f"Data: {suffix}")
    print("="*60)
    
    # Show top performers
    print("\nTop 10 players by win rate:")
    top_players = analysis_df.head(10)
    for _, player in top_players.iterrows():
        print(f"  {player['name']}: {player['win_rate']:.1%} "
              f"({player['wins']}/{player['total_comparisons']})")
    
    # Interactive analysis
    while True:
        print("\n" + "-"*60)
        print("Options:")
        print("1. Analyze player matchups")
        print("2. Find similar players")
        print("3. Exit")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            player_name = input("Enter player name: ").strip()
            analyze_player_matchups(bt_matrix, mappings, player_name)
            
        elif choice == "2":
            player_name = input("Enter player name: ").strip()
            find_similar_players(bt_matrix, mappings, analysis_df, player_name)
            
        elif choice == "3":
            break
        
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()