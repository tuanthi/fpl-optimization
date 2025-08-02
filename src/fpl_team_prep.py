#!/usr/bin/env python3
"""
FPL Team Bradley-Terry Matrix Preparation
Builds a Bradley-Terry matrix based on team head-to-head comparisons

Usage: python src/fpl_team_prep.py [YEAR] [PREVIOUS_WEEK] [NEXT_WEEK] [HOME_ADVANTAGE]
Example: python src/fpl_team_prep.py 2024 9 10 0.2
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import json


class TeamBradleyTerryBuilder:
    def __init__(self, season_year):
        self.season_year = season_year
        self.data_dir = Path("data") / f"{season_year}"
        
        # Load data files
        self.teams_df = pd.read_csv(self.data_dir / f"{season_year}_teams.csv")
        self.gameweek_df = pd.read_csv(self.data_dir / f"{season_year}_player_gameweek.csv")
        self.fixtures_df = pd.read_csv(self.data_dir / f"{season_year}_fixtures.csv")
        
        # Create team mappings
        self.team_names = self.teams_df.set_index('id')['name'].to_dict()
        self.team_name_to_id = {v: k for k, v in self.team_names.items()}
        
        # Get unique teams - use team names from gameweek data
        self.unique_teams = sorted(self.gameweek_df['team'].unique())
        self.team_to_idx = {team: idx for idx, team in enumerate(self.unique_teams)}
        self.idx_to_team = {idx: team for team, idx in self.team_to_idx.items()}
        
        self.n_teams = len(self.unique_teams)
        
    def build_bradley_terry_matrix(self, previous_week=None, home_advantage=0.2):
        """
        Build Bradley-Terry matrix based on team performance aggregated by gameweek
        
        Matrix[i,j] = number of weeks team i scored more total points than team j
        
        Args:
            previous_week: Last gameweek to include (None for all)
            home_advantage: Points advantage for home team players (default 0.2)
        """
        print(f"\nBuilding Bradley-Terry matrix for {self.n_teams} teams...")
        print(f"Home advantage: {home_advantage} points per player")
        
        # Filter gameweeks
        if previous_week is None:
            gw_data = self.gameweek_df
            max_gw = gw_data['GW'].max()
            print(f"Using all gameweeks (1-{max_gw})")
        else:
            gw_data = self.gameweek_df[self.gameweek_df['GW'] <= previous_week]
            print(f"Using gameweeks 1-{previous_week}")
        
        # Initialize matrix
        bt_matrix = np.zeros((self.n_teams, self.n_teams), dtype=int)
        
        # Process each gameweek
        unique_gws = sorted(gw_data['GW'].unique())
        
        for gw in unique_gws:
            print(f"  Processing GW{gw}...", end='\r')
            
            # Get all player points for this gameweek
            gw_players = gw_data[gw_data['GW'] == gw].copy()
            
            # Apply home advantage to player points
            gw_players['adjusted_points'] = gw_players.apply(
                lambda row: row['total_points'] + (home_advantage if row['was_home'] else 0),
                axis=1
            )
            
            # Aggregate points by team
            team_points = gw_players.groupby('team')['adjusted_points'].sum().to_dict()
            
            # Get teams that played this gameweek
            teams_this_gw = list(team_points.keys())
            
            # Compare all pairs of teams
            for i, team1 in enumerate(teams_this_gw):
                if team1 not in self.team_to_idx:
                    continue
                    
                idx1 = self.team_to_idx[team1]
                team1_points = team_points.get(team1, 0)
                
                for j, team2 in enumerate(teams_this_gw):
                    if i >= j or team2 not in self.team_to_idx:  # Avoid double counting and self-comparison
                        continue
                        
                    idx2 = self.team_to_idx[team2]
                    team2_points = team_points.get(team2, 0)
                    
                    # Update matrix based on comparison
                    if team1_points > team2_points:
                        bt_matrix[idx1, idx2] += 1
                    elif team2_points > team1_points:
                        bt_matrix[idx2, idx1] += 1
                    # If equal points, no update (draw)
        
        print(f"\n✓ Bradley-Terry matrix built ({self.n_teams}x{self.n_teams})")
        
        return bt_matrix
    
    def get_team_stats(self, previous_week=None, next_week=None):
        """Get additional team statistics for the specified period"""
        
        # Filter data
        if previous_week is None:
            hist_data = self.gameweek_df
        else:
            hist_data = self.gameweek_df[self.gameweek_df['GW'] <= previous_week]
        
        # Calculate team statistics
        team_stats = hist_data.groupby('team').agg({
            'total_points': ['sum', 'mean', 'std'],
            'minutes': 'sum',
            'goals_scored': 'sum',
            'assists': 'sum',
            'clean_sheets': 'sum',
            'goals_conceded': 'sum',
            'yellow_cards': 'sum',
            'red_cards': 'sum'
        }).round(2)
        
        team_stats.columns = ['total_points', 'avg_points_per_player', 'std_points',
                            'total_minutes', 'total_goals', 'total_assists',
                            'total_clean_sheets', 'total_goals_conceded',
                            'total_yellow_cards', 'total_red_cards']
        
        # Team names are already the index (no mapping needed)
        team_stats['name'] = team_stats.index
        
        # Calculate additional metrics
        team_stats['players_used'] = hist_data.groupby('team')['element'].nunique()
        team_stats['gameweeks_played'] = hist_data.groupby('team')['GW'].nunique()
        
        # If next_week specified, get that week's data
        if next_week is not None:
            next_gw_data = self.gameweek_df[self.gameweek_df['GW'] == next_week]
            next_points = next_gw_data.groupby('team')['total_points'].sum()
            team_stats['next_week_points'] = next_points
            team_stats['next_week_points'] = team_stats['next_week_points'].fillna(0)
        
        # Get fixture difficulty
        if previous_week is not None:
            # Calculate average opponent difficulty for upcoming fixtures
            upcoming_fixtures = self.fixtures_df[
                (self.fixtures_df['event'] > previous_week) & 
                (self.fixtures_df['event'] <= (previous_week + 5))
            ]
            
            home_difficulty = upcoming_fixtures.groupby('team_h')['team_a_difficulty'].mean()
            away_difficulty = upcoming_fixtures.groupby('team_a')['team_h_difficulty'].mean()
            
            avg_difficulty = pd.concat([home_difficulty, away_difficulty]).groupby(level=0).mean()
            team_stats['upcoming_difficulty'] = team_stats.index.map(avg_difficulty).fillna(3.0)
        
        return team_stats
    
    def analyze_matrix(self, bt_matrix):
        """Analyze the Bradley-Terry matrix to find dominant teams"""
        
        # Calculate win totals
        wins = bt_matrix.sum(axis=1)
        losses = bt_matrix.sum(axis=0)
        total_comparisons = wins + losses
        win_rate = np.divide(wins, total_comparisons, where=total_comparisons > 0)
        
        # Create summary DataFrame
        summary = pd.DataFrame({
            'team': [self.idx_to_team[i] for i in range(self.n_teams)],
            'wins': wins,
            'losses': losses,
            'total_comparisons': total_comparisons,
            'win_rate': win_rate
        })
        
        # Sort by win rate
        summary = summary[summary['total_comparisons'] > 0].sort_values('win_rate', ascending=False)
        
        return summary
    
    def save_results(self, bt_matrix, team_stats, previous_week=None, next_week=None, home_advantage=0.2):
        """Save Bradley-Terry matrix and related data"""
        
        # Create output directory
        output_dir = self.data_dir / "team_bradley_terry"
        output_dir.mkdir(exist_ok=True)
        
        # Determine file suffix
        if previous_week is None:
            suffix = "all_weeks"
        else:
            suffix = f"weeks_1_to_{previous_week}"
            
        # Save matrix as numpy array
        matrix_file = output_dir / f"team_bt_matrix_{suffix}.npy"
        np.save(matrix_file, bt_matrix)
        print(f"\n✓ Saved Team Bradley-Terry matrix to {matrix_file}")
        
        # Save team mappings
        mappings = {
            'team_to_idx': {str(k): int(v) for k, v in self.team_to_idx.items()},
            'idx_to_team': {str(k): str(v) for k, v in self.idx_to_team.items()},
            'team_names': {str(k): str(v) for k, v in self.team_names.items()},
            'n_teams': int(self.n_teams),
            'previous_week': int(previous_week) if previous_week is not None else None,
            'next_week': int(next_week) if next_week is not None else None,
            'home_advantage': float(home_advantage)
        }
        
        mappings_file = output_dir / f"team_mappings_{suffix}.json"
        with open(mappings_file, 'w') as f:
            json.dump(mappings, f, indent=2)
        print(f"✓ Saved team mappings to {mappings_file}")
        
        # Save team stats
        stats_file = output_dir / f"team_stats_{suffix}.csv"
        team_stats.to_csv(stats_file)
        print(f"✓ Saved team statistics to {stats_file}")
        
        # Save matrix analysis
        analysis = self.analyze_matrix(bt_matrix)
        analysis_file = output_dir / f"team_matrix_analysis_{suffix}.csv"
        analysis.to_csv(analysis_file, index=False)
        print(f"✓ Saved matrix analysis to {analysis_file}")
        
        return output_dir
    
    def print_summary(self, bt_matrix, team_stats, previous_week=None):
        """Print summary of results"""
        
        print("\n" + "="*60)
        print("Team Bradley-Terry Matrix Summary")
        print("="*60)
        
        # Matrix info
        print(f"\nMatrix dimensions: {bt_matrix.shape}")
        print(f"Total comparisons: {bt_matrix.sum():,}")
        print(f"Teams: {self.n_teams}")
        
        # Top performers by win rate
        analysis = self.analyze_matrix(bt_matrix)
        print("\nTeam rankings by win rate:")
        
        for _, team in analysis.iterrows():
            print(f"  {team['team']}: {team['win_rate']:.3f} "
                  f"({team['wins']}/{team['total_comparisons']})")
        
        # Most dominant head-to-heads
        print("\nMost dominant head-to-head records:")
        dominant_pairs = []
        
        for i in range(self.n_teams):
            for j in range(i+1, self.n_teams):
                diff = abs(bt_matrix[i,j] - bt_matrix[j,i])
                total = bt_matrix[i,j] + bt_matrix[j,i]
                
                if total >= 5 and diff >= 3:  # Significant difference
                    if bt_matrix[i,j] > bt_matrix[j,i]:
                        winner_idx, loser_idx = i, j
                    else:
                        winner_idx, loser_idx = j, i
                        
                    dominant_pairs.append({
                        'winner': self.idx_to_team[winner_idx],
                        'loser': self.idx_to_team[loser_idx],
                        'wins': max(bt_matrix[i,j], bt_matrix[j,i]),
                        'losses': min(bt_matrix[i,j], bt_matrix[j,i]),
                        'diff': diff
                    })
        
        dominant_pairs.sort(key=lambda x: x['diff'], reverse=True)
        
        for pair in dominant_pairs[:5]:
            print(f"  {pair['winner']} vs {pair['loser']}: "
                  f"{pair['wins']}-{pair['losses']} "
                  f"(+{pair['diff']})")
        
        # Team performance summary
        if not team_stats.empty:
            print("\nTop 5 teams by total FPL points:")
            top_teams = team_stats.nlargest(5, 'total_points')[['name', 'total_points', 'avg_points_per_player', 'players_used']]
            for idx, team in top_teams.iterrows():
                print(f"  {idx}: {int(team['total_points'])} pts "
                      f"({team['avg_points_per_player']:.1f} avg/player, "
                      f"{int(team['players_used'])} players)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/fpl_team_prep.py [YEAR] [PREVIOUS_WEEK] [NEXT_WEEK] [HOME_ADVANTAGE]")
        print("Example: python src/fpl_team_prep.py 2024 9 10 0.2")
        print("\nIf PREVIOUS_WEEK is not specified, uses all gameweeks")
        print("Default HOME_ADVANTAGE is 0.2 points per player")
        sys.exit(1)
    
    season_year = int(sys.argv[1])
    previous_week = int(sys.argv[2]) if len(sys.argv) > 2 else None
    next_week = int(sys.argv[3]) if len(sys.argv) > 3 else None
    home_advantage = float(sys.argv[4]) if len(sys.argv) > 4 else 0.2
    
    # Check if data exists
    data_dir = Path("data") / f"{season_year}"
    if not data_dir.exists():
        print(f"Error: No data found for {season_year}. Run fpl_download.py first.")
        sys.exit(1)
    
    print(f"Building Team Bradley-Terry matrix for {season_year}/{season_year+1} season")
    
    # Initialize builder
    builder = TeamBradleyTerryBuilder(season_year)
    
    # Build matrix with home advantage
    bt_matrix = builder.build_bradley_terry_matrix(previous_week, home_advantage)
    
    # Get team stats
    team_stats = builder.get_team_stats(previous_week, next_week)
    
    # Save results
    output_dir = builder.save_results(bt_matrix, team_stats, previous_week, next_week, home_advantage)
    
    # Print summary
    builder.print_summary(bt_matrix, team_stats, previous_week)
    
    print(f"\n✓ All results saved to: {output_dir}")


if __name__ == "__main__":
    main()