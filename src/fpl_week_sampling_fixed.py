#!/usr/bin/env python3
"""
FPL Week Sampling with Bradley-Terry Predictions - Fixed version with team names
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import json


class FPLWeekSamplerFixed:
    def __init__(self, season_year):
        self.season_year = season_year
        self.data_dir = Path("data") / f"{season_year}"
        
        # Load player data
        self.players_df = pd.read_csv(self.data_dir / f"{season_year}_players.csv")
        self.gameweek_df = pd.read_csv(self.data_dir / f"{season_year}_player_gameweek.csv")
        
        # Load teams data for name mapping
        self.teams_df = pd.read_csv(self.data_dir / f"{season_year}_teams.csv")
        self.team_id_to_name = dict(zip(self.teams_df['id'], self.teams_df['name']))
        
        # Create player name mapping
        self.player_id_to_name = {}
        for _, player in self.players_df.iterrows():
            player_id = player['id']
            first_name = player['first_name']
            # Use second_name if available, otherwise use web_name
            last_name = player['second_name'] if pd.notna(player['second_name']) and player['second_name'] != '' else player['web_name']
            self.player_id_to_name[player_id] = {
                'first_name': first_name,
                'last_name': last_name,
                'position': player['element_type']  # 1=GK, 2=DEF, 3=MID, 4=FWD
            }
        
        # Position mapping
        self.position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        
    def load_bradley_terry_matrices(self, last_observable_week):
        """Load player and team Bradley-Terry matrices"""
        # Determine file suffix
        suffix = f"weeks_1_to_{last_observable_week}"
        
        # Load player Bradley-Terry data
        player_bt_dir = self.data_dir / "bradley_terry"
        player_matrix_file = player_bt_dir / f"bt_matrix_{suffix}.npy"
        player_mappings_file = player_bt_dir / f"player_mappings_{suffix}.json"
        
        if player_matrix_file.exists() and player_mappings_file.exists():
            self.player_bt_matrix = np.load(player_matrix_file)
            with open(player_mappings_file, 'r') as f:
                player_mappings = json.load(f)
            self.player_to_idx = {int(k): v for k, v in player_mappings['player_to_idx'].items()}
            self.idx_to_player = {v: int(k) for k, v in player_mappings['player_to_idx'].items()}
        else:
            print(f"Warning: Player Bradley-Terry files not found for weeks 1-{last_observable_week}")
            self.player_bt_matrix = None
            self.player_to_idx = {}
            self.idx_to_player = {}
        
        # Load team Bradley-Terry data
        team_bt_dir = self.data_dir / "team_bradley_terry"
        team_matrix_file = team_bt_dir / f"team_bt_matrix_{suffix}.npy"
        team_mappings_file = team_bt_dir / f"team_mappings_{suffix}.json"
        
        if team_matrix_file.exists() and team_mappings_file.exists():
            self.team_bt_matrix = np.load(team_matrix_file)
            with open(team_mappings_file, 'r') as f:
                team_mappings = json.load(f)
            self.team_to_idx = {k: v for k, v in team_mappings['team_to_idx'].items()}
            self.idx_to_team = {v: k for k, v in team_mappings['team_to_idx'].items()}
        else:
            print(f"Warning: Team Bradley-Terry files not found for weeks 1-{last_observable_week}")
            self.team_bt_matrix = None
            self.team_to_idx = {}
            self.idx_to_team = {}
    
    def calculate_bradley_terry_scores(self, bt_matrix):
        """Calculate scores from Bradley-Terry matrix"""
        if bt_matrix is None:
            return np.array([])
        
        # Calculate win rates
        wins = bt_matrix.sum(axis=1)
        losses = bt_matrix.sum(axis=0)
        total_games = wins + losses
        
        # Avoid division by zero
        win_rates = np.zeros(len(wins))
        mask = total_games > 0
        win_rates[mask] = wins[mask] / total_games[mask]
        
        # Convert to scores (centered around 0)
        scores = (win_rates - 0.5) * 4  # Scale to roughly -2 to +2
        
        return scores
    
    def get_player_price_at_week(self, player_id, week):
        """Get player price at specific gameweek"""
        player_week_data = self.gameweek_df[
            (self.gameweek_df['element'] == player_id) & 
            (self.gameweek_df['GW'] == week)
        ]
        
        if len(player_week_data) > 0:
            return player_week_data.iloc[0]['price']
        
        # If no data for this week, try previous weeks
        prev_data = self.gameweek_df[
            (self.gameweek_df['element'] == player_id) & 
            (self.gameweek_df['GW'] < week)
        ]
        
        if len(prev_data) > 0:
            return prev_data.iloc[-1]['price']
        
        # Default to player's starting price
        player_data = self.players_df[self.players_df['id'] == player_id]
        if len(player_data) > 0:
            return player_data.iloc[0]['now_cost'] / 10.0
        
        return 0.0
    
    def create_sampling_dataframe(self, first_observable_week, last_observable_week):
        """Create dataframe with player scores for all weeks"""
        results = []
        
        # Load Bradley-Terry matrices
        self.load_bradley_terry_matrices(last_observable_week)
        
        # Get all unique players from gameweek data
        all_players = self.gameweek_df['element'].unique()
        
        # Get maximum gameweek in data
        max_gameweek = self.gameweek_df['GW'].max()
        
        # Process each gameweek
        for gw in range(first_observable_week, max_gameweek + 1):
            print(f"Processing gameweek {gw}...")
            
            # Calculate scores for this week
            if gw <= last_observable_week:
                # Use actual Bradley-Terry matrices
                player_scores = self.calculate_bradley_terry_scores(self.player_bt_matrix)
                team_scores = self.calculate_bradley_terry_scores(self.team_bt_matrix)
            else:
                # For future weeks, use the last observable week's scores
                player_scores = self.calculate_bradley_terry_scores(self.player_bt_matrix)
                team_scores = self.calculate_bradley_terry_scores(self.team_bt_matrix)
            
            # Get data for this gameweek
            gw_data = self.gameweek_df[self.gameweek_df['GW'] == gw]
            
            # Process each player
            for player_id in all_players:
                # Get player info
                player_info = self.player_id_to_name.get(player_id, {})
                if not player_info:
                    continue
                
                # Get player's team for this gameweek
                player_gw = gw_data[gw_data['element'] == player_id]
                if len(player_gw) > 0:
                    team_id = player_gw.iloc[0]['team']
                else:
                    # Try to find team from previous gameweeks
                    prev_data = self.gameweek_df[
                        (self.gameweek_df['element'] == player_id) & 
                        (self.gameweek_df['GW'] < gw)
                    ]
                    if len(prev_data) > 0:
                        team_id = prev_data.iloc[-1]['team']
                    else:
                        continue
                
                # Map team ID to team name
                team_name = self.team_id_to_name.get(team_id, f"Unknown_{team_id}")
                
                # Get scores
                player_score = 0.0
                if player_id in self.player_to_idx:
                    player_idx = self.player_to_idx[player_id]
                    player_score = player_scores[player_idx]
                
                team_score = 0.0
                if str(team_id) in self.team_to_idx:  # Team IDs might be strings in the mapping
                    team_idx = self.team_to_idx[str(team_id)]
                    team_score = team_scores[team_idx]
                
                # Calculate average score (simple average of player and team scores)
                average_score = (player_score + team_score) / 2
                
                # Get price
                price = self.get_player_price_at_week(player_id, gw)
                
                # Get position
                position = self.position_map.get(player_info.get('position', 0), 'UNK')
                
                # Add to results
                results.append({
                    'first_name': player_info.get('first_name', ''),
                    'last_name': player_info.get('last_name', ''),
                    'club': team_name,  # Use team name instead of ID
                    'gameweek': gw,
                    'price': price,
                    'player_score': round(player_score, 4),
                    'team_score': round(team_score, 4),
                    'average_score': round(average_score, 4),
                    'role': position
                })
        
        return pd.DataFrame(results)
    
    def save_results(self, df, first_observable_week, last_observable_week):
        """Save results to CSV"""
        output_file = self.data_dir / f"pred_{self.season_year}_week_sampling_{first_observable_week}_to_{last_observable_week}_fixed.csv"
        df.to_csv(output_file, index=False)
        print(f"\n✓ Saved results to {output_file}")
        return output_file


def main():
    if len(sys.argv) < 4:
        print("Usage: python src/fpl_week_sampling_fixed.py [YEAR] [FIRST_OBSERVABLE_WEEK] [LAST_OBSERVABLE_WEEK]")
        print("Example: python src/fpl_week_sampling_fixed.py 2024 1 9")
        sys.exit(1)
    
    season_year = int(sys.argv[1])
    first_observable_week = int(sys.argv[2])
    last_observable_week = int(sys.argv[3])
    
    # Create sampler
    sampler = FPLWeekSamplerFixed(season_year)
    
    # Create sampling dataframe
    print(f"Creating sampling data for {season_year} season (weeks {first_observable_week}-{last_observable_week})...")
    df = sampler.create_sampling_dataframe(first_observable_week, last_observable_week)
    
    print(f"\nGenerated {len(df)} player-week records")
    print(f"Unique players: {df[['first_name', 'last_name']].drop_duplicates().shape[0]}")
    print(f"Gameweeks: {df['gameweek'].min()} - {df['gameweek'].max()}")
    
    # Show sample
    print("\nSample data:")
    print(df.head(10))
    
    # Save results
    sampler.save_results(df, first_observable_week, last_observable_week)


if __name__ == "__main__":
    main()