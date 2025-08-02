#!/usr/bin/env python3
"""
Fix prices for gameweek 39 predictions to use 2025 season starting prices
"""

import pandas as pd
from pathlib import Path
import subprocess


def main():
    print("Fixing gameweek 39 prices to use 2025 season starting prices...")
    
    # Paths
    data_dir = Path("data")
    cache_dir = data_dir / "cached_merged_2024_2025"
    
    # Load 2025 players to get correct starting prices
    players_2025 = pd.read_csv(data_dir / "2025" / "2025_players.csv")
    teams_2025 = pd.read_csv(data_dir / "2025" / "2025_teams.csv")
    
    # Create team ID to name mapping
    team_id_to_name = dict(zip(teams_2025['id'], teams_2025['name']))
    
    # Build comprehensive price lookup
    price_lookup = {}
    for _, player in players_2025.iterrows():
        # Create multiple lookup keys for robust matching
        first_name = player['first_name']
        second_name = player['second_name']
        web_name = player['web_name']
        team_name = team_id_to_name.get(player['team'], 'Unknown')
        price = player['now_cost'] / 10  # Convert to millions
        
        # Add various key combinations
        price_lookup[(first_name, second_name, team_name)] = price
        price_lookup[(first_name, second_name)] = price
        price_lookup[(web_name, team_name)] = price
        
        # Special handling for complex names
        if ' ' in second_name:
            # For names like "Raya Martin", also add just "Raya"
            short_last = second_name.split()[0]
            price_lookup[(first_name, short_last, team_name)] = price
    
    print(f"✓ Loaded {len(players_2025)} players from 2025 season")
    
    # Load the current prediction file  
    pred_file = cache_dir / "pred_merged_week_sampling_1_to_38_fixed.csv"
    if not pred_file.exists():
        print(f"Error: {pred_file} not found. Run fix_and_cache_merged_data.py first.")
        return
        
    pred_df = pd.read_csv(pred_file)
    print(f"✓ Loaded prediction data with {len(pred_df)} rows")
    
    # Create a simulated gameweek 39 by duplicating gameweek 38 data
    gw38_data = pred_df[pred_df['gameweek'] == 38].copy()
    gw38_data['gameweek'] = 39
    
    # Update prices for gameweek 39 with 2025 season starting prices
    print("\nUpdating gameweek 39 prices:")
    updates = 0
    for idx in gw38_data.index:
        row = gw38_data.loc[idx]
        
        # Try different key combinations
        keys_to_try = [
            (row['first_name'], row['last_name'], row['club']),
            (row['first_name'], row['last_name']),
            (f"{row['first_name']} {row['last_name']}", row['club'])
        ]
        
        for key in keys_to_try:
            if key in price_lookup:
                new_price = price_lookup[key]
                old_price = row['price']
                if abs(new_price - old_price) > 0.01:  # Only update if different
                    gw38_data.loc[idx, 'price'] = new_price
                    if updates < 10:  # Show first 10 updates
                        print(f"  {row['first_name']} {row['last_name']} ({row['club']}): £{old_price:.1f}m -> £{new_price:.1f}m")
                    updates += 1
                break
    
    print(f"\n✓ Updated {updates} prices for gameweek 39")
    
    # Append gameweek 39 data to the prediction dataframe
    pred_df_with_gw39 = pd.concat([pred_df, gw38_data], ignore_index=True)
    
    # Save updated prediction file
    output_file = cache_dir / "pred_merged_week_sampling_1_to_39_fixed.csv"
    pred_df_with_gw39.to_csv(output_file, index=False)
    print(f"✓ Saved updated prediction file to {output_file}")
    
    # Run optimization with the updated data
    print("\nRunning optimization with corrected prices...")
    cmd = [
        "python", "src/fast_optimization_runner.py",
        str(output_file),
        str(cache_dir / "merged_top_50_teams_gameweek_39_fixed.csv")
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Optimization completed successfully")
        
        # Verify the results
        final_file = cache_dir / "merged_top_50_teams_gameweek_39_fixed.csv"
        if final_file.exists():
            df = pd.read_csv(final_file)
            print("\nVerifying top team prices:")
            
            # Check GK prices
            for col in ['GK1', 'GK2']:
                if col in df.columns:
                    player_info = df.iloc[0][col]
                    price = df.iloc[0][f'{col}_price']
                    print(f"  {col}: {player_info} - £{price:.1f}m")
                    
                    # Verify specific players
                    if "Robert Sánchez" in str(player_info):
                        expected = 5.0
                        if abs(price - expected) > 0.01:
                            print(f"    ⚠️  Expected £{expected:.1f}m for Sanchez")
                        else:
                            print(f"    ✓ Correct price for Sanchez")
                    elif "David Raya" in str(player_info):
                        expected = 5.5
                        if abs(price - expected) > 0.01:
                            print(f"    ⚠️  Expected £{expected:.1f}m for Raya")
                        else:
                            print(f"    ✓ Correct price for Raya")
    else:
        print(f"Error running optimization: {result.stderr}")


if __name__ == "__main__":
    main()