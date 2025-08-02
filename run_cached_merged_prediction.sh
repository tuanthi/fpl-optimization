#!/bin/bash
# Run merged season prediction using cached data

echo "Using cached merged season data for gameweek 39..."

# Check if cached data exists
if [ ! -d "data/cached_merged_2024_2025" ]; then
    echo "Cached data not found. Running full merge process..."
    ./run_merged_prediction.sh
    echo "Running fix script to cache corrected data..."
    python src/fix_and_cache_merged_data.py
else
    echo "Found cached data in data/cached_merged_2024_2025"
    
    # Check if we need to update predictions
    if [ "$1" == "--update" ]; then
        echo "Updating predictions with cached data..."
        
        # Set up temp directory
        mkdir -p data/9999
        cp data/cached_merged_2024_2025/merged_*.csv data/9999/
        cd data/9999
        for f in merged_*.csv; do 
            mv "$f" "9999_${f#merged_}"
        done
        
        # Copy Bradley-Terry results
        cp -r ../cached_merged_2024_2025/bradley_terry .
        cp -r ../cached_merged_2024_2025/team_bradley_terry .
        cd ../..
        
        # Run optimization with fixed prediction data
        if [ -f "data/cached_merged_2024_2025/pred_merged_week_sampling_1_to_38_fixed.csv" ]; then
            echo "Using fixed prediction data..."
            python src/fast_optimization_runner.py \
                data/cached_merged_2024_2025/pred_merged_week_sampling_1_to_38_fixed.csv \
                data/cached_merged_2024_2025/merged_top_50_teams_gameweek_39_fixed.csv
        else
            echo "Running week sampling..."
            python src/fpl_week_sampling.py 9999 1 38
            python src/fast_optimization_runner.py \
                data/9999/pred_9999_week_sampling_1_to_38.csv \
                data/cached_merged_2024_2025/merged_top_50_teams_gameweek_39_fixed.csv
        fi
        
        # Clean up
        rm -rf data/9999
    fi
fi

echo ""
echo "Results available in:"
echo "  - Top 50 teams: data/cached_merged_2024_2025/merged_top_50_teams_gameweek_39_fixed.csv"
echo "  - Player mappings: data/cached_merged_2024_2025/player_replacement_mapping.csv"
echo "  - Team reference: data/cached_merged_2024_2025/team_reference.json"
echo ""
echo "To update predictions with new data, run: ./run_cached_merged_prediction.sh --update"