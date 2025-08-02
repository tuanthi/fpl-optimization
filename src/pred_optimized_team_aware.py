from typing import List, Tuple, Dict
from dataclasses import dataclass
from collections import defaultdict
import itertools

@dataclass(frozen=True)  # Make it hashable
class Player:
    id: int
    score: float
    price: float
    role: str
    team: str = None  # Team/club name
    efficiency: float = None  # score/price ratio
    
    def __post_init__(self):
        if self.efficiency is None:
            # Use object.__setattr__ because dataclass is frozen
            object.__setattr__(self, 'efficiency', self.score / max(self.price, 0.1))
    
    def __repr__(self):
        return f"P{self.id}({self.role}, s={self.score:.1f}, p={self.price:.1f})"

class TeamAwareOptimizer:
    def __init__(self, players: List[Player], budget: float):
        self.players = players
        self.budget = budget
        self.players_by_role = self._group_by_role()
        self.players_by_team = self._group_by_team()
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
    
    def _group_by_team(self) -> Dict[str, List[Player]]:
        """Group players by team."""
        grouped = defaultdict(list)
        for player in self.players:
            if player.team:
                grouped[player.team].append(player)
        return grouped
    
    def _find_best_11_from_15_optimized(self, team_15: List[Player]) -> Tuple[List[Player], float]:
        """Find best 11 from 15 players."""
        by_role = defaultdict(list)
        for player in team_15:
            by_role[player.role].append(player)
        
        # Sort each role by score
        for role in by_role:
            by_role[role].sort(key=lambda p: p.score, reverse=True)
        
        best_score = -1
        best_11 = None
        
        # We need: 1 GK, 3-5 DEF, 0-4 MID, 1-3 FWD (total 11, at least 1 FWD)
        if not by_role['GK'] or len(by_role['GK']) < 1:
            return None, -1
        gk = by_role['GK'][0]  # Pick best GK
        
        # Try different formations
        for num_def in range(3, 6):  # 3-5 defenders
            if num_def > len(by_role['DEF']):
                continue
                
            remaining = 10 - num_def  # 11 - 1 GK - defenders
            
            for num_mid in range(0, min(remaining + 1, len(by_role['MID']) + 1)):
                num_fwd = remaining - num_mid
                
                if num_fwd < 1 or num_fwd > len(by_role['FWD']):
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
    
    def _generate_diverse_combinations(self, role: str, count: int, excluded_players: set, 
                                     team_counts: Dict[str, int]) -> List[List[Player]]:
        """Generate combinations that respect team constraints."""
        available = [p for p in self.players_by_role[role] if p not in excluded_players]
        
        if len(available) < count:
            return []
        
        # Group available players by team
        by_team = defaultdict(list)
        for p in available:
            by_team[p.team if p.team else 'NoTeam'].append(p)
        
        # Sort teams by how many slots they have available
        team_slots = []
        for team, players in by_team.items():
            current_count = team_counts.get(team, 0)
            available_slots = self.max_players_per_team - current_count
            if available_slots > 0:
                team_slots.append((team, players, available_slots))
        
        # Sort by number of high-quality players
        team_slots.sort(key=lambda x: sum(p.score for p in x[1][:3]), reverse=True)
        
        # Try to build combinations that respect team limits
        valid_combinations = []
        
        # Strategy: Try different distributions across teams
        def build_combinations(remaining_count, team_idx, current_combo, current_team_counts):
            if remaining_count == 0:
                valid_combinations.append(current_combo[:])
                return
            
            if team_idx >= len(team_slots):
                return
            
            team, players, max_from_team = team_slots[team_idx]
            current_from_team = current_team_counts.get(team, 0)
            can_take = min(remaining_count, len(players), max_from_team)
            
            # Try taking different numbers from this team
            for take in range(0, can_take + 1):
                if take == 0:
                    # Skip this team
                    build_combinations(remaining_count, team_idx + 1, current_combo, current_team_counts)
                else:
                    # Take top 'take' players from this team
                    for combo in itertools.combinations(players[:min(len(players), take + 2)], take):
                        new_combo = current_combo + list(combo)
                        new_counts = current_team_counts.copy()
                        new_counts[team] = current_from_team + take
                        build_combinations(remaining_count - take, team_idx + 1, new_combo, new_counts)
                        
                        if len(valid_combinations) >= 100:  # Limit combinations
                            return
        
        build_combinations(count, 0, [], team_counts)
        
        # If we don't have enough valid combinations, fall back to score-based selection
        if len(valid_combinations) < 10:
            # Sort all available players by score
            available.sort(key=lambda p: p.score, reverse=True)
            
            # Try to build teams greedily while respecting constraints
            for _ in range(20):  # Try 20 different starting points
                combo = []
                temp_counts = team_counts.copy()
                
                for player in available:
                    if len(combo) >= count:
                        break
                    
                    player_team = player.team if player.team else 'NoTeam'
                    if temp_counts.get(player_team, 0) < self.max_players_per_team:
                        combo.append(player)
                        temp_counts[player_team] = temp_counts.get(player_team, 0) + 1
                
                if len(combo) == count and combo not in valid_combinations:
                    valid_combinations.append(combo)
        
        return valid_combinations[:50]  # Return top 50 combinations
    
    def find_top_teams_with_constraint(self, top_k: int = 50) -> List[Dict]:
        """Find top teams respecting the team constraint."""
        results = []
        
        # Try different team compositions
        print("Building teams with team constraint...")
        
        # Start with goalkeepers
        gk_combos = self._generate_diverse_combinations('GK', 2, set(), {})
        
        for gk_combo in gk_combos[:20]:  # Try top 20 GK combinations
            gk_cost = sum(p.price for p in gk_combo)
            if gk_cost > self.budget * 0.15:  # Don't spend more than 15% on GKs
                continue
            
            # Count teams
            team_counts = defaultdict(int)
            for p in gk_combo:
                if p.team:
                    team_counts[p.team] += 1
            
            # Try defenders
            def_combos = self._generate_diverse_combinations('DEF', 5, set(gk_combo), team_counts)
            
            for def_combo in def_combos[:10]:
                def_cost = sum(p.price for p in def_combo)
                if gk_cost + def_cost > self.budget * 0.55:  # Don't spend more than 55% on GK+DEF
                    continue
                
                # Update team counts
                team_counts_def = team_counts.copy()
                for p in def_combo:
                    if p.team:
                        team_counts_def[p.team] += 1
                
                # Try midfielders
                mid_combos = self._generate_diverse_combinations('MID', 5, set(gk_combo + def_combo), team_counts_def)
                
                for mid_combo in mid_combos[:5]:
                    mid_cost = sum(p.price for p in mid_combo)
                    if gk_cost + def_cost + mid_cost > self.budget * 0.85:
                        continue
                    
                    # Update team counts
                    team_counts_mid = team_counts_def.copy()
                    for p in mid_combo:
                        if p.team:
                            team_counts_mid[p.team] += 1
                    
                    # Try forwards
                    fwd_combos = self._generate_diverse_combinations('FWD', 3, set(gk_combo + def_combo + mid_combo), team_counts_mid)
                    
                    for fwd_combo in fwd_combos[:3]:
                        total_cost = gk_cost + def_cost + mid_cost + sum(p.price for p in fwd_combo)
                        
                        if total_cost <= self.budget:
                            team_15 = gk_combo + def_combo + mid_combo + fwd_combo
                            best_11, best_score = self._find_best_11_from_15_optimized(team_15)
                            
                            results.append({
                                'team_15': team_15,
                                'best_11': best_11,
                                'best_11_score': best_score,
                                'total_price': total_cost,
                                'price_margin': self.budget - total_cost
                            })
                            
                            if len(results) >= top_k * 2:
                                # Sort and return top K
                                results.sort(key=lambda x: x['best_11_score'], reverse=True)
                                return results[:top_k]
        
        # Sort by best 11 score
        results.sort(key=lambda x: x['best_11_score'], reverse=True)
        return results[:top_k]