#!/usr/bin/env python3
"""
Regenerate merged prediction with correct 2025 season starting prices for gameweek 39
"""

import pandas as pd
import numpy as np
from pathlib import Path
import subprocess
import shutil


def main():
    print("Regenerating merged season prediction with correct 2025 prices...")
    
    # Paths
    data_dir = Path("data")
    cache_dir = data_dir / "cached_merged_2024_2025"
    merged_dir = data_dir / "merged_2024_2025"
    
    # Clear existing cache
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    print("✓ Cleared existing cache")
    
    # Load 2025 players to get correct starting prices
    players_2025 = pd.read_csv(data_dir / "2025" / "2025_players.csv")
    teams_2025 = pd.read_csv(data_dir / "2025" / "2025_teams.csv")
    
    # Create team ID to name mapping
    team_id_to_name = dict(zip(teams_2025['id'], teams_2025['name']))
    
    # Create price lookup for 2025 players
    price_lookup_2025 = {}
    for _, player in players_2025.iterrows():
        full_name = f"{player['first_name']} {player['second_name']}"
        web_name = player['web_name']
        team_name = team_id_to_name.get(player['team'], 'Unknown')
        
        # Store multiple keys for robust matching
        price_lookup_2025[full_name] = player['now_cost'] / 10
        price_lookup_2025[web_name] = player['now_cost'] / 10
        price_lookup_2025[f"{full_name} ({team_name})"] = player['now_cost'] / 10
        price_lookup_2025[f"{web_name} ({team_name})"] = player['now_cost'] / 10
    
    print(f"✓ Loaded {len(players_2025)} players from 2025 season")
    
    # Verify some key players
    print("\nVerifying 2025 season starting prices:")
    key_players = [
        ("Robert", "Sánchez", "Chelsea"),
        ("David", "Raya Martin", "Arsenal"),
        ("Emiliano", "Martínez Romero", "Aston Villa")
    ]
    
    for first, last, team in key_players:
        mask = (players_2025['first_name'] == first) & (players_2025['second_name'].str.contains(last.split()[0]))
        if mask.sum() > 0:
            player = players_2025[mask].iloc[0]
            price = player['now_cost'] / 10
            print(f"  {first} {last} ({team}): £{price:.1f}m")
    
    # Run the full pipeline
    print("\n" + "="*60)
    print("Running merged season prediction pipeline...")
    print("="*60)
    
    # Run merged seasons script
    cmd = ["python", "src/end_to_end_merged_seasons.py", "39"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running merged seasons script: {result.stderr}")
        return
    
    print("✓ Merged season data generated")
    
    # Now run our custom week sampling that uses 2025 prices for GW39+
    print("\n" + "="*60)
    print("Generating week sampling with correct 2025 prices...")
    print("="*60)
    
    # Copy merged data to working directory
    working_dir = data_dir / "9999"
    
    # Run week sampling
    cmd = ["python", "src/fpl_week_sampling.py", "9999", "1", "38"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running week sampling: {result.stderr}")
        return
    
    # Fix prices in the prediction file for GW39
    pred_file = working_dir / "pred_9999_week_sampling_1_to_38.csv"
    if pred_file.exists():
        print("\nFixing prices in prediction data...")
        pred_df = pd.read_csv(pred_file)
        
        # For gameweek 39 entries, use 2025 prices
        gw39_mask = pred_df['gameweek'] == 39
        
        # Count fixes
        fixes = 0
        for idx in pred_df[gw39_mask].index:
            row = pred_df.loc[idx]
            full_name = f"{row['first_name']} {row['last_name']}"
            
            # Try to find price in lookup
            new_price = None
            for key_variant in [full_name, row['last_name'], f"{full_name} ({row['club']})"]:
                if key_variant in price_lookup_2025:
                    new_price = price_lookup_2025[key_variant]
                    break
            
            if new_price and new_price != row['price']:
                print(f"  Fixed: {full_name} ({row['club']}): {row['price']:.1f} -> {new_price:.1f}")
                pred_df.loc[idx, 'price'] = new_price
                fixes += 1
        
        print(f"\n✓ Fixed {fixes} prices for gameweek 39")
        
        # Save corrected prediction file
        pred_df.to_csv(pred_file, index=False)
    
    # Run the fix and cache script
    print("\n" + "="*60)
    print("Running fix and cache script...")
    print("="*60)
    
    cmd = ["python", "src/fix_and_cache_merged_data.py"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Successfully cached merged data with correct prices")
        
        # Verify final results
        final_file = cache_dir / "merged_top_50_teams_gameweek_39_fixed.csv"
        if final_file.exists():
            print("\nVerifying final prices...")
            df = pd.read_csv(final_file)
            
            # Check specific players
            for col in ['GK1', 'GK2']:
                if col in df.columns:
                    player_info = df.iloc[0][col]
                    price = df.iloc[0][f'{col}_price']
                    print(f"  {col}: {player_info} - £{price:.1f}m")
                    
                    # Specific checks
                    if "Robert Sánchez" in player_info and price != 5.0:
                        print(f"    ⚠️  WARNING: Sanchez price should be 5.0, not {price}")
                    if "David Raya" in player_info and price != 5.5:
                        print(f"    ⚠️  WARNING: Raya price should be 5.5, not {price}")
    else:
        print(f"Error running fix script: {result.stderr}")


if __name__ == "__main__":
    main()