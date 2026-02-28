"""
Embed player providers: Vidking, VidLink, VidNest, VidSrc, 2Embed.
All use TMDB IDs. Unified opts: color (hex no #), auto_play, progress (seconds), subtitle_lang.
"""

from urllib.parse import urlencode

PROVIDER_NAMES = ["Vidking", "VidLink", "VidNest", "VidSrc", "2Embed"]


def _q(params: dict) -> str:
    if not params:
        return ""
    return "?" + urlencode({k: v for k, v in params.items() if v is not None})


def get_movie_embed_url(
    provider: str,
    tmdb_id: str | int,
    *,
    color: str | None = None,
    auto_play: bool = False,
    progress: int | None = None,
    subtitle_lang: str | None = "en",
) -> str:
    """Build movie embed URL for the given provider. progress in seconds."""
    pid = str(tmdb_id).strip()
    p = provider.strip() if provider else "Vidking"

    if p == "Vidking":
        base = "https://www.vidking.net/embed"
        path = f"{base}/movie/{pid}"
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
        return path + _q(params)

    if p == "VidLink":
        base = "https://vidlink.pro"
        path = f"{base}/movie/{pid}"
        params = {}
        if progress is not None and progress >= 0:
            params["startAt"] = str(progress)
        if auto_play:
            params["autoplay"] = "true"
        if color:
            params["primaryColor"] = color.lstrip("#")
        return path + _q(params)

    if p == "VidNest":
        base = "https://vidnest.fun"
        path = f"{base}/movie/{pid}"
        params = {}
        if progress is not None and progress >= 0:
            params["startAt"] = str(progress)
        return path + _q(params)

    if p == "VidSrc":
        base = "https://vidsrc.store"
        path = f"{base}/embed/movie/{pid}"
        return path

    if p == "2Embed":
        base = "https://www.2embed.stream"
        path = f"{base}/embed/movie/{pid}"
        return path

    # default Vidking
    return get_movie_embed_url(
        "Vidking", tmdb_id, color=color, auto_play=auto_play, progress=progress, subtitle_lang=subtitle_lang
    )


def get_tv_embed_url(
    provider: str,
    tmdb_id: str | int,
    season: int,
    episode: int,
    *,
    color: str | None = None,
    auto_play: bool = False,
    next_episode: bool = True,
    episode_selector: bool = True,
    progress: int | None = None,
    subtitle_lang: str | None = "en",
) -> str:
    """Build TV episode embed URL for the given provider. progress in seconds."""
    pid = str(tmdb_id).strip()
    s, e = int(season), int(episode)
    p = provider.strip() if provider else "Vidking"

    if p == "Vidking":
        base = "https://www.vidking.net/embed"
        path = f"{base}/tv/{pid}/{s}/{e}"
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
        if next_episode:
            params["nextEpisode"] = "true"
        if episode_selector:
            params["episodeSelector"] = "true"
        return path + _q(params)

    if p == "VidLink":
        base = "https://vidlink.pro"
        path = f"{base}/tv/{pid}/{s}/{e}"
        params = {}
        if progress is not None and progress >= 0:
            params["startAt"] = str(progress)
        if auto_play:
            params["autoplay"] = "true"
        if color:
            params["primaryColor"] = color.lstrip("#")
        return path + _q(params)

    if p == "VidNest":
        base = "https://vidnest.fun"
        path = f"{base}/tv/{pid}/{s}/{e}"
        params = {}
        if progress is not None and progress >= 0:
            params["startAt"] = str(progress)
        return path + _q(params)

    if p == "VidSrc":
        base = "https://vidsrc.store"
        path = f"{base}/embed/tv/{pid}/{s}/{e}"
        return path

    if p == "2Embed":
        base = "https://www.2embed.stream"
        path = f"{base}/embed/tv/{pid}/{s}/{e}"
        return path

    return get_tv_embed_url(
        "Vidking", tmdb_id, s, e,
        color=color, auto_play=auto_play, next_episode=next_episode, episode_selector=episode_selector,
        progress=progress, subtitle_lang=subtitle_lang,
    )
