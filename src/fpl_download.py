#!/usr/bin/env python3
"""
Consolidated FPL data downloader
Downloads all FPL data for a given season and saves to .venv/data/

Usage: python src/fpl_download.py [YEAR]
Example: python src/fpl_download.py 2024
"""

import sys
import os
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path


class FPLDownloader:
    def __init__(self, season_year):
        self.season_year = season_year
        self.season_str = f"{season_year}-{str(season_year + 1)[-2:]}"
        self.data_dir = Path("data") / f"{season_year}"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # API URLs
        self.fpl_base_url = "https://fantasy.premierleague.com/api/"
        self.historical_base = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
        
        # Output files
        self.output_files = {
            'players': self.data_dir / f"{season_year}_players.csv",
            'fixtures': self.data_dir / f"{season_year}_fixtures.csv",
            'teams': self.data_dir / f"{season_year}_teams.csv",
            'player_gameweek': self.data_dir / f"{season_year}_player_gameweek.csv"
        }
        
    def download_current_season_data(self):
        """Download data from official FPL API (for current/upcoming season)"""
        print(f"Attempting to download {self.season_year}/{self.season_year+1} season from FPL API...")
        
        try:
            # Get bootstrap data
            response = requests.get(f"{self.fpl_base_url}bootstrap-static/")
            response.raise_for_status()
            data = response.json()
            
            # Extract and save players
            players_df = pd.DataFrame(data['elements'])
            teams_df = pd.DataFrame(data['teams'])
            
            # Add team names to players
            team_map = teams_df.set_index('id')['name'].to_dict()
            players_df['team_name'] = players_df['team'].map(team_map)
            
            # Convert price
            players_df['now_cost'] = players_df['now_cost'] / 10
            
            # Save players
            players_df.to_csv(self.output_files['players'], index=False)
            print(f"✓ Saved {len(players_df)} players")
            
            # Save teams
            teams_df.to_csv(self.output_files['teams'], index=False)
            print(f"✓ Saved {len(teams_df)} teams")
            
            # Get fixtures
            response = requests.get(f"{self.fpl_base_url}fixtures/")
            response.raise_for_status()
            fixtures_df = pd.DataFrame(response.json())
            
            # Add team names to fixtures
            fixtures_df['home_team_name'] = fixtures_df['team_h'].map(team_map)
            fixtures_df['away_team_name'] = fixtures_df['team_a'].map(team_map)
            
            fixtures_df.to_csv(self.output_files['fixtures'], index=False)
            print(f"✓ Saved {len(fixtures_df)} fixtures")
            
            return True
            
        except Exception as e:
            print(f"✗ Could not fetch from FPL API: {e}")
            return False
    
    def download_historical_data(self):
        """Download data from historical repository"""
        print(f"\nDownloading historical data for {self.season_str} season...")
        
        success = True
        
        # Download players
        try:
            url = f"{self.historical_base}/{self.season_str}/players_raw.csv"
            players_df = pd.read_csv(url)
            players_df.to_csv(self.output_files['players'], index=False)
            print(f"✓ Saved {len(players_df)} players")
        except Exception as e:
            print(f"✗ Could not fetch players: {e}")
            success = False
        
        # Download teams
        try:
            url = f"{self.historical_base}/{self.season_str}/teams.csv"
            teams_df = pd.read_csv(url)
            teams_df.to_csv(self.output_files['teams'], index=False)
            print(f"✓ Saved {len(teams_df)} teams")
        except Exception as e:
            print(f"✗ Could not fetch teams: {e}")
            success = False
        
        # Download fixtures
        try:
            url = f"{self.historical_base}/{self.season_str}/fixtures.csv"
            fixtures_df = pd.read_csv(url)
            fixtures_df.to_csv(self.output_files['fixtures'], index=False)
            print(f"✓ Saved {len(fixtures_df)} fixtures")
        except Exception as e:
            print(f"✗ Could not fetch fixtures: {e}")
            success = False
        
        # Download player gameweek data
        print("\nDownloading player gameweek data...")
        all_gameweeks = []
        
        for gw in range(1, 39):
            try:
                url = f"{self.historical_base}/{self.season_str}/gws/gw{gw}.csv"
                gw_df = pd.read_csv(url)
                gw_df['GW'] = gw
                all_gameweeks.append(gw_df)
                print(f"  ✓ GW{gw}: {len(gw_df)} records", end='\r')
            except Exception as e:
                if gw == 1:  # If first GW fails, likely no data available
                    print(f"\n✗ No gameweek data available for {self.season_str}")
                    break
        
        if all_gameweeks:
            print()  # New line after progress
            
            # Combine all gameweeks
            combined_df = pd.concat(all_gameweeks, ignore_index=True)
            
            # Add price column (convert from value)
            if 'value' in combined_df.columns:
                combined_df['price'] = combined_df['value'] / 10
            
            # Save combined gameweek data
            combined_df.to_csv(self.output_files['player_gameweek'], index=False)
            print(f"✓ Saved {len(combined_df)} player-gameweek records ({len(all_gameweeks)} gameweeks)")
            
        return success
    
    def create_summary_report(self):
        """Create a summary report of downloaded data"""
        print("\n" + "="*60)
        print(f"FPL Data Download Summary for {self.season_year}/{self.season_year+1}")
        print("="*60)
        
        for file_type, file_path in self.output_files.items():
            if file_path.exists():
                size = file_path.stat().st_size / 1024 / 1024  # MB
                print(f"✓ {file_type.replace('_', ' ').title()}: {file_path.name} ({size:.1f} MB)")
                
                # Show sample stats
                if file_type == 'player_gameweek' and file_path.exists():
                    df = pd.read_csv(file_path)
                    if not df.empty:
                        print(f"  - Records: {len(df):,}")
                        if 'GW' in df.columns:
                            print(f"  - Gameweeks: {df['GW'].min()}-{df['GW'].max()}")
                        if 'total_points' in df.columns and 'name' in df.columns:
                            top_scorer = df.groupby('name')['total_points'].sum().idxmax()
                            top_points = df.groupby('name')['total_points'].sum().max()
                            print(f"  - Top scorer: {top_scorer} ({int(top_points)} pts)")
            else:
                print(f"✗ {file_type.replace('_', ' ').title()}: Not downloaded")
        
        print(f"\nAll files saved to: {self.data_dir}")
        
    def download_all(self):
        """Main download function"""
        print(f"FPL Data Downloader")
        print(f"Downloading data for {self.season_year}/{self.season_year+1} season")
        print("="*60)
        
        # Try current season API first
        current_season_success = False
        if self.season_year >= 2025:  # Adjust based on current year
            current_season_success = self.download_current_season_data()
        
        # If not current season or failed, try historical
        if not current_season_success:
            self.download_historical_data()
        
        # Create summary
        self.create_summary_report()


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/fpl_download.py [YEAR]")
        print("Example: python src/fpl_download.py 2024")
        print("\nAvailable seasons:")
        print("- 2016-2024: Historical data from GitHub repository")
        print("- 2025+: Current season from official FPL API")
        sys.exit(1)
    
    try:
        season_year = int(sys.argv[1])
        if season_year < 2016 or season_year > 2030:
            print("Error: Please provide a year between 2016 and 2030")
            sys.exit(1)
    except ValueError:
        print("Error: Please provide a valid year")
        sys.exit(1)
    
    downloader = FPLDownloader(season_year)
    downloader.download_all()


if __name__ == "__main__":
    main()