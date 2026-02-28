"""
TMDB lookup: search by movie or TV title → get tmdb_id (and genre/year) for catalog & Vidking.

Requires TMDB API key: https://www.themoviedb.org/settings/api
  export TMDB_API_KEY=your_key

Examples:
  python tmdb_lookup.py "Inception"
  python tmdb_lookup.py "Breaking Bad" --type tv
  python tmdb_lookup.py "Dune" --year 2021 --catalog
  python tmdb_lookup.py "Squid Game" --pick 1
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

TMDB_BASE = "https://api.themoviedb.org/3"
REQUEST_TIMEOUT = 15

# Map TMDB genre name → catalog-style (e.g. Science Fiction → Sci-Fi)
GENRE_ALIAS = {"Science Fiction": "Sci-Fi"}


def get_api_key() -> str:
    key = (os.environ.get("TMDB_API_KEY") or "").strip()
    if not key:
        logger.error(
            "TMDB_API_KEY is not set. Get a free key at https://www.themoviedb.org/settings/api"
        )
        sys.exit(1)
    return key


def get_genre_lists(api_key: str) -> tuple[dict[int, str], dict[int, str]]:
    """Fetch movie and TV genre id→name maps."""
    movie_resp = requests.get(
        f"{TMDB_BASE}/genre/movie/list",
        params={"api_key": api_key, "language": "en"},
        timeout=REQUEST_TIMEOUT,
    )
    movie_resp.raise_for_status()
    tv_resp = requests.get(
        f"{TMDB_BASE}/genre/tv/list",
        params={"api_key": api_key, "language": "en"},
        timeout=REQUEST_TIMEOUT,
    )
    tv_resp.raise_for_status()
    movie_genres = {g["id"]: g["name"] for g in movie_resp.json().get("genres", [])}
    tv_genres = {g["id"]: g["name"] for g in tv_resp.json().get("genres", [])}
    return movie_genres, tv_genres


def resolve_genre(name: str) -> str:
    return GENRE_ALIAS.get(name, name)


def search_movie(
    api_key: str, query: str, year: int | None = None, page: int = 1
) -> dict[str, Any]:
    params: dict[str, Any] = {"api_key": api_key, "query": query, "page": page}
    if year is not None:
        params["year"] = year
    resp = requests.get(
        f"{TMDB_BASE}/search/movie", params=params, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()


def search_tv(
    api_key: str, query: str, year: int | None = None, page: int = 1
) -> dict[str, Any]:
    params: dict[str, Any] = {"api_key": api_key, "query": query, "page": page}
    if year is not None:
        params["first_air_date_year"] = year
    resp = requests.get(
        f"{TMDB_BASE}/search/tv", params=params, timeout=REQUEST_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()


def parse_year(date_str: str | None) -> int | None:
    if not date_str or len(date_str) < 4:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return None


def build_result(
    r: dict[str, Any],
    media_type: str,
    genre_map: dict[int, str],
) -> dict[str, Any]:
    title = (r.get("title") or r.get("name") or r.get("original_title") or r.get("original_name") or "—")
    date_key = "release_date" if media_type == "movie" else "first_air_date"
    year = parse_year(r.get(date_key))
    genre_ids = r.get("genre_ids") or []
    first_genre = ""
    if genre_ids and genre_map:
        first_genre = resolve_genre(genre_map.get(genre_ids[0], "") or "")
    overview = (r.get("overview") or "").strip()
    if len(overview) > 120:
        overview = overview[:117] + "..."
    return {
        "tmdb_id": r["id"],
        "title": title,
        "year": year,
        "type": media_type,
        "genre": first_genre or "Drama",
        "vote_average": r.get("vote_average"),
        "overview": overview,
    }


def run(
    query: str,
    type_filter: str = "both",
    limit: int = 10,
    year: int | None = None,
    catalog_format: bool = False,
    pick_index: int | None = None,
    json_output: bool = False,
) -> None:
    api_key = get_api_key()
    query = query.strip()
    if not query:
        logger.error("Query cannot be empty")
        sys.exit(1)

    movie_genres: dict[int, str] = {}
    tv_genres: dict[int, str] = {}
    try:
        movie_genres, tv_genres = get_genre_lists(api_key)
    except requests.RequestException as e:
        logger.warning("Could not fetch genre lists: %s. Catalog output will use 'Drama'.", e)

    results: list[dict[str, Any]] = []

    if type_filter in ("movie", "both"):
        try:
            data = search_movie(api_key, query, year=year)
            for r in data.get("results", [])[:limit]:
                results.append(build_result(r, "movie", movie_genres))
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                logger.error("Invalid TMDB API key. Check TMDB_API_KEY.")
                sys.exit(1)
            raise
        except requests.RequestException as e:
            logger.error("Movie search failed: %s", e)
            sys.exit(1)

    if type_filter in ("tv", "both"):
        try:
            data = search_tv(api_key, query, year=year)
            for r in data.get("results", [])[:limit]:
                results.append(build_result(r, "tv", tv_genres))
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                logger.error("Invalid TMDB API key. Check TMDB_API_KEY.")
                sys.exit(1)
            raise
        except requests.RequestException as e:
            logger.error("TV search failed: %s", e)
            sys.exit(1)

    if not results:
        logger.error("No results found for %r", query)
        sys.exit(1)

    if pick_index is not None:
        idx = pick_index - 1
        if idx < 0 or idx >= len(results):
            logger.error("--pick must be between 1 and %d", len(results))
            sys.exit(1)
        r = results[idx]
        if json_output:
            print(json.dumps({"tmdb_id": r["tmdb_id"], "title": r["title"], "year": r["year"], "type": r["type"]}))
        else:
            print(r["tmdb_id"])
        return

    if json_output:
        out = [{"tmdb_id": x["tmdb_id"], "title": x["title"], "year": x["year"], "type": x["type"], "genre": x["genre"]} for x in results]
        print(json.dumps(out, indent=2))
        return

    if catalog_format:
        for r in results:
            title_esc = r["title"].replace('"', '\\"')
            genre = r["genre"]
            y = r["year"] or 0
            print(f'    ("{title_esc}", {r["tmdb_id"]}, "{genre}", {y}),')
        return

    # Rich table-like output
    col_id = 10
    col_title = 36
    col_year = 6
    col_type = 6
    col_vote = 5
    col_genre = 12
    header = (
        f"{'#':<3} {'tmdb_id':<{col_id}} {'Title':<{col_title}} "
        f"{'Year':<{col_year}} {'Type':<{col_type}} {'Vote':<{col_vote}} {'Genre':<{col_genre}}"
    )
    print(header)
    print("-" * (3 + col_id + col_title + col_year + col_type + col_vote + col_genre + 6))
    for i, r in enumerate(results, 1):
        title = (r["title"][: col_title - 2] + "..") if len(r["title"]) > col_title else r["title"]
        y = str(r["year"]) if r["year"] else "—"
        vote = f"{r['vote_average']:.1f}" if r.get("vote_average") is not None else "—"
        print(f"{i:<3} {r['tmdb_id']:<{col_id}} {title:<{col_title}} {y:<{col_year}} {r['type']:<{col_type}} {vote:<{col_vote}} {r['genre']:<{col_genre}}")
    print()
    for i, r in enumerate(results, 1):
        ov = r.get("overview") or ""
        if ov:
            print(f"  {i}. {r['title']} ({r['year'] or '?'}): {ov}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search TMDB by title → get tmdb_id for Vidking/catalog.",
        epilog="Set TMDB_API_KEY. Get a key: https://www.themoviedb.org/settings/api",
    )
    parser.add_argument("query", nargs="+", help="Movie or TV title to search")
    parser.add_argument(
        "--type",
        choices=("movie", "tv", "both"),
        default="both",
        help="Search movie, tv, or both (default: both)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Max results per type (default: 10)",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        metavar="YYYY",
        help="Filter by release/first_air year",
    )
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="Print catalog.py tuple lines: (title, tmdb_id, genre, year)",
    )
    parser.add_argument(
        "--pick",
        type=int,
        default=None,
        metavar="N",
        help="Print only the N-th result (1-based); prints tmdb_id only (for scripts)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()
    query = " ".join(args.query)
    run(
        query=query,
        type_filter=args.type,
        limit=args.limit,
        year=args.year,
        catalog_format=args.catalog,
        pick_index=args.pick,
        json_output=args.json,
    )


if __name__ == "__main__":
    main()
