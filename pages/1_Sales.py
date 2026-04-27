import streamlit as st
import pandas as pd
import os, re
from datetime import datetime, date, timedelta
from imap_tools import MailBox, AND
from pdf2image import convert_from_bytes
import pytesseract

st.set_page_config(
    page_title="Πωλήσεις — AB Σκύρος",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CONFIG ────────────────────────────────────────────────────────────────────
SALES_EMAIL_USER   = "ftoulisgm@gmail.com"
SALES_EMAIL_SENDER = "abf.skyros@gmail.com"
SALES_SUBJECT_KW   = "ΑΒ ΣΚΥΡΟΣ"
SALES_CACHE        = "sales_cache.csv"     # τελευταία 2 χρόνια
SALES_ARCHIVE      = "sales_archive.csv"   # παλαιότερα (δεν φορτώνονται ξανά)
DEEP_SCAN_YEARS    = 2
BATCH_SAVE_EVERY   = 30   # αποθήκευση κάθε Χ επιτυχημένα records

# ── SECRETS ───────────────────────────────────────────────────────────────────
_SECRET_PW = ""
try:
    _SECRET_PW = st.secrets.get("SALES_EMAIL_PASS", "")
except:
    pass

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background: #f8f9fb !important;
    color: #111827 !important;
}
.stApp { background: #f8f9fb !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container {
    padding: 1.5rem 1.5rem 4rem !important;
    max-width: 960px !important;
    margin: 0 auto !important;
}
.sh {
    font-size: .58rem; font-weight: 600; letter-spacing: .18em;
    text-transform: uppercase; color: #9ca3af;
    margin: 1.6rem 0 .7rem;
    border-bottom: 1px solid #f3f4f6;
    padding-bottom: .4rem;
}
.kr  { display: grid; gap: .7rem; margin: .5rem 0 1.2rem; }
.kr4 { grid-template-columns: repeat(4,1fr); }
.kr3 { grid-template-columns: repeat(3,1fr); }
@media(max-width:900px){ .kr4 { grid-template-columns: repeat(2,1fr); } }
@media(max-width:580px){ .kr4,.kr3 { grid-template-columns: 1fr; }
    .block-container { padding: 1rem 1rem 3rem !important; } }
.kc {
    background: #fff; border: 1px solid #e5e7eb;
    border-radius: 12px; padding: .9rem 1rem;
    position: relative; overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.kc::before {
    content: ''; position: absolute;
    top: 0; left: 0; bottom: 0; width: 3px;
    background: var(--a, #10b981);
}
.kl { font-size: .58rem; font-weight: 600; letter-spacing: .1em;
      text-transform: uppercase; color: #9ca3af; margin-bottom: .3rem; }
.kv { font-size: 1.05rem; font-weight: 700; color: #111827; }
.kv-g { color: #059669; }
.kv-r { color: #dc2626; }
.kv-sm { font-size: .88rem; font-weight: 700; color: #111827; }
.kdelta { font-size: .62rem; margin-top: .12rem; }
.up { color: #059669; } .dn { color: #dc2626; }

.stButton > button {
    border-radius: 9px !important; font-family: 'Inter', sans-serif !important;
    font-size: .82rem !important; font-weight: 600 !important;
    padding: .6rem 1rem !important; transition: all .15s !important;
}
.btn-g   > button { background: #10b981 !important; border: none !important; color: #fff !important; }
.btn-g   > button:hover { background: #059669 !important; }
.btn-back > button { background: #fff !important; border: 1px solid #d1d5db !important; color: #374151 !important; }

[data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid #e5e7eb !important; }
[data-baseweb="tab"] { background: transparent !important; border: none !important;
    color: #6b7280 !important; font-size: .74rem !important; font-weight: 600 !important;
    letter-spacing: .05em !important; text-transform: uppercase !important;
    padding: .5rem .9rem !important; border-radius: 8px 8px 0 0 !important; }
[aria-selected="true"][data-baseweb="tab"] {
    color: #10b981 !important; background: #ecfdf5 !important;
    border-bottom: 2px solid #10b981 !important; }
[data-testid="stDataFrame"] { border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; }

.ibox { background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 10px;
        padding: .75rem 1rem; font-size: .73rem; color: #059669; margin: .5rem 0; }
.wbox { background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px;
        padding: .75rem 1rem; font-size: .73rem; color: #92400e; margin: .5rem 0; }
.bbox { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px;
        padding: .75rem 1rem; font-size: .73rem; color: #1d4ed8; margin: .5rem 0; }
.step-card {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
    padding: 1rem 1.2rem; margin-bottom: .8rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.step-num {
    display: inline-flex; align-items: center; justify-content: center;
    width: 24px; height: 24px; border-radius: 50%;
    background: #10b981; color: #fff;
    font-size: .72rem; font-weight: 700; margin-right: .5rem;
}
.step-title { font-size: .88rem; font-weight: 700; color: #111827; margin-bottom: .3rem; }
.step-desc  { font-size: .73rem; color: #6b7280; }
</style>
""", unsafe_allow_html=True)

# ── MONTHS ────────────────────────────────────────────────────────────────────
MN = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

def parse_num(s):
    s = str(s).strip().replace(" ","").replace("€","")
    if "." in s and "," in s: s = s.replace(".","").replace(",",".")
    elif "," in s: s = s.replace(",",".")
    return float(s)

# ── CACHE I/O ─────────────────────────────────────────────────────────────────
def load_cache() -> pd.DataFrame:
    """Φορτώνει μόνο το SALES_CACHE (τελευταία 2 χρόνια)."""
    if os.path.exists(SALES_CACHE):
        try:
            df = pd.read_csv(SALES_CACHE)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"]).dt.date
                return (df.sort_values("net_sales", ascending=False)
                          .drop_duplicates("date", keep="first")
                          .sort_values("date", ascending=False)
                          .reset_index(drop=True))
        except: pass
    return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])

def load_all() -> pd.DataFrame:
    """Φορτώνει cache + archive (για ιστορικό/γράφημα)."""
    parts = []
    for f in [SALES_CACHE, SALES_ARCHIVE]:
        if os.path.exists(f):
            try:
                df = pd.read_csv(f)
                if not df.empty:
                    df["date"] = pd.to_datetime(df["date"]).dt.date
                    parts.append(df)
            except: pass
    if parts:
        combined = pd.concat(parts)
        return (combined.sort_values("net_sales", ascending=False)
                        .drop_duplicates("date", keep="first")
                        .sort_values("date", ascending=False)
                        .reset_index(drop=True))
    return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])

def save_and_split(df: pd.DataFrame):
    """
    Αποθηκεύει:
    - Τελευταία 2 χρόνια → SALES_CACHE  (ξαναφορτώνεται για ενημέρωση)
    - Παλαιότερα         → SALES_ARCHIVE (ΜΟΝΟ append, δεν ξαναφορτώνεται)
    """
    cutoff = date.today() - timedelta(days=365 * DEEP_SCAN_YEARS)
    recent = df[df["date"] >= cutoff].copy()
    old    = df[df["date"] <  cutoff].copy()

    recent.to_csv(SALES_CACHE, index=False)

    if not old.empty:
        if os.path.exists(SALES_ARCHIVE):
            try:
                ex = pd.read_csv(SALES_ARCHIVE)
                ex["date"] = pd.to_datetime(ex["date"]).dt.date
                # Merge: κρατάμε μεγαλύτερη τιμή ανά ημέρα
                old = (pd.concat([ex, old])
                         .sort_values("net_sales", ascending=False)
                         .drop_duplicates("date", keep="first")
                         .sort_values("date", ascending=False))
            except: pass
        old.to_csv(SALES_ARCHIVE, index=False)

def merge_new_into_cache(new_records: list) -> int:
    """
    Συγχωνεύει νέα records στο cache.
    Για κάθε ημερομηνία: κρατάει τη ΜΕΓΑΛΥΤΕΡΗ τιμή.
    Επιστρέφει αριθμό πραγματικά νέων/ενημερωμένων εγγραφών.
    """
    if not new_records:
        return 0

    new_df = pd.DataFrame(new_records)
    # Dedup within new batch (κρατάμε μεγαλύτερη τιμή ανά ημέρα)
    new_df = (new_df.sort_values("net_sales", ascending=False)
                    .drop_duplicates("date", keep="first"))

    old_df = load_cache()

    actually_new = 0
    if old_df.empty:
        merged = new_df
        actually_new = len(new_df)
    else:
        rows_to_add = []
        for _, row in new_df.iterrows():
            existing = old_df[old_df["date"] == row["date"]]
            if existing.empty:
                rows_to_add.append(row)
                actually_new += 1
            elif row["net_sales"] > existing.iloc[0]["net_sales"]:
                # Νεότερη, μεγαλύτερη τιμή → αντικατάσταση
                old_df = old_df[old_df["date"] != row["date"]]
                rows_to_add.append(row)
                actually_new += 1

        if rows_to_add:
            merged = pd.concat([old_df, pd.DataFrame(rows_to_add)])
        else:
            merged = old_df

    merged = (merged.sort_values("date", ascending=False)
                    .reset_index(drop=True))
    save_and_split(merged)
    return actually_new

def get_last_cached_date() -> date | None:
    """Επιστρέφει την πιο πρόσφατη ημερομηνία στο cache."""
    df = load_cache()
    if df.empty: return None
    return df["date"].max()

# ── OCR ───────────────────────────────────────────────────────────────────────
def extract_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Εξάγει: date, net_sales, customers, avg_basket
    από Department Report PDF (AB Σκύρος).
    Πεδία: NeitDaySalDis, NumItmSold, AvgItmPerCus
    """
    result = {"date": None, "net_sales": None, "customers": None, "avg_basket": None}
    try:
        images    = convert_from_bytes(pdf_bytes, dpi=200)
        full_text = ""
        for img in images:
            full_text += pytesseract.image_to_string(img, lang="ell+eng") + "\n"

        # ── Ημερομηνία: "For  25/04/2026" ────────────────────────────────────
        for pat in [
            r'[Ff]or\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'[Ff]or\s*[:\-]?\s*(\d{1,2}\.\d{1,2}\.\d{4})',
            r'(\d{2}/\d{2}/\d{4})',
        ]:
            m = re.search(pat, full_text)
            if m:
                try:
                    result["date"] = datetime.strptime(
                        m.group(1).replace(".","/"), "%d/%m/%Y"
                    ).date()
                    break
                except: pass

        # ── Καθαρές πωλήσεις: NeitDaySalDis ─────────────────────────────────
        for pat in [
            r'[Nn]e[it]{1,3}[Dd]ay[Ss]al[Dd]is\s+([\d.,]+)',
            r'[Nn]et[Dd]ay[Ss]al[Dd]is\s+([\d.,]+)',
        ]:
            m = re.search(pat, full_text)
            if m:
                try: result["net_sales"] = parse_num(m.group(1)); break
                except: pass

        # Fallback: Hourly Totals line
        if result["net_sales"] is None:
            m = re.search(r'[Tt]otals?\s*:?\s*([\d.,]+)\s+100[.,]00\s+([\d]+)', full_text)
            if m:
                try:
                    result["net_sales"] = parse_num(m.group(1))
                    if result["customers"] is None:
                        result["customers"] = int(m.group(2))
                except: pass

        # Fallback: GroupTot
        if result["net_sales"] is None:
            m = re.search(r'[Gg]roup[Tt]ot\s+([\d.,]+)\s+([\d.,]+)', full_text)
            if m:
                try: result["net_sales"] = parse_num(m.group(2))
                except: pass

        # ── Πελάτες: NumItmSold ───────────────────────────────────────────────
        if result["customers"] is None:
            m = re.search(r'[Nn]um[Ii]tm[Ss]old\s+([\d,.]+)', full_text)
            if m:
                try: result["customers"] = int(m.group(1).replace(",","").replace(".",""))
                except: pass

        # ── ΜΟ Καλαθιού: AvgItmPerCus ────────────────────────────────────────
        for pat in [
            r'[Aa]vg[Ii]tm[Pp]er[Cc]us\s+([\d.,]+)',
            r'[Aa]vg[Ii]tm[Pp]ric\s+([\d.,]+)',
        ]:
            m = re.search(pat, full_text)
            if m:
                try: result["avg_basket"] = parse_num(m.group(1)); break
                except: pass

    except Exception as e:
        pass  # silent fail — επιστρέφει empty result

    return result

# ── EMAIL FUNCTIONS ────────────────────────────────────────────────────────────
def preview_emails(password: str) -> tuple[list, list]:
    """
    Δοκιμή σύνδεσης: εμφανίζει emails χωρίς OCR — γρήγορο.
    """
    rows, errors = [], []
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, password) as mb:
            msgs = list(mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                 limit=5, reverse=True, mark_seen=False))
            for msg in msgs:
                atts = [a.filename for a in msg.attachments if a.filename] or ["—"]
                rows.append({
                    "Ημερομηνία": msg.date.strftime("%d/%m/%Y %H:%M") if msg.date else "—",
                    "Θέμα":       (msg.subject or "")[:60],
                    "Attachment": atts[0],
                })
    except Exception as e:
        errors.append(str(e))
    return rows, errors

def fetch_recent(password: str, days: int = 5) -> tuple[list, list, int]:
    """
    Φέρνει emails των τελευταίων N ημερών με OCR.
    Χρησιμοποιείται για δοκιμή (5 μέρες) και για καθημερινή ενημέρωση.
    """
    since = date.today() - timedelta(days=days)
    records, errors = [], []
    checked = 0
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, password) as mb:
            msgs = list(mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                 limit=days + 10, reverse=True, mark_seen=False))
            for msg in msgs:
                msg_date = msg.date.date() if msg.date else None
                if msg_date and msg_date < since:
                    continue
                subj = (msg.subject or "").upper()
                if SALES_SUBJECT_KW not in subj and "SKYROS" not in subj:
                    continue
                pdf = next((a for a in msg.attachments
                            if a.filename and a.filename.lower().endswith(".pdf")), None)
                if not pdf: continue
                checked += 1
                rec = extract_from_pdf(pdf.payload)
                if rec["date"] and rec["net_sales"] is not None:
                    records.append(rec)
    except Exception as e:
        errors.append(str(e))
    return records, errors, checked

def fetch_incremental(password: str) -> tuple[list, list, int]:
    """
    Καθημερινή ενημέρωση: φέρνει emails από την τελευταία
    αποθηκευμένη ημερομηνία + 3 μέρες overlap.
    """
    last_date = get_last_cached_date()
    if last_date is None:
        # Δεν υπάρχει cache → δοκιμή 5 ημερών
        return fetch_recent(password, days=5)

    since = last_date - timedelta(days=3)
    records, errors = [], []
    checked = 0
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, password) as mb:
            msgs = list(mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                 limit=60, reverse=True, mark_seen=False))
            for msg in msgs:
                msg_date = msg.date.date() if msg.date else None
                if msg_date and msg_date < since: continue
                subj = (msg.subject or "").upper()
                if SALES_SUBJECT_KW not in subj and "SKYROS" not in subj: continue
                pdf = next((a for a in msg.attachments
                            if a.filename and a.filename.lower().endswith(".pdf")), None)
                if not pdf: continue
                checked += 1
                rec = extract_from_pdf(pdf.payload)
                if rec["date"] and rec["net_sales"] is not None:
                    records.append(rec)
    except Exception as e:
        errors.append(str(e))
    return records, errors, checked

# ── DEEP SCAN (generator για streaming progress) ──────────────────────────────
def deep_scan_generator(password: str):
    """
    Generator που κάνει βαθιά σάρωση 2 ετών.
    Κάθε yield επιστρέφει (status_dict) για live progress.
    Αποθηκεύει κάθε BATCH_SAVE_EVERY επιτυχημένα records.
    """
    cutoff = date.today() - timedelta(days=365 * DEEP_SCAN_YEARS)
    status = {
        "phase": "connect",
        "total": 0, "done": 0, "saved": 0,
        "current": "", "error": None, "finished": False
    }
    yield status.copy()

    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, password) as mb:
            # Φάση 1: Φέρνουμε headers μόνο (γρήγορο)
            status["phase"] = "listing"
            yield status.copy()

            all_msgs = list(mb.fetch(
                AND(from_=SALES_EMAIL_SENDER),
                limit=2000, reverse=True, mark_seen=False,
                headers_only=True
            ))

            # Φιλτράρισμα
            to_process = []
            for msg in all_msgs:
                msg_date = msg.date.date() if msg.date else None
                if not msg_date or msg_date < cutoff: continue
                subj = (msg.subject or "").upper()
                if SALES_SUBJECT_KW not in subj and "SKYROS" not in subj: continue
                to_process.append(msg)

            status["total"] = len(to_process)
            status["phase"] = "ocr"
            yield status.copy()

            if not to_process:
                status["finished"] = True
                yield status.copy()
                return

            batch = []

            # Φάση 2: OCR ένα-ένα
            for i, msg_h in enumerate(to_process):
                status["done"]    = i + 1
                status["current"] = (msg_h.subject or "")[:50]
                yield status.copy()

                try:
                    # Re-fetch με attachments χρησιμοποιώντας uid
                    full = list(mb.fetch(
                        AND(uid=str(msg_h.uid)),
                        mark_seen=False
                    ))
                    if not full: continue
                    pdf = next((a for a in full[0].attachments
                                if a.filename and a.filename.lower().endswith(".pdf")), None)
                    if not pdf: continue

                    rec = extract_from_pdf(pdf.payload)
                    if rec["date"] and rec["net_sales"] is not None:
                        batch.append(rec)

                    # Ενδιάμεση αποθήκευση
                    if len(batch) >= BATCH_SAVE_EVERY:
                        saved = merge_new_into_cache(batch)
                        status["saved"] += saved
                        batch = []
                        yield status.copy()

                except:
                    continue

            # Τελευταίο batch
            if batch:
                saved = merge_new_into_cache(batch)
                status["saved"] += saved

            status["finished"] = True
            yield status.copy()

    except Exception as e:
        status["error"]    = str(e)
        status["finished"] = True
        yield status.copy()

# ── LOAD ─────────────────────────────────────────────────────────────────────
df    = load_all()
today = date.today()
week_start = today - timedelta(days=today.weekday())
week_end   = week_start + timedelta(days=6)
week_lbl   = f"{week_start.strftime('%d/%m')} – {week_end.strftime('%d/%m')}"
last_cached = get_last_cached_date()

# ── HEADER ────────────────────────────────────────────────────────────────────
col_title, col_back = st.columns([5, 1])
with col_title:
    st.markdown("## 📊 Πωλήσεις Καταστήματος")
with col_back:
    st.markdown('<div class="btn-back">', unsafe_allow_html=True)
    if st.button("← Αρχική", key="back"):
        st.switch_page("Home.py")
    st.markdown("</div>", unsafe_allow_html=True)

# ── TABS ─────────────────────────────────────────────────────────────────────
tab_dash, tab_hist, tab_update = st.tabs(["📈 DASHBOARD", "📋 ΙΣΤΟΡΙΚΟ", "🔄 ΕΝΗΜΕΡΩΣΗ"])

# ══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    if df.empty:
        st.markdown('<div class="wbox">⚠️ Δεν υπάρχουν δεδομένα. Μεταβείτε στην καρτέλα <b>ΕΝΗΜΕΡΩΣΗ</b>.</div>',
                    unsafe_allow_html=True)
    else:
        last = df.iloc[0]
        prev = df.iloc[1] if len(df) > 1 else None

        def delta(now, pv):
            if pv is None or (isinstance(pv, float) and pd.isna(pv)) or float(pv)==0: return ""
            d = float(now) - float(pv); p = d/float(pv)*100
            sym = "▲" if d>=0 else "▼"; cls = "up" if d>=0 else "dn"
            return f'<div class="kdelta {cls}">{sym} {abs(p):.1f}%</div>'

        p_ns = prev["net_sales"]  if prev is not None else None
        p_cu = prev["customers"]  if prev is not None and pd.notna(prev.get("customers")) else None
        p_ab = prev["avg_basket"] if prev is not None and pd.notna(prev.get("avg_basket")) else None
        days_old = (today - last["date"]).days
        date_lbl = last["date"].strftime("%d/%m/%Y")

        # ── Τελευταία Ημέρα ──────────────────────────────────────────────────
        st.markdown('<div class="sh">Τελευταία Ημέρα</div>', unsafe_allow_html=True)
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            cval = int(last["customers"]) if pd.notna(last.get("customers")) else "—"
            upd  = "Σήμερα" if days_old==0 else f"Πριν {days_old} μέρ."
            st.markdown(f"""<div class="kc" style="--a:#10b981">
              <div class="kl">Πωλήσεις · {date_lbl}</div>
              <div class="kv">{fmt(last['net_sales'])}</div>
              {delta(last['net_sales'], p_ns)}</div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="kc" style="--a:#7c3aed">
              <div class="kl">Πελάτες</div>
              <div class="kv">{cval}</div>
              {delta(cval if cval!='—' else 0, p_cu)}</div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="kc" style="--a:#3b82f6">
              <div class="kl">ΜΟ Καλαθιού</div>
              <div class="kv">{fmt(last.get('avg_basket'))}</div>
              {delta(last.get('avg_basket') or 0, p_ab)}</div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""<div class="kc" style="--a:#f59e0b">
              <div class="kl">Ενημέρωση</div>
              <div class="kv kv-sm">{upd}</div></div>""", unsafe_allow_html=True)

        # ── Εβδομάδα ─────────────────────────────────────────────────────────
        st.markdown(f'<div class="sh">Τρέχουσα Εβδομάδα · {week_lbl}</div>', unsafe_allow_html=True)
        w_df  = df[(df["date"] >= week_start) & (df["date"] <= today)]
        w_tot = w_df["net_sales"].sum() if not w_df.empty else 0
        w_avg = w_df["net_sales"].mean() if not w_df.empty else 0
        pw_s  = week_start - timedelta(days=7)
        pw_df = df[(df["date"] >= pw_s) & (df["date"] < week_start)]
        pw_t  = pw_df["net_sales"].sum() if not pw_df.empty else None
        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="kc" style="--a:#10b981">
              <div class="kl">Σύνολο Εβδομάδας</div>
              <div class="kv kv-g">{fmt(w_tot)}</div>
              {delta(w_tot, pw_t)}</div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="kc" style="--a:#3b82f6">
              <div class="kl">Ημερήσιος ΜΟ</div>
              <div class="kv">{fmt(w_avg)}</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="kc" style="--a:#7c3aed">
              <div class="kl">Ημέρες καταγεγραμμένες</div>
              <div class="kv">{len(w_df)} / 7</div></div>""", unsafe_allow_html=True)

        # ── Μήνας ────────────────────────────────────────────────────────────
        st.markdown(f'<div class="sh">Τρέχων Μήνας · {MN[today.month-1]} {today.year}</div>', unsafe_allow_html=True)
        m_df = df[(df["date"] >= date(today.year,today.month,1)) & (df["date"] <= today)]
        m_tot = m_df["net_sales"].sum() if not m_df.empty else 0
        lp = date(today.year,today.month,1) - timedelta(days=1)
        pm_df = df[(df["date"] >= date(lp.year,lp.month,1)) & (df["date"] <= lp)]
        pm_t  = pm_df["net_sales"].sum() if not pm_df.empty else None
        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="kc" style="--a:#10b981">
              <div class="kl">Σύνολο Μήνα</div>
              <div class="kv">{fmt(m_tot)}</div>
              {delta(m_tot, pm_t)}</div>""", unsafe_allow_html=True)
        with c2:
            avg_m = m_df["net_sales"].mean() if not m_df.empty else 0
            st.markdown(f"""<div class="kc" style="--a:#3b82f6">
              <div class="kl">Ημερήσιος ΜΟ</div>
              <div class="kv">{fmt(avg_m)}</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="kc" style="--a:#7c3aed">
              <div class="kl">Ημέρες</div>
              <div class="kv">{len(m_df)}</div></div>""", unsafe_allow_html=True)

        # ── Chart ─────────────────────────────────────────────────────────────
        st.markdown('<div class="sh">Τελευταίες 14 ημέρες</div>', unsafe_allow_html=True)
        ch = df[df["date"] >= (today - timedelta(days=13))].sort_values("date").copy()
        if not ch.empty:
            ch.index = ch["date"].apply(lambda d: d.strftime("%d/%m"))
            st.bar_chart(ch["net_sales"], color="#10b981", height=200)

# ══════════════════════════════════════════════════════════════════════════════
with tab_hist:
    if df.empty:
        st.markdown('<div class="wbox">Δεν υπάρχουν δεδομένα.</div>', unsafe_allow_html=True)
    else:
        c1,c2 = st.columns(2)
        with c1: sel_y = st.selectbox("Έτος", sorted({r.year for r in df["date"]}, reverse=True))
        with c2: sel_m = st.selectbox("Μήνας", range(1,13), format_func=lambda x: MN[x-1], index=today.month-1)
        filt = df[(df["date"].apply(lambda d:d.year)==sel_y) &
                  (df["date"].apply(lambda d:d.month)==sel_m)].copy()
        if not filt.empty:
            tot = filt["net_sales"].sum(); avg = filt["net_sales"].mean()
            c1,c2,c3 = st.columns(3)
            with c1: st.markdown(f'<div class="kc" style="--a:#10b981"><div class="kl">Σύνολο</div><div class="kv">{fmt(tot)}</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="kc" style="--a:#3b82f6"><div class="kl">Ημ. ΜΟ</div><div class="kv">{fmt(avg)}</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="kc" style="--a:#7c3aed"><div class="kl">Ημέρες</div><div class="kv">{len(filt)}</div></div>', unsafe_allow_html=True)
            disp = filt.copy()
            disp["date"] = disp["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
            disp.columns = ["Ημερομηνία","Καθαρές Πωλήσεις","Πελάτες","ΜΟ Καλαθιού"]
            st.dataframe(disp, use_container_width=True, hide_index=True)
            csv = filt.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 Λήψη CSV", csv, f"sales_{sel_y}_{sel_m:02d}.csv", "text/csv")
        else:
            st.markdown('<div class="wbox">Δεν υπάρχουν δεδομένα για αυτή την περίοδο.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
with tab_update:

    # ── Password ──────────────────────────────────────────────────────────────
    if _SECRET_PW:
        st.markdown(f'<div class="ibox">🔐 App Password φορτώθηκε από Streamlit Secrets · <b>{SALES_EMAIL_USER}</b></div>', unsafe_allow_html=True)
        password = _SECRET_PW
    else:
        st.markdown('<div class="wbox">⚠️ Δεν βρέθηκε <b>SALES_EMAIL_PASS</b> στα Secrets — εισάγετε χειροκίνητα.</div>', unsafe_allow_html=True)
        password = st.text_input("🔐 Gmail App Password", type="password", key="pw")

    # ── Κατάσταση Cache ───────────────────────────────────────────────────────
    st.markdown('<div class="sh">Κατάσταση Δεδομένων</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    n_cache   = len(pd.read_csv(SALES_CACHE)) if os.path.exists(SALES_CACHE) else 0
    n_archive = len(pd.read_csv(SALES_ARCHIVE)) if os.path.exists(SALES_ARCHIVE) else 0
    oldest    = df["date"].min().strftime("%d/%m/%Y") if not df.empty else "—"
    newest    = df["date"].max().strftime("%d/%m/%Y") if not df.empty else "—"
    with c1: st.markdown(f'<div class="kc" style="--a:#10b981"><div class="kl">Εγγραφές (2χρ)</div><div class="kv">{n_cache}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kc" style="--a:#7c3aed"><div class="kl">Αρχείο</div><div class="kv">{n_archive}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kc" style="--a:#3b82f6"><div class="kl">Από</div><div class="kv kv-sm">{oldest}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="kc" style="--a:#f59e0b"><div class="kl">Έως</div><div class="kv kv-sm">{newest}</div></div>', unsafe_allow_html=True)

    # ── Βήματα ───────────────────────────────────────────────────────────────
    st.markdown('<div class="sh">Επιλογές Ενημέρωσης</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="step-card">
      <div><span class="step-num">1</span><span class="step-title">Δοκιμή Σύνδεσης (χωρίς OCR)</span></div>
      <div class="step-desc">Επιβεβαιώνει ότι η σύνδεση λειτουργεί. Εμφανίζει τα 5 τελευταία emails σε δευτερόλεπτα.</div>
    </div>
    <div class="step-card">
      <div><span class="step-num">2</span><span class="step-title">Τελευταίες 5 μέρες (με OCR)</span></div>
      <div class="step-desc">Διαβάζει και αναλύει τα PDFs των τελευταίων 5 ημερών. Ιδανικό για πρώτη δοκιμή του OCR (~30 δευτ.).</div>
    </div>
    <div class="step-card">
      <div><span class="step-num">3</span><span class="step-title">Καθημερινή Ενημέρωση</span></div>
      <div class="step-desc">Φέρνει μόνο ό,τι λείπει από την τελευταία αποθηκευμένη ημερομηνία ({newest}). Γρήγορο.</div>
    </div>
    <div class="step-card">
      <div><span class="step-num">4</span><span class="step-title">Βαθιά Σάρωση 2 ετών</span></div>
      <div class="step-desc">Μία φορά για να φορτωθεί ΟΛΟ το ιστορικό. Αποθηκεύει κάθε {BATCH_SAVE_EVERY} records. Μείνετε στη σελίδα.</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    btn_preview    = c1.button("👁 Δοκιμή Σύνδεσης",     use_container_width=True)
    btn_5days      = c2.button("📅 Τελευταίες 5 Μέρες",  use_container_width=True)
    btn_incremental= c3.button("⚡ Καθημερινή Ενημέρωση", use_container_width=True)
    btn_deep       = c4.button("🔍 Βαθιά Σάρωση 2 ετών", use_container_width=True)

    if not password and (btn_preview or btn_5days or btn_incremental or btn_deep):
        st.error("⚠️ Εισάγετε App Password.")

    # ── Βήμα 1: Δοκιμή Σύνδεσης ─────────────────────────────────────────────
    elif btn_preview and password:
        with st.spinner("Σύνδεση..."):
            rows, errs = preview_emails(password)
        if errs:
            st.error(f"❌ {errs[0]}")
        elif not rows:
            st.markdown('<div class="wbox">⚠️ Δεν βρέθηκαν emails από αυτόν τον αποστολέα.</div>', unsafe_allow_html=True)
        else:
            st.success(f"✅ Σύνδεση επιτυχής! Βρέθηκαν {len(rows)} emails.")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.markdown('<div class="ibox">✅ Η σύνδεση λειτουργεί! Πατήστε <b>Τελευταίες 5 Μέρες</b> για να δοκιμάσετε το OCR.</div>', unsafe_allow_html=True)

    # ── Βήμα 2: Τελευταίες 5 μέρες (OCR) ────────────────────────────────────
    elif btn_5days and password:
        with st.spinner("OCR τελευταίων 5 ημερών..."):
            recs, errs, checked = fetch_recent(password, days=5)
        if errs:
            st.error(f"❌ {errs[0]}")
        else:
            st.markdown(f'<div class="ibox">📬 Βρέθηκαν <b>{checked}</b> PDFs · εξήχθησαν <b>{len(recs)}</b> εγγραφές</div>', unsafe_allow_html=True)
            if recs:
                saved = merge_new_into_cache(recs)
                pv = pd.DataFrame(recs)
                pv["date"] = pv["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
                st.dataframe(pv, use_container_width=True, hide_index=True)
                st.success(f"✅ Αποθηκεύτηκαν {saved} νέες/ενημερωμένες εγγραφές!")
                if saved > 0: st.rerun()
            else:
                st.markdown('<div class="ibox">Δεν βρέθηκαν δεδομένα στις τελευταίες 5 μέρες.</div>', unsafe_allow_html=True)

    # ── Βήμα 3: Καθημερινή Ενημέρωση ────────────────────────────────────────
    elif btn_incremental and password:
        last_d = get_last_cached_date()
        info   = f"από {last_d.strftime('%d/%m/%Y')}" if last_d else "τελευταίες 5 μέρες"
        with st.spinner(f"Ενημέρωση {info}..."):
            recs, errs, checked = fetch_incremental(password)
        if errs:
            st.error(f"❌ {errs[0]}")
        else:
            st.markdown(f'<div class="ibox">📬 Ελέγχθηκαν <b>{checked}</b> PDFs</div>', unsafe_allow_html=True)
            if recs:
                saved = merge_new_into_cache(recs)
                pv = pd.DataFrame(recs)
                pv["date"] = pv["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
                st.dataframe(pv, use_container_width=True, hide_index=True)
                st.success(f"✅ {saved} νέες/ενημερωμένες εγγραφές!")
                if saved > 0: st.rerun()
            else:
                st.markdown('<div class="ibox">✅ Ενημερωμένο — δεν υπάρχουν νέα δεδομένα.</div>', unsafe_allow_html=True)

    # ── Βήμα 4: Βαθιά Σάρωση ─────────────────────────────────────────────────
    elif btn_deep and password:
        st.markdown('<div class="wbox">⏳ Η βαθιά σάρωση τρέχει. <b>Μείνετε στη σελίδα.</b> Αποθηκεύεται αυτόματα κάθε λίγα records.</div>', unsafe_allow_html=True)

        prog_bar    = st.progress(0)
        status_text = st.empty()
        result_box  = st.empty()

        for status in deep_scan_generator(password):
            if status["error"]:
                result_box.error(f"❌ {status['error']}")
                break

            phase = status["phase"]
            if phase == "connect":
                status_text.markdown("🔌 Σύνδεση στο email...")
            elif phase == "listing":
                status_text.markdown("📋 Ανάκτηση λίστας emails...")
            elif phase == "ocr":
                total = status["total"]
                done  = status["done"]
                saved = status["saved"]
                if total > 0:
                    pct = int(done / total * 100)
                    prog_bar.progress(pct)
                    status_text.markdown(
                        f"🔍 OCR: **{done}/{total}** emails "
                        f"| 💾 Αποθηκεύτηκαν: **{saved}** εγγραφές "
                        f"| _{status['current'][:45]}_"
                    )

            if status["finished"]:
                prog_bar.progress(100)
                total_saved = status["saved"]
                status_text.markdown(f"✅ Ολοκληρώθηκε! **{total_saved}** εγγραφές αποθηκεύτηκαν.")
                result_box.success(
                    f"🎉 Βαθιά σάρωση ολοκληρώθηκε!\n\n"
                    f"• Emails επεξεργάστηκαν: {status['total']}\n"
                    f"• Νέες εγγραφές: {total_saved}"
                )
                break

        st.rerun()

    # ── Χειροκίνητη Εισαγωγή ─────────────────────────────────────────────────
    st.markdown('<div class="sh">Χειροκίνητη Εισαγωγή</div>', unsafe_allow_html=True)
    with st.form("manual"):
        c1,c2,c3,c4 = st.columns(4)
        with c1: ed = st.date_input("Ημερομηνία", value=today)
        with c2: ns = st.number_input("Καθαρές Πωλήσεις (€)", min_value=0.0, step=0.01, format="%.2f")
        with c3: cu = st.number_input("Πελάτες", min_value=0, step=1)
        with c4: ab = st.number_input("ΜΟ Καλαθιού (€)", min_value=0.0, step=0.01, format="%.2f")
        if st.form_submit_button("✅ Αποθήκευση", use_container_width=True):
            saved = merge_new_into_cache([{
                "date": ed, "net_sales": ns,
                "customers": cu if cu>0 else None,
                "avg_basket": ab if ab>0 else None
            }])
            st.success(f"✅ Αποθηκεύτηκε: {ed.strftime('%d/%m/%Y')} — {fmt(ns)}")
            st.rerun()
