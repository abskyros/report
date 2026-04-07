import streamlit as st
import pandas as pd
import io
import os
import re
import pdfplumber
from imap_tools import MailBox, AND
from datetime import datetime, timedelta, date

# ─────────────────────────────────────────────────────────────────────────────
# ΡΥΘΜΙΣΕΙΣ
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_USER    = "ftoulisgm@gmail.com"
EMAIL_PASS    = st.secrets["EMAIL_PASSWORD"]
EMAIL_SUBJECT = "ΑΒ ΣΚΥΡΟΣ"

HISTORY_FILE  = "sales_history.csv"
HOURLY_FILE   = "hourly_history.csv"

DAYS_GR   = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
              "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]

st.set_page_config(
    page_title="ΑΒ ΣΚΥΡΟΣ – Dashboard",
    layout="centered",
    page_icon="🛒",
    initial_sidebar_state="collapsed",
)

# ── CSS: Mobile-first ────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="metric-container"] {
    background: #f8f9fa; border-radius: 12px;
    padding: 12px 16px !important; border: 1px solid #e9ecef;
  }
  [data-testid="stMetricValue"]  { font-size: 1.45rem !important; font-weight: 700; }
  [data-testid="stMetricLabel"]  { font-size: 0.78rem !important; color: #6c757d; }
  [data-testid="stMetricDelta"]  { font-size: 0.80rem !important; }
  .stTabs [data-baseweb="tab-list"] { gap: 4px; }
  .stTabs [data-baseweb="tab"]  { font-size: 0.82rem; padding: 7px 11px; border-radius: 8px; }
  div[data-testid="stButton"] > button { border-radius: 10px; height: 2.8em; }
  [data-testid="stDataFrame"] { font-size: 0.83rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ΙΣΤΟΡΙΚΟ
# ─────────────────────────────────────────────────────────────────────────────

def load_history() -> pd.DataFrame:
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    return pd.DataFrame(columns=['date','netday','customers','avg_basket'])

def save_history(df: pd.DataFrame):
    df.to_csv(HISTORY_FILE, index=False)

def upsert_daily(record: dict):
    df = load_history()
    mask = df['date'] == record['date']
    if mask.any():
        for k, v in record.items():
            if v is not None:
                df.loc[mask, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df = df.sort_values('date').reset_index(drop=True)
    save_history(df)

def load_hourly() -> pd.DataFrame:
    if os.path.exists(HOURLY_FILE):
        df = pd.read_csv(HOURLY_FILE)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    return pd.DataFrame(columns=['date','hour','sales','customers'])

def save_hourly(df: pd.DataFrame):
    df.to_csv(HOURLY_FILE, index=False)

def upsert_hourly(record_date: date, hourly_rows: list):
    df = load_hourly()
    if not df.empty:
        df = df[df['date'] != record_date]
    if hourly_rows:
        new_rows = pd.DataFrame([{**r, 'date': record_date} for r in hourly_rows])
        df = pd.concat([df, new_rows], ignore_index=True)
        df = df.sort_values(['date','hour']).reset_index(drop=True)
    save_hourly(df)

def get_val(df: pd.DataFrame, target: date, col: str):
    if df.empty: return None
    mask = df['date'] == target
    if not mask.any(): return None
    v = df.loc[mask, col].values[0]
    return float(v) if pd.notna(v) else None

def fmt_euro(v):
    if v is None: return "—"
    return f"{v:,.2f} €"

def fmt_delta(current, ref_val):
    if ref_val is None or ref_val == 0: return None, None
    diff = current - ref_val
    pct  = (diff / ref_val) * 100
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:,.2f} €", f"{sign}{pct:.1f}%"

# ─────────────────────────────────────────────────────────────────────────────
# PDF PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse_number(s: str) -> float:
    s = s.strip().replace('€','').replace(' ','').replace('\xa0','')
    if "," in s and "." in s:
        if s.rfind(',') > s.rfind('.'): s = s.replace('.','').replace(',','.')
        else: s = s.replace(',','')
    elif "," in s:
        s = s.replace(',','.')
    try: return float(s)
    except: return 0.0

def extract_pdf_data(pdf_bytes: bytes) -> dict:
    result = {'date': None, 'netday': None, 'customers': None, 'avg_basket': None, 'hourly': []}
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        m = re.search(r'For\s+(\d{2}/\d{2}/\d{4})', full_text)
        if m: result['date'] = datetime.strptime(m.group(1), "%d/%m/%Y").date()

        m = re.search(r'NetDaySalDis\s+([\d,\.]+)', full_text)
        if m: result['netday'] = parse_number(m.group(1))

        m = re.search(r'NumOfCus\s+([\d,\.]+)', full_text)
        if m: result['customers'] = int(parse_number(m.group(1)))

        m = re.search(r'AvgSalCus\s+([\d,\.]+)', full_text)
        if m: result['avg_basket'] = parse_number(m.group(1))

        for h_str, s_str, c_str in re.findall(
            r'(\d{2}):\d{2}\s*-\s*\d{2}:\d{2}\s+([\d,\.]+)\s*€\s+[\d\.]+\s+(\d+)',
            full_text
        ):
            s = parse_number(s_str)
            if s > 0:
                result['hourly'].append({'hour': int(h_str), 'sales': s, 'customers': int(c_str)})

    except Exception as e:
        st.warning(f"PDF parsing: {e}")
    return result

# ─────────────────────────────────────────────────────────────────────────────
# EMAIL
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_reports(n_emails: int) -> list:
    results = []
    try:
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
            # ΠΡΟΣΟΧΗ: Προσθήκη charset='utf8' για να υποστηρίζονται τα ελληνικά στο Subject
            messages = list(mailbox.fetch(AND(subject=EMAIL_SUBJECT), limit=n_emails, reverse=True, charset='utf8'))
            for msg in messages:
                for att in msg.attachments:
                    if att.filename.lower().endswith('.pdf'):
                        data = extract_pdf_data(att.payload)
                        if data['date'] is None: data['date'] = msg.date.date()
                        if data['netday'] is not None:
                            results.append(data)
                            break
    except Exception as e:
        st.error(f"Email σφάλμα: {e}")
    return results

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_week_range(d):
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)

def week_table(history: pd.DataFrame, w_start: date) -> pd.DataFrame:
    rows = []
    for i in range(7):
        day = w_start + timedelta(days=i)
        net  = get_val(history, day, 'netday')
        cust = get_val(history, day, 'customers')
        avg  = get_val(history, day, 'avg_basket')
        rows.append({
            'Ημέρα':         DAYS_GR[i],
            'Ημ/νία':        day.strftime('%d/%m'),
            'Πωλήσεις':      fmt_euro(net),
            'Πελάτες':       int(cust) if cust else "—",
            'Μ.Ό. Καλαθιού': fmt_euro(avg),
            '_val':          net or 0.0,
        })
    return pd.DataFrame(rows)

def comparison_table(current_val, history, sel_date):
    rows = []
    for label, comp_date in [
        ("Χθες",             sel_date - timedelta(days=1)),
        ("Πριν 7 μέρες",     sel_date - timedelta(days=7)),
        ("Πριν 30 μέρες",    sel_date - timedelta(days=30)),
        ("Πέρσι ίδια μέρα",  date(sel_date.year-1, sel_date.month, sel_date.day)),
    ]:
        ref = get_val(history, comp_date, 'netday')
        d_eur, d_pct = fmt_delta(current_val, ref)
        rows.append({"Σύγκριση με": label, "Πωλήσεις": fmt_euro(ref),
                     "Διαφορά €": d_eur or "—", "Μεταβολή %": d_pct or "—"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# ══ UI ══
# ─────────────────────────────────────────────────────────────────────────────

st.title("🛒 ΑΒ ΣΚΥΡΟΣ – Sales Dashboard")

with st.expander("⚙️ Ενημέρωση Δεδομένων", expanded=False):
    c1, c2 = st.columns([3,1])
    with c1:
        n_fetch = st.selectbox("Αριθμός emails:", [7,14,30,60,90,180], index=1)
    with c2:
        st.write(""); st.write("")
        fetch_btn = st.button("📥 Λήψη", use_container_width=True)

    if fetch_btn:
        fetch_reports.clear()
        with st.spinner(f"Σάρωση emails '{EMAIL_SUBJECT}'..."):
            fetched = fetch_reports(n_fetch)
        if fetched:
            for d in fetched:
                upsert_daily({'date': d['date'], 'netday': d['netday'],
                              'customers': d['customers'], 'avg_basket': d['avg_basket']})
                if d['hourly']: upsert_hourly(d['date'], d['hourly'])
            st.success(f"✅ {len(fetched)} ημέρες αποθηκεύτηκαν!")
            st.rerun()
        else:
            st.warning("Δεν βρέθηκαν emails με PDF δεδομένα.")

    with st.expander("✏️ Χειροκίνητη Καταχώρηση"):
        m1, m2, m3 = st.columns(3)
        with m1: m_date = st.date_input("Ημερομηνία", datetime.now(), key="md")
        with m2: m_net  = st.number_input("Πωλήσεις €", 0.0, step=0.01, key="mn")
        with m3: m_cust = st.number_input("Πελάτες", 0, step=1, key="mc")
        m_avg = st.number_input("Μ.Ό. Καλαθιού €", 0.0, step=0.01, key="ma")
        if st.button("💾 Αποθήκευση", key="msave"):
            upsert_daily({'date': m_date, 'netday': m_net,
                          'customers': m_cust, 'avg_basket': m_avg})
            st.success("Αποθηκεύτηκε!"); st.rerun()

# Φόρτωση
history = load_history()
hourly  = load_hourly()

if history.empty:
    st.info("📭 Δεν υπάρχουν δεδομένα. Κάνε Λήψη από Email παραπάνω.")
    st.stop()

history['date'] = pd.to_datetime(history['date']).dt.date
last_date = max(history['date'])
st.caption(f"📅 Τελευταία ενημέρωση: **{last_date.strftime('%d/%m/%Y')}** | "
           f"Ημέρες στο ιστορικό: **{len(history)}**")

# ── TABS ─────────────────────────────────────────────────────────────────────
tab_day, tab_week, tab_month, tab_year, tab_hourly = st.tabs([
    "📍 Ημέρα", "📅 Εβδομάδα", "📆 Μήνας", "📊 Έτος", "🕐 Ανά Ώρα"
])

# ── TAB 1: ΗΜΕΡΑ ─────────────────────────────────────────────────────────────
with tab_day:
    sel_date = st.selectbox(
        "Επίλεξε ημέρα:",
        sorted(history['date'].unique(), reverse=True),
        format_func=lambda d: f"{DAYS_GR[d.weekday()]}  {d.strftime('%d/%m/%Y')}"
    )
    r     = history[history['date'] == sel_date].iloc[0]
    net   = float(r['netday'])    if pd.notna(r['netday'])    else 0.0
    cust  = int(r['customers'])   if pd.notna(r['customers']) else 0
    avg_b = float(r['avg_basket'])if pd.notna(r['avg_basket'])else 0.0

    _, pct_yst = fmt_delta(net, get_val(history, sel_date - timedelta(days=1), 'netday'))
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Πωλήσεις",       fmt_euro(net),              delta=pct_yst)
    c2.metric("👥 Πελάτες",        cust or "—")
    c3.metric("🛒 Μ.Ό. Καλαθιού", fmt_euro(avg_b) if avg_b else "—")

    st.divider()
    st.markdown("#### 🔄 Συγκρίσεις")
    comparison_table(net, history, sel_date)

# ── TAB 2: ΕΒΔΟΜΑΔΑ ──────────────────────────────────────────────────────────
with tab_week:
    sel_week = st.date_input("Επίλεξε εβδομάδα:", datetime.now(), key="wk")
    w_start, w_end = get_week_range(sel_week)
    st.info(f"📅 {w_start.strftime('%d/%m/%Y')} (Δευ)  →  {w_end.strftime('%d/%m/%Y')} (Κυρ)")

    wdf     = week_table(history, w_start)
    total_w = wdf['_val'].sum()
    days_w  = (wdf['_val'] > 0).sum()
    avg_w   = total_w / days_w if days_w else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Σύνολο Εβδομάδας",   fmt_euro(total_w))
    c2.metric("Μέσος Όρος/Ημέρα",   fmt_euro(avg_w))
    c3.metric("Ημέρες με δεδομένα", f"{days_w}/7")

    # Σύγκριση ίδιας εβδομάδας πέρσι
    py_w   = week_table(history, w_start - timedelta(weeks=52))
    t_py_w = py_w['_val'].sum()
    if t_py_w > 0:
        d_eur, d_pct = fmt_delta(total_w, t_py_w)
        st.caption(f"📊 Ίδια εβδομάδα πέρσι: **{fmt_euro(t_py_w)}** |  Διαφορά: **{d_eur}** ({d_pct})")

    st.dataframe(
        wdf[['Ημέρα','Ημ/νία','Πωλήσεις','Πελάτες','Μ.Ό. Καλαθιού']],
        use_container_width=True, hide_index=True
    )
    chart_w = wdf[wdf['_val'] > 0]
    if not chart_w.empty:
        st.bar_chart(chart_w.set_index('Ημέρα')['_val'].rename("Πωλήσεις €"), color="#1f77b4")

# ── TAB 3: ΜΗΝΑΣ ─────────────────────────────────────────────────────────────
with tab_month:
    years_avail = sorted(history['date'].apply(lambda d: d.year).unique(), reverse=True)
    cm, cy = st.columns(2)
    with cm: sel_month = st.selectbox("Μήνας", range(1,13),
                                       format_func=lambda x: MONTHS_GR[x-1],
                                       index=datetime.now().month-1)
    with cy: sel_year  = st.selectbox("Έτος", years_avail)

    m_df = history[history['date'].apply(lambda d: d.month==sel_month and d.year==sel_year)].copy()

    if m_df.empty:
        st.warning("Δεν υπάρχουν δεδομένα για αυτόν τον μήνα.")
    else:
        total_m = m_df['netday'].sum()
        days_m  = len(m_df)
        best    = m_df.loc[m_df['netday'].idxmax()]
        worst   = m_df.loc[m_df['netday'].idxmin()]

        c1, c2 = st.columns(2)
        c1.metric("Σύνολο Μήνα",      fmt_euro(total_m))
        c2.metric("Μέσος Όρος/Ημέρα", fmt_euro(total_m / days_m))
        c3, c4 = st.columns(2)
        c3.metric("🏆 Καλύτερη", f"{best['date'].strftime('%d/%m')} – {fmt_euro(float(best['netday']))}")
        c4.metric("📉 Χειρότερη", f"{worst['date'].strftime('%d/%m')} – {fmt_euro(float(worst['netday']))}")

        py_m = history[history['date'].apply(lambda d: d.month==sel_month and d.year==sel_year-1)]
        if not py_m.empty:
            d_eur, d_pct = fmt_delta(total_m, py_m['netday'].sum())
            st.caption(f"📊 {MONTHS_GR[sel_month-1]} {sel_year-1}: **{fmt_euro(py_m['netday'].sum())}** |  "
                       f"Διαφορά: **{d_eur}** ({d_pct})")

        st.divider()
        ch_m = m_df.copy()
        ch_m['Ημ/νία'] = ch_m['date'].apply(lambda d: d.strftime('%d/%m'))
        st.bar_chart(ch_m.set_index('Ημ/νία')['netday'].rename("Πωλήσεις €"), color="#1f77b4")

        show_m = m_df.copy()
        show_m['Ημέρα']      = show_m['date'].apply(lambda d: DAYS_GR[d.weekday()])
        show_m['Ημερομηνία'] = show_m['date'].apply(lambda d: d.strftime('%d/%m/%Y'))
        show_m['Πωλήσεις']   = show_m['netday'].map(lambda x: f"{x:,.2f} €")
        show_m['Πελάτες']    = show_m['customers'].apply(lambda x: int(x) if pd.notna(x) else "—")
        show_m['Μ.Ό.Καλ.']  = show_m['avg_basket'].apply(lambda x: f"{float(x):,.2f} €" if pd.notna(x) else "—")
        st.dataframe(show_m[['Ημέρα','Ημερομηνία','Πωλήσεις','Πελάτες','Μ.Ό.Καλ.']],
                     use_container_width=True, hide_index=True)
        st.download_button("📥 Εξαγωγή CSV",
                           m_df.to_csv(index=False).encode('utf-8-sig'),
                           f"sales_{sel_month:02d}_{sel_year}.csv", "text/csv")

# ── TAB 4: ΕΤΟΣ ──────────────────────────────────────────────────────────────
with tab_year:
    years_avail2 = sorted(history['date'].apply(lambda d: d.year).unique(), reverse=True)
    sel_year_y   = st.selectbox("Επίλεξε Έτος:", years_avail2, key="yr")

    y_df = history[history['date'].apply(lambda d: d.year == sel_year_y)].copy()

    if y_df.empty:
        st.warning("Δεν υπάρχουν δεδομένα για αυτό το έτος.")
    else:
        total_y = y_df['netday'].sum()
        days_y  = len(y_df)
        best_y  = y_df.loc[y_df['netday'].idxmax()]

        c1, c2, c3 = st.columns(3)
        c1.metric("Σύνολο Έτους",      fmt_euro(total_y))
        c2.metric("Μέσος Όρος/Ημέρα",  fmt_euro(total_y / days_y))
        c3.metric("Ημέρες καταγραφής", str(days_y))
        st.metric("🏆 Καλύτερη ημέρα",
                  f"{best_y['date'].strftime('%d/%m/%Y')} – "
                  f"{DAYS_GR[best_y['date'].weekday()]} – "
                  f"{fmt_euro(float(best_y['netday']))}")

        py_y = history[history['date'].apply(lambda d: d.year == sel_year_y - 1)]
        if not py_y.empty:
            d_eur, d_pct = fmt_delta(total_y, py_y['netday'].sum())
            st.caption(f"📊 {sel_year_y-1}: **{fmt_euro(py_y['netday'].sum())}** |  "
                       f"Διαφορά: **{d_eur}** ({d_pct})")

        st.divider()
        st.markdown("#### Μηνιαίες Πωλήσεις")
        y_df2 = y_df.copy()
        y_df2['month_num'] = y_df2['date'].apply(lambda d: d.month)
        monthly = (y_df2.groupby('month_num')['netday']
                        .agg(Συνολο='sum', Ημερες='count').reset_index())
        monthly['Μήνας']    = monthly['month_num'].apply(lambda x: MONTHS_GR[x-1][:3])
        monthly['Μ.Ό. €']   = monthly['Συνολο'] / monthly['Ημερες']

        st.bar_chart(monthly.set_index('Μήνας')['Συνολο'].rename("Πωλήσεις €"), color="#1f77b4")

        monthly['Σύνολο €'] = monthly['Συνολο'].map(lambda x: f"{x:,.2f} €")
        monthly['Μ.Ό./Ημ.€']= monthly['Μ.Ό. €'].map(lambda x: f"{x:,.2f} €")
        st.dataframe(monthly[['Μήνας','Ημερες','Σύνολο €','Μ.Ό./Ημ.€']]
                     .rename(columns={'Ημερες':'Ημέρες'}),
                     use_container_width=True, hide_index=True)

# ── TAB 5: ΑΝΑ ΩΡΑ ───────────────────────────────────────────────────────────
with tab_hourly:
    if hourly.empty:
        st.info("Δεν υπάρχουν ωριαία δεδομένα. Κάνε Λήψη από Email.")
    else:
        hourly['date'] = pd.to_datetime(hourly['date']).dt.date
        h_dates = sorted(hourly['date'].unique(), reverse=True)
        sel_h = st.selectbox(
            "Επίλεξε ημέρα:",
            h_dates,
            format_func=lambda d: f"{DAYS_GR[d.weekday()]}  {d.strftime('%d/%m/%Y')}",
            key="h_sel"
        )
        h_df = hourly[hourly['date'] == sel_h].copy()

        if h_df.empty:
            st.warning("Δεν υπάρχουν ωριαία δεδομένα για αυτή την ημέρα.")
        else:
            total_h = h_df['sales'].sum()
            best_h  = h_df.loc[h_df['sales'].idxmax()]
            peak_c  = h_df.loc[h_df['customers'].idxmax()]

            c1, c2, c3 = st.columns(3)
            c1.metric("Σύνολο",        fmt_euro(total_h))
            c2.metric("🏆 Κορυφή €",   f"{int(best_h['hour']):02d}:00 – {fmt_euro(float(best_h['sales']))}")
            c3.metric("👥 Ώρα αιχμής", f"{int(peak_c['hour']):02d}:00 – {int(peak_c['customers'])} πελ.")

            h_df['Ώρα'] = h_df['hour'].apply(lambda x: f"{x:02d}:00")
            st.bar_chart(h_df.set_index('Ώρα')['sales'].rename("Πωλήσεις €"), color="#1f77b4")

            h_show = h_df.copy()
            h_show['Πωλήσεις'] = h_show['sales'].map(lambda x: f"{x:,.2f} €")
            h_show['% Ημέρας'] = h_show['sales'].apply(
                lambda x: f"{(x/total_h*100):.1f}%" if total_h else "—")
            st.dataframe(
                h_show[['Ώρα','Πωλήσεις','customers','% Ημέρας']]
                      .rename(columns={'customers':'Πελάτες'}),
                use_container_width=True, hide_index=True
            )

            # Σύγκριση με χθες
            prev_d  = sel_h - timedelta(days=1)
            prev_hd = hourly[hourly['date'] == prev_d]
            if not prev_hd.empty:
                st.divider()
                st.markdown(f"**🔄 Σύγκριση με {prev_d.strftime('%d/%m/%Y')}**")
                merged = (h_df[['hour','sales']]
                          .merge(prev_hd[['hour','sales']].rename(columns={'sales':'prev'}),
                                 on='hour', how='outer')
                          .fillna(0).sort_values('hour'))
                merged['Ώρα']    = merged['hour'].apply(lambda x: f"{x:02d}:00")
                merged['Σήμερα'] = merged['sales'].map(lambda x: f"{x:,.2f} €")
                merged['Χθες']   = merged['prev'].map(lambda x: f"{x:,.2f} €")
                merged['Δ%']     = merged.apply(
                    lambda row: f"{((row['sales']-row['prev'])/row['prev']*100):+.1f}%"
                    if row['prev'] > 0 else "—", axis=1)
                st.dataframe(merged[['Ώρα','Σήμερα','Χθες','Δ%']],
                             use_container_width=True, hide_index=True)
