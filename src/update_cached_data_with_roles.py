#!/usr/bin/env python3
"""
Update cached gameweek 39 data with role-specific Bradley-Terry scores
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from fpl_week_sampling_with_roles import calculate_enhanced_predictions


def update_gameweek_39_predictions():
    """Update gameweek 39 predictions with role-specific scores"""
    
    # Paths
    cache_dir = Path("data/cached_merged_2024_2025_v2")
    
    # Load merged player gameweek data
    print("Loading merged player gameweek data...")
    player_gw_df = pd.read_csv("data/cached_merged_2024_2025/merged_player_gameweek.csv")
    
    # Add role information
    # In merged data, position is already the role name
    player_gw_df['role'] = player_gw_df['position']
    
    # Also add player_id from element column
    player_gw_df['player_id'] = player_gw_df['element']
    
    # Add first_name and last_name from name
    player_gw_df['first_name'] = player_gw_df['name'].apply(lambda x: ' '.join(x.split()[:-1]) if len(x.split()) > 1 else x)
    player_gw_df['last_name'] = player_gw_df['name'].apply(lambda x: x.split()[-1] if len(x.split()) > 1 else '')
    
    # Add gameweek from GW column
    player_gw_df['gameweek'] = player_gw_df['GW']
    
    # Add now_cost from value
    player_gw_df['now_cost'] = player_gw_df['value']
    
    # Calculate predictions with role-specific scores
    print("\nCalculating enhanced predictions for gameweek 39...")
    pred_df = calculate_enhanced_predictions(player_gw_df, week_limit=38, cache_dir=cache_dir)
    
    # Update the weighted_score to be the new average_score for compatibility
    pred_df['average_score'] = pred_df['weighted_score']
    
    # Match with player mapping to get correct names and teams for 2025
    mapping_df = pd.read_csv(cache_dir / "player_mapping_gw39.csv")
    
    # For merged data, we need to match by player name since we don't have direct ID mapping
    # Create a name column in pred_df for matching
    pred_df['full_name'] = pred_df['first_name'] + ' ' + pred_df['last_name']
    
    # Merge with mapping to get 2025 information
    pred_df = pred_df.merge(
        mapping_df[['player_2024', 'player_2025', 'team_2025']], 
        left_on='full_name', 
        right_on='player_2024',
        how='left'
    )
    
    # Update team names for 2025
    pred_df['club'] = pred_df['team_2025'].fillna(pred_df['team'])
    
    # Filter out players who don't have valid 2025 mappings
    # Get valid 2025 teams from mapping
    valid_2025_teams = mapping_df['team_2025'].dropna().unique()
    print(f"\\nValid 2025 teams: {sorted(valid_2025_teams)}")
    
    # Only keep players who have explicit 2025 mappings
    # This ensures we only include players who are actually in the 2025 season
    valid_players = pred_df[pred_df['team_2025'].notna()].copy()
    
    print(f"\\nFiltered from {len(pred_df)} to {len(valid_players)} players")
    
    # Remove duplicate player_ids (keep the one with highest score)
    valid_players = valid_players.sort_values('weighted_score', ascending=False).drop_duplicates(['player_id'], keep='first')
    
    print(f"\\nAfter removing duplicate player_ids: {len(valid_players)} players")
    
    # Save updated predictions
    output_cols = ['first_name', 'last_name', 'club', 'gameweek', 'price', 
                   'player_score', 'team_score', 'role_score', 'average_score', 
                   'weighted_score', 'role', 'player_id']
    
    final_df = valid_players[output_cols].copy()
    final_df.to_csv(cache_dir / "predictions_gw39_with_roles.csv", index=False)
    
    print(f"\nSaved updated predictions to {cache_dir}/predictions_gw39_with_roles.csv")
    print(f"Total players: {len(final_df)}")
    
    # Show example of score breakdown
    print("\nExample score breakdowns (top 5 by weighted score):")
    top5 = final_df.nlargest(5, 'weighted_score')
    for _, p in top5.iterrows():
        print(f"\n{p['first_name']} {p['last_name']} ({p['club']}, {p['role']}):")
        print(f"  Player Score: {p['player_score']:.2f}")
        print(f"  Team Score: {p['team_score']:.2f} (weighted 0.5x = {0.5*p['team_score']:.2f})")
        print(f"  Role Score: {p['role_score']:.2f}")
        print(f"  Weighted: ({p['player_score']:.2f} + {0.5*p['team_score']:.2f} + {p['role_score']:.2f}) / 3 = {p['weighted_score']:.2f}")
    
    return final_df


def update_optimization_script():
    """Update the optimization script to use new predictions"""
    
    print("\nUpdating optimized_gw39_teams.py to use new predictions...")
    
    # Read the current optimization script
    with open("src/optimized_gw39_teams.py", 'r') as f:
        content = f.read()
    
    # Update the predictions file path
    content = content.replace(
        'pred_file = "data/cached_merged_2024_2025_v2/predictions_gw39.csv"',
        'pred_file = "data/cached_merged_2024_2025_v2/predictions_gw39_with_roles.csv"'
    )
    
    # Update the scoring description in comments
    content = content.replace(
        '- Uses weighted score: 0.5 * (player_score + team_weight * team_score)',
        '- Uses weighted score: 1/3 * (player_score + 0.5 * team_score + role_score)'
    )
    
    # Update the calculation (remove the old calculation since we pre-calculate it now)
    content = content.replace(
        "# Calculate weighted average score\n    df['weighted_score'] = 0.5 * (df['player_score'] + team_weight * df['team_score'])",
        "# Weighted score already calculated: 1/3 * (player_score + 0.5 * team_score + role_score)"
    )
    
    # Save updated script
    with open("src/optimized_gw39_teams.py", 'w') as f:
        f.write(content)
    
    print("Updated optimization script")


def main():
    # Update predictions with role-specific scores
    pred_df = update_gameweek_39_predictions()
    
    # Update optimization script
    update_optimization_script()
    
    print("\n✓ All updates completed!")
    print("\nNext steps:")
    print("1. Run: python src/optimized_gw39_teams.py")
    print("2. This will regenerate top 200 teams with new scoring")


if __name__ == "__main__":
    main()