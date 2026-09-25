from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import json


st.set_page_config(page_title="ECRS | Employer Risk Console", page_icon="◈", layout="wide")
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "dummy"
SECTORS = ["Manufaktur", "Konstruksi", "Perdagangan & Ritel", "Jasa Keuangan", "Teknologi & Digital", "Perkebunan & Agribisnis"]
REGIONS = ["DKI Jakarta", "Jawa Barat", "Jawa Timur", "Sumatera Utara", "Sulawesi Selatan"]
SCALES = ["Kecil", "Menengah", "Besar"]
PERIODS = pd.period_range("2025-01", "2025-12", freq="M").astype(str).tolist()


def rupiah(value):
    value = float(value or 0)
    if abs(value) >= 1_000_000_000:
        return f"Rp {value / 1_000_000_000:.1f} M"
    if abs(value) >= 1_000_000:
        return f"Rp {value / 1_000_000:.1f} jt"
    return f"Rp {value:,.0f}".replace(",", ".")


@st.cache_data(show_spinner=False)
def make_demo_data():
    rng = np.random.default_rng(42)
    rows = []
    wage_bases = {"Manufaktur": 4_800_000, "Konstruksi": 4_500_000, "Perdagangan & Ritel": 3_800_000, "Jasa Keuangan": 7_500_000, "Teknologi & Digital": 8_500_000, "Perkebunan & Agribisnis": 3_400_000}
    region_factors = {"DKI Jakarta": 1.15, "Jawa Barat": 1, "Jawa Timur": .95, "Sumatera Utara": .90, "Sulawesi Selatan": .88}
    scale_factors = {"Kecil": .90, "Menengah": 1, "Besar": 1.12}
    for employer_number in range(1, 181):
        sector = SECTORS[(employer_number - 1) % len(SECTORS)]
        region = REGIONS[((employer_number - 1) // len(SECTORS)) % len(REGIONS)]
        scale = SCALES[(employer_number - 1) % len(SCALES)]
        headcount = max(12, int(rng.normal({"Kecil": 38, "Menengah": 145, "Besar": 510}[scale], 20)))
        wage_factor = rng.uniform(.96, 1.04)
        employer_id = f"EMP-{employer_number:04d}"
        for period in PERIODS:
            headcount = max(1, round(headcount * (1 + rng.normal(0, .018))))
            wage = wage_bases[sector] * region_factors[region] * scale_factors[scale] * wage_factor * (1 + rng.normal(0, .012))
            expected = wage * headcount * .04
            rows.append({"employer_id": employer_id, "periode": period, "sektor_usaha": sector, "wilayah": region, "skala": scale, "jumlah_peserta_aktif": headcount, "rata2_DPI": round(wage, -2), "expected_contribution": round(expected, -3), "actual_remittance": round(expected * (1 + rng.normal(0, .008)), -3), "jumlah_keluar": max(0, int(rng.poisson(max(.3, headcount * .01))))})
    data = pd.DataFrame(rows)
    labels = {employer: "CLEAN" for employer in data.employer_id.unique()}
    ids = list(labels)
    groups = {"PDUK": ids[:12], "UNDER_REPORTING_WAGE": ids[12:24], "REMITTANCE_GAP": ids[24:36], "COLD_START": ids[36:42], "CLEAN_MUTASI_SAH": ids[42:48]}
    for label, selected in groups.items():
        for employer in selected:
            labels[employer] = label
    for employer in ids[:12]:
        mask = data.employer_id.eq(employer) & data.periode.ge("2025-07")
        first = data.loc[data.employer_id.eq(employer) & data.periode.eq("2025-07"), "jumlah_peserta_aktif"].iloc[0]
        data.loc[mask, "jumlah_peserta_aktif"] = (first * .58).round().astype(int)
        data.loc[mask, "jumlah_keluar"] = 0
    for employer in ids[12:24]:
        peer = data[data.sektor_usaha.eq(data.loc[data.employer_id.eq(employer), "sektor_usaha"].iloc[0]) & data.wilayah.eq(data.loc[data.employer_id.eq(employer), "wilayah"].iloc[0])]
        data.loc[data.employer_id.eq(employer), "rata2_DPI"] = peer.groupby("employer_id").rata2_DPI.median().median() * .65
    for employer in ids[24:36]:
        data.loc[data.employer_id.eq(employer) & data.periode.ge("2025-06"), "actual_remittance"] *= .76
    for employer in ids[36:42]:
        data.drop(data.index[data.employer_id.eq(employer) & data.periode.lt("2025-11")], inplace=True)
    for employer in ids[42:48]:
        mask = data.employer_id.eq(employer) & data.periode.ge("2025-07")
        first = data.loc[data.employer_id.eq(employer) & data.periode.eq("2025-07"), "jumlah_peserta_aktif"].iloc[0]
        data.loc[mask, "jumlah_peserta_aktif"] = (first * .58).round().astype(int)
        data.loc[mask, "jumlah_keluar"] = data.loc[mask, "jumlah_peserta_aktif"].shift(1).fillna(first) - data.loc[mask, "jumlah_peserta_aktif"]
    truth = pd.DataFrame({"employer_id": list(labels), "anomaly_type": list(labels.values())})
    return data.reset_index(drop=True), truth


@st.cache_data(show_spinner=False)
def load_data():
    required = ["employer_master.csv", "headcount_timeseries.csv", "payroll_timeseries.csv", "remittance_timeseries.csv", "resign_records.csv"]
    if not all((DATA_DIR / name).exists() for name in required):
        return make_demo_data(), True
    master = pd.read_csv(DATA_DIR / "employer_master.csv")
    headcount = pd.read_csv(DATA_DIR / "headcount_timeseries.csv")
    payroll = pd.read_csv(DATA_DIR / "payroll_timeseries.csv")
    remittance = pd.read_csv(DATA_DIR / "remittance_timeseries.csv")
    resign = pd.read_csv(DATA_DIR / "resign_records.csv")
    data = headcount.merge(master, on="employer_id").merge(payroll, on=["employer_id", "periode"]).merge(remittance, on=["employer_id", "periode"]).merge(resign, on=["employer_id", "periode"])
    truth_path = DATA_DIR / "ground_truth.csv"
    truth = pd.read_csv(truth_path)[["employer_id", "anomaly_type"]] if truth_path.exists() else pd.DataFrame({"employer_id": data.employer_id.unique(), "anomaly_type": "UNKNOWN"})
    return (data, truth), False


def score_data(data, truth):
    data = data.sort_values(["employer_id", "periode"]).copy()
    data["prev_hc"] = data.groupby("employer_id").jumlah_peserta_aktif.shift(1)
    data["drop_pct"] = (data.prev_hc - data.jumlah_peserta_aktif) / data.prev_hc
    data["gap_pct"] = 1 - data.actual_remittance / data.expected_contribution
    cohort_median = data.groupby(["sektor_usaha", "wilayah", "skala"]).rata2_DPI.transform("median")
    data["wage_vs_peer"] = data.rata2_DPI / cohort_median
    a = data.groupby("employer_id").agg(max_drop=("drop_pct", "max"), resign=("jumlah_keluar", "sum"), periods=("periode", "nunique")).reset_index()
    b = data.groupby("employer_id").agg(min_peer_ratio=("wage_vs_peer", "min"), median_wage=("rata2_DPI", "median")).reset_index()
    c = data.groupby("employer_id").agg(max_gap=("gap_pct", "max"), avg_gap=("gap_pct", "mean")).reset_index()
    meta = data[["employer_id", "sektor_usaha", "wilayah", "skala"]].drop_duplicates("employer_id")
    scores = meta.merge(a, on="employer_id").merge(b, on="employer_id").merge(c, on="employer_id").merge(truth, on="employer_id", how="left")
    scores["module_a"] = (scores.max_drop >= .25) & (scores.resign < scores.max_drop * 100)
    scores["module_b"] = (scores.min_peer_ratio <= .78) & (scores.periods >= 3)
    scores["module_c"] = scores.max_gap >= .12
    scores["risk_score"] = (scores.module_a.astype(int) * 40 + scores.module_b.astype(int) * 35 + scores.module_c.astype(int) * 25).astype(int)
    scores["status"] = np.select([scores.risk_score >= 70, scores.risk_score >= 35], ["PRIORITAS TINGGI", "PERLU DITINJAU"], default="NORMAL")
    return data.merge(scores[["employer_id", "risk_score", "status"]], on="employer_id"), scores


@st.cache_data(show_spinner=False)
def load_wave2_scores():
    candidates = [
        *sorted((ROOT / "output_wave2").glob("output_scores*.json"), key=lambda item: item.stat().st_mtime, reverse=True),
        *sorted(DATA_DIR.glob("output_scores*.json"), key=lambda item: item.stat().st_mtime, reverse=True),
    ]
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        return None
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    companies = pd.DataFrame(payload.get("companies", []))
    if companies.empty:
        return None
    companies = companies.rename(columns={"id": "employer_id"})
    for module in ["A", "B", "C"]:
        companies[f"score_{module}"] = companies["scores"].map(lambda value: value.get(module) if isinstance(value, dict) else np.nan)
        companies[f"status_{module}"] = companies["status"].map(lambda value: value.get(module) if isinstance(value, dict) else "NO_DATA")
        companies[f"module_{module.lower()}"] = companies[f"status_{module}"].eq("FLAGGED")
    companies["risk_score"] = companies["composite_score"].fillna(0).mul(100).round().astype(int)
    companies["status"] = companies["band"]
    return companies, payload.get("meta", {}), path


def inject_css():
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: #14211f; }
    .stApp { background: #f6f4ec; } [data-testid="stSidebar"] { background: #173c35; }
    [data-testid="stSidebar"] * { color: #eef8f1 !important; } h1 { font-size: 2.4rem !important; }
    .eyebrow { font: 700 .72rem 'Space Mono', monospace; letter-spacing: .08em; color: #f27d52; text-transform: uppercase; }
    .subtitle { color: #60736e; margin-bottom: 1.4rem; }
    .metric-card { background: #fffdf8; border: 1px solid #e5e4d9; border-radius: 8px; padding: 1rem 1.1rem; min-height: 112px; }
    .metric-label { color: #60736e; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; }
    .metric-value { font: 700 1.7rem 'Space Mono', monospace; margin-top: .4rem; } .metric-note { color: #60736e; font-size: .76rem; margin-top: .3rem; }
    .callout { background: #173c35; color: #eef8f1; border-radius: 8px; padding: 1.2rem 1.3rem; margin: .4rem 0 1rem; }
    .callout strong { color: #a8e6cf; }
    </style>""", unsafe_allow_html=True)


def metric(label, value, note):
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)


def main():
    inject_css()
    (data, truth), demo = load_data()
    data, scores = score_data(data, truth)
    wave2 = load_wave2_scores()
    wave2_active = wave2 is not None
    if wave2_active:
        wave2_scores, wave2_meta, wave2_path = wave2
        wave2_columns = ["risk_score", "status", "band", "composite_score", "coverage",
                         "max_module_score", "score_A", "score_B", "score_C", "status_A", "status_B", "status_C",
                         "module_a", "module_b", "module_c"]
        scores = scores.drop(columns=wave2_columns, errors="ignore").merge(
            wave2_scores[["employer_id", "risk_score", "status", "band", "composite_score", "coverage",
                          "max_module_score", "score_A", "score_B", "score_C", "status_A", "status_B", "status_C",
                          "module_a", "module_b", "module_c"]], on="employer_id", how="left")
        data = data.drop(columns=["risk_score", "status"], errors="ignore").merge(
            scores[["employer_id", "risk_score", "status"]], on="employer_id", how="left")
    st.sidebar.markdown("<div class='eyebrow'>ECRS / WAVE 1</div><h2>Risk Console</h2>", unsafe_allow_html=True)
    st.sidebar.caption("Employer Contribution Risk Score")
    if demo:
        st.sidebar.info("Mode demo aktif. Letakkan enam CSV Wave 0 di data/dummy untuk memakai data engine.")
    if wave2_active:
        st.sidebar.success(f"Wave 2 aktif: {wave2_path.parent.name}/{wave2_path.name}")
    sectors = st.sidebar.multiselect("Sektor", sorted(data.sektor_usaha.unique()), default=sorted(data.sektor_usaha.unique()))
    regions = st.sidebar.multiselect("Wilayah", sorted(data.wilayah.unique()), default=sorted(data.wilayah.unique()))
    status_options = ["Tinggi", "Sedang", "Rendah", "Belum bisa dinilai"] if wave2_active else ["PRIORITAS TINGGI", "PERLU DITINJAU", "NORMAL"]
    statuses = st.sidebar.multiselect("Status risiko", status_options, default=status_options[:2])
    filtered_scores = scores[scores.sektor_usaha.isin(sectors) & scores.wilayah.isin(regions)]
    visible_scores = filtered_scores[filtered_scores.status.isin(statuses)]
    visible_data = data[data.employer_id.isin(filtered_scores.employer_id)]
    st.markdown(f"<div class='eyebrow'>COMMAND CENTER · {'WAVE 2 COMPOSITE' if wave2_active else 'WAVE 1 SIGNALS'}</div>", unsafe_allow_html=True)
    st.title("Employer risk, made inspectable.")
    st.markdown("<div class='subtitle'>Satu pandangan untuk menemukan pola yang perlu dicek, memahami alasannya, dan menelusuri sinyal sampai level perusahaan.</div>", unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]: metric("Employer dipantau", f"{len(filtered_scores):,}", "setelah filter aktif")
    high_status = "Tinggi" if wave2_active else "PRIORITAS TINGGI"
    with cols[1]: metric("Prioritas tinggi", f"{int((filtered_scores.status == high_status).sum()):,}", "berdasarkan composite score")
    with cols[2]: metric("Potensi gap kontribusi", rupiah(visible_data.expected_contribution.sub(visible_data.actual_remittance).clip(lower=0).sum()), "estimasi dari periode tampil")
    with cols[3]: metric("Data coverage", f"{visible_data.periode.nunique()} bln", "periode observasi terakhir")
    st.markdown("<div class='callout'><strong>Catatan pemeriksa:</strong> skor adalah prioritas investigasi, bukan vonis. Buka tabel di bawah untuk melihat sinyal penyusunnya dan alasan yang dapat ditindaklanjuti.</div>", unsafe_allow_html=True)
    tab_overview, tab_a, tab_b, tab_c = st.tabs(["Ringkasan risiko", "A · Headcount", "B · Peer wage", "C · Reconciliation"])
    with tab_overview:
        left, right = st.columns([1.05, .95])
        with left:
            st.subheader("Antrian pemeriksaan")
            table = visible_scores.sort_values(["risk_score", "max_gap"], ascending=False).copy()
            table["Sinyal"] = table.apply(lambda row: " · ".join([name for name, active in [("A", row.module_a), ("B", row.module_b), ("C", row.module_c)] if active]) or "-", axis=1)
            display_columns = ["employer_id", "status", "risk_score", "Sinyal", "anomaly_type"]
            if wave2_active:
                display_columns.insert(3, "coverage")
            st.dataframe(table[display_columns].rename(columns={"employer_id": "Employer", "status": "Band", "risk_score": "Skor", "coverage": "Coverage", "anomaly_type": "Label engine"}), width="stretch", hide_index=True)
        with right:
            st.subheader("Komposisi sinyal")
            signal_counts = pd.Series({"A / Headcount": int(visible_scores.module_a.sum()), "B / Peer wage": int(visible_scores.module_b.sum()), "C / Remittance": int(visible_scores.module_c.sum())})
            st.bar_chart(signal_counts, color="#f27d52", height=260)
            st.caption("Jumlah employer dengan setidaknya satu sinyal melewati threshold.")
    with tab_a:
        st.subheader("Registration volatility")
        st.caption("Penurunan headcount yang tajam dan tidak dijelaskan catatan resign diprioritaskan untuk dicek.")
        choices = visible_scores.sort_values("risk_score", ascending=False).employer_id.tolist()
        if choices:
            chart_id = st.selectbox("Pilih employer", choices, key="a")
            view = visible_data[visible_data.employer_id.eq(chart_id)].set_index("periode")
            st.line_chart(view[["jumlah_peserta_aktif", "jumlah_keluar"]], color=["#173c35", "#f27d52"], height=300)
            st.dataframe(visible_scores[visible_scores.employer_id.eq(chart_id)][["employer_id", "max_drop", "resign", "periods", "module_a"]], width="stretch", hide_index=True)
    with tab_b:
        st.subheader("Peer-group wage benchmarking")
        st.caption("DPI yang konsisten jauh di bawah median cohort sektor, wilayah, dan skala yang sama menjadi sinyal under-reporting.")
        st.line_chart(visible_data.groupby("periode", as_index=True)["rata2_DPI"].median(), color="#e6a23c", height=280)
        st.dataframe(visible_scores.sort_values("min_peer_ratio")[["employer_id", "median_wage", "min_peer_ratio", "module_b"]].head(15), width="stretch", hide_index=True)
    with tab_c:
        st.subheader("Contribution reconciliation")
        st.caption("Actual remittance dibandingkan dengan expected contribution = DPI × headcount × 4%.")
        monthly = visible_data.groupby("periode")[["expected_contribution", "actual_remittance"]].sum()
        st.line_chart(monthly, color=["#173c35", "#f27d52"], height=280)
        st.dataframe(visible_scores.sort_values("max_gap", ascending=False)[["employer_id", "max_gap", "avg_gap", "module_c"]].head(15), width="stretch", hide_index=True)


if __name__ == "__main__":
    main()