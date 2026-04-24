import streamlit as st
import pandas as pd
import json
from datetime import date, datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    COMMON_CSS, MONTHS_GR, DAYS_GR,
    fmt_euro, load_history, period_stats, delta_html
)

st.set_page_config(
    page_title="ΑΒ ΣΚΥΡΟΣ · Κεντρικό",
    layout="wide",
    page_icon="🏪",
    initial_sidebar_state="expanded",
)

st.markdown(COMMON_CSS, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 1.5rem;">
      <div style="font-size:.65rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#10b981;margin-bottom:.3rem;">ΑΒ ΣΚΥΡΟΣ 1082</div>
      <div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;">Business Hub</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#334155;margin-bottom:.5rem;">ΠΛΟΗΓΗΣΗ</div>', unsafe_allow_html=True)
    st.page_link("Home.py",                         label="🏠  Αρχική Σελίδα",    )
    st.page_link("pages/1_📊_Πωλήσεις.py",          label="📊  Sales Analytics",  )
    st.page_link("pages/2_📋_Τιμολόγια.py",          label="📋  Τιμολόγια",        )

    st.markdown("---")
    st.markdown(f'<div style="font-size:.7rem;color:#334155;">Σήμερα: {datetime.now().strftime("%d/%m/%Y")}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:2rem;">
  <div>
    <div style="font-size:.7rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#10b981;margin-bottom:.3rem;">
      ΑΒ ΣΚΥΡΟΣ · ΚΑΤΑΣΤΗΜΑ 1082
    </div>
    <h1 style="font-size:2.2rem;font-weight:700;color:#f1f5f9;margin:0;letter-spacing:-.02em;">
      Business Hub
    </h1>
    <div style="font-size:.85rem;color:#475569;margin-top:.4rem;">
      Κεντρικός πίνακας ελέγχου · {DAYS_GR[datetime.now().weekday()]}, {datetime.now().strftime('%d')} {MONTHS_GR[datetime.now().month-1]} {datetime.now().year}
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:.7rem;color:#475569;">Τελευταία ανανέωση</div>
    <div style="font-family:'DM Mono';font-size:.78rem;color:#64748b;">{datetime.now().strftime('%H:%M')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# NAVIGATION CARDS
# ══════════════════════════════════════════════════════════
st.markdown('<div class="sec-header"><span>▍</span> Εφαρμογές</div>', unsafe_allow_html=True)

nc1, nc2 = st.columns(2)
with nc1:
    st.markdown("""
    <a href="/📊_Πωλήσεις" target="_self" style="text-decoration:none;">
      <div class="nav-card">
        <div class="icon">📊</div>
        <div class="title">Sales Analytics</div>
        <div class="desc">Ημερήσιες πωλήσεις, τάσεις, ανάλυση τμημάτων και συγκρίσεις περιόδων. Αυτόματη λήψη από email με PDF reports.</div>
        <div class="badge">Sales · OCR · Email</div>
      </div>
    </a>
    """, unsafe_allow_html=True)

with nc2:
    st.markdown("""
    <a href="/📋_Τιμολόγια" target="_self" style="text-decoration:none;">
      <div class="nav-card" style="--accent:#3b82f6;">
        <div class="icon">📋</div>
        <div class="title">Έλεγχος Τιμολογίων</div>
        <div class="desc">Παρακολούθηση τιμολογίων και πιστωτικών εγγράφων. Εβδομαδιαία και μηνιαία εικόνα με εξαγωγή δεδομένων.</div>
        <div class="badge" style="background:#3b82f6;">Invoices · Weekly · Monthly</div>
      </div>
    </a>
    """, unsafe_allow_html=True)

st.markdown('<hr class="divider-module"/>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# QUICK KPIs – ΠΩΛΗΣΕΙΣ
# ══════════════════════════════════════════════════════════
st.markdown('<div class="sec-header"><span>▍</span> Sales Analytics · Σύνοψη</div>', unsafe_allow_html=True)

df_sales = load_history()
today    = date.today()

if not df_sales.empty:
    latest = df_sales.iloc[0]
    prev   = df_sales.iloc[1] if len(df_sales) > 1 else None
    ld     = latest['date']
    days_old = (today - ld).days

    # Status banner
    if days_old == 0:
        st.markdown('<div class="ok-banner">✓ Sales · Ενημερωμένο σήμερα</div>', unsafe_allow_html=True)
    elif days_old <= 2:
        st.markdown(f'<div class="stale-banner">⚠ Sales · Τελευταία αναφορά {days_old} {"ημέρα" if days_old==1 else "ημέρες"} πίσω</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="stale-banner">⚠ Sales · Τελευταία αναφορά: {ld.strftime("%d/%m/%Y")} ({days_old} ημέρες πίσω)</div>', unsafe_allow_html=True)

    def kpi(label, value, prev_val, accent, is_euro=True):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return f'<div class="kpi-card" style="--accent:{accent}"><div class="kpi-label">{label}</div><div class="kpi-value-sm">—</div></div>'
        disp = fmt_euro(value) if is_euro else f"{int(value):,}".replace(",",".")
        dlt  = delta_html(value, prev_val, is_euro) if prev_val is not None else ""
        return (f'<div class="kpi-card" style="--accent:{accent}">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-value-sm">{disp}</div>{dlt}</div>')

    st.markdown(f"""<div class="kpi-grid">
      {kpi(f"Πωλήσεις {ld.strftime('%d/%m')}",    latest['netday'],    prev['netday']    if prev is not None else None, "#10b981")}
      {kpi("Πελάτες",                              latest['customers'], prev['customers'] if prev is not None else None, "#3b82f6", False)}
      {kpi("Μ.Ό. Καλαθιού",                       latest['avg_basket'],prev['avg_basket'] if prev is not None else None, "#8b5cf6")}
      {kpi(f"Μήνας {MONTHS_GR[today.month-1][:3]}.",
           period_stats(df_sales, date(today.year,today.month,1), today)['total'], None, "#f59e0b")}
    </div>""", unsafe_allow_html=True)

    # Mini chart τελευταίων 14 ημερών
    ch = df_sales[df_sales['date'] >= (today - timedelta(days=14))].sort_values('date').copy()
    if not ch.empty:
        ch['label'] = ch['date'].apply(lambda d: d.strftime('%d/%m'))
        st.bar_chart(ch.set_index('label')['netday'], color="#10b981",
                     use_container_width=True, height=140)

    col_link = st.columns([1, 3])[0]
    with col_link:
        if st.button("→  Πλήρες Sales Dashboard", use_container_width=True):
            st.switch_page("pages/1_📊_Πωλήσεις.py")
else:
    st.markdown("""
    <div style="background:#111827;border:1px solid #1e2d45;border-radius:12px;padding:2rem;text-align:center;color:#334155;">
      <div style="font-size:2rem;margin-bottom:.5rem;">📭</div>
      <div>Δεν υπάρχουν δεδομένα πωλήσεων</div>
    </div>""", unsafe_allow_html=True)
    col_link = st.columns([1, 3])[0]
    with col_link:
        if st.button("→  Μετάβαση στο Sales Dashboard", use_container_width=True):
            st.switch_page("pages/1_📊_Πωλήσεις.py")

st.markdown('<hr class="divider-module"/>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# QUICK KPIs – ΤΙΜΟΛΟΓΙΑ (από session_state αν φορτώθηκαν)
# ══════════════════════════════════════════════════════════
st.markdown('<div class="sec-header"><span>▍</span> Τιμολόγια · Σύνοψη</div>', unsafe_allow_html=True)

inv_df = st.session_state.get('invoice_data', pd.DataFrame())

if not inv_df.empty:
    # Εβδομάδα
    from datetime import timedelta as td
    ws  = today - timedelta(days=today.weekday())
    we  = ws + timedelta(days=6)
    ms  = date(today.year, today.month, 1)

    w_mask = (inv_df['DATE'].dt.date >= ws) & (inv_df['DATE'].dt.date <= today)
    m_mask = (inv_df['DATE'].dt.month == today.month) & (inv_df['DATE'].dt.year == today.year)

    w_inv = inv_df[w_mask & ~inv_df['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()
    w_crd = inv_df[w_mask &  inv_df['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()
    m_inv = inv_df[m_mask & ~inv_df['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()
    m_crd = inv_df[m_mask &  inv_df['TYPE'].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]['VALUE'].sum()

    st.markdown(f"""<div class="kpi-grid">
      <div class="kpi-card" style="--accent:#3b82f6"><div class="kpi-label">Τιμολόγια Εβδ.</div><div class="kpi-value-sm">{fmt_euro(w_inv)}</div></div>
      <div class="kpi-card" style="--accent:#f43f5e"><div class="kpi-label">Πιστωτικά Εβδ.</div><div class="kpi-value-sm">{fmt_euro(w_crd)}</div></div>
      <div class="kpi-card" style="--accent:#3b82f6"><div class="kpi-label">Τιμολόγια Μήνα</div><div class="kpi-value-sm">{fmt_euro(m_inv)}</div></div>
      <div class="kpi-card" style="--accent:#10b981"><div class="kpi-label">Καθαρό Μήνα</div><div class="kpi-value-sm">{fmt_euro(m_inv - m_crd)}</div></div>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:#111827;border:1px solid #1e2d45;border-radius:12px;padding:2rem;text-align:center;color:#334155;">
      <div style="font-size:2rem;margin-bottom:.5rem;">📭</div>
      <div>Τα τιμολόγια δεν έχουν φορτωθεί ακόμα</div>
    </div>""", unsafe_allow_html=True)

col_link2 = st.columns([1, 3])[0]
with col_link2:
    if st.button("→  Μετάβαση στα Τιμολόγια", use_container_width=True, type="secondary"):
        st.switch_page("pages/2_📋_Τιμολόγια.py")
