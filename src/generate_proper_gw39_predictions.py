#!/usr/bin/env python3
"""
Generate proper gameweek 39 predictions starting from 2025 player list
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from fpl_week_sampling_with_roles import build_bradley_terry_matrices_with_roles, fit_bradley_terry_model


def main():
    # Paths
    cache_dir = Path("data/cached_merged_2024_2025_v2")
    
    print("Loading data...")
    
    # 1. Start with 2025 players as the base
    players_2025 = pd.read_csv("data/2025/2025_players.csv")
    players_2025['full_name'] = players_2025['first_name'] + ' ' + players_2025['second_name']
    
    # 2. Load the player mapping
    mapping_df = pd.read_csv(cache_dir / "player_mapping_gw39.csv")
    
    # 3. Load merged gameweek data for historical stats
    merged_gw = pd.read_csv("data/cached_merged_2024_2025/merged_player_gameweek.csv")
    
    # Map element_type to role
    element_type_to_role = {
        1: 'GK',
        2: 'DEF',
        3: 'MID',
        4: 'FWD'
    }
    
    # Process each 2025 player
    predictions = []
    
    for _, player_2025 in players_2025.iterrows():
        player_name = player_2025['full_name']
        team_2025 = player_2025['team_name']
        element_type = player_2025['element_type']
        role = element_type_to_role.get(element_type, 'MID')
        price = player_2025['now_cost']  # Already in millions for 2025 data
        
        # Find mapping for this player
        mapping = mapping_df[mapping_df['player_2025'] == player_name]
        
        if len(mapping) > 0:
            # Get the 2024 player name for stats lookup
            player_2024 = mapping.iloc[0]['player_2024']
            team_2024 = mapping.iloc[0]['team_2024']
            
            # Get stats from merged gameweek data
            if pd.notna(player_2024):
                player_stats = merged_gw[merged_gw['name'] == player_2024]
                
                if len(player_stats) > 0:
                    # Calculate average points
                    avg_points = player_stats['total_points'].mean()
                    total_points = player_stats['total_points'].sum()
                    games = len(player_stats)
                else:
                    avg_points = 2.0  # Default for players with no stats
                    total_points = 0
                    games = 0
            else:
                avg_points = 2.0
                total_points = 0
                games = 0
        else:
            # No mapping found - use defaults
            avg_points = 2.0
            total_points = 0
            games = 0
        
        # For now, use simple scoring (will be updated with Bradley-Terry)
        predictions.append({
            'player_id': player_2025['id'],
            'first_name': player_2025['first_name'],
            'last_name': player_2025['second_name'],
            'full_name': player_name,
            'club': team_2025,
            'role': role,
            'price': price,
            'avg_points': avg_points,
            'total_points': total_points,
            'games': games,
            'gameweek': 39
        })
    
    pred_df = pd.DataFrame(predictions)
    
    print(f"\\nCreated predictions for {len(pred_df)} players")
    print(f"\\nTeam distribution:")
    print(pred_df['club'].value_counts())
    
    # Now calculate Bradley-Terry scores
    print("\\nCalculating Bradley-Terry scores...")
    
    # Build matrices from historical data
    merged_gw['role'] = merged_gw['position']
    merged_gw['player_id'] = merged_gw['element']
    merged_gw['gameweek'] = merged_gw['GW']
    
    # Build Bradley-Terry matrices
    player_comparisons, team_comparisons, role_comparisons, player_roles = \
        build_bradley_terry_matrices_with_roles(merged_gw[merged_gw['gameweek'] <= 38])
    
    # Fit models
    player_strengths = fit_bradley_terry_model(player_comparisons)
    team_strengths = fit_bradley_terry_model(team_comparisons)
    
    role_strengths = {}
    for role, comparisons in role_comparisons.items():
        role_strengths[role] = fit_bradley_terry_model(comparisons)
    
    # Apply Bradley-Terry scores to predictions
    for idx, row in pred_df.iterrows():
        # Use average points as base
        base_score = row['avg_points']
        
        # Get team strength (use 2024 team mapping if available)
        team = row['club']
        # Map to 2024 team if it's a promoted team
        team_map = {'Burnley': 'Leicester', 'Leeds': 'Ipswich', 'Sunderland': 'Southampton'}
        team_for_bt = team_map.get(team, team)
        
        # Get strengths
        team_strength = team_strengths.get(team_for_bt, 0.001)
        
        # Default scores
        player_score = base_score
        team_score = base_score * (0.5 + 1.5 * team_strength / max(team_strengths.values())) if team_strengths else base_score
        role_score = base_score
        
        # Calculate weighted score
        weighted_score = (player_score + 0.5 * team_score + role_score) / 3
        
        pred_df.loc[idx, 'player_score'] = player_score
        pred_df.loc[idx, 'team_score'] = team_score
        pred_df.loc[idx, 'role_score'] = role_score
        pred_df.loc[idx, 'weighted_score'] = weighted_score
        pred_df.loc[idx, 'average_score'] = weighted_score  # For compatibility
    
    # Save predictions
    output_file = cache_dir / "predictions_gw39_proper.csv"
    pred_df.to_csv(output_file, index=False)
    
    print(f"\\nSaved predictions to {output_file}")
    print(f"\\nTop 10 players by weighted score:")
    top10 = pred_df.nlargest(10, 'weighted_score')
    for _, p in top10.iterrows():
        print(f"  {p['full_name']} ({p['club']}, {p['role']}): {p['weighted_score']:.2f}")
    
    # Update optimization script to use new file
    print("\\nUpdating optimization script...")
    with open("src/optimized_gw39_teams.py", 'r') as f:
        content = f.read()
    
    content = content.replace(
        'pred_file = "data/cached_merged_2024_2025_v2/predictions_gw39_with_roles.csv"',
        'pred_file = "data/cached_merged_2024_2025_v2/predictions_gw39_proper.csv"'
    )
    
    with open("src/optimized_gw39_teams.py", 'w') as f:
        f.write(content)
    
    print("Done!")


if __name__ == "__main__":
    main()