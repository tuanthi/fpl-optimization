#!/usr/bin/env python3
"""
FPL Week Sampling for Merged Seasons with Correct Pricing
Handles gameweeks 1-38 (2024) and 39+ (2025) with appropriate prices

For gameweeks 1-38: Uses 2024 season prices
For gameweeks 39+: Uses 2025 season starting prices (now_cost from 2025_players.csv)
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import json


class FPLWeekSamplerMerged:
    def __init__(self):
        self.data_dir = Path("data")
        
        # Load player data from both seasons
        self.players_2024 = pd.read_csv(self.data_dir / "2024" / "2024_players.csv")
        self.players_2025 = pd.read_csv(self.data_dir / "2025" / "2025_players.csv")
        self.gameweek_2024 = pd.read_csv(self.data_dir / "2024" / "2024_player_gameweek.csv")
        
        # Load team data
        self.teams_2024 = pd.read_csv(self.data_dir / "2024" / "2024_teams.csv")
        self.teams_2025 = pd.read_csv(self.data_dir / "2025" / "2025_teams.csv")
        
        # Create team mappings
        self.team_id_to_name_2024 = dict(zip(self.teams_2024['id'], self.teams_2024['name']))
        self.team_id_to_name_2025 = dict(zip(self.teams_2025['id'], self.teams_2025['name']))
        
        # Load cached merged data if available
        cache_dir = self.data_dir / "cached_merged_2024_2025"
        if cache_dir.exists():
            # Load player mapping
            mapping_file = cache_dir / "player_replacement_mapping.csv"
            if mapping_file.exists():
                self.player_mapping = pd.read_csv(mapping_file)
            else:
                self.player_mapping = None
        else:
            self.player_mapping = None
        
        # Position mapping
        self.position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        
    def get_player_price_for_gameweek(self, player_name, team, gameweek):
        """Get appropriate price based on gameweek"""
        
        if gameweek <= 38:
            # For 2024 season (GW 1-38), use 2024 prices
            # Try to find player in 2024 data
            first_name, last_name = player_name.split(' ', 1) if ' ' in player_name else (player_name, '')
            
            # Match by name and team
            mask = (
                (self.players_2024['first_name'] == first_name) |
                (self.players_2024['web_name'] == player_name)
            )
            
            candidates = self.players_2024[mask]
            if len(candidates) > 0:
                # If we have team info, use it to disambiguate
                if team and len(candidates) > 1:
                    # Get team ID from name
                    team_id = None
                    for tid, tname in self.team_id_to_name_2024.items():
                        if tname == team:
                            team_id = tid
                            break
                    if team_id:
                        team_candidates = candidates[candidates['team'] == team_id]
                        if len(team_candidates) > 0:
                            candidates = team_candidates
                
                # Return price in millions
                return candidates.iloc[0]['now_cost'] / 10
                
        else:
            # For 2025 season (GW 39+), use 2025 starting prices
            first_name, last_name = player_name.split(' ', 1) if ' ' in player_name else (player_name, '')
            
            # Check if this is a mapped player
            if self.player_mapping is not None:
                # Look for this player in the mapping
                mask = (self.player_mapping['new_player'] == player_name)
                if mask.sum() > 0:
                    # This is a mapped player, use their new price
                    return self.player_mapping[mask].iloc[0]['new_price']
            
            # Otherwise, find in 2025 players
            mask = (
                (self.players_2025['first_name'] == first_name) |
                (self.players_2025['web_name'] == player_name)
            )
            
            candidates = self.players_2025[mask]
            if len(candidates) > 0:
                # If we have team info, use it to disambiguate
                if team and len(candidates) > 1:
                    # Get team ID from name
                    team_id = None
                    for tid, tname in self.team_id_to_name_2025.items():
                        if tname == team:
                            team_id = tid
                            break
                    if team_id:
                        team_candidates = candidates[candidates['team'] == team_id]
                        if len(team_candidates) > 0:
                            candidates = team_candidates
                
                # Return price in millions (now_cost is already in tenths)
                return candidates.iloc[0]['now_cost'] / 10
        
        # Default fallback
        return 5.0  # Default price if not found
        
    def update_prediction_prices(self, pred_file, output_file):
        """Update prices in prediction file based on gameweek"""
        print(f"Updating prices in {pred_file}...")
        
        df = pd.read_csv(pred_file)
        
        # Update prices for each row
        updated_prices = []
        for _, row in df.iterrows():
            player_name = f"{row['first_name']} {row['last_name']}"
            gameweek = row['gameweek']
            team = row['club']
            
            # Get correct price for this gameweek
            price = self.get_player_price_for_gameweek(player_name, team, gameweek)
            updated_prices.append(price)
            
        df['price'] = updated_prices
        
        # Save updated file
        df.to_csv(output_file, index=False)
        print(f"Saved updated prediction file to {output_file}")
        
        # Show some examples of price updates
        print("\nSample price updates:")
        sample = df[df['gameweek'] == 39].head(10)
        for _, row in sample.iterrows():
            print(f"  {row['first_name']} {row['last_name']} ({row['club']}): £{row['price']:.1f}m")
            

def main():
    if len(sys.argv) < 3:
        print("Usage: python src/fpl_week_sampling_merged.py <input_pred_file> <output_pred_file>")
        print("Example: python src/fpl_week_sampling_merged.py data/9999/pred_9999_week_sampling_1_to_38.csv data/cached_merged_2024_2025/pred_merged_week_sampling_1_to_38_fixed.csv")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    sampler = FPLWeekSamplerMerged()
    sampler.update_prediction_prices(input_file, output_file)
    

if __name__ == "__main__":
    main()