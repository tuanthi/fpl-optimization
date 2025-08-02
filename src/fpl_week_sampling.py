#!/usr/bin/env python3
"""
FPL Week Sampling with Bradley-Terry Predictions
Generates player scores using Bradley-Terry matrices for prediction

Usage: python src/fpl_week_sampling.py [YEAR] [FIRST_OBSERVABLE_WEEK] [LAST_OBSERVABLE_WEEK]
Example: python src/fpl_week_sampling.py 2024 1 9
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import json


class FPLWeekSampler:
    def __init__(self, season_year):
        self.season_year = season_year
        self.data_dir = Path("data") / f"{season_year}"
        
        # Load player data
        self.players_df = pd.read_csv(self.data_dir / f"{season_year}_players.csv")
        self.gameweek_df = pd.read_csv(self.data_dir / f"{season_year}_player_gameweek.csv")
        
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
        
        self.player_bt_matrix = np.load(player_matrix_file)
        with open(player_mappings_file, 'r') as f:
            player_mappings = json.load(f)
        
        self.player_to_idx = {int(k): v for k, v in player_mappings['player_to_idx'].items()}
        self.idx_to_player = {v: int(k) for k, v in player_mappings['player_to_idx'].items()}
        
        # Load team Bradley-Terry data
        team_bt_dir = self.data_dir / "team_bradley_terry"
        team_matrix_file = team_bt_dir / f"team_bt_matrix_{suffix}.npy"
        team_mappings_file = team_bt_dir / f"team_mappings_{suffix}.json"
        
        self.team_bt_matrix = np.load(team_matrix_file)
        with open(team_mappings_file, 'r') as f:
            team_mappings = json.load(f)
        
        self.team_to_idx = team_mappings['team_to_idx']
        self.idx_to_team = team_mappings['idx_to_team']
        
    def calculate_bradley_terry_scores(self, matrix):
        """Calculate Bradley-Terry scores from win matrix"""
        n = matrix.shape[0]
        
        # Add small epsilon to avoid division by zero
        epsilon = 1e-6
        total_comparisons = matrix + matrix.T + epsilon
        
        # Calculate win rates
        win_rates = np.zeros(n)
        for i in range(n):
            wins = matrix[i, :].sum()
            total = total_comparisons[i, :].sum()
            win_rates[i] = wins / total if total > 0 else 0.5
        
        # Convert to Bradley-Terry scores (log-odds)
        scores = np.log(win_rates + epsilon) - np.log(1 - win_rates + epsilon)
        
        # Normalize scores to have mean 0 and std 1
        scores = (scores - scores.mean()) / (scores.std() + epsilon)
        
        return scores
    
    def get_player_price_at_week(self, player_id, gameweek):
        """Get player price at specific gameweek"""
        player_gw_data = self.gameweek_df[
            (self.gameweek_df['element'] == player_id) & 
            (self.gameweek_df['GW'] <= gameweek)
        ]
        
        if len(player_gw_data) > 0:
            # Get the most recent price
            latest_data = player_gw_data.iloc[-1]
            return latest_data['price']
        else:
            # If no data, try to get from players df
            player_data = self.players_df[self.players_df['id'] == player_id]
            if len(player_data) > 0:
                return player_data.iloc[0]['now_cost'] / 10  # Convert to millions
            return 0.0
    
    def simulate_future_week(self, player_bt_matrix, team_bt_matrix, previous_results):
        """Simulate Bradley-Terry comparisons for a future week"""
        # Calculate current scores
        player_scores = self.calculate_bradley_terry_scores(player_bt_matrix)
        team_scores = self.calculate_bradley_terry_scores(team_bt_matrix)
        
        # For each player, simulate comparisons based on scores
        n_players = player_bt_matrix.shape[0]
        
        for i in range(n_players):
            for j in range(i + 1, n_players):
                # Calculate probability of i beating j
                score_diff = player_scores[i] - player_scores[j]
                prob_i_wins = 1 / (1 + np.exp(-score_diff))
                
                # Simulate outcome
                if np.random.random() < prob_i_wins:
                    player_bt_matrix[i, j] += 1
                else:
                    player_bt_matrix[j, i] += 1
        
        return player_bt_matrix, team_bt_matrix
    
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
                # Simulate future week
                self.player_bt_matrix, self.team_bt_matrix = self.simulate_future_week(
                    self.player_bt_matrix.copy(), 
                    self.team_bt_matrix.copy(),
                    results
                )
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
                    team = player_gw.iloc[0]['team']
                else:
                    # Try to find team from previous gameweeks
                    prev_data = self.gameweek_df[
                        (self.gameweek_df['element'] == player_id) & 
                        (self.gameweek_df['GW'] < gw)
                    ]
                    if len(prev_data) > 0:
                        team = prev_data.iloc[-1]['team']
                    else:
                        continue
                
                # Get scores
                player_score = 0.0
                if player_id in self.player_to_idx:
                    player_idx = self.player_to_idx[player_id]
                    player_score = player_scores[player_idx]
                
                team_score = 0.0
                if team in self.team_to_idx:
                    team_idx = self.team_to_idx[team]
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
                    'club': team,
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
        output_file = self.data_dir / f"pred_{self.season_year}_week_sampling_{first_observable_week}_to_{last_observable_week}.csv"
        df.to_csv(output_file, index=False)
        print(f"\n✓ Saved results to {output_file}")
        return output_file


def main():
    if len(sys.argv) < 4:
        print("Usage: python src/fpl_week_sampling.py [YEAR] [FIRST_OBSERVABLE_WEEK] [LAST_OBSERVABLE_WEEK]")
        print("Example: python src/fpl_week_sampling.py 2024 1 9")
        sys.exit(1)
    
    season_year = int(sys.argv[1])
    first_observable_week = int(sys.argv[2])
    last_observable_week = int(sys.argv[3])
    
    # Check if data exists
    data_dir = Path("data") / f"{season_year}"
    if not data_dir.exists():
        print(f"Error: No data found for {season_year}. Run fpl_download.py first.")
        sys.exit(1)
    
    # Check if Bradley-Terry matrices exist
    bt_dir = data_dir / "bradley_terry"
    team_bt_dir = data_dir / "team_bradley_terry"
    
    if not bt_dir.exists() or not team_bt_dir.exists():
        print(f"Error: Bradley-Terry matrices not found. Run fpl_player_prep.py and fpl_team_prep.py first.")
        sys.exit(1)
    
    print(f"FPL Week Sampling for {season_year}/{season_year+1} season")
    print(f"Observable weeks: {first_observable_week} to {last_observable_week}")
    
    # Initialize sampler
    sampler = FPLWeekSampler(season_year)
    
    # Create sampling dataframe
    df = sampler.create_sampling_dataframe(first_observable_week, last_observable_week)
    
    # Save results
    output_file = sampler.save_results(df, first_observable_week, last_observable_week)
    
    # Print summary
    print("\nSummary:")
    print(f"Total records: {len(df):,}")
    print(f"Unique players: {df[['first_name', 'last_name']].drop_duplicates().shape[0]:,}")
    print(f"Gameweeks covered: {df['gameweek'].min()} to {df['gameweek'].max()}")
    print(f"\nRole distribution:")
    print(df['role'].value_counts())
    
    # Show sample of predictions for weeks after last_observable_week
    future_df = df[df['gameweek'] > last_observable_week]
    if len(future_df) > 0:
        print(f"\nSample predictions for gameweek {last_observable_week + 1}:")
        sample = future_df[future_df['gameweek'] == last_observable_week + 1].nlargest(10, 'average_score')
        print(sample[['first_name', 'last_name', 'club', 'average_score', 'role', 'price']].to_string(index=False))


if __name__ == "__main__":
    main()