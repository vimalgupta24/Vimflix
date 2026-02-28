# Vimflix

Stream movies, TV series, and anime using the [Vidking](https://www.vidking.net/documentation) embeddable player. **Python only:** Streamlit frontend + catalog/vidking modules (no HTML/JavaScript).

## Features

- **Streamlit UI** – Featured, Trending (Movies / Series / Anime), Top rated, Genres. Search and genre filter in sidebar.
- **Poster images** – Loaded from `posters.json` (see below) when present.
- **Player** – Multiple embed providers: **Vidking**, **VidLink**, **VidNest**, **VidSrc**, **2Embed**. Choose in sidebar (Stream provider). Auto-play; season/episode for TV; accent color; **Start at (min)** to resume. Progress for the last 10 watched items (per title/episode) is stored and used to resume when you reopen from history.
- **Large catalog** – Hundreds of movies, series, and anime in `catalog.py`; expand with `tmdb_lookup.py`.

## Run

```bash
./run_streamlit_vidking.sh
```

Open http://localhost:8501. Or: `pip install -r requirements.txt && streamlit run app.py --server.port 8501`

## Usage

1. Use **Search** (press Enter) and **Genre** in the sidebar to filter.
2. Click a **title** on any card to play. The Vidking player appears at the top.
3. For TV/Anime series, set **Season** and **Episode** above the player.
4. Click **Close player** to hide the player.

## Poster images

To show **poster images** (TMDB), run once (requires TMDB API key):

```bash
export TMDB_API_KEY=your_key
python fetch_posters.py
```

This creates `posters.json`. Restart the Streamlit app and reload the page to see posters. Re-run when you add new titles to the catalog.

## TMDB lookup tool

Adding titles to `catalog.py` requires **TMDB IDs**. Use the included CLI:

1. **Get a free API key:** [TMDB API](https://www.themoviedb.org/settings/api) → Create → copy key.
2. **Set it:** `export TMDB_API_KEY=your_key`
3. **From this directory:**
   ```bash
   pip install -r requirements.txt
   python tmdb_lookup.py "Inception"
   python tmdb_lookup.py "Breaking Bad" --type tv
   python tmdb_lookup.py "Dune" --year 2021 --catalog   # catalog tuple with TMDB genre
   python tmdb_lookup.py "Squid Game" --pick 1          # print only tmdb_id (for scripts)
   python tmdb_lookup.py "The Crown" --json             # machine-readable output
   ```
   - **--type** `movie` | `tv` | `both` (default: both)
   - **--year** YYYY – filter by release/first_air year
   - **--limit** N – max results per type (default 10)
   - **--catalog** – print `(title, tmdb_id, genre, year)` lines; genre from TMDB when available
   - **--pick** N – output only the N-th result’s tmdb_id (1-based)
   - **--json** – output results as JSON

## Embed providers

Vimflix supports several TMDB-based embed players (choose **Stream provider** in the sidebar):

| Provider   | Movies | TV |
|-----------|--------|-----|
| **Vidking** | vidking.net/embed/movie/{id} | …/tv/{id}/{s}/{e} |
| **VidLink** | vidlink.pro/movie/{id} | …/tv/{id}/{s}/{e} |
| **VidNest** | vidnest.fun/movie/{id} | …/tv/{id}/{s}/{e} |
| **VidSrc**  | vidsrc.store/embed/movie/{id} | …/embed/tv/{id}/{s}/{e} |
| **2Embed**  | 2embed.stream/embed/movie/{id} | …/embed/tv/{id}/{s}/{e} |

Common params (where supported): `color`, `autoPlay`/`autoplay`, `progress`/`startAt` (seconds). Vimflix maps these from the sidebar (Accent color, Auto-play) and player **Start at (min)**.

## Architecture & rewrite plan

For a **microservice-style rewrite** (clean architecture, Controller → Service → Repository, proper config/logging/tests), see:

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** – target architecture, package layout, API contract, migration path.
- **[docs/REFACTOR_CHECKLIST.md](docs/REFACTOR_CHECKLIST.md)** – step-by-step refactor checklist.

## Module layout

- `app.py` – **Streamlit frontend** (catalog, posters, embed)
- `catalog.py` – Movies, TV, anime data with genres
- `providers.py` – Multi-provider embed URL builder (Vidking, VidLink, VidNest, VidSrc, 2Embed)
- `vidking.py` – Vidking-only helpers (optional; providers.py uses same URL logic)
- `tmdb_lookup.py` – CLI: search by title → tmdb_id + genre (needs TMDB_API_KEY)
- `fetch_posters.py` – one-time: fetch TMDB poster paths → posters.json (needs TMDB_API_KEY)
- `posters.json` – optional; when present, app shows poster images
- `requirements.txt` – streamlit, requests
- `run_streamlit_vidking.sh` – Launcher
- `server.py` – optional FastAPI app (static + `/api/catalog`) if you want a separate API; main UI is Streamlit.
