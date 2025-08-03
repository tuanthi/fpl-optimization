#!/usr/bin/env python3
"""
Remove Luis Díaz from all prediction and team files as he has left Liverpool
"""

import pandas as pd
import os
from pathlib import Path

def remove_luis_diaz_from_predictions():
    """Remove Luis Díaz from all prediction CSV files"""
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
            
            # Check if Luis Díaz exists (multiple variations of the name)
            luis_diaz_mask = (
                (df['first_name'] == 'Luis') & 
                (df['last_name'].str.contains('Díaz', na=False)) & 
                (df['club'] == 'Liverpool')
            ) | (
                (df['full_name'].str.contains('Luis Díaz', na=False)) & 
                (df['club'] == 'Liverpool')
            )
            
            if luis_diaz_mask.any():
                print(f"  Found Luis Díaz in {file_name}, removing...")
                df = df[~luis_diaz_mask]
                df.to_csv(file_path, index=False)
                print(f"  Removed Luis Díaz from {file_name}")
            else:
                print(f"  Luis Díaz not found in {file_name}")

def remove_luis_diaz_from_team_files():
    """Remove Luis Díaz from all team CSV files"""
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
                if 'Luis Díaz' in str(df[col].values):
                    print(f"  Found Luis Díaz in column '{col}', updating...")
                    # Replace Luis Díaz entries with empty values
                    df[col] = df[col].apply(lambda x: '' if 'Luis Díaz' in str(x) else x)
                    modified = True
            
            if modified:
                df.to_csv(file_path, index=False)
                print(f"  Updated {file_path.name}")

def update_player_mapping():
    """Remove Luis Díaz from player mapping file"""
    mapping_file = Path("../data/cached_merged_2024_2025_v2/player_mapping_gw39.csv")
    if mapping_file.exists():
        print("Processing player mapping...")
        df = pd.read_csv(mapping_file)
        
        # Remove Luis Díaz entries
        luis_diaz_mask = (
            df['player_2025'].str.contains('Luis Díaz', na=False) & 
            df['team_2025'].str.contains('Liverpool', na=False)
        )
        if luis_diaz_mask.any():
            print("  Found Luis Díaz in player mapping, removing...")
            df = df[~luis_diaz_mask]
            df.to_csv(mapping_file, index=False)
            print("  Removed Luis Díaz from player mapping")

def main():
    print("Removing Luis Díaz from all files (no longer at Liverpool)...")
    print("=" * 60)
    
    # Remove from predictions
    remove_luis_diaz_from_predictions()
    
    print("\n" + "=" * 60)
    
    # Remove from team files
    remove_luis_diaz_from_team_files()
    
    print("\n" + "=" * 60)
    
    # Remove from player mapping
    update_player_mapping()
    
    print("\nDone! Luis Díaz has been removed from all files.")

if __name__ == "__main__":
    main()