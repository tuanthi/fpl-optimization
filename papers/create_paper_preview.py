#!/usr/bin/env python3
"""Create a preview image of key paper results"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# Create figure
fig, ax = plt.subplots(1, 1, figsize=(12, 8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

# Title
title_box = FancyBboxPatch((0.5, 8.5), 9, 1.2, 
                           boxstyle="round,pad=0.1",
                           facecolor='#2c3e50', 
                           edgecolor='none')
ax.add_patch(title_box)
ax.text(5, 9.1, 'Hierarchical Bayesian Framework for FPL Optimization', 
        ha='center', va='center', fontsize=20, color='white', weight='bold')

# Key Results Section
results_box = FancyBboxPatch((0.5, 5), 4, 3,
                            boxstyle="round,pad=0.1",
                            facecolor='#ecf0f1',
                            edgecolor='#34495e',
                            linewidth=2)
ax.add_patch(results_box)

ax.text(2.5, 7.5, 'Key Results', ha='center', fontsize=16, weight='bold')
ax.text(0.8, 6.8, '✓ 76% Rank Improvement', fontsize=12)
ax.text(0.8, 6.3, '✓ Top 0.2% Global Ranking', fontsize=12)
ax.text(0.8, 5.8, '✓ 23.7% Better Returns', fontsize=12)
ax.text(0.8, 5.3, '✓ 200x Faster than Brute Force', fontsize=12)

# Real-World Validation
validation_box = FancyBboxPatch((5, 5), 4.5, 3,
                               boxstyle="round,pad=0.1",
                               facecolor='#e8f6f3',
                               edgecolor='#16a085',
                               linewidth=2)
ax.add_patch(validation_box)

ax.text(7.25, 7.5, 'Real-World Performance', ha='center', fontsize=16, weight='bold')
ax.text(7.25, 6.8, '2023/24: Rank 81,117', ha='center', fontsize=12)
ax.text(7.25, 6.3, '↓', ha='center', fontsize=20, color='#27ae60')
ax.text(7.25, 5.8, '2024/25: Rank 19,601', ha='center', fontsize=12, weight='bold', color='#27ae60')
ax.text(7.25, 5.3, '(10+ Million Players)', ha='center', fontsize=10, style='italic')

# Technical Approach
approach_box = FancyBboxPatch((0.5, 1.5), 9, 3,
                             boxstyle="round,pad=0.1",
                             facecolor='#fdf6e3',
                             edgecolor='#e67e22',
                             linewidth=2)
ax.add_patch(approach_box)

ax.text(5, 4.2, 'Technical Approach', ha='center', fontsize=16, weight='bold')
ax.text(2.5, 3.5, '1. Bradley-Terry Modeling', fontsize=11)
ax.text(2.5, 3.0, '2. Weighted Scoring: Φ(p,t)', fontsize=11)
ax.text(2.5, 2.5, '3. Cross-Season Mapping', fontsize=11)
ax.text(2.5, 2.0, '4. Beam Search Optimization', fontsize=11)

ax.text(7, 3.5, '• 667 Players Mapped', fontsize=11)
ax.text(7, 3.0, '• 200 Teams Generated', fontsize=11)
ax.text(7, 2.5, '• £100m Budget Constraint', fontsize=11)
ax.text(7, 2.0, '• Max 3 Players/Club', fontsize=11)

# Footer
ax.text(5, 0.8, 'Technical Report - January 2025', 
        ha='center', fontsize=10, style='italic', color='#7f8c8d')

plt.tight_layout()
plt.savefig('paper_preview.png', dpi=150, bbox_inches='tight', facecolor='white')
print("Created paper_preview.png")

# Also create a simple results summary chart
fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Rank improvement visualization
seasons = ['2023/24', '2024/25']
ranks = [81117, 19601]
colors = ['#e74c3c', '#27ae60']

ax1.bar(seasons, ranks, color=colors, alpha=0.8, edgecolor='black', linewidth=2)
ax1.set_ylabel('Global Rank', fontsize=12)
ax1.set_title('FPL Rank Improvement', fontsize=14, weight='bold')
ax1.set_ylim(0, 90000)

# Add value labels
for i, (season, rank) in enumerate(zip(seasons, ranks)):
    ax1.text(i, rank + 2000, f'{rank:,}', ha='center', fontsize=11, weight='bold')
    
# Add improvement arrow
ax1.annotate('', xy=(1, ranks[1]), xytext=(0, ranks[0]),
            arrowprops=dict(arrowstyle='->', lw=3, color='#2c3e50', alpha=0.5))
ax1.text(0.5, 50000, '76%\nImprovement', ha='center', fontsize=12, 
         weight='bold', color='#2c3e50')

# Model performance comparison
methods = ['Random', 'Greedy', 'Our Method']
scores = [12.3, 15.7, 19.8]
colors2 = ['#95a5a6', '#f39c12', '#2ecc71']

bars = ax2.bar(methods, scores, color=colors2, alpha=0.8, edgecolor='black', linewidth=2)
ax2.set_ylabel('Average Team Score', fontsize=12)
ax2.set_title('Optimization Method Comparison', fontsize=14, weight='bold')
ax2.set_ylim(0, 22)

# Add value labels
for bar, score in zip(bars, scores):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{score:.1f}', ha='center', fontsize=11, weight='bold')

plt.tight_layout()
plt.savefig('results_summary.png', dpi=150, bbox_inches='tight', facecolor='white')
print("Created results_summary.png")