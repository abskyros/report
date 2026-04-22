import streamlit as st
import pandas as pd
import io
import os
import re
import pdfplumber
from imap_tools import MailBox, AND
from datetime import datetime, timedelta, date
import unicodedata
import traceback

# ─────────────────────────────────────────────────────────────────────────────
# ΡΥΘΜΙΣΕΙΣ
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_USER    = "ftoulisgm@gmail.com"
EMAIL_PASS    = st.secrets["bkrvmuqxysymqwbf"]
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

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="metric-container"] {
    background: #f8f9fa; border-radius: 12px;
    padding: 12px 16px !important; border: 1px solid #e9ecef;
  }
  [data-testid="stMetricValue"]  { font-size: 1.45rem !important; font-weight: 700; }
  [data-testid="stMetricLabel"]  { font-size: 0.78rem !important; color: #6c757d; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ
# ─────────────────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    """Αφαιρεί τόνους και κάνει uppercase για ασφαλές matching."""
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.upper()

def fmt_euro(v):
    if v is None: return "—"
    return f"{v:,.2f} €"

# ─────────────────────────────────────────────────────────────────────────────
# ΙΣΤΟΡΙΚΟ (CSV)
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

# ─────────────────────────────────────────────────────────────────────────────
# PDF PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse_number(s: str) -> float:
    s = s.strip().replace('€','').replace(' ','').replace('\xa0','')
    if "." in s and "," in s:
        s = s.replace('.', '').replace(',', '.')
    elif "," in s:
        s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def extract_pdf_data(pdf_bytes: bytes) -> dict:
    result = {'date': None, 'netday': None, 'customers': None, 'avg_basket': None, 'hourly': []}
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        lines = [l.strip() for l in full_text.split('\n') if l.strip()]

        # --- Ημερομηνία ---
        for line in lines:
            m = re.search(r'(\d{2}/\d{2}/\d{4})', line)
            if m:
                try:
                    result['date'] = datetime.strptime(m.group(1), "%d/%m/%Y").date()
                    break
                except Exception:
                    pass

        # --- Summary ---
        summary_labels = ['NetDaySalDis', 'NonMercDep', 'TotSal', 'NumOfCus',
                          'AvgSalCus', 'NumItmSold', 'AvgItmPerCus', 'AvgItmPric']
        found_labels = []
        for i, line in enumerate(lines):
            for k in summary_labels:
                if line == k or line.startswith(k + ' '):
                    found_labels.append((k, i))
                    break

        if found_labels:
            last_label_line = max(li for _, li in found_labels)
            num_re = re.compile(r'^-?\d{1,3}(?:\.\d{3})*(?:,\d+)?$|^-?\d+$')
            value_lines = []
            for i in range(last_label_line + 1, len(lines)):
                if num_re.match(lines[i]):
                    value_lines.append(lines[i])
                    if len(value_lines) >= len(found_labels):
                        break

            mapping = dict(zip([k for k, _ in found_labels], value_lines))
            if 'NetDaySalDis' in mapping:
                result['netday'] = parse_number(mapping['NetDaySalDis'])
            if 'NumOfCus' in mapping:
                try: result['customers'] = int(parse_number(mapping['NumOfCus']))
                except Exception: pass
            if 'AvgSalCus' in mapping:
                result['avg_basket'] = parse_number(mapping['AvgSalCus'])

        # --- Ωριαία ---
        time_re = re.compile(r'^(\d{2}):\d{2}\s*-\s*\d{2}:\d{2}$')
        time_hours, last_time_idx = [], -1
        for i, line in enumerate(lines):
            m = time_re.match(line)
            if m:
                time_hours.append(int(m.group(1)))
                last_time_idx = i

        if time_hours and last_time_idx >= 0:
            sales_re = re.compile(r'^([\d\.,]+)\s*€$')
            sales_values = []
            for i in range(last_time_idx + 1, len(lines)):
                m = sales_re.match(lines[i])
                if m:
                    sales_values.append(parse_number(m.group(1)))
                    if len(sales_values) >= len(time_hours):
                        break
            for h, s in zip(time_hours, sales_values):
                if s > 0:
                    result['hourly'].append({'hour': h, 'sales': s, 'customers': 0})

    except Exception as e:
        st.warning(f"⚠️ PDF parsing error: {e}")
    return result

# ─────────────────────────────────────────────────────────────────────────────
# EMAIL FETCH
# ─────────────────────────────────────────────────────────────────────────────

def _pick_folder(mailbox: MailBox) -> str:
    """
    Επιλέγει τον καλύτερο φάκελο για αναζήτηση.
    Προτεραιότητα: All Mail > INBOX
    """
    try:
        folders = [f.name for f in mailbox.folder.list()]
    except Exception:
        return 'INBOX'

    # Κοίταξε για φάκελο τύπου "All Mail" (αγγλικά ή ελληνικά)
    for f in folders:
        norm = _norm(f)
        if 'ALL' in norm and ('MAIL' in norm or 'ΜΗΝΥΜ' in norm or 'GMAIL' in norm):
            return f
    # Fallback στο INBOX
    return 'INBOX'


@st.cache_data(ttl=300, show_spinner=False)
def fetch_reports(limit: int) -> tuple[list, list]:
    """
    Επιστρέφει (results, log_messages).
    Χρησιμοποιεί client-side φιλτράρισμα θέματος (ασφαλές για ελληνικά).
    """
    results = []
    logs    = []
    target  = _norm(EMAIL_SUBJECT)

    try:
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:

            # 1. Επέλεξε φάκελο
            folder = _pick_folder(mailbox)
            try:
                mailbox.folder.set(folder)
                logs.append(f"📂 Φάκελος: **{folder}**")
            except Exception as e:
                logs.append(f"⚠️ Αδύνατο να ανοιχτεί '{folder}': {e} → δοκιμή INBOX")
                mailbox.folder.set('INBOX')
                folder = 'INBOX'

            # 2. Φόρτωσε emails (νεότερα πρώτα, με όριο)
            checked = matched = pdfs_ok = 0
            for msg in mailbox.fetch(reverse=True, mark_seen=False, limit=limit):
                checked += 1

                # Client-side φιλτράρισμα θέματος (χειρίζεται σωστά τα ελληνικά)
                if target not in _norm(msg.subject):
                    continue
                matched += 1

                for att in msg.attachments:
                    if not att.filename.lower().endswith('.pdf'):
                        continue

                    data = extract_pdf_data(att.payload)

                    # Fallback ημερομηνία από το email
                    if data['date'] is None:
                        data['date'] = msg.date.date()

                    if data['netday'] is not None:
                        results.append(data)
                        pdfs_ok += 1
                    else:
                        logs.append(
                            f"⚠️ Δεν βρέθηκαν πωλήσεις στο PDF **{att.filename}** "
                            f"({msg.date.strftime('%d/%m/%Y')})"
                        )
                    break  # ένα PDF ανά email

            logs.append(
                f"🔎 Ελέγχθηκαν **{checked}** emails · "
                f"ταίριαξαν **{matched}** · "
                f"επιτυχή PDFs **{pdfs_ok}**"
            )

    except Exception as e:
        logs.append(f"❌ **Σφάλμα σύνδεσης IMAP:** {e}")
        logs.append("```\n" + traceback.format_exc() + "\n```")

    return results, logs

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("🛒 ΑΒ ΣΚΥΡΟΣ – Dashboard")

# ── Ενημέρωση ────────────────────────────────────────────────────────────────
with st.expander("⚙️ Ενημέρωση Δεδομένων", expanded=False):
    c1, c2 = st.columns([3, 1])
    with c1:
        n_check = st.number_input("Έλεγχος τελευταίων emails:", 10, 1000, 200, step=10)
    with c2:
        st.write(""); st.write("")
        fetch_btn = st.button("📥 Λήψη", use_container_width=True)

    if fetch_btn:
        fetch_reports.clear()
        with st.spinner("Σύνδεση στο Gmail και αναζήτηση..."):
            fetched, logs = fetch_reports(n_check)

        # Εμφάνισε logs
        for msg in logs:
            st.markdown(msg)

        if fetched:
            for d in fetched:
                upsert_daily({
                    'date': d['date'],
                    'netday': d['netday'],
                    'customers': d['customers'],
                    'avg_basket': d['avg_basket'],
                })
                if d['hourly']:
                    upsert_hourly(d['date'], d['hourly'])
            st.success(f"✅ Αποθηκεύτηκαν δεδομένα για {len(fetched)} ημέρες!")
            st.rerun()
        else:
            st.info("Δεν βρέθηκαν νέα reports.")

    # ── Ανεβάστε PDF χειροκίνητα ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Ή ανεβάστε PDF χειροκίνητα:**")
    uploaded = st.file_uploader("Επιλέξτε αρχείο PDF", type="pdf", label_visibility="collapsed")
    if uploaded:
        data = extract_pdf_data(uploaded.read())
        if data['netday'] is not None:
            if data['date'] is None:
                data['date'] = date.today()
            upsert_daily({
                'date': data['date'],
                'netday': data['netday'],
                'customers': data['customers'],
                'avg_basket': data['avg_basket'],
            })
            if data['hourly']:
                upsert_hourly(data['date'], data['hourly'])
            st.success(
                f"✅ Εισήχθη: {data['date'].strftime('%d/%m/%Y')} · "
                f"Πωλήσεις: {fmt_euro(data['netday'])} · "
                f"Πελάτες: {data['customers']}"
            )
            st.rerun()
        else:
            st.error("Δεν ήταν δυνατή η ανάγνωση δεδομένων από αυτό το PDF.")
            with st.expander("🔍 Raw PDF text (debug)"):
                with pdfplumber.open(io.BytesIO(uploaded.getvalue())) as pdf:
                    raw = "\n".join(p.extract_text() or "" for p in pdf.pages)
                st.text(raw[:3000])

# ── Δεδομένα ─────────────────────────────────────────────────────────────────
history = load_history()
if history.empty:
    st.warning("Δεν υπάρχουν δεδομένα. Πατήστε 'Λήψη' ή ανεβάστε ένα PDF.")
    st.stop()

# Τελευταία ημέρα
last = history.iloc[-1]
day_name = DAYS_GR[last['date'].weekday()]
month_name = MONTHS_GR[last['date'].month - 1]
st.subheader(
    f"📅 {day_name}, {last['date'].day} {month_name} {last['date'].year}"
)

c1, c2, c3 = st.columns(3)
c1.metric("Πωλήσεις",        fmt_euro(last['netday']))
c2.metric("Πελάτες",         f"{int(last['customers'])}")
c3.metric("Μ.Ό. Καλαθιού",  fmt_euro(last['avg_basket']))

# Σύγκριση με χθες
if len(history) >= 2:
    prev = history.iloc[-2]
    diff = last['netday'] - prev['netday']
    pct  = diff / prev['netday'] * 100 if prev['netday'] else 0
    sign = "▲" if diff >= 0 else "▼"
    color = "green" if diff >= 0 else "red"
    st.markdown(
        f"<span style='color:{color}'>{sign} {fmt_euro(abs(diff))} ({pct:+.1f}%) vs χθες</span>",
        unsafe_allow_html=True,
    )

st.divider()

# Γράφημα 30 ημερών
st.subheader("📊 Τελευταίες 30 ημέρες")
chart_data = history.tail(30).copy()
chart_data['date_str'] = chart_data['date'].apply(lambda d: d.strftime('%d/%m'))
st.bar_chart(chart_data.set_index('date_str')['netday'])

# Ωριαίο γράφημα (αν υπάρχει)
hourly = load_hourly()
if not hourly.empty:
    last_date = history.iloc[-1]['date']
    today_h = hourly[hourly['date'] == last_date]
    if not today_h.empty:
        st.subheader("🕐 Ωριαίες Πωλήσεις (σήμερα)")
        st.bar_chart(today_h.set_index('hour')['sales'])

st.divider()
st.subheader("📋 Ιστορικό")
display_df = history.sort_values('date', ascending=False).copy()
display_df['date'] = display_df['date'].apply(lambda d: d.strftime('%d/%m/%Y'))
display_df.columns = ['Ημερομηνία', 'Πωλήσεις (€)', 'Πελάτες', 'Μ.Ό. Καλαθιού (€)']
st.dataframe(display_df, use_container_width=True, hide_index=True)
