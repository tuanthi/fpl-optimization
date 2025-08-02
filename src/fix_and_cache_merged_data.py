#!/usr/bin/env python3
"""
Fix team mappings and cache merged season data
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import shutil

class MergedDataFixer:
    def __init__(self):
        self.data_dir = Path("data")
        self.merged_dir = self.data_dir / "merged_2024_2025"
        self.cache_dir = self.data_dir / "cached_merged_2024_2025"
        
        # Create cache directory
        self.cache_dir.mkdir(exist_ok=True)
        
        # Load team data
        self.teams_2024 = pd.read_csv(self.data_dir / "2024" / "2024_teams.csv")
        self.teams_2025 = pd.read_csv(self.data_dir / "2025" / "2025_teams.csv")
        
        # Create team mappings
        self.team_id_to_name_2024 = dict(zip(self.teams_2024['id'], self.teams_2024['name']))
        self.team_id_to_name_2025 = dict(zip(self.teams_2025['id'], self.teams_2025['name']))
        
    def load_player_data(self):
        """Load player data from both seasons"""
        self.players_2024 = pd.read_csv(self.data_dir / "2024" / "2024_players.csv")
        self.players_2025 = pd.read_csv(self.data_dir / "2025" / "2025_players.csv")
        
        # Create player ID to correct team name mapping
        self.player_team_mapping = {}
        
        # 2024 players
        for _, player in self.players_2024.iterrows():
            player_id = player['id']
            team_id = player['team']
            team_name = self.team_id_to_name_2024.get(team_id, f"Unknown_{team_id}")
            self.player_team_mapping[player_id] = team_name
            
        # 2025 players - offset IDs by 10000 to avoid conflicts
        for _, player in self.players_2025.iterrows():
            player_id = player['id'] + 10000  # Offset to avoid conflicts
            team_id = player['team']
            team_name = self.team_id_to_name_2025.get(team_id, f"Unknown_{team_id}")
            self.player_team_mapping[player_id] = team_name
            
        print(f"Created team mappings for {len(self.player_team_mapping)} players")
        
    def fix_week_sampling_data(self):
        """Fix team names and prices in week sampling prediction data"""
        print("\nFixing week sampling data...")
        
        # Find the latest prediction file
        pred_files = list(self.data_dir.glob("*/pred_*_week_sampling_*.csv"))
        if not pred_files:
            print("No prediction files found")
            return None
            
        # Use the most recent one
        pred_file = sorted(pred_files)[-1]
        print(f"Processing {pred_file}")
        
        # Load prediction data
        pred_df = pd.read_csv(pred_file)
        
        # Create a more comprehensive mapping based on player names
        # First, let's build a name-to-team mapping from the gameweek data
        gameweek_2024 = pd.read_csv(self.data_dir / "2024" / "2024_player_gameweek.csv")
        
        # Get unique player-team combinations from gameweek data
        player_teams = gameweek_2024[['name', 'team']].drop_duplicates()
        name_to_team = dict(zip(player_teams['name'], player_teams['team']))
        
        # Also build from players data
        for _, player in self.players_2024.iterrows():
            full_name = f"{player['first_name']} {player['second_name']}"
            team_name = self.team_id_to_name_2024.get(player['team'], 'Unknown')
            name_to_team[full_name] = team_name
            
        for _, player in self.players_2025.iterrows():
            full_name = f"{player['first_name']} {player['second_name']}"
            team_name = self.team_id_to_name_2025.get(player['team'], 'Unknown')
            name_to_team[full_name] = team_name
        
        # Fix team names in prediction data
        fixed_clubs = []
        for _, row in pred_df.iterrows():
            full_name = f"{row['first_name']} {row['last_name']}"
            
            # Try to find the correct team
            if full_name in name_to_team:
                fixed_clubs.append(name_to_team[full_name])
            else:
                # Try partial match
                found = False
                for player_name, team in name_to_team.items():
                    if row['first_name'] in player_name and row['last_name'] in player_name:
                        fixed_clubs.append(team)
                        found = True
                        break
                if not found:
                    # Keep original if no match found
                    fixed_clubs.append(row['club'])
                    
        pred_df['club'] = fixed_clubs
        
        # Fix prices for gameweek 39+ (2025 season)
        print("\nFixing prices for 2025 season gameweeks...")
        
        # Load player replacement mapping if available
        mapping_file = self.merged_dir / "player_replacement_mapping.csv"
        if mapping_file.exists():
            player_mapping = pd.read_csv(mapping_file)
            name_to_new_price = dict(zip(player_mapping['new_player'], player_mapping['new_price']))
        else:
            name_to_new_price = {}
        
        # Update prices for gameweek 39+
        updated_prices = []
        for _, row in pred_df.iterrows():
            if row['gameweek'] >= 39:
                # This is a 2025 season gameweek, use 2025 starting prices
                full_name = f"{row['first_name']} {row['last_name']}"
                
                # Check mapping first
                if full_name in name_to_new_price:
                    updated_prices.append(name_to_new_price[full_name])
                else:
                    # Find in 2025 players
                    mask = (
                        (self.players_2025['first_name'] == row['first_name']) |
                        (self.players_2025['web_name'] == full_name)
                    )
                    candidates = self.players_2025[mask]
                    
                    if len(candidates) > 0:
                        # Use team to disambiguate if needed
                        if row['club'] in name_to_team.values() and len(candidates) > 1:
                            # Get team ID
                            team_id = None
                            for tid, tname in self.team_id_to_name_2025.items():
                                if tname == row['club']:
                                    team_id = tid
                                    break
                            if team_id:
                                team_candidates = candidates[candidates['team'] == team_id]
                                if len(team_candidates) > 0:
                                    candidates = team_candidates
                        
                        # Use now_cost from 2025 season (in tenths of millions)
                        updated_prices.append(candidates.iloc[0]['now_cost'] / 10)
                    else:
                        # Keep original price if not found
                        updated_prices.append(row['price'])
            else:
                # Keep original price for 2024 gameweeks
                updated_prices.append(row['price'])
                
        pred_df['price'] = updated_prices
        
        # Save fixed file
        output_file = self.cache_dir / "pred_merged_week_sampling_1_to_38_fixed.csv"
        pred_df.to_csv(output_file, index=False)
        print(f"Saved fixed prediction data to {output_file}")
        
        # Show sample of price updates for GW39
        print("\nSample GW39 price updates:")
        gw39_sample = pred_df[pred_df['gameweek'] == 39].head(10)
        for _, row in gw39_sample.iterrows():
            print(f"  {row['first_name']} {row['last_name']} ({row['club']}): £{row['price']:.1f}m")
        
        return output_file
        
    def fix_top_teams_file(self, pred_file):
        """Re-run optimization with fixed team names"""
        print("\nRe-running optimization with fixed data...")
        
        import subprocess
        
        output_file = self.cache_dir / "merged_top_50_teams_gameweek_39_fixed.csv"
        
        cmd = [
            "python", "src/fast_optimization_runner.py",
            str(pred_file),
            str(output_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Created fixed top teams file: {output_file}")
            return output_file
        else:
            print(f"Error running optimization: {result.stderr}")
            return None
            
    def cache_all_merged_data(self):
        """Copy all merged data to cache directory"""
        print("\nCaching merged data...")
        
        # Copy all CSV files from merged directory
        for file in self.merged_dir.glob("*.csv"):
            if file.name != "merged_top_50_teams_gameweek_39.csv":  # Skip the incorrect one
                shutil.copy(file, self.cache_dir / file.name)
                print(f"Cached {file.name}")
                
        # Copy Bradley-Terry directories
        for subdir in ["bradley_terry", "team_bradley_terry"]:
            src = self.merged_dir / subdir
            dst = self.cache_dir / subdir
            if src.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                print(f"Cached {subdir} directory")
                
    def create_team_reference(self):
        """Create a reference file for correct team mappings"""
        print("\nCreating team reference file...")
        
        # Create reference data
        reference = {
            "2024_teams": self.team_id_to_name_2024,
            "2025_teams": self.team_id_to_name_2025,
            "team_replacements": {
                "Burnley": "Leicester",  # Burnley (2025) uses Leicester (2024) stats
                "Leeds": "Ipswich",      # Leeds (2025) uses Ipswich (2024) stats
                "Sunderland": "Southampton"  # Sunderland (2025) uses Southampton (2024) stats
            }
        }
        
        # Save as JSON
        ref_file = self.cache_dir / "team_reference.json"
        with open(ref_file, 'w') as f:
            json.dump(reference, f, indent=2)
        print(f"Saved team reference to {ref_file}")
        
    def verify_fixed_data(self, top_teams_file):
        """Verify the fixed data has correct team names"""
        print("\nVerifying fixed data...")
        
        df = pd.read_csv(top_teams_file)
        
        # Check a few known players
        print("\nSample players from top team:")
        for col in ['GK1', 'DEF1', 'MID1', 'FWD1']:
            if col in df.columns:
                player_info = df.iloc[0][col]
                print(f"  {col}: {player_info}")
                
        # Check for obviously wrong mappings
        wrong_mappings = []
        for col in df.columns:
            if col.endswith(('1', '2', '3', '4', '5')) and not col.endswith(('_selected', '_price', '_score')):
                for player in df[col].unique():
                    if pd.notna(player):
                        # Check for known wrong mappings
                        if "Meslier" in player and "Liverpool" in player:
                            wrong_mappings.append(f"Illan Meslier should be Leeds, not Liverpool")
                        elif "Trafford" in player and "Chelsea" in player:
                            wrong_mappings.append(f"James Trafford should be Man City, not Chelsea")
                            
        if wrong_mappings:
            print("\n⚠️  Found incorrect team mappings:")
            for mapping in set(wrong_mappings):
                print(f"  - {mapping}")
        else:
            print("\n✓ No obvious team mapping errors found")
            
def main():
    fixer = MergedDataFixer()
    
    # Load player data
    fixer.load_player_data()
    
    # Fix week sampling data
    fixed_pred_file = fixer.fix_week_sampling_data()
    
    if fixed_pred_file:
        # Re-run optimization with fixed data
        fixed_top_teams = fixer.fix_top_teams_file(fixed_pred_file)
        
        if fixed_top_teams:
            # Verify the results
            fixer.verify_fixed_data(fixed_top_teams)
    
    # Cache all data
    fixer.cache_all_merged_data()
    
    # Create team reference
    fixer.create_team_reference()
    
    print(f"\n✓ All fixed data cached in: {fixer.cache_dir}")
    print("\nYou can now use the cached data without re-running the merge process.")
    print(f"Fixed top teams file: {fixer.cache_dir}/merged_top_50_teams_gameweek_39_fixed.csv")

if __name__ == "__main__":
    main()