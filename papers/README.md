# FPL Optimization Technical Papers

This directory contains academic papers and technical reports about our FPL optimization framework.

## Contents

- `fpl_optimization_paper.tex` - Main LaTeX source for the technical report
- `generate_paper_figures.py` - Python script to generate figures from actual data
- `compile_paper.sh` - Script to compile the LaTeX document to PDF

## Generated Figures

The following figures are generated from our actual optimization results:
- `budget_distribution.png` - Distribution of squad values across 200 teams
- `score_vs_budget.png` - Relationship between team budget and expected score
- `player_selection_frequency.png` - Most frequently selected players
- `formation_distribution.png` - Common formations in optimal teams
- `mapping_distribution.png` - Player mapping accuracy across seasons
- `ablation_study.png` - Component contribution analysis
- `computational_analysis.png` - Performance comparison

## Compiling the Paper

1. Ensure you have LaTeX installed (e.g., MacTeX, TeX Live)
2. Generate figures: `python generate_paper_figures.py`
3. Compile PDF: `./compile_paper.sh`

## Key Findings

- Weighted scoring function outperforms baselines by 23.7%
- Optimal teams use 92-98% of available budget
- 4-3-2 formation appears in 61% of top teams
- Premium players (>£10m) essential for competitive teams