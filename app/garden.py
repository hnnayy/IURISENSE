import json

import pandas as pd
import streamlit as st


BAND_MAP = {"PRIORITAS TINGGI": "Tinggi", "PERLU DITINJAU": "Sedang", "NORMAL": "Rendah"}
MODULE_LABELS = {"A": "Headcount", "B": "Peer wage", "C": "Remittance"}


def build_garden_frame(scores, wave2_scores=None):
    garden = scores[["employer_id", "sektor_usaha", "wilayah", "skala", "status", "risk_score", "module_a", "module_b", "module_c"]].copy()
    garden["band"] = garden.status.map(lambda value: BAND_MAP.get(value, value)).fillna("Belum bisa dinilai")
    garden["risk_score"] = garden.risk_score.fillna(0).astype(int)
    for column in ["module_a", "module_b", "module_c"]:
        garden[column] = garden[column].fillna(False).astype(bool)
    garden["summary"] = ""
    garden["recommendation"] = ""
    garden["drivers"] = [[] for _ in range(len(garden))]
    if wave2_scores is not None:
        extra = wave2_scores[["employer_id", "rank", "recommendation", "explanation"]].copy()
        extra["summary"] = extra.explanation.map(lambda value: value.get("summary", "") if isinstance(value, dict) else "")
        extra["drivers"] = extra.explanation.map(lambda value: [
            {"module": item.get("module"), "label": item.get("label"), "status": item.get("status"), "text": item.get("text")}
            for item in (value.get("drivers", []) if isinstance(value, dict) else [])
        ])
        garden = garden.drop(columns=["summary", "recommendation", "drivers"]).merge(
            extra[["employer_id", "rank", "summary", "recommendation", "drivers"]], on="employer_id", how="left")
        garden["summary"] = garden.summary.fillna("")
        garden["recommendation"] = garden.recommendation.fillna("")
        garden["drivers"] = garden.drivers.map(lambda value: value if isinstance(value, list) else [])
    else:
        garden["rank"] = garden.risk_score.rank(ascending=False, method="first")
        garden["summary"] = garden.apply(lambda row: "Sinyal aktif: " + (", ".join(
            f"{module} · {label}" for module, label in MODULE_LABELS.items() if row[f"module_{module.lower()}"]) or "tidak ada"), axis=1)
    garden["rank"] = pd.to_numeric(garden["rank"], errors="coerce")
    return garden.sort_values(["sektor_usaha", "wilayah", "employer_id"]).reset_index(drop=True)


def narration(garden):
    wilted = garden[garden.band.eq("Tinggi")]
    if wilted.empty:
        return "Kebun tenang — belum ada tanaman layu pada filter ini."
    worst_bed = wilted.sektor_usaha.value_counts().idxmax()
    first = wilted.sort_values(["rank", "risk_score"], ascending=[True, False]).iloc[0]
    return (f"{len(wilted)} tanaman layu dari {len(garden)} — petak terparah: {worst_bed} "
            f"({int(wilted.sektor_usaha.eq(worst_bed).sum())}). Mulai rawat dari {first.employer_id}.")


def render_garden(scores, wave2_scores=None):
    st.markdown("<div class='eyebrow'>GARDEN VIEW · ECRS</div>", unsafe_allow_html=True)
    st.title("Kebun kepatuhan pemberi kerja.")
    st.markdown("<div class='subtitle'>Setiap tanaman adalah satu pemberi kerja, setiap petak satu sektor. "
                "Tanaman layu berarti prioritas pemeriksaan — arahkan kursor untuk alasan, klik untuk detail.</div>", unsafe_allow_html=True)
    garden = build_garden_frame(scores, wave2_scores)
    if garden.empty:
        st.info("Tidak ada pemberi kerja pada filter sektor/wilayah ini.")
        return
    plants = [{
        "id": row.employer_id, "sector": row.sektor_usaha, "region": row.wilayah, "scale": row.skala,
        "band": row.band, "score": int(row.risk_score), "rank": None if pd.isna(row.rank) else int(row.rank),
        "a": bool(row.module_a), "b": bool(row.module_b), "c": bool(row.module_c),
        "summary": row.summary, "rec": row.recommendation, "drivers": row.drivers,
    } for row in garden.itertuples()]
    payload = json.dumps({"plants": plants, "narration": narration(garden)}, ensure_ascii=False).replace("</", "<\\/")
    st.iframe(GARDEN_HTML.replace("__PAYLOAD__", payload), height=780)

    st.subheader("Kondisi tiap petak")
    beds = garden.groupby("sektor_usaha").agg(
        Tanaman=("employer_id", "count"),
        Layu=("band", lambda value: int(value.eq("Tinggi").sum())),
        Menguning=("band", lambda value: int(value.eq("Sedang").sum())),
        A_Headcount=("module_a", "sum"), B_Peer_wage=("module_b", "sum"), C_Remittance=("module_c", "sum"),
    )
    beds["Sehat"] = (1 - (beds.Layu + beds.Menguning) / beds.Tanaman).map(lambda value: f"{value:.0%}")
    beds = beds.sort_values(["Layu", "Menguning"], ascending=False).reset_index().rename(columns={
        "sektor_usaha": "Petak (sektor)", "A_Headcount": "Daun rontok (A)", "B_Peer_wage": "Kerdil (B)", "C_Remittance": "Tanah kering (C)"})
    st.dataframe(beds, width="stretch", hide_index=True)
    st.caption("Garden View mengikuti filter sektor & wilayah di sidebar dan selalu menampilkan semua band risiko. "
               "Metafora hanya pembungkus visual — angka dan alasan tetap sama dengan dashboard.")


GARDEN_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400;600&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root { --wood:#5b3a21; --wood-hi:#8a5a33; --wood-lo:#3a2414; --parch:#f3e6c4; --ink:#2b1a0e; --leaf:#a8e6cf; }
  * { box-sizing:border-box; }
  body { margin:0; background:#1f3a24; font-family:'Pixelify Sans', monospace; color:var(--parch); overflow:hidden; }
  .wrap { display:grid; grid-template-columns:1fr 250px; grid-template-rows:44px minmax(0,1fr) 38px; gap:8px; height:100vh; padding:6px; }
  .panel { background:linear-gradient(var(--wood-hi), var(--wood)); border:3px solid var(--wood-lo); border-radius:6px;
           box-shadow:inset 0 0 0 2px #a8773f55, 0 2px 0 #0006; }
  .hud { grid-column:1 / 3; display:flex; align-items:center; gap:10px; padding:0 12px; }
  .hud .title { font-weight:600; letter-spacing:.06em; }
  .chip { background:#0003; border:2px solid var(--wood-lo); border-radius:4px; padding:3px 10px; font-size:14px; }
  .chip b { color:#ffd27a; }
  .stage { position:relative; overflow:hidden; border-radius:6px; border:3px solid var(--wood-lo); background:#3f7a3a; }
  canvas { image-rendering:pixelated; image-rendering:crisp-edges; display:block; position:absolute; }
  .side { display:flex; flex-direction:column; gap:6px; padding:8px; overflow:auto; }
  .btn { font:inherit; font-size:14px; color:var(--parch); text-align:left; cursor:pointer; padding:6px 10px;
         background:linear-gradient(#6d4527,#4a2d18); border:2px solid var(--wood-lo); border-radius:4px; }
  .btn:hover { filter:brightness(1.2); } .btn.on { color:#ffd27a; }
  input { font:inherit; font-size:14px; width:100%; padding:6px 8px; border-radius:4px; border:2px solid var(--wood-lo);
          background:var(--parch); color:var(--ink); }
  .legend { background:#0003; border-radius:4px; padding:6px 8px; font-size:13px; line-height:1.55; }
  .legend .sw { display:inline-block; width:10px; height:10px; margin-right:6px; border:1px solid #0008; vertical-align:middle; }
  .detail { background:var(--parch); color:var(--ink); border-radius:4px; padding:8px; font-family:'DM Sans', sans-serif; font-size:12.5px; line-height:1.4; }
  .detail h3 { margin:0 0 2px; font-family:'Pixelify Sans', monospace; font-size:16px; }
  .detail .meta { color:#6b5335; margin-bottom:6px; }
  .detail .drv { border-left:3px solid #c98b4b; padding-left:6px; margin:5px 0; }
  .detail .drv.flag { border-color:#c0392b; }
  .tag { display:inline-block; padding:1px 6px; border-radius:3px; font-size:11px; font-weight:600; color:#fff; }
  .narr { grid-column:1 / 3; display:flex; align-items:center; padding:0 12px; font-size:14px; }
  .tip { position:absolute; pointer-events:none; max-width:280px; background:#2b1a0ef2; color:var(--parch); border:2px solid #c98b4b;
         border-radius:4px; padding:6px 8px; font-family:'DM Sans', sans-serif; font-size:12px; line-height:1.35; display:none; z-index:5; }
  .tip b { font-family:'Pixelify Sans', monospace; font-size:14px; color:#ffd27a; }
</style></head>
<body>
<div class="wrap">
  <div class="panel hud">
    <span class="title">❀ VIRTUAL GARDEN · ECRS</span>
    <span class="chip" id="clock">06:00 · Fajar</span>
    <span class="chip">Layu <b id="cWilt">0</b></span>
    <span class="chip">Menguning <b id="cYellow">0</b></span>
    <span class="chip">Sehat <b id="cOk">0</b></span>
  </div>
  <div class="stage" id="stage"><canvas id="cv"></canvas><div class="tip" id="tip"></div></div>
  <div class="panel side">
    <input id="search" placeholder="Cari EMP-0001 lalu Enter">
    <button class="btn" id="bFocus">⚑ Soroti prioritas · Off</button>
    <button class="btn on" id="bCycle">☀ Siklus hari · On</button>
    <button class="btn" id="bSpeed">⏱ Waktu · 1×</button>
    <div class="legend">
      <div><span class="sw" style="background:#4caf50"></span>Sehat — band Rendah</div>
      <div><span class="sw" style="background:#c9b637"></span>Menguning — band Sedang</div>
      <div><span class="sw" style="background:#d08a3c"></span>Layu — band Tinggi</div>
      <div><span class="sw" style="background:#9ccc65"></span>Tunas — belum bisa dinilai</div>
      <div style="margin-top:4px"><span class="sw" style="background:#ff8f3a"></span>Daun rontok — A · headcount turun</div>
      <div><span class="sw" style="background:#6b8f3a"></span>Kerdil — B · upah di bawah peer</div>
      <div><span class="sw" style="background:#d9c08a"></span>Tanah retak — C · setoran kurang</div>
    </div>
    <div class="detail" id="detail"><h3>Pilih tanaman</h3><div class="meta">Klik salah satu tanaman untuk melihat alasan risikonya.</div></div>
  </div>
  <div class="panel narr" id="narr"></div>
</div>
<script>
const DATA = __PAYLOAD__;
const T = 8, S = 2, TILE = T * S;            // 8px sprite, drawn at 2x
const BED_COLS = 14, GAP = 3;                 // tiles

// ---------- sprites (palette-indexed 8x8) ----------
const SPR = {
  bush: ["..lll...", ".lgglll.", "lggfgggl", "lgggggfg", ".gGggGg.", "..GGGG..", "...tt...", "...tt..."],
  wilt: ["........", "..w.....", ".wWw....", "wW.Ww...", "...tWw..", "...t.w..", "...t....", "..ttt..."],
  sprout: ["........", "........", "........", "...ss...", "..s.ss..", "...s....", "...s....", "........"],
};
const PAL = {
  ok:     { l:"#8fd16a", g:"#4caf50", G:"#2e7d32", t:"#6d4c2f" },
  yellow: { l:"#e8d86a", g:"#c9b637", G:"#8f8a2a", t:"#6d4c2f" },
  wilt:   { w:"#f0c27a", W:"#d08a3c", t:"#9a6a3a" },
  sprout: { s:"#9ccc65" },
};
const FLOWERS = ["#ffffff", "#ff9ecb", "#ffd54f", "#b39ddb", null, null];
const hash = s => { let h = 2166136261; for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; };

function sprite(rows, pal, opts = {}) {
  const c = document.createElement("canvas"); c.width = c.height = T;
  const x = c.getContext("2d");
  const src = opts.stunted ? ["", "", ...rows.slice(2)] : rows;   // B: top cut off, sits low
  src.forEach((row, y) => [...row].forEach((k, i) => {
    let col = k === "f" ? opts.flower : pal[k];
    if (k === "f" && !opts.flower) col = pal.g;
    if (col) { x.fillStyle = col; x.fillRect(i, y, 1, 1); }
  }));
  return c;
}
const cache = {};
function plantSprite(p) {
  const kind = p.band === "Tinggi" ? "wilt" : p.band === "Sedang" ? "yellow" : p.band === "Rendah" ? "ok" : "sprout";
  const flower = kind === "ok" ? FLOWERS[hash(p.id) % FLOWERS.length] : null;
  const key = kind + (p.b ? "s" : "") + flower;
  if (!cache[key]) {
    const rows = kind === "wilt" ? SPR.wilt : kind === "sprout" ? SPR.sprout : SPR.bush;
    cache[key] = sprite(rows, PAL[kind], { flower, stunted: p.b && kind !== "sprout" });
  }
  return cache[key];
}
function soil(cracked, seed) {
  const c = document.createElement("canvas"); c.width = c.height = T;
  const x = c.getContext("2d");
  x.fillStyle = cracked ? "#d9c08a" : "#6b4a2e"; x.fillRect(0, 0, T, T);
  x.fillStyle = cracked ? "#9c7a45" : "#5a3d25";
  if (cracked) { [[1,2],[2,3],[3,3],[4,4],[5,4],[6,5],[4,5],[3,6],[5,1],[6,2]].forEach(([a,b]) => x.fillRect(a, b, 1, 1)); }
  else { for (let i = 0; i < 5; i++) x.fillRect((seed >> (i * 3)) % T, (seed >> (i * 5 + 1)) % T, 1, 1); }
  return c;
}
const soilOk = [0,1,2].map(i => soil(false, hash("s" + i))), soilDry = soil(true, 0);

// ---------- layout ----------
const sectors = [...new Set(DATA.plants.map(p => p.sector))];
const perBed = Math.max(...sectors.map(s => DATA.plants.filter(p => p.sector === s).length));
const BED_ROWS = Math.ceil(perBed / BED_COLS);
const COLS = Math.min(3, sectors.length), ROWS = Math.ceil(sectors.length / COLS);
const W = (COLS * (BED_COLS + GAP) + GAP) * TILE, H = (ROWS * (BED_ROWS + GAP + 1) + GAP) * TILE;
const beds = sectors.map((s, i) => ({ name: s, x: (GAP + (i % COLS) * (BED_COLS + GAP)) * TILE,
                                       y: (GAP + 1 + Math.floor(i / COLS) * (BED_ROWS + GAP + 1)) * TILE }));
DATA.plants.forEach(p => {
  const bed = beds[sectors.indexOf(p.sector)];
  bed.n = (bed.n || 0); const i = bed.n++;
  p.x = bed.x + (i % BED_COLS) * TILE; p.y = bed.y + Math.floor(i / BED_COLS) * TILE;
  p.seed = hash(p.id);
});
const byId = Object.fromEntries(DATA.plants.map(p => [p.id.toUpperCase(), p]));

const cv = document.getElementById("cv"), ctx = cv.getContext("2d"), stage = document.getElementById("stage");
cv.width = W; cv.height = H;
let scale = 1;
function fit() {
  scale = Math.min(stage.clientWidth / W, stage.clientHeight / H);
  cv.style.width = W * scale + "px"; cv.style.height = H * scale + "px";
  cv.style.left = (stage.clientWidth - W * scale) / 2 + "px"; cv.style.top = (stage.clientHeight - H * scale) / 2 + "px";
}
window.addEventListener("resize", fit);

// static background: grass, paths, fences, signs
const bg = document.createElement("canvas"); bg.width = W; bg.height = H;
function drawBg() {
  const x = bg.getContext("2d");
  x.fillStyle = "#4f8a3f"; x.fillRect(0, 0, W, H);
  for (let i = 0; i < W * H / 90; i++) {           // grass tufts
    const r = hash("g" + i); x.fillStyle = r % 3 ? "#5f9c49" : "#3f7434";
    x.fillRect((r % W) & ~1, ((r >> 11) % H) & ~1, 2, 2);
  }
  x.fillStyle = "#d8c08c";                          // sand paths between beds
  for (let c = 0; c <= COLS; c++) x.fillRect(c * (BED_COLS + GAP) * TILE + TILE * .75, 0, TILE * 1.5, H);
  for (let r = 0; r <= ROWS; r++) x.fillRect(0, r * (BED_ROWS + GAP + 1) * TILE + TILE * .75, W, TILE * 1.5);
  beds.forEach(b => {
    const bw = BED_COLS * TILE, bh = BED_ROWS * TILE;
    x.fillStyle = "#3a2414"; x.fillRect(b.x - 6, b.y - 6, bw + 12, bh + 12);     // fence
    x.fillStyle = "#8a5a33"; x.fillRect(b.x - 4, b.y - 4, bw + 8, bh + 8);
    x.fillStyle = "#5a3d25"; x.fillRect(b.x, b.y, bw, bh);
    for (let px = b.x - 6; px <= b.x + bw + 2; px += TILE) { x.fillStyle = "#3a2414"; x.fillRect(px, b.y - 10, 4, 6); x.fillRect(px, b.y + bh + 4, 4, 6); }
    x.font = "600 13px 'Pixelify Sans', monospace";                               // sign
    const tw = x.measureText(b.name).width + 16;
    x.fillStyle = "#3a2414"; x.fillRect(b.x + 6, b.y - TILE * 1.6 - 2, tw + 4, 22);
    x.fillStyle = "#b07a45"; x.fillRect(b.x + 8, b.y - TILE * 1.6, tw, 18);
    x.fillStyle = "#2b1a0e"; x.fillText(b.name, b.x + 16, b.y - TILE * 1.6 + 13);
  });
}

// ---------- state ----------
let focus = false, cycle = true, speed = 1, dayT = 0.25, selected = null, hover = null, last = performance.now();
const PHASES = [[0, "Malam"], [0.2, "Fajar"], [0.3, "Pagi"], [0.5, "Siang"], [0.7, "Senja"], [0.82, "Malam"]];
function tint(t) {        // ambient light over the day
  if (t < 0.2 || t >= 0.85) return "rgba(20,30,80,0.38)";
  if (t < 0.3) return "rgba(255,150,80,0.16)";
  if (t < 0.7) return null;
  return "rgba(180,80,120,0.18)";
}

function draw(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  if (cycle) dayT = (dayT + dt * speed / 90) % 1;       // 90 s per day at 1x
  ctx.drawImage(bg, 0, 0);
  const night = dayT < 0.2 || dayT >= 0.85;
  for (const p of DATA.plants) {
    ctx.drawImage(p.c ? soilDry : soilOk[p.seed % 3], p.x, p.y, TILE, TILE);
    const sway = p.band === "Rendah" && Math.sin(now / 700 + p.seed) > 0.85 ? 1 : 0;
    ctx.drawImage(plantSprite(p), p.x + sway, p.y, TILE, TILE);
    if (p.a) {                                            // A: falling leaves
      for (let k = 0; k < 2; k++) {
        const ph = ((now / 1600 + (p.seed % 97) / 97 + k / 2) % 1);
        ctx.fillStyle = k ? "#ff8f3a" : "#e0602a";
        ctx.fillRect(p.x + 3 + ((p.seed >> k) % 10) + Math.sin(ph * 6) * 2, p.y + ph * TILE, 2, 2);
      }
    }
    if (focus && (p.band === "Rendah" || p.band === "Belum bisa dinilai")) { ctx.fillStyle = "rgba(30,40,30,0.62)"; ctx.fillRect(p.x, p.y, TILE, TILE); }
  }
  const t = tint(dayT); if (t) { ctx.fillStyle = t; ctx.fillRect(0, 0, W, H); }
  if (night) {                                            // fireflies over wilted plants — "perlu dicek"
    for (const p of DATA.plants) if (p.band === "Tinggi") {
      const a = 0.5 + 0.5 * Math.sin(now / 400 + p.seed);
      ctx.fillStyle = `rgba(255,230,120,${a})`; ctx.fillRect(p.x + 7, p.y - 3 + Math.sin(now / 900 + p.seed) * 2, 2, 2);
    }
  }
  for (const [p, col] of [[hover, "#ffffffaa"], [selected, Math.floor(now / 300) % 2 ? "#ffd27a" : "#ff8f3a"]]) {
    if (!p) continue; ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.strokeRect(p.x - 1, p.y - 1, TILE + 2, TILE + 2);
  }
  const minutes = Math.floor(dayT * 24 * 60);
  const phase = PHASES.filter(([s]) => dayT >= s).pop()[1];
  document.getElementById("clock").textContent =
    `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")} · ${phase}`;
  requestAnimationFrame(draw);
}

// ---------- interaction ----------
function plantAt(ev) {
  const r = cv.getBoundingClientRect(), mx = (ev.clientX - r.left) / scale, my = (ev.clientY - r.top) / scale;
  return DATA.plants.find(p => mx >= p.x && mx < p.x + TILE && my >= p.y && my < p.y + TILE) || null;
}
const tip = document.getElementById("tip");
const bandColor = { "Tinggi": "#c0392b", "Sedang": "#b8860b", "Rendah": "#2e7d32", "Belum bisa dinilai": "#607d8b" };
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
cv.addEventListener("mousemove", ev => {
  hover = plantAt(ev); cv.style.cursor = hover ? "pointer" : "default";
  if (!hover) { tip.style.display = "none"; return; }
  tip.replaceChildren(el("b", null, hover.id), el("div", null, `${hover.band} · skor ${hover.score} · ${hover.region}`),
                      el("div", null, hover.summary || "Tidak ada sinyal menonjol."));
  const sr = stage.getBoundingClientRect();
  let left = ev.clientX - sr.left + 14, top = ev.clientY - sr.top + 14;
  tip.style.display = "block";
  if (left + tip.offsetWidth > sr.width) left -= tip.offsetWidth + 28;
  if (top + tip.offsetHeight > sr.height) top -= tip.offsetHeight + 28;
  tip.style.left = left + "px"; tip.style.top = top + "px";
});
cv.addEventListener("mouseleave", () => { hover = null; tip.style.display = "none"; });
cv.addEventListener("click", ev => { const p = plantAt(ev); if (p) select(p); });

function select(p) {
  selected = p;
  const d = document.getElementById("detail");
  const tag = el("span", "tag", p.band); tag.style.background = bandColor[p.band] || "#607d8b";
  const head = el("div", "meta", `${p.sector} · ${p.region} · ${p.scale}${p.rank ? " · rank #" + p.rank : ""}`);
  const kids = [el("h3", null, p.id), head, tag, el("div", "meta", `Skor komposit ${p.score}/100${p.rec ? " — " + p.rec : ""}`)];
  if (p.drivers && p.drivers.length) {
    p.drivers.forEach(dr => {
      const box = el("div", "drv" + (dr.status === "FLAGGED" ? " flag" : ""));
      box.append(el("b", null, `${dr.module} · ${dr.label || ""}`), el("div", null, dr.text || dr.status || ""));
      kids.push(box);
    });
  } else kids.push(el("div", "drv", p.summary || "Tidak ada sinyal menonjol."));
  kids.push(el("div", "meta", "Skor = prioritas pemeriksaan, bukan vonis."));
  d.replaceChildren(...kids);
}

document.getElementById("search").addEventListener("keydown", ev => {
  if (ev.key !== "Enter") return;
  const p = byId[ev.target.value.trim().toUpperCase()];
  ev.target.style.background = p ? "" : "#f5b7a8";
  if (p) select(p);
});
const bF = document.getElementById("bFocus"), bC = document.getElementById("bCycle"), bS = document.getElementById("bSpeed");
bF.onclick = () => { focus = !focus; bF.textContent = `⚑ Soroti prioritas · ${focus ? "On" : "Off"}`; bF.classList.toggle("on", focus); };
bC.onclick = () => { cycle = !cycle; if (!cycle) dayT = 0.5; bC.textContent = `☀ Siklus hari · ${cycle ? "On" : "Off"}`; bC.classList.toggle("on", cycle); };
bS.onclick = () => { speed = speed === 1 ? 3 : speed === 3 ? 10 : 1; bS.textContent = `⏱ Waktu · ${speed}×`; bS.classList.toggle("on", speed > 1); };

const count = b => DATA.plants.filter(p => p.band === b).length;
document.getElementById("cWilt").textContent = count("Tinggi");
document.getElementById("cYellow").textContent = count("Sedang");
document.getElementById("cOk").textContent = count("Rendah");
document.getElementById("narr").textContent = "» " + DATA.narration;
let started = false;
function start() { if (started) return; started = true; drawBg(); fit(); last = performance.now(); requestAnimationFrame(draw); }
document.fonts.ready.then(start);
setTimeout(start, 1500);   // fonts CDN unreachable → start with fallback font
</script></body></html>
"""
