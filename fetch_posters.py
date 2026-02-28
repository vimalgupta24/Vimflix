"""
Fetch poster_path for all catalog titles from TMDB and save to posters.json.
Run once (or when catalog changes): TMDB_API_KEY=xxx python fetch_posters.py
Server merges posters.json into /api/catalog so the UI can show poster images.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

import requests

from catalog import MOVIES, TV_SERIES, ANIME

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

TMDB_BASE = "https://api.themoviedb.org/3"
RATE_DELAY = 0.26  # ~40 requests per 10s


def get_api_key() -> str:
    key = (os.environ.get("TMDB_API_KEY") or "").strip()
    if not key:
        logger.error("Set TMDB_API_KEY. Get a key at https://www.themoviedb.org/settings/api")
        sys.exit(1)
    return key


def fetch_poster(api_key: str, kind: str, tmdb_id: int) -> str | None:
    url = f"{TMDB_BASE}/{kind}/{tmdb_id}"
    try:
        r = requests.get(url, params={"api_key": api_key}, timeout=10)
        r.raise_for_status()
        data = r.json()
        path = data.get("poster_path")
        return path if path else None
    except Exception as e:
        logger.debug(" %s %s: %s", kind, tmdb_id, e)
        return None


def main() -> None:
    api_key = get_api_key()
    out_path = Path(__file__).resolve().parent / "posters.json"

    movie_ids = sorted({m[1] for m in MOVIES})
    tv_ids = sorted({t[1] for t in TV_SERIES})
    anime_movie_ids = sorted({a[1] for a in ANIME if a[4] == "movie"})
    anime_tv_ids = sorted({a[1] for a in ANIME if a[4] == "tv"})
    all_movie_ids = sorted(set(movie_ids) | set(anime_movie_ids))
    all_tv_ids = sorted(set(tv_ids) | set(anime_tv_ids))

    movie_posters: dict[str, str] = {}
    tv_posters: dict[str, str] = {}

    for tid in all_movie_ids:
        path = fetch_poster(api_key, "movie", tid)
        if path:
            movie_posters[str(tid)] = path
        time.sleep(RATE_DELAY)

    for tid in all_tv_ids:
        path = fetch_poster(api_key, "tv", tid)
        if path:
            tv_posters[str(tid)] = path
        time.sleep(RATE_DELAY)

    out = {"movie": movie_posters, "tv": tv_posters}
    out_path.write_text(json.dumps(out, indent=0), encoding="utf-8")
    logger.info("Wrote %s (%d movie, %d tv posters)", out_path, len(movie_posters), len(tv_posters))


if __name__ == "__main__":
    main()
