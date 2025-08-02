#!/usr/bin/env python3
"""
Fix prices in the final merged top teams file to use correct 2025 starting prices
"""

import pandas as pd
from pathlib import Path


def main():
    print("Fixing prices in final top teams file...")
    
    # Paths
    data_dir = Path("data")
    cache_dir = data_dir / "cached_merged_2024_2025"
    
    # Load 2025 players to get correct starting prices
    players_2025 = pd.read_csv(data_dir / "2025" / "2025_players.csv")
    teams_2025 = pd.read_csv(data_dir / "2025" / "2025_teams.csv")
    
    # Create team ID to name mapping
    team_id_to_name = dict(zip(teams_2025['id'], teams_2025['name']))
    
    # Build comprehensive price lookup
    # Key: (player_name, team_name) -> price
    price_lookup = {}
    
    for _, player in players_2025.iterrows():
        first_name = player['first_name']
        second_name = player['second_name']
        web_name = player['web_name']
        team_name = team_id_to_name.get(player['team'], 'Unknown')
        price = player['now_cost']  # Already in millions for 2025 data
        
        # Create lookup entries
        full_name = f"{first_name} {second_name}"
        price_lookup[(full_name, team_name)] = price
        price_lookup[(web_name, team_name)] = price
        
        # Handle special cases
        if "Sánchez" in second_name and first_name == "Robert":
            price_lookup[("Robert Sánchez", "Chelsea")] = price
        if "Raya" in second_name and first_name == "David":
            price_lookup[("David Raya Martin", "Arsenal")] = price
            price_lookup[("David Raya", "Arsenal")] = price
        if "Martínez" in second_name and first_name == "Emiliano":
            price_lookup[("Emiliano Martínez Romero", "Aston Villa")] = price
            price_lookup[("Emiliano Martínez", "Aston Villa")] = price
            
    print(f"Built price lookup for {len(players_2025)} players")
    
    # Verify key prices
    print("\nKey player prices from 2025 data:")
    key_checks = [
        ("Robert Sánchez", "Chelsea"),
        ("David Raya Martin", "Arsenal"),
        ("Emiliano Martínez Romero", "Aston Villa"),
        ("Cole Palmer", "Chelsea"),
        ("Virgil van Dijk", "Liverpool"),
        ("Erling Haaland", "Man City")
    ]
    
    for player_name, team in key_checks:
        if (player_name, team) in price_lookup:
            print(f"  {player_name} ({team}): £{price_lookup[(player_name, team)]:.1f}m")
    
    # Load the current top teams file
    input_file = cache_dir / "merged_top_50_teams_gameweek_39_fixed.csv"
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return
        
    df = pd.read_csv(input_file)
    print(f"\nLoaded top teams data with {len(df)} teams")
    
    # Fix prices for each player column
    print("\nFixing prices...")
    updates = 0
    
    for prefix in ['GK', 'DEF', 'MID', 'FWD']:
        for i in range(1, 6):  # Up to 5 players per position
            player_col = f'{prefix}{i}'
            price_col = f'{prefix}{i}_price'
            
            if player_col not in df.columns or price_col not in df.columns:
                continue
                
            for idx in df.index:
                player_info = df.loc[idx, player_col]
                if pd.isna(player_info):
                    continue
                    
                # Extract player name and team
                if '(' in player_info and ')' in player_info:
                    player_name = player_info.split(' (')[0].strip()
                    team_name = player_info.split('(')[1].rstrip(')')
                    
                    # Look up correct price
                    if (player_name, team_name) in price_lookup:
                        correct_price = price_lookup[(player_name, team_name)]
                        current_price = df.loc[idx, price_col]
                        
                        if abs(correct_price - current_price) > 0.01:
                            df.loc[idx, price_col] = correct_price
                            if updates < 20:  # Show first 20 updates
                                print(f"  {player_info}: {current_price} -> {correct_price}")
                            updates += 1
    
    print(f"\nTotal price updates: {updates}")
    
    # Recalculate total prices
    print("\nRecalculating team total prices...")
    for idx in df.index:
        total_price = 0
        for prefix in ['GK', 'DEF', 'MID', 'FWD']:
            for i in range(1, 6):
                price_col = f'{prefix}{i}_price'
                if price_col in df.columns:
                    price = df.loc[idx, price_col]
                    if pd.notna(price):
                        total_price += price
        df.loc[idx, '15_total_price'] = round(total_price, 1)
    
    # Save corrected file
    output_file = cache_dir / "merged_top_50_teams_gameweek_39_fixed_prices.csv"
    df.to_csv(output_file, index=False)
    print(f"\n✓ Saved corrected file to {output_file}")
    
    # Verify the top team
    print("\nTop team with corrected prices:")
    for col in ['GK1', 'GK2', 'DEF1', 'MID1', 'FWD1']:
        if col in df.columns:
            player_info = df.iloc[0][col]
            price = df.iloc[0][f'{col}_price']
            print(f"  {col}: {player_info} - £{price:.1f}m")
    
    print(f"\nTotal squad value: £{df.iloc[0]['15_total_price']:.1f}m")


if __name__ == "__main__":
    main()