# FPL Data Tools

Scripts for downloading and analyzing Fantasy Premier League data, including Bradley-Terry matrix construction for player comparisons.

## Usage

```bash
python src/fpl_download.py [YEAR]
```

Example:
```bash
# Download 2024/25 season data
python src/fpl_download.py 2024

# Download 2025/26 season data (current/upcoming)
python src/fpl_download.py 2025
```

## Output

All data is saved to `.venv/data/[YEAR]/` with the following files:

### 1. `[YEAR]_players.csv`
- All players for the season
- Includes: name, position, team, price, total points, etc.

### 2. `[YEAR]_fixtures.csv`
- All 380 matches in the season
- Includes: teams, scores, dates, match stats

### 3. `[YEAR]_teams.csv`
- All 20 teams in the Premier League
- Includes: team ID, name, short name, strength ratings

### 4. `[YEAR]_player_gameweek.csv`
- Player performance for each gameweek
- Includes: points, goals, assists, price, transfers, ownership
- One row per player per gameweek they played

## Data Sources

- **Historical seasons (2016-2024)**: GitHub repository by vaastav
- **Current/future seasons (2025+)**: Official FPL API

## Features

- Automatic season detection (historical vs current)
- Progress tracking for large downloads
- Price data included in gameweek file (converted from value/10)
- Summary report after download
- Organized directory structure

## Bradley-Terry Matrix Builder

### Usage

```bash
# Build matrix for weeks 1-9, with week 10 as next week
python src/fpl_player_prep.py 2024 9 10

# Build matrix for all gameweeks
python src/fpl_player_prep.py 2024
```

### Output

Creates files in `data/[YEAR]/bradley_terry/`:

1. **`bt_matrix_[suffix].npy`** - The Bradley-Terry matrix (NxN numpy array)
   - Matrix[i,j] = number of weeks player i scored more points than player j

2. **`player_mappings_[suffix].json`** - Player ID mappings and metadata

3. **`player_stats_[suffix].csv`** - Player statistics for the period
   - Total points, average points, games played
   - Price changes, position, team
   - Next week points (if specified)

4. **`matrix_analysis_[suffix].csv`** - Win rate analysis
   - Total wins, losses, and win percentage
   - Sorted by win rate

### Understanding the Bradley-Terry Matrix

The Bradley-Terry model is used to rank players based on pairwise comparisons:
- Each gameweek, every player who played is compared to every other player
- If Player A scores more points than Player B in a gameweek, A gets a "win" over B
- The matrix accumulates these wins across all specified gameweeks
- This creates a comprehensive head-to-head record for all player pairs

### Visualization

```bash
# Interactive analysis tool
python src/visualize_bradley_terry.py 2024 weeks_1_to_9

# Or for all weeks
python src/visualize_bradley_terry.py 2024
```

Features:
- View top performers by win rate
- Analyze specific player matchups
- Find players with similar performance patterns

## Notes

- Player gameweek data is only available for completed gameweeks
- Prices are in millions (e.g., 12.5 = £12.5m)
- The 2025/26 season starts in August 2025
- Bradley-Terry matrix only includes players who actually played (minutes > 0)