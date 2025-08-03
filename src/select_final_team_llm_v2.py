#!/usr/bin/env python3
"""
Select the best FPL team using LLM analysis - Version 2
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


def analyze_teams_with_llm(teams_file: str, output_file: str):
    """Analyze teams using Anthropic's advanced reasoning"""
    
    # Load API key
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if not anthropic_key:
        raise ValueError("Missing ANTHROPIC_API_KEY")
    
    client = Anthropic(api_key=anthropic_key)
    
    # Load teams
    teams_df = pd.read_csv(teams_file)
    print(f"Loaded {len(teams_df)} teams for analysis")
    
    # Prepare detailed team data for top 10
    top_teams = []
    for idx, team in teams_df.head(10).iterrows():
        # Extract full lineup
        lineup = {
            'GK': [],
            'DEF': [],
            'MID': [],
            'FWD': []
        }
        
        # Parse players
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            if pos == 'GK':
                max_num = 2
            elif pos == 'DEF':
                max_num = 5
            elif pos == 'MID':
                max_num = 5
            else:  # FWD
                max_num = 3
                
            for i in range(1, max_num + 1):
                player_col = f'{pos}{i}'
                if player_col in team and pd.notna(team[player_col]):
                    player_info = {
                        'name': team[player_col],
                        'price': team.get(f'{player_col}_price', 0),
                        'score': team.get(f'{player_col}_score', 0),
                        'selected': team.get(f'{player_col}_selected', 0)
                    }
                    lineup[pos].append(player_info)
        
        team_data = {
            'rank': idx + 1,
            'captain': team['captain'],
            'formation': team['formation'],
            'budget': team['budget'],
            'gw1_score': team['gw1_score'],
            '5gw_estimated': team['5gw_estimated'],
            'lineup': lineup
        }
        
        top_teams.append(team_data)
    
    # Create analysis prompt
    prompt = f"""
    You are an expert FPL analyst evaluating teams for the 2025/26 season.
    
    Analyze these top 10 teams and select the BEST 3 considering:
    
    1. **Statistical Performance**: Teams with highest projected points
    2. **Risk vs Reward**: Balance between safe picks and differentials
    3. **Team Structure**: Formation flexibility and bench strength
    4. **Captain Options**: Reliability of captain choices
    5. **Budget Efficiency**: Value extraction across all positions
    6. **GK Strategy**: Note that teams have same-team GK pairings for injury coverage
    
    Top 10 Teams Data:
    {json.dumps(top_teams, indent=2)}
    
    Key considerations:
    - Mohamed Salah (Liverpool) - Premium captain, consistent performer
    - Cole Palmer (Chelsea) - Creative midfielder with good form
    - Bryan Mbeumo (Man Utd) - Key player in this scenario
    - Chris Wood (Nott'm Forest) - Value forward option
    - GK pairings from same team provide injury coverage
    
    Select exactly 3 teams and provide detailed reasoning.
    
    Return ONLY a JSON array (no other text) with this exact format:
    [
        {{
            "rank": 1,
            "reason": "Detailed explanation of why this is the best team",
            "key_strengths": ["strength1", "strength2", "strength3"],
            "potential_weaknesses": ["weakness1", "weakness2"],
            "risk_assessment": "low",
            "confidence": 90
        }},
        {{
            "rank": 2,
            "reason": "Explanation for second choice",
            "key_strengths": ["strength1", "strength2", "strength3"],
            "potential_weaknesses": ["weakness1", "weakness2"],
            "risk_assessment": "low",
            "confidence": 85
        }},
        {{
            "rank": 5,
            "reason": "Explanation for third choice",
            "key_strengths": ["strength1", "strength2", "strength3"],
            "potential_weaknesses": ["weakness1", "weakness2"],
            "risk_assessment": "medium",
            "confidence": 80
        }}
    ]
    """
    
    try:
        print("\nAnalyzing teams with advanced LLM reasoning...")
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        content = response.content[0].text.strip()
        
        # Try to parse JSON directly
        try:
            selections = json.loads(content)
        except:
            # If that fails, try to extract JSON from the response
            import re
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                selections = json.loads(json_match.group())
            else:
                raise ValueError("Could not extract valid JSON from response")
        
        # Get the selected teams with full data
        results = []
        for selection in selections[:3]:
            team_idx = selection['rank'] - 1
            team_data = teams_df.iloc[team_idx].to_dict()
            
            # Add LLM analysis to team data
            team_data['selection_reason'] = selection['reason']
            team_data['key_strengths'] = selection.get('key_strengths', [])
            team_data['potential_weaknesses'] = selection.get('potential_weaknesses', [])
            team_data['risk_assessment'] = selection.get('risk_assessment', 'medium')
            team_data['confidence'] = selection.get('confidence', 75)
            
            results.append(team_data)
        
        # Save results
        output_data = {
            'analysis_date': datetime.now().isoformat(),
            'analysis_type': 'LLM_advanced',
            'teams_analyzed': len(teams_df),
            'selected_teams': results
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        # Save CSV with proper formatting
        csv_output = output_file.replace('.json', '.csv')
        selected_df = pd.DataFrame(results)
        
        # Convert lists to strings for CSV
        for col in ['key_strengths', 'potential_weaknesses']:
            if col in selected_df.columns:
                selected_df[col] = selected_df[col].apply(
                    lambda x: '; '.join(x) if isinstance(x, list) else str(x)
                )
        
        selected_df.to_csv(csv_output, index=False)
        
        print(f"\nResults saved to: {output_file}")
        print(f"Selected teams CSV: {csv_output}")
        
        # Display results
        print("\n" + "="*80)
        print("TOP 3 RECOMMENDED TEAMS (LLM ANALYSIS)")
        print("="*80)
        
        for i, team in enumerate(results):
            print(f"\n{i+1}. Team (Original Rank: #{selection['rank']})")
            print(f"   Captain: {team['captain']}")
            print(f"   Formation: {team['formation']}")
            print(f"   Budget: £{team['budget']}m")
            print(f"   GW1 Score: {team['gw1_score']:.1f}")
            print(f"   5GW Score: {team['5gw_estimated']:.1f}")
            print(f"   GK Pairing: {team.get('GK1', 'N/A')} / {team.get('GK2', 'N/A')}")
            print(f"   Risk: {team['risk_assessment']}")
            print(f"   Confidence: {team['confidence']}%")
            
            if team.get('key_strengths'):
                print(f"   Key Strengths:")
                for strength in team['key_strengths']:
                    print(f"     + {strength}")
            
            if team.get('potential_weaknesses'):
                print(f"   Potential Weaknesses:")
                for weakness in team['potential_weaknesses']:
                    print(f"     - {weakness}")
            
            print(f"   Analysis: {team['selection_reason']}")
            print("-" * 80)
            
        return results
            
    except Exception as e:
        print(f"Error in LLM analysis: {e}")
        print(f"Full error details: {str(e)}")
        
        # Fallback to statistical selection
        print("\nFalling back to statistical top 3...")
        results = []
        for i in range(3):
            team_data = teams_df.iloc[i].to_dict()
            team_data['selection_reason'] = f"Top {i+1} team by projected 5GW score"
            team_data['key_strengths'] = [
                "Highest statistical projection",
                "Proven player combinations",
                "Balanced team structure"
            ]
            team_data['potential_weaknesses'] = [
                "May be highly owned",
                "Limited differentials"
            ]
            team_data['risk_assessment'] = "low"
            team_data['confidence'] = 90 - i*5
            results.append(team_data)
        
        return results


def main():
    """Entry point"""
    import sys
    if len(sys.argv) > 2:
        teams_file = sys.argv[1]
        output_file = sys.argv[2]
    else:
        teams_file = "../data/cached_merged_2024_2025_v2/top_200_teams_final_v8.csv"
        output_file = "../data/cached_merged_2024_2025_v2/final_selected_teams_llm_v2.json"
    
    analyze_teams_with_llm(teams_file, output_file)


if __name__ == "__main__":
    main()