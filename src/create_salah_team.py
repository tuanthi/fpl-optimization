#!/usr/bin/env python3
"""
Create an optimal team with Mohamed Salah for transfer demonstration
"""

import pandas as pd
from pathlib import Path


def create_salah_team():
    """Create a balanced team including Mohamed Salah"""
    
    # Load predictions
    predictions = pd.read_csv("data/cached_merged_2024_2025_v2/predictions_gw39_proper.csv")
    
    # Sort by weighted score
    predictions = predictions.sort_values('weighted_score', ascending=False)
    
    # Build team with Salah
    team = {}
    total_cost = 0
    team_counts = {}
    
    # Must have Mohamed Salah
    salah = predictions[predictions['full_name'] == 'Mohamed Salah'].iloc[0]
    team['MID1'] = f"{salah['full_name']} ({salah['club']})"
    team['MID1_selected'] = 1
    team['MID1_price'] = salah['price']
    team['MID1_score'] = salah['weighted_score']
    total_cost += salah['price']
    team_counts[salah['club']] = team_counts.get(salah['club'], 0) + 1
    
    # Add top GK
    gks = predictions[predictions['role'] == 'GK']
    for _, gk in gks.iterrows():
        if team_counts.get(gk['club'], 0) < 3 and total_cost + gk['price'] <= 85:
            team['GK1'] = f"{gk['full_name']} ({gk['club']})"
            team['GK1_selected'] = 1
            team['GK1_price'] = gk['price']
            team['GK1_score'] = gk['weighted_score']
            total_cost += gk['price']
            team_counts[gk['club']] = team_counts.get(gk['club'], 0) + 1
            break
    
    # Add cheap backup GK
    cheap_gks = gks[gks['price'] <= 4.5].sort_values('price')
    for _, gk in cheap_gks.iterrows():
        if team_counts.get(gk['club'], 0) < 3:
            team['GK2'] = f"{gk['full_name']} ({gk['club']})"
            team['GK2_selected'] = 0
            team['GK2_price'] = gk['price']
            team['GK2_score'] = gk['weighted_score']
            total_cost += gk['price']
            team_counts[gk['club']] = team_counts.get(gk['club'], 0) + 1
            break
    
    # Add 4 DEF (3-4 starting)
    defs = predictions[predictions['role'] == 'DEF'].head(30)
    def_count = 0
    for _, df in defs.iterrows():
        if team_counts.get(df['club'], 0) < 3 and total_cost + df['price'] <= 75:
            def_count += 1
            team[f'DEF{def_count}'] = f"{df['full_name']} ({df['club']})"
            team[f'DEF{def_count}_selected'] = 1 if def_count <= 3 else 0
            team[f'DEF{def_count}_price'] = df['price']
            team[f'DEF{def_count}_score'] = df['weighted_score']
            total_cost += df['price']
            team_counts[df['club']] = team_counts.get(df['club'], 0) + 1
            if def_count == 5:
                break
    
    # Add 4 more MID (including Salah we have 5)
    mids = predictions[predictions['role'] == 'MID'].head(30)
    mid_count = 1  # Already have Salah
    for _, mid in mids.iterrows():
        if mid['full_name'] == 'Mohamed Salah':
            continue
        if team_counts.get(mid['club'], 0) < 3 and total_cost + mid['price'] <= 85:
            mid_count += 1
            team[f'MID{mid_count}'] = f"{mid['full_name']} ({mid['club']})"
            team[f'MID{mid_count}_selected'] = 1 if mid_count <= 4 else 0
            team[f'MID{mid_count}_price'] = mid['price']
            team[f'MID{mid_count}_score'] = mid['weighted_score']
            total_cost += mid['price']
            team_counts[mid['club']] = team_counts.get(mid['club'], 0) + 1
            if mid_count == 5:
                break
    
    # Add 3 FWD (2 starting)
    fwds = predictions[predictions['role'] == 'FWD'].head(20)
    fwd_count = 0
    for _, fwd in fwds.iterrows():
        if team_counts.get(fwd['club'], 0) < 3 and total_cost + fwd['price'] <= 95:
            fwd_count += 1
            team[f'FWD{fwd_count}'] = f"{fwd['full_name']} ({fwd['club']})"
            team[f'FWD{fwd_count}_selected'] = 1 if fwd_count <= 2 else 0
            team[f'FWD{fwd_count}_price'] = fwd['price']
            team[f'FWD{fwd_count}_score'] = fwd['weighted_score']
            total_cost += fwd['price']
            team_counts[fwd['club']] = team_counts.get(fwd['club'], 0) + 1
            if fwd_count == 3:
                break
    
    # Fill remaining spots with cheap players
    while total_cost > 100:
        # Replace expensive bench players with cheaper ones
        for pos in ['DEF', 'MID', 'FWD']:
            if pos == 'DEF':
                start, end = 4, 5
            elif pos == 'MID':
                start, end = 5, 5
            else:
                start, end = 3, 3
            
            for i in range(start, end + 1):
                key = f'{pos}{i}'
                if key in team and team.get(f'{key}_selected', 0) == 0:
                    # Find cheaper replacement
                    role_players = predictions[predictions['role'] == pos[0:3] if pos != 'FWD' else 'FWD']
                    cheap_players = role_players[role_players['price'] <= 4.5].sort_values('price')
                    
                    for _, player in cheap_players.iterrows():
                        player_id = f"{player['full_name']} ({player['club']})"
                        if player_id not in [team[k] for k in team if k.endswith(str(j)) for j in range(1, 6)]:
                            old_price = team[f'{key}_price']
                            team[key] = player_id
                            team[f'{key}_price'] = player['price']
                            team[f'{key}_score'] = player['weighted_score']
                            total_cost = total_cost - old_price + player['price']
                            break
    
    # Calculate total score
    total_score = 0
    for pos in ['GK', 'DEF', 'MID', 'FWD']:
        for i in range(1, 6):
            if team.get(f'{pos}{i}_selected', 0) == 1:
                total_score += team.get(f'{pos}{i}_score', 0)
    
    team['11_selected_total_scores'] = round(total_score, 2)
    team['15_total_price'] = round(total_cost, 1)
    
    print("Created team with Mohamed Salah:")
    print(f"Total cost: £{total_cost:.1f}m")
    print(f"Starting XI score: {total_score:.2f}")
    print("\nStarting XI:")
    for pos in ['GK', 'DEF', 'MID', 'FWD']:
        for i in range(1, 6):
            if team.get(f'{pos}{i}_selected', 0) == 1:
                print(f"  {pos}{i}: {team[f'{pos}{i}']} - £{team[f'{pos}{i}_price']:.1f}m ({team[f'{pos}{i}_score']:.2f})")
    
    return team


def main():
    team = create_salah_team()
    
    # Run transfer analysis
    from transfer_captain_detailed import analyze_team_with_details
    
    print("\n\nTRANSFER ANALYSIS FOR SALAH TEAM")
    print("="*80)
    
    analyze_team_with_details(team, "data/cached_merged_2024_2025_v2/predictions_gw39_proper.csv", 
                             start_gw=39, num_gw=5)


if __name__ == "__main__":
    main()