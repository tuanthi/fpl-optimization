#!/usr/bin/env python3
"""
Create properly merged 2024-2025 squads following these rules:
1. Use 2025 squad compositions (all players from 2025 season)
2. For players who moved clubs, use their 2024 stats from their previous club
3. For new players not in promoted teams, copy stats from 2024 teammates with similar prices
4. For promoted teams (Burnley, Leeds, Sunderland), use replacement team stats
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import subprocess
from collections import defaultdict


class ProperSquadMerger:
    def __init__(self):
        self.data_dir = Path("data")
        self.cache_dir = self.data_dir / "cached_merged_2024_2025_v2"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Load all data
        self.load_all_data()
        
        # Team replacements for promoted teams
        self.team_replacements = {
            'Burnley': 'Leicester',
            'Leeds': 'Ipswich', 
            'Sunderland': 'Southampton'
        }
        
    def load_all_data(self):
        """Load all necessary data from both seasons"""
        print("Loading 2024 and 2025 season data...")
        
        # 2024 data
        self.players_2024 = pd.read_csv(self.data_dir / "2024" / "2024_players.csv")
        self.teams_2024 = pd.read_csv(self.data_dir / "2024" / "2024_teams.csv")
        self.gameweek_2024 = pd.read_csv(self.data_dir / "2024" / "2024_player_gameweek.csv")
        
        # 2025 data
        self.players_2025 = pd.read_csv(self.data_dir / "2025" / "2025_players.csv")
        self.teams_2025 = pd.read_csv(self.data_dir / "2025" / "2025_teams.csv")
        
        # Create team mappings
        self.team_id_to_name_2024 = dict(zip(self.teams_2024['id'], self.teams_2024['name']))
        self.team_id_to_name_2025 = dict(zip(self.teams_2025['id'], self.teams_2025['name']))
        self.team_name_to_id_2024 = {v: k for k, v in self.team_id_to_name_2024.items()}
        self.team_name_to_id_2025 = {v: k for k, v in self.team_id_to_name_2025.items()}
        
        # Position mapping
        self.position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        
        print(f"Loaded {len(self.players_2024)} players from 2024")
        print(f"Loaded {len(self.players_2025)} players from 2025")
        
    def calculate_player_stats_2024(self):
        """Calculate total points for each player in 2024"""
        print("\nCalculating 2024 player statistics...")
        
        # Group by player and sum total points
        player_stats = self.gameweek_2024.groupby('element').agg({
            'total_points': 'sum',
            'minutes': 'sum',
            'goals_scored': 'sum',
            'assists': 'sum',
            'clean_sheets': 'sum',
            'GW': 'count'  # Number of gameweeks played
        }).reset_index()
        
        player_stats.columns = ['player_id', 'total_points', 'total_minutes', 
                               'total_goals', 'total_assists', 'total_clean_sheets', 'games_played']
        
        # Merge with player info
        player_stats = player_stats.merge(
            self.players_2024[['id', 'first_name', 'second_name', 'web_name', 'team', 'element_type', 'now_cost']],
            left_on='player_id', right_on='id', how='left'
        )
        
        # Add team name
        player_stats['team_name'] = player_stats['team'].map(self.team_id_to_name_2024)
        
        return player_stats
        
    def find_player_in_2024(self, player_2025):
        """Find a 2025 player in 2024 data (they might have moved clubs)"""
        first_name = player_2025['first_name']
        second_name = player_2025['second_name']
        web_name = player_2025['web_name']
        
        # Try exact match first
        exact_match = self.players_2024[
            (self.players_2024['first_name'] == first_name) & 
            (self.players_2024['second_name'] == second_name)
        ]
        
        if len(exact_match) > 0:
            return exact_match.iloc[0]
            
        # Try web_name match
        web_match = self.players_2024[self.players_2024['web_name'] == web_name]
        if len(web_match) > 0:
            return web_match.iloc[0]
            
        # Try partial name match
        if ' ' in second_name:
            # Handle compound names
            last_part = second_name.split()[-1]
            partial_match = self.players_2024[
                (self.players_2024['first_name'] == first_name) & 
                (self.players_2024['second_name'].str.contains(last_part, na=False))
            ]
            if len(partial_match) > 0:
                return partial_match.iloc[0]
                
        return None
        
    def find_similar_teammate_2024(self, player_2025, player_stats_2024, threshold=0.3):
        """Find a similar 2024 teammate for a new player"""
        team_2025 = self.team_id_to_name_2025.get(player_2025['team'])
        position = player_2025['element_type']
        price_2025 = player_2025['now_cost']  # Already in millions
        
        # Get 2024 team ID (handling promoted teams)
        if team_2025 in self.team_replacements:
            team_2024 = self.team_replacements[team_2025]
        else:
            team_2024 = team_2025
            
        team_id_2024 = self.team_name_to_id_2024.get(team_2024)
        if not team_id_2024:
            return None
            
        # Find teammates from 2024 with same position
        teammates = player_stats_2024[
            (player_stats_2024['team'] == team_id_2024) & 
            (player_stats_2024['element_type'] == position)
        ].copy()
        
        if len(teammates) == 0:
            return None
            
        # Calculate price differences (2024 prices are in tenths)
        teammates['price_2024'] = teammates['now_cost'] / 10
        teammates['price_diff'] = abs(teammates['price_2024'] - price_2025)
        
        # Find within threshold
        candidates = teammates[teammates['price_diff'] <= threshold]
        
        if len(candidates) > 0:
            # Return the one with most points
            return candidates.nlargest(1, 'total_points').iloc[0]
            
        return None
        
    def merge_squads(self):
        """Create merged squad data using 2025 rosters"""
        print("\n" + "="*60)
        print("Creating merged squad data")
        print("="*60)
        
        # Calculate 2024 stats
        player_stats_2024 = self.calculate_player_stats_2024()
        
        # Process each 2025 player
        merged_players = []
        mapping_records = []
        
        for _, player_2025 in self.players_2025.iterrows():
            player_id_2025 = player_2025['id']
            team_2025 = self.team_id_to_name_2025.get(player_2025['team'])
            position = self.position_map.get(player_2025['element_type'], 'Unknown')
            
            # Skip if team not found
            if not team_2025:
                continue
                
            # Find player in 2024 (might be at different club)
            player_2024 = self.find_player_in_2024(player_2025)
            
            if player_2024 is not None:
                # Found player in 2024 - use their stats
                player_id_2024 = player_2024['id']
                team_2024 = self.team_id_to_name_2024.get(player_2024['team'])
                
                # Get their 2024 stats
                stats = player_stats_2024[player_stats_2024['player_id'] == player_id_2024]
                
                if len(stats) > 0:
                    stats_row = stats.iloc[0]
                    total_points = stats_row['total_points']
                    games_played = stats_row['games_played']
                    
                    mapping_records.append({
                        'player_2025': f"{player_2025['first_name']} {player_2025['second_name']}",
                        'team_2025': team_2025,
                        'price_2025': player_2025['now_cost'],
                        'player_2024': f"{player_2024['first_name']} {player_2024['second_name']}",
                        'team_2024': team_2024,
                        'total_points_2024': int(total_points),
                        'games_played_2024': int(games_played),
                        'mapping_type': 'direct_match',
                        'position': position
                    })
                    
                    print(f"✓ {player_2025['first_name']} {player_2025['second_name']} ({team_2025}) "
                          f"-> found in 2024 at {team_2024} ({int(total_points)} pts)")
                else:
                    # Player existed but didn't play
                    total_points = 0
                    games_played = 0
                    
            else:
                # New player or from promoted team - find similar teammate
                threshold = 0.3
                max_attempts = 5
                teammate_found = False
                
                for attempt in range(max_attempts):
                    similar = self.find_similar_teammate_2024(player_2025, player_stats_2024, threshold)
                    if similar is not None:
                        total_points = similar['total_points']
                        games_played = similar['games_played']
                        
                        mapping_records.append({
                            'player_2025': f"{player_2025['first_name']} {player_2025['second_name']}",
                            'team_2025': team_2025,
                            'price_2025': player_2025['now_cost'],
                            'player_2024': f"{similar['first_name']} {similar['second_name']}",
                            'team_2024': similar['team_name'],
                            'total_points_2024': int(total_points),
                            'games_played_2024': int(games_played),
                            'mapping_type': f'similar_teammate_threshold_{threshold:.1f}',
                            'position': position
                        })
                        
                        print(f"  {player_2025['first_name']} {player_2025['second_name']} ({team_2025}) "
                              f"-> similar: {similar['first_name']} {similar['second_name']} "
                              f"(£{threshold:.1f}m threshold, {int(total_points)} pts)")
                        teammate_found = True
                        break
                    
                    threshold += 0.2
                    
                if not teammate_found:
                    # No similar player found
                    total_points = 0
                    games_played = 0
                    print(f"  ⚠️  {player_2025['first_name']} {player_2025['second_name']} ({team_2025}) "
                          f"-> no similar player found")
                          
            # Create merged player record
            merged_player = {
                'id': player_id_2025 + 10000,  # Offset to avoid conflicts
                'player_id_2025': player_id_2025,
                'first_name': player_2025['first_name'],
                'second_name': player_2025['second_name'],
                'web_name': player_2025['web_name'],
                'team': player_2025['team'],
                'team_name': team_2025,
                'element_type': player_2025['element_type'],
                'position': position,
                'now_cost': player_2025['now_cost'],  # 2025 price
                'total_points_2024': total_points,
                'games_played_2024': games_played,
                'season': 2025
            }
            
            merged_players.append(merged_player)
            
        # Save results
        merged_df = pd.DataFrame(merged_players)
        merged_df.to_csv(self.cache_dir / "merged_players_gw39.csv", index=False)
        
        mapping_df = pd.DataFrame(mapping_records)
        mapping_df.to_csv(self.cache_dir / "player_mapping_gw39.csv", index=False)
        
        print(f"\n✓ Created {len(merged_players)} merged player records")
        print(f"✓ Saved to {self.cache_dir}")
        
        # Show summary
        print("\nMapping summary:")
        if len(mapping_df) > 0:
            print(mapping_df['mapping_type'].value_counts())
            
            # Show some examples of transfers
            transfers = mapping_df[mapping_df['team_2024'] != mapping_df['team_2025']]
            if len(transfers) > 0:
                print(f"\nFound {len(transfers)} players who changed clubs:")
                for _, row in transfers.head(10).iterrows():
                    print(f"  {row['player_2025']}: {row['team_2024']} -> {row['team_2025']}")
                    
        return merged_df, mapping_df
        
    def create_gameweek_39_data(self, merged_players):
        """Create gameweek 39 data using merged players"""
        print("\nCreating gameweek 39 prediction data...")
        
        # Create prediction rows for each player
        predictions = []
        
        for _, player in merged_players.iterrows():
            # Skip players with no 2024 data
            if player['games_played_2024'] == 0:
                continue
                
            # Calculate average score
            avg_points = player['total_points_2024'] / max(player['games_played_2024'], 1)
            
            prediction = {
                'first_name': player['first_name'],
                'last_name': player['second_name'],
                'club': player['team_name'],
                'gameweek': 39,
                'price': player['now_cost'],  # 2025 price
                'player_score': avg_points * 0.7,  # Weighted scores
                'team_score': avg_points * 0.3,
                'average_score': avg_points,
                'role': player['position'],
                'player_id': player['id']
            }
            
            predictions.append(prediction)
            
        pred_df = pd.DataFrame(predictions)
        pred_df.to_csv(self.cache_dir / "predictions_gw39.csv", index=False)
        
        print(f"✓ Created {len(predictions)} prediction records for gameweek 39")
        
        return pred_df
        
    def run_optimization(self, pred_file):
        """Run optimization to get top teams"""
        print("\nRunning optimization for gameweek 39...")
        
        output_file = self.cache_dir / "top_50_teams_gw39.csv"
        
        cmd = [
            "python", "src/fast_optimization_runner.py",
            str(pred_file),
            str(output_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Optimization completed successfully")
            return output_file
        else:
            print(f"Error running optimization: {result.stderr}")
            return None
            
    def create_reference_files(self):
        """Create reference files for future use"""
        print("\nCreating reference files...")
        
        # Team reference
        reference = {
            "2024_teams": self.team_id_to_name_2024,
            "2025_teams": self.team_id_to_name_2025,
            "team_replacements": self.team_replacements,
            "created_for": "gameweek_39",
            "description": "Merged 2024-2025 data with proper squad handling"
        }
        
        with open(self.cache_dir / "reference.json", 'w') as f:
            json.dump(reference, f, indent=2)
            
        print("✓ Created reference files")
        
    def verify_results(self, top_teams_file):
        """Verify the results"""
        if not top_teams_file or not Path(top_teams_file).exists():
            return
            
        print("\nVerifying results...")
        df = pd.read_csv(top_teams_file)
        
        print("\nTop team composition:")
        for col in ['GK1', 'GK2', 'DEF1', 'MID1', 'FWD1']:
            if col in df.columns:
                player_info = df.iloc[0][col]
                price = df.iloc[0][f'{col}_price']
                print(f"  {col}: {player_info} - £{price:.1f}m")
                
        print(f"\nTotal squad value: £{df.iloc[0]['15_total_price']:.1f}m")


def main():
    merger = ProperSquadMerger()
    
    # Create merged squads
    merged_players, mapping = merger.merge_squads()
    
    # Create gameweek 39 data
    predictions = merger.create_gameweek_39_data(merged_players)
    
    # Run optimization
    top_teams_file = merger.run_optimization(
        merger.cache_dir / "predictions_gw39.csv"
    )
    
    # Create reference files
    merger.create_reference_files()
    
    # Verify results
    merger.verify_results(top_teams_file)
    
    print("\n" + "="*60)
    print("COMPLETED!")
    print("="*60)
    print(f"All files saved to: {merger.cache_dir}")
    print("\nKey files:")
    print(f"  - Merged players: merged_players_gw39.csv")
    print(f"  - Player mappings: player_mapping_gw39.csv") 
    print(f"  - Predictions: predictions_gw39.csv")
    print(f"  - Top teams: top_50_teams_gw39.csv")
    print(f"  - Reference: reference.json")


if __name__ == "__main__":
    main()