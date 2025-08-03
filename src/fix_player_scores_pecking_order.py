#!/usr/bin/env python3
"""
Fix player scores based on pecking order and historical playing time.
Players with no history and low pecking order should get minimal scores.
"""

import pandas as pd
import numpy as np
from pathlib import Path


def load_historical_minutes():
    """Load historical playing time data"""
    player_gw_file = "/Users/huetuanthi/dev/dokeai/fpl/data/2024/2024_player_gameweek.csv"
    if not Path(player_gw_file).exists():
        print("Warning: No historical minutes data available")
        return {}
    
    gw_df = pd.read_csv(player_gw_file)
    
    # Calculate total minutes per player
    minutes_df = gw_df.groupby(['name', 'team'])['minutes'].sum().reset_index()
    minutes_df.columns = ['player_name', 'team', 'total_minutes']
    
    # Create lookup dictionary
    minutes_dict = {}
    for _, row in minutes_df.iterrows():
        minutes_dict[row['player_name']] = row['total_minutes']
    
    return minutes_dict


def get_team_pecking_order(predictions_df):
    """Determine pecking order within each team and position"""
    pecking_order = {}
    
    # Group by team and role
    for (club, role), group in predictions_df.groupby(['club', 'role']):
        # Sort by price (descending) as proxy for pecking order
        sorted_players = group.sort_values('price', ascending=False)
        
        # Assign pecking order rank
        for rank, (idx, player) in enumerate(sorted_players.iterrows(), 1):
            player_name = f"{player['first_name']} {player['last_name']}"
            key = (club, role)
            if key not in pecking_order:
                pecking_order[key] = {}
            pecking_order[key][player_name] = rank
    
    return pecking_order


def adjust_scores_by_pecking_order(predictions_df, minutes_dict):
    """Adjust player scores based on pecking order and playing time"""
    
    # Get pecking order
    pecking_order = get_team_pecking_order(predictions_df)
    
    # Known players with no real playing time potential
    # These should get minimal scores regardless of calculation
    no_play_players = [
        'Dário Luís Essugo',  # Chelsea youth player
        'Tyrique George',      # Chelsea youth player
        'Santos',              # Minimal minutes
        # Add more as identified
    ]
    
    adjusted_scores = []
    adjustments_made = []
    
    for idx, player in predictions_df.iterrows():
        player_name = f"{player['first_name']} {player['last_name']}"
        player_club = player['club']
        player_role = player['role']
        original_score = player['weighted_score']
        
        # Get player's pecking order rank
        pecking_rank = pecking_order.get((player_club, player_role), {}).get(player_name, 99)
        
        # Get historical minutes
        historical_minutes = minutes_dict.get(player_name, 0)
        
        # Determine if player needs adjustment
        needs_adjustment = False
        adjustment_factor = 1.0
        reason = ""
        
        # Case 1: Known no-play players
        if any(no_play in player_name for no_play in no_play_players):
            needs_adjustment = True
            adjustment_factor = 0.01  # Near zero score
            reason = "known no-play player"
        
        # Case 2: No historical minutes and low pecking order
        elif historical_minutes == 0:
            if player_role == 'GK' and pecking_rank >= 3:
                # 3rd choice GK or lower
                needs_adjustment = True
                adjustment_factor = 0.05
                reason = f"3rd+ choice GK with no history"
            elif player_role in ['DEF', 'MID', 'FWD']:
                if pecking_rank >= 6 and player['price'] <= 5.0:
                    # Low price, low pecking order, no history
                    needs_adjustment = True
                    adjustment_factor = 0.1
                    reason = f"low pecking order ({pecking_rank}) with no history"
                elif pecking_rank >= 8:
                    # Very low pecking order
                    needs_adjustment = True
                    adjustment_factor = 0.05
                    reason = f"very low pecking order ({pecking_rank})"
        
        # Case 3: Very low historical minutes
        elif historical_minutes < 200:  # Less than ~2 full games
            if pecking_rank >= 5:
                needs_adjustment = True
                adjustment_factor = 0.2
                reason = f"minimal minutes ({historical_minutes}) and low pecking order"
        
        # Case 4: Price-based adjustment for unknowns
        if not needs_adjustment and historical_minutes == 0:
            if player['price'] == 4.5:  # Minimum price
                # Compare to other minimum price players in same role/team
                same_team_role = predictions_df[
                    (predictions_df['club'] == player_club) & 
                    (predictions_df['role'] == player_role)
                ]
                
                if len(same_team_role) > 3:
                    # If 4+ players in same position, minimum price = likely no play
                    avg_price = same_team_role['price'].mean()
                    if player['price'] < avg_price - 1.0:
                        needs_adjustment = True
                        adjustment_factor = 0.15
                        reason = "minimum price in crowded position"
        
        # Apply adjustment
        if needs_adjustment:
            adjusted_score = original_score * adjustment_factor
            
            # Ensure minimum scores by position
            min_scores = {
                'GK': 0.5,
                'DEF': 0.5,
                'MID': 0.5,
                'FWD': 0.5
            }
            
            adjusted_score = max(adjusted_score, min_scores.get(player_role, 0.5))
            
            adjustments_made.append({
                'player': player_name,
                'club': player_club,
                'role': player_role,
                'price': player['price'],
                'pecking_order': pecking_rank,
                'historical_minutes': historical_minutes,
                'original_score': original_score,
                'adjusted_score': adjusted_score,
                'adjustment_factor': adjustment_factor,
                'reason': reason
            })
        else:
            adjusted_score = original_score
        
        adjusted_scores.append(adjusted_score)
    
    return adjusted_scores, adjustments_made


def main():
    """Fix player scores in predictions"""
    
    # Load predictions
    print("Loading predictions...")
    predictions_file = "../data/cached_merged_2024_2025_v2/predictions_gw39_proper_v2.csv"
    predictions_df = pd.read_csv(predictions_file)
    
    # Load historical minutes
    print("Loading historical playing time data...")
    minutes_dict = load_historical_minutes()
    print(f"Loaded minutes data for {len(minutes_dict)} players")
    
    # Adjust scores
    print("\nAdjusting scores based on pecking order...")
    adjusted_scores, adjustments_made = adjust_scores_by_pecking_order(predictions_df, minutes_dict)
    
    # Update predictions
    predictions_df['original_weighted_score'] = predictions_df['weighted_score']
    predictions_df['weighted_score'] = adjusted_scores
    
    # Save updated predictions
    output_file = "../data/cached_merged_2024_2025_v2/predictions_gw39_proper_v3.csv"
    predictions_df.to_csv(output_file, index=False)
    
    print(f"\nSaved updated predictions to {output_file}")
    
    # Report adjustments
    if adjustments_made:
        print(f"\nMade {len(adjustments_made)} score adjustments:")
        
        # Sort by adjustment size
        adjustments_df = pd.DataFrame(adjustments_made)
        adjustments_df['score_change'] = adjustments_df['original_score'] - adjustments_df['adjusted_score']
        adjustments_df = adjustments_df.sort_values('score_change', ascending=False)
        
        print("\nTop 20 adjusted players:")
        print("-" * 120)
        print(f"{'Player':<30} {'Club':<15} {'Role':<5} {'Price':<6} {'Rank':<5} {'Mins':<6} "
              f"{'Original':<8} {'Adjusted':<8} {'Reason':<30}")
        print("-" * 120)
        
        for _, adj in adjustments_df.head(20).iterrows():
            print(f"{adj['player']:<30} {adj['club']:<15} {adj['role']:<5} "
                  f"£{adj['price']:<5.1f} {adj['pecking_order']:<5} {adj['historical_minutes']:<6} "
                  f"{adj['original_score']:<8.2f} {adj['adjusted_score']:<8.2f} {adj['reason']:<30}")
    
    # Check specific players
    print("\n\nChecking specific players:")
    check_players = ['Dário Luís Essugo', 'Tyrique George', 'Santos']
    
    for check_name in check_players:
        matches = predictions_df[predictions_df['first_name'].str.contains(check_name.split()[0], na=False) | 
                                predictions_df['last_name'].str.contains(check_name.split()[-1], na=False)]
        
        if not matches.empty:
            for _, player in matches.iterrows():
                full_name = f"{player['first_name']} {player['last_name']}"
                print(f"\n{full_name} ({player['club']}):")
                print(f"  Price: £{player['price']}m")
                print(f"  Original score: {player['original_weighted_score']:.3f}")
                print(f"  Adjusted score: {player['weighted_score']:.3f}")


if __name__ == "__main__":
    main()