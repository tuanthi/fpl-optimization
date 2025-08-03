#!/usr/bin/env python3
"""
Add fixture scores to existing predictions based on team strength differences
"""

import pandas as pd
import numpy as np


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
    
    # Load existing predictions
    print("Loading existing predictions...")
    predictions_df = pd.read_csv("../data/cached_merged_2024_2025_v2/predictions_gw39_proper.csv")
    
    # Load fixtures
    print("Loading fixture data...")
    fixtures_df = pd.read_csv("../data/cached_merged_2024_2025/merged_fixtures.csv")
    opponent_map = load_fixtures("../data/cached_merged_2024_2025/merged_fixtures.csv")
    
    # Extract team scores from the predictions (use average team_score)
    print("Calculating team scores...")
    team_scores = predictions_df.groupby('club')['team_score'].mean().to_dict()
    
    print(f"\nProcessing gameweek {gameweek} fixtures...")
    
    # Get GW39 opponents
    gw39_opponents = opponent_map.get(gameweek, {})
    
    # Add fixture scores to predictions
    fixture_scores = []
    opponents = []
    venues = []
    
    for _, player in predictions_df.iterrows():
        player_club = player['club']
        
        # Calculate fixture score
        fixture_score = 0.0
        opponent_info = gw39_opponents.get(player_club)
        
        if opponent_info:
            opponent_team, venue = opponent_info
            fixture_score = calculate_fixture_score(player_club, opponent_team, team_scores, fixture_weight)
            opponents.append(opponent_team)
            venues.append(venue)
        else:
            print(f"Warning: No fixture found for {player_club} in GW{gameweek}")
            opponents.append('Unknown')
            venues.append('Unknown')
        
        fixture_scores.append(fixture_score)
    
    # Add to dataframe
    predictions_df['fixture_score'] = fixture_scores
    predictions_df['opponent'] = opponents
    predictions_df['venue'] = venues
    
    # Update weighted score with fixture component
    # E[player_score + alpha * team_score + role_weight * role_score + abs_weight * abs_score + fixture_score]
    # E is expectation (1/5), alpha = 0.5, abs_weight = 2.0
    
    # Recalculate weighted score
    role_weights = {
        'FWD': 0.3347 * 4,  # 4x multiplier
        'MID': 0.2630 * 4,
        'GK': 0.2121 * 4,
        'DEF': 0.1902 * 4
    }
    
    new_weighted_scores = []
    for _, player in predictions_df.iterrows():
        role_weight = role_weights.get(player['role'], 0.2)
        weighted_role_score = role_weight * player['role_score']
        
        # New formula with fixture score
        weighted_score = (
            player['player_score'] + 
            0.5 * player['team_score'] + 
            weighted_role_score + 
            2.0 * player['abs_score'] + 
            player['fixture_score']
        ) / 5
        
        new_weighted_scores.append(weighted_score)
    
    predictions_df['weighted_score'] = new_weighted_scores
    
    # Sort by new weighted score
    predictions_df = predictions_df.sort_values('weighted_score', ascending=False)
    
    # Save updated predictions
    output_file = "../data/cached_merged_2024_2025_v2/predictions_gw39_proper_v2.csv"
    predictions_df.to_csv(output_file, index=False)
    
    print(f"\nSaved updated predictions to {output_file}")
    
    # Show top players by position
    print("\nTop players by position (with fixture consideration):")
    for role in ['GK', 'DEF', 'MID', 'FWD']:
        print(f"\n{role}:")
        role_df = predictions_df[predictions_df['role'] == role].head(5)
        for _, p in role_df.iterrows():
            opponent_str = f"vs {p['opponent']} ({p['venue']})"
            print(f"  {p['first_name']} {p['last_name']} ({p['club']}) {opponent_str}: {p['weighted_score']:.3f} "
                  f"(fixture: {p['fixture_score']:.3f})")
    
    # Show impact of fixture scores
    print("\nFixture score impact analysis:")
    print(f"Average fixture score: {predictions_df['fixture_score'].mean():.3f}")
    
    print(f"\nBest fixtures (top 5):")
    best_fixtures = predictions_df.nlargest(5, 'fixture_score')
    for _, p in best_fixtures.iterrows():
        print(f"  {p['first_name']} {p['last_name']} ({p['club']}) vs {p['opponent']}: {p['fixture_score']:.3f}")
    
    print(f"\nWorst fixtures (bottom 5):")
    worst_fixtures = predictions_df.nsmallest(5, 'fixture_score')
    for _, p in worst_fixtures.iterrows():
        print(f"  {p['first_name']} {p['last_name']} ({p['club']}) vs {p['opponent']}: {p['fixture_score']:.3f}")
    
    # Compare top players before and after fixture adjustment
    print("\n\nTop 10 players comparison (before vs after fixture adjustment):")
    # Load original predictions
    original_df = pd.read_csv("../data/cached_merged_2024_2025_v2/predictions_gw39_proper.csv")
    original_top10 = original_df.nlargest(10, 'weighted_score')[['first_name', 'last_name', 'club', 'weighted_score']]
    new_top10 = predictions_df.nlargest(10, 'weighted_score')[['first_name', 'last_name', 'club', 'weighted_score', 'fixture_score', 'opponent']]
    
    print("\nOriginal Top 10:")
    for i, (_, p) in enumerate(original_top10.iterrows(), 1):
        print(f"{i}. {p['first_name']} {p['last_name']} ({p['club']}): {p['weighted_score']:.3f}")
    
    print("\nNew Top 10 (with fixtures):")
    for i, (_, p) in enumerate(new_top10.iterrows(), 1):
        print(f"{i}. {p['first_name']} {p['last_name']} ({p['club']}) vs {p['opponent']}: {p['weighted_score']:.3f} (fixture: {p['fixture_score']:.3f})")


if __name__ == "__main__":
    main()