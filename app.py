"""
Vimflix - Streamlit frontend. Uses catalog + embed providers (Vidking, VidLink, VidNest, VidSrc, 2Embed).
Run: streamlit run app.py --server.port 8501
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import streamlit as st

# Reduce WebSocketClosedError noise when users close the tab or disconnect
logging.getLogger("tornado").setLevel(logging.WARNING)
logging.getLogger("tornado.application").setLevel(logging.WARNING)

from catalog import (
    all_genres_movies,
    get_anime,
    get_movies,
    get_tv_series,
)
from providers import PROVIDER_NAMES, get_movie_embed_url, get_tv_embed_url

POSTER_BASE = "https://image.tmdb.org/t/p/"
POSTERS_PATH = Path(__file__).resolve().parent / "posters.json"
COLS_PER_ROW = 6
RECENTLY_PLAYED_MAX = 10
WATCH_PROGRESS_MAX = 10
TITLE_BUTTON_MAX = 26


def _progress_key(tmdb_id: int | str, is_tv: bool, season: int, episode: int) -> str:
    """Unique key for progress store: movie or tv SxEy."""
    s = 0 if not is_tv else season
    e = 0 if not is_tv else episode
    return f"{tmdb_id}_{'t' if is_tv else 'm'}_{s}_{e}"


def get_stored_progress(tmdb_id: int | str, is_tv: bool, season: int, episode: int) -> int | None:
    """Return stored progress in seconds for this title, or None."""
    store = st.session_state.get("watch_progress") or {}
    key = _progress_key(tmdb_id, is_tv, season, episode)
    return store.get(key)


def set_stored_progress(tmdb_id: int | str, is_tv: bool, season: int, episode: int, progress_seconds: int) -> None:
    """Store progress (seconds) for this title; keep only last WATCH_PROGRESS_MAX entries."""
    if "watch_progress" not in st.session_state:
        st.session_state["watch_progress"] = {}
    if "watch_progress_order" not in st.session_state:
        st.session_state["watch_progress_order"] = []
    key = _progress_key(tmdb_id, is_tv, season, episode)
    st.session_state["watch_progress"][key] = progress_seconds
    order = st.session_state["watch_progress_order"]
    if key in order:
        order.remove(key)
    order.append(key)
    while len(order) > WATCH_PROGRESS_MAX:
        old = order.pop(0)
        st.session_state["watch_progress"].pop(old, None)


def title_label(item: dict, suffix: str = "") -> str:
    t = (item.get("title") or "").strip()
    if suffix:
        t = f"{t} {suffix}".strip()
    if len(t) > TITLE_BUTTON_MAX:
        return t[: TITLE_BUTTON_MAX - 1].rstrip() + "…"
    return t or "Play"


@st.cache_data(ttl=300)
def load_catalog_with_posters() -> tuple[list[dict], list[dict], list[dict]]:
    """Load movies, TV, anime and merge poster_path from posters.json."""
    movies = get_movies()
    tv = get_tv_series()
    anime = get_anime()

    posters: dict = {"movie": {}, "tv": {}}
    if POSTERS_PATH.is_file():
        try:
            posters = json.loads(POSTERS_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logging.getLogger(__name__).warning("Could not load posters.json: %s", e)

    for item in movies:
        item["poster_path"] = posters.get("movie", {}).get(str(item["tmdb_id"]))
    for item in tv:
        item["poster_path"] = posters.get("tv", {}).get(str(item["tmdb_id"]))
    for item in anime:
        kind = "tv" if item.get("type") == "tv" else "movie"
        item["poster_path"] = posters.get(kind, {}).get(str(item["tmdb_id"]))

    return movies, tv, anime


def poster_url(item: dict, size: str = "w342") -> str | None:
    path = item.get("poster_path")
    if not path:
        return None
    return POSTER_BASE + size + path


def push_recently_played(item: dict, is_tv: bool, season: int = 1, episode: int = 1) -> None:
    """Prepend one entry to recently_played (max RECENTLY_PLAYED_MAX)."""
    if "recently_played" not in st.session_state:
        st.session_state["recently_played"] = []
    rec = {
        "title": item.get("title", f"TMDB {item.get('tmdb_id')}"),
        "tmdb_id": item["tmdb_id"],
        "is_tv": is_tv,
        "season": season,
        "episode": episode,
        "year": item.get("year"),
        "genre": item.get("genre"),
        "poster_path": item.get("poster_path"),
    }
    recent = st.session_state["recently_played"]
    # avoid duplicate at top (same tmdb_id + type + season + episode)
    recent = [r for r in recent if not (
        r["tmdb_id"] == rec["tmdb_id"] and r["is_tv"] == rec["is_tv"]
        and r.get("season") == rec["season"] and r.get("episode") == rec["episode"]
    )]
    st.session_state["recently_played"] = [rec] + recent[:RECENTLY_PLAYED_MAX - 1]


def _find_item_by_tmdb_id(
    tmdb_id: int,
    movies: list[dict],
    tv: list[dict],
    anime: list[dict],
) -> tuple[dict, bool] | None:
    """Return (item, is_tv) from catalog or None."""
    for m in movies:
        if m.get("tmdb_id") == tmdb_id:
            return (m, False)
    for t in tv:
        if t.get("tmdb_id") == tmdb_id:
            return (t, True)
    for a in anime:
        if a.get("tmdb_id") == tmdb_id:
            return (a, a.get("type") == "tv")
    return None


def _playing_from_query_params(
    movies: list[dict],
    tv: list[dict],
    anime: list[dict],
) -> dict | None:
    """Build playing state from URL query params (id, t, s, e). Returns None if no id."""
    q = getattr(st, "query_params", None)
    if q is None:
        return None
    raw_id = q.get("id")
    if not raw_id:
        return None
    try:
        tmdb_id = int(str(raw_id).strip())
    except ValueError:
        return None
    is_tv = str(q.get("t", "m")).lower() == "tv"
    try:
        season = max(1, int(q.get("s", "1")))
    except (TypeError, ValueError):
        season = 1
    try:
        episode = max(1, int(q.get("e", "1")))
    except (TypeError, ValueError):
        episode = 1
    found = _find_item_by_tmdb_id(tmdb_id, movies, tv, anime)
    if found:
        item, _ = found
        item = {**item, "tmdb_id": tmdb_id}
    else:
        item = {"tmdb_id": tmdb_id, "title": f"TMDB {tmdb_id}"}
    if is_tv:
        return {
            "title": item.get("title", f"TMDB {tmdb_id}"),
            "item": item,
            "is_tv": True,
            "season": season,
            "episode": episode,
        }
    return {
        "title": item.get("title", f"TMDB {tmdb_id}"),
        "item": item,
        "is_tv": False,
        "url": get_movie_embed_url("Vidking", tmdb_id, subtitle_lang="en"),
    }


def _sync_url_from_playing(playing: dict | None, season: int | None = None, episode: int | None = None) -> None:
    """Update browser URL query params to match playing state."""
    q = getattr(st, "query_params", None)
    if q is None:
        return
    if not playing:
        q.clear()
        return
    item = playing.get("item") or {}
    tmdb_id = item.get("tmdb_id")
    if tmdb_id is None:
        return
    q["id"] = str(tmdb_id)
    if playing.get("is_tv"):
        q["t"] = "tv"
        q["s"] = str(season if season is not None else playing.get("season", 1))
        q["e"] = str(episode if episode is not None else playing.get("episode", 1))
    else:
        q["t"] = "m"
        for key in ("s", "e"):
            if key in q:
                del q[key]


def start_playing(
    item: dict,
    is_tv: bool,
    season: int = 1,
    episode: int = 1,
    opts: dict | None = None,
) -> None:
    """Set now-playing state, push to recently played, sync URL, and rerun."""
    push_recently_played(item, is_tv, season, episode)
    opts = opts or {}
    if is_tv:
        st.session_state["playing"] = {
            "title": item.get("title", f"TMDB {item['tmdb_id']}"),
            "item": item,
            "is_tv": True,
            "season": season,
            "episode": episode,
        }
    else:
        st.session_state["playing"] = {
            "title": item.get("title", f"TMDB {item['tmdb_id']}"),
            "item": item,
            "is_tv": False,
            "url": get_movie_embed_url(
                opts.get("provider", "Vidking"),
                item["tmdb_id"],
                color=opts.get("color"),
                auto_play=opts.get("auto_play", False),
                subtitle_lang=opts.get("subtitle_lang", "en"),
            ),
        }
    _sync_url_from_playing(st.session_state["playing"], season=season, episode=episode)
    st.rerun()


def main() -> None:
    st.set_page_config(page_title="Vimflix", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")
    st.markdown(
        """
        <style>
        /* Base theme */
        .stApp { background: linear-gradient(180deg, #0c0c0e 0%, #12121a 100%); min-height: 100vh; }
        [data-testid="stVerticalBlock"] > div { padding: 0.25rem 0; }
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #0e0e12; border-right: 1px solid rgba(255,255,255,0.06);
        }
        section[data-testid="stSidebar"] .stMarkdown { color: #a0a0a8; }
        section[data-testid="stSidebar"] input { background: #1a1a20 !important; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); }
        section[data-testid="stSidebar"] .stSelectbox > div { background: #1a1a20; border-radius: 8px; }
        /* Cards: poster + caption + button */
        .poster-card { background: #16161c; border-radius: 10px; overflow: hidden; border: 1px solid rgba(255,255,255,0.06); }
        /* Buttons */
        .stButton > button {
            width: 100%; font-weight: 500; border-radius: 8px; border: none;
            background: rgba(255,255,255,0.07); color: #e2e2e8;
            transition: background 0.15s ease, color 0.15s ease;
        }
        .stButton > button:hover { background: rgba(229,9,20,0.85); color: #fff; }
        /* Headers */
        h1, h2, h3 { color: #f0f0f4 !important; font-weight: 600 !important; letter-spacing: -0.02em; }
        .stHeader { color: #f0f0f4; }
        /* Poster placeholder when no image */
        .poster-placeholder {
            width: 100%; aspect-ratio: 2/3; background: #1a1a20; border-radius: 8px;
            display: flex; align-items: center; justify-content: center; color: #505058; font-size: 12px;
        }
        /* Expander */
        .streamlit-expanderHeader { background: #16161c; border-radius: 8px; }
        /* Player area */
        iframe { border-radius: 8px; }
        /* Captions under posters */
        .stCaption { color: #808088 !important; font-size: 0.85rem; }
        /* Sidebar home link (first button) */
        section[data-testid="stSidebar"] .stButton:first-of-type > button {
            background: transparent !important; color: #f0f0f4 !important; font-size: 1.5rem !important; font-weight: 700 !important;
            box-shadow: none !important; padding: 0.25rem 0 !important;
        }
        section[data-testid="stSidebar"] .stButton:first-of-type > button:hover {
            background: transparent !important; color: #fff !important; text-decoration: underline;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "playing" not in st.session_state:
        st.session_state["playing"] = None
    if "recently_played" not in st.session_state:
        st.session_state["recently_played"] = []
    if "watch_progress" not in st.session_state:
        st.session_state["watch_progress"] = {}
    if "watch_progress_order" not in st.session_state:
        st.session_state["watch_progress_order"] = []

    movies, tv, anime = load_catalog_with_posters()
    # Deep link: set playing from URL if ?id=... is present
    from_url = _playing_from_query_params(movies, tv, anime)
    if from_url is not None:
        st.session_state["playing"] = from_url
    genres = ["All"] + all_genres_movies()

    with st.sidebar:
        if st.button("Vimflix", key="sidebar_home"):
            st.session_state["playing"] = None
            _sync_url_from_playing(None)
            if "search_input" in st.session_state:
                st.session_state["search_input"] = ""
            st.rerun()
        st.caption("Search by title")
        search = st.text_input(
            "Search by title",
            placeholder="e.g. demon, inception",
            help="Filter by keyword. Press Enter to search.",
            key="search_input",
            label_visibility="collapsed",
        )
        search = (search or "").strip()
        # When user submits a new search, close the player and show results
        prev_search = st.session_state.get("search_value_prev", None)
        if prev_search is not None and search != prev_search:
            st.session_state["playing"] = None
            _sync_url_from_playing(None)
        st.session_state["search_value_prev"] = search
        genre_filter = st.selectbox("Genre (movies)", genres, index=0)
        st.caption("Year range")
        y_col1, y_col2 = st.columns(2)
        with y_col1:
            year_from = st.number_input("From", min_value=1900, max_value=2030, value=1900, key="year_from")
        with y_col2:
            year_to = st.number_input("To", min_value=1900, max_value=2030, value=2030, key="year_to")
        sort_year = st.selectbox(
            "Sort by year",
            ["None", "Newest first", "Oldest first"],
            index=0,
            key="sort_year",
        )
        autoplay = st.checkbox("Auto-play", value=False)
        st.caption("Player")
        player_color = st.selectbox(
            "Accent color",
            ["Default", "Red", "Blue", "Green", "Purple", "Orange"],
            index=0,
            key="player_color",
            label_visibility="collapsed",
        )
        color_map = {
            "Default": None,
            "Red": "e50914",
            "Blue": "1e90ff",
            "Green": "2ecc71",
            "Purple": "9b59b6",
            "Orange": "e67e22",
        }
        embed_color = color_map.get(player_color)
        stream_provider = st.selectbox(
            "Stream provider",
            PROVIDER_NAMES,
            index=0,
            key="stream_provider",
            help="Vidking works in-page. Others may show 'disable sandbox'—use 'Open in new tab' below the player.",
        )

    def matches_search(item: dict, q: str) -> bool:
        if not q or not q.strip():
            return True
        return q.strip().lower() in (item.get("title") or "").lower()

    y_min, y_max = min(year_from, year_to), max(year_from, year_to)

    def in_year_range(item: dict) -> bool:
        y = item.get("year")
        if y is None:
            y = 0
        try:
            y = int(y)
        except (TypeError, ValueError):
            y = 0
        return y_min <= y <= y_max

    def apply_sort(lst: list[dict], reverse: bool | None) -> list[dict]:
        if reverse is None:
            return lst
        return sorted(lst, key=lambda x: (x.get("year") or 0), reverse=reverse)

    movies_f = [m for m in movies if matches_search(m, search) and in_year_range(m)]
    tv_f = [t for t in tv if matches_search(t, search) and in_year_range(t)]
    anime_f = [a for a in anime if matches_search(a, search) and in_year_range(a)]

    has_search = bool(search and search.strip())
    if genre_filter != "All":
        movies_f = [m for m in movies_f if m.get("genre") == genre_filter]

    sort_reverse = {"None": None, "Newest first": True, "Oldest first": False}[sort_year]
    movies_f = apply_sort(movies_f, sort_reverse)
    tv_f = apply_sort(tv_f, sort_reverse)
    anime_f = apply_sort(anime_f, sort_reverse)

    opts = {"auto_play": autoplay, "subtitle_lang": "en", "color": embed_color, "provider": stream_provider}

    # Header
    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

    # Play by TMDB ID (in expander to keep main view clean)
    with st.expander("Play by TMDB ID", expanded=False):
        id_col, type_col, btn_col = st.columns([2, 1, 1])
        with id_col:
            tmdb_id_input = st.text_input("TMDB ID", placeholder="e.g. 27205", key="tmdb_id_input", label_visibility="collapsed")
        with type_col:
            id_type = st.selectbox("Type", ["Movie", "TV"], key="tmdb_id_type", label_visibility="collapsed")
        with btn_col:
            play_by_id_clicked = st.button("Play by ID", key="play_by_tmdb_id")
        if id_type == "TV":
            s_col, e_col, _ = st.columns([1, 1, 4])
            with s_col:
                id_season = st.number_input("Season", min_value=1, value=1, key="tmdb_id_season")
            with e_col:
                id_episode = st.number_input("Episode", min_value=1, value=1, key="tmdb_id_episode")
        else:
            id_season = id_episode = 1
        if play_by_id_clicked and tmdb_id_input and tmdb_id_input.strip():
            try:
                tid = int(tmdb_id_input.strip())
            except ValueError:
                st.error("Please enter a valid numeric TMDB ID.")
            else:
                synthetic = {"tmdb_id": tid, "title": f"TMDB {tid} ({id_type})"}
                start_playing(synthetic, is_tv=(id_type == "TV"), season=id_season, episode=id_episode, opts=opts)

    # Now playing
    playing = st.session_state["playing"]
    if playing:
        title = playing["title"]
        is_tv = playing["is_tv"]
        item = playing["item"]
        col_close, _ = st.columns([1, 5])
        with col_close:
            if st.button("Close player"):
                st.session_state["playing"] = None
                _sync_url_from_playing(None)
                st.rerun()
        # Resume: when this title/episode changes, init Start at (min) from stored progress
        if is_tv:
            season_for_key = st.session_state.get("play_season", playing.get("season", 1))
            episode_for_key = st.session_state.get("play_episode", playing.get("episode", 1))
        else:
            season_for_key = episode_for_key = 0
        current_key = _progress_key(item["tmdb_id"], is_tv, season_for_key, episode_for_key)
        if st.session_state.get("_progress_key") != current_key:
            st.session_state["_progress_key"] = current_key
            stored = get_stored_progress(item["tmdb_id"], is_tv, season_for_key, episode_for_key)
            st.session_state["start_at_min"] = (stored or 0) // 60
        if is_tv:
            c1, c2, c3 = st.columns([1, 1, 4])
            with c1:
                season = st.number_input("Season", min_value=1, value=playing.get("season", 1), key="play_season")
            with c2:
                episode = st.number_input("Episode", min_value=1, value=playing.get("episode", 1), key="play_episode")
            _sync_url_from_playing(playing, season=season, episode=episode)
            start_at_min = st.number_input(
                "Start at (min)",
                min_value=0,
                value=st.session_state.get("start_at_min", 0),
                key="start_at_min",
                step=1,
                help="Resume from this minute. Progress is saved for the last 10 items.",
            )
            progress = (start_at_min * 60) if start_at_min > 0 else None
            if progress is not None and progress > 0:
                set_stored_progress(item["tmdb_id"], True, season, episode, progress)
            play_opts = {**opts, "progress": progress} if progress is not None else opts
            url = get_tv_embed_url(
                opts.get("provider", "Vidking"),
                item["tmdb_id"],
                season,
                episode,
                color=play_opts.get("color"),
                auto_play=play_opts.get("auto_play", False),
                progress=play_opts.get("progress"),
                subtitle_lang=play_opts.get("subtitle_lang", "en"),
                next_episode=True,
                episode_selector=True,
            )
        else:
            start_at_min = st.number_input(
                "Start at (min)",
                min_value=0,
                value=st.session_state.get("start_at_min", 0),
                key="start_at_min",
                step=1,
                help="Resume from this minute. Progress is saved for the last 10 items.",
            )
            progress = (start_at_min * 60) if start_at_min > 0 else None
            if progress is not None and progress > 0:
                set_stored_progress(item["tmdb_id"], False, 0, 0, progress)
            play_opts = {**opts, "progress": progress} if progress is not None else opts
            url = get_movie_embed_url(
                opts.get("provider", "Vidking"),
                item["tmdb_id"],
                color=play_opts.get("color"),
                auto_play=play_opts.get("auto_play", False),
                progress=play_opts.get("progress"),
                subtitle_lang=play_opts.get("subtitle_lang", "en"),
            )
        st.markdown(f"**Now playing:** *{title}*")
        # If embed shows "please disable sandbox", open in new tab (Streamlit's iframe is sandboxed)
        url_safe = url.replace("&", "&amp;").replace('"', "&quot;")
        st.markdown(
            f'<p style="margin:0 0 6px 0;color:#888;font-size:12px">'
            f'If the player shows "please disable sandbox", '
            f'<a href="{url_safe}" target="_blank" rel="noopener noreferrer">open in new tab</a>.'
            f'</p>',
            unsafe_allow_html=True,
        )
        url_esc = url.replace('"', "&quot;")
        player_html = f'''
        <iframe src="{url_esc}" width="100%" height="520" allowfullscreen allow="autoplay" style="border:0"></iframe>
        '''
        st.components.v1.html(player_html, height=545)
        st.divider()

    # Recently played (after player when playing, so user can switch quickly)
    recent = st.session_state.get("recently_played") or []
    if recent:
        st.markdown("### 🕐 Recently played")
        n_show = min(len(recent), 10)
        rcols = st.columns(n_show)
        for idx, rec in enumerate(recent[:n_show]):
            with rcols[idx]:
                _poster_or_placeholder(rec, "w154")
                label = rec["title"]
                if rec.get("year"):
                    label += f" ({rec['year']})"
                if rec["is_tv"]:
                    label += f" · S{rec.get('season', 1)}E{rec.get('episode', 1)}"
                st.caption(label[:40] + "…" if len(label) > 40 else label)
                btn_text = title_label(rec)
                if st.button(btn_text, key=f"recent_play_{rec['tmdb_id']}_{rec['is_tv']}_{idx}"):
                    item = {
                        "tmdb_id": rec["tmdb_id"],
                        "title": rec["title"],
                        "year": rec.get("year"),
                        "genre": rec.get("genre"),
                        "poster_path": rec.get("poster_path"),
                    }
                    start_playing(
                        item,
                        rec["is_tv"],
                        rec.get("season", 1),
                        rec.get("episode", 1),
                        opts=opts,
                    )
        st.divider()

    # Browse sections only when not playing
    if not playing:
        if has_search:
            st.markdown(f"**Search:** *{search.strip()}*")
            st.caption("Movies, series, and anime matching your search.")
            combined = [(m, "movie", False) for m in movies_f]
            combined += [(t, "series", True) for t in tv_f]
            combined += [(a, "anime", a.get("type") == "tv") for a in anime_f]
            show_search_results(combined, opts, "search")
        else:
            st.markdown("### ✨ Featured")
            featured = movies_f[:8]
            cols = st.columns(len(featured) or 1)
            for i, item in enumerate(featured):
                with cols[i]:
                    _poster_or_placeholder(item, "w500")
                    st.caption(f"{item.get('year', '')}")
                    if st.button(title_label(item), key=f"feat_{item['tmdb_id']}_{i}"):
                        start_playing(item, False, opts=opts)

            st.markdown("### 📈 Trending")
            trend_tab = st.tabs(["Movies", "Series", "Anime"])
            with trend_tab[0]:
                show_grid(movies_f[:24], False, opts, "trend_m")
            with trend_tab[1]:
                show_grid(tv_f[:24], True, opts, "trend_tv")
            with trend_tab[2]:
                show_grid(anime_f[:24], None, opts, "trend_a")

            st.markdown("### ⭐ Top rated")
            top_tab = st.tabs(["Movies", "Series"])
            with top_tab[0]:
                show_grid(movies_f[:24], False, opts, "top_m")
            with top_tab[1]:
                show_grid(tv_f[:24], True, opts, "top_tv")

            st.markdown("### 🎭 Genres")
            show_grid(movies_f[:36], False, opts, "genre")


def _poster_or_placeholder(item: dict, size: str = "w342") -> None:
    """Show poster image or a placeholder if missing."""
    img_url = poster_url(item, size)
    if img_url:
        st.image(img_url, use_container_width=True)
    else:
        st.markdown(
            '<div class="poster-placeholder">No poster</div>',
            unsafe_allow_html=True,
        )


def show_search_results(
    combined: list[tuple[dict, str, bool]],
    opts: dict,
    key_prefix: str,
) -> None:
    """Show single grid of search results with (movie)/(series)/(anime) labels."""
    if not combined:
        st.markdown("---")
        st.info("No titles match your search. Try a different keyword or clear the search.")
        return
    n = len(combined)
    rows = (n + COLS_PER_ROW - 1) // COLS_PER_ROW
    for row in range(rows):
        cols = st.columns(COLS_PER_ROW)
        for col_idx in range(COLS_PER_ROW):
            i = row * COLS_PER_ROW + col_idx
            if i >= n:
                break
            item, label, is_tv = combined[i]
            with cols[col_idx]:
                _poster_or_placeholder(item, "w342")
                st.caption(f"({label})")
                if st.button(title_label(item), key=f"{key_prefix}_{item['tmdb_id']}_{label}_{i}"):
                    start_playing(item, is_tv, 1, 1, opts=opts)


def show_grid(
    items: list[dict],
    is_tv: bool | None,
    opts: dict,
    key_prefix: str,
) -> None:
    if not items:
        st.caption("No titles in this section.")
        return
    n = len(items)
    rows = (n + COLS_PER_ROW - 1) // COLS_PER_ROW
    for row in range(rows):
        cols = st.columns(COLS_PER_ROW)
        for col_idx in range(COLS_PER_ROW):
            i = row * COLS_PER_ROW + col_idx
            if i >= n:
                break
            item = items[i]
            tv_item = is_tv if is_tv is not None else (item.get("type") == "tv")
            with cols[col_idx]:
                _poster_or_placeholder(item, "w342")
                st.caption(f"{item.get('year', '')}")
                if st.button(title_label(item), key=f"{key_prefix}_{item['tmdb_id']}_{i}"):
                    start_playing(item, tv_item, 1, 1, opts=opts)


if __name__ == "__main__":
    main()
