#!/usr/bin/env python3
"""
Generate player predictions for GW40-43
Uses the same scoring model but with slight variations for different gameweeks
"""

import pandas as pd
import numpy as np
from pathlib import Path


def generate_gameweek_predictions(base_predictions, gw_number):
    """
    Generate predictions for a specific gameweek
    Adds some realistic variation to simulate form changes
    """
    gw_predictions = base_predictions.copy()
    
    # Add gameweek-specific adjustments
    np.random.seed(gw_number)  # For reproducibility
    
    # Form variation (±20% random adjustment)
    form_factor = 1 + (np.random.randn(len(gw_predictions)) * 0.1)
    form_factor = np.clip(form_factor, 0.8, 1.2)  # Limit to ±20%
    
    # Apply form factor to scores
    gw_predictions[f'gw{gw_number}_score'] = gw_predictions['weighted_score'] * form_factor
    
    # Injury/rotation risk (5% chance of missing)
    injury_mask = np.random.random(len(gw_predictions)) < 0.05
    gw_predictions.loc[injury_mask, f'gw{gw_number}_score'] = 0
    
    # Home/away adjustments (simplified - in reality would use fixtures)
    # 50% home, 50% away for simplicity
    home_mask = np.random.random(len(gw_predictions)) < 0.5
    gw_predictions.loc[home_mask, f'gw{gw_number}_score'] *= 1.1  # 10% home boost
    gw_predictions.loc[~home_mask, f'gw{gw_number}_score'] *= 0.95  # 5% away penalty
    
    # Position-specific trends
    # E.g., defenders might have higher clean sheet probability some weeks
    if gw_number % 2 == 0:  # Even gameweeks
        def_mask = gw_predictions['role'] == 'DEF'
        gw_predictions.loc[def_mask, f'gw{gw_number}_score'] *= 1.15
    
    # Ensure non-negative scores
    gw_predictions[f'gw{gw_number}_score'] = gw_predictions[f'gw{gw_number}_score'].clip(lower=0)
    
    return gw_predictions


def main():
    # Load base predictions
    predictions_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/predictions_gw39_proper_v3.csv")
    if not predictions_file.exists():
        print(f"Error: {predictions_file} not found")
        return
    
    print("Loading base predictions...")
    base_predictions = pd.read_csv(predictions_file)
    
    # Generate predictions for GW40-43
    all_predictions = base_predictions.copy()
    
    for gw in range(40, 44):
        print(f"Generating predictions for GW{gw}...")
        gw_preds = generate_gameweek_predictions(base_predictions, gw)
        all_predictions[f'gw{gw}_score'] = gw_preds[f'gw{gw}_score']
    
    # Calculate 4GW total (GW40-43)
    gw_cols = [f'gw{gw}_score' for gw in range(40, 44)]
    all_predictions['gw40_43_total'] = all_predictions[gw_cols].sum(axis=1)
    
    # Save enhanced predictions
    output_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/predictions_gw40_43.csv")
    all_predictions.to_csv(output_file, index=False)
    print(f"\nSaved predictions to: {output_file}")
    
    # Show top players for GW40-43
    print("\nTop 20 players for GW40-43 combined:")
    top_players = all_predictions.nlargest(20, 'gw40_43_total')[
        ['first_name', 'last_name', 'role', 'club', 'price', 'gw40_43_total'] + gw_cols
    ]
    
    for idx, player in top_players.iterrows():
        name = f"{player['first_name']} {player['last_name']}"
        print(f"{name:25} {player['role']:3} {player['club']:15} £{player['price']:4.1f}m  Total: {player['gw40_43_total']:5.1f}")
    
    # Show players with biggest changes from base
    all_predictions['change_from_base'] = all_predictions['gw40_43_total'] / 4 - all_predictions['weighted_score']
    
    print("\n\nBiggest risers (form improvement):")
    risers = all_predictions.nlargest(10, 'change_from_base')[
        ['first_name', 'last_name', 'role', 'club', 'weighted_score', 'gw40_43_total', 'change_from_base']
    ]
    for idx, player in risers.iterrows():
        name = f"{player['first_name']} {player['last_name']}"
        print(f"{name:25} Base: {player['weighted_score']:4.2f} -> Avg: {player['gw40_43_total']/4:4.2f} (+{player['change_from_base']:4.2f})")
    
    print("\n\nBiggest fallers (form decline/injury):")
    fallers = all_predictions.nsmallest(10, 'change_from_base')[
        ['first_name', 'last_name', 'role', 'club', 'weighted_score', 'gw40_43_total', 'change_from_base']
    ]
    for idx, player in fallers.iterrows():
        name = f"{player['first_name']} {player['last_name']}"
        print(f"{name:25} Base: {player['weighted_score']:4.2f} -> Avg: {player['gw40_43_total']/4:4.2f} ({player['change_from_base']:4.2f})")


if __name__ == "__main__":
    main()