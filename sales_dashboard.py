import streamlit as st
import pandas as pd
import io
import os
import re
import json
import pdfplumber
from imap_tools import MailBox, AND, A
from datetime import datetime, timedelta, date

# ─────────────────────────────────────────────────────────────────────────────
# ΡΥΘΜΙΣΕΙΣ
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_USER    = "abf.skyros@gmail.com"
EMAIL_PASS    = st.secrets["uqrgpbhxuchdidmh"]
EMAIL_SUBJECT = "ΑΒ ΣΚΥΡΟΣ"

HISTORY_FILE  = "sales_history.csv"   # ημερήσιο ιστορικό
HOURLY_FILE   = "hourly_history.csv"  # ωριαίο ιστορικό

DAYS_GR = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
              "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]

st.set_page_config(
    page_title="ΑΒ ΣΚΥΡΟΣ – Dashboard",
    layout="centered",          # καλύτερο για κινητό
    page_icon="🛒",
    initial_sidebar_state="collapsed",
)

# ── Mobile-friendly CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
  /* μεγαλύτερα metrics για κινητό */
  [data-testid="metric-container"] { padding: 10px 14px !important; }
  [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
  [data-testid="stMetricLabel"] { font-size: 0.85rem !important; }
  /* tabs */
  .stTabs [data-baseweb="tab"] { font-size: 0.82rem; padding: 6px 10px; }
  /* dataframe */
  [data-testid="stDataFrame"] { font-size: 0.82rem; }
  /* buttons full width on mobile */
  .stButton > button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ΙΣΤΟΡΙΚΟ – ΒΟΗΘΗΤΙΚΕΣ
# ─────────────────────────────────────────────────────────────────────────────

def load_history() -> pd.DataFrame:
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE, parse_dates=['date'])
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    return pd.DataFrame(columns=['date','netday','grossal','customers','items','avg_basket'])

def save_history(df: pd.DataFrame):
    df.to_csv(HISTORY_FILE, index=False)

def upsert_daily(record: dict):
    df = load_history()
    df['date'] = pd.to_datetime(df['date']).dt.date
    mask = df['date'] == record['date']
    if mask.any():
        for k, v in record.items():
            df.loc[mask, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df = df.sort_values('date').reset_index(drop=True)
    save_history(df)

def load_hourly() -> pd.DataFrame:
    if os.path.exists(HOURLY_FILE):
        df = pd.read_csv(HOURLY_FILE, parse_dates=['date'])
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    return pd.DataFrame(columns=['date','hour','sales','customers','items'])

def save_hourly(df: pd.DataFrame):
    df.to_csv(HOURLY_FILE, index=False)

def upsert_hourly(record_date: date, hourly_rows: list[dict]):
    df = load_hourly()
    df['date'] = pd.to_datetime(df['date']).dt.date
    df = df[df['date'] != record_date]          # αφαιρεί παλιές εγγραφές ίδιας μέρας
    new_rows = pd.DataFrame([{**r, 'date': record_date} for r in hourly_rows])
    df = pd.concat([df, new_rows], ignore_index=True)
    df = df.sort_values(['date','hour']).reset_index(drop=True)
    save_hourly(df)

def get_history_value(df: pd.DataFrame, target_date: date, col: str):
    mask = df['date'] == target_date
    if mask.any():
        return float(df.loc[mask, col].values[0])
    return None

# ─────────────────────────────────────────────────────────────────────────────
# PDF EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def parse_number(s: str) -> float:
    """Μετατρέπει '7,633.56' ή '7.633,56' σε float."""
    s = s.strip().replace('€','').replace(' ','')
    # Ανιχνεύει ευρωπαϊκή μορφή (τελευταίο διαχωριστικό = κόμμα)
    if re.match(r'^\d{1,3}(\.\d{3})*(,\d+)?$', s):
        s = s.replace('.','').replace(',','.')
    else:
        s = s.replace(',','')
    try:
        return float(s)
    except:
        return 0.0

def extract_pdf_data(pdf_bytes: bytes) -> dict:
    """
    Εξάγει όλα τα χρήσιμα δεδομένα από το Department Report PDF.
    Επιστρέφει dict με daily summary + hourly list.
    """
    result = {
        'date': None,
        'netday': None,
        'grossal': None,
        'customers': None,
        'items': None,
        'avg_basket': None,
        'hourly': [],
    }
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_text = [p.extract_text() or "" for p in pdf.pages]
            full_text  = "\n".join(pages_text)

        # ── Ημερομηνία ────────────────────────────────────────────────────
        m = re.search(r'For\s+(\d{2}/\d{2}/\d{4})', full_text)
        if m:
            result['date'] = datetime.strptime(m.group(1), "%d/%m/%Y").date()

        # ── NetDaySalDis ──────────────────────────────────────────────────
        m = re.search(r'NetDaySalDis\s+([\d,\.]+)', full_text)
        if m:
            result['netday'] = parse_number(m.group(1))

        # ── GrossSal (πρώτη εμφάνιση μετά το NetDaySalDis) ───────────────
        m = re.search(r'GrossSal\s+([\d,\.]+)', full_text)
        if m:
            result['grossal'] = parse_number(m.group(1))

        # ── NumOfCus → πελάτες ────────────────────────────────────────────
        m = re.search(r'NumOfCus\s+([\d,\.]+)', full_text)
        if m:
            result['customers'] = int(parse_number(m.group(1)))

        # ── NetSal total → items proxy / AvgSalCus ────────────────────────
        m = re.search(r'AvgSalCus\s+([\d,\.]+)', full_text)
        if m:
            result['avg_basket'] = parse_number(m.group(1))

        # ── Hourly Productivity ───────────────────────────────────────────
        # Ψάχνουμε γραμμές: "HH:00 - HH:59  SALES  %  Cust  ..."
        hourly_pattern = re.findall(
            r'(\d{2}:\d{2})\s*-\s*\d{2}:\d{2}\s+([\d,\.]+)\s*€\s+([\d\.]+)\s+(\d+)',
            full_text
        )
        for match in hourly_pattern:
            hour_str, sales_str, pct_str, cust_str = match
            hour = int(hour_str.split(':')[0])
            sales = parse_number(sales_str)
            if sales > 0:
                result['hourly'].append({
                    'hour': hour,
                    'sales': sales,
                    'customers': int(cust_str),
                })

        # ── Items (από hourly) ─────────────────────────────────────────────
        items_matches = re.findall(r'(\d+)\s*$', full_text, re.MULTILINE)
        # Fallback: αθροίζουμε items απο hourly section αν υπάρχει
        items_pattern = re.findall(
            r'(\d{2}:\d{2})\s*-\s*\d{2}:\d{2}.*?(\d+)\s*$',
            full_text, re.MULTILINE
        )

    except Exception as e:
        st.warning(f"PDF parsing error: {e}")

    return result

# ─────────────────────────────────────────────────────────────────────────────
# EMAIL FETCH
# ─────────────────────────────────────────────────────────────────────────────

def fetch_latest_report(n_emails: int = 30) -> list[dict]:
    """
    Φέρνει τα n τελευταία emails με subject που περιέχει EMAIL_SUBJECT,
    εξάγει δεδομένα από PDF και επιστρέφει list of dicts.
    """
    results = []
    try:
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
            messages = list(mailbox.fetch(
                AND(subject=EMAIL_SUBJECT),
                limit=n_emails,
                reverse=True
            ))
            for msg in messages:
                for att in msg.attachments:
                    if att.filename.lower().endswith('.pdf'):
                        data = extract_pdf_data(att.payload)
                        if data['date'] is None:
                            data['date'] = msg.date.date()
                        if data['netday'] is not None:
                            results.append(data)
                            break
    except Exception as e:
        st.error(f"Σφάλμα email: {e}")
    return results

# ─────────────────────────────────────────────────────────────────────────────
# ΕΒΔΟΜΑΔΙΑΙΟΣ ΠΙΝΑΚΑΣ
# ─────────────────────────────────────────────────────────────────────────────

def get_week_range(d):
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)

def build_week_table(history_df: pd.DataFrame, week_start: date) -> pd.DataFrame:
    rows = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        netday = get_history_value(history_df, day, 'netday')
        cust   = get_history_value(history_df, day, 'customers')
        avg    = get_history_value(history_df, day, 'avg_basket')
        rows.append({
            'Ημέρα':       DAYS_GR[i],
            'Ημ/νία':      day.strftime('%d/%m'),
            'Πωλήσεις':    f"{netday:,.2f} €" if netday else "—",
            'Πελάτες':     int(cust) if cust else "—",
            'Μ.Ό. Καλαθιού': f"{avg:,.2f} €" if avg else "—",
            '_val':        netday or 0,
        })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("🛒 ΑΒ ΣΚΥΡΟΣ – Sales Dashboard")

# ── Refresh bar ─────────────────────────────────────────────────────────────
with st.expander("⚙️ Ενημέρωση Δεδομένων", expanded=False):
    col_a, col_b = st.columns(2)
    with col_a:
        n_fetch = st.selectbox("Πόσα emails;", [7, 14, 30, 60, 90], index=1)
    with col_b:
        st.write("")
        st.write("")
        fetch_btn = st.button("📥 Λήψη από Email", use_container_width=True)

    if fetch_btn:
        with st.spinner(f"Λήψη τελευταίων {n_fetch} emails..."):
            fetched = fetch_latest_report(n_emails=n_fetch)
        if fetched:
            for d in fetched:
                upsert_daily({
                    'date':       d['date'],
                    'netday':     d['netday'],
                    'grossal':    d['grossal'],
                    'customers':  d['customers'],
                    'avg_basket': d['avg_basket'],
                })
                if d['hourly']:
                    upsert_hourly(d['date'], d['hourly'])
            st.success(f"✅ Αποθηκεύτηκαν {len(fetched)} ημέρες.")
            st.rerun()
        else:
            st.warning("Δεν βρέθηκαν νέα δεδομένα.")

    # Χειροκίνητη καταχώρηση
    with st.expander("✏️ Χειροκίνητη Καταχώρηση"):
        mc1, mc2 = st.columns(2)
        with mc1:
            m_date = st.date_input("Ημερομηνία", datetime.now(), key="m_date")
            m_net  = st.number_input("NetDaySalDis €", 0.0, step=0.01, key="m_net")
        with mc2:
            m_cust = st.number_input("Πελάτες", 0, step=1, key="m_cust")
            m_avg  = st.number_input("Μ.Ό. Καλαθιού €", 0.0, step=0.01, key="m_avg")
        if st.button("💾 Αποθήκευση", key="manual_save"):
            upsert_daily({'date': m_date, 'netday': m_net, 'grossal': None,
                          'customers': m_cust, 'avg_basket': m_avg})
            st.success("Αποθηκεύτηκε!")
            st.rerun()

history = load_history()
hourly  = load_hourly()

if history.empty:
    st.info("📭 Δεν υπάρχουν δεδομένα. Πάτα 'Λήψη από Email' παραπάνω.")
    st.stop()

history['date'] = pd.to_datetime(history['date']).dt.date

# ─── TABS ────────────────────────────────────────────────────────────────────
tab_day, tab_week, tab_month, tab_year, tab_hourly = st.tabs([
    "📍 Σήμερα", "📅 Εβδομάδα", "📆 Μήνας", "📊 Έτος", "🕐 Ανά Ώρα"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – ΣΗΜΕΡΑ / ΕΠΙΛΕΓΜΕΝΗ ΗΜΕΡΑ
# ══════════════════════════════════════════════════════════════════════════════
with tab_day:
    available_dates = sorted(history['date'].tolist(), reverse=True)
    sel_date = st.selectbox(
        "Επίλεξε ημέρα:",
        available_dates,
        format_func=lambda d: f"{DAYS_GR[d.weekday()]} {d.strftime('%d/%m/%Y')}"
    )

    row = history[history['date'] == sel_date]
    if row.empty:
        st.warning("Δεν υπάρχουν δεδομένα.")
    else:
        netday    = float(row['netday'].values[0])   if pd.notna(row['netday'].values[0])    else 0.0
        customers = row['customers'].values[0]
        avg_b     = row['avg_basket'].values[0]

        # Σύγκριση με χθες
        yesterday  = sel_date - timedelta(days=1)
        last_month = sel_date - timedelta(days=30)
        last_year  = date(sel_date.year - 1, sel_date.month, sel_date.day)

        def delta_pct(current, compare_date, col):
            v = get_history_value(history, compare_date, col)
            if v and v != 0:
                return ((current - v) / v) * 100
            return None

        st.markdown(f"### {DAYS_GR[sel_date.weekday()]} {sel_date.strftime('%d/%m/%Y')}")

        # Κύριες μετρικές
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Πωλήσεις", f"{netday:,.2f} €",
                  delta=f"{delta_pct(netday, yesterday, 'netday'):+.1f}% vs χθες" if delta_pct(netday, yesterday, 'netday') else None)
        c2.metric("👥 Πελάτες",
                  int(customers) if pd.notna(customers) else "—")
        c3.metric("🛒 Μ.Ό. Καλαθιού",
                  f"{float(avg_b):,.2f} €" if pd.notna(avg_b) else "—")

        # Συγκρίσεις
        st.divider()
        st.markdown("#### 🔄 Συγκρίσεις")
        comp_data = {
            "Χθες":           get_history_value(history, yesterday,  'netday'),
            "Πριν 30 μέρες":  get_history_value(history, last_month, 'netday'),
            "Πέρσι ίδια μέρα":get_history_value(history, last_year,  'netday'),
        }
        comp_rows = []
        for label, val in comp_data.items():
            if val:
                diff = netday - val
                pct  = (diff / val) * 100
                comp_rows.append({
                    "Περίοδος": label,
                    "Πωλήσεις": f"{val:,.2f} €",
                    "Διαφορά":  f"{diff:+,.2f} €",
                    "Μεταβολή": f"{pct:+.1f}%",
                })
            else:
                comp_rows.append({"Περίοδος": label, "Πωλήσεις": "—", "Διαφορά": "—", "Μεταβολή": "—"})

        st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – ΕΒΔΟΜΑΔΑ
# ══════════════════════════════════════════════════════════════════════════════
with tab_week:
    sel_week = st.date_input("Επίλεξε ημέρα της εβδομάδας:", datetime.now(), key="week_sel")
    w_start, w_end = get_week_range(sel_week)
    st.info(f"📅 {w_start.strftime('%d/%m/%Y')} (Δευ) → {w_end.strftime('%d/%m/%Y')} (Κυρ)")

    week_df = build_week_table(history, w_start)
    total_w = week_df['_val'].sum()
    days_w  = (week_df['_val'] > 0).sum()
    avg_w   = total_w / days_w if days_w else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Σύνολο Εβδομάδας", f"{total_w:,.2f} €")
    c2.metric("Μέσος Όρος/Ημέρα",  f"{avg_w:,.2f} €")
    c3.metric("Ημέρες με δεδομένα", f"{days_w}/7")

    # Σύγκριση με περσινή εβδομάδα
    prev_year_start = w_start - timedelta(weeks=52)
    prev_week_df    = build_week_table(history, prev_year_start)
    total_py        = prev_week_df['_val'].sum()
    if total_py > 0:
        diff_py = total_w - total_py
        pct_py  = (diff_py / total_py) * 100
        st.caption(f"📊 Ίδια εβδομάδα πέρσι: **{total_py:,.2f} €** → Διαφορά: **{diff_py:+,.2f} €** ({pct_py:+.1f}%)")

    st.dataframe(
        week_df[['Ημέρα','Ημ/νία','Πωλήσεις','Πελάτες','Μ.Ό. Καλαθιού']],
        use_container_width=True, hide_index=True
    )

    # Mini bar chart
    chart_data = week_df[week_df['_val'] > 0][['Ημέρα','_val']].rename(columns={'_val':'Πωλήσεις €'})
    if not chart_data.empty:
        st.bar_chart(chart_data.set_index('Ημέρα'))

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – ΜΗΝΑΣ
# ══════════════════════════════════════════════════════════════════════════════
with tab_month:
    years_avail = sorted(history['date'].apply(lambda d: d.year).unique(), reverse=True)
    col_m, col_y = st.columns(2)
    with col_m:
        sel_month = st.selectbox("Μήνας", range(1,13),
                                  format_func=lambda x: MONTHS_GR[x-1],
                                  index=datetime.now().month-1)
    with col_y:
        sel_year = st.selectbox("Έτος", years_avail)

    m_mask = history['date'].apply(lambda d: d.month == sel_month and d.year == sel_year)
    m_df   = history[m_mask].copy()

    if m_df.empty:
        st.warning("Δεν υπάρχουν δεδομένα για αυτόν τον μήνα.")
    else:
        total_m    = m_df['netday'].sum()
        days_m     = len(m_df)
        avg_m      = total_m / days_m
        best_day   = m_df.loc[m_df['netday'].idxmax()]
        worst_day  = m_df.loc[m_df['netday'].idxmin()]

        c1, c2 = st.columns(2)
        c1.metric("Σύνολο Μήνα",    f"{total_m:,.2f} €")
        c2.metric("Μέσος Όρος/Ημέρα", f"{avg_m:,.2f} €")

        c3, c4 = st.columns(2)
        c3.metric("🏆 Καλύτερη μέρα",
                  f"{best_day['date'].strftime('%d/%m')} – {float(best_day['netday']):,.2f} €")
        c4.metric("📉 Χειρότερη μέρα",
                  f"{worst_day['date'].strftime('%d/%m')} – {float(worst_day['netday']):,.2f} €")

        # Σύγκριση με ίδιο μήνα πέρσι
        prev_year_mask = history['date'].apply(
            lambda d: d.month == sel_month and d.year == sel_year - 1
        )
        prev_m_df = history[prev_year_mask]
        if not prev_m_df.empty:
            total_pm = prev_m_df['netday'].sum()
            diff_m   = total_m - total_pm
            pct_m    = (diff_m / total_pm) * 100
            st.caption(f"📊 {MONTHS_GR[sel_month-1]} {sel_year-1}: **{total_pm:,.2f} €** → Διαφορά: **{diff_m:+,.2f} €** ({pct_m:+.1f}%)")

        st.divider()

        # Γράφημα μήνα
        chart_m = m_df[['date','netday']].copy()
        chart_m['date'] = chart_m['date'].apply(lambda d: d.strftime('%d/%m'))
        st.bar_chart(chart_m.set_index('date').rename(columns={'netday':'Πωλήσεις €'}))

        # Πίνακας
        show_m = m_df.copy()
        show_m['Ημέρα']     = show_m['date'].apply(lambda d: DAYS_GR[d.weekday()])
        show_m['Ημερομηνία']= show_m['date'].apply(lambda d: d.strftime('%d/%m/%Y'))
        show_m['Πωλήσεις']  = show_m['netday'].map(lambda x: f"{x:,.2f} €")
        show_m['Πελάτες']   = show_m['customers'].apply(lambda x: int(x) if pd.notna(x) else "—")
        show_m['Μ.Ό. Καλ.'] = show_m['avg_basket'].apply(lambda x: f"{float(x):,.2f} €" if pd.notna(x) else "—")

        st.dataframe(show_m[['Ημέρα','Ημερομηνία','Πωλήσεις','Πελάτες','Μ.Ό. Καλ.']],
                     use_container_width=True, hide_index=True)

        csv_m = m_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Εξαγωγή CSV", csv_m,
                           f"sales_{sel_month}_{sel_year}.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – ΕΤΟΣ
# ══════════════════════════════════════════════════════════════════════════════
with tab_year:
    sel_year_y = st.selectbox("Έτος", years_avail, key="year_sel")

    y_mask = history['date'].apply(lambda d: d.year == sel_year_y)
    y_df   = history[y_mask].copy()

    if y_df.empty:
        st.warning("Δεν υπάρχουν δεδομένα για αυτό το έτος.")
    else:
        total_y = y_df['netday'].sum()
        days_y  = len(y_df)
        avg_y   = total_y / days_y

        c1, c2, c3 = st.columns(3)
        c1.metric("Σύνολο Έτους",     f"{total_y:,.2f} €")
        c2.metric("Ημέρες με δεδομένα", str(days_y))
        c3.metric("Μέσος Όρος/Ημέρα",  f"{avg_y:,.2f} €")

        # Ανά μήνα
        y_df['month'] = y_df['date'].apply(lambda d: d.month)
        monthly = y_df.groupby('month')['netday'].sum().reset_index()
        monthly['Μήνας'] = monthly['month'].apply(lambda x: MONTHS_GR[x-1][:3])

        st.divider()
        st.markdown("#### Μηνιαίες Πωλήσεις")
        st.bar_chart(monthly.set_index('Μήνας')['netday'].rename("Πωλήσεις €"))

        # Σύγκριση με περσινό έτος
        py_mask = history['date'].apply(lambda d: d.year == sel_year_y - 1)
        py_df   = history[py_mask]
        if not py_df.empty:
            total_py2 = py_df['netday'].sum()
            diff_y    = total_y - total_py2
            pct_y     = (diff_y / total_py2) * 100
            st.caption(f"📊 {sel_year_y-1}: **{total_py2:,.2f} €** → Διαφορά: **{diff_y:+,.2f} €** ({pct_y:+.1f}%)")

        # Μηνιαίος πίνακας
        monthly_show = monthly.copy()
        monthly_show['Πωλήσεις'] = monthly_show['netday'].map(lambda x: f"{x:,.2f} €")
        st.dataframe(monthly_show[['Μήνας','Πωλήσεις']], use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 – ΑΝΑ ΩΡΑ
# ══════════════════════════════════════════════════════════════════════════════
with tab_hourly:
    if hourly.empty:
        st.info("Δεν υπάρχουν ωριαία δεδομένα ακόμα. Κάνε Λήψη από Email.")
    else:
        hourly['date'] = pd.to_datetime(hourly['date']).dt.date
        h_dates = sorted(hourly['date'].unique(), reverse=True)

        sel_h_date = st.selectbox(
            "Επίλεξε ημέρα:",
            h_dates,
            format_func=lambda d: f"{DAYS_GR[d.weekday()]} {d.strftime('%d/%m/%Y')}",
            key="hourly_date"
        )

        h_df = hourly[hourly['date'] == sel_h_date].copy()

        if h_df.empty:
            st.warning("Δεν υπάρχουν ωριαία δεδομένα για αυτή την ημέρα.")
        else:
            best_h  = h_df.loc[h_df['sales'].idxmax()]
            total_h = h_df['sales'].sum()

            c1, c2 = st.columns(2)
            c1.metric("Συνολικές Πωλήσεις", f"{total_h:,.2f} €")
            c2.metric("🏆 Καλύτερη Ώρα",
                      f"{int(best_h['hour']):02d}:00 – {float(best_h['sales']):,.2f} €")

            # Γράφημα
            h_chart = h_df[['hour','sales']].copy()
            h_chart['Ώρα'] = h_chart['hour'].apply(lambda x: f"{x:02d}:00")
            st.bar_chart(h_chart.set_index('Ώρα')['sales'].rename("Πωλήσεις €"))

            # Πίνακας
            h_show = h_df.copy()
            h_show['Ώρα']       = h_show['hour'].apply(lambda x: f"{x:02d}:00–{x:02d}:59")
            h_show['Πωλήσεις']  = h_show['sales'].map(lambda x: f"{x:,.2f} €")
            h_show['Πελάτες']   = h_show['customers'].apply(lambda x: int(x) if pd.notna(x) else "—")
            st.dataframe(h_show[['Ώρα','Πωλήσεις','Πελάτες']],
                         use_container_width=True, hide_index=True)

            # Σύγκριση ίδιας μέρας χθες
            prev_h_date = sel_h_date - timedelta(days=1)
            prev_h_df   = hourly[hourly['date'] == prev_h_date]
            if not prev_h_df.empty:
                st.divider()
                st.markdown(f"**Σύγκριση με {prev_h_date.strftime('%d/%m/%Y')}:**")
                merged = h_df[['hour','sales']].merge(
                    prev_h_df[['hour','sales']].rename(columns={'sales':'sales_prev'}),
                    on='hour', how='outer'
                ).fillna(0).sort_values('hour')
                merged['Ώρα']     = merged['hour'].apply(lambda x: f"{x:02d}:00")
                merged['Σήμερα']  = merged['sales'].map(lambda x: f"{x:,.2f} €")
                merged['Χθες']    = merged['sales_prev'].map(lambda x: f"{x:,.2f} €")
                merged['Δ%']      = merged.apply(
                    lambda r: f"{((r['sales']-r['sales_prev'])/r['sales_prev']*100):+.1f}%"
                    if r['sales_prev'] > 0 else "—", axis=1
                )
                st.dataframe(merged[['Ώρα','Σήμερα','Χθες','Δ%']],
                             use_container_width=True, hide_index=True)

# ─── Footer ──────────────────────────────────────────────────────────────────
st.divider()
if not history.empty:
    last_date = max(history['date'])
    st.caption(f"📅 Τελευταία ενημέρωση: {last_date.strftime('%d/%m/%Y')} | "
               f"Σύνολο ημερών: {len(history)}")
