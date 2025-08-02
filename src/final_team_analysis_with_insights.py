#!/usr/bin/env python3
"""
Final comprehensive team analysis with web insights
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path


def create_final_analysis():
    """Create final analysis combining statistical and web insights"""
    
    # Load the teams
    teams_file = "../data/cached_merged_2024_2025_v2/top_200_teams_final_v8.csv"
    teams_df = pd.read_csv(teams_file)
    
    # Create comprehensive analysis based on all insights
    analysis = {
        "analysis_date": datetime.now().isoformat(),
        "analysis_type": "comprehensive_with_web_insights",
        "key_insights_from_web": {
            "mohamed_salah": {
                "2024_25_performance": "Record-breaking 344 points in single season",
                "captain_stats": "Captained 139,874,652 times across 38 GWs",
                "best_score": "29 points in DGW24 (Triple-Captained by 1M+ managers)",
                "consistency": "18 double-figure returns - twice any other player",
                "goals": "22 goals - 3 ahead of Haaland"
            },
            "cole_palmer": {
                "2024_25_performance": "Second-highest scorer with 173 points",
                "best_score": "25 points vs Brighton (4 goals in GW6)",
                "key_stats": "Created most chances (65) across all positions",
                "penalties": "Chelsea's no.1 penalty taker"
            },
            "matz_sels": {
                "performance": "13 clean sheets - best among all GKs",
                "fpl_points": "150 points - second best among GKs",
                "value": "£5.2m - excellent value with 11 bonus points",
                "status": "Clear first-choice GK for Nottingham Forest"
            },
            "matt_turner": {
                "status": "Third choice GK behind Sels and Carlos Miguel",
                "last_start": "February 28 in FA Cup",
                "fpl_relevance": "Not recommended for FPL - won't get minutes"
            },
            "chris_wood": {
                "performance": "Named in Team of the Month (October)",
                "partnership": "Strong partnership with Matz Sels"
            }
        },
        "recommendations": {
            "top_team": {
                "rank": 1,
                "formation": "4-4-2",
                "captain": "Mohamed Salah",
                "key_players": ["Mohamed Salah", "Cole Palmer", "Chris Wood", "Matz Sels"],
                "projected_score": 352.2,
                "budget": 99.0,
                "reasoning": [
                    "Salah's proven record-breaking consistency as captain",
                    "Palmer's explosive potential and penalty duties",
                    "Wood offers excellent value in strong Nottingham Forest team",
                    "Balanced formation with flexibility",
                    "Strong bench options for rotation"
                ],
                "concerns": [
                    "Matt Turner as backup GK won't play - consider alternative",
                    "High ownership of key players may limit rank gains"
                ]
            },
            "alternative_1": {
                "rank": 2,
                "formation": "5-3-2",
                "reasoning": "More defensive stability while maintaining Salah-Palmer core"
            },
            "alternative_2": {
                "rank": 5,
                "formation": "4-4-2",
                "reasoning": "Similar structure with differential picks for upside"
            }
        },
        "gk_pairing_issue": {
            "problem": "Matt Turner is third choice at Nottingham Forest",
            "solution": "Consider different backup GK strategy or accept minimal risk",
            "note": "Matz Sels has been extremely reliable with 13 clean sheets"
        }
    }
    
    # Save comprehensive analysis
    output_file = "../data/cached_merged_2024_2025_v2/final_analysis_comprehensive.json"
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    # Create final recommended teams CSV
    final_teams = []
    
    # Team 1 - Best overall
    team1 = teams_df.iloc[0].to_dict()
    team1['recommendation_rank'] = 1
    team1['recommendation_reason'] = "Highest scoring potential with proven captain in Salah"
    team1['web_insights'] = "Salah broke FPL records with 344 points in 2024/25"
    final_teams.append(team1)
    
    # Team 2 - Defensive option
    team2 = teams_df.iloc[1].to_dict()
    team2['recommendation_rank'] = 2
    team2['recommendation_reason'] = "5-3-2 offers defensive stability with premium assets"
    team2['web_insights'] = "Clean sheet potential with Sels (13 CS in 2024/25)"
    final_teams.append(team2)
    
    # Team 3 - Differential option
    team3 = teams_df.iloc[4].to_dict()
    team3['recommendation_rank'] = 3
    team3['recommendation_reason'] = "Balanced team with differential picks for rank climbs"
    team3['web_insights'] = "Less template-dependent for mini-league success"
    final_teams.append(team3)
    
    # Save final recommendations
    final_df = pd.DataFrame(final_teams)
    final_df.to_csv("../data/cached_merged_2024_2025_v2/final_recommended_teams_v1.csv", index=False)
    
    # Print summary
    print("\n" + "="*80)
    print("FINAL FPL TEAM RECOMMENDATIONS (WITH WEB INSIGHTS)")
    print("="*80)
    
    print("\n📊 KEY INSIGHTS FROM 2024/25 SEASON:")
    print(f"   • Mohamed Salah: Record 344 points, captained 139M times")
    print(f"   • Cole Palmer: 173 points, created most chances (65)")
    print(f"   • Matz Sels: 13 clean sheets (best among GKs)")
    print(f"   • Chris Wood: Team of the Month performer")
    
    print("\n⚠️  IMPORTANT NOTES:")
    print(f"   • Matt Turner is 3rd choice GK - won't get minutes")
    print(f"   • Consider alternative backup GK strategy")
    print(f"   • Sels has been extremely reliable as starting GK")
    
    print("\n🏆 TOP 3 RECOMMENDED TEAMS:")
    for i, team in enumerate(final_teams):
        print(f"\n{i+1}. {team['formation']} Formation - £{team['budget']}m")
        print(f"   Captain: {team['captain']}")
        print(f"   GW1 Score: {team['gw1_score']:.1f}")
        print(f"   5GW Projection: {team['5gw_estimated']:.1f}")
        print(f"   Key: {team['recommendation_reason']}")
        print(f"   Insight: {team['web_insights']}")
    
    print("\n" + "="*80)
    print("Analysis complete! Files saved:")
    print(f"   • {output_file}")
    print(f"   • ../data/cached_merged_2024_2025_v2/final_recommended_teams_v1.csv")
    print("="*80)


if __name__ == "__main__":
    create_final_analysis()