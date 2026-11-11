
import requests
import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import quote

BASE = "https://api.chess.com/pub"

# Search at most the latest 12 months.
MAX_MONTHS = 12

# Cache file is automatically created beside this Python file.
CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "chess_cache.json"
)

HEADERS = {
    "User-Agent": "ChessAnalyzer/1.0",
    "Accept-Encoding": "gzip"
}


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError):
            return {}

    return {}


def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as file:
            json.dump(cache, file)
    except OSError:
        pass


def get_json(url, cache=None, cache_key=None, permanent=False):

    # Reuse previously downloaded monthly archives.
    if cache is not None and cache_key in cache:
        saved = cache[cache_key]

        age = time.time() - saved.get("time", 0)

        # Older completed months can be cached permanently.
        # Current month and archive lists refresh after 12 hours.
        if permanent or age < 43200:
            return saved["data"]

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    if response.status_code == 404:
        raise ValueError(
            "Chess.com returned 404. This account's requested "
            "public data or game archives are unavailable."
        )

    if response.status_code == 429:
        raise ValueError(
            "Chess.com is temporarily limiting requests. "
            "Wait a minute and try again."
        )

    response.raise_for_status()

    data = response.json()

    if cache is not None and cache_key is not None:
        cache[cache_key] = {
            "time": time.time(),
            "data": data
        }
        save_cache(cache)

    return data


def convert_game(game, username):

    white = game.get("white", {})
    black = game.get("black", {})

    if not isinstance(white, dict) or not isinstance(black, dict):
        return None

    username = username.lower()

    if white.get("username", "").lower() == username:
        player = white
        opponent = black
        color = "White"

    elif black.get("username", "").lower() == username:
        player = black
        opponent = white
        color = "Black"

    else:
        return None

    result = player.get("result", "").lower()

    draws = [
        "agreed",
        "repetition",
        "stalemate",
        "insufficient",
        "50move",
        "timevsinsufficient"
    ]

    losses = [
        "checkmated",
        "resigned",
        "timeout",
        "lose"
    ]

    if result == "win":
        score = 1
        outcome = "Win"

    elif result in draws:
        score = 0.5
        outcome = "Draw"

    elif result in losses:
        score = 0
        outcome = "Loss"

    else:
        return None

    timestamp = game.get("end_time", 0)

    try:
        date = datetime.fromtimestamp(
            timestamp,
            timezone.utc
        ).strftime("%Y-%m-%d")
    except (ValueError, OSError, OverflowError, TypeError):
        date = "Unknown"

    return {
        "date": date,
        "timestamp": timestamp,
        "opponent": opponent.get("username", "Unknown"),
        "player_rating": player.get("rating", 0),
        "opponent_rating": opponent.get("rating", 0),
        "color": color,
        "result": outcome,
        "score": score
    }


def fetch_games(username, limit=100):

    username = username.strip()

    if not username:
        raise ValueError("Enter a Chess.com username.")

    encoded_username = quote(username.lower())

    cache = load_cache()

    # Get player profile.
    profile_url = f"{BASE}/player/{encoded_username}"

    profile = get_json(profile_url)

    actual_username = profile.get("username", username)

    # Get current rapid rating.
    current_rating = None

    try:
        stats_url = f"{BASE}/player/{encoded_username}/stats"

        stats = get_json(stats_url)

        rapid = stats.get("chess_rapid", {})
        last_rating = rapid.get("last", {})

        if isinstance(last_rating, dict):
            current_rating = last_rating.get("rating")

    except (ValueError, requests.RequestException):
        pass

    # Get monthly archive URLs.
    archives_url = (
        f"{BASE}/player/{encoded_username}/games/archives"
    )

    archives_data = get_json(
        archives_url,
        cache,
        "archives_" + encoded_username
    )

    archives = archives_data.get("archives", [])

    # Only inspect the latest 12 months.
    recent_archives = list(reversed(archives[-MAX_MONTHS:]))

    games = []

    for archive_url in recent_archives:

        if len(games) >= limit:
            break

        # Older completed months never need to be downloaded again.
        is_old_month = archive_url != recent_archives[0]

        monthly_data = get_json(
            archive_url,
            cache,
            archive_url,
            permanent=is_old_month
        )

        monthly_games = monthly_data.get("games", [])

        if not isinstance(monthly_games, list):
            continue

        for game in reversed(monthly_games):

            if len(games) >= limit:
                break

            if not isinstance(game, dict):
                continue

            if game.get("time_class") != "rapid":
                continue

            if game.get("rules", "chess") != "chess":
                continue

            if game.get("rated") is False:
                continue

            converted = convert_game(
                game,
                actual_username
            )

            if converted is not None:
                games.append(converted)

    # Chronological order.
    games.sort(key=lambda x: x["timestamp"])

    games = games[-limit:]

    if not games:
        raise ValueError(
            "No rated rapid games were found in the latest "
            f"{MAX_MONTHS} months of available archives."
        )

    if current_rating is None:
        current_rating = games[-1]["player_rating"]

    return {
        "username": actual_username,
        "games": games,
        "current_rating": current_rating
    }
