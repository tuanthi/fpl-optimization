#!/usr/bin/env python3
"""
Generate a comprehensive transfer strategy report for GW40-43
"""

import json
import pandas as pd
from pathlib import Path


def generate_transfer_report():
    """Generate detailed transfer report with recommendations"""
    
    # Load results
    results_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/transfer_optimization_gw40_43.json")
    with open(results_file, 'r') as f:
        all_results = json.load(f)
    
    # Load summary
    summary_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/transfer_summary_gw40_43.csv")
    summary_df = pd.read_csv(summary_file)
    
    # Create comprehensive report
    report = []
    report.append("="*80)
    report.append("FPL TRANSFER OPTIMIZATION REPORT: GW40-43")
    report.append("="*80)
    report.append("")
    
    # Overall summary
    report.append("EXECUTIVE SUMMARY")
    report.append("-"*40)
    report.append("Period: Gameweeks 40-43 (4 gameweeks)")
    report.append("Transfer Rule: 1 free transfer per GW, -4 points for additional")
    report.append("")
    
    # Team performance comparison
    report.append("TEAM PERFORMANCE COMPARISON")
    report.append("-"*40)
    
    team_summary = []
    for i, result in enumerate(all_results):
        team_num = i + 1
        total_score = result['total_score']
        transfer_cost = result['total_transfer_cost']
        net_score = total_score - transfer_cost
        
        team_summary.append({
            'Team': team_num,
            'Total Score': f"{total_score:.1f}",
            'Transfer Cost': f"-{transfer_cost}",
            'Net Score': f"{net_score:.1f}",
            'Avg per GW': f"{net_score/4:.1f}"
        })
    
    summary_table = pd.DataFrame(team_summary)
    report.append(summary_table.to_string(index=False))
    report.append("")
    
    # Best performing team
    best_team_idx = max(range(len(all_results)), 
                       key=lambda i: all_results[i]['total_score'] - all_results[i]['total_transfer_cost'])
    report.append(f"RECOMMENDED: Team {best_team_idx + 1} (highest net score)")
    report.append("")
    
    # Detailed team analysis
    for i, result in enumerate(all_results):
        team_num = i + 1
        report.append("="*80)
        report.append(f"TEAM {team_num} DETAILED TRANSFER PLAN")
        report.append("="*80)
        report.append("")
        
        # Initial squad summary
        report.append("Initial Squad Key Players:")
        initial = result['initial_team']
        
        # Extract key players from initial team
        key_players = []
        if 'MID1' in initial:
            key_players.append(f"- Captain: {initial.get('captain', 'N/A')}")
            key_players.append(f"- Goalkeeper: {initial.get('GK1', 'N/A')}")
            key_players.append(f"- Key Midfielders: {initial.get('MID1', 'N/A')}, {initial.get('MID2', 'N/A')}")
            key_players.append(f"- Key Forward: {initial.get('FWD1', 'N/A')}")
        
        report.extend(key_players)
        report.append("")
        
        # Gameweek by gameweek breakdown
        report.append("Transfer Strategy by Gameweek:")
        report.append("-"*40)
        
        for gw_num in range(40, 44):
            gw_key = f'GW{gw_num}'
            if gw_key in result['gameweeks']:
                gw_data = result['gameweeks'][gw_key]
                
                report.append(f"\nGameweek {gw_num}:")
                report.append(f"  Formation: {gw_data['formation']}")
                report.append(f"  Captain: {gw_data['captain']}")
                report.append(f"  Score: {gw_data['score']:.1f} points")
                
                if gw_data['transfers']:
                    report.append(f"  Transfers ({len(gw_data['transfers'])}):")
                    for transfer in gw_data['transfers']:
                        report.append(f"    • OUT: {transfer['out']}")
                        report.append(f"      IN:  {transfer['in']} (+{transfer['improvement']:.1f} pts)")
                    
                    if gw_data['transfer_cost'] > 0:
                        report.append(f"  Transfer Cost: -{gw_data['transfer_cost']} points")
                else:
                    report.append("  Transfers: None (squad unchanged)")
        
        report.append("")
        report.append(f"Team {team_num} Total Net Score: {result['total_score'] - result['total_transfer_cost']:.1f} points")
        report.append("")
    
    # Key insights
    report.append("="*80)
    report.append("KEY INSIGHTS & RECOMMENDATIONS")
    report.append("="*80)
    report.append("")
    
    # Analyze transfer patterns
    all_transfers = []
    for result in all_results:
        for gw_key, gw_data in result['gameweeks'].items():
            for transfer in gw_data['transfers']:
                all_transfers.append({
                    'out': transfer['out'],
                    'in': transfer['in'],
                    'improvement': transfer['improvement']
                })
    
    if all_transfers:
        # Most transferred out
        out_counts = pd.Series([t['out'] for t in all_transfers]).value_counts()
        report.append("Most Transferred Out Players:")
        for player, count in out_counts.head(5).items():
            report.append(f"  • {player}: {count} times")
        report.append("")
        
        # Most transferred in
        in_counts = pd.Series([t['in'] for t in all_transfers]).value_counts()
        report.append("Most Transferred In Players:")
        for player, count in in_counts.head(5).items():
            report.append(f"  • {player}: {count} times")
        report.append("")
        
        # Best value transfers
        transfers_df = pd.DataFrame(all_transfers)
        best_transfers = transfers_df.nlargest(5, 'improvement')
        report.append("Highest Impact Transfers:")
        for _, transfer in best_transfers.iterrows():
            report.append(f"  • {transfer['out']} → {transfer['in']} (+{transfer['improvement']:.1f} pts)")
    
    report.append("")
    report.append("FINAL RECOMMENDATIONS:")
    report.append("-"*40)
    report.append("1. Team 2 provides the best balance with minimal transfer costs")
    report.append("2. Key transfers focus on form players and fixture swings")
    report.append("3. Goalkeeper transfers can provide significant gains")
    report.append("4. Avoid taking hits (-4) unless improvement exceeds 4 points")
    report.append("5. Monitor Chris Wood and Anthony Elanga as key differentials")
    
    # Save report
    report_text = '\n'.join(report)
    report_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/transfer_strategy_report.txt")
    with open(report_file, 'w') as f:
        f.write(report_text)
    
    print(report_text)
    print(f"\n\nReport saved to: {report_file}")
    
    # Also create a visual summary CSV
    visual_summary = []
    for i, result in enumerate(all_results):
        team_num = i + 1
        for gw_num in range(40, 44):
            gw_key = f'GW{gw_num}'
            if gw_key in result['gameweeks']:
                gw_data = result['gameweeks'][gw_key]
                visual_summary.append({
                    'Team': team_num,
                    'GW': gw_num,
                    'Captain': gw_data['captain'],
                    'Formation': gw_data['formation'],
                    'Transfers': len(gw_data['transfers']),
                    'Transfer_Cost': gw_data['transfer_cost'],
                    'GW_Score': gw_data['score'],
                    'Cumulative_Score': sum(result['gameweeks'][f'GW{g}']['score'] 
                                           for g in range(40, gw_num+1) 
                                           if f'GW{g}' in result['gameweeks'])
                })
    
    visual_df = pd.DataFrame(visual_summary)
    visual_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/transfer_visual_summary.csv")
    visual_df.to_csv(visual_file, index=False)
    print(f"Visual summary saved to: {visual_file}")


if __name__ == "__main__":
    generate_transfer_report()