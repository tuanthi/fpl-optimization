#!/bin/bash
# Complete script to run merged season prediction with optimization

echo "Running merged season prediction for gameweek 39..."

# Step 1: Run the merged seasons script (creates merged data and Bradley-Terry matrices)
python src/end_to_end_merged_seasons.py 39

# Step 2: Set up temporary directory for optimization
mkdir -p data/9999
cp data/merged_2024_2025/merged_*.csv data/9999/

# Rename files to expected format
cd data/9999
for f in merged_*.csv; do 
    mv "$f" "9999_${f#merged_}"
done

# Copy Bradley-Terry results
cp -r ../merged_2024_2025/bradley_terry .
cp -r ../merged_2024_2025/team_bradley_terry .
cd ../..

# Step 3: Run week sampling (creates prediction data)
echo "Running week sampling..."
python src/fpl_week_sampling.py 9999 1 38

# Step 4: Run optimization to find top 50 teams
echo "Running optimization..."
python src/fast_optimization_runner.py data/9999/pred_9999_week_sampling_1_to_38.csv data/merged_2024_2025/merged_top_50_teams_gameweek_39.csv

# Clean up
rm -rf data/9999

echo "Done! Check data/merged_2024_2025/merged_top_50_teams_gameweek_39.csv"