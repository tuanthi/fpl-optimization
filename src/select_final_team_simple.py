#!/usr/bin/env python3
"""
Simplified version: Select the best FPL team from top 200 candidates
"""

import os
import json
import pandas as pd
from datetime import datetime
from anthropic import Anthropic
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


def analyze_teams_simple(teams_file: str, output_file: str):
    """Simplified team analysis using just Anthropic"""
    
    # Load API key
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if not anthropic_key:
        raise ValueError("Missing ANTHROPIC_API_KEY")
    
    client = Anthropic(api_key=anthropic_key)
    
    # Load teams
    teams_df = pd.read_csv(teams_file)
    print(f"Loaded {len(teams_df)} teams for analysis")
    
    # Prepare top 10 teams for analysis
    top_teams = []
    for idx, team in teams_df.head(10).iterrows():
        team_data = {
            'rank': idx + 1,
            'captain': team['captain'],
            'formation': team['formation'],
            'budget': team['budget'],
            'gw1_score': team['gw1_score'],
            '5gw_estimated': team['5gw_estimated'],
            'key_players': []
        }
        
        # Extract key players (captain + high scorers)
        for col in teams_df.columns:
            if col.endswith('_score') and pd.notna(team[col]) and team[col] > 4.0:
                player_col = col.replace('_score', '')
                selected_col = col.replace('_score', '_selected')
                
                if player_col in teams_df.columns and selected_col in teams_df.columns:
                    if team[selected_col] == 1:  # Only starting XI
                        player_name = team[player_col]
                        player_score = team[col]
                        team_data['key_players'].append({
                            'name': player_name,
                            'score': player_score,
                            'position': player_col[:3]
                        })
        
        # Sort by score
        team_data['key_players'].sort(key=lambda x: x['score'], reverse=True)
        team_data['key_players'] = team_data['key_players'][:5]  # Top 5 only
        
        top_teams.append(team_data)
    
    # Get analysis from Claude
    prompt = f"""
    You are an expert FPL analyst. Analyze these top 10 teams and select the BEST 3 teams 
    considering current form, fixtures, and general injury/suspension risks.
    
    Top 10 Teams:
    {json.dumps(top_teams, indent=2)}
    
    Key considerations:
    1. Mohamed Salah - Liverpool's talisman, consistent performer
    2. Bryan Mbeumo - Brentford's key player
    3. Cole Palmer - Chelsea's creative force
    4. Erling Haaland - Man City striker but rotation risk
    5. General injury/suspension risks for popular players
    
    Select the TOP 3 teams and explain why. Consider:
    - Captain reliability (avoid rotation risks)
    - Team balance 
    - Player form and fixtures
    - Value for money
    
    Return as JSON array with format:
    [
        {{
            "rank": original_rank,
            "reason": "detailed explanation",
            "risk_assessment": "low/medium/high",
            "confidence": 0-100
        }}
    ]
    
    Be specific about WHY each team is selected.
    """
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        content = response.content[0].text
        print("\nAnalysis Response:")
        print(content)
        
        # Extract JSON
        import re
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if json_match:
            selections = json.loads(json_match.group())
            
            # Get the selected teams
            results = []
            for selection in selections[:3]:
                team_idx = selection['rank'] - 1
                team_data = teams_df.iloc[team_idx].to_dict()
                team_data['selection_reason'] = selection['reason']
                team_data['risk_assessment'] = selection.get('risk_assessment', 'medium')
                team_data['confidence'] = selection.get('confidence', 75)
                results.append(team_data)
            
            # Save results
            output_data = {
                'analysis_date': datetime.now().isoformat(),
                'teams_analyzed': len(teams_df),
                'selected_teams': results
            }
            
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            # Save CSV
            csv_output = output_file.replace('.json', '.csv')
            selected_df = pd.DataFrame(results)
            selected_df.to_csv(csv_output, index=False)
            
            print(f"\nResults saved to: {output_file}")
            print(f"Selected teams CSV: {csv_output}")
            
            # Display results
            print("\n" + "="*80)
            print("TOP 3 RECOMMENDED TEAMS")
            print("="*80)
            
            for i, team in enumerate(results):
                print(f"\n{i+1}. Team")
                print(f"   Captain: {team['captain']}")
                print(f"   Formation: {team['formation']}")
                print(f"   Budget: £{team['budget']}m")
                print(f"   GW1 Score: {team['gw1_score']:.1f}")
                print(f"   5GW Score: {team['5gw_estimated']:.1f}")
                print(f"   Risk: {team['risk_assessment']}")
                print(f"   Confidence: {team['confidence']}%")
                print(f"   Reason: {team['selection_reason']}")
                print("-" * 80)
                
            return results
            
    except Exception as e:
        print(f"Error in analysis: {e}")
        # Fallback to top 3
        print("\nFalling back to top 3 teams by score...")
        results = []
        for i in range(3):
            team_data = teams_df.iloc[i].to_dict()
            team_data['selection_reason'] = "Top scoring team"
            team_data['risk_assessment'] = "low"
            team_data['confidence'] = 90 - i*5
            results.append(team_data)
        return results


def main():
    """Entry point"""
    teams_file = "../data/cached_merged_2024_2025_v2/top_200_teams_final_v8.csv"
    output_file = "../data/cached_merged_2024_2025_v2/final_selected_teams_v5.json"
    
    analyze_teams_simple(teams_file, output_file)


if __name__ == "__main__":
    main()