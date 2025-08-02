#!/usr/bin/env python3
"""
Run optimization on merged 2024-2025 data
"""

import sys
import shutil
from pathlib import Path
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: python src/run_merged_optimization.py [GAMEWEEK]")
        sys.exit(1)
    
    gameweek = int(sys.argv[1])
    
    # Set up temporary directory structure for optimization
    temp_year = 9999
    temp_dir = Path("data") / str(temp_year)
    temp_dir.mkdir(exist_ok=True)
    
    # Copy necessary files from merged directory
    merged_dir = Path("data") / "merged_2024_2025"
    
    if not merged_dir.exists():
        print(f"Error: Merged data directory {merged_dir} not found")
        sys.exit(1)
    
    # Copy data files
    shutil.copy(merged_dir / "merged_players.csv", temp_dir / f"{temp_year}_players.csv")
    shutil.copy(merged_dir / "merged_player_gameweek.csv", temp_dir / f"{temp_year}_player_gameweek.csv")
    shutil.copy(merged_dir / "merged_teams.csv", temp_dir / f"{temp_year}_teams.csv")
    shutil.copy(merged_dir / "merged_fixtures.csv", temp_dir / f"{temp_year}_fixtures.csv")
    
    # Copy Bradley-Terry results
    if (merged_dir / "bradley_terry").exists():
        shutil.copytree(merged_dir / "bradley_terry", temp_dir / "bradley_terry", dirs_exist_ok=True)
    if (merged_dir / "team_bradley_terry").exists():
        shutil.copytree(merged_dir / "team_bradley_terry", temp_dir / "team_bradley_terry", dirs_exist_ok=True)
    
    print(f"Running optimization for gameweek {gameweek}...")
    
    # First run week sampling
    last_week = min(gameweek - 1, 38)  # Use available data up to week 38
    cmd1 = f"source .venv/bin/activate && python src/fpl_week_sampling.py {temp_year} 1 {last_week}"
    result1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
    
    if result1.returncode != 0:
        print(f"Week sampling failed: {result1.stderr}")
        sys.exit(1)
    
    print("✓ Week sampling completed")
    
    # Run optimization
    pred_file = temp_dir / f"pred_{temp_year}_week_sampling_1_to_{last_week}.csv"
    output_file = merged_dir / f"merged_top_50_teams_gameweek_{gameweek}.csv"
    
    cmd2 = f"source .venv/bin/activate && python src/fpl_optimization_runner.py {pred_file} {output_file}"
    result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
    
    if result2.returncode != 0:
        print(f"Optimization failed: {result2.stderr}")
        sys.exit(1)
    
    print(result2.stdout)
    
    if output_file.exists():
        print(f"\n✓ Top 50 teams saved to: {output_file}")
    else:
        print(f"\nWarning: Expected output file {output_file} not found")
    
    # Also copy comparison file if it exists
    comp_file = temp_dir / f"comparison_optimized_week_{gameweek}.csv"
    if comp_file.exists():
        shutil.copy(comp_file, merged_dir / f"merged_comparison_gameweek_{gameweek}.csv")
    
    # Clean up temp directory
    shutil.rmtree(temp_dir)
    
    print("\nOptimization complete!")

if __name__ == "__main__":
    main()