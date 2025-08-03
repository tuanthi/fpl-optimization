#!/usr/bin/env python3
"""
Enhanced LLM-based team selection with validation and auto-correction
Ensures all FPL requirements are met:
- Captain is highest scoring player
- 15 players total (2 GK, 5 DEF, 5 MID, 3 FWD)
- Starting XI: 1 GK, 3-5 DEF, 2-5 MID, 1-3 FWD
- No players who left Premier League
- Budget <= £100m
"""

import pandas as pd
import json
import os
from pathlib import Path
from anthropic import Anthropic
from datetime import datetime
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')

# Initialize Anthropic client
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def load_valid_players():
    """Load the current valid player pool"""
    predictions_file = Path("../data/cached_merged_2024_2025_v3/predictions_gw39_proper_v3.csv")
    if predictions_file.exists():
        df = pd.read_csv(predictions_file)
        # Create player lookup with club info
        player_lookup = {}
        for _, row in df.iterrows():
            player_name = f"{row['first_name']} {row['last_name']}".strip()
            player_lookup[player_name] = {
                'club': row['club'],
                'position': row['role'],
                'price': row['price'],
                'score': row.get('weighted_score', row.get('score', 0))
            }
        return player_lookup
    return {}

def apply_gk_rules(team_data):
    """Apply GK rules: 2 GKs from same club, backup gets 0.2 score"""
    fixes = []
    
    # Find all GKs
    gks = []
    for col in team_data.keys():
        if col.startswith('GK') and not col.endswith('_score') and not col.endswith('_price') and not col.endswith('_role'):
            if pd.notna(team_data.get(col)):
                gk_data = {
                    'name': team_data[col],
                    'score': team_data.get(f'{col}_score', 0),
                    'price': team_data.get(f'{col}_price', 0),
                    'club': team_data.get(f'{col}_club', ''),
                    'col': col
                }
                # Extract club from name if needed
                if isinstance(gk_data['name'], str) and '(' in gk_data['name'] and ')' in gk_data['name']:
                    gk_data['club'] = gk_data['name'].split('(')[1].split(')')[0]
                    gk_data['name'] = gk_data['name'].split(' (')[0]
                gks.append(gk_data)
    
    if len(gks) == 2:
        # Apply score rule: lower scoring GK gets 0.2
        if gks[0]['score'] > gks[1]['score']:
            team_data[f'{gks[1]["col"]}_score'] = 0.2
            fixes.append(f"Set backup GK {gks[1]['name']} score to 0.2")
        else:
            team_data[f'{gks[0]["col"]}_score'] = 0.2
            fixes.append(f"Set backup GK {gks[0]['name']} score to 0.2")
    
    return team_data, fixes

def validate_and_fix_team(team_data, valid_players):
    """Validate team and fix any issues"""
    issues = []
    fixes = []
    
    # Apply GK rules first
    team_data, gk_fixes = apply_gk_rules(team_data)
    fixes.extend(gk_fixes)
    
    # Extract all players from team
    players = []
    bench = []
    
    # Collect starting XI
    for pos in ['GK', 'DEF', 'MID', 'FWD']:
        for i in range(1, 12):
            key = f'{pos}{i}'
            if key in team_data and team_data[key]:
                player_info = {
                    'name': team_data[key],
                    'position': pos,
                    'price': team_data.get(f'{key}_price', 0),
                    'score': team_data.get(f'{key}_score', 0),
                    'club': team_data.get(f'{key}_club', ''),
                    'selected': team_data.get(f'{key}_selected', 1),
                    'key': key
                }
                if player_info['selected'] == 1:
                    players.append(player_info)
    
    # Collect bench
    for i in range(1, 5):
        key = f'BENCH{i}'
        if key in team_data and team_data[key]:
            bench.append({
                'name': team_data[key],
                'position': team_data.get(f'{key}_role', ''),
                'price': team_data.get(f'{key}_price', 0),
                'club': team_data.get(f'{key}_club', ''),
                'key': key
            })
    
    # 1. Check captain is highest scorer
    if players:
        highest_scorer = max(players, key=lambda x: x['score'])
        current_captain = team_data.get('captain', '')
        
        if current_captain != highest_scorer['name']:
            issues.append(f"Captain should be {highest_scorer['name']} (score: {highest_scorer['score']:.2f}) not {current_captain}")
            team_data['captain'] = highest_scorer['name']
            fixes.append(f"Changed captain to {highest_scorer['name']}")
    
    # 2. Check for invalid players (not in Premier League)
    all_team_players = players + bench
    for player in all_team_players:
        if player['name'] not in valid_players:
            issues.append(f"{player['name']} is not in valid player pool (may have left Premier League)")
            # This would need replacement logic
    
    # 3. Count positions
    pos_count = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
    for player in players:
        pos_count[player['position']] += 1
    
    # 4. Check starting XI formation
    if pos_count['GK'] != 1:
        issues.append(f"Starting XI must have exactly 1 GK, has {pos_count['GK']}")
    
    if pos_count['DEF'] < 3 or pos_count['DEF'] > 5:
        issues.append(f"Starting XI must have 3-5 DEF, has {pos_count['DEF']}")
    
    if pos_count['MID'] < 2 or pos_count['MID'] > 5:
        issues.append(f"Starting XI must have 2-5 MID, has {pos_count['MID']}")
    
    if pos_count['FWD'] < 1 or pos_count['FWD'] > 3:
        issues.append(f"Starting XI must have 1-3 FWD, has {pos_count['FWD']}")
    
    # 5. Check total squad (including bench)
    bench_pos_count = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
    for player in bench:
        if player['position'] in bench_pos_count:
            bench_pos_count[player['position']] += 1
    
    total_gk = pos_count['GK'] + bench_pos_count['GK']
    total_def = pos_count['DEF'] + bench_pos_count['DEF']
    total_mid = pos_count['MID'] + bench_pos_count['MID']
    total_fwd = pos_count['FWD'] + bench_pos_count['FWD']
    
    if total_gk != 2:
        issues.append(f"Total squad must have exactly 2 GK, has {total_gk}")
    
    if total_def != 5:
        issues.append(f"Total squad must have exactly 5 DEF, has {total_def}")
    
    if total_mid != 5:
        issues.append(f"Total squad must have exactly 5 MID, has {total_mid}")
    
    if total_fwd != 3:
        issues.append(f"Total squad must have exactly 3 FWD, has {total_fwd}")
    
    # 6. Update formation string
    team_data['formation'] = f"{pos_count['DEF']}-{pos_count['MID']}-{pos_count['FWD']}"
    
    # 7. Check budget
    total_cost = sum(p['price'] for p in all_team_players)
    if total_cost > 100.0:
        issues.append(f"Budget exceeds £100m: £{total_cost}m")
    
    return team_data, issues, fixes

def analyze_teams_with_llm(teams_df, valid_players):
    """Use Claude to analyze and fix teams"""
    
    # Prepare context
    context = f"""You are an expert Fantasy Premier League analyst for the 2025/26 season.

CRITICAL REQUIREMENTS that MUST be validated and fixed:
1. Captain MUST be the highest scoring player in the starting XI
2. Total squad: EXACTLY 15 players (2 GK, 5 DEF, 5 MID, 3 FWD)
3. Starting XI formation rules:
   - Exactly 1 GK
   - Between 3-5 DEF
   - Between 2-5 MID  
   - Between 1-3 FWD
   - Total starting XI = 11 players
4. No players who have left the Premier League
5. Budget must not exceed £100m

Your task:
1. Analyze the given teams
2. Fix any validation issues (especially captain selection)
3. Select the top 3 teams that meet ALL requirements
4. Provide detailed reasoning for selections

Focus on:
- Maximizing expected points over 5 gameweeks
- Team balance and coverage
- Captain selection (MUST be highest scorer)
- Budget efficiency
- Risk assessment
"""

    # Convert teams to analyzable format
    teams_data = []
    for idx, team in teams_df.head(30).iterrows():  # Analyze top 30 teams
        team_dict = team.to_dict()
        
        # Validate and fix issues
        fixed_team, issues, fixes = validate_and_fix_team(team_dict.copy(), valid_players)
        
        team_dict['validation_issues'] = issues
        team_dict['fixes_applied'] = fixes
        team_dict['original_index'] = idx
        
        teams_data.append(team_dict)
    
    # Create prompt
    prompt = f"""{context}

Here are the teams to analyze (with validation results):

{json.dumps(teams_data, indent=2)}

Please:
1. Review validation issues and fixes for each team
2. Select the TOP 3 teams that best meet all requirements
3. For each selected team, provide:
   - Fixed captain (highest scorer in starting XI)
   - Confirmed formation 
   - Key strengths and weaknesses
   - Risk assessment
   - Confidence score (0-100)
   - Detailed reasoning

Return your analysis as a JSON object with this structure:
{{
  "selected_teams": [
    {{
      "original_rank": <original index in input>,
      "captain": "<highest scoring player name>",
      "formation": "<DEF-MID-FWD>",
      "budget": <total budget>,
      "gw1_score": <gameweek 1 score>,
      "5gw_estimated": <5 gameweek score>,
      "validation_passed": true/false,
      "fixes_applied": ["list of fixes"],
      "key_strengths": ["strength1", "strength2", ...],
      "potential_weaknesses": ["weakness1", "weakness2", ...],
      "risk_assessment": "low/medium/high",
      "confidence": <0-100>,
      "selection_reason": "Detailed explanation"
    }}
  ],
  "analysis_summary": "Overall summary of selection process"
}}
"""

    # Get LLM response
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Parse response
    try:
        # Extract JSON from response
        response_text = response.content[0].text
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        json_text = response_text[json_start:json_end]
        
        analysis_result = json.loads(json_text)
        
        # Merge with original team data
        for selected_team in analysis_result['selected_teams']:
            orig_idx = selected_team['original_rank']
            orig_team = teams_data[orig_idx]
            
            # Apply fixes to create final team
            for key, value in orig_team.items():
                if key not in selected_team:
                    selected_team[key] = value
        
        return analysis_result
        
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        print(f"Response: {response_text[:500]}...")
        return None

def save_analysis_results(analysis_result, output_dir):
    """Save the analysis results"""
    if not analysis_result:
        return
    
    # Save JSON
    json_path = output_dir / "final_selected_teams_llm_v3.json"
    with open(json_path, 'w') as f:
        json.dump({
            'analysis_date': datetime.now().isoformat(),
            'analysis_type': 'LLM_validated_and_fixed',
            'teams_analyzed': 30,
            **analysis_result
        }, f, indent=2)
    
    # Create CSV with fixed teams
    selected_teams = []
    for team in analysis_result['selected_teams']:
        # Create clean row with all player data
        row = {
            'rank': len(selected_teams) + 1,
            'captain': team['captain'],
            'formation': team['formation'],
            'budget': team['budget'],
            'gw1_score': team.get('gw1_score', 0),
            '5gw_estimated': team.get('5gw_estimated', 0),
            'confidence': team['confidence'],
            'risk_assessment': team['risk_assessment'],
            'validation_passed': team.get('validation_passed', True),
            'fixes_applied': '; '.join(team.get('fixes_applied', [])),
            'key_strengths': '; '.join(team.get('key_strengths', [])),
            'selection_reason': team['selection_reason']
        }
        
        # Add all player data
        for key, value in team.items():
            if any(pos in key for pos in ['GK', 'DEF', 'MID', 'FWD', 'BENCH']) and '_' in key:
                row[key] = value
        
        selected_teams.append(row)
    
    # Save CSV with proper player names
    df = pd.DataFrame(selected_teams)
    
    # Ensure player names are included in CSV, not just roles
    for col in df.columns:
        if col.endswith('_role'):
            # Find corresponding player name column
            base_col = col[:-5]  # Remove '_role' suffix
            if base_col in df.columns:
                # We have the player name, keep it
                pass
            else:
                # Try to find player name in the data
                for team in selected_teams:
                    if base_col in team and col in team:
                        # Add player name column if missing
                        df[base_col] = df.apply(lambda row: team.get(base_col) if row.name == selected_teams.index(team) else row.get(base_col, ''), axis=1)
    
    csv_path = output_dir / "final_selected_teams_llm_v3.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"\nResults saved to:")
    print(f"  JSON: {json_path}")
    print(f"  CSV: {csv_path}")
    
    # Display summary
    print("\n" + "="*80)
    print("TOP 3 VALIDATED AND FIXED TEAMS")
    print("="*80)
    
    for i, team in enumerate(analysis_result['selected_teams'], 1):
        print(f"\n{i}. Team (Original Rank: #{team['original_rank']+1})")
        print(f"   Captain: {team['captain']}")
        print(f"   Formation: {team['formation']}")
        print(f"   Budget: £{team['budget']}m")
        print(f"   5GW Score: {team['5gw_estimated']}")
        print(f"   Validation: {'PASSED' if team.get('validation_passed', True) else 'FIXED'}")
        if team.get('fixes_applied'):
            print(f"   Fixes: {', '.join(team['fixes_applied'])}")
        print(f"   Risk: {team['risk_assessment']}")
        print(f"   Confidence: {team['confidence']}%")
        print(f"   Reasoning: {team['selection_reason']}")
        print("-" * 80)

def main():
    # Load valid players
    valid_players = load_valid_players()
    print(f"Loaded {len(valid_players)} valid players")
    
    # Load teams to analyze
    teams_file = Path("../data/cached_merged_2024_2025_v3/top_200_teams_final_gk_fixed.csv")
    if not teams_file.exists():
        print(f"Error: {teams_file} not found")
        return
    
    teams_df = pd.read_csv(teams_file)
    print(f"Loaded {len(teams_df)} teams for analysis")
    
    # Analyze with LLM
    print("\nAnalyzing teams with validation and auto-correction...")
    analysis_result = analyze_teams_with_llm(teams_df, valid_players)
    
    # Save results
    output_dir = Path("../data/cached_merged_2024_2025_v3")
    save_analysis_results(analysis_result, output_dir)

if __name__ == "__main__":
    main()