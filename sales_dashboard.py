import streamlit as st
import pandas as pd
import io
import os
import re
import pdfplumber
from imap_tools import MailBox
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

def fmt_euro(v):
    if v is None: return "—"
    return f"{v:,.2f} €"

# ─────────────────────────────────────────────────────────────────────────────
# PDF PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse_number(s: str) -> float:
    # Καθαρισμός για μορφή όπως 8.795,38
    s = s.strip().replace('€','').replace(' ','').replace('\xa0','')
    # Αν έχει και τελεία και κόμμα, η τελεία είναι χιλιάδες
    if "." in s and "," in s:
        s = s.replace('.', '').replace(',', '.')
    # Αν έχει μόνο κόμμα, είναι δεκαδικό
    elif "," in s:
        s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def extract_pdf_data(pdf_bytes: bytes) -> dict:
    result = {'date': None, 'netday': None, 'customers': None, 'avg_basket': None, 'hourly': []}
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        m_date = re.search(r'For\s+(\d{2}/\d{2}/\d{4})', full_text)
        if m_date: result['date'] = datetime.strptime(m_date.group(1), "%d/%m/%Y").date()

        m_net = re.search(r'NetDaySalDis\s+([\d\.,]+)', full_text)
        if m_net: result['netday'] = parse_number(m_net.group(1))

        m_cus = re.search(r'NumOfCus\s+([\d\.,]+)', full_text)
        if m_cus: result['customers'] = int(parse_number(m_cus.group(1)))

        m_avg = re.search(r'AvgSalCus\s+([\d\.,]+)', full_text)
        if m_avg: result['avg_basket'] = parse_number(m_avg.group(1))

        # Ωριαία δεδομένα
        pattern = r'(\d{2}):\d{2}\s*-\s*\d{2}:\d{2}\s+([\d\.,]+)\s*€?\s+[\d\.,]+\s+(\d+)'
        for h_str, s_str, c_str in re.findall(pattern, full_text):
            s_val = parse_number(s_str)
            if s_val > 0:
                result['hourly'].append({'hour': int(h_str), 'sales': s_val, 'customers': int(parse_number(c_str))})
    except Exception as e:
        st.warning(f"PDF Error: {e}")
    return result

# ─────────────────────────────────────────────────────────────────────────────
# EMAIL (Η ΛΥΣΗ ΧΩΡΙΣ SEARCH)
# ─────────────────────────────────────────────────────────────────────────────

import unicodedata

def _norm(s: str) -> str:
    # αφαιρεί τόνους και κάνει uppercase για σίγουρο matching
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.upper()

@st.cache_data(ttl=300, show_spinner=False)
def fetch_reports(limit: int) -> list:
    results = []
    target = _norm(EMAIL_SUBJECT)
    folders_to_try = ['[Gmail]/All Mail', '[Gmail]/Όλα τα μηνύματα', 'INBOX']
    debug_texts = []
    try:
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
            chosen = None
            for f in folders_to_try:
                try:
                    mailbox.folder.set(f); chosen = f; break
                except Exception:
                    continue
            st.caption(f"📂 Φάκελος: {chosen}")

            checked = matched = pdfs_found = 0
            for msg in mailbox.fetch(limit=limit, reverse=True, mark_seen=False):
                checked += 1
                if target in _norm(msg.subject):
                    matched += 1
                    for att in msg.attachments:
                        if att.filename.lower().endswith('.pdf'):
                            pdfs_found += 1
                            # DEBUG: πάρε το ωμό κείμενο
                            try:
                                with pdfplumber.open(io.BytesIO(att.payload)) as pdf:
                                    raw = "\n".join(p.extract_text() or "" for p in pdf.pages)
                                debug_texts.append((msg.date, att.filename, raw))
                            except Exception as e:
                                debug_texts.append((msg.date, att.filename, f"ERROR: {e}"))

                            data = extract_pdf_data(att.payload)
                            if data['date'] is None:
                                data['date'] = msg.date.date()
                            if data['netday'] is not None:
                                results.append(data)
                                break
            st.caption(f"🔎 Ελέγχθηκαν {checked}, ταίριαξαν {matched}, PDFs {pdfs_found}")
    except Exception as e:
        st.error(f"Email Error: {e}")

    # Εμφάνισε το ωμό κείμενο του πρώτου PDF
    if debug_texts:
        d, fn, raw = debug_texts[0]
        with st.expander(f"🔍 DEBUG: Περιεχόμενο PDF ({fn})", expanded=True):
            st.text(raw[:3000] if raw else "(κενό)")
    return results
# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("🛒 ΑΒ ΣΚΥΡΟΣ – Dashboard")

with st.expander("⚙️ Ενημέρωση Δεδομένων", expanded=False):
    c1, c2 = st.columns([3,1])
    with c1:
        n_check = st.number_input("Έλεγχος τελευταίων emails:", 10, 1000, 200)
    with c2:
        st.write(""); st.write("")
        if st.button("📥 Λήψη", use_container_width=True):
            fetch_reports.clear()
            with st.spinner("Αναζήτηση..."):
                fetched = fetch_reports(n_check)
            if fetched:
                for d in fetched:
                    upsert_daily({'date': d['date'], 'netday': d['netday'], 
                                  'customers': d['customers'], 'avg_basket': d['avg_basket']})
                    if d['hourly']: upsert_hourly(d['date'], d['hourly'])
                st.success(f"✅ Βρέθηκαν {len(fetched)} ημέρες!")
                st.rerun()
            else:
                st.info("Δεν βρέθηκαν νέα reports.")

history = load_history()
if history.empty:
    st.warning("Δεν υπάρχουν δεδομένα. Πατήστε 'Λήψη'.")
    st.stop()

# Display
last = history.iloc[-1]
st.subheader(f"📅 Ημερομηνία: {last['date'].strftime('%d/%m/%Y')}")
c1, c2, c3 = st.columns(3)
c1.metric("Πωλήσεις", fmt_euro(last['netday']))
c2.metric("Πελάτες", f"{int(last['customers'])}")
c3.metric("Μ.Ό. Καλαθιού", fmt_euro(last['avg_basket']))

st.divider()
st.subheader("📊 Τελευταίες 30 ημέρες")
chart_data = history.tail(30).copy()
chart_data['date_str'] = chart_data['date'].apply(lambda d: d.strftime('%d/%m'))
st.bar_chart(chart_data.set_index('date_str')['netday'])

st.dataframe(history.sort_values('date', ascending=False), use_container_width=True, hide_index=True)
