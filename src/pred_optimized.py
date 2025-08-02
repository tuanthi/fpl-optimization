import heapq
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass
from collections import defaultdict
import itertools

@dataclass
class Player:
    id: int
    score: float
    price: float
    role: str
    team: str = None  # Team/club name
    efficiency: float = None  # score/price ratio
    
    def __post_init__(self):
        if self.efficiency is None:
            self.efficiency = self.score / max(self.price, 0.1)
    
    def __repr__(self):
        return f"P{self.id}({self.role}, s={self.score:.1f}, p={self.price:.1f})"

class OptimizedFantasyOptimizer:
    def __init__(self, players: List[Player], budget: float):
        self.players = players
        self.budget = budget
        self.players_by_role = self._group_by_role()
        self.role_requirements_15 = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
        self.max_players_per_team = 3  # Maximum players from same team
        
    def _group_by_role(self) -> Dict[str, List[Player]]:
        """Group and sort players by role."""
        grouped = defaultdict(list)
        for player in self.players:
            grouped[player.role].append(player)
        
        # Sort by score (for greedy selection in 11-player subset)
        for role in grouped:
            grouped[role].sort(key=lambda p: p.score, reverse=True)
        
        return grouped
    
    def _estimate_min_cost_for_role(self, role: str, count: int) -> float:
        """Get minimum cost to fill a role requirement."""
        if count == 0:
            return 0
        players = self.players_by_role[role]
        if len(players) < count:
            return float('inf')
        # Get cheapest players for this role
        return sum(sorted(p.price for p in players)[:count])
    
    def _estimate_min_remaining_cost(self, selected_by_role: Dict[str, int]) -> float:
        """Estimate minimum cost to complete team from current state."""
        total = 0
        for role, required in self.role_requirements_15.items():
            needed = required - selected_by_role.get(role, 0)
            if needed > 0:
                total += self._estimate_min_cost_for_role(role, needed)
        return total
    
    def _find_best_11_from_15_optimized(self, team_15: List[Player]) -> Tuple[List[Player], float]:
        """Optimized version of finding best 11 from 15.
        Constraints: 1 GK, 3-5 DEF, at least 1 FWD, total 11 players."""
        by_role = defaultdict(list)
        for player in team_15:
            by_role[player.role].append(player)
        
        # Sort each role by score
        for role in by_role:
            by_role[role].sort(key=lambda p: p.score, reverse=True)
        
        best_score = -1
        best_11 = None
        
        # We need: 1 GK, 3-5 DEF, 0-4 MID, 1-3 FWD (total 11, at least 1 FWD)
        gk = by_role['GK'][0]  # Pick best GK
        
        # Try different formations
        for num_def in range(3, 6):  # 3-5 defenders
            if num_def > len(by_role['DEF']):
                continue
                
            remaining = 10 - num_def  # 11 - 1 GK - defenders
            
            for num_mid in range(0, min(remaining + 1, len(by_role['MID']) + 1)):
                num_fwd = remaining - num_mid
                
                if num_fwd < 1 or num_fwd > len(by_role['FWD']):  # Changed: num_fwd must be at least 1
                    continue
                
                # Select top players for each position
                team_11 = [gk]
                team_11.extend(by_role['DEF'][:num_def])
                team_11.extend(by_role['MID'][:num_mid])
                team_11.extend(by_role['FWD'][:num_fwd])
                
                score = sum(p.score for p in team_11)
                if score > best_score:
                    best_score = score
                    best_11 = team_11[:]
        
        return best_11, best_score
    
    def _generate_top_teams_beam_search(self, beam_width: int = 1000, max_results: int = 5000):
        """Use beam search to find top team combinations efficiently."""
        # State: (cost, team_players, counts_by_role)
        initial_state = (0.0, [], {role: 0 for role in self.role_requirements_15})
        beam = [initial_state]
        complete_teams = []
        
        # Build team role by role
        for role in ['GK', 'DEF', 'MID', 'FWD']:
            required = self.role_requirements_15[role]
            next_beam = []
            
            for cost, team, counts in beam:
                # Generate combinations for this role
                available = [p for p in self.players_by_role[role] if p not in team]
                
                if len(available) < required:
                    continue
                
                # Count current team composition
                team_counts = defaultdict(int)
                for p in team:
                    if p.team:
                        team_counts[p.team] += 1
                
                # For large numbers, sample combinations intelligently
                if len(available) > 20 and required > 3:
                    # Use top players by score and some by efficiency
                    top_by_score = sorted(available, key=lambda p: p.score, reverse=True)[:15]
                    top_by_efficiency = sorted(available, key=lambda p: p.efficiency, reverse=True)[:10]
                    candidates = list(set(top_by_score + top_by_efficiency))
                else:
                    candidates = available
                
                # Generate combinations
                for combo in itertools.combinations(candidates, required):
                    # Check team constraint
                    temp_team_counts = team_counts.copy()
                    valid_team_constraint = True
                    for p in combo:
                        if p.team:
                            temp_team_counts[p.team] += 1
                            if temp_team_counts[p.team] > self.max_players_per_team:
                                valid_team_constraint = False
                                break
                    
                    if not valid_team_constraint:
                        continue
                    
                    new_cost = cost + sum(p.price for p in combo)
                    
                    # Prune if over budget
                    if new_cost > self.budget:
                        continue
                    
                    # Estimate if we can complete the team within budget
                    new_counts = counts.copy()
                    new_counts[role] = required
                    min_remaining = self._estimate_min_remaining_cost(new_counts)
                    
                    if new_cost + min_remaining > self.budget:
                        continue
                    
                    new_team = team + list(combo)
                    next_beam.append((new_cost, new_team, new_counts))
            
            # Keep top entries by potential (could sort by score heuristic)
            if len(next_beam) > beam_width:
                # Sort by a heuristic: current average score of selected players
                next_beam.sort(key=lambda x: sum(p.score for p in x[1]) / max(len(x[1]), 1), reverse=True)
                next_beam = next_beam[:beam_width]
            
            beam = next_beam
            
            # If this was the last role, add to complete teams
            if role == 'FWD':
                complete_teams.extend([(team, cost) for cost, team, _ in beam])
        
        return complete_teams[:max_results]
    
    def find_top_combinations_optimized(self, top_k: int = 50) -> List[Dict]:
        """Find top K combinations using optimized beam search."""
        # Generate candidate teams
        candidate_teams = self._generate_top_teams_beam_search(beam_width=1000, max_results=5000)
        
        if not candidate_teams:
            return []
        
        # Evaluate each team
        results = []
        
        for team_15, total_price in candidate_teams:
            best_11, best_score = self._find_best_11_from_15_optimized(team_15)
            
            results.append({
                'team_15': team_15,
                'best_11': best_11,
                'best_11_score': best_score,
                'total_price': total_price,
                'price_margin': self.budget - total_price
            })
        
        # Sort by best 11 score
        results.sort(key=lambda x: x['best_11_score'], reverse=True)
        
        return results[:top_k]
    
    def print_results(self, results: List[Dict], top_k: int = 10):
        """Print results in a formatted way."""
        for i, result in enumerate(results[:top_k]):
            print(f"\n{'='*60}")
            print(f"Rank #{i+1}")
            print(f"Best 11 Score: {result['best_11_score']:.2f}")
            print(f"Budget Used: ${result['total_price']:.2f}/${self.budget} (Margin: ${result['price_margin']:.2f})")
            
            # Show best 11 formation
            formation = defaultdict(int)
            for p in result['best_11']:
                formation[p.role] += 1
            print(f"Formation: {formation['DEF']}-{formation['MID']}-{formation['FWD']}")
            
            print("\nBest 11 Players:")
            for role in ['GK', 'DEF', 'MID', 'FWD']:
                players = [p for p in result['best_11'] if p.role == role]
                if players:
                    print(f"  {role}: {', '.join(str(p) for p in players)}")
            
            print(f"\nBench (4 players):")
            bench = [p for p in result['team_15'] if p not in result['best_11']]
            for p in bench:
                print(f"  {p}")


# Performance comparison function
def compare_algorithms(players: List[Player], budget: float):
    """Compare performance of different optimization approaches."""
    import time
    
    print("="*60)
    print("Performance Comparison")
    print("="*60)
    
    # Optimized algorithm
    start = time.time()
    optimizer2 = OptimizedFantasyOptimizer(players, budget)
    results2 = optimizer2.find_top_combinations_optimized(top_k=50)
    time2 = time.time() - start
    
    print(f"\nOptimized Algorithm:")
    print(f"  Time: {time2:.2f} seconds")
    print(f"  Teams evaluated: ~5000 (beam search)")
    print(f"  Top team score: {results2[0]['best_11_score']:.2f}" if results2 else "No valid teams")
    
    return results2


# Example usage
if __name__ == "__main__":
    import random
    random.seed(42)
    
    # Generate 300 realistic players
    players = []
    player_id = 0
    
    # Role distribution matching typical fantasy sports
    role_counts = {'GK': 30, 'DEF': 100, 'MID': 100, 'FWD': 70}
    
    for role, count in role_counts.items():
        for _ in range(count):
            # Create realistic score/price relationships
            if role == 'GK':
                base_score = random.uniform(3, 5)
            elif role == 'DEF':
                base_score = random.uniform(3, 6)
            elif role == 'MID':
                base_score = random.uniform(3, 7)
            else:  # FWD
                base_score = random.uniform(4, 8)
            
            # Price loosely correlated with score
            price_factor = random.uniform(0.8, 1.5)
            noise = random.uniform(0.9, 1.1)
            
            player = Player(
                id=player_id,
                score=base_score * random.uniform(0.9, 1.1),
                price=base_score * price_factor * noise,
                role=role
            )
            players.append(player)
            player_id += 1
    
    # Set budget
    budget = 100.0
    
    print(f"Dataset: {len(players)} players")
    print(f"Budget: ${budget}")
    print(f"Constraints: 15 players (2 GK, 5 DEF, 5 MID, 3 FWD)")
    print(f"Best 11 must have: 1 GK, 3+ DEF, 1+ FWD")
    
    # Run optimized algorithm
    optimizer = OptimizedFantasyOptimizer(players, budget)
    results = optimizer.find_top_combinations_optimized(top_k=50)
    
    print(f"\nFound {len(results)} valid team combinations")
    optimizer.print_results(results, top_k=5)
    
    # Run performance comparison
    print("\n" + "="*60)
    compare_algorithms(players, budget)