"""
Vidking Player API helpers.
API reference: https://www.vidking.net/documentation
"""

from urllib.parse import urlencode

BASE_URL = "https://www.vidking.net/embed"


def _embed_params(
    *,
    color: str | None = None,
    auto_play: bool = False,
    progress: int | None = None,
    subtitle_lang: str | None = "en",
) -> dict:
    params = {}
    if color:
        params["color"] = color.lstrip("#")
    if auto_play:
        params["autoPlay"] = "true"
    if progress is not None and progress >= 0:
        params["progress"] = str(progress)
    if subtitle_lang:
        params["subtitle"] = subtitle_lang
        params["lang"] = subtitle_lang
    return params


def movie_embed_url(
    tmdb_id: str | int,
    *,
    color: str | None = None,
    auto_play: bool = False,
    progress: int | None = None,
    subtitle_lang: str | None = "en",
) -> str:
    """
    Build Vidking embed URL for a movie.
    subtitle_lang: e.g. "en" for English-only subtitles (if supported by player).
    """
    path = f"{BASE_URL}/movie/{tmdb_id}"
    params = _embed_params(color=color, auto_play=auto_play, progress=progress, subtitle_lang=subtitle_lang)
    if params:
        path += "?" + urlencode(params)
    return path


def tv_embed_url(
    tmdb_id: str | int,
    season: int,
    episode: int,
    *,
    color: str | None = None,
    auto_play: bool = False,
    next_episode: bool = False,
    episode_selector: bool = False,
    progress: int | None = None,
    subtitle_lang: str | None = "en",
) -> str:
    """
    Build Vidking embed URL for a TV series episode.
    subtitle_lang: e.g. "en" for English-only subtitles (if supported by player).
    """
    path = f"{BASE_URL}/tv/{tmdb_id}/{season}/{episode}"
    params = _embed_params(color=color, auto_play=auto_play, progress=progress, subtitle_lang=subtitle_lang)
    if next_episode:
        params["nextEpisode"] = "true"
    if episode_selector:
        params["episodeSelector"] = "true"
    if params:
        path += "?" + urlencode(params)
    return path
