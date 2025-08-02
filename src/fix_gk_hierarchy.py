#!/usr/bin/env python3
"""
Fix GK hierarchy - ensure backup GKs don't get selected as starting GKs
Main GKs should have significantly higher scores than backups
"""

import pandas as pd
import numpy as np

def identify_main_gks():
    """Identify main GKs based on historical data and price"""
    # Known main GKs for 2025 season (based on price and status)
    main_gks = {
        'Arsenal': 'David Raya Martín',
        'Aston Villa': 'Emiliano Martínez Romero',
        'Bournemouth': 'Norberto Murara Neto',  # Neto
        'Brentford': 'Caoimhín Kelleher',
        'Brighton': 'Bart Verbruggen',
        'Burnley': 'Max Weiß',
        'Chelsea': 'Robert Lynch Sánchez',  # Sánchez is main, not Jörgensen
        'Crystal Palace': 'Dean Henderson',
        'Everton': 'Jordan Pickford',
        'Fulham': 'Bernd Leno',
        'Leeds': 'Illan Meslier',
        'Liverpool': 'Alisson Becker',
        'Man City': 'Ederson Santana de Moraes',
        'Man Utd': 'André Onana',
        'Newcastle': 'Nick Pope',
        "Nott'm Forest": 'Matz Sels',
        'Southampton': 'Aaron Ramsdale',
        'Spurs': 'Guglielmo Vicario',
        'Sunderland': 'Robin Roefs',
        'West Ham': 'Alphonse Areola',
        'Wolves': 'José Malheiro de Sá'
    }
    return main_gks

def fix_gk_scores():
    """Adjust GK scores to ensure proper hierarchy"""
    
    # Load predictions
    df = pd.read_csv('../data/cached_merged_2024_2025_v2/predictions_gw39_proper_v3.csv')
    
    # Get main GKs
    main_gks = identify_main_gks()
    
    print("Fixing GK hierarchy...")
    print("="*80)
    
    adjustments = []
    
    # Group by club and check GKs
    gk_df = df[df['role'] == 'GK'].copy()
    
    for club in gk_df['club'].unique():
        club_gks = gk_df[gk_df['club'] == club].copy()
        
        if len(club_gks) > 1:
            print(f"\n{club}:")
            
            # Sort by price (higher price usually = main GK)
            club_gks = club_gks.sort_values('price', ascending=False)
            
            main_gk_name = main_gks.get(club, None)
            
            for idx, gk in club_gks.iterrows():
                gk_name = f"{gk['first_name']} {gk['last_name']}"
                is_main = gk_name == main_gk_name
                
                old_score = gk['weighted_score']
                
                if is_main:
                    # Main GK - ensure reasonable score
                    if old_score < 2.0:
                        new_score = max(2.5, old_score * 1.5)
                    else:
                        new_score = old_score
                    print(f"  MAIN: {gk_name} - £{gk['price']}m, score: {old_score:.2f} → {new_score:.2f}")
                else:
                    # Backup GK - heavily penalize to prevent starting selection
                    if old_score > 2.0:
                        # This is too high for a backup
                        new_score = min(1.5, old_score * 0.4)
                    else:
                        new_score = old_score * 0.5
                    print(f"  Backup: {gk_name} - £{gk['price']}m, score: {old_score:.2f} → {new_score:.2f}")
                
                if new_score != old_score:
                    adjustments.append({
                        'index': idx,
                        'name': gk_name,
                        'club': club,
                        'old_score': old_score,
                        'new_score': new_score,
                        'is_main': is_main
                    })
                    df.loc[idx, 'weighted_score'] = new_score
    
    # Special cases based on the specific issue
    print("\nSpecial adjustments for known issues:")
    
    # Fix Filip Jörgensen specifically
    filip_mask = (df['first_name'] == 'Filip') & (df['last_name'] == 'Jörgensen') & (df['club'] == 'Chelsea')
    if filip_mask.any():
        filip_idx = df[filip_mask].index[0]
        old_score = df.loc[filip_idx, 'weighted_score']
        new_score = 1.2  # Low score for backup
        df.loc[filip_idx, 'weighted_score'] = new_score
        print(f"  Filip Jörgensen (Chelsea backup): {old_score:.2f} → {new_score:.2f}")
    
    # Ensure Sánchez is properly scored
    sanchez_mask = (df['last_name'] == 'Lynch Sánchez') & (df['club'] == 'Chelsea')
    if sanchez_mask.any():
        sanchez_idx = df[sanchez_mask].index[0]
        old_score = df.loc[sanchez_idx, 'weighted_score']
        if old_score < 3.0:
            new_score = 3.5  # Reasonable score for main GK
            df.loc[sanchez_idx, 'weighted_score'] = new_score
            print(f"  Robert Sánchez (Chelsea main): {old_score:.2f} → {new_score:.2f}")
    
    # Save updated predictions
    output_file = '../data/cached_merged_2024_2025_v2/predictions_gw39_proper_v4.csv'
    df.to_csv(output_file, index=False)
    
    print(f"\nSaved {len(adjustments)} GK adjustments to: {output_file}")
    
    # Show summary
    print("\nSummary of GK adjustments:")
    print(f"- Total GKs adjusted: {len(adjustments)}")
    print(f"- Main GKs boosted: {sum(1 for a in adjustments if a['is_main'])}")
    print(f"- Backup GKs penalized: {sum(1 for a in adjustments if not a['is_main'])}")
    
    # Verify Chelsea GKs
    print("\nVerifying Chelsea GK hierarchy:")
    chelsea_gks = df[(df['club'] == 'Chelsea') & (df['role'] == 'GK')].sort_values('weighted_score', ascending=False)
    for _, gk in chelsea_gks.iterrows():
        print(f"  {gk['first_name']} {gk['last_name']}: £{gk['price']}m, score: {gk['weighted_score']:.2f}")
    
    return df

if __name__ == "__main__":
    fix_gk_scores()