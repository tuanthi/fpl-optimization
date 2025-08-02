# FPL Data Fetcher

A Python script to fetch Fantasy Premier League (FPL) data including player statistics, match details, and gameweek points.

## Setup

1. Create and activate a Python environment using uv:
```bash
uv venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
uv pip install requests pandas
```

## Usage

### Fetch data for a specific season

```bash
# Fetch 2025/26 season data
python fetch_fpl_data.py 2025

# Fetch 2024/25 season data  
python fetch_fpl_data.py 2024

# Default (no argument) fetches 2025/26 season
python fetch_fpl_data.py
```

### Fetch player weekly data only

```bash
# Fetch just player weekly performance data
python fetch_player_weekly.py 2025

# Fetch 2024/25 season weekly data
python fetch_player_weekly.py 2024
```

### Direct script usage

```bash
# Fetch 2025/26 season
python fpl_data_fetcher.py 2025

# Fetch 2024/25 season
python fpl_data_fetcher.py 2024
```

## Output Files

The script creates CSV files with the season year as prefix:

- `{year}_fpl_players.csv` - All player data including:
  - Basic info (name, team, position, price)
  - Season statistics (total points, goals, assists, clean sheets)
  - Advanced metrics (xG, xA, BPS, ICT index)
  - Cards (yellow/red)

- `{year}_fpl_matches.csv` - All match details including:
  - Teams, scores, kickoff times
  - Match status (finished/scheduled)
  - Match difficulty ratings
  - Match statistics (for finished matches)

- `{year}_fpl_gameweek_{gw}_points.csv` - Player points for specific gameweeks (when available)

- `{year}_fpl_all_gameweeks_points.csv` - All gameweek points combined (when season has started)

- `{year}_fpl_player_weekly_data.csv` - Detailed player performance by gameweek including:
  - Player info (name, team, position)
  - Match details (opponent, home/away, score)
  - Performance stats per gameweek (points, goals, assists, etc.)
  - Advanced metrics (BPS, ICT index components)
  - Ownership and transfer data

## Examples

```bash
# Fetch current season data
python fetch_fpl_data.py

# This creates:
# - 2025_fpl_players.csv
# - 2025_fpl_matches.csv
# - 2025_fpl_gameweek_X_points.csv (if season has started)
```

## Historical Data

The official FPL API only provides current season data. For historical seasons, use the historical data fetcher:

```bash
# Check available historical seasons
python fetch_historical_data.py

# Fetch specific season (2023-24, 2022-23, etc.)
python fetch_historical_data.py 2023-24

# Or use just the year
python fetch_historical_data.py 2023
```

This fetches data from community-maintained repositories and creates:
- `{year}_fpl_players_historical.csv` - All players from that season
- `{year}_fpl_gameweeks_historical.csv` - Player performance by gameweek
- `{year}_fpl_fixtures_historical.csv` - All match results
- `{year}_fpl_teams_historical.csv` - Team information

Available seasons: 2024-25, 2023-24, 2022-23, 2021-22, 2020-21, 2019-20, 2018-19, 2017-18, 2016-17

### Complete Historical Data (All Gameweeks)

For complete season data with all 38 gameweeks:

```bash
# Fetch complete season data (recommended for 2024-25)
python fetch_complete_historical.py 2024-25

# Or use just the year
python fetch_complete_historical.py 2024
```

This creates files with '_complete' suffix and includes all 38 gameweeks by fetching individual gameweek files.

### Current Season Gameweek Data

For the ongoing 2024-25 season, use:

```bash
# Fetch all completed gameweeks from current season
python fetch_current_gameweeks.py
```

This creates `2024_fpl_gameweeks_current.csv` with all gameweek data from the current season.
Note: This only works after gameweeks have been played (typically from mid-August onwards).

## API Information

The script uses the official Fantasy Premier League API:
- Base URL: `https://fantasy.premierleague.com/api/`
- No authentication required
- Rate limiting may apply for excessive requests

## Notes

- The FPL API typically updates for the new season in July/August
- Historical data may be limited or unavailable for past seasons
- Match statistics are only available for finished matches
- Player prices are shown in actual pounds (API value / 10)