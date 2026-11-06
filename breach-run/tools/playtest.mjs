// Simulated playtest: a bot with human limits plays the map many times and reports where it dies.
//   node tools/playtest.mjs [runs=300] [noise_ms=45] [lookahead_s=1.2]
// The bot knows the map (like a player who has learned it), waits until a flip is due (no earlier than 0.25 s ahead),
// aims for the middle of the window of tap times that still let it finish, and its tap lands off by a random amount
// (noise_ms standard deviation). lookahead_s caps how far ahead it plans a tap.
// It reads the map and physics straight out of index.html, so it always tests the real game.
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const src = html.slice(html.indexOf('const SPEED'), html.indexOf('\n', html.indexOf('const SPEED'))) +
  html.slice(html.indexOf('// the one map'), html.indexOf('let S;'));
const { SPEED, R, END, OBS, MAP, hit, near, move } =
  new Function(src + 'return { SPEED, R, END, OBS, MAP, hit, near, move };')();

const [runs = 300, noiseMs = 45, look = 1.2] = process.argv.slice(2).map(Number);
const dt = 1 / 60, H = Math.round(look / dt), NEAR = [];  // NEAR[f] = obstacles near the virus at frame f
for (let f = 0; f <= END / dt + H; f++) NEAR[f] = near(f * dt * SPEED);
const dead = (f, y, m = 0) => hit(NEAR[f], f * dt * SPEED, y, f * dt, R + m);
const M = 0.015;  // the bot plans with this much room to spare, like a player who doesn't shave walls; deaths use the real hitbox

// SAFE[f][q][d]: can a virus at height q / Q, moving d (1 up, 0 down), at frame f still reach the server? Worked out backwards once.
const Q = 400, F = Math.round(END / dt), q = y => Math.round(y * Q);
const SAFE = Array.from({ length: F + 1 }, (_, f) => f === F ? [new Uint8Array(Q + 1).fill(1), new Uint8Array(Q + 1).fill(1)] : null);
for (let f = F - 1; f >= 0; f--) {
  SAFE[f] = [new Uint8Array(Q + 1), new Uint8Array(Q + 1)];
  for (let i = 0; i <= Q; i++) for (const d of [0, 1]) {
    const y = i / Q, dir = d ? 1 : -1, ky = move(y, dir, dt), fy = move(y, -dir, dt);
    SAFE[f][d][i] = (!dead(f + 1, ky, M) && SAFE[f + 1][d][q(ky)]) || (!dead(f + 1, fy, M) && SAFE[f + 1][1 - d][q(fy)]) ? 1 : 0;
  }
}
const safe = (f, y, dir) => SAFE[Math.min(f, F)][dir > 0 ? 1 : 0][q(y)] === 1;

// frames from now at which the bot should tap, or null if it can wait: keep k frames, then flip, then still reach the server
function plan(f, y, dir, kmin) {  // kmin: earliest frame the next tap can land (fingers need a moment between taps)
  const until = Math.min(f + H, F);
  let ky = y;
  const ok = [];
  for (let k = 0; f + k < until; k++) {
    const fy = move(ky, -dir, dt);
    ok.push(k >= kmin && !dead(f + k + 1, fy, M) && safe(f + k + 1, fy, -dir));
    ky = move(ky, dir, dt);
    if (dead(f + k + 1, ky, M)) break;  // can't keep going this way any longer
    if (f + k + 1 === until && safe(until, ky, dir)) return null;  // no flip needed within the lookahead
  }
  const a = ok.indexOf(true);
  if (a < 0) return 0;  // doomed: panic tap
  if (a * dt > 0.25) return null;  // window still far off: wait and look again
  let b = a;
  while (ok[b + 1]) b++;
  return (a + b) / 2;
}

const GAP = 6;  // frames: a player can't tap much faster than 10 times a second
const gauss = () => Math.sqrt(-2 * Math.log(1 - Math.random())) * Math.cos(2 * Math.PI * Math.random());
const deaths = new Map(), times = [];
for (let r = 0; r < runs; r++) {
  let y = 0.5, dir = -1, f = 0, tapAt = null, lastTap = -99;
  for (; f * dt < END; f++) {
    if (tapAt === null) {
      const p = plan(f, y, dir, lastTap + GAP - f - 1);
      if (p !== null) tapAt = Math.max(f + 1, lastTap + 1, Math.round(f + 1 + p + gauss() * noiseMs / 1000 / dt));
    }
    if (tapAt === f + 1) { dir = -dir; tapAt = null; lastTap = f + 1; }
    y = move(y, dir, dt);
    if (dead(f + 1, y)) break;
  }
  const t = Math.min(END, (f + 1) * dt);
  times.push(t);
  if (t < END) {  // blame the map entry closest ahead of / at the virus
    const x = t * SPEED, e = MAP.reduce((b, m) => Math.abs(m[1] * SPEED - x) < Math.abs(b[1] * SPEED - x) ? m : b);
    const key = `${e[0]} @ ${e[1]} s`;
    deaths.set(key, (deaths.get(key) ?? 0) + 1);
  }
}

const pct = n => (100 * n / runs).toFixed(0).padStart(3) + '%';
console.log(`${runs} runs, tap timing noise ${noiseMs} ms, plans ${look} s ahead`);
console.log(`reached the server ${pct(times.filter(t => t >= END).length)}`);
for (const s of [50, 75]) console.log(`reached ${s}%          ${pct(times.filter(t => t >= END * s / 100).length)}`);
console.log('deaths by obstacle:');
for (const [k, n] of [...deaths].sort((a, b) => b[1] - a[1])) console.log(`  ${pct(n)}  ${k}`);
