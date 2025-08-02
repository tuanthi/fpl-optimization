#!/usr/bin/env python3
"""
Enhanced FPL weekly sampling with role-specific Bradley-Terry models
"""

import pandas as pd
import numpy as np
from collections import defaultdict
import json
from pathlib import Path


def build_bradley_terry_matrices_with_roles(player_gw_df):
    """Build Bradley-Terry matrices for overall players, teams, and role-specific"""
    # Overall player comparisons
    player_comparisons = defaultdict(lambda: defaultdict(int))
    
    # Absolute points comparisons (uses score differences as weights)
    # Higher score differences indicate more dominant performances
    abs_comparisons = defaultdict(lambda: defaultdict(float))
    
    # Team comparisons
    team_comparisons = defaultdict(lambda: defaultdict(int))
    
    # Role-specific comparisons
    role_comparisons = {
        'GK': defaultdict(lambda: defaultdict(int)),
        'DEF': defaultdict(lambda: defaultdict(int)),
        'MID': defaultdict(lambda: defaultdict(int)),
        'FWD': defaultdict(lambda: defaultdict(int))
    }
    
    # Get player roles mapping
    player_roles = {}
    for _, row in player_gw_df.iterrows():
        player_id = row['player_id']
        role = row['role']
        player_roles[player_id] = role
    
    # Group by gameweek and match
    for gw in player_gw_df['gameweek'].unique():
        gw_data = player_gw_df[player_gw_df['gameweek'] == gw]
        
        # Group by match
        matches = gw_data.groupby(['team', 'opponent_team']).groups
        
        for (team_a, team_b), indices in matches.items():
            # Skip if not a valid match
            if team_a == team_b:
                continue
                
            # Get players from each team
            team_a_players = gw_data.loc[indices]
            team_b_players = gw_data[
                (gw_data['team'] == team_b) & 
                (gw_data['opponent_team'] == team_a)
            ]
            
            # Overall player comparisons
            for _, player_a in team_a_players.iterrows():
                for _, player_b in team_b_players.iterrows():
                    if player_a['total_points'] > player_b['total_points']:
                        player_comparisons[player_a['player_id']][player_b['player_id']] += 1
                        # Absolute points comparison - use score difference as weight
                        score_diff = player_a['total_points'] - player_b['total_points']
                        abs_comparisons[player_a['player_id']][player_b['player_id']] += score_diff
                    elif player_b['total_points'] > player_a['total_points']:
                        player_comparisons[player_b['player_id']][player_a['player_id']] += 1
                        # Absolute points comparison - use score difference as weight
                        score_diff = player_b['total_points'] - player_a['total_points']
                        abs_comparisons[player_b['player_id']][player_a['player_id']] += score_diff
                    
                    # Role-specific comparisons (only if same role)
                    role_a = player_roles.get(player_a['player_id'])
                    role_b = player_roles.get(player_b['player_id'])
                    
                    if role_a and role_b and role_a == role_b:
                        if player_a['total_points'] > player_b['total_points']:
                            role_comparisons[role_a][player_a['player_id']][player_b['player_id']] += 1
                        elif player_b['total_points'] > player_a['total_points']:
                            role_comparisons[role_b][player_b['player_id']][player_a['player_id']] += 1
            
            # Team comparisons
            team_a_points = team_a_players['total_points'].sum()
            team_b_points = team_b_players['total_points'].sum()
            
            if team_a_points > team_b_points:
                team_comparisons[team_a][team_b] += 1
            elif team_b_points > team_a_points:
                team_comparisons[team_b][team_a] += 1
    
    return player_comparisons, team_comparisons, role_comparisons, player_roles, abs_comparisons


def sigmoid(x, temperature=1.0):
    """Sigmoid function with temperature control"""
    return 1 / (1 + np.exp(-x * temperature))


def compute_hessian(comparisons, params, entities):
    """Compute Hessian matrix for Bradley-Terry model"""
    n = len(entities)
    entity_to_idx = {entity: i for i, entity in enumerate(entities)}
    hessian = np.zeros((n, n))
    
    # Compute second derivatives
    for i, entity_i in enumerate(entities):
        for j, entity_j in enumerate(entities):
            if i == j:
                # Diagonal elements
                diag_sum = 0
                
                # Contributions from wins
                if entity_i in comparisons:
                    for opponent, count in comparisons[entity_i].items():
                        if opponent in entity_to_idx:
                            pi = np.exp(params[entity_i])
                            pj = np.exp(params[opponent])
                            diag_sum += count * pi * pj / ((pi + pj) ** 2)
                
                # Contributions from losses
                for opponent in entities:
                    if opponent != entity_i and opponent in comparisons:
                        if entity_i in comparisons[opponent]:
                            count = comparisons[opponent][entity_i]
                            pi = np.exp(params[entity_i])
                            pj = np.exp(params[opponent])
                            diag_sum += count * pi * pj / ((pi + pj) ** 2)
                
                hessian[i, i] = -diag_sum
            else:
                # Off-diagonal elements
                if entity_i in comparisons and entity_j in comparisons[entity_i]:
                    count = comparisons[entity_i][entity_j]
                elif entity_j in comparisons and entity_i in comparisons[entity_j]:
                    count = comparisons[entity_j][entity_i]
                else:
                    count = 0
                
                if count > 0:
                    pi = np.exp(params[entity_i])
                    pj = np.exp(params[entity_j])
                    hessian[i, j] = count * pi * pj / ((pi + pj) ** 2)
    
    return hessian


def fit_bradley_terry_model_with_uncertainty(comparisons, max_iter=100, tol=1e-6, temperature=2.0):
    """Fit Bradley-Terry model with uncertainty estimation"""
    if not comparisons:
        return {}, {}
    
    # Get all entities
    entities = set()
    for winner in comparisons:
        entities.add(winner)
        entities.update(comparisons[winner].keys())
    
    entities = sorted(list(entities), key=str)
    n = len(entities)
    
    if n == 0:
        return {}, {}
    
    # Initialize parameters (log scale)
    params = {entity: 0.0 for entity in entities}
    
    # Fit model (same as before)
    for iteration in range(max_iter):
        old_params = params.copy()
        
        # Update each parameter
        for i, entity_i in enumerate(entities):
            numerator = 0
            denominator = 0
            
            # Wins by entity_i
            if entity_i in comparisons:
                for entity_j, count in comparisons[entity_i].items():
                    numerator += count
                    denominator += count / (np.exp(params[entity_i]) + np.exp(params[entity_j]))
            
            # Losses to entity_i
            for entity_j in entities:
                if entity_j != entity_i and entity_j in comparisons:
                    if entity_i in comparisons[entity_j]:
                        count = comparisons[entity_j][entity_i]
                        denominator += count / (np.exp(params[entity_j]) + np.exp(params[entity_i]))
            
            # Update parameter
            if denominator > 0:
                params[entity_i] = np.log(numerator / denominator) if numerator > 0 else -10
        
        # Check convergence
        max_change = max(abs(params[e] - old_params[e]) for e in entities)
        if max_change < tol:
            break
    
    # Compute uncertainties using Hessian
    hessian = compute_hessian(comparisons, params, entities)
    
    # Compute variance-covariance matrix
    uncertainties = {}
    try:
        # Add small regularization to ensure positive definite
        regularization = 1e-6 * np.eye(n)
        cov_matrix = np.linalg.inv(-hessian + regularization)
        variances = np.diag(cov_matrix)
        
        # Map back to entities
        for i, entity in enumerate(entities):
            uncertainties[entity] = np.sqrt(max(variances[i], 1e-10))
    except np.linalg.LinAlgError:
        # If inversion fails, use default uncertainty
        for entity in entities:
            uncertainties[entity] = 1.0
    
    # Convert to ratings
    ratings = {entity: np.exp(param) for entity, param in params.items()}
    
    # Apply sigmoid transformation with uncertainty weighting
    rating_values = np.array([ratings[e] for e in entities])
    uncertainty_values = np.array([uncertainties[e] for e in entities])
    
    # Normalize ratings
    if len(rating_values) > 1 and np.std(rating_values) > 0:
        normalized = (rating_values - np.mean(rating_values)) / np.std(rating_values)
    else:
        normalized = np.zeros_like(rating_values)
    
    # Apply sigmoid stretching
    stretched = sigmoid(normalized, temperature)
    
    # Weight by confidence (inverse uncertainty)
    weights = 1 / (1 + uncertainty_values)
    final_ratings = weights * stretched + (1 - weights) * 0.5
    
    # Map back to dictionary
    final_strengths = {entity: final_ratings[i] for i, entity in enumerate(entities)}
    
    # Normalize to sum to 1
    total = sum(final_strengths.values())
    if total > 0:
        final_strengths = {e: s/total for e, s in final_strengths.items()}
    
    return final_strengths, uncertainties


def fit_bradley_terry_model(comparisons, max_iter=100, tol=1e-6):
    """Backward compatible wrapper"""
    strengths, _ = fit_bradley_terry_model_with_uncertainty(comparisons, max_iter, tol)
    return strengths


def calculate_enhanced_predictions(player_gw_df, week_limit, cache_dir=None):
    """Calculate predictions with role-specific Bradley-Terry scores"""
    
    # Filter data
    train_df = player_gw_df[player_gw_df['gameweek'] <= week_limit].copy()
    
    print(f"Building Bradley-Terry matrices for weeks 1-{week_limit}...")
    player_comparisons, team_comparisons, role_comparisons, player_roles = \
        build_bradley_terry_matrices_with_roles(train_df)
    
    print("Fitting Bradley-Terry models...")
    
    # Fit overall models
    player_strengths = fit_bradley_terry_model(player_comparisons)
    team_strengths = fit_bradley_terry_model(team_comparisons)
    
    # Fit role-specific models
    role_strengths = {}
    for role, comparisons in role_comparisons.items():
        print(f"  Fitting {role} model...")
        role_strengths[role] = fit_bradley_terry_model(comparisons)
    
    # Calculate predictions
    predictions = []
    
    # Group by player to get summary stats
    player_stats = train_df.groupby(['player_id', 'first_name', 'last_name', 
                                     'team', 'role']).agg({
        'total_points': ['sum', 'mean', 'count'],
        'now_cost': 'last'
    }).reset_index()
    
    player_stats.columns = ['player_id', 'first_name', 'last_name', 'team', 
                           'role', 'total_points', 'avg_points', 'games', 'price']
    
    for _, player in player_stats.iterrows():
        player_id = player['player_id']
        team = player['team']
        role = player['role']
        
        # Get scores - scale based on actual performance
        base_score = player['avg_points']  # Use historical average as base
        
        # Adjust by Bradley-Terry strength (multiplicative factor)
        player_strength = player_strengths.get(player_id, 0.001)
        team_strength = team_strengths.get(team, 0.001)
        
        # Scale strengths to meaningful range (0.5 to 2.0 multiplier)
        player_multiplier = 0.5 + 1.5 * (player_strength / max(player_strengths.values())) if player_strengths else 1.0
        team_multiplier = 0.5 + 1.5 * (team_strength / max(team_strengths.values())) if team_strengths else 1.0
        
        # Calculate scores
        player_score = base_score * player_multiplier
        team_score = base_score * team_multiplier
        
        # Get role-specific score
        role_score = base_score
        if role in role_strengths and player_id in role_strengths[role]:
            role_strength = role_strengths[role][player_id]
            max_role_strength = max(role_strengths[role].values()) if role_strengths[role] else 1.0
            role_multiplier = 0.5 + 1.5 * (role_strength / max_role_strength)
            role_score = base_score * role_multiplier
        
        # Calculate weighted average: 1/3(player_score + 0.5*team_score + role_score)
        weighted_score = (player_score + 0.5 * team_score + role_score) / 3
        
        predictions.append({
            'player_id': player_id,
            'first_name': player['first_name'],
            'last_name': player['last_name'],
            'team': team,
            'role': role,
            'gameweek': week_limit + 1,
            'price': player['price'] / 10,  # Convert to millions
            'player_score': player_score,
            'team_score': team_score,
            'role_score': role_score,
            'weighted_score': weighted_score,
            'games_played': player['games'],
            'total_points': player['total_points'],
            'avg_points_historical': player['avg_points']
        })
    
    pred_df = pd.DataFrame(predictions)
    
    # Save models if cache_dir provided
    if cache_dir:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        # Save Bradley-Terry models
        bt_data = {
            'player_strengths': player_strengths,
            'team_strengths': team_strengths,
            'role_strengths': role_strengths,
            'player_roles': player_roles,
            'week_limit': week_limit
        }
        
        with open(cache_path / f'bradley_terry_models_week_{week_limit}.json', 'w') as f:
            json.dump(bt_data, f, indent=2)
        
        print(f"Saved Bradley-Terry models to {cache_path}")
    
    return pred_df


def main():
    import sys
    
    # Parse arguments
    if len(sys.argv) < 4:
        print("Usage: python fpl_week_sampling_with_roles.py <player_gameweek.csv> <output.csv> <week_limit> [cache_dir]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    week_limit = int(sys.argv[3])
    cache_dir = sys.argv[4] if len(sys.argv) > 4 else None
    
    # Load data
    print(f"Loading player gameweek data from {input_file}...")
    player_gw_df = pd.read_csv(input_file)
    
    # Add role information if not present
    if 'role' not in player_gw_df.columns:
        # Map element_type to role
        role_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
        player_gw_df['role'] = player_gw_df['element_type'].map(role_map)
    
    # Calculate predictions
    pred_df = calculate_enhanced_predictions(player_gw_df, week_limit, cache_dir)
    
    # Save results
    pred_df.to_csv(output_file, index=False)
    print(f"\nSaved predictions to {output_file}")
    print(f"Total players: {len(pred_df)}")
    print(f"\nRole distribution:")
    print(pred_df['role'].value_counts())
    
    # Show top players by weighted score
    print("\nTop 10 players by weighted score:")
    top_players = pred_df.nlargest(10, 'weighted_score')
    for _, p in top_players.iterrows():
        print(f"  {p['first_name']} {p['last_name']} ({p['team']}, {p['role']}): "
              f"£{p['price']:.1f}m, Score: {p['weighted_score']:.2f}")


if __name__ == "__main__":
    main()