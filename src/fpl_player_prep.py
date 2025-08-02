#!/usr/bin/env python3
"""
FPL Player Bradley-Terry Matrix Preparation
Builds a Bradley-Terry matrix based on player head-to-head comparisons

Usage: python src/fpl_player_prep.py [YEAR] [PREVIOUS_WEEK] [NEXT_WEEK]
Example: python src/fpl_player_prep.py 2024 9 10
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import json


class BradleyTerryBuilder:
    def __init__(self, season_year):
        self.season_year = season_year
        self.data_dir = Path("data") / f"{season_year}"
        
        # Load data files
        self.players_df = pd.read_csv(self.data_dir / f"{season_year}_players.csv")
        self.gameweek_df = pd.read_csv(self.data_dir / f"{season_year}_player_gameweek.csv")
        
        # Create player ID to name mapping
        if 'element' in self.gameweek_df.columns:
            self.player_id_col = 'element'
        else:
            self.player_id_col = 'player_id'
            
        # Get unique players who actually played
        self.active_players = self.gameweek_df[self.gameweek_df['minutes'] > 0][self.player_id_col].unique()
        
        # Create mappings
        self.player_names = self.gameweek_df.groupby(self.player_id_col)['name'].first().to_dict()
        self.player_to_idx = {pid: idx for idx, pid in enumerate(self.active_players)}
        self.idx_to_player = {idx: pid for pid, idx in self.player_to_idx.items()}
        
        self.n_players = len(self.active_players)
        
    def build_bradley_terry_matrix(self, previous_week=None, home_advantage=0.2):
        """
        Build Bradley-Terry matrix based on gameweeks 1 to previous_week
        
        Matrix[i,j] = number of weeks player i scored more points than player j
        
        Args:
            previous_week: Last gameweek to include (None for all)
            home_advantage: Points advantage for home players (default 0.2)
        """
        print(f"\nBuilding Bradley-Terry matrix for {self.n_players} active players...")
        print(f"Home advantage: {home_advantage} points")
        
        # Filter gameweeks
        if previous_week is None:
            gw_data = self.gameweek_df
            max_gw = gw_data['GW'].max()
            print(f"Using all gameweeks (1-{max_gw})")
        else:
            gw_data = self.gameweek_df[self.gameweek_df['GW'] <= previous_week]
            print(f"Using gameweeks 1-{previous_week}")
        
        # Initialize matrix
        bt_matrix = np.zeros((self.n_players, self.n_players), dtype=int)
        
        # Process each gameweek
        unique_gws = sorted(gw_data['GW'].unique())
        
        for gw in unique_gws:
            print(f"  Processing GW{gw}...", end='\r')
            
            # Get points and home/away status for this gameweek
            gw_points = gw_data[gw_data['GW'] == gw][[self.player_id_col, 'total_points', 'was_home']]
            
            # Only consider players who played (already filtered by minutes > 0)
            players_this_gw = gw_points[self.player_id_col].values
            points_this_gw = gw_points.set_index(self.player_id_col)['total_points'].to_dict()
            home_status = gw_points.set_index(self.player_id_col)['was_home'].to_dict()
            
            # Compare all pairs of players who played this gameweek
            for i, p1 in enumerate(players_this_gw):
                if p1 not in self.player_to_idx:
                    continue
                    
                idx1 = self.player_to_idx[p1]
                p1_points = points_this_gw.get(p1, 0)
                p1_home = home_status.get(p1, False)
                
                # Apply home advantage
                p1_adjusted = p1_points + (home_advantage if p1_home else 0)
                
                for j, p2 in enumerate(players_this_gw):
                    if i >= j or p2 not in self.player_to_idx:  # Avoid double counting and self-comparison
                        continue
                        
                    idx2 = self.player_to_idx[p2]
                    p2_points = points_this_gw.get(p2, 0)
                    p2_home = home_status.get(p2, False)
                    
                    # Apply home advantage
                    p2_adjusted = p2_points + (home_advantage if p2_home else 0)
                    
                    # Update matrix based on comparison with adjusted points
                    if p1_adjusted > p2_adjusted:
                        bt_matrix[idx1, idx2] += 1
                    elif p2_adjusted > p1_adjusted:
                        bt_matrix[idx2, idx1] += 1
                    # If equal points (after adjustment), no update (draw)
        
        print(f"\n✓ Bradley-Terry matrix built ({self.n_players}x{self.n_players})")
        
        return bt_matrix
    
    def get_player_stats(self, previous_week=None, next_week=None):
        """Get additional player statistics for the specified period"""
        
        # Filter data
        if previous_week is None:
            hist_data = self.gameweek_df
        else:
            hist_data = self.gameweek_df[self.gameweek_df['GW'] <= previous_week]
        
        # Calculate historical stats
        player_stats = hist_data.groupby(self.player_id_col).agg({
            'total_points': ['sum', 'mean', 'std'],
            'minutes': 'sum',
            'GW': 'count',
            'price': ['first', 'last'],
            'position': 'first',
            'team': 'first'
        }).round(2)
        
        player_stats.columns = ['total_points', 'avg_points', 'std_points', 
                              'total_minutes', 'games_played', 
                              'start_price', 'end_price', 'position', 'team']
        
        # Add player names
        player_stats['name'] = player_stats.index.map(self.player_names)
        
        # If next_week specified, get that week's data
        if next_week is not None:
            next_gw_data = self.gameweek_df[self.gameweek_df['GW'] == next_week]
            next_points = next_gw_data.set_index(self.player_id_col)['total_points']
            player_stats['next_week_points'] = next_points
            player_stats['next_week_points'] = player_stats['next_week_points'].fillna(0)
        
        return player_stats
    
    def analyze_matrix(self, bt_matrix):
        """Analyze the Bradley-Terry matrix to find dominant players"""
        
        # Calculate win totals
        wins = bt_matrix.sum(axis=1)
        losses = bt_matrix.sum(axis=0)
        total_comparisons = wins + losses
        win_rate = np.divide(wins, total_comparisons, where=total_comparisons > 0)
        
        # Create summary DataFrame
        summary = pd.DataFrame({
            'player_id': [self.idx_to_player[i] for i in range(self.n_players)],
            'wins': wins,
            'losses': losses,
            'total_comparisons': total_comparisons,
            'win_rate': win_rate
        })
        
        # Add player names and sort by win rate
        summary['name'] = summary['player_id'].map(self.player_names)
        summary = summary[summary['total_comparisons'] > 0].sort_values('win_rate', ascending=False)
        
        return summary
    
    def save_results(self, bt_matrix, player_stats, previous_week=None, next_week=None, home_advantage=0.2):
        """Save Bradley-Terry matrix and related data"""
        
        # Create output directory
        output_dir = self.data_dir / "bradley_terry"
        output_dir.mkdir(exist_ok=True)
        
        # Determine file suffix
        if previous_week is None:
            suffix = "all_weeks"
        else:
            suffix = f"weeks_1_to_{previous_week}"
            
        # Save matrix as numpy array
        matrix_file = output_dir / f"bt_matrix_{suffix}.npy"
        np.save(matrix_file, bt_matrix)
        print(f"\n✓ Saved Bradley-Terry matrix to {matrix_file}")
        
        # Save player mappings (convert numpy types to Python types for JSON)
        mappings = {
            'player_to_idx': {str(k): int(v) for k, v in self.player_to_idx.items()},
            'idx_to_player': {str(k): int(v) for k, v in self.idx_to_player.items()},
            'player_names': {str(k): str(v) for k, v in self.player_names.items()},
            'n_players': int(self.n_players),
            'previous_week': int(previous_week) if previous_week is not None else None,
            'next_week': int(next_week) if next_week is not None else None,
            'home_advantage': float(home_advantage)
        }
        
        mappings_file = output_dir / f"player_mappings_{suffix}.json"
        with open(mappings_file, 'w') as f:
            json.dump(mappings, f, indent=2)
        print(f"✓ Saved player mappings to {mappings_file}")
        
        # Save player stats
        stats_file = output_dir / f"player_stats_{suffix}.csv"
        player_stats.to_csv(stats_file)
        print(f"✓ Saved player statistics to {stats_file}")
        
        # Save matrix analysis
        analysis = self.analyze_matrix(bt_matrix)
        analysis_file = output_dir / f"matrix_analysis_{suffix}.csv"
        analysis.to_csv(analysis_file, index=False)
        print(f"✓ Saved matrix analysis to {analysis_file}")
        
        return output_dir
    
    def print_summary(self, bt_matrix, player_stats, previous_week=None):
        """Print summary of results"""
        
        print("\n" + "="*60)
        print("Bradley-Terry Matrix Summary")
        print("="*60)
        
        # Matrix info
        print(f"\nMatrix dimensions: {bt_matrix.shape}")
        print(f"Total comparisons: {bt_matrix.sum():,}")
        print(f"Active players: {self.n_players}")
        
        # Top performers by win rate
        analysis = self.analyze_matrix(bt_matrix)
        print("\nTop 10 players by win rate (min 100 comparisons):")
        top_players = analysis[analysis['total_comparisons'] >= 100].head(10)
        
        for _, player in top_players.iterrows():
            print(f"  {player['name']}: {player['win_rate']:.3f} "
                  f"({player['wins']}/{player['total_comparisons']})")
        
        # Most dominant head-to-heads
        print("\nMost dominant head-to-head records:")
        dominant_pairs = []
        
        for i in range(self.n_players):
            for j in range(i+1, self.n_players):
                diff = abs(bt_matrix[i,j] - bt_matrix[j,i])
                total = bt_matrix[i,j] + bt_matrix[j,i]
                
                if total >= 10 and diff >= 5:  # Significant difference
                    if bt_matrix[i,j] > bt_matrix[j,i]:
                        winner_idx, loser_idx = i, j
                    else:
                        winner_idx, loser_idx = j, i
                        
                    dominant_pairs.append({
                        'winner': self.player_names.get(self.idx_to_player[winner_idx], 'Unknown'),
                        'loser': self.player_names.get(self.idx_to_player[loser_idx], 'Unknown'),
                        'wins': max(bt_matrix[i,j], bt_matrix[j,i]),
                        'losses': min(bt_matrix[i,j], bt_matrix[j,i]),
                        'diff': diff
                    })
        
        dominant_pairs.sort(key=lambda x: x['diff'], reverse=True)
        
        for pair in dominant_pairs[:5]:
            print(f"  {pair['winner']} vs {pair['loser']}: "
                  f"{pair['wins']}-{pair['losses']} "
                  f"(+{pair['diff']})")


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/fpl_player_prep.py [YEAR] [PREVIOUS_WEEK] [NEXT_WEEK] [HOME_ADVANTAGE]")
        print("Example: python src/fpl_player_prep.py 2024 9 10 0.2")
        print("\nIf PREVIOUS_WEEK is not specified, uses all gameweeks")
        print("Default HOME_ADVANTAGE is 0.2 points")
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
    
    print(f"Building Bradley-Terry matrix for {season_year}/{season_year+1} season")
    
    # Initialize builder
    builder = BradleyTerryBuilder(season_year)
    
    # Build matrix with home advantage
    bt_matrix = builder.build_bradley_terry_matrix(previous_week, home_advantage)
    
    # Get player stats
    player_stats = builder.get_player_stats(previous_week, next_week)
    
    # Save results
    output_dir = builder.save_results(bt_matrix, player_stats, previous_week, next_week, home_advantage)
    
    # Print summary
    builder.print_summary(bt_matrix, player_stats, previous_week)
    
    print(f"\n✓ All results saved to: {output_dir}")


if __name__ == "__main__":
    main()