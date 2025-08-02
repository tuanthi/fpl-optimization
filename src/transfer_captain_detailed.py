#!/usr/bin/env python3
"""
Detailed Transfer and Captain Analysis

Shows exactly which transfers are being made and why
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from transfer_captain_optimizer import TransferOptimizer


def analyze_team_with_details(team_dict, predictions_file, start_gw=39, num_gw=5):
    """Analyze a single team with detailed transfer information"""
    
    # Calculate initial budget
    total_cost = 0
    for pos in ['GK', 'DEF', 'MID', 'FWD']:
        for i in range(1, 6):
            price_key = f'{pos}{i}_price'
            if price_key in team_dict:
                total_cost += team_dict[price_key]
    
    budget_remaining = 100.0 - total_cost
    
    optimizer = TransferOptimizer(predictions_file, budget_remaining)
    
    print(f"\nInitial Team (Budget: £{total_cost:.1f}m, Remaining: £{budget_remaining:.1f}m)")
    print("="*80)
    
    # Show initial starting XI
    print("\nStarting XI:")
    for pos in ['GK', 'DEF', 'MID', 'FWD']:
        for i in range(1, 6):
            player_key = f'{pos}{i}'
            if player_key in team_dict and team_dict.get(f'{player_key}_selected', 0) == 1:
                player = team_dict[player_key]
                score = team_dict.get(f'{player_key}_score', 0)
                price = team_dict.get(f'{player_key}_price', 0)
                print(f"  {player_key}: {player} - £{price:.1f}m (score: {score:.2f})")
    
    # Track transfers over gameweeks
    current_team = team_dict.copy()
    current_budget = budget_remaining
    
    for gw in range(start_gw, start_gw + num_gw):
        print(f"\n\nGAMEWEEK {gw}")
        print("-"*60)
        
        # Find best captain without transfers
        best_captain = None
        best_captain_score = 0
        
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for i in range(1, 6):
                player_key = f'{pos}{i}'
                if player_key in current_team and current_team.get(f'{player_key}_selected', 0) == 1:
                    player_id = current_team[player_key]
                    score = optimizer.get_player_score(player_id, gw)
                    if score > best_captain_score:
                        best_captain_score = score
                        best_captain = player_id
        
        print(f"Best captain (no transfers): {best_captain} ({best_captain_score:.2f} x 2 = {best_captain_score*2:.2f})")
        
        # Find best single transfer
        best_transfer = None
        best_transfer_improvement = 0
        best_new_captain = best_captain
        best_new_captain_score = best_captain_score
        
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for i in range(1, 6):
                player_key = f'{pos}{i}'
                if player_key in current_team and current_team.get(f'{player_key}_selected', 0) == 1:
                    current_player = current_team[player_key]
                    current_score = optimizer.get_player_score(current_player, gw)
                    
                    # Get valid transfers
                    valid_transfers = optimizer.get_valid_transfers(current_player, current_budget, current_team)
                    
                    for target_id, price_diff in valid_transfers[:5]:  # Top 5 options
                        target_score = optimizer.get_player_score(target_id, gw)
                        
                        # Calculate improvement including captain change
                        test_team = current_team.copy()
                        test_team[player_key] = target_id
                        
                        # Find best captain with this transfer
                        new_best_captain = None
                        new_best_score = 0
                        
                        for pos2 in ['GK', 'DEF', 'MID', 'FWD']:
                            for j in range(1, 6):
                                pk2 = f'{pos2}{j}'
                                if pk2 in test_team and test_team.get(f'{pk2}_selected', 0) == 1:
                                    pid = test_team[pk2]
                                    score = optimizer.get_player_score(pid, gw)
                                    if score > new_best_score:
                                        new_best_score = score
                                        new_best_captain = pid
                        
                        # Calculate total improvement
                        old_total = optimizer.calculate_team_score(current_team, best_captain, gw)
                        new_total = optimizer.calculate_team_score(test_team, new_best_captain, gw)
                        improvement = new_total - old_total
                        
                        if improvement > best_transfer_improvement:
                            best_transfer_improvement = improvement
                            best_transfer = (player_key, current_player, target_id, price_diff, 
                                           target_score - current_score)
                            best_new_captain = new_best_captain
                            best_new_captain_score = new_best_score
        
        # Make the transfer if beneficial
        if best_transfer and best_transfer_improvement > 0:
            player_key, out_player, in_player, price_diff, score_diff = best_transfer
            print(f"\nTransfer OUT: {out_player}")
            print(f"Transfer IN:  {in_player}")
            print(f"Price change: £{-price_diff:.1f}m")
            print(f"Score improvement: {score_diff:.2f} pts/week")
            
            # Update team
            current_team[player_key] = in_player
            current_budget -= price_diff
            
            # Update prices if available
            if in_player in optimizer.player_lookup:
                price_key = f'{player_key}_price'
                current_team[price_key] = optimizer.player_lookup[in_player]['price']
        else:
            print("\nNo beneficial transfer found - keeping current team")
        
        # Captain decision
        if best_new_captain != best_captain:
            print(f"\nCaptain change: {best_captain} -> {best_new_captain}")
        print(f"Final captain: {best_new_captain} ({best_new_captain_score:.2f} x 2 = {best_new_captain_score*2:.2f})")
        
        total_score = optimizer.calculate_team_score(current_team, best_new_captain, gw)
        print(f"\nGameweek {gw} total: {total_score:.2f} points")
        print(f"Remaining budget: £{current_budget:.1f}m")


def main():
    # Load top team
    teams_df = pd.read_csv("data/cached_merged_2024_2025_v2/top_200_teams_gw39.csv")
    predictions_file = "data/cached_merged_2024_2025_v2/predictions_gw39_proper.csv"
    
    # Analyze team 2 (best performer from previous run)
    print("DETAILED TRANSFER ANALYSIS - TEAM 2")
    print("="*80)
    
    team_dict = teams_df.iloc[1].to_dict()
    analyze_team_with_details(team_dict, predictions_file, start_gw=39, num_gw=3)


if __name__ == "__main__":
    main()