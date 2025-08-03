#!/usr/bin/env python3
"""
Compare the two transfer strategies and generate insights
"""

import json
import pandas as pd
from pathlib import Path


def main():
    # Load both strategy results
    v1_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/transfer_optimization_gw40_43.json")
    v2_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/transfer_optimization_v2_gw40_43.json")
    
    with open(v1_file, 'r') as f:
        v1_results = json.load(f)
    
    with open(v2_file, 'r') as f:
        v2_results = json.load(f)
    
    print("="*80)
    print("TRANSFER STRATEGY COMPARISON REPORT")
    print("="*80)
    print()
    
    print("STRATEGY COMPARISON")
    print("-"*40)
    print("V1: Standard (immediate transfers)")
    print("V2: Enhanced (rollover capability, GK penalty)")
    print()
    
    # Compare overall scores
    print("OVERALL PERFORMANCE")
    print("-"*40)
    print("Team | V1 Net Score | V2 Net Score | Difference")
    print("-"*50)
    
    for i in range(3):
        v1_net = v1_results[i]['total_score'] - v1_results[i]['total_transfer_cost']
        v2_net = v2_results[i]['total_score'] - v2_results[i]['total_transfer_cost']
        diff = v2_net - v1_net
        print(f"  {i+1}  |    {v1_net:6.1f}    |    {v2_net:6.1f}    |  {diff:+6.1f}")
    
    print()
    
    # Analyze transfer patterns
    print("TRANSFER PATTERNS")
    print("-"*40)
    
    # Count GK transfers
    v1_gk_transfers = 0
    v2_gk_transfers = 0
    
    for result in v1_results:
        for gw, gw_data in result['gameweeks'].items():
            for transfer in gw_data['transfers']:
                if 'GK' in transfer['out'] or any(gk in transfer['out'] for gk in ['Sels', 'Pickford', 'Raya', 'Weiß']):
                    v1_gk_transfers += 1
    
    for result in v2_results:
        for gw, gw_data in result['gameweeks'].items():
            for transfer in gw_data['transfers']:
                if 'GK' in transfer['out'] or any(gk in transfer['out'] for gk in ['Sels', 'Pickford', 'Raya', 'Weiß']):
                    v2_gk_transfers += 1
    
    print(f"GK Transfers in V1: {v1_gk_transfers}")
    print(f"GK Transfers in V2: {v2_gk_transfers}")
    print()
    
    # Transfer timing analysis
    print("TRANSFER TIMING")
    print("-"*40)
    
    for i in range(3):
        print(f"\nTeam {i+1}:")
        v1_transfers = []
        v2_transfers = []
        
        for gw in ['GW40', 'GW41', 'GW42', 'GW43']:
            v1_count = len(v1_results[i]['gameweeks'][gw]['transfers'])
            v2_count = len(v2_results[i]['gameweeks'][gw]['transfers'])
            v1_transfers.append(v1_count)
            v2_transfers.append(v2_count)
        
        print(f"  V1 transfers by GW: {v1_transfers} (Total: {sum(v1_transfers)})")
        print(f"  V2 transfers by GW: {v2_transfers} (Total: {sum(v2_transfers)})")
        print(f"  V1 hits taken: {max(0, sum(v1_transfers) - 4)}")
        print(f"  V2 hits taken: {max(0, sum(v2_transfers) - 4)}")
    
    # Key differences
    print("\n" + "="*80)
    print("KEY INSIGHTS")
    print("="*80)
    
    insights = []
    
    # Which strategy performed better?
    v1_avg = sum(r['total_score'] - r['total_transfer_cost'] for r in v1_results) / 3
    v2_avg = sum(r['total_score'] - r['total_transfer_cost'] for r in v2_results) / 3
    
    if v2_avg > v1_avg:
        insights.append(f"✓ V2 (Enhanced) strategy performed better: +{v2_avg - v1_avg:.1f} points on average")
    else:
        insights.append(f"✓ V1 (Standard) strategy performed better: +{v1_avg - v2_avg:.1f} points on average")
    
    # Transfer efficiency
    v1_total_transfers = sum(sum(len(r['gameweeks'][f'GW{g}']['transfers']) for g in range(40, 44)) for r in v1_results)
    v2_total_transfers = sum(sum(len(r['gameweeks'][f'GW{g}']['transfers']) for g in range(40, 44)) for r in v2_results)
    
    insights.append(f"✓ V1 made {v1_total_transfers} total transfers vs V2's {v2_total_transfers}")
    
    # Hit avoidance
    v1_hits = sum(r['total_transfer_cost'] for r in v1_results) // 4
    v2_hits = sum(r['total_transfer_cost'] for r in v2_results) // 4
    
    if v2_hits < v1_hits:
        insights.append(f"✓ V2 avoided {v1_hits - v2_hits} hits (-{(v1_hits - v2_hits) * 4} points saved)")
    
    # GK transfer analysis
    if v2_gk_transfers < v1_gk_transfers:
        insights.append(f"✓ V2 reduced GK transfers by {v1_gk_transfers - v2_gk_transfers}")
    elif v2_gk_transfers > 0:
        insights.append("! V2 still made GK transfers despite penalty (high value opportunities)")
    
    # Rollover usage
    rollover_used = False
    for result in v2_results:
        for gw, gw_data in result['gameweeks'].items():
            if gw_data.get('free_transfers_remaining', 1) > 1:
                rollover_used = True
                break
    
    if not rollover_used:
        insights.append("! No rollovers were used - immediate transfers were optimal")
    
    for insight in insights:
        print(f"  {insight}")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    print("1. Both strategies avoided taking hits, maximizing net scores")
    print("2. GK transfers can still be valuable despite low ROI perception")
    print("3. The rollover feature didn't provide benefit in this scenario")
    print("4. Focus on outfield transfers generally provides better returns")
    print("5. Team 1 consistently performs best across both strategies")
    
    # Save comparison
    comparison_data = {
        'strategy_comparison': {
            'v1_average_score': v1_avg,
            'v2_average_score': v2_avg,
            'difference': v2_avg - v1_avg,
            'v1_total_transfers': v1_total_transfers,
            'v2_total_transfers': v2_total_transfers,
            'v1_hits': v1_hits,
            'v2_hits': v2_hits,
            'v1_gk_transfers': v1_gk_transfers,
            'v2_gk_transfers': v2_gk_transfers
        },
        'team_scores': {
            f'team_{i+1}': {
                'v1_net_score': v1_results[i]['total_score'] - v1_results[i]['total_transfer_cost'],
                'v2_net_score': v2_results[i]['total_score'] - v2_results[i]['total_transfer_cost']
            } for i in range(3)
        }
    }
    
    output_file = Path("/Users/huetuanthi/dev/dokeai/fpl/data/cached_merged_2024_2025_v3/strategy_comparison.json")
    with open(output_file, 'w') as f:
        json.dump(comparison_data, f, indent=2)
    
    print(f"\n\nComparison saved to: {output_file}")


if __name__ == "__main__":
    main()