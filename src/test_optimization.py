#!/usr/bin/env python3
"""Test optimization with debug output"""

import pandas as pd
from pathlib import Path

# Load the prediction data
pred_file = Path("data/9999/pred_9999_week_sampling_1_to_38.csv")
if pred_file.exists():
    df = pd.read_csv(pred_file)
    print(f"Loaded {len(df)} rows")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Unique players: {df[['first_name', 'last_name']].drop_duplicates().shape[0]}")
    print(f"Gameweeks: {df['gameweek'].min()} to {df['gameweek'].max()}")
    print(f"Sample data:")
    print(df.head())
    
    # Check for any issues
    print(f"\nNull values:")
    print(df.isnull().sum())
    
    print(f"\nRole distribution:")
    print(df['role'].value_counts())
else:
    print(f"File not found: {pred_file}")