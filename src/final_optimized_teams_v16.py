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


def load_player_minutes():
    """Load player minutes data from 2024 season"""
    player_gw_file = "/Users/huetuanthi/dev/dokeai/fpl/data/2024/2024_player_gameweek.csv"
    if not Path(player_gw_file).exists():
        print("Warning: No minutes data available")
        return {}
    
    gw_df = pd.read_csv(player_gw_file)
    
    # Calculate total minutes per player
    minutes_df = gw_df.groupby(['name', 'team'])['minutes'].sum().reset_index()
    minutes_df.columns = ['player_name', 'team', 'total_minutes']
    
    # Create a dictionary for lookup
    minutes_dict = {}
    for _, row in minutes_df.iterrows():
        minutes_dict[row['player_name']] = row['total_minutes']
    
    return minutes_dict


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
    
    # Load minutes data
    print("Loading player minutes data...")
    minutes_dict = load_player_minutes()
    
    # Get known main GKs
    main_gks = get_known_main_gks()
    
    # Identify main GKs with special handling
    for club, main_gk_name in main_gks.items():
        club_gks = df[(df['role'] == 'GK') & (df['club'] == club)].copy()
        for idx, gk in club_gks.iterrows():
            if gk['player_name'] == main_gk_name:
                df.loc[idx, 'is_main_gk'] = True
            else:
                df.loc[idx, 'is_main_gk'] = False
    
    # For clubs not in the list, use minutes played
    unlisted_clubs = df[df['role'] == 'GK']['club'].unique()
    for club in unlisted_clubs:
        if club not in main_gks:
            club_gks = df[(df['role'] == 'GK') & (df['club'] == club)].copy()
            club_gks['minutes'] = club_gks['player_name'].map(lambda x: minutes_dict.get(x, 0))
            if len(club_gks) > 0:
                main_gk_idx = club_gks['minutes'].idxmax()
                for idx in club_gks.index:
                    df.loc[idx, 'is_main_gk'] = (idx == main_gk_idx)
    
    # Fill missing is_main_gk values
    df['is_main_gk'] = df['is_main_gk'].fillna(False)
    
    # Get GKs by club for pairing
    gk_pairs_by_club = {}
    for club in df[df['role'] == 'GK']['club'].unique():
        club_gks = df[(df['role'] == 'GK') & (df['club'] == club)].copy()
        if len(club_gks) >= 2:
            # Sort by is_main_gk (True first) then by score
            club_gks = club_gks.sort_values(['is_main_gk', 'weighted_score'], ascending=[False, False])
            gk_pairs_by_club[club] = club_gks.head(2).to_dict('records')
    
    # Set up scoring for backup GKs
    df['team_score'] = df['weighted_score'].copy()
    
    # Count players before filtering
    gk_count = len(df[df['role'] == 'GK'])
    main_gk_count = len(df[(df['role'] == 'GK') & (df['is_main_gk'] == True)])
    print(f"\nSkipped {len(df[df['club'].isna()])} invalid players")
    print(f"Found {len(gk_pairs_by_club)} clubs with 2+ GKs")
    
    # Get players by position (excluding GKs initially)
    defenders = df[df['role'] == 'DEF'].sort_values('weighted_score', ascending=False).to_dict('records')
    midfielders = df[df['role'] == 'MID'].sort_values('weighted_score', ascending=False).to_dict('records')
    forwards = df[df['role'] == 'FWD'].sort_values('weighted_score', ascending=False).to_dict('records')
    
    print(f"\nPlayers by position (validated):")
    print(f"GK: {main_gk_count} main GKs, {gk_count} total")
    print(f"DEF: {len(defenders)}")
    print(f"MID: {len(midfielders)}")
    print(f"FWD: {len(forwards)}")
    
    # Show top players by position
    print("\nTop players by position:\n")
    for pos, players in [('MID', midfielders), ('FWD', forwards)]:
        print(f"{pos}:")
        for i, p in enumerate(players[:5]):
            print(f"  {i+1}. {p['player_name']} ({p['club']}): {p['weighted_score']:.2f} - £{p['price']}m")
        print()
    
    teams = []
    
    # Must-have players
    must_have = ['Mohamed Salah']
    print(f"Generating teams with must-have players: {must_have}")
    
    # Generate teams
    team_id = 0
    
    # Try different GK pair combinations
    for club, gk_pair in list(gk_pairs_by_club.items())[:10]:  # Limit to first 10 clubs for testing
        if team_id >= num_teams:
            break
            
        # For each GK pair, generate multiple team variations
        for variation in range(10):
            if team_id >= num_teams:
                break
                
            team = {
                'players': [],
                'bench': [],
                'budget': 0,
                'score': 0,
                'positions': {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
            }
            
            # Add the GK pair from same club
            main_gk = gk_pair[0]
            backup_gk = gk_pair[1]
            
            # Add main GK to starting XI
            team['players'].append({
                'name': main_gk['player_name'],
                'position': 'GK',
                'price': main_gk['price'],
                'score': main_gk['weighted_score'],
                'club': main_gk['club']
            })
            
            # Add backup GK to bench
            team['bench'].append({
                'name': backup_gk['player_name'],
                'position': 'GK',
                'price': backup_gk['price'],
                'score': 0.2,  # Fixed score for backup GK
                'club': backup_gk['club']
            })
            
            team['budget'] += main_gk['price'] + backup_gk['price']
            team['score'] += main_gk['weighted_score'] + 0.2  # Use 0.2 for team score
            team['positions']['GK'] = 2
            
            # Track clubs
            club_count = {main_gk['club']: 2}  # Both GKs from same club
            
            # Add must-have players
            for player_name in must_have:
                player = next((p for p in midfielders if p['player_name'] == player_name), None)
                if player and club_count.get(player['club'], 0) < 3:
                    team['players'].append({
                        'name': player['player_name'],
                        'position': player['role'],
                        'price': player['price'],
                        'score': player['weighted_score'],
                        'club': player['club']
                    })
                    team['budget'] += player['price']
                    team['score'] += player['weighted_score']
                    team['positions']['MID'] += 1
                    club_count[player['club']] = club_count.get(player['club'], 0) + 1
            
            # Fill remaining positions
            # Need: 5 DEF, 5 MID (including must-haves), 3 FWD
            # Starting XI: 1 GK, 3-5 DEF, 2-5 MID, 1-3 FWD
            
            # Add defenders (need 5 total)
            def_added = 0
            for defender in defenders:
                if def_added >= 5:
                    break
                if club_count.get(defender['club'], 0) < 3 and team['budget'] + defender['price'] <= 100.5:
                    if def_added < 4:  # First 4 defenders go to starting XI
                        team['players'].append({
                            'name': defender['player_name'],
                            'position': 'DEF',
                            'price': defender['price'],
                            'score': defender['weighted_score'],
                            'club': defender['club']
                        })
                    else:  # 5th defender to bench
                        team['bench'].append({
                            'name': defender['player_name'],
                            'position': 'DEF',
                            'price': defender['price'],
                            'score': defender['weighted_score'],
                            'club': defender['club']
                        })
                    team['budget'] += defender['price']
                    team['score'] += defender['weighted_score']
                    team['positions']['DEF'] += 1
                    club_count[defender['club']] = club_count.get(defender['club'], 0) + 1
                    def_added += 1
            
            # Add midfielders (need 5 total, including must-haves)
            mid_added = team['positions']['MID']
            mid_idx = variation * 2  # Vary midfielder selection
            for i, midfielder in enumerate(midfielders[mid_idx:] + midfielders[:mid_idx]):
                if mid_added >= 5:
                    break
                if midfielder['player_name'] in must_have:
                    continue
                if club_count.get(midfielder['club'], 0) < 3 and team['budget'] + midfielder['price'] <= 100:
                    if mid_added < 4:  # First 4 mids go to starting XI
                        team['players'].append({
                            'name': midfielder['player_name'],
                            'position': 'MID',
                            'price': midfielder['price'],
                            'score': midfielder['weighted_score'],
                            'club': midfielder['club']
                        })
                    else:  # 5th mid to bench
                        team['bench'].append({
                            'name': midfielder['player_name'],
                            'position': 'MID',
                            'price': midfielder['price'],
                            'score': midfielder['weighted_score'],
                            'club': midfielder['club']
                        })
                    team['budget'] += midfielder['price']
                    team['score'] += midfielder['weighted_score']
                    team['positions']['MID'] += 1
                    club_count[midfielder['club']] = club_count.get(midfielder['club'], 0) + 1
                    mid_added += 1
            
            # Add forwards (need 3 total)
            fwd_added = 0
            fwd_idx = variation  # Vary forward selection
            remaining_budget = 100 - team['budget']
            remaining_fwds = 3
            
            for i, forward in enumerate(forwards[fwd_idx:] + forwards[:fwd_idx]):
                if fwd_added >= 3:
                    break
                # Be more lenient with budget for last players
                budget_check = team['budget'] + forward['price'] <= 100.5 if fwd_added < 2 else team['budget'] + forward['price'] <= 101
                if club_count.get(forward['club'], 0) < 3 and budget_check:
                    if fwd_added < 1:  # First forward to starting XI
                        team['players'].append({
                            'name': forward['player_name'],
                            'position': 'FWD',
                            'price': forward['price'],
                            'score': forward['weighted_score'],
                            'club': forward['club']
                        })
                    else:  # Other forwards to bench
                        team['bench'].append({
                            'name': forward['player_name'],
                            'position': 'FWD',
                            'price': forward['price'],
                            'score': forward['weighted_score'],
                            'club': forward['club']
                        })
                    team['budget'] += forward['price']
                    team['score'] += forward['weighted_score']
                    team['positions']['FWD'] += 1
                    club_count[forward['club']] = club_count.get(forward['club'], 0) + 1
                    fwd_added += 1
            
            # Verify we have exactly 15 players with correct distribution
            total_players = len(team['players']) + len(team['bench'])
            if total_players != 15:
                if variation == 0 and team_id == 0:  # Debug first attempt
                    print(f"  Failed: Only {total_players} players (need 15)")
                    print(f"    GK: {team['positions']['GK']}, DEF: {team['positions']['DEF']}, MID: {team['positions']['MID']}, FWD: {team['positions']['FWD']}")
                    print(f"    Budget used: £{team['budget']:.1f}m")
                continue
            
            positions_filled = team['positions']
            if positions_filled['GK'] != 2 or positions_filled['DEF'] != 5 or \
               positions_filled['MID'] != 5 or positions_filled['FWD'] != 3:
                if variation == 0 and team_id == 0:  # Debug first attempt
                    print(f"  Failed position check: GK={positions_filled['GK']}, DEF={positions_filled['DEF']}, MID={positions_filled['MID']}, FWD={positions_filled['FWD']}")
                continue
            
            # Verify starting XI has valid formation
            starting_positions = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
            for player in team['players']:
                starting_positions[player['position']] += 1
            
            # Valid formations: 1 GK, 3-5 DEF, 2-5 MID, 1-3 FWD
            if not (starting_positions['GK'] == 1 and 
                    3 <= starting_positions['DEF'] <= 5 and
                    2 <= starting_positions['MID'] <= 5 and
                    1 <= starting_positions['FWD'] <= 3 and
                    sum(starting_positions.values()) == 11):
                continue
            
            # Sort players by score for captain selection
            all_scorers = sorted(team['players'], key=lambda x: x['score'], reverse=True)
            captain = all_scorers[0]['name']
            
            # Determine formation
            formation = f"{starting_positions['DEF']}-{starting_positions['MID']}-{starting_positions['FWD']}"
            
            # Calculate scores
            gw1_score = sum(p['score'] for p in team['players'])
            captain_score = all_scorers[0]['score']
            gw1_score += captain_score  # Captain gets double points
            
            teams.append({
                'captain': captain,
                'formation': formation,
                'budget': round(team['budget'], 1),
                'gw1_score': round(gw1_score, 1),
                '5gw_estimated': round(gw1_score * 5.15, 1),  # Rough estimate
                'players': team['players'],
                'bench': team['bench'],
                'total_players': 15,
                'total_gk': 2,
                'total_def': 5,
                'total_mid': 5,
                'total_fwd': 3
            })
            
            team_id += 1
    
    # Convert to DataFrame
    teams_df = pd.DataFrame(teams)
    
    if len(teams_df) == 0:
        print("No valid teams generated!")
        return teams_df
    
    # Sort by score
    teams_df = teams_df.sort_values('5gw_estimated', ascending=False)
    
    print(f"\nGenerated {len(teams_df)} valid teams with correct 15-player squads")
    
    # Verify captain distribution
    print(f"\nCaptain distribution in top teams:")
    captain_counts = teams_df.head(50)['captain'].value_counts()
    for captain, count in captain_counts.head().items():
        print(f"  {captain}: {count} teams")
    
    # Verify all teams have correct player counts
    print(f"\nVerifying player counts:")
    print(f"All teams have 2 GKs: {(teams_df['total_gk'] == 2).all()}")
    print(f"All teams have 5 DEFs: {(teams_df['total_def'] == 5).all()}")
    print(f"All teams have 5 MIDs: {(teams_df['total_mid'] == 5).all()}")
    print(f"All teams have 3 FWDs: {(teams_df['total_fwd'] == 3).all()}")
    
    return teams_df


if __name__ == "__main__":
    import os
    
    # Use the v3 predictions
    predictions_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/predictions_gw39_proper_v3.csv"
    
    if not os.path.exists(predictions_file):
        print(f"Error: Predictions file not found: {predictions_file}")
        exit(1)
    
    print("Building optimal FPL teams with EXACTLY 15 players (2 GK, 5 DEF, 5 MID, 3 FWD)...")
    print("Special rules: 2 GKs must be from same club, backup GK score = 0.2")
    teams_df = build_optimal_teams(predictions_file, num_teams=200)
    
    # Save results
    output_file = "/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/top_200_teams_final_v16.csv"
    teams_df.to_csv(output_file, index=False)
    print(f"\nSaved {len(teams_df)} teams to {output_file}")
    
    # Display top teams
    if len(teams_df) > 0:
        print(f"\nTop 10 teams:")
        display_cols = ['captain', 'formation', 'budget', '5gw_estimated', 
                        'total_players', 'total_gk', 'total_def', 'total_mid', 'total_fwd']
        print(teams_df.head(10)[display_cols])
    else:
        print("\nNo valid teams generated - check constraints!")