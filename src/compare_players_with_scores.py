#!/usr/bin/env python3
"""
Compare Predicted vs Actual FPL Scores
Merges predicted team compositions with actual gameweek scores

Usage: python src/compare_players_with_scores.py [PREDICTED_CSV] [YEAR] [GAMEWEEK] [OUTPUT_CSV]
Example: python src/compare_players_with_scores.py data/2024/top_50_teams_with_scores.csv 2024 10 data/2024/comparison_week_10.csv
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import re


def extract_player_name_and_club(player_string):
    """Extract player name and club from 'First Last (Club)' format"""
    if pd.isna(player_string) or player_string == '':
        return None, None
    
    # Match pattern: "First Last (Club)"
    match = re.match(r'^(.+?)\s*\((.+?)\)$', player_string.strip())
    if match:
        full_name = match.group(1).strip()
        club = match.group(2).strip()
        return full_name, club
    return player_string.strip(), None


def load_actual_gameweek_scores(year, gameweek):
    """Load actual scores for a specific gameweek"""
    data_dir = Path("data") / f"{year}"
    
    # Load gameweek data
    gameweek_df = pd.read_csv(data_dir / f"{year}_player_gameweek.csv")
    
    # Filter to specific gameweek
    gw_data = gameweek_df[gameweek_df['GW'] == gameweek]
    
    # Load player metadata to get full names
    players_df = pd.read_csv(data_dir / f"{year}_players.csv")
    
    # Merge to get full names
    gw_data = gw_data.merge(
        players_df[['id', 'first_name', 'second_name', 'web_name']],
        left_on='element',
        right_on='id',
        how='left'
    )
    
    # Create full name - use second_name if available, otherwise web_name
    gw_data['full_name'] = gw_data.apply(
        lambda row: row['first_name'] + ' ' + (row['second_name'] if pd.notna(row['second_name']) and row['second_name'] != '' else row['web_name']),
        axis=1
    )
    
    # Create lookup dictionary: (full_name, team) -> score
    score_lookup = {}
    for _, row in gw_data.iterrows():
        key = (row['full_name'], row['team'])
        score_lookup[key] = int(row['total_points'])
    
    return score_lookup


def compare_predictions_with_actual(predicted_csv, year, gameweek, output_csv):
    """Compare predicted teams with actual gameweek scores"""
    
    # Load predicted teams
    predicted_df = pd.read_csv(predicted_csv)
    
    # Load actual scores
    print(f"Loading actual scores for gameweek {gameweek}...")
    actual_scores = load_actual_gameweek_scores(year, gameweek)
    
    print(f"Found {len(actual_scores)} players with actual scores")
    
    # Process each row
    comparison_data = []
    
    for idx, row in predicted_df.iterrows():
        new_row = {}
        total_predicted_11 = 0
        total_actual_11 = 0
        total_actual_15 = 0
        
        # Process each position
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            if pos == 'GK':
                count = 2
            elif pos == 'DEF':
                count = 5
            elif pos == 'MID':
                count = 5
            else:
                count = 3
            
            for i in range(1, count + 1):
                col_name = f'{pos}{i}'
                
                # Copy existing columns
                new_row[col_name] = row.get(col_name, '')
                new_row[f'{col_name}_selected'] = row.get(f'{col_name}_selected', 0)
                new_row[f'{col_name}_price'] = row.get(f'{col_name}_price', 0)
                new_row[f'{col_name}_score'] = row.get(f'{col_name}_score', 0)
                
                # Get actual score
                player_string = row.get(col_name, '')
                full_name, club = extract_player_name_and_club(player_string)
                
                actual_score = 0
                if full_name and club:
                    # Look up actual score
                    actual_score = actual_scores.get((full_name, club), 0)
                
                new_row[f'{col_name}_actual_score'] = actual_score
                
                # Add to totals
                total_actual_15 += actual_score
                
                if row.get(f'{col_name}_selected', 0) == 1:
                    total_predicted_11 += row.get(f'{col_name}_score', 0)
                    total_actual_11 += actual_score
        
        # Add totals
        new_row['11_selected_total_scores'] = row.get('11_selected_total_scores', 0)
        new_row['11_selected_total_actual_scores'] = total_actual_11
        new_row['15_total_price'] = row.get('15_total_price', 0)
        new_row['15_total_actual_scores'] = total_actual_15
        
        # Calculate differences
        new_row['11_score_difference'] = total_actual_11 - row.get('11_selected_total_scores', 0)
        new_row['prediction_accuracy'] = round(
            (total_actual_11 / row.get('11_selected_total_scores', 1)) * 100, 1
        ) if row.get('11_selected_total_scores', 0) > 0 else 0
        
        comparison_data.append(new_row)
    
    # Create DataFrame with proper column order
    columns = []
    for pos in ['GK', 'DEF', 'MID', 'FWD']:
        if pos == 'GK':
            count = 2
        elif pos == 'DEF':
            count = 5
        elif pos == 'MID':
            count = 5
        else:
            count = 3
        
        for i in range(1, count + 1):
            columns.extend([
                f'{pos}{i}',
                f'{pos}{i}_selected',
                f'{pos}{i}_price',
                f'{pos}{i}_score',
                f'{pos}{i}_actual_score'
            ])
    
    columns.extend([
        '11_selected_total_scores',
        '11_selected_total_actual_scores',
        '15_total_price',
        '15_total_actual_scores',
        '11_score_difference',
        'prediction_accuracy'
    ])
    
    comparison_df = pd.DataFrame(comparison_data, columns=columns)
    
    # Save to CSV
    comparison_df.to_csv(output_csv, index=False)
    print(f"\nSaved comparison to {output_csv}")
    
    # Print summary statistics
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)
    
    print(f"\nGameweek {gameweek} Prediction vs Actual:")
    print(f"Average predicted score (11 players): {comparison_df['11_selected_total_scores'].mean():.1f}")
    print(f"Average actual score (11 players): {comparison_df['11_selected_total_actual_scores'].mean():.1f}")
    print(f"Average difference: {comparison_df['11_score_difference'].mean():.1f}")
    print(f"Average prediction accuracy: {comparison_df['prediction_accuracy'].mean():.1f}%")
    
    # Show best and worst predictions
    print("\nTop 5 most accurate predictions:")
    best_predictions = comparison_df.nsmallest(5, '11_score_difference', keep='all')[
        ['11_selected_total_scores', '11_selected_total_actual_scores', '11_score_difference', 'prediction_accuracy']
    ]
    print(best_predictions.to_string(index=False))
    
    print("\nTop 5 least accurate predictions:")
    worst_predictions = comparison_df.nlargest(5, '11_score_difference', keep='all')[
        ['11_selected_total_scores', '11_selected_total_actual_scores', '11_score_difference', 'prediction_accuracy']
    ]
    print(worst_predictions.to_string(index=False))
    
    # Analyze by position
    print("\nPrediction accuracy by position:")
    for pos in ['GK', 'DEF', 'MID', 'FWD']:
        if pos == 'GK':
            count = 2
        elif pos == 'DEF':
            count = 5
        elif pos == 'MID':
            count = 5
        else:
            count = 3
        
        predicted_total = 0
        actual_total = 0
        selections = 0
        
        for _, row in comparison_df.iterrows():
            for i in range(1, count + 1):
                if row[f'{pos}{i}_selected'] == 1:
                    predicted_total += row[f'{pos}{i}_score']
                    actual_total += row[f'{pos}{i}_actual_score']
                    selections += 1
        
        if selections > 0:
            avg_predicted = predicted_total / selections
            avg_actual = actual_total / selections
            print(f"  {pos}: Predicted {avg_predicted:.2f}, Actual {avg_actual:.2f}, "
                  f"Diff {avg_actual - avg_predicted:.2f}")
    
    return comparison_df


def main():
    if len(sys.argv) < 5:
        print("Usage: python src/compare_players_with_scores.py [PREDICTED_CSV] [YEAR] [GAMEWEEK] [OUTPUT_CSV]")
        print("Example: python src/compare_players_with_scores.py data/2024/top_50_teams_with_scores.csv 2024 10 data/2024/comparison_week_10.csv")
        sys.exit(1)
    
    predicted_csv = sys.argv[1]
    year = int(sys.argv[2])
    gameweek = int(sys.argv[3])
    output_csv = sys.argv[4]
    
    # Check if files exist
    if not Path(predicted_csv).exists():
        print(f"Error: Predicted teams file {predicted_csv} not found")
        sys.exit(1)
    
    data_dir = Path("data") / f"{year}"
    if not data_dir.exists():
        print(f"Error: No data found for {year}")
        sys.exit(1)
    
    print(f"Comparing predictions with actual gameweek {gameweek} scores")
    
    # Run comparison
    comparison_df = compare_predictions_with_actual(predicted_csv, year, gameweek, output_csv)
    
    # Additional analysis - show best performing players we missed
    print("\n" + "="*60)
    print("NOTABLE PLAYERS ANALYSIS")
    print("="*60)
    
    # Load actual scores to find top performers
    actual_scores = load_actual_gameweek_scores(year, gameweek)
    top_actual = sorted(actual_scores.items(), key=lambda x: x[1], reverse=True)[:20]
    
    print(f"\nTop scorers in gameweek {gameweek} (for reference):")
    for (name, club), score in top_actual[:10]:
        print(f"  {name} ({club}): {score} pts")
    
    # Check how many top scorers were in our predicted teams
    predicted_players = set()
    for _, row in comparison_df.iterrows():
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            if pos == 'GK':
                count = 2
            elif pos == 'DEF':
                count = 5
            elif pos == 'MID':
                count = 5
            else:
                count = 3
            
            for i in range(1, count + 1):
                player_string = row[f'{pos}{i}']
                full_name, club = extract_player_name_and_club(player_string)
                if full_name and club:
                    predicted_players.add((full_name, club))
    
    top_10_in_predictions = sum(1 for p, _ in top_actual[:10] if p in predicted_players)
    print(f"\nTop 10 scorers included in predictions: {top_10_in_predictions}/10")
    
    print("\nTop scorers NOT in any predicted team:")
    missed_top_scorers = [(p, s) for p, s in top_actual[:20] if p not in predicted_players]
    for (name, club), score in missed_top_scorers[:5]:
        print(f"  {name} ({club}): {score} pts")


if __name__ == "__main__":
    main()