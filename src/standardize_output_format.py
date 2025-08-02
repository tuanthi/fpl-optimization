#!/usr/bin/env python3
"""
Standardize all output files to have consistent column ordering:
captain, formation, budget, gw1_score, 5gw_estimated, 
then GK1-GK2, DEF1-DEF5, MID1-MID5, FWD1-FWD3 with all associated columns
"""

import pandas as pd
import json
from pathlib import Path


def get_standard_column_order():
    """Define the standard column order for all output files"""
    # Key info columns
    key_cols = ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated']
    
    # Position columns with associated attributes
    position_cols = []
    
    # GK1-GK2
    for i in range(1, 3):
        position_cols.extend([
            f'GK{i}', f'GK{i}_role', f'GK{i}_selected', f'GK{i}_price', f'GK{i}_score'
        ])
    
    # DEF1-DEF5
    for i in range(1, 6):
        position_cols.extend([
            f'DEF{i}', f'DEF{i}_role', f'DEF{i}_selected', f'DEF{i}_price', f'DEF{i}_score'
        ])
    
    # MID1-MID5
    for i in range(1, 6):
        position_cols.extend([
            f'MID{i}', f'MID{i}_role', f'MID{i}_selected', f'MID{i}_price', f'MID{i}_score'
        ])
    
    # FWD1-FWD3
    for i in range(1, 4):
        position_cols.extend([
            f'FWD{i}', f'FWD{i}_role', f'FWD{i}_selected', f'FWD{i}_price', f'FWD{i}_score'
        ])
    
    return key_cols + position_cols


def reformat_csv_file(input_file, output_file=None):
    """Reformat a CSV file to standard column order"""
    if output_file is None:
        output_file = input_file
    
    df = pd.read_csv(input_file)
    standard_cols = get_standard_column_order()
    
    # Map BENCH1 (if GK) to GK2
    new_df = pd.DataFrame()
    
    # Copy key columns
    for col in ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated']:
        if col in df.columns:
            new_df[col] = df[col]
    
    # Process each row
    for idx, row in df.iterrows():
        # Find bench GK and move to GK2
        bench_gk = None
        for i in range(1, 5):
            if row.get(f'BENCH{i}_role') == 'GK':
                bench_gk = {
                    'name': row.get(f'BENCH{i}'),
                    'role': 'GK',
                    'selected': 0,
                    'price': row.get(f'BENCH{i}_price'),
                    'score': row.get(f'BENCH{i}_score')
                }
                break
        
        # Assign GK1 and GK2
        if 'GK1' in row:
            new_df.loc[idx, 'GK1'] = row['GK1']
            new_df.loc[idx, 'GK1_role'] = 'GK'
            new_df.loc[idx, 'GK1_selected'] = 1
            new_df.loc[idx, 'GK1_price'] = row.get('GK1_price')
            new_df.loc[idx, 'GK1_score'] = row.get('GK1_score')
        
        if bench_gk:
            new_df.loc[idx, 'GK2'] = bench_gk['name']
            new_df.loc[idx, 'GK2_role'] = 'GK'
            new_df.loc[idx, 'GK2_selected'] = 0
            new_df.loc[idx, 'GK2_price'] = bench_gk['price']
            new_df.loc[idx, 'GK2_score'] = bench_gk['score']
        
        # Copy other positions as-is
        for pos in ['DEF', 'MID', 'FWD']:
            if pos == 'DEF':
                max_num = 5
            elif pos == 'MID':
                max_num = 5
            else:  # FWD
                max_num = 3
                
            for i in range(1, max_num + 1):
                col_base = f'{pos}{i}'
                if col_base in row and pd.notna(row[col_base]):
                    new_df.loc[idx, col_base] = row[col_base]
                    new_df.loc[idx, f'{col_base}_role'] = pos
                    new_df.loc[idx, f'{col_base}_selected'] = row.get(f'{col_base}_selected', 1)
                    new_df.loc[idx, f'{col_base}_price'] = row.get(f'{col_base}_price')
                    new_df.loc[idx, f'{col_base}_score'] = row.get(f'{col_base}_score')
    
    # Add any additional columns at the end
    additional_cols = []
    for col in df.columns:
        if col not in standard_cols and col not in new_df.columns and not col.startswith('BENCH'):
            additional_cols.append(col)
    
    for col in additional_cols:
        new_df[col] = df[col]
    
    # Ensure all standard columns exist
    final_cols = standard_cols + additional_cols
    for col in standard_cols:
        if col not in new_df.columns:
            new_df[col] = None
    
    # Reorder columns
    new_df = new_df[final_cols]
    
    # Save
    new_df.to_csv(output_file, index=False)
    print(f"Reformatted: {output_file}")
    return new_df


def reformat_json_file(input_file, output_file=None):
    """Reformat JSON file to match standard order"""
    if output_file is None:
        output_file = input_file
        
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Process each team in selected_teams
    if 'selected_teams' in data:
        for team in data['selected_teams']:
            # Find bench GK
            bench_gk = None
            for i in range(1, 5):
                if team.get(f'BENCH{i}_role') == 'GK':
                    bench_gk = {
                        'name': team.get(f'BENCH{i}'),
                        'role': 'GK',
                        'selected': 0,
                        'price': team.get(f'BENCH{i}_price'),
                        'score': team.get(f'BENCH{i}_score')
                    }
                    break
            
            # Create new team dict with standard order
            new_team = {}
            
            # Key columns
            for col in ['captain', 'formation', 'budget', 'gw1_score', '5gw_estimated']:
                if col in team:
                    new_team[col] = team[col]
            
            # GK1
            if 'GK1' in team:
                new_team['GK1'] = team['GK1']
                new_team['GK1_role'] = 'GK'
                new_team['GK1_selected'] = 1
                new_team['GK1_price'] = team.get('GK1_price')
                new_team['GK1_score'] = team.get('GK1_score')
            
            # GK2 (from bench)
            if bench_gk:
                new_team['GK2'] = bench_gk['name']
                new_team['GK2_role'] = 'GK'
                new_team['GK2_selected'] = 0
                new_team['GK2_price'] = bench_gk['price']
                new_team['GK2_score'] = bench_gk['score']
            
            # Other positions
            for pos in ['DEF', 'MID', 'FWD']:
                if pos == 'DEF':
                    max_num = 5
                elif pos == 'MID':
                    max_num = 5
                else:  # FWD
                    max_num = 3
                    
                for i in range(1, max_num + 1):
                    col_base = f'{pos}{i}'
                    if col_base in team:
                        new_team[col_base] = team[col_base]
                        new_team[f'{col_base}_role'] = pos
                        new_team[f'{col_base}_selected'] = team.get(f'{col_base}_selected', 1)
                        new_team[f'{col_base}_price'] = team.get(f'{col_base}_price')
                        new_team[f'{col_base}_score'] = team.get(f'{col_base}_score')
            
            # Additional fields
            for key in ['selection_reason', 'risk_assessment', 'confidence']:
                if key in team:
                    new_team[key] = team[key]
            
            # Replace team with reformatted version
            team.clear()
            team.update(new_team)
    
    # Save
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Reformatted JSON: {output_file}")


def main():
    """Reformat all output files"""
    data_dir = Path("../data/cached_merged_2024_2025_v2")
    
    # List of files to reformat
    csv_files = [
        "top_200_teams_final_v5.csv",
        "top_200_teams_final_v6.csv",
        "final_selected_teams_v5.csv"
    ]
    
    json_files = [
        "final_selected_teams_v5.json"
    ]
    
    print("Reformatting all output files to standard column order...")
    print("Standard order: captain, formation, budget, gw1_score, 5gw_estimated,")
    print("                GK1-GK2, DEF1-DEF5, MID1-MID5, FWD1-FWD3 (with all associated columns)")
    print("-" * 80)
    
    # Process CSV files
    for filename in csv_files:
        filepath = data_dir / filename
        if filepath.exists():
            try:
                reformat_csv_file(filepath)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
        else:
            print(f"File not found: {filename}")
    
    # Process JSON files
    for filename in json_files:
        filepath = data_dir / filename
        if filepath.exists():
            try:
                reformat_json_file(filepath)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
        else:
            print(f"File not found: {filename}")
    
    print("\nAll files reformatted successfully!")
    
    # Verify the format by showing a sample
    sample_file = data_dir / "final_selected_teams_v5.csv"
    if sample_file.exists():
        df = pd.read_csv(sample_file)
        print("\nSample of reformatted columns:")
        print(list(df.columns[:20]))


if __name__ == "__main__":
    main()