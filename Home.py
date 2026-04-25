import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from utils import CSS, MONTHS_GR, DAYS_GR, fmt_euro, load_history, period_stats, delta_html

st.set_page_config(
    page_title="AB Skyros — Business Hub",
    layout="wide",
    page_icon=None,
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1.2rem 0 1rem;">
      <div style="font-size:.62rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#60a5fa;margin-bottom:.3rem;">AB SKYROS 1082</div>
      <div style="font-size:1rem;font-weight:700;color:#f1f5f9;margin-bottom:1.5rem;">Business Hub</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#4b5563;margin-bottom:.4rem;padding-left:.9rem;">NAVIGATION</div>', unsafe_allow_html=True)
    st.page_link("Home.py",                     label="Home")
    st.page_link("pages/1_Sales.py",             label="Sales Analytics")
    st.page_link("pages/2_Invoices.py",          label="Invoices")
    st.markdown(f'<div style="position:absolute;bottom:1.5rem;left:0;right:0;padding:0 1rem;font-size:.65rem;color:#374151;">{datetime.now().strftime("%d/%m/%Y · %H:%M")}</div>', unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
today = date.today()
st.markdown(f"""
<div class="page-header">
  <div class="page-header-left">
    <div class="eyebrow">AB Skyros — Κατάστημα 1082</div>
    <h1>Business Hub</h1>
  </div>
  <div class="page-header-right">
    <div class="ts-label">Σήμερα</div>
    <div class="ts-val">{DAYS_GR[today.weekday()]}, {today.day} {MONTHS_GR[today.month-1]} {today.year}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Module cards ─────────────────────────────────────────────────────────────
st.markdown('<div class="sec-hdr">Ενότητες</div>', unsafe_allow_html=True)
st.markdown("""
<div class="nav-grid">
  <div class="nav-card" style="--stripe:#2563eb;">
    <div class="nc-module">Sales Analytics</div>
    <div class="nc-title">Πωλήσεις Καταστήματος</div>
    <div class="nc-desc">Ημερήσιος τζίρος, αριθμός πελατών, ανάλυση τμημάτων, συγκρίσεις περιόδων. Αυτόματη ανάκτηση μέσω email.</div>
    <div class="nc-tags"><span class="nc-tag">Daily Sales</span><span class="nc-tag">OCR</span><span class="nc-tag">Departments</span></div>
  </div>
  <div class="nav-card" style="--stripe:#0891b2;">
    <div class="nc-module" style="color:#0891b2;">Invoices</div>
    <div class="nc-title">Έλεγχος Τιμολογίων</div>
    <div class="nc-desc">Παρακολούθηση τιμολογίων και πιστωτικών. Εβδομαδιαία και μηνιαία εικόνα με εξαγωγή δεδομένων.</div>
    <div class="nc-tags"><span class="nc-tag" style="background:#ecfeff;color:#0e7490;">Weekly</span><span class="nc-tag" style="background:#ecfeff;color:#0e7490;">Monthly</span><span class="nc-tag" style="background:#ecfeff;color:#0e7490;">Export</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

ca, cb = st.columns(2)
with ca:
    if st.button("Μετάβαση στο Sales Analytics", use_container_width=True):
        st.switch_page("pages/1_Sales.py")
with cb:
    if st.button("Μετάβαση στα Τιμολόγια", use_container_width=True, type="secondary"):
        st.switch_page("pages/2_Invoices.py")

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Sales KPI snapshot ───────────────────────────────────────────────────────
st.markdown('<div class="sec-hdr">Sales Analytics — Σύνοψη</div>', unsafe_allow_html=True)
df_s = load_history()

if not df_s.empty:
    last   = df_s.iloc[0]
    prev   = df_s.iloc[1] if len(df_s) > 1 else None
    ld     = last["date"]
    days_old = (today - ld).days

    if days_old == 0:
        st.markdown('<div class="banner banner-ok">Ενημερωμένο — τελευταία αναφορά σήμερα</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="banner banner-warn">Τελευταία αναφορά: {ld.strftime("%d/%m/%Y")} — {days_old} {"ημέρα" if days_old==1 else "ημέρες"} πίσω</div>', unsafe_allow_html=True)

    cur_month_total = period_stats(df_s, date(today.year, today.month, 1), today)["total"]

    def kpi_s(lbl, val, prev_val, acc, euro=True):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return f'<div class="kpi" style="--a:{acc}"><div class="kpi-lbl">{lbl}</div><div class="kpi-val-sm">—</div></div>'
        disp = fmt_euro(val) if euro else f"{int(val):,}".replace(",",".")
        dlt  = delta_html(val, prev_val, euro) if prev_val is not None else ""
        return (f'<div class="kpi" style="--a:{acc}">'
                f'<div class="kpi-lbl">{lbl}</div>'
                f'<div class="kpi-val-sm">{disp}</div>{dlt}</div>')

    st.markdown(f"""<div class="kpi-row kpi-row-4">
      {kpi_s(f"Πωλήσεις {ld.strftime('%d/%m')}", last["netday"],    prev["netday"]    if prev is not None else None, "#2563eb")}
      {kpi_s("Πελάτες",                           last["customers"], prev["customers"] if prev is not None else None, "#7c3aed", euro=False)}
      {kpi_s("Μ.Ο. Καλαθιού",                    last["avg_basket"],prev["avg_basket"] if prev is not None else None, "#0891b2")}
      {kpi_s(f"Μηνιαίο ({MONTHS_GR[today.month-1][:3]})", cur_month_total, None, "#059669")}
    </div>""", unsafe_allow_html=True)

    # Mini chart 14 ημερών
    ch = df_s[df_s["date"] >= (today - timedelta(days=13))].sort_values("date").copy()
    if not ch.empty:
        ch["Ημέρα"] = ch["date"].apply(lambda d: d.strftime("%d/%m"))
        st.bar_chart(ch.set_index("Ημέρα")["netday"], color="#2563eb",
                     use_container_width=True, height=130)
else:
    st.markdown('<div class="banner banner-info">Δεν υπάρχουν δεδομένα πωλήσεων. Μεταβείτε στο Sales Analytics για συγχρονισμό.</div>', unsafe_allow_html=True)

st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

# ── Invoice KPI snapshot ──────────────────────────────────────────────────────
st.markdown('<div class="sec-hdr">Τιμολόγια — Σύνοψη</div>', unsafe_allow_html=True)
inv_df = st.session_state.get("invoice_data", pd.DataFrame())

if not inv_df.empty:
    ws  = today - timedelta(days=today.weekday())
    m   = today.month; y = today.year

    w_mask = (inv_df["DATE"].dt.date >= ws) & (inv_df["DATE"].dt.date <= today)
    m_mask = (inv_df["DATE"].dt.month == m) & (inv_df["DATE"].dt.year == y)

    w_inv = inv_df[w_mask & ~inv_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
    w_crd = inv_df[w_mask &  inv_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
    m_inv = inv_df[m_mask & ~inv_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
    m_crd = inv_df[m_mask &  inv_df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()

    st.markdown(f"""<div class="kpi-row kpi-row-4">
      <div class="kpi" style="--a:#0891b2"><div class="kpi-lbl">Τιμολόγια Εβδ.</div><div class="kpi-val-sm">{fmt_euro(w_inv)}</div></div>
      <div class="kpi" style="--a:#dc2626"><div class="kpi-lbl">Πιστωτικά Εβδ.</div><div class="kpi-val-sm">{fmt_euro(w_crd)}</div></div>
      <div class="kpi" style="--a:#0891b2"><div class="kpi-lbl">Τιμολόγια Μήνα</div><div class="kpi-val-sm">{fmt_euro(m_inv)}</div></div>
      <div class="kpi" style="--a:#059669"><div class="kpi-lbl">Καθαρό Μήνα</div><div class="kpi-val-sm">{fmt_euro(m_inv - m_crd)}</div></div>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown('<div class="banner banner-info">Τα τιμολόγια δεν έχουν φορτωθεί. Μεταβείτε στην ενότητα Τιμολόγια.</div>', unsafe_allow_html=True)
