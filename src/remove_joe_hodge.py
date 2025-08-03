#!/usr/bin/env python3
"""
Remove Joe Hodge from all prediction and team files as he has transferred to CD Tondela
"""

import pandas as pd
import os
from pathlib import Path

def remove_joe_hodge_from_predictions():
    """Remove Joe Hodge from all prediction CSV files"""
    data_dir = Path("../data/cached_merged_2024_2025_v2")
    
    # List of prediction files to update
    prediction_files = [
        "predictions_gw39_proper.csv",
        "predictions_gw39_proper_v2.csv", 
        "predictions_gw39_proper_v3.csv",
        "predictions_gw39_proper_v4.csv"
    ]
    
    for file_name in prediction_files:
        file_path = data_dir / file_name
        if file_path.exists():
            print(f"Processing {file_name}...")
            df = pd.read_csv(file_path)
            
            # Check if Joe Hodge exists
            joe_hodge_mask = (df['first_name'] == 'Joe') & (df['last_name'] == 'Hodge')
            if joe_hodge_mask.any():
                print(f"  Found Joe Hodge in {file_name}, removing...")
                df = df[~joe_hodge_mask]
                df.to_csv(file_path, index=False)
                print(f"  Removed Joe Hodge from {file_name}")
            else:
                print(f"  Joe Hodge not found in {file_name}")

def remove_joe_hodge_from_team_files():
    """Remove Joe Hodge from all team CSV files"""
    data_dir = Path("../data/cached_merged_2024_2025_v2")
    
    # Pattern for team files
    team_files = list(data_dir.glob("*teams*.csv"))
    team_files.extend(list(data_dir.glob("*selected*.csv")))
    
    for file_path in team_files:
        if file_path.exists():
            print(f"Processing {file_path.name}...")
            df = pd.read_csv(file_path)
            
            # Check all columns that might contain player names
            modified = False
            for col in df.columns:
                if 'Joe Hodge' in str(df[col].values):
                    print(f"  Found Joe Hodge in column '{col}', updating...")
                    # Replace Joe Hodge entries with empty values
                    df[col] = df[col].apply(lambda x: '' if 'Joe Hodge' in str(x) else x)
                    modified = True
            
            if modified:
                df.to_csv(file_path, index=False)
                print(f"  Updated {file_path.name}")

def update_player_mapping():
    """Remove Joe Hodge from player mapping file"""
    mapping_file = Path("../data/cached_merged_2024_2025_v2/player_mapping_gw39.csv")
    if mapping_file.exists():
        print("Processing player mapping...")
        df = pd.read_csv(mapping_file)
        
        # Remove Joe Hodge entries
        joe_hodge_mask = df['player_2025'].str.contains('Joe Hodge', na=False)
        if joe_hodge_mask.any():
            print("  Found Joe Hodge in player mapping, removing...")
            df = df[~joe_hodge_mask]
            df.to_csv(mapping_file, index=False)
            print("  Removed Joe Hodge from player mapping")

def main():
    print("Removing Joe Hodge from all files (transferred to CD Tondela)...")
    print("=" * 60)
    
    # Remove from predictions
    remove_joe_hodge_from_predictions()
    
    print("\n" + "=" * 60)
    
    # Remove from team files
    remove_joe_hodge_from_team_files()
    
    print("\n" + "=" * 60)
    
    # Remove from player mapping
    update_player_mapping()
    
    print("\nDone! Joe Hodge has been removed from all files.")

if __name__ == "__main__":
    main()