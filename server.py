"""
Vimflix - FastAPI backend. Serves static UI and catalog API (Vidking embed).
"""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from catalog import (
    all_genres_anime,
    all_genres_movies,
    all_genres_tv,
    get_anime,
    get_movies,
    get_tv_series,
)

app = FastAPI(title="Vimflix")
STATIC_DIR = Path(__file__).resolve().parent / "static"
POSTERS_PATH = Path(__file__).resolve().parent / "posters.json"

_posters_cache: dict | None = None


def _load_posters() -> dict:
    global _posters_cache
    if _posters_cache is not None:
        return _posters_cache
    if not POSTERS_PATH.is_file():
        _posters_cache = {"movie": {}, "tv": {}}
        return _posters_cache
    try:
        _posters_cache = json.loads(POSTERS_PATH.read_text(encoding="utf-8"))
    except Exception:
        _posters_cache = {"movie": {}, "tv": {}}
    return _posters_cache


def _with_posters(items: list[dict], kind: str) -> list[dict]:
    posters = _load_posters().get(kind, {})
    out = []
    for item in items:
        rec = dict(item)
        rec["poster_path"] = posters.get(str(rec["tmdb_id"]))
        out.append(rec)
    return out


def _anime_with_posters(items: list[dict]) -> list[dict]:
    posters = _load_posters()
    out = []
    for item in items:
        rec = dict(item)
        kind = "tv" if item.get("type") == "tv" else "movie"
        rec["poster_path"] = posters.get(kind, {}).get(str(rec["tmdb_id"]))
        out.append(rec)
    return out


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/catalog")
def api_catalog():
    body = {
        "movies": _with_posters(get_movies(), "movie"),
        "tv": _with_posters(get_tv_series(), "tv"),
        "anime": _anime_with_posters(get_anime()),
        "genres": {
            "movies": ["All"] + all_genres_movies(),
            "tv": ["All"] + all_genres_tv(),
            "anime": ["All"] + all_genres_anime(),
        },
    }
    return JSONResponse(
        content=body,
        headers={
            "Cache-Control": "public, max-age=300",
        },
    )


@app.get("/")
def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {"message": "Vimflix", "docs": "/docs"}
