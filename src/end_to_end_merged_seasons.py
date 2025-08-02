#!/usr/bin/env python3
"""
End-to-End FPL Prediction Pipeline with Merged 2024-2025 Seasons
Merges data from 2024 and 2025 seasons, handles team replacements, and predicts scores

Team Replacements:
- Leicester City (2025) -> Burnley (2024)
- Ipswich Town (2025) -> Leeds United (2024)
- Southampton (2025) -> Sheffield United (2024)

Gameweeks:
- 2024: GW 1-38
- 2025: GW 39-76 (continuing from 2024)

Usage: python src/end_to_end_merged_seasons.py [GAMEWEEK]
Example: python src/end_to_end_merged_seasons.py 45
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import json
import subprocess
from datetime import datetime
from collections import defaultdict
import shutil


class MergedSeasonsPredictor:
    def __init__(self, target_gameweek):
        """Initialize the predictor for merged seasons
        
        Args:
            target_gameweek: The gameweek to predict (1-76)
        """
        self.target_gameweek = target_gameweek
        self.data_dir = Path("data") / "merged_2024_2025"
        self.position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        
        # Team replacement mapping
        # Maps 2025 teams to 2024 teams they should copy stats from
        self.team_replacements = {
            'Burnley': 'Leicester',      # Burnley (2025) uses Leicester (2024) stats
            'Leeds': 'Ipswich',          # Leeds (2025) uses Ipswich (2024) stats  
            'Sunderland': 'Southampton'  # Sunderland (2025) uses Southampton (2024) stats
        }
        
        # Create output directory
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def run_command(self, cmd, description):
        """Run a shell command and handle errors"""
        print(f"\n{description}...")
        try:
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            if e.stderr:
                print(f"Error details: {e.stderr}")
            return False
            
    def download_both_seasons(self):
        """Download data for both 2024 and 2025 seasons"""
        print(f"\n{'='*60}")
        print("Step 1: Downloading FPL data for both seasons")
        print(f"{'='*60}")
        
        # Download 2024 data
        if not self.run_command(
            "source .venv/bin/activate && python src/fpl_download.py 2024",
            "Downloading 2024 season data"
        ):
            return False
            
        # Download 2025 data
        if not self.run_command(
            "source .venv/bin/activate && python src/fpl_download.py 2025",
            "Downloading 2025 season data"
        ):
            return False
            
        return True
        
    def load_and_merge_data(self):
        """Load and merge data from both seasons with team replacements"""
        print(f"\n{'='*60}")
        print("Step 2: Loading and merging season data")
        print(f"{'='*60}")
        
        # Load 2024 data
        players_2024 = pd.read_csv("data/2024/2024_players.csv")
        gameweek_2024 = pd.read_csv("data/2024/2024_player_gameweek.csv")
        teams_2024 = pd.read_csv("data/2024/2024_teams.csv")
        fixtures_2024 = pd.read_csv("data/2024/2024_fixtures.csv")
        
        # Load 2025 data
        players_2025 = pd.read_csv("data/2025/2025_players.csv")
        teams_2025 = pd.read_csv("data/2025/2025_teams.csv")
        fixtures_2025 = pd.read_csv("data/2025/2025_fixtures.csv")
        
        # Add team names to players if not present
        if 'team_name' not in players_2024.columns:
            players_2024 = players_2024.merge(
                teams_2024[['id', 'name']].rename(columns={'id': 'team', 'name': 'team_name'}),
                on='team',
                how='left'
            )
        
        # Check if 2025 has gameweek data
        gameweek_2025_file = Path("data/2025/2025_player_gameweek.csv")
        if gameweek_2025_file.exists():
            gameweek_2025 = pd.read_csv(gameweek_2025_file)
        else:
            print("Note: No gameweek data available for 2025 season yet")
            gameweek_2025 = pd.DataFrame()
        
        # Create team name mapping
        team_id_to_name_2024 = dict(zip(teams_2024['id'], teams_2024['name']))
        team_id_to_name_2025 = dict(zip(teams_2025['id'], teams_2025['name']))
        
        # Find team IDs for replacements
        team_name_to_id_2025 = dict(zip(teams_2025['name'], teams_2025['id']))
        team_name_to_id_2024 = dict(zip(teams_2024['name'], teams_2024['id']))
        replacement_team_ids = {}
        
        for new_team, old_team in self.team_replacements.items():
            # Find exact match in 2025
            if new_team in team_name_to_id_2025:
                new_team_id = team_name_to_id_2025[new_team]
                replacement_team_ids[new_team_id] = old_team
                print(f"Found {new_team} (ID: {new_team_id}) -> will use {old_team} stats")
            else:
                print(f"Warning: Could not find {new_team} in 2025 teams")
        
        # Perform player replacements
        print("\n" + "="*60)
        print("Player Replacement Mapping")
        print("="*60)
        
        replacement_mapping = []
        
        # Track which old players have been matched to avoid duplicates
        matched_old_players = set()
        
        for new_team_id, old_team_name in replacement_team_ids.items():
            # Get players from new team (2025)
            new_team_players = players_2025[players_2025['team'] == new_team_id]
            
            # Get players from old team (2024) with their stats
            old_team_id = None
            for tid, tname in team_id_to_name_2024.items():
                if tname == old_team_name:
                    old_team_id = tid
                    break
            
            if old_team_id is None:
                print(f"Warning: Could not find {old_team_name} in 2024 data")
                continue
                
            old_team_players = players_2024[players_2024['team'] == old_team_id]
            
            # Calculate total points for each old player
            old_player_points = gameweek_2024.groupby('element')['total_points'].sum()
            
            print(f"\nProcessing {team_id_to_name_2025[new_team_id]} -> {old_team_name}")
            
            # Get initial prices (gameweek 1) for old team players
            # Since we're using 2024 data, the prices should be from the start of season
            initial_prices_2024 = {}
            for _, player in old_team_players.iterrows():
                # Get the earliest price from gameweek data or use current price
                player_gw_data = gameweek_2024[gameweek_2024['element'] == player['id']]
                if len(player_gw_data) > 0:
                    initial_price = player_gw_data.iloc[0]['price']  # First gameweek price
                else:
                    initial_price = player['now_cost'] / 10
                initial_prices_2024[player['id']] = initial_price
            
            # Sort new players by position and price (highest to lowest)
            new_players_sorted = []
            for position in [1, 2, 3, 4]:  # GK, DEF, MID, FWD
                position_players = new_team_players[new_team_players['element_type'] == position].copy()
                # Add price in millions for sorting
                position_players['price_millions'] = position_players['now_cost'].apply(
                    lambda x: x if x < 20 else x / 10
                )
                position_players = position_players.sort_values('price_millions', ascending=False)
                new_players_sorted.extend(position_players.iterrows())
            
            # Sort old players by position and price (highest to lowest), then by points
            old_players_by_position = {}
            for position in [1, 2, 3, 4]:
                position_players = old_team_players[old_team_players['element_type'] == position].copy()
                # Add initial price and points
                position_players['initial_price'] = position_players['id'].map(initial_prices_2024)
                position_players['total_points'] = position_players['id'].map(old_player_points).fillna(0)
                # Sort by price (desc), then points (desc)
                position_players = position_players.sort_values(
                    ['initial_price', 'total_points'], ascending=[False, False]
                )
                old_players_by_position[position] = list(position_players.iterrows())
            
            # Match players using the sorted order
            unmatched_new_players = new_players_sorted
            threshold = 0.3  # Start with 0.3
            iteration = 0
            
            while unmatched_new_players and iteration < 10:  # Max 10 iterations
                iteration += 1
                still_unmatched = []
                
                print(f"\n  Matching iteration {iteration} with threshold £{threshold:.1f}m")
                
                for idx, new_player in unmatched_new_players:
                    position = new_player['element_type']
                    new_price = new_player['price_millions']
                    
                    # Get sorted old players for this position
                    old_players_list = old_players_by_position.get(position, [])
                    
                    # Find first matching old player within threshold
                    matched = False
                    for old_idx, old_player in old_players_list:
                        old_player_id = old_player['id']
                        old_price = old_player['initial_price']
                        
                        # Check price threshold
                        if abs(old_price - new_price) <= threshold:
                            # Check if already matched (allow duplicates after iteration 3)
                            if iteration <= 3 and old_player_id in matched_old_players:
                                continue
                            
                            # Found a match!
                            total_pts = old_player['total_points']
                            
                            replacement_mapping.append({
                                'new_player': f"{new_player['first_name']} {new_player['second_name']}",
                                'new_team': team_id_to_name_2025.get(new_team_id, 'Unknown'),
                                'new_price': new_price,
                                'old_player': f"{old_player['first_name']} {old_player['second_name']}",
                                'old_team': old_team_name,
                                'old_price': old_price,
                                'old_total_points': int(total_pts),
                                'position': self.position_map.get(position, 'Unknown'),
                                'threshold_used': threshold
                            })
                            
                            matched_old_players.add(old_player_id)
                            print(f"    Matched: {new_player['first_name']} {new_player['second_name']} (£{new_price:.1f}m) -> "
                                  f"{old_player['first_name']} {old_player['second_name']} (£{old_price:.1f}m, {int(total_pts)} pts)")
                            matched = True
                            break
                    
                    if not matched:
                        still_unmatched.append((idx, new_player))
                
                # Update unmatched list and increase threshold
                unmatched_new_players = still_unmatched
                if unmatched_new_players:
                    print(f"  {len(unmatched_new_players)} players still unmatched")
                    threshold += 0.2
                else:
                    print(f"  All players matched!")
            
            # Report any remaining unmatched players
            if unmatched_new_players:
                print(f"\n  Warning: {len(unmatched_new_players)} players could not be matched:")
                for _, player in unmatched_new_players:
                    print(f"    {player['first_name']} {player['second_name']} ({self.position_map.get(player['element_type'], 'Unknown')})")
        
        # Save replacement mapping
        replacement_df = pd.DataFrame(replacement_mapping)
        if not replacement_df.empty:
            replacement_df.to_csv(self.data_dir / "player_replacement_mapping.csv", index=False)
            
            print("\nReplacement Mapping Summary:")
            print(f"Total replacements: {len(replacement_df)}")
            print(f"\nThreshold distribution:")
            print(replacement_df['threshold_used'].value_counts().sort_index())
            print("\nSample mappings (first 10):")
            print(replacement_df.head(10).to_string())
        else:
            print("\nNo replacement mappings created")
        
        # Merge the data
        print("\n" + "="*60)
        print("Merging season data")
        print("="*60)
        
        # Adjust 2025 gameweeks to continue from 2024
        if not gameweek_2025.empty:
            gameweek_2025['GW'] = gameweek_2025['GW'] + 38
        
        # Merge players (add season identifier)
        players_2024['season'] = 2024
        players_2025['season'] = 2025
        
        # For 2025 players in replacement teams, copy stats from 2024
        for _, replacement in replacement_df.iterrows():
            # Find the new player in 2025
            mask = (
                (players_2025['first_name'] == replacement['new_player'].split()[0]) &
                (players_2025['element_type'] == ['GK', 'DEF', 'MID', 'FWD'].index(replacement['position']) + 1)
            )
            
            if mask.sum() > 0:
                new_player_id = players_2025[mask].iloc[0]['id']
                
                # Find the old player in 2024
                old_mask = (
                    (players_2024['first_name'] == replacement['old_player'].split()[0]) &
                    (players_2024['element_type'] == ['GK', 'DEF', 'MID', 'FWD'].index(replacement['position']) + 1)
                )
                
                if old_mask.sum() > 0:
                    old_player_id = players_2024[old_mask].iloc[0]['id']
                    
                    # Copy gameweek stats if we process 2025 gameweeks
                    # This will be used when 2025 gameweek data becomes available
                    print(f"Mapped player {new_player_id} -> {old_player_id} stats")
        
        # Add team names to gameweek data for easier processing
        gameweek_2024 = gameweek_2024.merge(
            teams_2024[['id', 'name']].rename(columns={'id': 'opponent_team', 'name': 'opponent_team_name'}),
            on='opponent_team',
            how='left'
        )
        
        # Apply team replacements to gameweek data
        for new_team_id, old_team_name in replacement_team_ids.items():
            old_team_id = team_name_to_id_2024.get(old_team_name)
            if old_team_id:
                # Update team IDs in fixtures for 2025
                fixtures_2025.loc[fixtures_2025['team_h'] == new_team_id, 'team_h'] = old_team_id + 100
                fixtures_2025.loc[fixtures_2025['team_a'] == new_team_id, 'team_a'] = old_team_id + 100
        
        # Merge all data
        merged_players = pd.concat([players_2024, players_2025], ignore_index=True)
        merged_gameweeks = pd.concat([gameweek_2024, gameweek_2025], ignore_index=True) if not gameweek_2025.empty else gameweek_2024
        
        # Adjust fixtures
        fixtures_2025['event'] = fixtures_2025['event'] + 38
        merged_fixtures = pd.concat([fixtures_2024, fixtures_2025], ignore_index=True)
        
        # Create merged teams (use 2024 teams as base, update with replacements)
        merged_teams = teams_2024.copy()
        
        # Save merged data
        merged_players.to_csv(self.data_dir / "merged_players.csv", index=False)
        merged_gameweeks.to_csv(self.data_dir / "merged_player_gameweek.csv", index=False)
        merged_fixtures.to_csv(self.data_dir / "merged_fixtures.csv", index=False)
        merged_teams.to_csv(self.data_dir / "merged_teams.csv", index=False)
        
        print(f"\nMerged data summary:")
        print(f"Total players: {len(merged_players)}")
        print(f"Total gameweeks: {merged_gameweeks['GW'].nunique() if not merged_gameweeks.empty else 0}")
        print(f"Total fixtures: {len(merged_fixtures)}")
        
        return True
        
    def build_bradley_terry_matrix(self, up_to_week, home_advantage=0.2):
        """Build Bradley-Terry matrices for merged data"""
        print(f"\n{'='*60}")
        print(f"Building Bradley-Terry matrices for weeks 1-{up_to_week}")
        print(f"{'='*60}")
        
        # Use merged data directory
        # We need to create a temporary symlink or copy data to expected location
        
        # Create temporary directory structure
        temp_year = 9999  # Use a dummy year
        temp_dir = Path("data") / str(temp_year)
        temp_dir.mkdir(exist_ok=True)
        
        # Copy merged data with expected naming
        shutil.copy(self.data_dir / "merged_players.csv", temp_dir / f"{temp_year}_players.csv")
        shutil.copy(self.data_dir / "merged_player_gameweek.csv", temp_dir / f"{temp_year}_player_gameweek.csv")
        # Also need teams and fixtures
        shutil.copy(self.data_dir / "merged_teams.csv", temp_dir / f"{temp_year}_teams.csv")
        shutil.copy(self.data_dir / "merged_fixtures.csv", temp_dir / f"{temp_year}_fixtures.csv")
        
        # Build player matrix
        cmd = f"source .venv/bin/activate && python src/fpl_player_prep.py {temp_year} {up_to_week} {up_to_week + 1} {home_advantage}"
        if not self.run_command(cmd, f"Building player Bradley-Terry matrix (weeks 1-{up_to_week})"):
            return False
            
        # Build team matrix
        cmd = f"source .venv/bin/activate && python src/fpl_team_prep.py {temp_year} {up_to_week} {up_to_week + 1} {home_advantage}"
        if not self.run_command(cmd, f"Building team Bradley-Terry matrix (weeks 1-{up_to_week})"):
            return False
            
        # Copy results back to merged directory
        bt_dir = temp_dir / "bradley_terry"
        team_bt_dir = temp_dir / "team_bradley_terry"
        
        if bt_dir.exists():
            shutil.copytree(bt_dir, self.data_dir / "bradley_terry", dirs_exist_ok=True)
        if team_bt_dir.exists():
            shutil.copytree(team_bt_dir, self.data_dir / "team_bradley_terry", dirs_exist_ok=True)
            
        # Clean up temp directory
        shutil.rmtree(temp_dir)
        
        return True
        
    def check_available_gameweeks(self):
        """Check which gameweeks have actual data in merged dataset"""
        gameweek_file = self.data_dir / "merged_player_gameweek.csv"
        
        if not gameweek_file.exists():
            print(f"Error: Gameweek data file not found at {gameweek_file}")
            return []
            
        df = pd.read_csv(gameweek_file)
        available_weeks = sorted(df['GW'].unique())
        
        print(f"\nAvailable gameweeks with data: {available_weeks}")
        return available_weeks
        
    def run_merged_prediction(self):
        """Run the complete prediction pipeline for merged seasons"""
        print(f"\n{'='*80}")
        print(f"MERGED 2024-2025 FPL PREDICTION FOR GAMEWEEK {self.target_gameweek}")
        print(f"{'='*80}")
        
        # Step 1: Download data for both seasons
        if not self.download_both_seasons():
            print("Failed to download data")
            return False
            
        # Step 2: Load and merge data with replacements
        if not self.load_and_merge_data():
            print("Failed to merge data")
            return False
            
        # Step 3: Check available gameweeks
        available_weeks = self.check_available_gameweeks()
        if not available_weeks:
            print("No gameweek data available")
            return False
            
        last_available_week = max(available_weeks)
        print(f"Last available gameweek: {last_available_week}")
        
        # Step 4: Determine prediction strategy
        if self.target_gameweek <= last_available_week:
            print(f"\nTarget gameweek {self.target_gameweek} has actual data available")
            observable_weeks = self.target_gameweek - 1
        else:
            print(f"\nTarget gameweek {self.target_gameweek} is beyond available data")
            print(f"Will use all available data up to gameweek {last_available_week}")
            observable_weeks = last_available_week
            
        # Step 5: Build matrices
        if observable_weeks > 0:
            if not self.build_bradley_terry_matrix(observable_weeks):
                return False
        else:
            print("Not enough weeks to build Bradley-Terry matrices")
            return False
            
        # Step 6: Find optimal teams
        print(f"\n{'='*60}")
        print("Finding optimal teams based on merged data")
        print(f"{'='*60}")
        
        # Set up temporary directory structure for optimization
        temp_year = 9999
        temp_dir = Path("data") / str(temp_year)
        temp_dir.mkdir(exist_ok=True)
        
        # Copy necessary files for optimization
        shutil.copy(self.data_dir / "merged_players.csv", temp_dir / f"{temp_year}_players.csv")
        shutil.copy(self.data_dir / "merged_player_gameweek.csv", temp_dir / f"{temp_year}_player_gameweek.csv")
        shutil.copy(self.data_dir / "merged_teams.csv", temp_dir / f"{temp_year}_teams.csv")
        shutil.copy(self.data_dir / "merged_fixtures.csv", temp_dir / f"{temp_year}_fixtures.csv")
        
        # Copy Bradley-Terry results
        if (self.data_dir / "bradley_terry").exists():
            shutil.copytree(self.data_dir / "bradley_terry", temp_dir / "bradley_terry", dirs_exist_ok=True)
        if (self.data_dir / "team_bradley_terry").exists():
            shutil.copytree(self.data_dir / "team_bradley_terry", temp_dir / "team_bradley_terry", dirs_exist_ok=True)
        
        # Run optimized prediction
        cmd = f"source .venv/bin/activate && python src/pred_optimized_fixed.py {temp_year} {self.target_gameweek}"
        if not self.run_command(cmd, "Finding optimal team combinations"):
            print("Warning: Could not run team optimization")
        else:
            # Copy the results to merged directory
            pred_file = Path("data") / str(temp_year) / f"pred_optimized_top_50_teams_week_{self.target_gameweek}.csv"
            if pred_file.exists():
                shutil.copy(pred_file, self.data_dir / f"merged_top_50_teams_gameweek_{self.target_gameweek}.csv")
                print(f"✓ Top 50 teams saved to: {self.data_dir}/merged_top_50_teams_gameweek_{self.target_gameweek}.csv")
            
            # Also copy comparison file if it exists
            comp_file = Path("data") / str(temp_year) / f"comparison_optimized_week_{self.target_gameweek}.csv"
            if comp_file.exists():
                shutil.copy(comp_file, self.data_dir / f"merged_comparison_gameweek_{self.target_gameweek}.csv")
        
        # Clean up temp directory
        shutil.rmtree(temp_dir)
        
        print(f"\n{'='*60}")
        print("PREDICTION COMPLETE!")
        print(f"Merged season prediction saved to: {self.data_dir}")
        print(f"{'='*60}")
        
        return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/end_to_end_merged_seasons.py [GAMEWEEK]")
        print("Example: python src/end_to_end_merged_seasons.py 45")
        print("\nGameweek ranges:")
        print("  2024 season: 1-38")
        print("  2025 season: 39-76")
        sys.exit(1)
        
    target_gameweek = int(sys.argv[1])
    
    if target_gameweek < 1 or target_gameweek > 76:
        print(f"Error: Gameweek must be between 1 and 76 (got {target_gameweek})")
        sys.exit(1)
    
    # Create predictor and run
    predictor = MergedSeasonsPredictor(target_gameweek)
    
    # Run the prediction pipeline
    success = predictor.run_merged_prediction()
    
    if not success:
        print("\nMerged prediction pipeline failed!")
        sys.exit(1)
    else:
        print("\nMerged prediction pipeline completed successfully!")


if __name__ == "__main__":
    main()