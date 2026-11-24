/* 148AI 2D game runtime (warehouse item 134, released by the owner 2026-11-23).
 *
 * One tested engine for every game the platform builds. The model never writes engine code: it writes a game
 * DEFINITION (omni_prod/game_kit/schema.py validates it before anything runs), and this file plays it. Four kinds:
 * platformer, shooter (top-down), match (puzzle) and runner. Keyboard on the computer, on-screen buttons on a touch
 * screen, a fixed 60 Hz simulation, a seeded random source, and an end screen in the game's own language.
 *
 * window.__game is the probe's window into the REAL state (omni_prod/game_kit/probe.py): it reads, it never plays.
 * fastForward() steps the same simulation the frame loop steps, with whatever input the probe is holding.
 */
(function () {
  'use strict';
  var DEF = JSON.parse(document.getElementById('game-def').textContent);
  var W = 960, H = 540, STEP = 1 / 60;
  // a puzzle on a phone held upright gets an upright board, so each cell stays a finger's size
  if (DEF.kind === 'match' && window.innerHeight > window.innerWidth) { W = 540; H = 960; }
  var LABELS = {
    he: { left: 'שמאלה', right: 'ימינה', up: 'למעלה', down: 'למטה', jump: 'קפיצה', fire: 'ירייה', start: 'התחלה', again: 'שוב',
          lives: 'חיים', time: 'זמן', moves: 'מהלכים', paused: 'הפסקה', resume: 'המשך', rotate: 'סובבו את הטלפון לרוחב למשחק נוח יותר' },
    en: { left: 'Left', right: 'Right', up: 'Up', down: 'Down', jump: 'Jump', fire: 'Fire', start: 'Start', again: 'Play again',
          lives: 'Lives', time: 'Time', moves: 'Moves', paused: 'Paused', resume: 'Resume', rotate: 'Turn your phone sideways for a bigger game' },
    ar: { left: 'يسار', right: 'يمين', up: 'أعلى', down: 'أسفل', jump: 'قفز', fire: 'إطلاق', start: 'ابدأ', again: 'مرة أخرى',
          lives: 'أرواح', time: 'الوقت', moves: 'حركات', paused: 'إيقاف مؤقت', resume: 'متابعة', rotate: 'أدر الهاتف أفقيًا للعب أكبر' }
  };
  var L = LABELS[DEF.lang];
  if (!L) throw new Error('game: unknown language ' + DEF.lang);
  var P = DEF.palette, T = DEF.texts;

  // ---- seeded random (mulberry32): the same definition plays the same way every time ----
  var seed = (DEF.seed >>> 0) || 1;
  function rnd() { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }

  // ---- canvas, letterboxed to the window ----
  var canvas = document.getElementById('game');
  var ctx = canvas.getContext('2d');
  var view = { s: 1, ox: 0, oy: 0, dpr: 1 };
  function fit() {
    var cw = window.innerWidth, ch = window.innerHeight, dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(cw * dpr); canvas.height = Math.round(ch * dpr);
    canvas.style.width = cw + 'px'; canvas.style.height = ch + 'px';
    var s = Math.min(cw / W, ch / H);
    view = { s: s, ox: (cw - W * s) / 2, oy: (ch - H * s) / 2, dpr: dpr };
  }
  window.addEventListener('resize', fit); fit();
  function toLogical(cx, cy) { return { x: (cx - view.ox) / view.s, y: (cy - view.oy) / view.s }; }

  // ---- sound: tiny tones, only after a gesture, never fatal ----
  var audio = null;
  function tone(freq, dur) {
    if (!DEF.sound) return;
    try {
      if (!audio) audio = new (window.AudioContext || window.webkitAudioContext)();
      var o = audio.createOscillator(), g = audio.createGain();
      o.frequency.value = freq; o.type = 'square'; g.gain.value = 0.04;
      o.connect(g); g.connect(audio.destination); o.start(); o.stop(audio.currentTime + dur);
    } catch (e) { DEF.sound = false; }
  }

  // ---- input ----
  var input = { left: false, right: false, up: false, down: false, jump: false, fire: false };
  var jumpBuffer = 0;
  var KEYS = { ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right', ArrowUp: 'up', KeyW: 'up',
               ArrowDown: 'down', KeyS: 'down', Space: 'jump' };
  window.addEventListener('keydown', function (e) {
    if (e.code === 'Enter') { if (G.status !== 'playing') begin(); e.preventDefault(); return; }
    if (e.code === 'KeyP' || e.code === 'Escape') { togglePause(); e.preventDefault(); return; }
    var k = KEYS[e.code]; if (!k) return;
    e.preventDefault();
    if (G.status !== 'playing') return;
    if (DEF.kind === 'match') { matchKey(k); return; }
    press(k, true);
  });
  window.addEventListener('keyup', function (e) { var k = KEYS[e.code]; if (k) press(k, false); });
  function press(k, down) {
    if (k === 'jump') { input.jump = down; input.fire = down; if (down) jumpBuffer = 0.15; return; }
    if (k === 'up' && DEF.kind !== 'shooter') { input.jump = down; if (down) jumpBuffer = 0.15; }
    input[k] = down;
  }
  document.addEventListener('visibilitychange', function () { if (document.hidden && G.status === 'playing') togglePause(); });

  // ---- on-screen buttons on a touch screen ----
  var TOUCH = { platformer: [['left', '◀'], ['right', '▶'], ['jump', '⤒']],
                shooter: [['left', '◀'], ['right', '▶'], ['up', '▲'], ['down', '▼'], ['fire', '●']],
                runner: [['jump', '⤒']], match: [] }[DEF.kind];
  var touchCapable = (navigator.maxTouchPoints || 0) > 0 || 'ontouchstart' in window ||
                     (window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
  var pad = document.getElementById('touch'), rotate = document.getElementById('rotate');
  function hintRotate() { rotate.hidden = !(touchCapable && DEF.kind !== 'match' && window.innerHeight > window.innerWidth); }
  rotate.textContent = L.rotate; hintRotate(); window.addEventListener('resize', hintRotate);
  if (touchCapable && TOUCH.length) {
    pad.hidden = false;
    TOUCH.forEach(function (b) {
      var el = document.createElement('button');
      el.type = 'button'; el.className = 'tb tb-' + b[0]; el.textContent = b[1]; el.setAttribute('aria-label', L[b[0]]);
      var downAt = 0, timer = null;
      el.addEventListener('pointerdown', function (e) { e.preventDefault(); clearTimeout(timer); downAt = performance.now();
        if (G.status === 'playing') press(b[0], true); });
      var up = function () { var held = performance.now() - downAt;   // a quick tap still moves: held for 120 ms at least
        timer = setTimeout(function () { press(b[0], false); }, Math.max(0, 120 - held)); };
      el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up); el.addEventListener('pointerleave', up);
      pad.appendChild(el);
    });
  }

  // ---- the game state ----
  var G = { status: 'title', score: 0, lives: DEF.player.lives, time: 0, level: 0, frames: 0, steps: 0,
            fx: [], world: null };
  var screen = document.getElementById('screen'), screenTitle = document.getElementById('screen-title'),
      screenText = document.getElementById('screen-text'), screenBtn = document.getElementById('screen-btn');
  function showScreen(title, text, btn) {
    screenTitle.textContent = title; screenText.textContent = text; screenBtn.textContent = btn; screen.hidden = false;
  }
  screenBtn.addEventListener('click', function () { if (G.status === 'paused') togglePause(); else begin(); });
  canvas.addEventListener('pointerdown', function (e) {
    if (G.status !== 'playing') return;
    if (DEF.kind === 'match') { var p = toLogical(e.clientX, e.clientY); matchTap(p.x, p.y); return; }
    if (DEF.kind === 'runner') { press('jump', true); setTimeout(function () { press('jump', false); }, 120); }
  });
  function togglePause() {
    if (G.status === 'playing') { G.status = 'paused'; showScreen(L.paused, DEF.title, L.resume); }
    else if (G.status === 'paused') { G.status = 'playing'; screen.hidden = true; }
  }
  function begin() {
    seed = (DEF.seed >>> 0) || 1;
    G.status = 'playing'; G.score = 0; G.lives = DEF.player.lives; G.time = 0; G.level = 0; G.fx = [];
    for (var k in input) input[k] = false;
    KIND.init(); screen.hidden = true; tone(660, 0.08);
  }
  function end(won) {
    G.status = won ? 'won' : 'lost';
    showScreen(won ? T.win : T.lose, T.score + ': ' + G.score, L.again); tone(won ? 880 : 220, 0.25);
  }
  function hurt() {
    G.lives -= 1; tone(180, 0.12); burst(G.world.p ? G.world.p.x : W / 2, G.world.p ? G.world.p.y : H / 2, P.enemy, 14);
    if (G.lives <= 0) end(false); return G.lives > 0;
  }
  function burst(x, y, color, n) {
    for (var i = 0; i < n; i++) G.fx.push({ x: x, y: y, vx: (rnd() - 0.5) * 360, vy: (rnd() - 0.8) * 360, t: 0.6, c: color });
  }
  function hit(a, b) { return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y; }

  // ================= platformer =================
  var TS = 40;
  var platformer = {
    init: function () { this.load(G.level); },
    load: function (n) {
      var rows = DEF.levels[n].rows, w = { tiles: [], coins: [], enemies: [], spikes: [], flag: null, cols: rows[0].length,
        rows: rows.length, cam: 0 };
      w.top = H - rows.length * TS;
      for (var r = 0; r < rows.length; r++) {
        w.tiles.push([]);
        for (var c = 0; c < rows[r].length; c++) {
          var ch = rows[r][c], x = c * TS, y = w.top + r * TS;
          w.tiles[r].push(ch === '#');
          if (ch === 'o') w.coins.push({ x: x + 10, y: y + 10, w: 20, h: 20 });
          if (ch === 'E') w.enemies.push({ x: x + 4, y: y + 8, w: 32, h: 32, vx: -60, vy: 0 });
          if (ch === '^') w.spikes.push({ x: x + 4, y: y + 22, w: 32, h: 18 });
          if (ch === 'F') w.flag = { x: x + 8, y: y - TS, w: 24, h: TS * 2 };
          if (ch === 'P') w.start = { x: x + 6, y: y + 4 };
        }
      }
      w.p = { x: w.start.x, y: w.start.y, w: 28, h: 36, vx: 0, vy: 0, ground: false, inv: 0, face: 1 };
      G.world = w;
    },
    solid: function (px, py) {
      var w = G.world, c = Math.floor(px / TS), r = Math.floor((py - w.top) / TS);
      if (c < 0 || c >= w.cols) return true;
      if (r < 0 || r >= w.rows) return false;
      return w.tiles[r][c];
    },
    move: function (b, dx, dy) {
      b.x += dx;
      if (this.solid(b.x, b.y + 2) || this.solid(b.x + b.w, b.y + 2) || this.solid(b.x, b.y + b.h - 2) || this.solid(b.x + b.w, b.y + b.h - 2)) {
        b.x -= dx; if (b.vx !== undefined) b.blocked = true;
      }
      b.y += dy; b.ground = false;
      if (this.solid(b.x + 2, b.y) || this.solid(b.x + b.w - 2, b.y) || this.solid(b.x + 2, b.y + b.h) || this.solid(b.x + b.w - 2, b.y + b.h)) {
        if (dy > 0) { b.y = Math.floor((b.y + b.h - G.world.top) / TS) * TS + G.world.top - b.h - 0.01; b.ground = true; }
        else { b.y = Math.floor((b.y - G.world.top) / TS) * TS + G.world.top + TS + 0.01; }
        b.vy = 0;
      }
    },
    update: function (dt) {
      var w = G.world, p = w.p, speed = 120 + DEF.player.speed * 30;
      p.vx = (input.right ? speed : 0) - (input.left ? speed : 0);
      if (p.vx) p.face = p.vx > 0 ? 1 : -1;
      if (jumpBuffer > 0 && p.ground) { p.vy = -(450 + DEF.player.jump * 40); p.ground = false; jumpBuffer = 0; tone(520, 0.05); }
      p.vy = Math.min(p.vy + 1800 * dt, 900);
      this.move(p, p.vx * dt, p.vy * dt);
      if (p.inv > 0) p.inv -= dt;
      for (var i = w.coins.length - 1; i >= 0; i--) if (hit(p, w.coins[i])) {
        burst(w.coins[i].x + 10, w.coins[i].y + 10, P.item, 8); w.coins.splice(i, 1); G.score += 10; tone(990, 0.05); }
      for (i = w.enemies.length - 1; i >= 0; i--) {
        var e = w.enemies[i]; e.blocked = false;
        e.vy = Math.min(e.vy + 1800 * dt, 900); this.move(e, e.vx * dt, e.vy * dt);
        var ahead = e.vx < 0 ? e.x - 2 : e.x + e.w + 2;
        if (e.blocked || (e.ground && !this.solid(ahead, e.y + e.h + 4))) e.vx = -e.vx;
        if (hit(p, e)) {
          if (p.vy > 0 && p.y + p.h - e.y < 18) { burst(e.x + 16, e.y + 16, P.enemy, 12); w.enemies.splice(i, 1); p.vy = -420; G.score += 50; tone(330, 0.08); }
          else if (p.inv <= 0) { if (!hurt()) return; this.respawn(); return; }
        }
      }
      for (i = 0; i < w.spikes.length; i++) if (hit(p, w.spikes[i]) && p.inv <= 0) { if (!hurt()) return; this.respawn(); return; }
      if (p.y > H + 80) { if (!hurt()) return; this.respawn(); return; }
      if (w.flag && hit(p, w.flag)) {
        G.score += 100; burst(w.flag.x, w.flag.y + 20, P.item, 20);
        if (G.level + 1 < DEF.levels.length) { G.level += 1; this.load(G.level); } else end(true);
        return;
      }
      w.cam = Math.max(0, Math.min(p.x - W * 0.4, w.cols * TS - W));
    },
    respawn: function () { var p = G.world.p; p.x = G.world.start.x; p.y = G.world.start.y; p.vx = p.vy = 0; p.inv = 1.5; },
    sense: function () {
      var w = G.world, p = w.p, ax = p.x + p.w + 14, feet = p.y + p.h + 6, near = null;
      for (var i = 0; i < w.enemies.length; i++) { var d = w.enemies[i].x - p.x; if (d > 0 && d < 110 && Math.abs(w.enemies[i].y - p.y) < 60) near = d; }
      var coinUp = w.coins.some(function (c) { return c.x - p.x > -10 && c.x - p.x < 60 && p.y - c.y > 20 && p.y - c.y < 160; });
      return { wallAhead: this.solid(ax, p.y + p.h / 2), gapAhead: p.ground && !this.solid(ax, feet) && !this.solid(ax + TS, feet),
               spikeAhead: w.spikes.some(function (s) { return s.x - p.x > 0 && s.x - p.x < 70; }),
               enemyAhead: near !== null, coinAbove: coinUp, ground: p.ground };
    },
    draw: function () {
      var w = G.world, cam = w.cam;
      for (var r = 0; r < w.rows; r++) for (var c = Math.max(0, Math.floor(cam / TS)); c < Math.min(w.cols, Math.ceil((cam + W) / TS) + 1); c++) {
        if (!w.tiles[r][c]) continue;
        var x = c * TS - cam, y = w.top + r * TS;
        ctx.fillStyle = P.ground; rr(x, y, TS, TS, 6); ctx.fill();
        if (r === 0 || !w.tiles[r - 1][c]) { ctx.fillStyle = shade(P.ground, 0.25); ctx.fillRect(x, y, TS, 7); }
      }
      ctx.fillStyle = P.enemy; w.spikes.forEach(function (s) { var x = s.x - cam; ctx.beginPath();
        for (var k = 0; k < 3; k++) { ctx.moveTo(x + k * 11, s.y + s.h); ctx.lineTo(x + k * 11 + 5.5, s.y); ctx.lineTo(x + k * 11 + 11, s.y + s.h); }
        ctx.fill(); });
      w.coins.forEach(function (o) { coin(o.x - cam + 10, o.y + 10); });
      if (w.flag) { var fx = w.flag.x - cam; ctx.fillStyle = P.text; ctx.fillRect(fx, w.flag.y, 4, w.flag.h);
        ctx.fillStyle = P.item; ctx.beginPath(); ctx.moveTo(fx + 4, w.flag.y); ctx.lineTo(fx + 30, w.flag.y + 12); ctx.lineTo(fx + 4, w.flag.y + 24); ctx.fill(); }
      w.enemies.forEach(function (e) { creature(e.x - cam, e.y, e.w, e.h, P.enemy, e.vx > 0 ? 1 : -1); });
      var p = w.p; if (!(p.inv > 0 && Math.floor(p.inv * 10) % 2)) creature(p.x - cam, p.y, p.w, p.h, P.player, p.face);
    }
  };

  // ================= shooter (top-down) =================
  var shooter = {
    init: function () { G.world = { p: { x: W / 2 - 18, y: H - 80, w: 36, h: 36, inv: 0 }, shots: [], enemies: [], wave: 0, cool: 0, spawn: 0, left: 0 };
      this.wave(0); },
    wave: function (n) { var wv = DEF.levels[0].waves[n]; G.world.wave = n; G.world.left = wv.count; G.world.spawn = 0.6; },
    update: function (dt) {
      var w = G.world, p = w.p, sp = 160 + DEF.player.speed * 30, wv = DEF.levels[0].waves[w.wave];
      p.x = Math.max(0, Math.min(W - p.w, p.x + ((input.right ? 1 : 0) - (input.left ? 1 : 0)) * sp * dt));
      p.y = Math.max(H * 0.45, Math.min(H - p.h - 8, p.y + ((input.down ? 1 : 0) - (input.up ? 1 : 0)) * sp * dt));
      if (p.inv > 0) p.inv -= dt;
      w.cool -= dt;
      if (input.fire && w.cool <= 0) { w.shots.push({ x: p.x + p.w / 2 - 3, y: p.y - 10, w: 6, h: 14 }); w.cool = 0.22; tone(760, 0.03); }
      w.shots.forEach(function (s) { s.y -= 620 * dt; });
      w.shots = w.shots.filter(function (s) { return s.y > -20; });
      w.spawn -= dt;
      if (w.left > 0 && w.spawn <= 0) {
        w.enemies.push({ x: 30 + rnd() * (W - 90), y: -40, w: 34, h: 30, ph: rnd() * 6, vy: 40 + wv.speed * 18 });
        w.left -= 1; w.spawn = Math.max(0.35, 1.4 - wv.speed * 0.1);
      }
      for (var i = w.enemies.length - 1; i >= 0; i--) {
        var e = w.enemies[i]; e.ph += dt * 2; e.y += e.vy * dt; e.x += Math.sin(e.ph) * 60 * dt;
        for (var j = w.shots.length - 1; j >= 0; j--) if (hit(w.shots[j], e)) {
          burst(e.x + 17, e.y + 15, P.enemy, 10); w.enemies.splice(i, 1); w.shots.splice(j, 1); G.score += 10; tone(300, 0.05); e = null; break; }
        if (!e) continue;
        if (e.y > H || (hit(p, e) && p.inv <= 0)) { w.enemies.splice(i, 1); if (!hurt()) return; p.inv = 1.2; }
      }
      if (w.left === 0 && w.enemies.length === 0) {
        if (w.wave + 1 < DEF.levels[0].waves.length) { G.level = w.wave + 1; this.wave(w.wave + 1); } else end(true);
      }
    },
    sense: function () { var w = G.world, p = w.p, best = null;
      w.enemies.forEach(function (e) { if (e.y > -10 && (!best || e.y > best.y)) best = e; });
      return { targetDx: best ? (best.x + best.w / 2) - (p.x + p.w / 2) : 0, enemies: w.enemies.length }; },
    draw: function () {
      var w = G.world, p = w.p;
      ctx.fillStyle = P.item; w.shots.forEach(function (s) { rr(s.x, s.y, s.w, s.h, 3); ctx.fill(); });
      w.enemies.forEach(function (e) { ctx.fillStyle = P.enemy; ctx.beginPath(); ctx.moveTo(e.x, e.y); ctx.lineTo(e.x + e.w, e.y);
        ctx.lineTo(e.x + e.w / 2, e.y + e.h); ctx.fill(); eyes(e.x + e.w / 2, e.y + 9, 1); });
      if (!(p.inv > 0 && Math.floor(p.inv * 10) % 2)) { ctx.fillStyle = P.player; ctx.beginPath(); ctx.moveTo(p.x + p.w / 2, p.y);
        ctx.lineTo(p.x + p.w, p.y + p.h); ctx.lineTo(p.x, p.y + p.h); ctx.fill(); ctx.fillStyle = shade(P.player, 0.35); ctx.fillRect(p.x + p.w / 2 - 4, p.y + 14, 8, 10); }
    }
  };

  // ================= runner =================
  var GROUND = H - 90;
  var runner = {
    init: function () { var lv = DEF.levels[0];
      G.world = { p: { x: 150, y: GROUND - 44, w: 32, h: 44, vy: 0, ground: true, inv: 0 }, obs: [], coins: [], dist: 0,
        speed: 260 + lv.obstacle_rate * 14, next: 1.2, nextCoin: 0.8, len: lv.length_s, scroll: 0 }; },
    update: function (dt) {
      var w = G.world, p = w.p, lv = DEF.levels[0];
      if (jumpBuffer > 0 && p.ground) { p.vy = -(520 + DEF.player.jump * 30); p.ground = false; jumpBuffer = 0; tone(520, 0.05); }
      p.vy += 1900 * dt; p.y += p.vy * dt;
      if (p.y >= GROUND - p.h) { p.y = GROUND - p.h; p.vy = 0; p.ground = true; }
      if (p.inv > 0) p.inv -= dt;
      var dx = w.speed * dt; w.dist += dx; w.scroll += dx;
      w.next -= dt; w.nextCoin -= dt;
      if (w.next <= 0) { var hgt = 26 + Math.floor(rnd() * 3) * 14; w.obs.push({ x: W + 20, y: GROUND - hgt, w: 26, h: hgt });
        w.next = Math.max(0.55, 2.2 - lv.obstacle_rate * 0.15) + rnd() * 0.8; }
      if (lv.coin_rate > 0 && w.nextCoin <= 0) { w.coins.push({ x: W + 20, y: GROUND - 70 - rnd() * 90, w: 20, h: 20 });
        w.nextCoin = Math.max(0.3, 2.4 - lv.coin_rate * 0.2); }
      w.obs.forEach(function (o) { o.x -= dx; }); w.coins.forEach(function (o) { o.x -= dx; });
      w.obs = w.obs.filter(function (o) { return o.x > -40; }); w.coins = w.coins.filter(function (o) { return o.x > -40; });
      for (var i = w.coins.length - 1; i >= 0; i--) if (hit(p, w.coins[i])) { burst(w.coins[i].x, w.coins[i].y, P.item, 8); w.coins.splice(i, 1); G.score += 10; tone(990, 0.05); }
      for (i = w.obs.length - 1; i >= 0; i--) if (hit(p, w.obs[i]) && p.inv <= 0) { w.obs.splice(i, 1); if (!hurt()) return; p.inv = 1.2; }
      G.score += Math.floor((w.dist - dx) / 100) !== Math.floor(w.dist / 100) ? 1 : 0;
      if (G.time >= w.len) end(true);
    },
    sense: function () { var w = G.world, p = w.p;
      return { obstacleAhead: w.obs.some(function (o) { return o.x - (p.x + p.w) > 0 && o.x - (p.x + p.w) < 70 + w.speed * 0.08; }), ground: p.ground }; },
    draw: function () {
      var w = G.world, p = w.p;
      ctx.fillStyle = P.ground; ctx.fillRect(0, GROUND, W, H - GROUND);
      ctx.fillStyle = shade(P.ground, 0.25); for (var x = -(w.scroll % 48); x < W; x += 48) ctx.fillRect(x, GROUND, 24, 6);
      ctx.fillStyle = P.enemy; w.obs.forEach(function (o) { rr(o.x, o.y, o.w, o.h, 5); ctx.fill(); });
      w.coins.forEach(function (o) { coin(o.x + 10, o.y + 10); });
      if (!(p.inv > 0 && Math.floor(p.inv * 10) % 2)) creature(p.x, p.y, p.w, p.h, P.player, 1);
    }
  };

  // ================= match (puzzle) =================
  var match = {
    init: function () {
      var lv = DEF.levels[0], tries = 0;
      do { this.fill(lv); tries += 1; if (tries > 200) throw new Error('game: no playable board after 200 tries'); }
      while (this.findMatches().length || !this.hint());
      G.world.moves = lv.moves; G.world.target = lv.target; G.world.sel = null; G.world.cur = { c: 0, r: 0 }; G.world.anim = 0;
    },
    fill: function (lv) {
      var g = []; for (var r = 0; r < lv.rows; r++) { g.push([]); for (var c = 0; c < lv.cols; c++) g[r].push(Math.floor(rnd() * lv.colors)); }
      var cell = Math.min(Math.floor((H - 70) / lv.rows), Math.floor((W - 40) / lv.cols));
      G.world = { g: g, cols: lv.cols, rows: lv.rows, colors: lv.colors, cell: cell,
        x0: Math.round((W - cell * lv.cols) / 2), y0: Math.round(55 + (H - 55 - cell * lv.rows) / 2) };
    },
    findMatches: function () {
      var w = G.world, g = w.g, out = [];
      for (var r = 0; r < w.rows; r++) for (var c = 0; c < w.cols; c++) {
        var v = g[r][c]; if (v < 0) continue;
        if (c + 2 < w.cols && g[r][c + 1] === v && g[r][c + 2] === v) out.push([r, c], [r, c + 1], [r, c + 2]);
        if (r + 2 < w.rows && g[r + 1][c] === v && g[r + 2][c] === v) out.push([r, c], [r + 1, c], [r + 2, c]);
      }
      return out;
    },
    swap: function (a, b) { var g = G.world.g, t = g[a.r][a.c]; g[a.r][a.c] = g[b.r][b.c]; g[b.r][b.c] = t; },
    hint: function () {
      var w = G.world;
      for (var r = 0; r < w.rows; r++) for (var c = 0; c < w.cols; c++) {
        var a = { r: r, c: c }, ns = [{ r: r, c: c + 1 }, { r: r + 1, c: c }];
        for (var i = 0; i < 2; i++) { var b = ns[i]; if (b.c >= w.cols || b.r >= w.rows) continue;
          this.swap(a, b); var ok = this.findMatches().length > 0; this.swap(a, b); if (ok) return [a, b]; }
      }
      return null;
    },
    tryMove: function (a, b) {
      var w = G.world;
      if (Math.abs(a.r - b.r) + Math.abs(a.c - b.c) !== 1) { w.sel = b; return; }
      this.swap(a, b);
      var m = this.findMatches();
      if (!m.length) { this.swap(a, b); w.sel = null; tone(200, 0.06); return; }
      w.moves -= 1; w.sel = null;
      var chain = 0;
      while (m.length && chain < 50) {
        chain += 1; var seen = {};
        m.forEach(function (x) { if (!seen[x]) { seen[x] = 1; w.g[x[0]][x[1]] = -1;
          burst(w.x0 + x[1] * w.cell + w.cell / 2, w.y0 + x[0] * w.cell + w.cell / 2, P.item, 3); } });
        G.score += Object.keys(seen).length * 10 * chain; tone(600 + chain * 120, 0.06);
        for (var c = 0; c < w.cols; c++) { var col = []; for (var r = w.rows - 1; r >= 0; r--) if (w.g[r][c] >= 0) col.push(w.g[r][c]);
          for (r = w.rows - 1, k = 0; r >= 0; r--, k++) w.g[r][c] = k < col.length ? col[k] : Math.floor(rnd() * w.colors); }
        m = this.findMatches();
      }
      var k;
      if (G.score >= w.target) { end(true); return; }
      if (w.moves <= 0) { end(false); return; }
      var tries = 0; while (!this.hint()) { tries += 1; if (tries > 200) throw new Error('game: no move after reshuffle');
        for (var rr2 = 0; rr2 < w.rows; rr2++) for (var cc = 0; cc < w.cols; cc++) w.g[rr2][cc] = Math.floor(rnd() * w.colors); }
    },
    pick: function (cell) { var w = G.world; if (w.sel) this.tryMove(w.sel, cell); else w.sel = cell; },
    update: function () {},
    sense: function () { return {}; },
    draw: function () {
      var w = G.world, cs = w.cell, shapes = ['circle', 'square', 'diamond', 'tri', 'star', 'ring'];
      var colors = [P.player, P.enemy, P.item, P.ground, P.text, shade(P.player, 0.4)];
      for (var r = 0; r < w.rows; r++) for (var c = 0; c < w.cols; c++) {
        var x = w.x0 + c * cs, y = w.y0 + r * cs, v = w.g[r][c];
        ctx.fillStyle = (r + c) % 2 ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.12)'; rr(x + 2, y + 2, cs - 4, cs - 4, 8); ctx.fill();
        if (v >= 0) gem(x + cs / 2, y + cs / 2, cs * 0.34, colors[v], shapes[v]);
      }
      var mark = function (cell, color) { ctx.strokeStyle = color; ctx.lineWidth = 4; rr(w.x0 + cell.c * cs + 3, w.y0 + cell.r * cs + 3, cs - 6, cs - 6, 8); ctx.stroke(); };
      mark(w.cur, 'rgba(255,255,255,0.5)'); if (w.sel) mark(w.sel, P.text);
    }
  };
  function matchTap(x, y) {
    var w = G.world, c = Math.floor((x - w.x0) / w.cell), r = Math.floor((y - w.y0) / w.cell);
    if (c < 0 || r < 0 || c >= w.cols || r >= w.rows) return;
    w.cur = { c: c, r: r }; match.pick({ c: c, r: r });
  }
  function matchKey(k) {
    var w = G.world, d = { left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1] }[k];
    if (k === 'jump') { match.pick({ c: w.cur.c, r: w.cur.r }); return; }
    w.cur = { c: Math.max(0, Math.min(w.cols - 1, w.cur.c + d[0])), r: Math.max(0, Math.min(w.rows - 1, w.cur.r + d[1])) };
  }

  var KIND = { platformer: platformer, shooter: shooter, runner: runner, match: match }[DEF.kind];
  if (!KIND) throw new Error('game: unknown kind ' + DEF.kind);

  // ---- drawing helpers ----
  function rr(x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  function shade(hex, f) { var n = parseInt(hex.slice(1), 16), r = n >> 16, g = n >> 8 & 255, b = n & 255;
    var m = function (v) { return Math.round(Math.max(0, Math.min(255, v + (f > 0 ? (255 - v) * f : v * f)))); };
    return 'rgb(' + m(r) + ',' + m(g) + ',' + m(b) + ')'; }
  function eyes(cx, cy, face) { ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(cx - 5 + face * 2, cy, 4, 0, 7); ctx.arc(cx + 5 + face * 2, cy, 4, 0, 7); ctx.fill();
    ctx.fillStyle = '#111'; ctx.beginPath(); ctx.arc(cx - 4 + face * 3, cy, 2, 0, 7); ctx.arc(cx + 6 + face * 3, cy, 2, 0, 7); ctx.fill(); }
  function creature(x, y, w, h, color, face) { ctx.fillStyle = color; rr(x, y, w, h, 9); ctx.fill();
    ctx.fillStyle = shade(color, -0.2); ctx.fillRect(x + 3, y + h - 7, w - 6, 4); eyes(x + w / 2, y + 12, face); }
  function coin(cx, cy) { ctx.fillStyle = P.item; ctx.beginPath(); ctx.arc(cx, cy, 10, 0, 7); ctx.fill();
    ctx.fillStyle = shade(P.item, 0.45); ctx.beginPath(); ctx.arc(cx - 3, cy - 3, 3.5, 0, 7); ctx.fill(); }
  function gem(cx, cy, r, color, shape) {
    ctx.fillStyle = color; ctx.beginPath();
    if (shape === 'circle') ctx.arc(cx, cy, r, 0, 7);
    else if (shape === 'square') { rr(cx - r, cy - r, 2 * r, 2 * r, 6); }
    else if (shape === 'diamond') { ctx.moveTo(cx, cy - r); ctx.lineTo(cx + r, cy); ctx.lineTo(cx, cy + r); ctx.lineTo(cx - r, cy); }
    else if (shape === 'tri') { ctx.moveTo(cx, cy - r); ctx.lineTo(cx + r, cy + r * 0.8); ctx.lineTo(cx - r, cy + r * 0.8); }
    else if (shape === 'star') { for (var i = 0; i < 10; i++) { var a = -Math.PI / 2 + i * Math.PI / 5, q = i % 2 ? r * 0.45 : r; ctx.lineTo(cx + Math.cos(a) * q, cy + Math.sin(a) * q); } }
    else { ctx.arc(cx, cy, r, 0, 7); ctx.arc(cx, cy, r * 0.45, 0, 7, true); }
    ctx.fill(); ctx.fillStyle = 'rgba(255,255,255,0.35)'; ctx.beginPath(); ctx.arc(cx - r * 0.35, cy - r * 0.35, r * 0.22, 0, 7); ctx.fill();
  }
  function background() {
    var g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, shade(P.bg, 0.18)); g.addColorStop(1, shade(P.bg, -0.25));
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    var cam = (G.world && (G.world.cam || G.world.scroll)) || 0;
    if (DEF.kind === 'shooter') { ctx.fillStyle = 'rgba(255,255,255,0.55)';
      for (var i = 0; i < 60; i++) { var sx = (i * 157) % W, sy = ((i * 89) + G.time * (20 + (i % 3) * 25)) % H; ctx.fillRect(sx, sy, 2, 2); } }
    else if (DEF.kind !== 'match') { ctx.fillStyle = shade(P.bg, -0.12);
      for (var k = -1; k < 6; k++) { var hx = k * 240 - (cam * 0.3) % 240; ctx.beginPath(); ctx.arc(hx + 120, H - 40, 150, Math.PI, 0); ctx.fill(); } }
  }
  function hud() {
    ctx.save(); ctx.direction = DEF.dir; ctx.font = '600 22px system-ui, -apple-system, "Segoe UI", Arial, sans-serif';
    ctx.fillStyle = 'rgba(0,0,0,0.28)'; rr(10, 10, W - 20, 40, 12); ctx.fill(); ctx.fillStyle = P.text; ctx.textBaseline = 'middle';
    var parts = [T.score + ': ' + G.score];
    if (DEF.kind === 'match') parts.push(L.moves + ': ' + G.world.moves);
    else parts.push(L.lives + ': ' + G.lives);
    parts.push(L.time + ': ' + Math.max(0, Math.ceil(DEF.time_limit_s - G.time)));
    var line = parts.join('   ·   ');
    if (DEF.dir === 'rtl') { ctx.textAlign = 'right'; ctx.fillText(line, W - 26, 30); } else { ctx.textAlign = 'left'; ctx.fillText(line, 26, 30); }
    ctx.restore();
  }

  // ---- the loop: fixed 60 Hz steps, one render per frame ----
  function step(dt) {
    if (G.status !== 'playing') return;
    G.time += dt; G.steps += 1;
    if (jumpBuffer > 0) jumpBuffer -= dt;
    KIND.update(dt);
    if (G.status === 'playing' && G.time >= DEF.time_limit_s) end(DEF.kind === 'runner');
    G.fx.forEach(function (f) { f.x += f.vx * dt; f.y += f.vy * dt; f.vy += 900 * dt; f.t -= dt; });
    G.fx = G.fx.filter(function (f) { return f.t > 0; });
  }
  function render() {
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = shade(P.bg, -0.45); ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(view.s * view.dpr, 0, 0, view.s * view.dpr, view.ox * view.dpr, view.oy * view.dpr);
    ctx.save(); ctx.beginPath(); ctx.rect(0, 0, W, H); ctx.clip();
    background();
    if (G.world) KIND.draw();
    G.fx.forEach(function (f) { ctx.globalAlpha = Math.max(0, f.t / 0.6); ctx.fillStyle = f.c; ctx.fillRect(f.x - 3, f.y - 3, 6, 6); });
    ctx.globalAlpha = 1;
    if (G.world) hud();
    ctx.restore();
  }
  var last = performance.now(), acc = 0;
  function frame(now) {
    acc += Math.min(0.1, (now - last) / 1000); last = now;
    var n = 0; while (acc >= STEP && n < 6) { step(STEP); acc -= STEP; n += 1; }
    if (n === 6) acc = 0;
    G.frames += 1; render(); requestAnimationFrame(frame);
  }
  showScreen(DEF.title, T.start, L.start);
  KIND.init(); G.status = 'title';     // the board or level shows behind the start screen
  requestAnimationFrame(frame);

  // ---- the probe's read-only window (and the simulation stepper) ----
  window.__game = {
    kind: DEF.kind,
    state: function () { var w = G.world || {}, p = w.p || {};
      return { status: G.status, score: G.score, lives: G.lives, level: G.level, frames: G.frames, steps: G.steps, time: G.time,
               player: p.x !== undefined ? { x: Math.round(p.x * 10) / 10, y: Math.round(p.y * 10) / 10 } : null,
               cursor: w.cur ? { c: w.cur.c, r: w.cur.r } : null, selected: w.sel ? { c: w.sel.c, r: w.sel.r } : null,
               moves: w.moves === undefined ? null : w.moves }; },
    fastForward: function (seconds) { var n = Math.min(Math.round(seconds * 60), 60 * 400);
      for (var i = 0; i < n && G.status === 'playing'; i++) step(STEP); return G.status; },
    sense: function () { return G.status === 'playing' ? KIND.sense() : {}; },
    hint: function () { return DEF.kind === 'match' ? match.hint() : null; },
    cellCenter: function (c, r) { var w = G.world; if (DEF.kind !== 'match') return null;
      return { x: view.ox + (w.x0 + c * w.cell + w.cell / 2) * view.s, y: view.oy + (w.y0 + r * w.cell + w.cell / 2) * view.s }; }
  };
})();
