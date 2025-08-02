#!/usr/bin/env python3
"""
Generate predictions for gameweek 39 with all score components including fixture difficulty
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from src.fpl_week_sampling_with_roles import fit_bradley_terry_model_with_uncertainty


def load_fixtures(fixtures_file):
    """Load fixture data and create opponent mapping"""
    fixtures_df = pd.read_csv(fixtures_file)
    
    # Create opponent mapping for each gameweek
    opponent_map = {}
    
    for _, row in fixtures_df.iterrows():
        gw = row['event']
        home_team = row['home_team_name']
        away_team = row['away_team_name']
        
        if gw not in opponent_map:
            opponent_map[gw] = {}
        
        # Map both directions
        opponent_map[gw][home_team] = (away_team, 'home')
        opponent_map[gw][away_team] = (home_team, 'away')
    
    return opponent_map


def calculate_fixture_score(player_team, opponent_team, team_scores, fixture_weight=2.0):
    """
    Calculate fixture score based on team strength difference
    
    fixture_score = fixture_weight * (player_team_score - opponent_team_score)
    
    Positive means favorable fixture, negative means difficult fixture
    """
    player_team_score = team_scores.get(player_team, 0.5)  # Default to 0.5 if not found
    opponent_team_score = team_scores.get(opponent_team, 0.5)
    
    # Calculate raw difference
    score_diff = player_team_score - opponent_team_score
    
    # Apply fixture weight
    fixture_score = fixture_weight * score_diff
    
    return fixture_score


def main():
    # Parameters
    gameweek = 39
    fixture_weight = 2.0  # Default fixture weight
    
    # Load merged data
    print("Loading merged data...")
    df_merged = pd.read_csv("../data/cached_merged_2024_2025_v2/merged_data_with_teams.csv")
    
    # Load fixtures
    print("Loading fixture data...")
    opponent_map = load_fixtures("../data/cached_merged_2024_2025/merged_fixtures.csv")
    
    # Load team scores
    print("Loading team scores...")
    team_df = pd.read_csv("../data/cached_merged_2024_2025_v2/merged_teams_all.csv")
    team_scores = dict(zip(team_df['name'], team_df['score']))
    
    # Filter for gameweek 39
    print(f"\nProcessing gameweek {gameweek} data...")
    df_gw = df_merged[df_merged['gameweek'] == gameweek].copy()
    
    print(f"Players in GW{gameweek}: {len(df_gw)}")
    
    # Prepare data for Bradley-Terry models
    print("\nPreparing player comparisons...")
    player_comparisons = {}
    role_comparisons = {'GK': {}, 'DEF': {}, 'MID': {}, 'FWD': {}}
    abs_comparisons = {}  # For absolute points comparison
    
    # Get all gameweeks for comparison
    all_gameweeks = sorted(df_merged['gameweek'].unique())
    comparison_gameweeks = [gw for gw in all_gameweeks if gw < gameweek][-10:]  # Last 10 gameweeks
    
    print(f"Using gameweeks {comparison_gameweeks[0]}-{comparison_gameweeks[-1]} for comparisons")
    
    # Build comparisons
    for gw in comparison_gameweeks:
        gw_data = df_merged[df_merged['gameweek'] == gw]
        
        # Group by gameweek for pairwise comparisons
        for _, group in gw_data.groupby('gameweek'):
            players = group.to_dict('records')
            
            # Compare all pairs
            for i in range(len(players)):
                for j in range(i + 1, len(players)):
                    p1, p2 = players[i], players[j]
                    
                    # Skip if same player
                    if p1['player_id'] == p2['player_id']:
                        continue
                    
                    p1_name = f"{p1['first_name']} {p1['last_name']}"
                    p2_name = f"{p2['first_name']} {p2['last_name']}"
                    
                    # Overall comparison
                    if p1['total_points'] > p2['total_points']:
                        winner, loser = p1_name, p2_name
                        win_points = p1['total_points']
                        lose_points = p2['total_points']
                    else:
                        winner, loser = p2_name, p1_name
                        win_points = p2['total_points']
                        lose_points = p1['total_points']
                    
                    if winner not in player_comparisons:
                        player_comparisons[winner] = {}
                    if loser not in player_comparisons[winner]:
                        player_comparisons[winner][loser] = 0
                    player_comparisons[winner][loser] += 1
                    
                    # Absolute points comparison (track both directions with points)
                    # Add winner's points to winner->loser
                    if winner not in abs_comparisons:
                        abs_comparisons[winner] = {}
                    if loser not in abs_comparisons[winner]:
                        abs_comparisons[winner][loser] = 0
                    abs_comparisons[winner][loser] += win_points
                    
                    # Add loser's points to loser->winner
                    if loser not in abs_comparisons:
                        abs_comparisons[loser] = {}
                    if winner not in abs_comparisons[loser]:
                        abs_comparisons[loser][winner] = 0
                    abs_comparisons[loser][winner] += lose_points
                    
                    # Role-specific comparison
                    if p1['role'] == p2['role']:
                        role = p1['role']
                        if winner not in role_comparisons[role]:
                            role_comparisons[role][winner] = {}
                        if loser not in role_comparisons[role][winner]:
                            role_comparisons[role][winner][loser] = 0
                        role_comparisons[role][winner][loser] += 1
    
    # Fit Bradley-Terry models
    print("\nFitting Bradley-Terry models...")
    
    # Overall player model with uncertainty
    player_scores_dict, player_uncertainties = fit_bradley_terry_model_with_uncertainty(
        player_comparisons, temperature=3.0
    )
    
    # Role-specific models with uncertainty
    role_scores_dict = {}
    role_uncertainties_dict = {}
    for role in ['GK', 'DEF', 'MID', 'FWD']:
        if role_comparisons[role]:
            scores, uncertainties = fit_bradley_terry_model_with_uncertainty(
                role_comparisons[role], temperature=3.0
            )
            role_scores_dict[role] = scores
            role_uncertainties_dict[role] = uncertainties
    
    # Absolute score model with uncertainty (using score differences)
    abs_scores_dict, abs_uncertainties = fit_bradley_terry_model_with_uncertainty(
        abs_comparisons, temperature=3.0
    )
    
    # Load role weights
    role_weights = {
        'FWD': 0.3347 * 4,  # 4x multiplier as requested
        'MID': 0.2630 * 4,
        'GK': 0.2121 * 4,
        'DEF': 0.1902 * 4
    }
    
    # Generate predictions for gameweek 39
    print(f"\nGenerating predictions for gameweek {gameweek}...")
    predictions = []
    
    # Get GW39 opponents
    gw39_opponents = opponent_map.get(gameweek, {})
    
    for _, player in df_gw.iterrows():
        player_name = f"{player['first_name']} {player['last_name']}"
        player_club = player['club']
        
        # Get scores
        player_score = player_scores_dict.get(player_name, 0.5)
        team_score = team_scores.get(player_club, 0.5)
        
        # Role score
        role = player['role']
        if role in role_scores_dict:
            role_score = role_scores_dict[role].get(player_name, 0.5)
        else:
            role_score = 0.5
        
        # Weighted role score
        role_weight = role_weights.get(role, 0.2)
        weighted_role_score = role_weight * role_score
        
        # Absolute score
        abs_score = abs_scores_dict.get(player_name, 0.5)
        
        # Calculate fixture score
        fixture_score = 0.0
        opponent_info = gw39_opponents.get(player_club)
        
        if opponent_info:
            opponent_team, venue = opponent_info
            fixture_score = calculate_fixture_score(player_club, opponent_team, team_scores, fixture_weight)
        else:
            print(f"Warning: No fixture found for {player_club} in GW{gameweek}")
        
        # Calculate weighted score with fixture component
        # E[player_score + alpha * team_score + role_weight * role_score + abs_weight * abs_score + fixture_score]
        # E is expectation (1/5), alpha = 0.5, abs_weight = 2.0
        weighted_score = (player_score + 0.5 * team_score + weighted_role_score + 2.0 * abs_score + fixture_score) / 5
        
        # Create prediction entry
        prediction = {
            'player_id': player['player_id'],
            'first_name': player['first_name'],
            'last_name': player['last_name'],
            'full_name': player_name,
            'club': player_club,
            'role': role,
            'price': player['price'],
            'avg_points': player['average_points'],
            'total_points': player['total_points'],
            'games': player['games_played'],
            'gameweek': gameweek,
            'player_score': player_score,
            'team_score': team_score,
            'role_score': role_score,
            'abs_score': abs_score,
            'fixture_score': fixture_score,
            'weighted_score': weighted_score,
            'average_score': player['average_score'] if 'average_score' in player else 0,
            'opponent': opponent_info[0] if opponent_info else 'Unknown',
            'venue': opponent_info[1] if opponent_info else 'Unknown'
        }
        
        predictions.append(prediction)
    
    # Convert to DataFrame
    predictions_df = pd.DataFrame(predictions)
    
    # Sort by weighted score
    predictions_df = predictions_df.sort_values('weighted_score', ascending=False)
    
    # Save predictions
    output_file = "../data/cached_merged_2024_2025_v2/predictions_gw39_proper_v2.csv"
    predictions_df.to_csv(output_file, index=False)
    
    print(f"\nSaved predictions to {output_file}")
    
    # Show top players by position
    print("\nTop players by position:")
    for role in ['GK', 'DEF', 'MID', 'FWD']:
        print(f"\n{role}:")
        role_df = predictions_df[predictions_df['role'] == role].head(5)
        for _, p in role_df.iterrows():
            opponent_str = f"vs {p['opponent']} ({p['venue']})"
            print(f"  {p['full_name']} ({p['club']}) {opponent_str}: {p['weighted_score']:.3f} "
                  f"(fixture: {p['fixture_score']:.3f})")
    
    # Show impact of fixture scores
    print("\nFixture score impact analysis:")
    print(f"Average fixture score: {predictions_df['fixture_score'].mean():.3f}")
    print(f"Best fixtures (top 5):")
    best_fixtures = predictions_df.nlargest(5, 'fixture_score')
    for _, p in best_fixtures.iterrows():
        print(f"  {p['full_name']} ({p['club']}) vs {p['opponent']}: {p['fixture_score']:.3f}")
    
    print(f"\nWorst fixtures (bottom 5):")
    worst_fixtures = predictions_df.nsmallest(5, 'fixture_score')
    for _, p in worst_fixtures.iterrows():
        print(f"  {p['full_name']} ({p['club']}) vs {p['opponent']}: {p['fixture_score']:.3f}")


if __name__ == "__main__":
    main()