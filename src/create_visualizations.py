#!/usr/bin/env python3
"""
Create comprehensive visualizations for FPL optimization analysis
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def load_data():
    """Load all necessary data files"""
    data_path = Path("../data/cached_merged_2024_2025_v2")
    
    # Load predictions
    predictions = pd.read_csv(data_path / "predictions_gw39_proper_v4.csv")
    
    # Load top teams
    top_teams = pd.read_csv(data_path / "top_200_teams_final_v8.csv")
    
    # Load team scores
    with open(data_path / "bradley_terry_models_week_38.json", 'r') as f:
        bradley_terry_data = json.load(f)
        team_scores = bradley_terry_data['team_strengths']
        # Filter out numeric keys (team IDs) and keep only team names
        team_scores = {k: v for k, v in team_scores.items() if not k.isdigit()}
    
    # Load final recommendations
    final_teams = pd.read_csv(data_path / "final_recommended_teams_v1.csv")
    
    return predictions, top_teams, team_scores, final_teams


def create_player_score_distribution(predictions, output_dir):
    """Create histogram of player score distributions by position"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Player Score Distribution by Position', fontsize=16, fontweight='bold')
    
    positions = ['GK', 'DEF', 'MID', 'FWD']
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    
    for idx, (pos, ax) in enumerate(zip(positions, axes.flatten())):
        pos_data = predictions[predictions['role'] == pos]['weighted_score']
        
        # Create histogram
        n, bins, patches = ax.hist(pos_data, bins=30, alpha=0.7, color=colors[idx], edgecolor='black')
        
        # Add statistics
        mean_score = pos_data.mean()
        median_score = pos_data.median()
        
        ax.axvline(mean_score, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_score:.2f}')
        ax.axvline(median_score, color='green', linestyle='--', linewidth=2, label=f'Median: {median_score:.2f}')
        
        # Labeling
        ax.set_title(f'{pos} Score Distribution', fontsize=14, fontweight='bold')
        ax.set_xlabel('Weighted Score', fontsize=12)
        ax.set_ylabel('Number of Players', fontsize=12)
        ax.legend()
        
        # Add text box with stats
        textstr = f'Count: {len(pos_data)}\nStd: {pos_data.std():.2f}'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=props)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'player_score_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_team_strength_ranking(team_scores, output_dir):
    """Create horizontal bar chart of team strength rankings"""
    # Sort teams by score
    sorted_teams = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)[:20]
    
    fig, ax = plt.subplots(figsize=(10, 12))
    
    teams = [team for team, _ in sorted_teams]
    scores = [score for _, score in sorted_teams]
    
    # Create color gradient
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(teams)))
    
    # Create horizontal bar chart
    bars = ax.barh(teams, scores, color=colors, edgecolor='black', linewidth=0.5)
    
    # Add value labels
    for bar, score in zip(bars, scores):
        ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2, 
                f'{score:.3f}', ha='left', va='center', fontweight='bold')
    
    ax.set_xlabel('Bradley-Terry Team Strength Score', fontsize=14, fontweight='bold')
    ax.set_title('Premier League Team Strength Rankings (2024/25)', fontsize=16, fontweight='bold')
    ax.set_xlim(0, max(scores) * 1.1)
    
    # Add grid
    ax.grid(axis='x', alpha=0.3)
    
    # Invert y-axis to have best team at top
    ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(output_dir / 'team_strength_rankings.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_formation_analysis(top_teams, output_dir):
    """Create pie chart and bar chart of formation preferences"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Count formations
    formation_counts = top_teams['formation'].value_counts()
    
    # Pie chart
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFA07A']
    wedges, texts, autotexts = ax1.pie(formation_counts.values, labels=formation_counts.index, 
                                        autopct='%1.1f%%', colors=colors, startangle=90)
    
    # Make percentage text bold
    for autotext in autotexts:
        autotext.set_fontweight('bold')
        autotext.set_fontsize(12)
    
    ax1.set_title('Formation Distribution in Top 200 Teams', fontsize=14, fontweight='bold')
    
    # Bar chart with average scores
    formation_scores = top_teams.groupby('formation')['5gw_estimated'].agg(['mean', 'std', 'count'])
    
    x = range(len(formation_scores))
    ax2.bar(x, formation_scores['mean'], yerr=formation_scores['std'], 
            color=colors[:len(formation_scores)], capsize=10, edgecolor='black', linewidth=1)
    
    ax2.set_xticks(x)
    ax2.set_xticklabels(formation_scores.index, fontsize=12)
    ax2.set_ylabel('Average 5GW Projected Score', fontsize=12, fontweight='bold')
    ax2.set_title('Average Score by Formation', fontsize=14, fontweight='bold')
    
    # Add count labels on bars
    for i, (idx, row) in enumerate(formation_scores.iterrows()):
        ax2.text(i, row['mean'] + row['std'] + 0.5, f"n={row['count']}", 
                ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'formation_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_captain_analysis(predictions, top_teams, output_dir):
    """Create visualization of captain selections"""
    # Get captain counts
    captain_counts = top_teams['captain'].value_counts().head(10)
    
    # Get captain scores
    captain_scores = {}
    for captain in captain_counts.index:
        player_data = predictions[predictions['full_name'] == captain]
        if not player_data.empty:
            captain_scores[captain] = player_data.iloc[0]['weighted_score']
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Bar chart of captain selections
    colors = plt.cm.viridis(np.linspace(0, 1, len(captain_counts)))
    bars1 = ax1.bar(range(len(captain_counts)), captain_counts.values, color=colors, edgecolor='black')
    
    ax1.set_xticks(range(len(captain_counts)))
    ax1.set_xticklabels(captain_counts.index, rotation=45, ha='right')
    ax1.set_ylabel('Number of Teams', fontsize=12, fontweight='bold')
    ax1.set_title('Most Popular Captain Choices', fontsize=14, fontweight='bold')
    
    # Add count labels
    for bar, count in zip(bars1, captain_counts.values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                str(count), ha='center', va='bottom', fontweight='bold')
    
    # Scatter plot of captain score vs selection frequency
    if captain_scores:
        captains = list(captain_scores.keys())
        scores = list(captain_scores.values())
        frequencies = [captain_counts.get(c, 0) for c in captains]
        
        scatter = ax2.scatter(scores, frequencies, s=200, c=scores, cmap='coolwarm', 
                            edgecolor='black', linewidth=2, alpha=0.7)
        
        # Add player names
        for i, captain in enumerate(captains):
            ax2.annotate(captain.split()[0], (scores[i], frequencies[i]), 
                        xytext=(5, 5), textcoords='offset points', fontsize=10)
        
        ax2.set_xlabel('Player Weighted Score', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Selection Frequency', fontsize=12, fontweight='bold')
        ax2.set_title('Captain Score vs Selection Frequency', fontsize=14, fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax2)
        cbar.set_label('Player Score', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'captain_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_price_value_analysis(predictions, output_dir):
    """Create scatter plot of price vs value (points per million)"""
    # Calculate points per million
    predictions['points_per_million'] = predictions['weighted_score'] / predictions['price']
    
    # Filter valid players (those who made it to teams)
    valid_players = predictions[predictions['weighted_score'] > 2.0].copy()
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Create scatter plot by position
    positions = ['GK', 'DEF', 'MID', 'FWD']
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    markers = ['o', 's', 'D', '^']
    
    for pos, color, marker in zip(positions, colors, markers):
        pos_data = valid_players[valid_players['role'] == pos]
        ax.scatter(pos_data['price'], pos_data['points_per_million'], 
                  c=color, s=100, alpha=0.6, label=pos, marker=marker, edgecolor='black', linewidth=0.5)
    
    # Highlight top value picks
    top_value = valid_players.nlargest(10, 'points_per_million')
    for _, player in top_value.iterrows():
        ax.annotate(player['full_name'].split()[-1], 
                   (player['price'], player['points_per_million']),
                   xytext=(5, 5), textcoords='offset points', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    ax.set_xlabel('Price (£m)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Points per Million', fontsize=14, fontweight='bold')
    ax.set_title('Player Value Analysis: Price vs Points per Million', fontsize=16, fontweight='bold')
    ax.legend(title='Position', title_fontsize=12, fontsize=11, loc='upper right')
    ax.grid(alpha=0.3)
    
    # Add trend line
    z = np.polyfit(valid_players['price'], valid_players['points_per_million'], 2)
    p = np.poly1d(z)
    x_trend = np.linspace(valid_players['price'].min(), valid_players['price'].max(), 100)
    ax.plot(x_trend, p(x_trend), 'r--', alpha=0.8, linewidth=2, label='Trend')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'price_value_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_team_composition_heatmap(final_teams, predictions, output_dir):
    """Create heatmap showing player selection across recommended teams"""
    # Extract all players from the three teams
    player_data = []
    
    for idx, team in final_teams.iterrows():
        team_players = []
        positions = ['GK', 'DEF', 'MID', 'FWD']
        
        for pos in positions:
            for i in range(1, 6):  # Max 5 per position
                player_col = f'{pos}{i}'
                if player_col in team.index and pd.notna(team[player_col]) and team[player_col]:
                    player_name = team[player_col]
                    # Get player score
                    player_info = predictions[predictions['full_name'] == player_name]
                    if not player_info.empty:
                        score = player_info.iloc[0]['weighted_score']
                        player_data.append({
                            'Team': f"Team {idx+1}",
                            'Player': player_name.split('(')[0].strip(),
                            'Position': pos,
                            'Score': score,
                            'Selected': 1 if team.get(f'{player_col}_selected', 0) == 1 else 0.3
                        })
    
    # Create pivot table
    df = pd.DataFrame(player_data)
    if len(df) > 0:
        pivot = df.pivot_table(values='Selected', index='Player', columns='Team', aggfunc='first', fill_value=0)
    else:
        # Create empty pivot table if no data
        pivot = pd.DataFrame()
    
    # Sort by total selection
    pivot['Total'] = pivot.sum(axis=1)
    pivot = pivot.sort_values('Total', ascending=False).drop('Total', axis=1)
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(8, 12))
    
    # Custom colormap
    colors = ['white', 'lightblue', 'darkblue']
    n_bins = 3
    cmap = sns.blend_palette(colors, n_colors=n_bins, as_cmap=True)
    
    sns.heatmap(pivot, annot=False, cmap=cmap, cbar_kws={'label': 'Selection Status'}, 
                linewidths=0.5, linecolor='gray', ax=ax)
    
    ax.set_title('Player Selection Across Recommended Teams', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Team', fontsize=12, fontweight='bold')
    ax.set_ylabel('Player', fontsize=12, fontweight='bold')
    
    # Rotate labels
    plt.setp(ax.get_xticklabels(), rotation=0)
    plt.setp(ax.get_yticklabels(), rotation=0, fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'team_composition_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_score_projection_comparison(top_teams, output_dir):
    """Create box plot comparing score projections by different factors"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Score distribution by formation
    formations = top_teams['formation'].unique()
    data_by_formation = [top_teams[top_teams['formation'] == f]['5gw_estimated'] for f in formations]
    
    bp1 = ax1.boxplot(data_by_formation, labels=formations, patch_artist=True)
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFA07A']
    for patch, color in zip(bp1['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax1.set_ylabel('5GW Projected Score', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Formation', fontsize=12, fontweight='bold')
    ax1.set_title('Score Distribution by Formation', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    
    # Score vs budget spent
    ax2.scatter(top_teams['budget'], top_teams['5gw_estimated'], 
                alpha=0.6, s=50, c=top_teams['5gw_estimated'], cmap='viridis', edgecolor='black', linewidth=0.5)
    
    # Add trend line
    z = np.polyfit(top_teams['budget'], top_teams['5gw_estimated'], 1)
    p = np.poly1d(z)
    ax2.plot(top_teams['budget'], p(top_teams['budget']), 'r--', linewidth=2, alpha=0.8)
    
    ax2.set_xlabel('Budget Used (£m)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('5GW Projected Score', fontsize=12, fontweight='bold')
    ax2.set_title('Projected Score vs Budget Used', fontsize=14, fontweight='bold')
    ax2.grid(alpha=0.3)
    
    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap='viridis', norm=plt.Normalize(vmin=top_teams['5gw_estimated'].min(), 
                                                                   vmax=top_teams['5gw_estimated'].max()))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax2)
    cbar.set_label('5GW Score', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'score_projection_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_summary_dashboard(predictions, top_teams, team_scores, final_teams, output_dir):
    """Create a comprehensive summary dashboard"""
    fig = plt.figure(figsize=(20, 16))
    
    # Create grid
    gs = fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)
    
    # 1. Top players by position
    ax1 = fig.add_subplot(gs[0, :2])
    positions = ['GK', 'DEF', 'MID', 'FWD']
    colors_pos = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    
    for i, (pos, color) in enumerate(zip(positions, colors_pos)):
        top_pos = predictions[predictions['role'] == pos].nlargest(3, 'weighted_score')
        y_positions = [i * 3 + j for j in range(len(top_pos))]
        bars = ax1.barh(y_positions, top_pos['weighted_score'], color=color, alpha=0.7, edgecolor='black')
        
        for bar, (_, player) in zip(bars, top_pos.iterrows()):
            ax1.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                    f"{player['full_name'].split('(')[0]} (£{player['price']}m)",
                    va='center', fontsize=10)
    
    ax1.set_yticks([i * 3 + 1 for i in range(4)])
    ax1.set_yticklabels(positions)
    ax1.set_xlabel('Weighted Score', fontsize=12, fontweight='bold')
    ax1.set_title('Top 3 Players by Position', fontsize=14, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)
    
    # 2. Team strength top 10
    ax2 = fig.add_subplot(gs[0, 2])
    top_10_teams = sorted(team_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    teams = [t[0] for t in top_10_teams]
    scores = [t[1] for t in top_10_teams]
    
    bars = ax2.barh(range(len(teams)), scores, color=plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(teams))))
    ax2.set_yticks(range(len(teams)))
    ax2.set_yticklabels(teams, fontsize=9)
    ax2.set_xlabel('Bradley-Terry Score', fontsize=10)
    ax2.set_title('Top 10 Team Strengths', fontsize=12, fontweight='bold')
    ax2.invert_yaxis()
    
    # 3. Formation pie chart
    ax3 = fig.add_subplot(gs[1, 0])
    formation_counts = top_teams['formation'].value_counts()
    ax3.pie(formation_counts.values, labels=formation_counts.index, autopct='%1.0f%%', startangle=90)
    ax3.set_title('Formation Distribution', fontsize=12, fontweight='bold')
    
    # 4. Captain selection bar
    ax4 = fig.add_subplot(gs[1, 1])
    captain_counts = top_teams['captain'].value_counts().head(5)
    ax4.bar(range(len(captain_counts)), captain_counts.values, color='#FF6B6B', edgecolor='black')
    ax4.set_xticks(range(len(captain_counts)))
    ax4.set_xticklabels([c.split()[0] for c in captain_counts.index], rotation=45)
    ax4.set_ylabel('Teams', fontsize=10)
    ax4.set_title('Top 5 Captain Picks', fontsize=12, fontweight='bold')
    
    # 5. Score distribution
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.hist(top_teams['5gw_estimated'], bins=20, color='#4ECDC4', alpha=0.7, edgecolor='black')
    ax5.axvline(top_teams['5gw_estimated'].mean(), color='red', linestyle='--', linewidth=2)
    ax5.set_xlabel('5GW Projected Score', fontsize=10)
    ax5.set_ylabel('Number of Teams', fontsize=10)
    ax5.set_title('Score Distribution', fontsize=12, fontweight='bold')
    
    # 6. Best value players
    ax6 = fig.add_subplot(gs[2, :])
    predictions['points_per_million'] = predictions['weighted_score'] / predictions['price']
    best_value = predictions[predictions['weighted_score'] > 3.0].nlargest(15, 'points_per_million')
    
    x = range(len(best_value))
    bars = ax6.bar(x, best_value['points_per_million'], color=plt.cm.viridis(best_value['weighted_score']))
    ax6.set_xticks(x)
    ax6.set_xticklabels([p.split('(')[0] for p in best_value['full_name']], rotation=45, ha='right')
    ax6.set_ylabel('Points per £Million', fontsize=12)
    ax6.set_title('Best Value Players (Score > 3.0)', fontsize=14, fontweight='bold')
    
    # Add price labels
    for bar, (_, player) in zip(bars, best_value.iterrows()):
        ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"£{player['price']}m", ha='center', va='bottom', fontsize=8)
    
    # 7. Final team summary
    ax7 = fig.add_subplot(gs[3, :])
    ax7.axis('off')
    
    summary_text = "FINAL RECOMMENDED TEAMS SUMMARY\n" + "="*50 + "\n\n"
    
    for idx, team in final_teams.iterrows():
        summary_text += f"Team {idx+1}: {team['formation']} Formation | Budget: £{team['budget']}m | "
        summary_text += f"Captain: {team['captain'].split()[0]} | 5GW Score: {team['5gw_estimated']:.1f}\n"
        summary_text += f"Key Players: "
        
        # Get key players
        key_players = []
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            for i in range(1, 6):
                col = f'{pos}{i}'
                if col in team.index and pd.notna(team[col]) and team[col] and team.get(f'{col}_selected', 0) == 1:
                    player_name = team[col].split('(')[0]
                    if len(key_players) < 5:  # Limit to 5 key players
                        key_players.append(player_name)
        
        summary_text += ", ".join(key_players[:5]) + "\n\n"
    
    ax7.text(0.5, 0.5, summary_text, transform=ax7.transAxes, fontsize=12,
             verticalalignment='center', horizontalalignment='center',
             bbox=dict(boxstyle='round,pad=1', facecolor='lightgray', alpha=0.8))
    
    fig.suptitle('FPL Optimization Analysis Dashboard', fontsize=20, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'summary_dashboard.png', dpi=300, bbox_inches='tight')
    plt.close()


def main():
    """Create all visualizations"""
    print("Creating FPL optimization visualizations...")
    
    # Create output directory
    output_dir = Path("../visualizations")
    output_dir.mkdir(exist_ok=True)
    
    # Load data
    predictions, top_teams, team_scores, final_teams = load_data()
    
    # Create individual visualizations
    print("1. Creating player score distribution...")
    create_player_score_distribution(predictions, output_dir)
    
    print("2. Creating team strength rankings...")
    create_team_strength_ranking(team_scores, output_dir)
    
    print("3. Creating formation analysis...")
    create_formation_analysis(top_teams, output_dir)
    
    print("4. Creating captain analysis...")
    create_captain_analysis(predictions, top_teams, output_dir)
    
    print("5. Creating price-value analysis...")
    create_price_value_analysis(predictions, output_dir)
    
    print("6. Creating team composition heatmap...")
    create_team_composition_heatmap(final_teams, predictions, output_dir)
    
    print("7. Creating score projection comparison...")
    create_score_projection_comparison(top_teams, output_dir)
    
    print("8. Creating summary dashboard...")
    create_summary_dashboard(predictions, top_teams, team_scores, final_teams, output_dir)
    
    print(f"\nAll visualizations created successfully in {output_dir}/")
    print("\nGenerated files:")
    for file in sorted(output_dir.glob("*.png")):
        print(f"  - {file.name}")


if __name__ == "__main__":
    main()