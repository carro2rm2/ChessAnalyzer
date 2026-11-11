
import math
from statistics import mean


def percentile(values, percentage):

    values = sorted(values)

    if not values:
        return 0

    position = (len(values) - 1) * percentage

    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return values[lower]

    fraction = position - lower

    return (
        values[lower] * (1 - fraction)
        + values[upper] * fraction
    )


def performance_rating(games):

    if not games:
        return None

    average_opponent = mean(
        game["opponent_rating"] for game in games
    )

    score = mean(
        game["score"] for game in games
    )

    # Prevent infinite ratings with 0% or 100% scores.
    score = max(0.01, min(0.99, score))

    difference = 400 * math.log10(
        score / (1 - score)
    )

    return round(average_opponent + difference)


def rolling_performance(games, window):

    results = []

    if len(games) < window:
        return results

    for i in range(len(games) - window + 1):

        group = games[i:i + window]

        results.append({
            "rating": performance_rating(group),
            "start": group[0]["date"],
            "end": group[-1]["date"],
            "games": window
        })

    return results


def analyze_games(games, current_rating):

    if not games:
        raise ValueError("No games to analyze.")

    wins = sum(
        game["result"] == "Win" for game in games
    )

    draws = sum(
        game["result"] == "Draw" for game in games
    )

    losses = sum(
        game["result"] == "Loss" for game in games
    )

    total = len(games)

    points = wins + draws * 0.5

    score_percentage = points / total * 100

    # Use 20-game windows for consistency.
    window = min(20, total)

    rolling = rolling_performance(games, window)

    ratings = [
        item["rating"] for item in rolling
    ]

    # Use 10-game windows to identify short hot streaks.
    short_window = min(10, total)

    short_rolling = rolling_performance(
        games, short_window
    )

    best_sustained = max(
        rolling, key=lambda item: item["rating"]
    )

    best_short = max(
        short_rolling, key=lambda item: item["rating"]
    )

    return {

        "total": total,

        "wins": wins,
        "draws": draws,
        "losses": losses,

        "score": round(score_percentage, 1),

        "current_rating": current_rating,

        "average_player": round(mean(
            game["player_rating"] for game in games
        )),

        "average_opponent": round(mean(
            game["opponent_rating"] for game in games
        )),

        "floor": round(percentile(ratings, 0.20)),

        "typical": round(percentile(ratings, 0.50)),

        "ceiling": round(percentile(ratings, 0.80)),

        "best_sustained": best_sustained,

        "best_short": best_short,

        "rolling": rolling,

        "warnings": (
            ["Fewer than 20 games: estimates are less reliable."]
            if total < 20 else
            ["Fewer than 50 games: treat estimates as preliminary."]
            if total < 50 else []
        )
    }
