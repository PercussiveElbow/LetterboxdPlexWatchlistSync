#!/usr/bin/env python3
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
import requests
from dotenv import load_dotenv
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables from .env file
load_dotenv()

def get_environment_variables():
    """Get and validate required environment variables."""
    plex_token = os.getenv('PLEX_TOKEN')
    plex_url = os.getenv('PLEX_URL')
    letterboxd_username = os.getenv('LETTERBOXD_USERNAME')

    required_vars = {
        'PLEX_TOKEN': plex_token,
        'PLEX_URL': plex_url,
        'LETTERBOXD_USERNAME': letterboxd_username
    }

    missing_vars = [var_name for var_name, var_value in required_vars.items() if not var_value]

    if missing_vars:
        print("Error: Missing required environment variables:", file=sys.stderr)
        for var_name in missing_vars:
            print(f"- {var_name}", file=sys.stderr)
        print("\nPlease set these variables in your .env file", file=sys.stderr)
        sys.exit(1)

    return plex_token, plex_url, letterboxd_username

def fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed. Retrying... Error: {str(e)}")
                continue
            else:
                print(f"Failed after {max_retries} attempts. Error: {str(e)}")
                sys.exit(1)

def get_letterboxd_data(username):
    """Fetch watchlist and watched films from Letterboxd."""
    print("Get Watchlist and Watched Films info from Letterboxd")
    print("Warning: The following API calls may take some time to complete.")
    
    watchlist = fetch_with_retry(f"https://letterboxd-list-radarr.onrender.com/{username}/watchlist/")
    watched = fetch_with_retry(f"https://letterboxd-list-radarr.onrender.com/{username}/films/")
    print("Got Watchlist and Watched Films info from Letterboxd")
    
    return watchlist, watched

def get_imdb_id_from_guid(guid):
    """Extract IMDB ID from Plex GUID."""
    if "imdb://" in str(guid):
        return str(guid).split('://')[1].split(">")[0]
    return None

def process_single_watchlist_item(watchlist_item, letterboxd_watchlist, letterboxd_watched):
    """Process a single watchlist item and return its categorization."""
    # print(f"Existing movie {watchlist_item.title} is in Plex watchlist, checking if we need to do anything with it")
    
    found_already = False
    for guid in watchlist_item.guids:
        imdb_id = get_imdb_id_from_guid(guid)
        if not imdb_id:
            continue

        # Check if movie is already watched
        for watched_movie in letterboxd_watched:
            if imdb_id == watched_movie["imdb_id"]:
                print(f"Movie {watchlist_item.title} already watched. Adding to delete list")
                return "remove", imdb_id, watchlist_item

        # Check if movie is already in watchlist
        if not found_already:
            for watchlist_movie in letterboxd_watchlist:
                if imdb_id == watchlist_movie["imdb_id"]:
                    return "present", imdb_id, None

    return "add", None, watchlist_item

def process_watchlist_items(current_items, letterboxd_watchlist, letterboxd_watched):
    """Process current watchlist items and categorize them using parallel processing."""
    movies_to_remove = []
    already_present = []
    movies_to_add_to_letterboxd = []

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all tasks
        future_to_item = {
            executor.submit(
                process_single_watchlist_item,
                item,
                letterboxd_watchlist,
                letterboxd_watched
            ): item for item in current_items
        }

        # Process completed tasks
        for future in as_completed(future_to_item):
            action, imdb_id, item = future.result()
            
            if action == "remove":
                movies_to_remove.append(item)
            elif action == "present":
                already_present.append(imdb_id)
            elif action == "add":
                movies_to_add_to_letterboxd.append(item)

    return movies_to_remove, already_present, movies_to_add_to_letterboxd

def sync_watchlist(account, letterboxd_watchlist, already_present):
    """Sync Letterboxd watchlist with Plex.
    Returns a list of movies that couldn't be synced."""
    unsynced_movies = []
    
    for movie in letterboxd_watchlist:
        title = movie["title"]

        if movie["imdb_id"] in already_present:
            # print(f"{title} is already present in Plex Watchlist, don't need to add")
            continue

        discover_results = account.searchDiscover(title, providers="discover")
        print(f"Searching for.. {title}")
        
        found = False
        for discover_result in discover_results:
            for guid in discover_result.guids:
                imdb_id = get_imdb_id_from_guid(guid)
                if imdb_id and imdb_id == movie["imdb_id"]:
                    print(f" - Adding {title} to Plex watchlist")
                    account.addToWatchlist(discover_result)
                    found = True
                    break
            if found:
                break
                
        if not found:
            print(f" - Could not find {title} (IMDB ID: {movie['imdb_id']}) in Plex Discover")
            unsynced_movies.append(movie)
    
    return unsynced_movies

def main():
    # Get and validate environment variables
    plex_token, plex_url, letterboxd_username = get_environment_variables()
    
    account = MyPlexAccount(token=plex_token)
    
    # Get current watchlist
    current_watchlist_items = account.watchlist()
    
    print("Getting Letterboxd data")
    letterboxd_watchlist, letterboxd_watched = get_letterboxd_data(letterboxd_username)
    
    print("Processing watchlist items")
    movies_to_remove, already_present, movies_to_add = process_watchlist_items(
        current_watchlist_items, letterboxd_watchlist, letterboxd_watched
    )
    
    # Remove watched movies
    if movies_to_remove:
        print("Clear already watched movies.")
        account.removeFromWatchlist(movies_to_remove)
        print("Done clear already watched movies.")
    
    # Sync watchlist
    unsynced_movies = sync_watchlist(account, letterboxd_watchlist, already_present)
    
    # Report unsynced movies
    if unsynced_movies:
        print("\nThe following movies could not be synced:")
        for movie in unsynced_movies:
            print(f"- {movie['title']} (IMDB ID: {movie['imdb_id']})")
        print(f"\nThis can be for a few reasons e.g.:")
        print(f"- The movie is is considered a TV show on Plex Discover")
        print(f"- The movie is considered upcoming/unconfirmed as is so not available on the Plex Discover")

if __name__ == "__main__":
    main()
