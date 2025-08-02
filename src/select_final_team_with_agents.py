#!/usr/bin/env python3
"""
Select the best FPL team from top 200 candidates using AI agents
that analyze injury news, team news, and Scout recommendations.

Uses Tavily for web search and Anthropic for analysis.
"""

import os
import json
import pandas as pd
from typing import List, Dict, Tuple
from datetime import datetime
import asyncio
import aiohttp
from anthropic import Anthropic
from tavily import TavilyClient as Tavily
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class FPLNewsAgent:
    """Agent that searches for and analyzes FPL-related news"""
    
    def __init__(self, tavily_api_key: str):
        self.tavily = Tavily(api_key=tavily_api_key)
        self.sources = {
            'injury': 'https://www.premierinjuries.com/injury-table.php',
            'team_news': 'https://www.fantasyfootballscout.co.uk/team-news',
            'scout': 'https://www.fantasyfootballscout.co.uk/',
            'fpl_official': 'https://fantasy.premierleague.com/'
        }
    
    async def search_player_news(self, player_name: str, team: str) -> Dict:
        """Search for news about a specific player"""
        try:
            # Search for injury news
            injury_query = f"{player_name} {team} injury status Premier League"
            injury_results = self.tavily.search(
                query=injury_query,
                search_depth="advanced",
                max_results=5
            )
            
            # Search for team news
            team_query = f"{player_name} {team} team news starting lineup"
            team_results = self.tavily.search(
                query=team_query,
                search_depth="advanced", 
                max_results=5
            )
            
            return {
                'player': player_name,
                'team': team,
                'injury_news': injury_results.get('results', []),
                'team_news': team_results.get('results', [])
            }
        except Exception as e:
            print(f"Error searching news for {player_name}: {e}")
            return {
                'player': player_name,
                'team': team,
                'injury_news': [],
                'team_news': []
            }
    
    async def get_general_updates(self) -> Dict:
        """Get general FPL updates and Scout recommendations"""
        try:
            # Search for latest FPL Scout recommendations
            scout_query = "FPL Scout gameweek team selection recommendations"
            scout_results = self.tavily.search(
                query=scout_query,
                search_depth="advanced",
                max_results=10
            )
            
            # Search for general injury updates
            injury_query = "Premier League injury news suspended players gameweek"
            injury_results = self.tavily.search(
                query=injury_query,
                search_depth="advanced",
                max_results=10
            )
            
            return {
                'scout_recommendations': scout_results.get('results', []),
                'general_injuries': injury_results.get('results', [])
            }
        except Exception as e:
            print(f"Error getting general updates: {e}")
            return {
                'scout_recommendations': [],
                'general_injuries': []
            }


class FPLAnalysisAgent:
    """Agent that analyzes news and makes team recommendations"""
    
    def __init__(self, anthropic_api_key: str):
        self.client = Anthropic(api_key=anthropic_api_key)
    
    def analyze_player_fitness(self, player_news: Dict) -> Dict:
        """Analyze a player's fitness and availability"""
        
        prompt = f"""
        Analyze the following news about {player_news['player']} from {player_news['team']}:
        
        Injury News:
        {json.dumps(player_news['injury_news'], indent=2)}
        
        Team News:
        {json.dumps(player_news['team_news'], indent=2)}
        
        Based on this information, provide:
        1. Injury status (fit/doubtful/injured)
        2. Likelihood of starting (0-100%)
        3. Risk assessment (low/medium/high)
        4. Brief explanation
        
        Return as JSON with keys: status, start_probability, risk, explanation
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response
            content = response.content[0].text
            
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback if no JSON found
                return {
                    'status': 'unknown',
                    'start_probability': 50,
                    'risk': 'medium',
                    'explanation': 'Unable to determine from available information'
                }
                
        except Exception as e:
            print(f"Error analyzing player {player_news['player']}: {e}")
            return {
                'status': 'unknown',
                'start_probability': 50,
                'risk': 'medium', 
                'explanation': f'Analysis error: {str(e)}'
            }
    
    def select_best_teams(self, teams_df: pd.DataFrame, player_analyses: Dict, 
                         general_updates: Dict) -> List[Dict]:
        """Select the best teams based on all available information"""
        
        # Prepare team summaries for analysis
        team_summaries = []
        for idx, team in teams_df.head(20).iterrows():  # Analyze top 20 teams
            players = []
            
            # Extract all players from the team
            for col in teams_df.columns:
                if col.endswith('_selected') and team[col] == 1:
                    player_col = col.replace('_selected', '')
                    if player_col in teams_df.columns and pd.notna(team[player_col]):
                        player_info = team[player_col]
                        # Extract player name and team
                        if '(' in player_info and ')' in player_info:
                            name = player_info.split('(')[0].strip()
                            club = player_info.split('(')[1].replace(')', '').strip()
                            
                            # Get analysis if available
                            analysis = player_analyses.get(name, {
                                'status': 'not_analyzed',
                                'start_probability': 90,  # Default assumption
                                'risk': 'low'
                            })
                            
                            players.append({
                                'name': name,
                                'club': club,
                                'position': player_col[:3],
                                'analysis': analysis
                            })
            
            team_summaries.append({
                'index': idx,
                'captain': team['captain'],
                'formation': team['formation'],
                'score': team['gw1_score'],
                '5gw_score': team['5gw_estimated'],
                'players': players
            })
        
        # Use Claude to select best teams
        prompt = f"""
        Select the TOP 3 teams from these candidates based on injury news and team updates:
        
        Team Candidates:
        {json.dumps(team_summaries, indent=2)}
        
        General Updates:
        Scout Recommendations: {len(general_updates['scout_recommendations'])} articles
        Injury Updates: {len(general_updates['general_injuries'])} articles
        
        Consider:
        1. Player fitness and availability
        2. Risk of players not starting
        3. Overall team strength with available players
        4. Captain choice reliability
        
        Return a JSON array of the 3 best team indices with explanations.
        Format: [{"index": 0, "reason": "explanation"}, ...]
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            
            # Extract JSON array
            import re
            json_match = re.search(r'\[[^\]]+\]', content, re.DOTALL)
            if json_match:
                selections = json.loads(json_match.group())
                
                # Get the selected teams
                result = []
                for selection in selections[:3]:
                    team_idx = selection['index']
                    team_data = teams_df.iloc[team_idx].to_dict()
                    team_data['selection_reason'] = selection['reason']
                    team_data['team_rank'] = team_idx + 1
                    result.append(team_data)
                
                return result
            else:
                # Fallback to top 3 by score
                return [teams_df.iloc[i].to_dict() for i in range(3)]
                
        except Exception as e:
            print(f"Error selecting teams: {e}")
            # Fallback to top 3 by score
            return [teams_df.iloc[i].to_dict() for i in range(3)]


async def analyze_teams(teams_file: str, output_file: str):
    """Main function to analyze teams and select the best ones"""
    
    # Load API keys
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    tavily_key = os.getenv('TAVILY_API_KEY')
    
    if not anthropic_key or not tavily_key:
        raise ValueError("Missing API keys. Please set ANTHROPIC_API_KEY and TAVILY_API_KEY")
    
    # Initialize agents
    news_agent = FPLNewsAgent(tavily_key)
    analysis_agent = FPLAnalysisAgent(anthropic_key)
    
    # Load teams
    teams_df = pd.read_csv(teams_file)
    print(f"Loaded {len(teams_df)} teams for analysis")
    
    # Get general updates first
    print("\nFetching general FPL updates...")
    general_updates = await news_agent.get_general_updates()
    print(f"Found {len(general_updates['scout_recommendations'])} Scout recommendations")
    print(f"Found {len(general_updates['general_injuries'])} injury updates")
    
    # Analyze key players from top teams
    print("\nAnalyzing key players...")
    key_players = set()
    
    # Extract unique players from top 20 teams
    for idx, team in teams_df.head(20).iterrows():
        # Captain is always key
        if '(' in team['captain']:
            captain_name = team['captain'].split('(')[0].strip()
            captain_team = team['captain'].split('(')[1].replace(')', '').strip()
            key_players.add((captain_name, captain_team))
        
        # Also check high-value players
        for col in teams_df.columns:
            if col.endswith('_selected') and team[col] == 1:
                player_col = col.replace('_selected', '')
                score_col = col.replace('_selected', '_score')
                
                if (player_col in teams_df.columns and score_col in teams_df.columns and 
                    pd.notna(team[player_col]) and pd.notna(team[score_col])):
                    
                    if team[score_col] > 4.0:  # High scoring players
                        player_info = team[player_col]
                        if '(' in player_info and ')' in player_info:
                            name = player_info.split('(')[0].strip()
                            club = player_info.split('(')[1].replace(')', '').strip()
                            key_players.add((name, club))
    
    print(f"Analyzing {len(key_players)} key players...")
    
    # Search news for key players
    player_analyses = {}
    for i, (player_name, team) in enumerate(list(key_players)[:15]):  # Limit to top 15 to avoid rate limits
        print(f"  [{i+1}/{min(15, len(key_players))}] {player_name} ({team})")
        news = await news_agent.search_player_news(player_name, team)
        
        if news['injury_news'] or news['team_news']:
            analysis = analysis_agent.analyze_player_fitness(news)
            player_analyses[player_name] = analysis
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    # Select best teams
    print("\nSelecting best teams based on analysis...")
    best_teams = analysis_agent.select_best_teams(teams_df, player_analyses, general_updates)
    
    # Save results
    results = {
        'analysis_date': datetime.now().isoformat(),
        'teams_analyzed': len(teams_df),
        'players_analyzed': len(player_analyses),
        'player_analyses': player_analyses,
        'selected_teams': best_teams
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Also save a simplified CSV
    csv_output = output_file.replace('.json', '.csv')
    selected_df = pd.DataFrame(best_teams)
    selected_df.to_csv(csv_output, index=False)
    
    print(f"\nAnalysis complete!")
    print(f"Results saved to: {output_file}")
    print(f"Selected teams saved to: {csv_output}")
    
    # Display selected teams
    print("\n" + "="*80)
    print("TOP 3 RECOMMENDED TEAMS")
    print("="*80)
    
    for i, team in enumerate(best_teams):
        print(f"\n{i+1}. Team (Rank #{team.get('team_rank', i+1)})")
        print(f"   Captain: {team['captain']}")
        print(f"   Formation: {team['formation']}")
        print(f"   GW1 Score: {team['gw1_score']:.1f}")
        print(f"   5GW Score: {team['5gw_estimated']:.1f}")
        print(f"   Reason: {team.get('selection_reason', 'Top scoring team')}")
        print("-" * 80)


def main():
    """Entry point"""
    teams_file = "../data/cached_merged_2024_2025_v2/top_200_teams_final.csv"
    output_file = "../data/cached_merged_2024_2025_v2/final_selected_teams.json"
    
    # Run async function
    asyncio.run(analyze_teams(teams_file, output_file))


if __name__ == "__main__":
    main()