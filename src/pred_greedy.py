import heapq
from itertools import combinations
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class Player:
    id: int
    score: float
    price: float
    role: str
    team: str = None  # Team/club name
    
    def __repr__(self):
        return f"Player({self.id}, {self.role}, score={self.score:.1f}, price={self.price:.1f})"

class FantasyTeamOptimizer:
    def __init__(self, players: List[Player], budget: float):
        self.players = players
        self.budget = budget
        self.players_by_role = self._group_by_role()
        self.max_players_per_team = 3  # Maximum players from same team
        
    def _group_by_role(self) -> Dict[str, List[Player]]:
        """Group players by their roles and sort by score/price ratio."""
        grouped = defaultdict(list)
        for player in self.players:
            grouped[player.role].append(player)
        
        # Sort each role group by score (descending) for better pruning
        for role in grouped:
            grouped[role].sort(key=lambda p: p.score, reverse=True)
        
        return grouped
    
    def _find_best_11_from_15(self, team_15: List[Player]) -> Tuple[List[Player], float]:
        """
        Find the best 11 players from a team of 15 that satisfies:
        - Exactly 1 GK
        - At least 3 DEF
        - At least 1 FWD
        - Maximum total score
        """
        # Group the 15 players by role
        by_role = defaultdict(list)
        for player in team_15:
            by_role[player.role].append(player)
        
        # We have 2 GK, need to pick 1
        # We have 5 DEF, need to pick 3-5
        # We have 5 MID, need to pick 0-4 (since we need at least 1 FWD)
        # We have 3 FWD, need to pick 1-3 (at least 1 required)
        # Total must be 11
        
        best_score = -1
        best_11 = None
        
        # Try each GK
        for gk in by_role['GK']:
            # Try different numbers of DEF (3-5)
            for num_def in range(3, min(6, len(by_role['DEF']) + 1)):
                # Calculate remaining spots
                remaining_spots = 11 - 1 - num_def  # 11 - GK - DEF
                
                # Try different combinations of MID and FWD
                max_mid = min(len(by_role['MID']), remaining_spots)
                max_fwd = min(len(by_role['FWD']), remaining_spots)
                
                for num_mid in range(0, max_mid + 1):
                    num_fwd = remaining_spots - num_mid
                    if num_fwd > max_fwd or num_fwd < 1:  # Changed: num_fwd must be at least 1
                        continue
                    
                    # Select best players for each position
                    # Since we sorted by score, we can just take the top N
                    selected_def = sorted(by_role['DEF'], key=lambda p: p.score, reverse=True)[:num_def]
                    selected_mid = sorted(by_role['MID'], key=lambda p: p.score, reverse=True)[:num_mid]
                    selected_fwd = sorted(by_role['FWD'], key=lambda p: p.score, reverse=True)[:num_fwd]
                    
                    team_11 = [gk] + selected_def + selected_mid + selected_fwd
                    total_score = sum(p.score for p in team_11)
                    
                    if total_score > best_score:
                        best_score = total_score
                        best_11 = team_11
        
        return best_11, best_score
    
    def _generate_valid_15_teams(self, max_teams: int = 10000) -> List[Tuple[List[Player], float]]:
        """
        Generate valid 15-player teams using a branch-and-bound approach.
        Returns list of (team, total_price) tuples.
        """
        valid_teams = []
        
        # Required: 2 GK, 5 DEF, 5 MID, 3 FWD
        required = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
        
        # Use combinations for each role
        gk_combos = list(combinations(self.players_by_role['GK'], required['GK']))
        def_combos = list(combinations(self.players_by_role['DEF'], required['DEF']))
        mid_combos = list(combinations(self.players_by_role['MID'], required['MID']))
        fwd_combos = list(combinations(self.players_by_role['FWD'], required['FWD']))
        
        # Early termination if we can't form valid teams
        if not (gk_combos and def_combos and mid_combos and fwd_combos):
            return []
        
        # Generate all combinations
        count = 0
        for gks in gk_combos:
            gk_price = sum(p.price for p in gks)
            if gk_price > self.budget:
                continue
                
            for defs in def_combos:
                def_price = sum(p.price for p in defs)
                if gk_price + def_price > self.budget:
                    continue
                    
                for mids in mid_combos:
                    mid_price = sum(p.price for p in mids)
                    if gk_price + def_price + mid_price > self.budget:
                        continue
                        
                    for fwds in fwd_combos:
                        total_price = gk_price + def_price + mid_price + sum(p.price for p in fwds)
                        if total_price <= self.budget:
                            team = list(gks) + list(defs) + list(mids) + list(fwds)
                            
                            # Check team constraint
                            team_counts = defaultdict(int)
                            for p in team:
                                if p.team:
                                    team_counts[p.team] += 1
                            
                            # Check if any team has more than max_players_per_team
                            if all(count <= self.max_players_per_team for count in team_counts.values()):
                                valid_teams.append((team, total_price))
                                count += 1
                                if count >= max_teams:
                                    return valid_teams
        
        return valid_teams
    
    def find_top_combinations(self, top_k: int = 50) -> List[Dict]:
        """
        Find the top K team combinations.
        Returns a list of dictionaries containing team info.
        """
        # Generate valid 15-player teams
        valid_15_teams = self._generate_valid_15_teams(max_teams=10000)
        
        if not valid_15_teams:
            return []
        
        # Evaluate each team
        team_evaluations = []
        
        for team_15, total_price in valid_15_teams:
            best_11, best_score = self._find_best_11_from_15(team_15)
            
            team_evaluations.append({
                'team_15': team_15,
                'best_11': best_11,
                'best_11_score': best_score,
                'total_price': total_price,
                'price_margin': self.budget - total_price
            })
        
        # Sort by best_11_score (descending)
        team_evaluations.sort(key=lambda x: x['best_11_score'], reverse=True)
        
        # Return top K
        return team_evaluations[:top_k]
    
    def print_top_combinations(self, top_k: int = 10):
        """Print the top K combinations in a readable format."""
        results = self.find_top_combinations(top_k)
        
        for i, result in enumerate(results):
            print(f"\n{'='*60}")
            print(f"Rank #{i+1}")
            print(f"Best 11 Score: {result['best_11_score']:.2f}")
            print(f"Total Price: {result['total_price']:.2f} (Budget: {self.budget}, Margin: {result['price_margin']:.2f})")
            
            print("\n15-Player Squad:")
            for role in ['GK', 'DEF', 'MID', 'FWD']:
                role_players = [p for p in result['team_15'] if p.role == role]
                print(f"  {role}: {', '.join(f'P{p.id}(${p.price:.1f}, {p.score:.1f})' for p in role_players)}")
            
            print("\nBest 11 Selection (1 GK, 3+ DEF, 1+ FWD):")
            for role in ['GK', 'DEF', 'MID', 'FWD']:
                role_players = [p for p in result['best_11'] if p.role == role]
                if role_players:
                    print(f"  {role}: {', '.join(f'P{p.id}(${p.price:.1f}, {p.score:.1f})' for p in role_players)}")
            
            # Show formation
            formation = defaultdict(int)
            for p in result['best_11']:
                formation[p.role] += 1
            formation_str = f"{formation['DEF']}-{formation['MID']}-{formation['FWD']}"
            print(f"\nFormation: {formation_str}")


# Example usage and testing
if __name__ == "__main__":
    import random
    random.seed(42)
    
    # Generate sample players
    players = []
    player_id = 0
    
    # Generate players for each role
    role_counts = {'GK': 30, 'DEF': 100, 'MID': 100, 'FWD': 70}
    
    for role, count in role_counts.items():
        for _ in range(count):
            # Create realistic score/price relationships
            base_score = random.uniform(3, 8)
            price_factor = random.uniform(0.8, 1.5)
            
            player = Player(
                id=player_id,
                score=base_score * random.uniform(0.8, 1.2),
                price=base_score * price_factor * random.uniform(0.9, 1.1),
                role=role
            )
            players.append(player)
            player_id += 1
    
    # Create optimizer
    budget = 100.0
    optimizer = FantasyTeamOptimizer(players, budget)
    
    # Find and print top combinations
    print(f"Total players: {len(players)}")
    print(f"Budget: ${budget}")
    print("\nFinding top team combinations...")
    
    optimizer.print_top_combinations(top_k=5)