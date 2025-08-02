#!/usr/bin/env python3
"""
Calculate role weights based on 2024 season data
Weight = normalized (total_points / total_minutes) for each role
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path


def calculate_role_weights():
    """Calculate role weights from 2024 gameweek data"""
    
    print("Loading 2024 gameweek data...")
    gameweek_df = pd.read_csv("data/2024/2024_player_gameweek.csv")
    
    # Position is already the role in gameweek data
    gameweek_df['role'] = gameweek_df['position']
    
    # Calculate total points and minutes per role
    role_stats = {}
    
    for role in ['GK', 'DEF', 'MID', 'FWD']:
        role_data = gameweek_df[gameweek_df['role'] == role]
        
        total_points = role_data['total_points'].sum()
        total_minutes = role_data['minutes'].sum()
        
        # Avoid division by zero
        if total_minutes > 0:
            points_per_minute = total_points / total_minutes
        else:
            points_per_minute = 0
            
        role_stats[role] = {
            'total_points': int(total_points),
            'total_minutes': int(total_minutes),
            'points_per_minute': float(points_per_minute)
        }
        
        print(f"\n{role}:")
        print(f"  Total points: {total_points:,.0f}")
        print(f"  Total minutes: {total_minutes:,.0f}")
        print(f"  Points per minute: {points_per_minute:.6f}")
    
    # Calculate normalized weights
    total_ppm = sum(stats['points_per_minute'] for stats in role_stats.values())
    
    role_weights = {}
    print("\nNormalized role weights:")
    for role, stats in role_stats.items():
        weight = stats['points_per_minute'] / total_ppm if total_ppm > 0 else 0.25
        role_weights[role] = weight
        print(f"  {role}: {weight:.4f} ({weight*100:.1f}%)")
    
    # Save to JSON
    output_data = {
        'role_stats': role_stats,
        'role_weights': role_weights,
        'description': 'Role weights based on total points per total minutes played in 2024 season'
    }
    
    output_path = Path("data/cached_merged_2024_2025_v2/role_weights_2024.json")
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nSaved role weights to {output_path}")
    
    return role_weights


def main():
    role_weights = calculate_role_weights()
    
    # Verify weights sum to 1
    total = sum(role_weights.values())
    print(f"\nVerification: Sum of weights = {total:.6f}")


if __name__ == "__main__":
    main()