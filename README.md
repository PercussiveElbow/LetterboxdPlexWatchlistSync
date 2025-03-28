# Letterboxd to Plex Watchlist Sync

A simple Python script that syncs your Letterboxd watchlist to your Plex watchlist. This script uses the [letterboxd-list-radarr](https://github.com/screeny05/letterboxd-list-radarr) API service to fetch your Letterboxd data and then builds your Plex watchlist off of it. It's a bit hacky so there may be cases where movies fail to match where there's not a reliable IMDB ID, Plex considers a movie a TV show special or similar.

## Prerequisites

- Python 3.x
- A Plex account with a valid token
- A Letterboxd account
- **Important**: You need to log your watched movies on Letterboxd for the script to properly remove them from your Plex watchlist

## Setup

1. Clone this repository
2. Install the required Python packages:
   ```bash
   pip install python-plexapi requests python-dotenv
   ```
3. Create a `.env` file in the root directory with the following variables:
   ```
   PLEX_TOKEN=your_plex_token
   PLEX_URL=your_plex_server_url e.g. 127.0.0.1:32400
   LETTERBOXD_USERNAME=your_letterboxd_username
   ```

   Format details:
   - `PLEX_TOKEN`: Your Plex authentication token (found via https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)
   - `PLEX_URL`: Your Plex server URL (e.g., `http://127.0.0.1:32400` or `https://192.168.1.100:32400`) # Please note if there's a self signed cert here you may need to tweak the script
   - `LETTERBOXD_USERNAME`: Your Letterboxd username as it appears in your profile URL (e.g., if your profile is `letterboxd.com/username`, use `username`)

## Usage

Just run it
```bash
python letterboxd_plex_watchlist_sync.py
```

## How it works

1. Fetches your current Plex watchlist
2. Gets your Letterboxd watchlist and watched films using the letterboxd-list-radarr API
3. Removes movies from Plex watchlist if you've already watched them on Letterboxd
4. Adds new movies from your Letterboxd watchlist to Plex using the Discover feature

## Credits

This script relies on the [letterboxd-list-radarr](https://github.com/screeny05/letterboxd-list-radarr) API service for fetching Letterboxd data. Please check out that repo. 