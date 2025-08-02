#!/usr/bin/env python3
"""
End-to-End FPL Prediction Pipeline
Downloads data, builds Bradley-Terry matrices, and predicts scores for a target gameweek

Usage: python src/end_to_end_prediction.py [GAMEWEEK]
Example: python src/end_to_end_prediction.py 8
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import json
import subprocess
from datetime import datetime


class EndToEndFPLPredictor:
    def __init__(self, target_gameweek, season_year=None):
        """Initialize the predictor
        
        Args:
            target_gameweek: The gameweek to predict
            season_year: The season year (default: current season)
        """
        self.target_gameweek = target_gameweek
        
        # Determine season year
        if season_year is None:
            current_date = datetime.now()
            if current_date.month >= 8:
                self.season_year = current_date.year
            else:
                self.season_year = current_date.year - 1
        else:
            self.season_year = season_year
            
        self.data_dir = Path("data") / f"{self.season_year}"
        self.position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        
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
            
    def download_data(self):
        """Download FPL data for the season"""
        print(f"\n{'='*60}")
        print(f"Step 1: Downloading FPL data for {self.season_year}/{self.season_year+1} season")
        print(f"{'='*60}")
        
        cmd = f"source .venv/bin/activate && python src/fpl_download.py {self.season_year}"
        return self.run_command(cmd, "Downloading FPL data")
        
    def check_available_gameweeks(self):
        """Check which gameweeks have actual data"""
        gameweek_file = self.data_dir / f"{self.season_year}_player_gameweek.csv"
        
        if not gameweek_file.exists():
            print(f"Error: Gameweek data file not found at {gameweek_file}")
            return []
            
        df = pd.read_csv(gameweek_file)
        available_weeks = sorted(df['GW'].unique())
        
        # For testing iterative predictions, we can limit available weeks
        # Uncomment the next line to simulate having data only up to gameweek 4
        # available_weeks = [w for w in available_weeks if w <= 4]
        
        print(f"\nAvailable gameweeks with data: {available_weeks}")
        return available_weeks
        
    def build_bradley_terry_matrix(self, up_to_week, home_advantage=0.2):
        """Build Bradley-Terry matrices for players and teams"""
        print(f"\n{'='*60}")
        print(f"Building Bradley-Terry matrices for weeks 1-{up_to_week}")
        print(f"{'='*60}")
        
        # Build player matrix
        cmd = f"source .venv/bin/activate && python src/fpl_player_prep.py {self.season_year} {up_to_week} {up_to_week + 1} {home_advantage}"
        if not self.run_command(cmd, f"Building player Bradley-Terry matrix (weeks 1-{up_to_week})"):
            return False
            
        # Build team matrix
        cmd = f"source .venv/bin/activate && python src/fpl_team_prep.py {self.season_year} {up_to_week} {up_to_week + 1} {home_advantage}"
        if not self.run_command(cmd, f"Building team Bradley-Terry matrix (weeks 1-{up_to_week})"):
            return False
            
        return True
        
    def predict_single_gameweek(self, predict_week, based_on_weeks):
        """Predict scores for a single gameweek based on previous weeks"""
        print(f"\nPredicting gameweek {predict_week} based on weeks 1-{based_on_weeks}")
        
        # First build Bradley-Terry matrices
        if not self.build_bradley_terry_matrix(based_on_weeks):
            return None
            
        # Load the matrices and calculate scores
        bt_dir = self.data_dir / "bradley_terry"
        team_bt_dir = self.data_dir / "team_bradley_terry"
        
        suffix = f"weeks_1_to_{based_on_weeks}"
        
        # Load player Bradley-Terry matrix
        player_matrix = np.load(bt_dir / f"bt_matrix_{suffix}.npy")
        with open(bt_dir / f"player_mappings_{suffix}.json", 'r') as f:
            player_mappings = json.load(f)
            
        # Load team Bradley-Terry matrix
        team_matrix = np.load(team_bt_dir / f"team_bt_matrix_{suffix}.npy")
        with open(team_bt_dir / f"team_mappings_{suffix}.json", 'r') as f:
            team_mappings = json.load(f)
            
        # Calculate Bradley-Terry scores
        player_scores = self.calculate_bradley_terry_scores(player_matrix)
        team_scores = self.calculate_bradley_terry_scores(team_matrix)
        
        # Create predicted scores dataframe
        predictions = self.create_predictions_dataframe(
            predict_week, player_scores, team_scores, 
            player_mappings, team_mappings
        )
        
        return predictions
        
    def calculate_bradley_terry_scores(self, matrix):
        """Calculate Bradley-Terry scores from win matrix"""
        n = matrix.shape[0]
        epsilon = 1e-6
        total_comparisons = matrix + matrix.T + epsilon
        
        win_rates = np.zeros(n)
        for i in range(n):
            wins = matrix[i, :].sum()
            total = total_comparisons[i, :].sum()
            win_rates[i] = wins / total if total > 0 else 0.5
            
        # Convert to Bradley-Terry scores (log-odds)
        scores = np.log(win_rates + epsilon) - np.log(1 - win_rates + epsilon)
        
        # Normalize scores
        scores = (scores - scores.mean()) / (scores.std() + epsilon)
        
        return scores
        
    def create_predictions_dataframe(self, gameweek, player_scores, team_scores, 
                                   player_mappings, team_mappings):
        """Create dataframe with predicted scores for a gameweek"""
        # Load player metadata
        players_df = pd.read_csv(self.data_dir / f"{self.season_year}_players.csv")
        gameweek_df = pd.read_csv(self.data_dir / f"{self.season_year}_player_gameweek.csv")
        
        # Get all unique players
        all_players = gameweek_df['element'].unique()
        
        results = []
        
        for player_id in all_players:
            # Get player info
            player_info = players_df[players_df['id'] == player_id]
            if len(player_info) == 0:
                continue
                
            player_info = player_info.iloc[0]
            
            # Get player's team
            player_gw_data = gameweek_df[gameweek_df['element'] == player_id]
            if len(player_gw_data) > 0:
                team = player_gw_data.iloc[-1]['team']
                price = player_gw_data.iloc[-1]['price']
            else:
                continue
                
            # Get scores
            player_score = 0.0
            player_to_idx = {int(k): v for k, v in player_mappings['player_to_idx'].items()}
            if player_id in player_to_idx:
                player_idx = player_to_idx[player_id]
                player_score = player_scores[player_idx]
                
            team_score = 0.0
            if team in team_mappings['team_to_idx']:
                team_idx = team_mappings['team_to_idx'][team]
                team_score = team_scores[team_idx]
                
            # Calculate average score
            average_score = (player_score + team_score) / 2
            
            # Create full name
            first_name = player_info['first_name']
            last_name = player_info['second_name'] if pd.notna(player_info['second_name']) and player_info['second_name'] != '' else player_info['web_name']
            
            results.append({
                'first_name': first_name,
                'last_name': last_name,
                'club': team,
                'gameweek': gameweek,
                'price': price,
                'player_score': round(player_score, 4),
                'team_score': round(team_score, 4),
                'average_score': round(average_score, 4),
                'role': self.position_map.get(player_info['element_type'], 'UNK')
            })
            
        return pd.DataFrame(results)
        
    def update_gameweek_data_with_predictions(self, predictions_df, gameweek):
        """Add predicted scores to gameweek data for iterative predictions"""
        # Load existing gameweek data
        gameweek_file = self.data_dir / f"{self.season_year}_player_gameweek.csv"
        gameweek_df = pd.read_csv(gameweek_file)
        
        # Create new gameweek data from predictions
        new_gw_data = []
        
        for _, pred in predictions_df.iterrows():
            # Find player element ID
            players_df = pd.read_csv(self.data_dir / f"{self.season_year}_players.csv")
            
            # Match by name
            player_match = players_df[
                (players_df['first_name'] == pred['first_name']) & 
                ((players_df['second_name'] == pred['last_name']) | (players_df['web_name'] == pred['last_name']))
            ]
            
            if len(player_match) > 0:
                player_id = player_match.iloc[0]['id']
                
                # Get last known data for this player
                last_data = gameweek_df[gameweek_df['element'] == player_id].iloc[-1] if len(gameweek_df[gameweek_df['element'] == player_id]) > 0 else None
                
                if last_data is not None:
                    # Create new row with predicted points
                    new_row = last_data.copy()
                    new_row['GW'] = gameweek
                    new_row['total_points'] = max(0, int(pred['average_score'] * 5))  # Scale score to points
                    new_row['price'] = pred['price']
                    new_gw_data.append(new_row)
                    
        # Append new data to gameweek dataframe
        if new_gw_data:
            new_df = pd.DataFrame(new_gw_data)
            gameweek_df = pd.concat([gameweek_df, new_df], ignore_index=True)
            gameweek_df.to_csv(gameweek_file, index=False)
            print(f"Added {len(new_gw_data)} predicted entries for gameweek {gameweek}")
            
    def find_optimal_teams(self, last_observable_week):
        """Find optimal teams using the prediction data"""
        print(f"\n{'='*60}")
        print(f"Finding optimal teams based on predictions")
        print(f"{'='*60}")
        
        # Generate week sampling data
        cmd = f"source .venv/bin/activate && python src/fpl_week_sampling.py {self.season_year} 1 {last_observable_week}"
        if not self.run_command(cmd, "Generating week sampling data"):
            return False
            
        # Find top 50 teams
        pred_file = self.data_dir / f"pred_{self.season_year}_week_sampling_1_to_{last_observable_week}.csv"
        output_file = self.data_dir / f"end_to_end_top_50_teams_gameweek_{self.target_gameweek}.csv"
        
        cmd = f"source .venv/bin/activate && python src/fpl_optimization_runner.py {pred_file} {output_file}"
        if not self.run_command(cmd, "Finding optimal team combinations"):
            return False
            
        return True
        
    def run_end_to_end_prediction(self):
        """Run the complete end-to-end prediction pipeline"""
        print(f"\n{'='*80}")
        print(f"END-TO-END FPL PREDICTION FOR GAMEWEEK {self.target_gameweek}")
        print(f"Season: {self.season_year}/{self.season_year+1}")
        print(f"{'='*80}")
        
        # Step 1: Download data
        if not self.download_data():
            print("Failed to download data")
            return False
            
        # Step 2: Check available gameweeks
        available_weeks = self.check_available_gameweeks()
        if not available_weeks:
            print("No gameweek data available")
            return False
            
        last_available_week = max(available_weeks)
        print(f"Last available gameweek: {last_available_week}")
        
        # Step 3: Determine prediction strategy
        if self.target_gameweek <= last_available_week:
            # We have actual data for the target week
            print(f"\nTarget gameweek {self.target_gameweek} has actual data available")
            observable_weeks = self.target_gameweek - 1
        else:
            # Need to predict future weeks
            print(f"\nTarget gameweek {self.target_gameweek} is beyond available data")
            print(f"Will predict gameweeks {last_available_week + 1} to {self.target_gameweek}")
            observable_weeks = last_available_week
            
        # Step 4: Build matrices and predict iteratively if needed
        if self.target_gameweek > last_available_week:
            # Need to predict intermediate weeks
            for week in range(last_available_week + 1, self.target_gameweek + 1):
                print(f"\n{'='*60}")
                print(f"Predicting gameweek {week}")
                print(f"{'='*60}")
                
                # Predict this week based on all previous weeks
                predictions = self.predict_single_gameweek(week, week - 1)
                
                if predictions is not None:
                    # Save predictions
                    pred_file = self.data_dir / f"predicted_gameweek_{week}.csv"
                    predictions.to_csv(pred_file, index=False)
                    print(f"Saved predictions to {pred_file}")
                    
                    # Update gameweek data with predictions for next iteration
                    if week < self.target_gameweek:
                        self.update_gameweek_data_with_predictions(predictions, week)
                else:
                    print(f"Failed to predict gameweek {week}")
                    return False
        else:
            # Just build matrices for the target week
            if not self.build_bradley_terry_matrix(observable_weeks):
                return False
                
        # Step 5: Find optimal teams
        if not self.find_optimal_teams(self.target_gameweek - 1):
            return False
            
        # Step 6: Save final output
        output_file = self.data_dir / f"end_to_end_prediction_gameweek_{self.target_gameweek}.csv"
        
        # Copy the top teams file to the final output
        import shutil
        source_file = self.data_dir / f"end_to_end_top_50_teams_gameweek_{self.target_gameweek}.csv"
        if source_file.exists():
            shutil.copy(source_file, output_file)
            print(f"\n{'='*60}")
            print(f"PREDICTION COMPLETE!")
            print(f"Final predictions saved to: {output_file}")
            print(f"{'='*60}")
            
            # Show summary
            results_df = pd.read_csv(output_file)
            print(f"\nTop 5 predicted teams for gameweek {self.target_gameweek}:")
            print(results_df[['11_selected_total_scores', '15_total_price']].head())
            
            return True
        else:
            print("Failed to generate final output")
            return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/end_to_end_prediction.py [GAMEWEEK]")
        print("Example: python src/end_to_end_prediction.py 8")
        sys.exit(1)
        
    target_gameweek = int(sys.argv[1])
    
    # Optional: specify season year as second argument
    season_year = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # Create predictor and run
    predictor = EndToEndFPLPredictor(target_gameweek, season_year)
    
    # Run the prediction pipeline
    success = predictor.run_end_to_end_prediction()
    
    if not success:
        print("\nPrediction pipeline failed!")
        sys.exit(1)
    else:
        print("\nPrediction pipeline completed successfully!")


if __name__ == "__main__":
    main()