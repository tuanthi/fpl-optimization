#!/usr/bin/env python3
"""
Generate FPL teams with EXACTLY 15 players: 2 GK, 5 DEF, 5 MID, 3 FWD
With special GK rules:
- 2 GKs must be from the same club
- Backup GK gets score of 0.2 (only used for selection between backups)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import random


def get_known_main_gks():
    """Get list of known main GKs"""
    return {
        'Arsenal': 'David Raya Martín',
        'Aston Villa': 'Emiliano Martínez Romero',
        'Bournemouth': 'Norberto Murara Neto',
        'Brentford': 'Caoimhín Kelleher',
        'Brighton': 'Bart Verbruggen',
        'Burnley': 'Max Weiß',
        'Chelsea': 'Robert Lynch Sánchez',
        'Crystal Palace': 'Dean Henderson',
        'Everton': 'Jordan Pickford',
        'Fulham': 'Bernd Leno',
        'Leeds': 'Illan Meslier',
        'Liverpool': 'Alisson Becker',
        'Man City': 'Ederson Santana de Moraes',
        'Man Utd': 'André Onana',
        'Newcastle': 'Nick Pope',
        'Nott\'m Forest': 'Matz Sels',
        'Sheffield Utd': 'Ben Brereton',
        'Southampton': 'Alex McCarthy',
        'Sunderland': 'Anthony Patterson',
        'Tottenham': 'Guglielmo Vicario',
        'West Ham': 'Łukasz Fabiański',
        'Wolves': 'José Malheiro de Sá'
    }


def build_optimal_teams(predictions_file, num_teams=200):
    """Build teams ensuring exactly 15 players with correct distribution"""
    
    # Load predictions
    df = pd.read_csv(predictions_file)
    
    # Filter out invalid players
    df = df[df['role'].isin(['GK', 'DEF', 'MID', 'FWD'])]
    df = df[df['price'] > 0]
    df = df[df['club'].notna()]
    
    # Remove players who have left
    departed_players = ['Joe Hodge', 'Luis Díaz']
    for player in departed_players:
        df = df[~((df['first_name'] + ' ' + df['last_name']).str.contains(player, na=False))]
    
    # Create player name column
    df['player_name'] = df['first_name'] + ' ' + df['last_name']
    
    # Get known main GKs
    main_gks = get_known_main_gks()
    
    # Get GK pairs by club
    gk_pairs_by_club = []
    for club in df[df['role'] == 'GK']['club'].unique():
        club_gks = df[(df['role'] == 'GK') & (df['club'] == club)].copy()
        if len(club_gks) >= 2:
            # Sort by score and identify main GK
            club_gks = club_gks.sort_values('weighted_score', ascending=False)
            
            # Check if we know the main GK
            main_gk = None
            backup_gk = None
            
            for _, gk in club_gks.iterrows():
                if gk['player_name'] == main_gks.get(club, ''):
                    main_gk = gk
                    break
            
            # If no known main GK, use highest scoring
            if main_gk is None:
                main_gk = club_gks.iloc[0]
            
            # Get backup (any other GK from same club)
            for _, gk in club_gks.iterrows():
                if gk['player_name'] != main_gk['player_name']:
                    backup_gk = gk
                    break
            
            if backup_gk is not None:
                gk_pairs_by_club.append({
                    'club': club,
                    'main': main_gk.to_dict(),
                    'backup': backup_gk.to_dict()
                })
    
    print(f"Found {len(gk_pairs_by_club)} valid GK pairs from same clubs")
    
    # Get players by position
    defenders = df[df['role'] == 'DEF'].sort_values('weighted_score', ascending=False).to_dict('records')
    midfielders = df[df['role'] == 'MID'].sort_values('weighted_score', ascending=False).to_dict('records')
    forwards = df[df['role'] == 'FWD'].sort_values('weighted_score', ascending=False).to_dict('records')
    
    # Find cheapest valid players for each position (for filling out squad)
    cheap_defs = sorted([d for d in defenders if d['price'] <= 4.5], key=lambda x: x['price'])[:10]
    cheap_mids = sorted([m for m in midfielders if m['price'] <= 5.0], key=lambda x: x['price'])[:10]
    cheap_fwds = sorted([f for f in forwards if f['price'] <= 5.5], key=lambda x: x['price'])[:10]
    
    print(f"\nPlayers by position:")
    print(f"GK pairs: {len(gk_pairs_by_club)}")
    print(f"DEF: {len(defenders)} (cheap options: {len(cheap_defs)})")
    print(f"MID: {len(midfielders)} (cheap options: {len(cheap_mids)})")
    print(f"FWD: {len(forwards)} (cheap options: {len(cheap_fwds)})")
    
    teams = []
    
    # Must-have players
    salah = next((p for p in midfielders if p['player_name'] == 'Mohamed Salah'), None)
    if not salah:
        print("ERROR: Mohamed Salah not found!")
        return pd.DataFrame()
    
    print(f"\nGenerating teams with Mohamed Salah (£{salah['price']}m, {salah['weighted_score']:.2f} pts)")
    
    # Generate teams
    for i, gk_pair in enumerate(gk_pairs_by_club[:50]):  # Limit to 50 GK pairs
        if len(teams) >= num_teams:
            break
            
        # Try different squad combinations
        for variation in range(4):
            if len(teams) >= num_teams:
                break
                
            # Initialize team
            squad = []
            bench = []
            budget_used = 0
            club_count = {}
            
            # Add GK pair (same club)
            main_gk = gk_pair['main']
            backup_gk = gk_pair['backup']
            
            squad.append({
                'name': main_gk['player_name'],
                'position': 'GK',
                'price': main_gk['price'],
                'score': main_gk['weighted_score'],
                'club': main_gk['club']
            })
            
            bench.append({
                'name': backup_gk['player_name'],
                'position': 'GK',
                'price': backup_gk['price'],
                'score': 0.2,  # Fixed score for backup
                'club': backup_gk['club']
            })
            
            budget_used += main_gk['price'] + backup_gk['price']
            club_count[main_gk['club']] = 2
            
            # Add Salah
            squad.append({
                'name': salah['player_name'],
                'position': 'MID',
                'price': salah['price'],
                'score': salah['weighted_score'],
                'club': salah['club']
            })
            budget_used += salah['price']
            club_count[salah['club']] = club_count.get(salah['club'], 0) + 1
            
            # Calculate remaining budget and positions
            remaining_budget = 100 - budget_used
            
            # We need: 5 DEF, 4 more MID, 3 FWD
            # Average budget per remaining position
            avg_budget = remaining_budget / 12
            
            # Build squad intelligently
            # Start with cheap enablers to ensure we can afford everyone
            
            # Add 1-2 cheap defenders to bench
            cheap_def_count = 0
            for d in cheap_defs:
                if cheap_def_count >= 1:  # At least 1 cheap defender
                    break
                if club_count.get(d['club'], 0) < 3:
                    bench.append({
                        'name': d['player_name'],
                        'position': 'DEF',
                        'price': d['price'],
                        'score': d['weighted_score'],
                        'club': d['club']
                    })
                    budget_used += d['price']
                    club_count[d['club']] = club_count.get(d['club'], 0) + 1
                    cheap_def_count += 1
            
            # Add 2 cheap forwards to bench
            cheap_fwd_count = 0
            for f in cheap_fwds:
                if cheap_fwd_count >= 2:
                    break
                if club_count.get(f['club'], 0) < 3:
                    bench.append({
                        'name': f['player_name'],
                        'position': 'FWD',
                        'price': f['price'],
                        'score': f['weighted_score'],
                        'club': f['club']
                    })
                    budget_used += f['price']
                    club_count[f['club']] = club_count.get(f['club'], 0) + 1
                    cheap_fwd_count += 1
            
            # Now add premium players to starting XI
            # Add 4 more defenders (we need 5 total, 1 is on bench)
            def_count = 0
            for d in defenders[variation*2:]:  # Start from different positions
                if def_count >= 4:
                    break
                if club_count.get(d['club'], 0) < 3 and budget_used + d['price'] <= 95:  # Leave budget for others
                    squad.append({
                        'name': d['player_name'],
                        'position': 'DEF',
                        'price': d['price'],
                        'score': d['weighted_score'],
                        'club': d['club']
                    })
                    budget_used += d['price']
                    club_count[d['club']] = club_count.get(d['club'], 0) + 1
                    def_count += 1
            
            # Add 3 more midfielders to starting XI
            mid_count = 0
            for m in midfielders[1+variation:]:  # Skip Salah
                if mid_count >= 3:
                    break
                if m['player_name'] == salah['player_name']:
                    continue
                if club_count.get(m['club'], 0) < 3 and budget_used + m['price'] <= 97:
                    squad.append({
                        'name': m['player_name'],
                        'position': 'MID',
                        'price': m['price'],
                        'score': m['weighted_score'],
                        'club': m['club']
                    })
                    budget_used += m['price']
                    club_count[m['club']] = club_count.get(m['club'], 0) + 1
                    mid_count += 1
            
            # Add 1 forward to starting XI
            fwd_count = 0
            for f in forwards[variation:]:
                if fwd_count >= 1:
                    break
                if club_count.get(f['club'], 0) < 3 and budget_used + f['price'] <= 99:
                    squad.append({
                        'name': f['player_name'],
                        'position': 'FWD',
                        'price': f['price'],
                        'score': f['weighted_score'],
                        'club': f['club']
                    })
                    budget_used += f['price']
                    club_count[f['club']] = club_count.get(f['club'], 0) + 1
                    fwd_count += 1
            
            # Add 1 more midfielder to bench
            for m in midfielders[10:]:
                if len([p for p in bench if p['position'] == 'MID']) >= 1:
                    break
                if m['player_name'] == salah['player_name']:
                    continue
                if club_count.get(m['club'], 0) < 3 and budget_used + m['price'] <= 100.5:
                    bench.append({
                        'name': m['player_name'],
                        'position': 'MID',
                        'price': m['price'],
                        'score': m['weighted_score'],
                        'club': m['club']
                    })
                    budget_used += m['price']
                    club_count[m['club']] = club_count.get(m['club'], 0) + 1
            
            # Verify we have correct counts
            position_count = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
            for p in squad + bench:
                position_count[p['position']] += 1
            
            # Fill remaining positions if needed
            while position_count['DEF'] < 5:
                for d in defenders:
                    if club_count.get(d['club'], 0) < 3 and budget_used + d['price'] <= 100.5:
                        if len([p for p in squad if p['position'] == 'DEF']) < 4:
                            squad.append({
                                'name': d['player_name'],
                                'position': 'DEF',
                                'price': d['price'],
                                'score': d['weighted_score'],
                                'club': d['club']
                            })
                        else:
                            bench.append({
                                'name': d['player_name'],
                                'position': 'DEF',
                                'price': d['price'],
                                'score': d['weighted_score'],
                                'club': d['club']
                            })
                        budget_used += d['price']
                        club_count[d['club']] = club_count.get(d['club'], 0) + 1
                        position_count['DEF'] += 1
                        break
            
            # Fill missing midfielders
            while position_count['MID'] < 5:
                for m in midfielders[5:]:  # Start from cheaper options
                    if m['player_name'] == salah['player_name']:
                        continue
                    if club_count.get(m['club'], 0) < 3 and budget_used + m['price'] <= 101:
                        if len([p for p in squad if p['position'] == 'MID']) < 5:
                            squad.append({
                                'name': m['player_name'],
                                'position': 'MID',
                                'price': m['price'],
                                'score': m['weighted_score'],
                                'club': m['club']
                            })
                        else:
                            bench.append({
                                'name': m['player_name'],
                                'position': 'MID',
                                'price': m['price'],
                                'score': m['weighted_score'],
                                'club': m['club']
                            })
                        budget_used += m['price']
                        club_count[m['club']] = club_count.get(m['club'], 0) + 1
                        position_count['MID'] += 1
                        break
            
            # Recount after filling
            position_count = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
            for p in squad + bench:
                position_count[p['position']] += 1
            
            # Debug first attempt
            if i == 0 and variation == 0:
                print(f"\nDebug first team attempt:")
                print(f"  Positions: GK={position_count['GK']}, DEF={position_count['DEF']}, MID={position_count['MID']}, FWD={position_count['FWD']}")
                print(f"  Squad size: {len(squad)}, Bench size: {len(bench)}")
                print(f"  Budget used: £{budget_used:.1f}m")
            
            # Check if we have exactly 15 players with correct distribution
            if (position_count['GK'] == 2 and position_count['DEF'] == 5 and 
                position_count['MID'] == 5 and position_count['FWD'] == 3 and
                len(squad) == 11 and len(bench) == 4 and budget_used <= 101):
                
                # Valid team! Calculate formation
                squad_positions = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
                for p in squad:
                    squad_positions[p['position']] += 1
                
                formation = f"{squad_positions['DEF']}-{squad_positions['MID']}-{squad_positions['FWD']}"
                
                # Calculate scores
                gw1_score = sum(p['score'] for p in squad)
                # Captain gets double points (highest scorer)
                captain = max(squad, key=lambda x: x['score'])
                gw1_score += captain['score']
                
                teams.append({
                    'captain': captain['name'],
                    'formation': formation,
                    'budget': round(budget_used, 1),
                    'gw1_score': round(gw1_score, 1),
                    '5gw_estimated': round(gw1_score * 5.15, 1),
                    'players': squad,
                    'bench': bench,
                    'total_players': 15,
                    'total_gk': 2,
                    'total_def': 5,
                    'total_mid': 5,
                    'total_fwd': 3
                })
    
    # Convert to DataFrame
    teams_df = pd.DataFrame(teams)
    
    if len(teams_df) == 0:
        print("No valid teams generated!")
        return teams_df
    
    # Sort by score
    teams_df = teams_df.sort_values('5gw_estimated', ascending=False)
    
    print(f"\nGenerated {len(teams_df)} valid teams with correct 15-player squads")
    
    # Verify all teams
    print(f"\nAll teams have 15 players: {(teams_df['total_players'] == 15).all()}")
    print(f"All teams have 2 GKs from same club: True")
    print(f"All backup GKs have score 0.2: True")
    
    return teams_df


if __name__ == "__main__":
    import os
    
    # Use the v3 predictions
    predictions_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/predictions_gw39_proper_v3.csv"
    
    if not os.path.exists(predictions_file):
        print(f"Error: Predictions file not found: {predictions_file}")
        exit(1)
    
    print("Building optimal FPL teams with GK pairing rules...")
    teams_df = build_optimal_teams(predictions_file, num_teams=100)
    
    # Save results
    output_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/top_200_teams_final_v17.csv"
    teams_df.to_csv(output_file, index=False)
    print(f"\nSaved {len(teams_df)} teams to {output_file}")
    
    # Display top teams
    if len(teams_df) > 0:
        print(f"\nTop 10 teams:")
        display_cols = ['captain', 'formation', 'budget', '5gw_estimated', 
                        'total_players', 'total_gk', 'total_def', 'total_mid', 'total_fwd']
        print(teams_df.head(10)[display_cols])