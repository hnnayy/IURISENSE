import json

import pandas as pd
import streamlit as st

from garden import BAND_MAP


SOURCE_MAP = pd.DataFrame([
    ["employer_master.csv", "Registrasi badan usaha (sektor, wilayah, skala)", "e-Dabu", "B (cohort)"],
    ["headcount_timeseries.csv", "Peserta PPU aktif per bulan", "e-Dabu", "A, C"],
    ["payroll_timeseries.csv", "Upah dilaporkan (gaji pokok + tunjangan tetap)", "e-Dabu · ubah data gaji", "B, C"],
    ["resign_records.csv", "Penonaktifan peserta (resign, kontrak habis, meninggal)", "e-Dabu · penonaktifan", "A"],
    ["remittance_timeseries.csv", "Tagihan iuran vs pembayaran masuk", "Billing e-Dabu + Virtual Account bank", "C"],
    ["ground_truth.csv", "Label kecurangan (kunci jawaban simulasi)", "Hasil pemeriksaan kepatuhan petugas", "Validasi"],
], columns=["File dummy", "Isi", "Padanan di dunia nyata", "Dipakai modul"])


def _clean(value):
    return None if value is None or (isinstance(value, float) and pd.isna(value)) else value


def build_jobs(scores):
    jobs = []
    for row in scores.itertuples():
        status = {}
        why = {}
        for module in ["A", "B", "C"]:
            flagged = bool(getattr(row, f"module_{module.lower()}", False) is True)
            status[module] = _clean(getattr(row, f"status_{module}", None)) or ("FLAGGED" if flagged else "NORMAL")
            reason = _clean(getattr(row, f"reason_{module}", None))
            if reason and status[module] != "NORMAL":
                why[module] = reason
        band = _clean(row.status)
        jobs.append({
            "id": row.employer_id, "sector": row.sektor_usaha, "region": row.wilayah, "scale": row.skala,
            "band": BAND_MAP.get(band, band) or "Belum bisa dinilai", "score": int(_clean(row.risk_score) or 0),
            "st": status, "why": why, "gap": float(_clean(getattr(row, "C_total_shortfall", 0)) or 0),
        })
    return jobs


def render_workspace(scores, meta=None):
    meta = meta or {}
    st.markdown("<div class='eyebrow'>WORKSPACE · ALUR DATA ECRS</div>", unsafe_allow_html=True)
    st.title("Dari e-Dabu sampai meja pemeriksa.")
    st.markdown("<div class='subtitle'>Replay bagaimana engine mengolah data tiap pemberi kerja: sumber data di lantai bawah, "
                "tiga modul deteksi di tengah, keputusan prioritas di atas. Arahkan kursor ke ruangan untuk penjelasannya.</div>", unsafe_allow_html=True)
    if scores.empty:
        st.info("Tidak ada pemberi kerja pada filter sektor/wilayah ini.")
        return
    payload = json.dumps({"jobs": build_jobs(scores), "generated": str(meta.get("generated_at", ""))[:10]}, ensure_ascii=False).replace("</", "<\\/")
    st.iframe(WORKSPACE_HTML.replace("__PAYLOAD__", payload), height=820)
    with st.expander("Peta sumber data: file dummy ↔ sistem asli", expanded=False):
        st.dataframe(SOURCE_MAP, width="stretch", hide_index=True)
        st.caption("Engine berjalan batch: data dihitung sekali, hasilnya disimpan ke output_scores.json. "
                   "Workspace ini memutar ulang hasil tersebut — bukan pemrosesan live. Data sepenuhnya simulasi.")


WORKSPACE_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root { --bg:#070b14; --panel:#0c1322; --line:#1c2a44; --text:#dbe6f5; --mute:#7f8fa9; --acc:#38bdf8; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:13px 'Inter', sans-serif; overflow:hidden; }
  .wrap { display:grid; grid-template-columns:250px minmax(0,1fr) 270px; grid-template-rows:52px minmax(0,1fr) 70px; gap:6px; height:100vh; padding:6px; }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; }
  .top { grid-column:1 / 4; display:flex; align-items:center; gap:8px; padding:0 12px; overflow:hidden; }
  .brand { font-weight:700; font-size:15px; white-space:nowrap; } .brand span { color:var(--acc); }
  .pill { font:600 10.5px 'JetBrains Mono', monospace; padding:3px 8px; border-radius:99px; border:1px solid #f59e0b66; color:#fbbf24; white-space:nowrap; }
  .kpis { display:flex; gap:6px; margin-left:auto; }
  .kpi { border:1px solid var(--line); border-radius:6px; padding:3px 9px; min-width:78px; }
  .kpi .l { font-size:9.5px; color:var(--mute); text-transform:uppercase; letter-spacing:.05em; white-space:nowrap; }
  .kpi .v { font:600 14px 'JetBrains Mono', monospace; }
  .side { display:flex; flex-direction:column; min-height:0; padding:10px; }
  .side h4 { margin:0 0 8px; font-size:12.5px; display:flex; justify-content:space-between; align-items:center; }
  .chips { display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px; }
  .chip { font:inherit; font-size:11px; padding:2px 8px; border-radius:5px; border:1px solid var(--line); background:#101a2e; color:var(--mute); cursor:pointer; }
  .chip.on { background:#1d4ed8; color:#fff; border-color:#1d4ed8; }
  .log { overflow:auto; flex:1; min-height:0; font-size:11.5px; line-height:1.35; }
  .log div { padding:5px 6px; border-left:2px solid var(--line); margin-bottom:4px; background:#0a1120; border-radius:0 4px 4px 0; }
  .log .t { font-family:'JetBrains Mono', monospace; color:var(--mute); font-size:10px; }
  .queue { overflow:auto; flex:1; min-height:0; }
  .q { display:grid; grid-template-columns:1fr auto auto; gap:6px; align-items:center; padding:5px 6px; border-radius:5px; cursor:pointer; font-size:12px; }
  .q:hover, .q.sel { background:#13213b; }
  .q .id { font-family:'JetBrains Mono', monospace; } .q .fl { color:var(--mute); font-size:10.5px; }
  .band { font-size:10px; font-weight:700; padding:1px 6px; border-radius:4px; }
  .detail { border-top:1px solid var(--line); margin-top:8px; padding-top:8px; font-size:11.5px; line-height:1.4; max-height:45%; overflow:auto; }
  .detail b { font-family:'JetBrains Mono', monospace; }
  .detail .r { border-left:2px solid #f87171; padding-left:6px; margin:5px 0; }
  .stage { position:relative; overflow:hidden; background:radial-gradient(ellipse at 50% 30%, #0f1b33 0%, #070b14 70%); }
  canvas { position:absolute; inset:0; }
  .ctrl { position:absolute; top:8px; right:8px; display:flex; gap:4px; z-index:3; }
  .ctrl button { font:inherit; font-size:11.5px; padding:4px 9px; border-radius:5px; border:1px solid var(--line); background:#0c1322e6; color:var(--text); cursor:pointer; }
  .ctrl button:hover { border-color:var(--acc); }
  .prog { position:absolute; left:10px; right:10px; bottom:8px; height:3px; background:#16233d; border-radius:2px; z-index:3; }
  .prog i { display:block; height:100%; width:0; background:linear-gradient(90deg,#38bdf8,#2dd4bf); border-radius:2px; }
  .tip { position:absolute; display:none; pointer-events:none; max-width:270px; padding:7px 9px; border-radius:6px; background:#0b1222f2;
         border:1px solid var(--acc); font-size:11.5px; line-height:1.4; z-index:4; }
  .tip b { display:block; margin-bottom:2px; }
  .agents { grid-column:1 / 4; display:grid; grid-template-columns:repeat(5, 1fr); gap:6px; background:none; border:none; }
  .agent { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:7px 10px; display:grid; grid-template-columns:auto 1fr; gap:2px 8px; align-items:center; }
  .agent .dot { width:22px; height:22px; border-radius:50%; grid-row:1 / 3; display:grid; place-items:center; font:700 11px 'JetBrains Mono', monospace; color:#07101f; }
  .agent .n { font-weight:600; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .agent .s { font:10.5px 'JetBrains Mono', monospace; color:var(--mute); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .agent.busy { border-color:#2dd4bf66; }
</style></head>
<body>
<div class="wrap">
  <div class="panel top">
    <div class="brand"><span>◈</span> Kantor Virtual ECRS</div>
    <div class="pill" id="replay">REPLAY · hasil engine</div>
    <div class="kpis">
      <div class="kpi"><div class="l">Diproses</div><div class="v" id="kDone">0</div></div>
      <div class="kpi"><div class="l">Flag A</div><div class="v" id="kA" style="color:#fb923c">0</div></div>
      <div class="kpi"><div class="l">Flag B</div><div class="v" id="kB" style="color:#a78bfa">0</div></div>
      <div class="kpi"><div class="l">Flag C</div><div class="v" id="kC" style="color:#f472b6">0</div></div>
      <div class="kpi"><div class="l">Antrian</div><div class="v" id="kQ" style="color:#f87171">0</div></div>
      <div class="kpi"><div class="l">Potensi gap</div><div class="v" id="kGap">Rp 0</div></div>
    </div>
  </div>
  <div class="panel side">
    <h4>Aktivitas langsung <span class="t" id="clock" style="font:10px 'JetBrains Mono';color:var(--mute)">00:00</span></h4>
    <div class="chips" id="chips"></div>
    <div class="log" id="log"></div>
  </div>
  <div class="panel stage" id="stage">
    <canvas id="cv"></canvas>
    <div class="ctrl">
      <button id="bPlay">⏸ Jeda</button><button id="bSpeed">1×</button><button id="bEnd">⏭ Selesaikan</button><button id="bReset">↺ Ulang</button>
    </div>
    <div class="prog"><i id="prog"></i></div>
    <div class="tip" id="tip"></div>
  </div>
  <div class="panel side">
    <h4>Antrian pemeriksaan <span id="qCount" style="color:var(--mute);font-weight:400">0</span></h4>
    <div class="queue" id="queue"></div>
    <div class="detail" id="detail" style="color:var(--mute)">Klik perusahaan di antrian untuk melihat alasan dari engine.</div>
  </div>
  <div class="agents" id="agents"></div>
</div>
<script>
const DATA = __PAYLOAD__;
const COL = { src:"#38bdf8", A:"#fb923c", B:"#a78bfa", C:"#f472b6", comp:"#2dd4bf", queue:"#f87171", arch:"#4ade80" };
const STATUS_COL = { FLAGGED:"#f87171", ONE_OFF_GAP:"#fbbf24", EXPLAINED_BY_RESIGN:"#fbbf24", NORMAL:"#4ade80" };
const BAND_COL = { "Tinggi":"#f87171", "Sedang":"#fbbf24", "Rendah":"#4ade80", "Belum bisa dinilai":"#94a3b8" };
const hash = s => { let h = 2166136261; for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; };
const rupiah = v => v >= 1e9 ? `Rp ${(v / 1e9).toFixed(1)} M` : v >= 1e6 ? `Rp ${(v / 1e6).toFixed(0)} jt` : `Rp ${Math.round(v).toLocaleString("id-ID")}`;
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
if (DATA.generated) document.getElementById("replay").textContent = `REPLAY · hasil engine ${DATA.generated} · data simulasi`;

// ---------- world: 3 floors, oblique projection ----------
const FLOORS = [
  { label:"LANTAI 1 · SUMBER DATA (simulasi e-Dabu)", z:0,   dx:0 },
  { label:"LANTAI 2 · ENGINE ECRS",                   z:3.7, dx:.7 },
  { label:"LANTAI 3 · KEPUTUSAN",                     z:7.4, dx:1.4 },
];
const ROOMS = {
  reg:     { f:0, x:[.2, 1.9],  name:"Registrasi BU", col:COL.src, desc:"Data pendaftaran badan usaha: sektor, wilayah, skala. Module B memakainya untuk menentukan cohort 'perusahaan sejenis'. (employer_master.csv)" },
  peserta: { f:0, x:[2.1, 3.8], name:"Peserta aktif", col:COL.src, desc:"Jumlah pekerja PPU yang didaftarkan per bulan. Dipakai Module A (headcount) dan C (tagihan). (headcount_timeseries.csv)" },
  upah:    { f:0, x:[4.0, 5.7], name:"Data upah",     col:COL.src, desc:"Upah yang dilaporkan badan usaha (gaji pokok + tunjangan tetap) sebagai dasar iuran. Dipakai Module B dan C. (payroll_timeseries.csv)" },
  keluar:  { f:0, x:[5.9, 7.6], name:"Penonaktifan",  col:COL.src, desc:"Peserta yang dinonaktifkan: resign, kontrak habis, meninggal. Pembanding Module A — penurunan headcount wajar jika ada catatannya. (resign_records.csv)" },
  billing: { f:0, x:[7.8, 9.8], name:"Billing & VA", col:COL.src, desc:"Tagihan iuran badan usaha vs pembayaran yang masuk lewat Virtual Account bank. Dipakai Module C. (remittance_timeseries.csv)" },
  A:       { f:1, x:[.4, 3.2],  name:"Module A · PDS Tenaga Kerja", col:COL.A, desc:"Mendeteksi headcount turun tajam (z-score terhadap riwayatnya) yang tidak dijelaskan catatan penonaktifan — indikasi pekerja disembunyikan." },
  B:       { f:1, x:[3.6, 6.4], name:"Module B · PDS Upah",         col:COL.B, desc:"Membandingkan upah dengan median cohort sektor × wilayah × skala. Flag jika jauh di bawah dan konsisten — indikasi upah dilaporkan lebih rendah." },
  C:       { f:1, x:[6.8, 9.6], name:"Module C · Rekonsiliasi iuran", col:COL.C, desc:"Mencocokkan tagihan vs setoran. Flag jika kurang setor melewati toleransi berbulan-bulan berturut-turut; kurang sekali dianggap wajar." },
  comp:    { f:2, x:[.4, 3.4],  name:"Wave 2 · Skor komposit",   col:COL.comp, desc:"Skor tiga modul dinormalisasi lalu dirata-rata menjadi skor komposit, kemudian dikelompokkan ke band Tinggi / Sedang / Rendah." },
  queue:   { f:2, x:[3.8, 6.8], name:"Antrian pemeriksaan",      col:COL.queue, desc:"Band Tinggi & Sedang diteruskan ke petugas pemeriksa kepatuhan, lengkap dengan alasannya. Prioritas pemeriksaan, bukan vonis." },
  arch:    { f:2, x:[7.2, 9.6], name:"Arsip · dipantau",          col:COL.arch, desc:"Band Rendah atau belum bisa dinilai. Tidak diperiksa sekarang, tetap dipantau pada periode berikutnya." },
};
const Y0 = .35, Y1 = 2.55, WALL = .8, SLAB = [0, 10, 0, 2.9];
const room = k => ROOMS[k], fl = r => FLOORS[r.f];
const center = k => { const r = room(k); return [(r.x[0] + r.x[1]) / 2 + fl(r).dx, (Y0 + Y1) / 2, fl(r).z + .35]; };

const AX = [Math.cos(.17), Math.sin(.17)], AY = [.55, -.34];
let S = 40, OX = 0, OY = 0;
const P = (x, y, z) => [OX + (x * AX[0] + y * AY[0]) * S, OY + (x * AX[1] + y * AY[1] - z) * S];

const cv = document.getElementById("cv"), ctx = cv.getContext("2d"), stage = document.getElementById("stage");
let VW = 0, VH = 0;
function fit() {
  const dpr = window.devicePixelRatio || 1;
  VW = stage.clientWidth; VH = stage.clientHeight;
  cv.width = VW * dpr; cv.height = VH * dpr; cv.style.width = VW + "px"; cv.style.height = VH + "px";
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  S = 1; OX = 0; OY = 0;
  const pts = [];
  FLOORS.forEach(f => [[SLAB[0], SLAB[2]], [SLAB[1], SLAB[2]], [SLAB[0], SLAB[3]], [SLAB[1], SLAB[3]]].forEach(([x, y]) => {
    pts.push(P(x + f.dx, y, f.z - .3), P(x + f.dx, y, f.z + WALL + .9));
  }));
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const bw = Math.max(...xs) - Math.min(...xs), bh = Math.max(...ys) - Math.min(...ys);
  S = Math.min((VW - 40) / bw, (VH - 60) / bh);
  OX = (VW - bw * S) / 2 - Math.min(...xs) * S;
  OY = (VH - bh * S) / 2 - Math.min(...ys) * S + 8;
}
window.addEventListener("resize", fit);

function poly(pts, fill, stroke, glow) {
  ctx.beginPath(); pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.closePath();
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.save(); ctx.strokeStyle = stroke; ctx.lineWidth = 1.2; if (glow) { ctx.shadowColor = stroke; ctx.shadowBlur = glow; } ctx.stroke(); ctx.restore(); }
}
const quad = (x0, x1, y0, y1, z) => [P(x0, y0, z), P(x1, y0, z), P(x1, y1, z), P(x0, y1, z)];
function label(x, y, text, col, now, strong) {
  ctx.font = `600 ${Math.max(9, S * .24)}px Inter, sans-serif`;
  const w = ctx.measureText(text).width + 16, h = Math.max(15, S * .4);
  ctx.save(); ctx.shadowColor = col; ctx.shadowBlur = strong ? 16 : 8;
  ctx.fillStyle = "#0b1222"; ctx.strokeStyle = col; ctx.lineWidth = 1.2;
  ctx.beginPath(); ctx.roundRect(x - w / 2, y - h / 2, w, h, h / 2); ctx.fill(); ctx.stroke(); ctx.restore();
  ctx.fillStyle = "#e6f0ff"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(text, x, y + .5);
  ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
}

function drawFloor(f, i, now) {
  const [x0, x1, y0, y1] = SLAB, dx = f.dx, z = f.z;
  poly([P(x0 + dx, y0, z), P(x1 + dx, y0, z), P(x1 + dx, y0, z - .3), P(x0 + dx, y0, z - .3)], "#0d1628", "#23385c");
  poly([P(x1 + dx, y0, z), P(x1 + dx, y1, z), P(x1 + dx, y1, z - .3), P(x1 + dx, y0, z - .3)], "#0a1220", "#23385c");
  poly(quad(x0 + dx, x1 + dx, y0, y1, z), "#111c32", "#2a4270");
  for (let k = 0; k <= 40; k++) {                                   // string lights on the slab edge
    const [px, py] = P(x0 + dx + (x1 - x0) * k / 40, y0, z - .05);
    const on = .55 + .45 * Math.sin(now / 500 + k * 1.3 + i);
    ctx.fillStyle = `rgba(255,214,140,${on})`; ctx.beginPath(); ctx.arc(px, py, Math.max(1, S * .035), 0, 7); ctx.fill();
  }
  const [lx, ly] = P(x0 + dx, y0, z - .3);
  ctx.font = `600 ${Math.max(9, S * .2)}px 'JetBrains Mono', monospace`; ctx.fillStyle = "#6f86ad";
  ctx.fillText(f.label, lx, ly + Math.max(14, S * .42));
}

function drawRoom(k, now) {
  const r = room(k), f = fl(r), dx = f.dx, z = f.z, x0 = r.x[0] + dx, x1 = r.x[1] + dx;
  const hot = busy[k] > now - 250 || hoverRoom === k;
  poly(quad(x0, x1, Y0, Y1, z + .01), r.col + (hot ? "30" : "18"), r.col + "88", hot ? 10 : 0);
  poly([P(x0, Y1, z), P(x1, Y1, z), P(x1, Y1, z + WALL), P(x0, Y1, z + WALL)], "#101b30cc", r.col + "aa", hot ? 12 : 5);   // back wall
  poly([P(x0, Y0, z), P(x0, Y1, z), P(x0, Y1, z + WALL), P(x0, Y0, z + WALL)], "#0c1628aa", r.col + "55");              // left wall
  // wall screen / shelves
  const [sx, sy] = P((x0 + x1) / 2 - .5, Y1 - .01, z + .25);
  const bars = r.f === 0 ? 6 : 4;
  for (let b = 0; b < bars; b++) {
    const hgt = (.15 + .35 * ((Math.sin(now / 600 + b + hash(k) % 7) + 1) / 2)) * S;
    ctx.fillStyle = r.col + (hot ? "dd" : "88"); ctx.fillRect(sx + b * S * .17, sy - hgt, S * .1, hgt);
  }
  // desks + agents
  const seats = r.f === 0 ? 1 : 2;
  for (let s = 0; s < seats; s++) {
    const ax = x0 + (x1 - x0) * (s + 1) / (seats + 1), ay = (Y0 + Y1) / 2;
    poly(quad(ax - .3, ax + .3, ay + .15, ay + .5, z + .3), "#1a2946", "#34507e");
    const [mx, my] = P(ax, ay + .5, z + .3);
    ctx.fillStyle = hot ? r.col : "#223452"; ctx.fillRect(mx - S * .15, my - S * .3, S * .3, S * .2);
    const bob = Math.sin(now / 300 + s * 2 + hash(k)) * (hot ? 1.5 : .4);
    const [px, py] = P(ax, ay - .1, z);
    ctx.fillStyle = "#c7d4ea"; ctx.beginPath(); ctx.roundRect(px - S * .09, py - S * .42 + bob, S * .18, S * .3, S * .06); ctx.fill();
    ctx.fillStyle = "#f1d3b3"; ctx.beginPath(); ctx.arc(px, py - S * .5 + bob, S * .08, 0, 7); ctx.fill();
  }
  const [lx, ly] = P((x0 + x1) / 2, Y1, z + WALL + .35);
  label(lx, ly, r.name, r.col, now, hot);
  r.box = [P(x0, Y0, z), P(x1, Y0, z), P(x1, Y1, z + WALL + .6), P(x0, Y1, z + WALL + .6)];
}

// ---------- replay timeline ----------
const JOBS = DATA.jobs.slice().sort((a, b) => hash(a.id) - hash(b.id));
const GAP = .28, T1 = 1.0, T2 = 1.6, T3 = 2.5, T4 = 2.9, T5 = 3.7, END = JOBS.length * GAP + T5;
const FEEDS = [["peserta", "A"], ["keluar", "A"], ["reg", "B"], ["upah", "B"], ["billing", "C"]];
let tau = 0, speed = 1, playing = true, last = performance.now();
let busy = {}, hoverRoom = null, logFilter = "Semua", selectedId = null;
let state;
function reset() {
  tau = 0; busy = {};
  state = { next: 0, done: 0, flags: { A: 0, B: 0, C: 0 }, queue: [], gap: 0, archived: 0, log: [], agent: {}, stage: JOBS.map(() => 0) };
  document.getElementById("log").replaceChildren(); renderQueue(); renderKpis();
}
function pushLog(kind, text, col) {
  const t = Math.floor(tau);
  state.log.push({ kind, text, col, t: `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}` });
  if (state.log.length > 160) state.log.shift();
  logDirty = true;
}
let logDirty = false;
function step() {           // fire events whose time has passed
  const upto = Math.min(JOBS.length, Math.floor(tau / GAP) + 1);
  for (let i = Math.max(0, state.done - 40); i < upto; i++) {
    const j = JOBS[i], t = tau - i * GAP, s = state.stage[i];
    if (s < 1 && t >= 0) { state.stage[i] = 1; state.agent.src = j.id; }
    if (s < 2 && t >= T2) {
      state.stage[i] = 2;
      for (const m of ["A", "B", "C"]) {
        state.agent[m] = j.id;
        if (j.st[m] === "FLAGGED") { state.flags[m]++; pushLog(m, `Agen ${m} · ${j.id} FLAGGED — ${j.why[m] || "melewati threshold"}`, COL[m]); }
      }
    }
    if (s < 3 && t >= T4) { state.stage[i] = 3; state.agent.comp = j.id; }
    if (s < 4 && t >= T5) {
      state.stage[i] = 4; state.done = Math.max(state.done, i + 1); state.gap += j.gap;
      if (j.band === "Tinggi" || j.band === "Sedang") {
        state.queue.push(j); state.queue.sort((a, b) => b.score - a.score); queueDirty = true;
        pushLog("Antrian", `Masuk antrian: ${j.id} · ${j.band} · skor ${j.score} (${j.sector}, ${j.region})`, BAND_COL[j.band]);
      } else if (++state.archived % 50 === 0) pushLog("Arsip", `${state.archived} perusahaan normal diarsipkan`, COL.arch);
    }
  }
}
let queueDirty = false;

function lerp(a, b, t) { return a.map((v, i) => v + (b[i] - v) * t); }
function packet(from, to, t, col, big) {
  const e = t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  const mid = lerp(from, to, .5); mid[2] += .8;                       // arc upward
  const p = e < .5 ? lerp(from, mid, e * 2) : lerp(mid, to, (e - .5) * 2);
  const [x, y] = P(...p);
  ctx.save(); ctx.shadowColor = col; ctx.shadowBlur = 10; ctx.fillStyle = col;
  ctx.fillRect(x - S * (big ? .09 : .06), y - S * (big ? .09 : .06), S * (big ? .18 : .12), S * (big ? .18 : .12)); ctx.restore();
}
function drawPackets(now) {
  const lo = Math.max(0, Math.floor((tau - T5) / GAP)), hi = Math.min(JOBS.length - 1, Math.floor(tau / GAP));
  for (let i = lo; i <= hi; i++) {
    const j = JOBS[i], t = tau - i * GAP;
    if (t < 0 || t > T5) continue;
    if (t < T1) FEEDS.forEach(([s, m]) => { busy[s] = now; packet(center(s), center(m), t / T1, COL.src); });
    else if (t < T2) ["A", "B", "C"].forEach(m => busy[m] = now);
    else if (t < T3) ["A", "B", "C"].forEach(m => packet(center(m), center("comp"), (t - T2) / (T3 - T2), STATUS_COL[j.st[m]] || "#94a3b8"));
    else if (t < T4) busy.comp = now;
    else {
      const dest = j.band === "Tinggi" || j.band === "Sedang" ? "queue" : "arch";
      packet(center("comp"), center(dest), (t - T4) / (T5 - T4), BAND_COL[j.band], true);
      if (t > T5 - .15) busy[dest] = now;
    }
  }
}

function frame(now) {
  const dt = Math.min(.1, (now - last) / 1000); last = now;
  if (playing && tau < END) tau = Math.min(END, tau + dt * speed);
  step();
  ctx.clearRect(0, 0, VW, VH);
  for (let i = FLOORS.length - 1; i >= 0; i--) {                     // back (top) floor first
    drawFloor(FLOORS[i], i, now);
    Object.keys(ROOMS).filter(k => ROOMS[k].f === i).forEach(k => drawRoom(k, now));
  }
  drawPackets(now);
  document.getElementById("prog").style.width = (tau / END * 100) + "%";
  const t = Math.floor(tau); document.getElementById("clock").textContent = `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
  if (logDirty) renderLog(); if (queueDirty) renderQueue();
  renderKpis(); renderAgents();
  requestAnimationFrame(frame);
}

// ---------- panels ----------
const LOG_KINDS = ["Semua", "A", "B", "C", "Antrian"];
const chips = document.getElementById("chips");
LOG_KINDS.forEach(k => { const b = el("button", "chip" + (k === logFilter ? " on" : ""), k); b.onclick = () => { logFilter = k; [...chips.children].forEach(c => c.classList.toggle("on", c === b)); renderLog(); }; chips.append(b); });
function renderLog() {
  logDirty = false;
  const box = document.getElementById("log");
  const rows = state.log.filter(r => logFilter === "Semua" || r.kind === logFilter).slice(-60).reverse().map(r => {
    const d = el("div"); d.style.borderLeftColor = r.col; d.append(el("span", "t", r.t + "  "), document.createTextNode(r.text)); return d;
  });
  box.replaceChildren(...rows);
}
function renderQueue() {
  queueDirty = false;
  document.getElementById("qCount").textContent = state.queue.length;
  document.getElementById("queue").replaceChildren(...state.queue.map(j => {
    const row = el("div", "q" + (j.id === selectedId ? " sel" : ""));
    const band = el("span", "band", j.band); band.style.background = BAND_COL[j.band] + "33"; band.style.color = BAND_COL[j.band];
    const flags = ["A", "B", "C"].filter(m => j.st[m] === "FLAGGED").join("·") || "—";
    const left = el("div"); left.append(el("div", "id", j.id), el("div", "fl", `${j.sector} · sinyal ${flags}`));
    row.append(left, band, el("span", "id", String(j.score)));
    row.onclick = () => { selectedId = j.id; renderQueue(); renderDetail(j); };
    return row;
  }));
}
function renderDetail(j) {
  const d = document.getElementById("detail"); d.style.color = "var(--text)";
  const kids = [el("b", null, j.id), el("div", null, `${j.sector} · ${j.region} · ${j.scale} — ${j.band}, skor ${j.score}/100`)];
  ["A", "B", "C"].forEach(m => { if (j.why[m]) { const r = el("div", "r", `${m} (${j.st[m]}): ${j.why[m]}`); r.style.borderColor = STATUS_COL[j.st[m]] || "#94a3b8"; kids.push(r); } });
  kids.push(el("div", null, "Skor = prioritas pemeriksaan, bukan vonis."));
  d.replaceChildren(...kids);
}
function renderKpis() {
  document.getElementById("kDone").textContent = `${state.done}/${JOBS.length}`;
  ["A", "B", "C"].forEach(m => document.getElementById("k" + m).textContent = state.flags[m]);
  document.getElementById("kQ").textContent = state.queue.length;
  document.getElementById("kGap").textContent = rupiah(state.gap);
}
const AGENTS = [["src", "Ingest · e-Dabu", COL.src, "↓"], ["A", "Agen A · Headcount", COL.A, "A"], ["B", "Agen B · Peer wage", COL.B, "B"],
                ["C", "Agen C · Rekonsiliasi", COL.C, "C"], ["comp", "Agen Komposit", COL.comp, "Σ"]];
const agentBox = document.getElementById("agents");
const agentEls = AGENTS.map(([k, name, col, icon]) => {
  const card = el("div", "agent"), dot = el("div", "dot", icon); dot.style.background = col;
  const s = el("div", "s", "idle"); card.append(dot, el("div", "n", name), s); agentBox.append(card); return { k, card, s };
});
function renderAgents() {
  const now = performance.now();
  agentEls.forEach(({ k, card, s }) => {
    const room = k === "src" ? "billing" : k, active = busy[room] > now - 300 && tau < END;
    card.classList.toggle("busy", active);
    const extra = k in state.flags ? ` · flag ${state.flags[k]}` : k === "comp" ? ` · antrian ${state.queue.length}` : "";
    s.textContent = (active ? `memeriksa ${state.agent[k] || "…"}` : tau >= END ? "selesai" : "idle") + extra;
  });
}

// ---------- controls & hover ----------
const bPlay = document.getElementById("bPlay"), bSpeed = document.getElementById("bSpeed");
bPlay.onclick = () => { playing = !playing; bPlay.textContent = playing ? "⏸ Jeda" : "▶ Putar"; };
bSpeed.onclick = () => { speed = speed === 1 ? 4 : speed === 4 ? 16 : 1; bSpeed.textContent = speed + "×"; };
document.getElementById("bEnd").onclick = () => { tau = END; };
document.getElementById("bReset").onclick = () => { reset(); playing = true; bPlay.textContent = "⏸ Jeda"; };
const tip = document.getElementById("tip");
function inside(pt, box) {
  let c = false;
  for (let i = 0, j = box.length - 1; i < box.length; j = i++) {
    const [xi, yi] = box[i], [xj, yj] = box[j];
    if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi) c = !c;
  }
  return c;
}
cv.addEventListener("mousemove", ev => {
  const r = cv.getBoundingClientRect(), pt = [ev.clientX - r.left, ev.clientY - r.top];
  hoverRoom = Object.keys(ROOMS).find(k => ROOMS[k].box && inside(pt, ROOMS[k].box)) || null;
  if (!hoverRoom) { tip.style.display = "none"; return; }
  const rm = ROOMS[hoverRoom];
  tip.replaceChildren(el("b", null, rm.name), document.createTextNode(rm.desc)); tip.style.borderColor = rm.col; tip.style.display = "block";
  let left = pt[0] + 14, top = pt[1] + 14;
  if (left + tip.offsetWidth > VW) left = pt[0] - tip.offsetWidth - 14;
  if (top + tip.offsetHeight > VH) top = pt[1] - tip.offsetHeight - 14;
  tip.style.left = left + "px"; tip.style.top = top + "px";
});
cv.addEventListener("mouseleave", () => { hoverRoom = null; tip.style.display = "none"; });

reset(); fit();
let started = false;
function start() { if (started) return; started = true; fit(); last = performance.now(); requestAnimationFrame(frame); }
document.fonts.ready.then(start);
setTimeout(start, 1500);
</script></body></html>
"""
