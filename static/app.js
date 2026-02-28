(function () {
  const BASE = 'https://www.vidking.net/embed';
  let catalog = { movies: [], tv: [], anime: [], genres: {} };
  let trendSection = 'movies';
  let topSection = 'movies';
  let selectedGenre = 'All';
  let currentTvItem = null;
  let searchDebounce = null;

  function buildMovieUrl(tmdbId, opts) {
    const p = new URLSearchParams();
    if (opts.color) p.set('color', opts.color.replace('#', ''));
    if (opts.autoPlay) p.set('autoPlay', 'true');
    if (opts.progress) p.set('progress', String(opts.progress || 0));
    const q = p.toString();
    return BASE + '/movie/' + tmdbId + (q ? '?' + q : '');
  }

  function buildTvUrl(tmdbId, season, episode, opts) {
    const p = new URLSearchParams();
    if (opts.color) p.set('color', opts.color.replace('#', ''));
    if (opts.autoPlay) p.set('autoPlay', 'true');
    p.set('nextEpisode', 'true');
    p.set('episodeSelector', 'true');
    if (opts.progress) p.set('progress', String(opts.progress));
    const q = p.toString();
    return BASE + '/tv/' + tmdbId + '/' + season + '/' + episode + (q ? '?' + q : '');
  }

  function getOpts() {
    return {
      color: document.getElementById('theme').value,
      autoPlay: document.getElementById('autoplay').checked,
      progress: 0,
    };
  }

  function getSeasonEpisode() {
    return {
      season: parseInt(document.getElementById('season').value, 10) || 1,
      episode: parseInt(document.getElementById('episode').value, 10) || 1,
    };
  }

  const POSTER_BASE = 'https://image.tmdb.org/t/p/';

  function escapeHtml(s) {
    const el = document.createElement('div');
    el.textContent = s;
    return el.innerHTML;
  }

  function posterUrl(item, size) {
    if (!item || !item.poster_path) return '';
    return POSTER_BASE + (size || 'w342') + item.poster_path;
  }

  function posterImg(item, size, cssClass) {
    var url = posterUrl(item, size);
    if (url) return '<img class="absolute inset-0 w-full h-full object-cover ' + (cssClass || '') + '" src="' + escapeHtml(url) + '" alt="" loading="lazy" onerror="this.style.display=\'none\';var n=this.nextElementSibling;if(n)n.style.display=\'flex\'" /><div class="absolute inset-0 flex items-center justify-center text-white/20 text-2xl poster" style="display:none;background:linear-gradient(145deg,#1c1b22,#252330)"><i class="fas fa-film"></i></div>';
    return '<div class="absolute inset-0 flex items-center justify-center text-white/20 text-2xl poster"><i class="fas fa-film"></i></div>';
  }

  function playItem(item, isTv) {
    const opts = getOpts();
    if (isTv) {
      currentTvItem = item;
      const { season, episode } = getSeasonEpisode();
      const url = buildTvUrl(item.tmdb_id, season, episode, opts);
      document.getElementById('playing-title').textContent = item.title + ' · S' + season + 'E' + episode;
      document.getElementById('player-iframe').src = url;
      document.getElementById('tv-controls').classList.remove('hidden');
    } else {
      currentTvItem = null;
      const url = buildMovieUrl(item.tmdb_id, opts);
      document.getElementById('playing-title').textContent = item.title;
      document.getElementById('player-iframe').src = url;
      document.getElementById('tv-controls').classList.add('hidden');
    }
    document.getElementById('player-area').classList.remove('hidden');
    document.getElementById('player-backdrop').classList.remove('hidden');
  }

  function applyTvEpisode() {
    if (!currentTvItem) return;
    const { season, episode } = getSeasonEpisode();
    const url = buildTvUrl(currentTvItem.tmdb_id, season, episode, getOpts());
    document.getElementById('playing-title').textContent = currentTvItem.title + ' · S' + season + 'E' + episode;
    document.getElementById('player-iframe').src = url;
  }

  function heroCard(item, isTv) {
    const div = document.createElement('div');
    div.className = 'hero-poster poster rounded-lg overflow-hidden shrink-0 w-64 sm:w-72 card-hover cursor-pointer';
    div.innerHTML =
      '<div class="relative h-36 flex items-end p-3 bg-zinc-900">' +
      '<div class="absolute inset-0">' + posterImg(item, 'w500', '') + '</div>' +
      '<div class="relative z-10 w-full">' +
      '<div class="text-xs text-amber-400/90 font-medium">' + escapeHtml(String(item.year)) + ' · ' + escapeHtml(item.genre) + '</div>' +
      '</div></div>' +
      '<div class="p-2.5 bg-zinc-900/95">' +
      '<h3 class="font-semibold text-white text-sm truncate">' + escapeHtml(item.title) + '</h3>' +
      '<button type="button" class="play-btn mt-1.5 w-full py-1.5 rounded bg-red-600 hover:bg-red-500 text-white text-xs font-medium">Play</button>' +
      '</div>';
    div.querySelector('.play-btn').addEventListener('click', function (e) { e.stopPropagation(); playItem(item, isTv); });
    div.addEventListener('click', function (e) { if (!e.target.closest('.play-btn')) { e.preventDefault(); playItem(item, isTv); } });
    return div;
  }

  function trendCard(item, isTv) {
    const div = document.createElement('div');
    div.className = 'trend-card shrink-0 card-hover rounded-lg overflow-hidden bg-zinc-800/90 border border-white/5';
    div.innerHTML =
      '<div class="relative h-20 bg-zinc-800">' + posterImg(item, 'w154', '') + '</div>' +
      '<div class="p-2">' +
      '<div class="text-xs text-amber-400/90">' + escapeHtml(String(item.year)) + '</div>' +
      '<div class="font-medium text-white text-sm truncate mt-0.5">' + escapeHtml(item.title) + '</div>' +
      '<button type="button" class="play-trend mt-1 w-full py-1 rounded bg-red-600/80 hover:bg-red-500 text-white text-xs">Play</button>' +
      '</div>';
    div.querySelector('.play-trend').addEventListener('click', function () { playItem(item, isTv); });
    return div;
  }

  function gridCard(item, isTv) {
    const div = document.createElement('div');
    div.className = 'rounded-lg overflow-hidden bg-zinc-800/90 border border-white/5 card-hover';
    div.innerHTML =
      '<div class="relative aspect-[2/3] bg-zinc-800">' + posterImg(item, 'w342', '') + '</div>' +
      '<div class="p-2">' +
      '<div class="text-xs text-amber-400/90">' + escapeHtml(String(item.year)) + '</div>' +
      '<div class="font-medium text-white text-sm truncate mt-0.5">' + escapeHtml(item.title) + '</div>' +
      '<div class="text-xs text-gray-500 mt-0.5">' + escapeHtml(item.genre) + '</div>' +
      '<button type="button" class="play-grid mt-1.5 w-full py-1 rounded bg-red-600/80 hover:bg-red-500 text-white text-xs">Play</button>' +
      '</div>';
    div.querySelector('.play-grid').addEventListener('click', function () { playItem(item, isTv); });
    return div;
  }

  function getTrendingItems() {
    if (trendSection === 'movies') return catalog.movies.slice(0, 24);
    if (trendSection === 'tv') return catalog.tv.slice(0, 24);
    return catalog.anime.slice(0, 24);
  }

  function getTopItems() {
    const list = topSection === 'movies' ? catalog.movies : catalog.tv;
    return list.slice(0, 24);
  }

  function getGenreItems() {
    if (selectedGenre === 'All') return catalog.movies;
    return catalog.movies.filter(function (m) { return m.genre === selectedGenre; });
  }

  function appendAll(parent, items, cardFn, isTvFn) {
    const frag = document.createDocumentFragment();
    for (var i = 0; i < items.length; i++) frag.appendChild(cardFn(items[i], isTvFn ? isTvFn(items[i]) : false));
    parent.appendChild(frag);
  }

  function renderHero() {
    const row = document.getElementById('hero-row');
    row.innerHTML = '';
    appendAll(row, catalog.movies.slice(0, 8), heroCard, function () { return false; });
  }

  function renderTrending() {
    const row = document.getElementById('trending-row');
    row.innerHTML = '';
    var items = getTrendingItems();
    var isTv = trendSection === 'tv' || (trendSection === 'anime');
    appendAll(row, items, trendCard, trendSection === 'anime' ? function (item) { return item.type === 'tv'; } : function () { return isTv; });
  }

  function renderTopRated() {
    const grid = document.getElementById('top-rated-grid');
    grid.innerHTML = '';
    var items = getTopItems();
    var isTv = topSection === 'tv';
    appendAll(grid, items, gridCard, function () { return isTv; });
  }

  function renderGenreGrid() {
    const grid = document.getElementById('genre-grid');
    grid.innerHTML = '';
    appendAll(grid, getGenreItems(), gridCard, function () { return false; });
  }

  function renderGenres() {
    const pillsEl = document.getElementById('genre-pills');
    var genres = catalog.genres.movies || ['All'];
    pillsEl.innerHTML = genres.map(function (g) {
      var active = g === selectedGenre ? ' active' : '';
      return '<button type="button" class="genre-pill' + active + ' px-3 py-1.5 rounded-full text-sm bg-white/10 text-gray-300 hover:bg-white/15" data-genre="' + escapeHtml(g) + '">' + escapeHtml(g) + '</button>';
    }).join('');
    pillsEl.querySelectorAll('.genre-pill').forEach(function (btn) {
      btn.addEventListener('click', function () {
        selectedGenre = btn.dataset.genre;
        pillsEl.querySelectorAll('.genre-pill').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        renderGenreGrid();
      });
    });
    renderGenreGrid();
  }

  function filterBySearch(q) {
    q = (q || '').trim().toLowerCase();
    if (!q) return { movies: catalog.movies, tv: catalog.tv, anime: catalog.anime };
    var match = function (x) { return (x.title || '').toLowerCase().indexOf(q) !== -1; };
    return { movies: catalog.movies.filter(match), tv: catalog.tv.filter(match), anime: catalog.anime.filter(match) };
  }

  function renderSearchResults() {
    var q = document.getElementById('search').value;
    var filtered = filterBySearch(q);
    var total = filtered.movies.length + filtered.tv.length + filtered.anime.length;
    var row = document.getElementById('trending-row');
    if (total === 0 && q) {
      row.innerHTML = '<p class="text-gray-500 py-6 text-sm">No results for "' + escapeHtml(q) + '"</p>';
      return;
    }
    if (!q) { renderTrending(); return; }
    row.innerHTML = '';
    var all = filtered.movies.map(function (m) { return { item: m, isTv: false }; })
      .concat(filtered.tv.map(function (m) { return { item: m, isTv: true }; }))
      .concat(filtered.anime.map(function (m) { return { item: m, isTv: m.type === 'tv' }; }));
    var frag = document.createDocumentFragment();
    for (var i = 0; i < Math.min(30, all.length); i++) frag.appendChild(trendCard(all[i].item, all[i].isTv));
    row.appendChild(frag);
  }

  function onSearchInput() {
    if (searchDebounce) clearTimeout(searchDebounce);
    searchDebounce = setTimeout(renderSearchResults, 150);
  }

  function init() {
    fetch('/api/catalog', { headers: { Accept: 'application/json' } })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        catalog = data;
        renderHero();
        renderTrending();
        renderTopRated();
        renderGenres();
      })
      .catch(function () {
        document.getElementById('hero-row').innerHTML = '<p class="text-gray-500 py-4">Unable to load catalog.</p>';
      });

    document.getElementById('search').addEventListener('input', onSearchInput);
    document.getElementById('search').addEventListener('keydown', function (e) { if (e.key === 'Enter') { if (searchDebounce) clearTimeout(searchDebounce); renderSearchResults(); } });
    document.getElementById('search-btn').addEventListener('click', function () { if (searchDebounce) clearTimeout(searchDebounce); renderSearchResults(); });

    document.querySelectorAll('[data-trend]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        trendSection = btn.dataset.trend;
        document.querySelectorAll('[data-trend]').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        renderTrending();
      });
    });

    document.querySelectorAll('[data-top]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        topSection = btn.dataset.top;
        document.querySelectorAll('[data-top]').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        renderTopRated();
      });
    });

    document.getElementById('close-player').addEventListener('click', closePlayer);
    document.getElementById('player-backdrop').addEventListener('click', closePlayer);
    document.getElementById('season').addEventListener('change', applyTvEpisode);
    document.getElementById('episode').addEventListener('change', applyTvEpisode);

    function closePlayer() {
      document.getElementById('player-area').classList.add('hidden');
      document.getElementById('player-backdrop').classList.add('hidden');
      document.getElementById('player-iframe').src = '';
      document.getElementById('tv-controls').classList.add('hidden');
      currentTvItem = null;
    }
  }

  init();
})();
