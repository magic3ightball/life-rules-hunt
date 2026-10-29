"""Build gallery.html: how the hunt works (diagrams + live soup), the rule ranking
from results/screen_b3.json, and per-rule search results from results/*.json.

  python3 gallery.py [--rare 3] [--cap 30]
gallery.html is an Artifact page body (no <html>/<head>/<body> tags; the
publisher wraps it); site/index.html is the same page as a full document for Vercel.
"""
import argparse
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# rules picked for the 1M-soup searches, and why (see results/screen_b3.md)
PICKS = {
    "b368s238": "우주선(글라이더)이 수프당 약 1개씩 나오는 규칙 중 Catagolue 기록이 가장 적음",
    "b3578s1267": "수프 4개 중 1개꼴로 주기 12 진동자가 남고, 기록이 25만 수프뿐",
    "b36s034678": "Catagolue C1 기록 0. 잿더미의 40%가 주기 3 이상",
}

PAGE = r"""<title>Life Rules Hunt</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+KR:wght@400;600;700&display=swap">
<style>
/* Layout: one reading column; diagrams sit in quiet panels, live cells are the only saturated colour. */
:root {
  --paper: #f3f5f2; --panel: #ffffff; --ink: #1b2421; --mute: #5f6b66; --rule: #d9dfdb;
  --cell: #0f7b62; --cell-soft: #d5ece4; --new: #c8462b; --new-soft: #f7dfd8; --ship: #2f5fb3;
  --f-body: "IBM Plex Sans KR", "Apple SD Gothic Neo", system-ui, sans-serif;
  --f-mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --paper: #121715; --panel: #1a211e; --ink: #e6ece9; --mute: #94a39c; --rule: #2c3531;
  --cell: #4fd1a8; --cell-soft: #1f3a31; --new: #ff8a6b; --new-soft: #3d221b; --ship: #82a8f0; color-scheme: dark } }
:root[data-theme="dark"] {
  --paper: #121715; --panel: #1a211e; --ink: #e6ece9; --mute: #94a39c; --rule: #2c3531;
  --cell: #4fd1a8; --cell-soft: #1f3a31; --new: #ff8a6b; --new-soft: #3d221b; --ship: #82a8f0; color-scheme: dark }
* { box-sizing: border-box; }
body { background: var(--paper); color: var(--ink); font: 16px/1.65 var(--f-body); }
.wrap { max-width: 1040px; margin: 0 auto; padding-block: 36px 72px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
h1 { font-size: clamp(28px, 5vw, 40px); line-height: 1.15; margin: 0 0 8px; letter-spacing: -0.01em; }
h2 { font-size: 22px; margin: 56px 0 6px; text-wrap: balance; }
h3 { font-size: 17px; margin: 0 0 6px; }
.lede { color: var(--mute); max-width: 62ch; margin: 0; }
.eyebrow { font: 600 12px var(--f-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--cell); }
p.note { color: var(--mute); max-width: 65ch; margin: 4px 0 18px; }
.panel { background: var(--panel); border: 1px solid var(--rule); border-radius: 10px; padding: 18px; min-width: 0; }
.twocol { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
svg { display: block; width: 100%; height: auto; }
svg text { font-family: var(--f-body); fill: var(--ink); }
svg .m { fill: var(--mute); } svg .mono { font-family: var(--f-mono); }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 14px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--rule); white-space: nowrap; }
th { font-weight: 600; color: var(--mute); font-size: 12px; }
td.why { white-space: normal; min-width: 220px; }
.mono { font-family: var(--f-mono); }
tr.pick td { background: var(--cell-soft); }
.chip { display: inline-block; font: 600 11px var(--f-mono); padding: 1px 7px; border-radius: 99px; background: var(--rule); color: var(--ink); }
.chip.new { background: var(--new); color: var(--panel); }
.chip.ship { background: var(--ship); color: var(--panel); }
.chip.ok { background: var(--cell-soft); color: var(--cell); }
.emit { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 10px; margin-top: 10px; }
.emit .card { gap: 4px; }
.emit button { align-self: flex-start; font-size: 13px; padding: 5px 10px; }
/* live soup */
.demo { display: grid; grid-template-columns: minmax(0, 1fr) minmax(240px, 300px); gap: 18px; align-items: start; }
@media (max-width: 720px) { .demo { grid-template-columns: 1fr; } }
#soup { width: 100%; max-width: 100%; aspect-ratio: 1; border-radius: 8px; background: var(--paper); display: block; }
.controls { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
select, button { font: 14px var(--f-body); padding: 7px 12px; border-radius: 7px; border: 1px solid var(--rule); background: var(--panel); color: var(--ink); cursor: pointer; }
button.primary { background: var(--cell); border-color: var(--cell); color: var(--panel); font-weight: 600; }
button:focus-visible, select:focus-visible, a:focus-visible { outline: 2px solid var(--ship); outline-offset: 2px; }
.readout { display: grid; grid-template-columns: auto 1fr; gap: 4px 14px; font-size: 14px; }
.readout dt { color: var(--mute); } .readout dd { margin: 0; font-family: var(--f-mono); }
.status { margin-top: 12px; padding: 10px 12px; border-radius: 8px; background: var(--cell-soft); font-size: 14px; }
/* results */
.rule-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 16px; margin: 40px 0 10px; }
.rule-head h3 { font: 600 20px var(--f-mono); margin: 0; }
.stats { display: flex; flex-wrap: wrap; gap: 6px 18px; color: var(--mute); font-size: 14px; }
.stats b { color: var(--ink); font-variant-numeric: tabular-nums; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.card { background: var(--panel); border: 1px solid var(--rule); border-radius: 10px; padding: 10px; min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.card.new { border-color: var(--new); }
.card canvas { width: 100%; max-width: 100%; aspect-ratio: 1; display: block; border-radius: 6px; background: var(--paper); }
.card .code { font: 11px var(--f-mono); color: var(--mute); word-break: break-all; }
.card .meta { font-size: 13px; }
a { color: var(--ship); }
.pending { color: var(--mute); font-style: italic; }
footer { margin-top: 60px; color: var(--mute); font-size: 13px; max-width: 70ch; }
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
</style>

<div class="wrap">
<div class="eyebrow">Life-like 세포 자동자 · 새 패턴 찾기</div>
<h1>Life Rules Hunt</h1>
<p class="lede">콘웨이의 생명 게임과 같은 방식으로 움직이지만 규칙 숫자만 다른 세계가 26만 개 있습니다. 그중 아직 아무도 많이 뒤져 보지 않은 세계를 골라, 무작위 수프 수백만 개를 돌려서 전 세계 기록(Catagolue)에 없는 물체를 찾습니다.</p>

<h2>규칙 이름 읽는 법</h2>
<p class="note">모든 칸은 이웃 8칸을 셉니다. <b>B</b> 뒤 숫자는 빈 칸이 태어나는 이웃 수, <b>S</b> 뒤 숫자는 산 칸이 살아남는 이웃 수입니다. 아래는 이번에 고른 규칙 b368s238의 예입니다.</p>
<div class="panel scroll">__RULE_SVG__</div>

<h2>찾는 과정</h2>
<p class="note">두 단계입니다. 먼저 어느 규칙을 뒤질지 고르고(1), 고른 규칙에서 수프를 대량으로 돌립니다(2~5).</p>
<div class="panel scroll">__PIPE_SVG__</div>

<h2>규칙 고르기: 1만 6천 개에서 3개로</h2>
<p class="note">생명 게임과 가까운 규칙(B3 포함, B2 없음) 16,384개를 전부 돌려 걸렀습니다. 막대 길이는 로그 눈금입니다.</p>
<div class="twocol">
  <div class="panel scroll">__FUNNEL_SVG__</div>
  <div class="panel">
    <h3>거르는 기준</h3>
    <dl class="readout">
      <dt>폭발</dt><dd>수프가 끝없이 커지면 제외</dd>
      <dt>덩어리</dt><dd>잿더미가 40칸 넘는 한 덩어리면 제외</dd>
      <dt>재미</dt><dd>우주선·긴 주기 진동자가 많을수록 +</dd>
      <dt>속도</dt><dd>초당 수프 수가 많을수록 +</dd>
      <dt>새로움</dt><dd>Catagolue C1 수프 수가 적을수록 +</dd>
    </dl>
    <p class="note" style="margin-top:12px">안정적인 B3 규칙은 대부분 누군가 이미 약 100만 수프씩 돌려 두었습니다. 기록이 0인 규칙은 조회한 600여 개 중 9개뿐이었고, 그중 8개가 S0(외톨이 칸이 살아남음) 규칙이었습니다.</p>
  </div>
</div>

<h3 style="margin-top:28px">고른 규칙과 우주선이 나오는 규칙</h3>
<div class="panel scroll">__RANK_TABLE__</div>

<h2>수프 하나 직접 돌려 보기</h2>
<p class="note">검색이 실제로 하는 일과 같습니다. 문자열을 SHA-256으로 바꿔 16×16 수프를 만들고, 반복될 때까지 돌립니다. 점선 원 밖으로 나간 물체는 우주선으로 보고 떼어 냅니다.</p>
<div class="panel demo">
  <canvas id="soup" width="640" height="640" aria-label="수프 시뮬레이션"></canvas>
  <div>
    <div class="controls">
      <select id="demo-rule" aria-label="규칙">__RULE_OPTIONS__</select>
      <select id="demo-seed" aria-label="수프 번호"></select>
    </div>
    <div class="controls">
      <button id="demo-play" class="primary">재생</button>
      <button id="demo-step">한 세대</button>
      <button id="demo-reset">처음으로</button>
    </div>
    <dl class="readout">
      <dt>시드</dt><dd id="r-seed">-</dd>
      <dt>세대</dt><dd id="r-gen">0</dd>
      <dt>살아 있는 칸</dt><dd id="r-pop">0</dd>
      <dt>떼어 낸 우주선 칸</dt><dd id="r-ship">0</dd>
    </dl>
    <div class="status" id="r-status">재생을 누르세요.</div>
    <p class="note" style="font-size:13px;margin-top:10px">같은 시드는 <a id="r-link" href="#" target="_blank" rel="noopener">Catagolue의 hashsoup</a>에서도 똑같은 수프로 나옵니다.</p>
  </div>
</div>

<h2>검색 결과</h2>
<p class="note">Catagolue 기록이 <b>__RARE__회 미만</b>인 물체만 보여 줍니다. <span class="chip new">처음</span>은 그 규칙의 Catagolue 기록에 없는 물체, <span class="chip ship">우주선</span>은 움직이는 물체입니다. <span class="chip ok">단일 물체</span>는 두 조각으로 나누는 모든 방법을 시험해 봐도 따로 살아남는 조각이 없다는 뜻입니다(붙어 있기만 한 두 물체가 아님). 우주선 → 주기 3 이상 진동자 → 나머지 순서이고, 규칙당 최대 __CAP__개까지 보입니다.</p>
<div id="results"></div>

<footer>
<p>검색 엔진: C로 만든 수프 실행기 + Python 물체 분리기(apgsearch의 C1 hashsoup 방식과 호환). Catagolue에는 아무것도 올리지 않았습니다. "처음"은 Catagolue 기록과 대조한 결과이며, 물체 분리 방식이 apgsearch와 조금 달라 붙어 있는 두 물체가 하나로 잡힌 경우가 섞일 수 있습니다. 원본 수프 링크로 확인할 수 있습니다.</p>
<p>생성: __DATE__</p>
</footer>
</div>

<script>
const DATA = __DATA__;
function parseRule(r) { const m = r.match(/b(\d*)s(\d*)/); return [new Set([...m[1]].map(Number)), new Set([...m[2]].map(Number))]; }
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const kindOf = c => c.startsWith('xq') ? ['우주선', 'ship'] : c.startsWith('xp') ? ['진동자', 'osc'] : c.startsWith('xs') ? ['정물', 'still'] : ['기타', ''];
const periodOf = c => /^x[pq]/.test(c) ? +c.slice(2).split('_')[0] : 1;

/* ---------- cell-set stepping for the cards ---------- */
function stepSet(cells, [B, S]) {
  const cnt = new Map(), live = new Set(cells.map(([x, y]) => x + ',' + y));
  for (const [x, y] of cells) for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++)
    if (dx || dy) { const k = (x + dx) + ',' + (y + dy); cnt.set(k, (cnt.get(k) || 0) + 1); }
  const out = [];
  for (const [k, n] of cnt) if (live.has(k) ? S.has(n) : B.has(n)) out.push(k.split(',').map(Number));
  if (S.has(0)) for (const [x, y] of cells) if (!cnt.has(x + ',' + y)) out.push([x, y]);
  return out;
}

const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
/* ---------- results ---------- */
const anims = [];
const res = document.getElementById('results');
for (const run of DATA.runs) {
  const head = document.createElement('div');
  head.className = 'rule-head';
  if (!run.soups) {
    head.innerHTML = `<h3>${run.rule}</h3><span class="pending">검색 진행 중 · 끝나면 이 자리에 결과가 들어옵니다</span>`;
    res.appendChild(head); continue;
  }
  const nNew = run.items.filter(i => i.census === 0).length;
  head.innerHTML = `<h3>${run.rule}</h3><div class="stats">
    <span>수프 <b>${run.soups.toLocaleString()}</b></span>
    <span>물체 종류 <b>${run.distinct.toLocaleString()}</b></span>
    <span>Catagolue에 없음 <b>${run.new_total.toLocaleString()}</b></span>
    <span>우주선 종류 <b>${run.ship_kinds}</b></span>
    <span>Catagolue 기존 기록 <b>${run.census_soups.toLocaleString()}</b> 수프</span>
    <span>안정 안 됨 <b>${run.unstable.toLocaleString()}</b></span></div>`;
  res.appendChild(head);
  if (run.note) { const p = document.createElement('p'); p.className = 'note'; p.textContent = run.note; res.appendChild(p); }
  const grid = document.createElement('div'); grid.className = 'grid'; res.appendChild(grid);
  if (!run.items.length) { grid.innerHTML = '<p class="note">기록이 드문 물체가 없었습니다.</p>'; }
  if (run.recheck) {
    const box = document.createElement('div');
    const k = run.recheck.kinds;
    box.innerHTML = `<p class="note" style="margin-top:18px"><b>안정 안 된 수프 ${run.recheck.soups.toLocaleString()}개 재검사</b> (더 큰 판에서 다시 돌림):
      정착 ${(k.settled || 0).toLocaleString()} · 계속 무언가를 내보냄 ${(k.emitter || 0).toLocaleString()} · 끝까지 안 멈춤 ${(k.unsettled || 0).toLocaleString()}.
      정착한 수프에서는 기록이 드문 물체가 나오지 않았습니다.
      ${run.recheck.catagolue_linear ? `물체를 내보내는 수프(퍼퍼·총)는 Catagolue도 이 규칙에서 <b>${run.recheck.catagolue_linear.toLocaleString()}번</b> "선형 성장"으로 기록해 둔 흔한 현상이라, 새 발견으로 치지 않습니다.` : ''}</p>` +
      (run.emitters.length ? `<h3 style="margin-top:6px">구경거리: 일정한 간격으로 물체를 내보내는 수프</h3>
      <p class="note">방출 간격별로 하나씩 골랐습니다. "데모에서 보기"를 누르면 위 시뮬레이션에 이 수프가 올라갑니다.</p>
      <div class="emit">${run.emitters.map(e => `<div class="card"><div class="meta"><b>약 ${e.emit_period}세대마다</b> 방출 · 같은 간격 수프 ${e.n_same}개</div>
        <div class="code">${e.soup}</div><div class="meta"><a href="https://catagolue.hatsya.com/hashsoup/C1/${e.soup}/${run.rule}" target="_blank" rel="noopener">원본 수프</a></div>
        <button data-rule="${run.rule}" data-idx="${e.soup.split('_').pop()}">데모에서 보기</button></div>`).join('')}</div>` : '');
    res.appendChild(box);
    box.querySelectorAll('button[data-idx]').forEach(b => b.onclick = () => {
      document.getElementById('demo-rule').value = b.dataset.rule; fillSeeds(b.dataset.idx);
      resetDemo(); document.getElementById('soup').scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' });
    });
  }
  const rule = parseRule(run.rule);
  for (const it of run.items) {
    const [kname, kcls] = kindOf(it.code), p = periodOf(it.code);
    const card = document.createElement('div');
    card.className = 'card' + (it.census === 0 ? ' new' : '');
    const link = `https://catagolue.hatsya.com/hashsoup/C1/${it.soup}/${run.rule}`;
    const obj = `https://catagolue.hatsya.com/object/${it.code}/${run.rule}`;
    card.innerHTML = `<canvas width="200" height="200"></canvas>
      <div>${it.census === 0 ? '<span class="chip new">처음</span> ' : `<span class="chip">기록 ${it.census}회</span> `}${kcls === 'ship' ? '<span class="chip ship">우주선</span>' : ''}${it.verdict === 'strict' ? ' <span class="chip ok">단일 물체' + (it.how === 'partial' ? '(부분 검사)' : '') + '</span>' : ''}${it.recheck ? ' <span class="chip">큰 수프 재검사</span>' : ''}</div>
      <div class="meta"><b>${kname}${p > 1 ? ' · 주기 ' + p : ''}</b> · ${it.cells.length}칸 · 이번 ${it.count}회</div>
      <div class="code">${it.code}</div>
      <div class="meta"><a href="${link}" target="_blank" rel="noopener">원본 수프</a> · <a href="${obj}" target="_blank" rel="noopener">Catagolue</a></div>`;
    grid.appendChild(card);
    const xs = it.cells.map(c => c[0]), ys = it.cells.map(c => c[1]);
    anims.push({ canvas: card.querySelector('canvas'), cells: it.cells, start: it.cells, rule, ship: kcls === 'ship',
      cx: (Math.min(...xs) + Math.max(...xs)) / 2, cy: (Math.min(...ys) + Math.max(...ys)) / 2,
      span: Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)) + 6, t: 0, p });
  }
}
function drawCards() {
  const ink = css('--cell'), shipInk = css('--ship');
  for (const a of anims) {
    const c = a.canvas, d = devicePixelRatio || 1, W = Math.round(c.clientWidth * d) || 200;
    if (c.width !== W) { c.width = W; c.height = W; }
    const g = c.getContext('2d'); g.clearRect(0, 0, W, W);
    const s = W / Math.max(a.span, 10); g.fillStyle = a.ship ? shipInk : ink;
    let ox = a.cx, oy = a.cy;
    if (a.ship && a.cells.length) { const xs = a.cells.map(q => q[0]), ys = a.cells.map(q => q[1]);
      ox = (Math.min(...xs) + Math.max(...xs)) / 2; oy = (Math.min(...ys) + Math.max(...ys)) / 2; }
    const gap = s > 6 ? 1 : 0;
    for (const [x, y] of a.cells) g.fillRect(W / 2 + (x - ox - 0.5) * s + gap, W / 2 + (y - oy - 0.5) * s + gap, s - 2 * gap, s - 2 * gap);
  }
}
if (!reduce) setInterval(() => { for (const a of anims) { a.t++; a.cells = a.t % (a.p * 4) === 0 ? a.start : stepSet(a.cells, a.rule); if (!a.cells.length) a.cells = a.start; } drawCards(); }, 300);
addEventListener('resize', drawCards); drawCards();

/* ---------- live soup demo (same layout as soup.c / apgsearch C1 hashsoup) ---------- */
const N = 200, C = N >> 1, R = 64;  // demo cuts at radius 64 (the engine uses 80 and checks the object is a ship)
let grid = new Uint8Array(N * N), nxt = new Uint8Array(N * N), gen = 0, ejected = 0, timer = null, hist = new Map(), done = false, demoRule;
const cv = document.getElementById('soup');
function sha256js(bytes) {  // fallback where crypto.subtle is missing (non-https previews)
  const K = [], H = [];
  const isP = n => { for (let i = 2; i * i <= n; i++) if (n % i === 0) return false; return true; };
  for (let n = 2, c = 0; c < 64; n++) if (isP(n)) { if (c < 8) H[c] = (Math.pow(n, 1 / 2) % 1) * 2 ** 32 | 0; K[c++] = (Math.pow(n, 1 / 3) % 1) * 2 ** 32 | 0; }
  const l = bytes.length, m = new Uint8Array(((l + 9 + 63) >> 6) << 6);
  m.set(bytes); m[l] = 0x80; const dv = new DataView(m.buffer); dv.setUint32(m.length - 4, l * 8);
  const w = new Int32Array(64), rot = (x, n) => (x >>> n) | (x << (32 - n));
  for (let o = 0; o < m.length; o += 64) {
    for (let i = 0; i < 16; i++) w[i] = dv.getInt32(o + 4 * i);
    for (let i = 16; i < 64; i++) {
      const a = w[i - 15], b = w[i - 2];
      w[i] = (w[i - 16] + (rot(a, 7) ^ rot(a, 18) ^ (a >>> 3)) + w[i - 7] + (rot(b, 17) ^ rot(b, 19) ^ (b >>> 10))) | 0;
    }
    let [a, b, c, d, e, f, g, h] = H;
    for (let i = 0; i < 64; i++) {
      const t1 = (h + (rot(e, 6) ^ rot(e, 11) ^ rot(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) | 0;
      const t2 = ((rot(a, 2) ^ rot(a, 13) ^ rot(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) | 0;
      h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
    }
    [a, b, c, d, e, f, g, h].forEach((v, i) => H[i] = (H[i] + v) | 0);
  }
  return H.map(v => (v >>> 0).toString(16).padStart(8, '0')).join('');
}
async function sha256hex(s) {
  const bytes = new TextEncoder().encode(s);
  if (window.crypto && crypto.subtle) {
    try {
      const buf = await crypto.subtle.digest('SHA-256', bytes);
      return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
    } catch (e) { /* fall through */ }
  }
  return sha256js(bytes);
}
function fillSeeds(pick) {
  const rule = document.getElementById('demo-rule').value, sel = document.getElementById('demo-seed');
  sel.innerHTML = DATA.demo_seeds[rule].map(([i, label]) => `<option value="${i}">${label}</option>`).join('');
  if (pick !== undefined) sel.value = pick;
}
async function resetDemo() {
  stop();
  const rule = document.getElementById('demo-rule').value, idx = document.getElementById('demo-seed').value;
  const seed = DATA.demo_prefix[rule] + idx;
  demoRule = parseRule(rule);
  grid.fill(0); gen = 0; ejected = 0; hist = new Map(); done = false;
  const hex = await sha256hex(seed);
  for (let j = 0; j < 32; j++) {
    const v = parseInt(hex.slice(2 * j, 2 * j + 2), 16), y = j >> 1, xb = j % 2 ? 0 : 8;
    for (let b = 0; b < 8; b++) if ((v >> b) & 1) grid[(C - 8 + y) * N + C - 8 + xb + b] = 1;
  }
  document.getElementById('r-seed').textContent = seed;
  document.getElementById('r-link').href = `https://catagolue.hatsya.com/hashsoup/C1/${seed}/${rule}`;
  document.getElementById('r-status').textContent = '재생을 누르세요.';
  drawSoup(); readout();
}
function stepSoup() {
  const [B, S] = demoRule; let pop = 0, h = 0;
  nxt.fill(0);
  for (let y = 1; y < N - 1; y++) for (let x = 1; x < N - 1; x++) {
    const k = y * N + x;
    const n = grid[k - N - 1] + grid[k - N] + grid[k - N + 1] + grid[k - 1] + grid[k + 1] + grid[k + N - 1] + grid[k + N] + grid[k + N + 1];
    if (grid[k] ? S.has(n) : B.has(n)) {
      const dx = x - C, dy = y - C;
      if (dx * dx + dy * dy > R * R) { ejected++; continue; }  // flew away: cut out
      nxt[k] = 1; pop++; h = (h + Math.imul(k, 2654435761)) >>> 0;
    }
  }
  [grid, nxt] = [nxt, grid]; gen++;
  const key = h + ':' + pop;
  if (hist.has(key) && !done) {
    const p = gen - hist.get(key);
    done = true; stop();
    document.getElementById('r-status').innerHTML = pop === 0 ? `${gen}세대에 모두 사라졌습니다.`
      : `${gen}세대에 안정: 주기 <b>${p}</b>로 반복됩니다. 이 상태를 물체 단위로 나눠 이름(apgcode)을 붙이고 Catagolue와 비교합니다.`;
  }
  hist.set(key, gen);
  if (gen > 6000 && !done) { done = true; stop(); document.getElementById('r-status').textContent = '6000세대 안에 안정되지 않았습니다. 실제 검색에서는 이런 수프를 따로 모아 둡니다.'; }
  return pop;
}
function readout() {
  let pop = 0; for (let i = 0; i < grid.length; i++) pop += grid[i];
  document.getElementById('r-gen').textContent = gen;
  document.getElementById('r-pop').textContent = pop;
  document.getElementById('r-ship').textContent = ejected;
}
function drawSoup() {
  const d = devicePixelRatio || 1, W = Math.round(cv.clientWidth * d) || 640;
  if (cv.width !== W) { cv.width = W; cv.height = W; }
  const g = cv.getContext('2d'), view = 2 * (R + 6), s = W / view, o = C - view / 2;
  g.clearRect(0, 0, W, W);
  g.strokeStyle = css('--mute'); g.setLineDash([4 * d, 5 * d]); g.lineWidth = d;
  g.beginPath(); g.arc(W / 2, W / 2, R * s, 0, Math.PI * 2); g.stroke(); g.setLineDash([]);
  g.strokeStyle = css('--rule'); g.strokeRect(W / 2 - 8 * s, W / 2 - 8 * s, 16 * s, 16 * s);
  g.fillStyle = css('--cell');
  for (let y = 0; y < view; y++) for (let x = 0; x < view; x++) if (grid[(y + o) * N + x + o]) g.fillRect(x * s, y * s, Math.max(1, s - 0.3), Math.max(1, s - 0.3));
  g.fillStyle = css('--mute'); g.font = `${11 * d}px ${css('--f-mono')}`;
  g.fillText('16×16 수프 자리', W / 2 - 8 * s, W / 2 - 8 * s - 4 * d);
}
function stop() { if (timer) clearInterval(timer); timer = null; document.getElementById('demo-play').textContent = '재생'; }
document.getElementById('demo-play').onclick = () => {
  if (timer) return stop();
  if (done) return;
  document.getElementById('demo-play').textContent = '멈춤';
  document.getElementById('r-status').textContent = '돌리는 중… 같은 모양이 반복되는지 세대마다 확인합니다.';
  timer = setInterval(() => { for (let i = 0; i < 2 && !done; i++) stepSoup(); drawSoup(); readout(); }, 40);
};
document.getElementById('demo-step').onclick = () => { if (!done) { stepSoup(); drawSoup(); readout(); } };
document.getElementById('demo-reset').onclick = resetDemo;
document.getElementById('demo-rule').onchange = () => { fillSeeds(); resetDemo(); };
document.getElementById('demo-seed').onchange = resetDemo;
addEventListener('resize', drawSoup);
fillSeeds();
resetDemo();
</script>
"""


def rule_svg():
    """Neighbourhood diagram: birth with 3 neighbours, survival with 2, death with 4."""
    def hood(ox, title, live, center, result, color):
        out = [f'<text x="{ox + 75}" y="22" text-anchor="middle" font-size="15" font-weight="600">{title}</text>']
        for j in range(3):
            for i in range(3):
                x, y = ox + i * 50, 36 + j * 50
                on = (i, j) in live or ((i, j) == (1, 1) and center)
                fill = "var(--cell)" if on else "var(--paper)"
                stroke = "var(--ink)" if (i, j) == (1, 1) else "var(--rule)"
                sw = 2.5 if (i, j) == (1, 1) else 1
                out.append(f'<rect x="{x}" y="{y}" width="46" height="46" rx="5" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        out.append(f'<text x="{ox + 75}" y="212" text-anchor="middle" font-size="14" class="m">이웃 {len(live)}칸</text>')
        out.append(f'<text x="{ox + 75}" y="236" text-anchor="middle" font-size="15" font-weight="600" fill="{color}" style="fill:{color}">{result}</text>')
        return "".join(out)
    parts = [
        hood(20, "빈 칸 + 이웃 3", {(0, 0), (2, 0), (1, 2)}, False, "B3 → 태어남", "var(--cell)"),
        hood(220, "산 칸 + 이웃 2", {(0, 1), (2, 2)}, True, "S2 → 살아남음", "var(--cell)"),
        hood(420, "산 칸 + 이웃 4", {(0, 0), (1, 0), (2, 0), (0, 2)}, True, "S에 4 없음 → 죽음", "var(--new)"),
    ]
    legend = ('<text x="620" y="70" font-size="15" class="mono" font-weight="600">b368s238</text>'
              '<text x="620" y="96" font-size="13" class="m">태어남: 이웃 3, 6, 8</text>'
              '<text x="620" y="118" font-size="13" class="m">살아남음: 이웃 2, 3, 8</text>'
              '<text x="620" y="150" font-size="13" class="m">생명 게임 = b3s23</text>'
              '<text x="620" y="172" font-size="13" class="m">B·S에 0~8을 골라 넣음: 2¹⁸개</text>'
              '<text x="620" y="194" font-size="13" class="m">B0·B1 빼면 6만 5천 개</text>')
    return f'<svg viewBox="0 0 820 250" role="img" aria-label="규칙 표기법 그림" style="min-width:620px">{"".join(parts)}{legend}</svg>'


def pipe_svg():
    steps = [
        ("1", "규칙 고르기", "1만 6천 규칙 × 수프 12~100개", "폭발·덩어리 규칙 제외, Catagolue 기록 수 조회"),
        ("2", "수프 만들기", "'lrh_b368s238_1020_' + 번호 → SHA-256", "256비트 = 16×16 칸. Catagolue와 같은 방식"),
        ("3", "안정될 때까지 돌리기 (C)", "세대마다 상태 해시를 기록", "같은 해시가 다시 나오면 주기 발견. 반경 80 밖 물체는 떼어 냄"),
        ("4", "물체 나누고 이름 붙이기", "붙어 있기만 한 두 물체는 모든 나누는 방법을 시험해 분리", "apgcode: xs=정물 xp=진동자 xq=우주선 + 모양 코드"),
        ("5", "Catagolue와 대조", "그 규칙의 전체 집계표를 내려받아 비교", "집계표에 없으면 '처음 보는 물체'"),
    ]
    out = ['<svg viewBox="0 0 820 560" role="img" aria-label="검색 과정 그림" style="min-width:560px">',
           '<defs><marker id="ar" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
           '<path d="M0,0 L10,5 L0,10 z" fill="var(--mute)"/></marker></defs>']
    for i, (n, title, a, b) in enumerate(steps):
        y = 10 + i * 110
        fill = "var(--cell-soft)" if i == 0 else "var(--panel)"
        out.append(f'<rect x="10" y="{y}" width="800" height="84" rx="10" fill="{fill}" stroke="var(--rule)"/>')
        out.append(f'<circle cx="52" cy="{y + 42}" r="20" fill="var(--cell)"/>'
                   f'<text x="52" y="{y + 48}" text-anchor="middle" font-size="17" font-weight="700" style="fill:var(--panel)">{n}</text>')
        out.append(f'<text x="92" y="{y + 32}" font-size="17" font-weight="600">{title}</text>')
        out.append(f'<text x="92" y="{y + 56}" font-size="14" class="m">{a}</text>')
        out.append(f'<text x="92" y="{y + 75}" font-size="13" class="m">{b}</text>')
        if i < len(steps) - 1:
            out.append(f'<line x1="52" y1="{y + 86}" x2="52" y2="{y + 106}" stroke="var(--mute)" stroke-width="2" marker-end="url(#ar)"/>')
    out.append('<text x="800" y="{}" text-anchor="end" font-size="12" class="m">2~5를 규칙마다 수프 100만 개씩, 10코어 병렬</text>'.format(10 + 4 * 110 + 102))
    out.append("</svg>")
    return "".join(out)


def funnel_svg(f):
    import math
    rows = [("검사한 규칙", f["rules"]), ("폭발 안 함", f["stable"]), ("물체가 잘 나뉨", f["good"]),
            ("우주선이 나옴", f["ships"]), ("Catagolue 기록 0", f["zero"]), ("검색에 고름", 3)]
    top = math.log10(max(r[1] for r in rows))
    out = ['<svg viewBox="0 0 520 300" role="img" aria-label="규칙 거르기 깔때기" style="min-width:420px">']
    for i, (label, n) in enumerate(rows):
        y = 14 + i * 46
        w = max(6, 300 * math.log10(max(n, 1)) / top)
        out.append(f'<text x="0" y="{y + 20}" font-size="14">{label}</text>')
        out.append(f'<rect x="150" y="{y + 4}" width="{w:.1f}" height="24" rx="4" fill="var(--cell)" opacity="{1 - i * 0.1:.2f}"/>')
        out.append(f'<text x="{150 + w + 8:.1f}" y="{y + 21}" font-size="14" class="mono" font-weight="600">{n:,}</text>')
    out.append("</svg>")
    return "".join(out)


def rank_table(stage2):
    by = {r["rule"]: r for r in stage2}
    ships = sorted([r for r in stage2 if r["ships_per_soup"] >= 0.03 and r["unstable"] <= 0.05 and r["blob"] < 0.5],
                   key=lambda r: -r["ships_per_soup"])
    rows = [by[p] for p in PICKS if p in by] + [r for r in ships if r["rule"] not in PICKS]

    def c1(r):
        if r.get("c1_checked"):
            return f'{r["c1"]:,}'
        return "미조회"
    out = ['<table><thead><tr><th>규칙</th><th>Catagolue C1 수프</th><th>우주선/수프</th><th>주기≥3 잿더미</th>'
           '<th>물체/수프</th><th>수프/초</th><th>폭발</th><th>고른 이유</th></tr></thead><tbody>']
    for r in rows:
        pick = r["rule"] in PICKS
        out.append(f'<tr class="{"pick" if pick else ""}"><td class="mono">{r["rule"]}</td><td>{c1(r)}</td>'
                   f'<td>{r["ships_per_soup"]:.2f}</td><td>{r["p_hi"]:.0%}</td><td>{r["objs_per_soup"]}</td>'
                   f'<td>{r["soups_per_s"]:,.0f}</td><td>{r["unstable"]:.0%}</td>'
                   f'<td class="why">{PICKS.get(r["rule"], "우주선이 나오는 안정 규칙")}</td></tr>')
    out.append("</tbody></table>")
    return "".join(out)


def main():
    import datetime
    ap = argparse.ArgumentParser()
    ap.add_argument("--rare", type=int, default=3)
    ap.add_argument("--cap", type=int, default=30)
    a = ap.parse_args()

    screen = json.load(open(os.path.join(HERE, "results", "screen_b3.json")))
    s1, s2 = screen["stage1"], screen["stage2"]
    funnel = {"rules": len(s1), "stable": len(s2),
              "good": sum(1 for r in s2 if r.get("score", -1) > 0 or r.get("intrinsic", -1) > 0),
              "ships": sum(1 for r in s2 if r["ships_per_soup"] >= 0.03 and r["unstable"] <= 0.05 and r["blob"] < 0.5),
              "zero": sum(1 for r in s2 if r.get("c1_checked") and r["c1"] == 0)}
    c1 = {r["rule"]: r["c1"] for r in s2 if r.get("c1_checked")}

    runs = {}
    for path in sorted(glob.glob(os.path.join(HERE, "results", "*_lrh_*.json"))):
        r = json.load(open(path))
        if not r["prefix"].startswith("lrh_"):
            continue
        runs[r["rule"]] = r
    vpath = os.path.join(HERE, "results", "verify.json")
    verdicts = {(v["rule"], v["code"]): v for v in json.load(open(vpath))} if os.path.exists(vpath) else {}
    out_runs = []
    demo_seeds = {}
    for rule in PICKS:
        demo_seeds[rule] = [(i, f"수프 #{i}") for i in (0, 1, 2, 7, 42)]
        r = runs.get(rule)
        if not r:
            out_runs.append({"rule": rule, "soups": 0})
            continue
        objs = r["objects"]
        rare = [o for o in objs if o["census"] is not None and o["census"] < a.rare]
        upath = os.path.join(HERE, "results", f"{rule}_unstable.json")
        recheck, emitters = None, []
        if os.path.exists(upath):
            u = json.load(open(upath))
            recheck = {"soups": u["soups"], "kinds": u["kinds"]}
            # one example per emission interval, most common intervals first
            by_p = {}
            for e in u["emitters"]:
                by_p.setdefault(e["emit_period"], []).append(e)
            emitters = [dict(v[0], n_same=len(v)) for v in sorted(by_p.values(), key=lambda v: -len(v))][:6]
            linear = 0
            cpath = os.path.join(HERE, "census_cache", f"{rule}_ALL.csv")
            if os.path.exists(cpath):
                for line in open(cpath):
                    if line.startswith('"zz_LINEAR"'):
                        linear = int(line.split(",")[1].strip().strip('"'))
            recheck["catagolue_linear"] = linear
            have = {o["code"] for o in rare}
            for o in u["objects"]:
                if o["census"] is not None and o["census"] < a.rare and o["code"] not in have:
                    rare.append({**o, "recheck": True})
            demo_seeds[rule] += [(e["soup"].split("_")[-1], f"방출 후보 #{e['soup'].split('_')[-1]}") for e in emitters[:5]]
        for o in rare:
            v = verdicts.get((rule, o["code"]))
            if v:
                o["verdict"], o["how"] = v["verdict"], v["how"]

        def rank(o):
            c = o["code"]
            p = int(c[2:].split("_")[0]) if c[:2] in ("xp", "xq") else 1
            kind = 0 if c.startswith("xq") else 1 if c.startswith("xp") and p > 2 else 2
            return (o["census"] > 0, kind, o["count"], -len(o["cells"]))
        rare.sort(key=rank)
        note = ""
        if c1.get(rule) == 0:
            note = ("이 규칙은 Catagolue C1 기록이 0이라 나온 물체가 전부 '처음'입니다. "
                    "흔한 물체까지 다 보이지 않도록 우주선과 주기 3 이상 진동자를 먼저, 이번 검색에서 드물게 나온 순으로 보여 줍니다.")
        out_runs.append({
            "rule": rule, "soups": r["soups"], "distinct": len(objs), "unstable": len(r["unstable"]),
            "new_total": sum(1 for o in objs if o["census"] == 0),
            "ship_kinds": sum(1 for o in objs if o["code"].startswith("xq")),
            "census_soups": c1.get(rule, 0), "note": note,
            "items": [{k: o[k] for k in ("code", "count", "census", "soup", "cells", "verdict", "how", "recheck") if k in o}
                      for o in rare[:a.cap]],
            "recheck": recheck, "emitters": emitters,
        })
    data = {"runs": out_runs, "demo_prefix": {p: f"lrh_{p}_1020_" for p in PICKS}, "demo_seeds": demo_seeds}
    opts = "".join(f'<option value="{p}">{p}</option>' for p in PICKS)
    page = (PAGE.replace("__RULE_SVG__", rule_svg()).replace("__PIPE_SVG__", pipe_svg())
            .replace("__FUNNEL_SVG__", funnel_svg(funnel)).replace("__RANK_TABLE__", rank_table(s2))
            .replace("__RULE_OPTIONS__", opts).replace("__RARE__", str(a.rare)).replace("__CAP__", str(a.cap))
            .replace("__DATE__", datetime.date.today().isoformat())
            .replace("__DATA__", json.dumps(data, separators=(",", ":"))))
    out = os.path.join(HERE, "gallery.html")
    open(out, "w").write(page)
    # standalone copy for Vercel (site/): same page inside a full HTML document
    os.makedirs(os.path.join(HERE, "site"), exist_ok=True)
    open(os.path.join(HERE, "site", "index.html"), "w").write(
        '<!doctype html>\n<html lang="ko"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>:root{padding-block:env(safe-area-inset-top,0px) env(safe-area-inset-bottom,0px)}body{margin:0}</style>\n'
        '</head><body>\n' + page + '\n</body></html>\n')
    print("wrote", out, sum(len(r.get("items", [])) for r in out_runs), "cards", funnel)


if __name__ == "__main__":
    main()
