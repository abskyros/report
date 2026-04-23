import streamlit as st
import pandas as pd
import io
import os
import re
import pdfplumber
from imap_tools import MailBox
from datetime import datetime, date
import unicodedata
import traceback

# ─────────────────────────────────────────────────────────────────────────────
# ΡΥΘΜΙΣΕΙΣ
# ─────────────────────────────────────────────────────────────────────────────
EMAIL_USER   = "ftoulisgm@gmail.com"
EMAIL_PASS   = st.secrets["EMAIL_PASSWORD"]
EMAIL_FROM   = "abf.skyros@gmail.com"   # ← φιλτράρουμε βάσει αποστολέα

HISTORY_FILE = "sales_history.csv"
HOURLY_FILE  = "hourly_history.csv"

DAYS_GR   = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος",
              "Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"]

st.set_page_config(
    page_title="ΑΒ ΣΚΥΡΟΣ – Dashboard",
    layout="centered",
    page_icon="🛒",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  [data-testid="metric-container"] {
    background: #f8f9fa; border-radius: 12px;
    padding: 12px 16px !important; border: 1px solid #e9ecef;
  }
  [data-testid="stMetricValue"] { font-size: 1.45rem !important; font-weight: 700; }
  [data-testid="stMetricLabel"] { font-size: 0.78rem !important; color: #6c757d; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ΒΟΗΘΗΤΙΚΕΣ
# ─────────────────────────────────────────────────────────────────────────────

def fmt_euro(v):
    if v is None: return "—"
    return f"{v:,.2f} €"

def parse_number(s: str) -> float:
    """Μετατρέπει '7.488,29' ή '7,488.29' ή '288' σε float."""
    s = s.strip().replace('€','').replace(' ','').replace('\xa0','')
    if '.' in s and ',' in s:
        if s.index('.') < s.index(','):
            s = s.replace('.','').replace(',','.')
        else:
            s = s.replace(',','')
    elif ',' in s:
        s = s.replace(',','.')
    try:
        return float(s)
    except:
        return 0.0

# ─────────────────────────────────────────────────────────────────────────────
# ΙΣΤΟΡΙΚΟ CSV
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
    save_history(df.sort_values('date').reset_index(drop=True))

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
        new_df = pd.DataFrame([{**r, 'date': record_date} for r in hourly_rows])
        df = pd.concat([df, new_df], ignore_index=True)
        df = df.sort_values(['date','hour']).reset_index(drop=True)
    save_hourly(df)

# ─────────────────────────────────────────────────────────────────────────────
# PDF PARSER
# ─────────────────────────────────────────────────────────────────────────────

def extract_pdf_data(pdf_bytes: bytes) -> dict:
    """
    Διαβάζει το PDF από abf.skyros@gmail.com.
    Περιέχει: Department Report + Hourly Productivity + Total Declaration
    Εξάγει: date, netday (NetDaySalDis), customers (NumOfCus), avg_basket (AvgSalCus)
    """
    result = {
        'date': None, 'netday': None,
        'customers': None, 'avg_basket': None,
        'hourly': []
    }

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        st.warning(f"⚠️ Δεν άνοιξε το PDF: {e}")
        return result

    # ── 1. Ημερομηνία ──────────────────────────────────────────────────────
    # Αναζητούμε "For DD/MM/YYYY"
    m = re.search(r'For\s+(\d{2}/\d{2}/\d{4})', full_text)
    if not m:
        m = re.search(r'(\d{2}/\d{2}/\d{4})', full_text)
    if m:
        try:
            result['date'] = datetime.strptime(m.group(1), "%d/%m/%Y").date()
        except Exception:
            pass

    # ── 2. Κύρια μεγέθη ────────────────────────────────────────────────────
    # Βρίσκουμε το label και παίρνουμε τον πρώτο αριθμό που ακολουθεί
    NUM_PAT = re.compile(r'-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|-?\d+')

    def find_value_after(label: str):
        idx = full_text.find(label)
        if idx == -1:
            return None
        snippet = full_text[idx + len(label): idx + len(label) + 80]
        m = NUM_PAT.search(snippet)
        return m.group() if m else None

    raw = find_value_after('NetDaySalDis')
    if raw:
        result['netday'] = parse_number(raw)

    raw = find_value_after('NumOfCus')
    if raw:
        try:
            result['customers'] = int(parse_number(raw))
        except Exception:
            pass

    raw = find_value_after('AvgSalCus')
    if raw:
        result['avg_basket'] = parse_number(raw)

    # ── 3. Ωριαία ──────────────────────────────────────────────────────────
    # Μορφή: "08:00 - 08:59  111.17 €  1.48  6  ..."
    hourly_re = re.compile(
        r'(\d{2}):\d{2}\s*-\s*\d{2}:\d{2}\s+([\d.,]+)\s*€(?:\s+[\d.,]+\s+(\d+))?'
    )
    for m in hourly_re.finditer(full_text):
        hour  = int(m.group(1))
        sales = parse_number(m.group(2))
        custs = int(m.group(3)) if m.group(3) else 0
        if sales > 0:
            result['hourly'].append({'hour': hour, 'sales': sales, 'customers': custs})

    return result

# ─────────────────────────────────────────────────────────────────────────────
# EMAIL FETCH
# ─────────────────────────────────────────────────────────────────────────────

def _pick_folder(mailbox: MailBox) -> str:
    try:
        folders = [f.name for f in mailbox.folder.list()]
    except Exception:
        return 'INBOX'
    for f in folders:
        if 'ALL' in f.upper() and ('MAIL' in f.upper() or 'GMAIL' in f.upper()):
            return f
    return 'INBOX'


@st.cache_data(ttl=300, show_spinner=False)
def fetch_reports(limit: int) -> tuple[list, list]:
    results, logs = [], []

    try:
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:

            folder = _pick_folder(mailbox)
            try:
                mailbox.folder.set(folder)
            except Exception:
                folder = 'INBOX'
                mailbox.folder.set(folder)
            logs.append(f"📂 Φάκελος: **{folder}**")

            checked = matched = pdfs_ok = 0

            for msg in mailbox.fetch(reverse=True, mark_seen=False, limit=limit):
                checked += 1

                # Φιλτράρισμα βάσει αποστολέα
                sender = (msg.from_ or '').lower()
                if EMAIL_FROM.lower() not in sender:
                    continue
                matched += 1

                for att in msg.attachments:
                    if not att.filename.lower().endswith('.pdf'):
                        continue

                    data = extract_pdf_data(att.payload)
                    if data['date'] is None:
                        data['date'] = msg.date.date()

                    if data['netday'] is not None:
                        results.append(data)
                        pdfs_ok += 1
                    else:
                        logs.append(
                            f"⚠️ Δεν βρέθηκε NetDaySalDis στο **{att.filename}** "
                            f"({msg.date.strftime('%d/%m/%Y')})"
                        )
                    break

            logs.append(
                f"🔎 Ελέγχθηκαν **{checked}** emails · "
                f"από `{EMAIL_FROM}`: **{matched}** · "
                f"επιτυχή PDFs: **{pdfs_ok}**"
            )

    except Exception as e:
        logs.append(f"❌ **Σφάλμα IMAP:** {e}")
        logs.append("```\n" + traceback.format_exc() + "\n```")

    return results, logs

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("🛒 ΑΒ ΣΚΥΡΟΣ – Dashboard")

with st.expander("⚙️ Ενημέρωση Δεδομένων", expanded=False):

    c1, c2 = st.columns([3, 1])
    with c1:
        n_check = st.number_input("Έλεγχος τελευταίων emails:", 10, 2000, 200, step=10)
    with c2:
        st.write(""); st.write("")
        fetch_btn = st.button("📥 Λήψη", use_container_width=True)

    if fetch_btn:
        fetch_reports.clear()
        with st.spinner(f"Σύνδεση και αναζήτηση από {EMAIL_FROM}..."):
            fetched, logs = fetch_reports(n_check)
        for msg in logs:
            st.markdown(msg)
        if fetched:
            for d in fetched:
                upsert_daily({
                    'date': d['date'], 'netday': d['netday'],
                    'customers': d['customers'], 'avg_basket': d['avg_basket'],
                })
                if d['hourly']:
                    upsert_hourly(d['date'], d['hourly'])
            st.success(f"✅ Αποθηκεύτηκαν δεδομένα για **{len(fetched)}** ημέρες!")
            st.rerun()
        else:
            st.info("Δεν βρέθηκαν νέα δεδομένα.")

    st.markdown("---")
    st.markdown("**Ή ανεβάστε PDF χειροκίνητα:**")
    uploaded = st.file_uploader("PDF", type="pdf", label_visibility="collapsed")
    if uploaded:
        raw_bytes = uploaded.read()
        data = extract_pdf_data(raw_bytes)
        if data['netday'] is not None:
            if data['date'] is None:
                data['date'] = date.today()
            upsert_daily({
                'date': data['date'], 'netday': data['netday'],
                'customers': data['customers'], 'avg_basket': data['avg_basket'],
            })
            if data['hourly']:
                upsert_hourly(data['date'], data['hourly'])
            st.success(
                f"✅ {data['date'].strftime('%d/%m/%Y')} · "
                f"Πωλήσεις: **{fmt_euro(data['netday'])}** · "
                f"Πελάτες: **{data['customers']}**"
            )
            st.rerun()
        else:
            st.error("Δεν βρέθηκαν δεδομένα στο PDF.")
            with st.expander("🔍 Raw PDF text (debug)"):
                with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                    raw = "\n".join(p.extract_text() or "" for p in pdf.pages)
                st.text(raw[:4000])

# ── Δεδομένα ─────────────────────────────────────────────────────────────────
history = load_history()
if history.empty:
    st.warning("Δεν υπάρχουν δεδομένα. Πατήστε «Λήψη» ή ανεβάστε PDF.")
    st.stop()

last       = history.iloc[-1]
day_name   = DAYS_GR[last['date'].weekday()]
month_name = MONTHS_GR[last['date'].month - 1]
st.subheader(f"📅 {day_name}, {last['date'].day} {month_name} {last['date'].year}")

c1, c2, c3 = st.columns(3)
c1.metric("Πωλήσεις",       fmt_euro(last['netday']))
c2.metric("Πελάτες",        f"{int(last['customers'])}" if last['customers'] else "—")
c3.metric("Μ.Ό. Καλαθιού", fmt_euro(last['avg_basket']))

if len(history) >= 2:
    prev = history.iloc[-2]
    if prev['netday'] and last['netday']:
        diff = last['netday'] - prev['netday']
        pct  = diff / prev['netday'] * 100
        sign, color = ("▲", "green") if diff >= 0 else ("▼", "red")
        st.markdown(
            f"<span style='color:{color}'>{sign} {fmt_euro(abs(diff))} "
            f"({pct:+.1f}%) σε σχέση με {prev['date'].strftime('%d/%m')}</span>",
            unsafe_allow_html=True,
        )

st.divider()
st.subheader("📊 Τελευταίες 30 ημέρες – Πωλήσεις")
chart = history.tail(30).copy()
chart['label'] = chart['date'].apply(lambda d: d.strftime('%d/%m'))
st.bar_chart(chart.set_index('label')['netday'])

hourly_df = load_hourly()
if not hourly_df.empty:
    last_date    = history.iloc[-1]['date']
    today_hourly = hourly_df[hourly_df['date'] == last_date]
    if not today_hourly.empty:
        st.subheader(f"🕐 Ωριαίες Πωλήσεις – {last_date.strftime('%d/%m/%Y')}")
        st.bar_chart(today_hourly.set_index('hour')['sales'])

st.divider()
st.subheader("📋 Ιστορικό")
disp = history.sort_values('date', ascending=False).copy()
disp['date'] = disp['date'].apply(lambda d: d.strftime('%d/%m/%Y'))
disp.columns = ['Ημερομηνία','Πωλήσεις (€)','Πελάτες','Μ.Ό. Καλαθιού (€)']
st.dataframe(disp, use_container_width=True, hide_index=True)
