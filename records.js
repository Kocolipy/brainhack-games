// Personal bests kept in this browser's localStorage, shared by the games and the landing page (same origin).
// Every game's record has completed (bool) and stars (0-3), plus its own best-score fields.
window.records = {
  get(game) {
    try { return JSON.parse(localStorage.getItem('brainhack:' + game)) || {}; } catch { return {}; }
  },
  // merge one run's result into the stored record: completed sticks, stars keep the max,
  // best(old) returns the game's own best-score fields to overwrite (or {} to keep the old ones)
  save(game, { completed = false, stars = 0 } = {}, best = () => ({})) {
    const o = this.get(game);
    const r = { ...o, ...best(o), completed: !!(o.completed || completed), stars: Math.max(o.stars ?? 0, stars) };
    try { localStorage.setItem('brainhack:' + game, JSON.stringify(r)); } catch {} // storage off (private mode): just don't record
  },
  // ★★☆ (unearned stars dimmed) and a COMPLETED tag; used by the end screens and the landing page
  badge: ({ completed = false, stars = 0 }) =>
    `<span style="color:#fd4;font-size:1.6em;letter-spacing:.15em">${'★'.repeat(stars)}<span style="opacity:.3">${'★'.repeat(3 - stars)}</span></span>` +
    (completed ? '<span style="background:#2a7a4a;color:#fff;font:800 .75em system-ui,sans-serif;letter-spacing:.1em;padding:.3em .7em;border-radius:.4em">COMPLETED</span>' : ''),
  // end screen: show one run's badge on a line right after el (made the first time, then updated)
  show(el, result) {
    let line = el.nextElementSibling;
    if (!line?.classList.contains('rating')) {
      line = document.createElement('div');
      line.className = 'rating';
      line.style.cssText = 'display:flex;gap:12px;justify-content:center;align-items:center;margin:10px 0';
      el.after(line);
    }
    line.innerHTML = this.badge(result);
  },
  // stars for reaching each of three thresholds, e.g. stars(7, [3, 7, 10]) === 2
  stars: (v, [one, two, three]) => v >= three ? 3 : v >= two ? 2 : v >= one ? 1 : 0,
};
