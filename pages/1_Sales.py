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
SALES_CACHE        = "sales_cache.csv"
SALES_ARCHIVE      = "sales_archive.csv"
DEEP_SCAN_YEARS    = 2
BATCH_SAVE_EVERY   = 25

# ── SECRETS ───────────────────────────────────────────────────────────────────
_PW = ""
try: _PW = st.secrets.get("SALES_EMAIL_PASS", "")
except: pass

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background:#f7fafc!important;color:#1a202c!important;}
.stApp{background:#f7fafc!important;}
section[data-testid="stSidebar"]{display:none!important;}
#MainMenu,footer,header{visibility:hidden!important;}
.block-container{padding:1.5rem 1.5rem 4rem!important;max-width:960px!important;margin:0 auto!important;}

.page-header{
  display:flex;justify-content:space-between;align-items:center;
  margin-bottom:1.5rem;padding-bottom:1rem;
  border-bottom:2px solid #e2e8f0;
}
.page-title{font-size:1.4rem;font-weight:800;color:#1a202c;}

.sh{
  font-size:.58rem;font-weight:700;letter-spacing:.18em;
  text-transform:uppercase;color:#a0aec0;
  margin:1.5rem 0 .7rem;
  padding-bottom:.4rem;
  border-bottom:1px solid #edf2f7;
}

.kr{display:grid;gap:.7rem;margin:.4rem 0 1rem;}
.kr4{grid-template-columns:repeat(4,1fr);}
.kr3{grid-template-columns:repeat(3,1fr);}
@media(max-width:860px){.kr4{grid-template-columns:repeat(2,1fr);}}
@media(max-width:500px){.kr4,.kr3{grid-template-columns:1fr;}}

.kc{
  background:#fff;border:1px solid #e2e8f0;
  border-radius:12px;padding:.9rem 1rem;
  position:relative;overflow:hidden;
  box-shadow:0 1px 3px rgba(0,0,0,.04);
}
.kc::before{
  content:'';position:absolute;top:0;left:0;bottom:0;
  width:3px;background:var(--a,#48bb78);
}
.kl{font-size:.57rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#a0aec0;margin-bottom:.3rem;}
.kv{font-size:1.05rem;font-weight:700;color:#1a202c;}
.kv-g{color:#38a169;} .kv-b{color:#3182ce;}
.kdelta{font-size:.62rem;margin-top:.12rem;}
.up{color:#38a169;} .dn{color:#e53e3e;}

/* Таблица */
[data-testid="stDataFrame"]{border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;}

/* Кнопки */
.stButton>button{
  border-radius:9px!important;font-family:'Inter',sans-serif!important;
  font-size:.82rem!important;font-weight:600!important;
  padding:.6rem 1rem!important;transition:all .15s!important;
}
.btn-primary>button{background:#48bb78!important;border:none!important;color:#fff!important;}
.btn-primary>button:hover{background:#38a169!important;}
.btn-secondary>button{background:#fff!important;border:1px solid #e2e8f0!important;color:#4a5568!important;}
.btn-secondary>button:hover{background:#f7fafc!important;}
.btn-deep>button{background:#744210!important;border:none!important;color:#fff!important;}
.btn-deep>button:hover{background:#5c3209!important;}
.btn-back>button{background:#fff!important;border:1px solid #e2e8f0!important;color:#718096!important;}

/* Info boxes */
.ibox{background:#f0fff4;border:1px solid #9ae6b4;border-radius:10px;padding:.75rem 1rem;font-size:.73rem;color:#276749;margin:.5rem 0;}
.wbox{background:#fffbeb;border:1px solid #f6e05e;border-radius:10px;padding:.75rem 1rem;font-size:.73rem;color:#744210;margin:.5rem 0;}
.bbox{background:#ebf8ff;border:1px solid #90cdf4;border-radius:10px;padding:.75rem 1rem;font-size:.73rem;color:#2b6cb0;margin:.5rem 0;}
.dbox{background:#fff5f5;border:1px solid #feb2b2;border-radius:10px;padding:.75rem 1rem;font-size:.73rem;color:#742a2a;margin:.5rem 0;}

/* Auto-update banner */
.auto-banner{
  background:linear-gradient(135deg,#f0fff4,#ebf8ff);
  border:1px solid #9ae6b4;border-radius:12px;
  padding:.9rem 1.2rem;margin-bottom:1.2rem;
  display:flex;align-items:center;gap:.8rem;
}
.auto-ico{font-size:1.3rem;}
.auto-text{font-size:.78rem;color:#276749;font-weight:500;}
.auto-sub{font-size:.65rem;color:#48bb78;margin-top:.1rem;}
</style>
""", unsafe_allow_html=True)

MN = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

def fmt(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return "—"
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

def parse_num(s):
    s = str(s).strip().replace(" ","").replace("€","")
    if "." in s and "," in s: s = s.replace(".","").replace(",",".")
    elif "," in s: s = s.replace(",",".")
    return float(s)

# ── CACHE I/O ─────────────────────────────────────────────────────────────────
def _dedup(df: pd.DataFrame) -> pd.DataFrame:
    """Κρατάει τη μεγαλύτερη τιμή ανά ημέρα (αγνοεί duplicates/re-sends)."""
    if df.empty: return df
    return (df.sort_values("net_sales", ascending=False)
              .drop_duplicates("date", keep="first")
              .sort_values("date", ascending=False)
              .reset_index(drop=True))

def load_cache() -> pd.DataFrame:
    if os.path.exists(SALES_CACHE):
        try:
            df = pd.read_csv(SALES_CACHE)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"]).dt.date
                return _dedup(df)
        except: pass
    return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])

def load_all() -> pd.DataFrame:
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
        return _dedup(pd.concat(parts, ignore_index=True))
    return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])

def save_and_split(df: pd.DataFrame):
    """Recent (2yr) → cache. Older → archive (append-only)."""
    df = _dedup(df)
    cutoff = date.today() - timedelta(days=365*DEEP_SCAN_YEARS)
    recent = df[df["date"] >= cutoff].copy()
    old    = df[df["date"]  < cutoff].copy()
    recent.to_csv(SALES_CACHE, index=False)
    if not old.empty:
        if os.path.exists(SALES_ARCHIVE):
            try:
                ex = pd.read_csv(SALES_ARCHIVE)
                ex["date"] = pd.to_datetime(ex["date"]).dt.date
                old = _dedup(pd.concat([ex, old], ignore_index=True))
            except: pass
        old.to_csv(SALES_ARCHIVE, index=False)

def merge_records(new_recs: list) -> int:
    """
    Συγχωνεύει νέα records στο cache.
    Για κάθε ημέρα κρατάει τη ΜΕΓΑΛΥΤΕΡΗ τιμή (αγνοεί duplicates).
    Επιστρέφει αριθμό πραγματικά νέων/ενημερωμένων εγγραφών.
    """
    if not new_recs: return 0
    new_df = _dedup(pd.DataFrame(new_recs))
    old_df = load_cache()
    count  = 0
    to_add = []
    for _, row in new_df.iterrows():
        ex = old_df[old_df["date"] == row["date"]]
        if ex.empty:
            to_add.append(row); count += 1
        elif row["net_sales"] > ex.iloc[0]["net_sales"]:
            old_df = old_df[old_df["date"] != row["date"]]
            to_add.append(row); count += 1
    if to_add:
        merged = _dedup(pd.concat([old_df, pd.DataFrame(to_add)], ignore_index=True))
        save_and_split(merged)
    return count

def last_date() -> date | None:
    df = load_cache()
    return df["date"].max() if not df.empty else None

# ── OCR ───────────────────────────────────────────────────────────────────────
def extract_pdf(pdf_bytes: bytes) -> dict:
    """
    Εξάγει: date, net_sales, customers, avg_basket
    Πεδία: NeitDaySalDis | NumOfCus | AvgSalCus
    """
    r = {"date":None,"net_sales":None,"customers":None,"avg_basket":None}
    try:
        imgs = convert_from_bytes(pdf_bytes, dpi=200)
        txt  = "".join(pytesseract.image_to_string(i, lang="ell+eng") for i in imgs)

        # Ημερομηνία
        for pat in [r'[Ff]or\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})',
                    r'[Ff]or\s*:?\s*(\d{1,2}\.\d{1,2}\.\d{4})',
                    r'(\d{2}/\d{2}/\d{4})']:
            m = re.search(pat, txt)
            if m:
                try: r["date"] = datetime.strptime(m.group(1).replace(".","/"),"%d/%m/%Y").date(); break
                except: pass

        # Καθαρές πωλήσεις
        for pat in [r'[Nn]e[it]{1,3}[Dd]ay[Ss]al[Dd]is\s+([\d.,]+)',
                    r'[Nn]et[Dd]ay[Ss]al[Dd]is\s+([\d.,]+)']:
            m = re.search(pat, txt)
            if m:
                try: r["net_sales"] = parse_num(m.group(1)); break
                except: pass

        # Fallback πωλήσεις: Hourly Totals
        if r["net_sales"] is None:
            m = re.search(r'[Tt]otals?\s*:?\s*([\d.,]+)\s+100[.,]00\s+([\d]+)', txt)
            if m:
                try:
                    r["net_sales"] = parse_num(m.group(1))
                    v = int(m.group(2))
                    if 10 <= v <= 2000: r["customers"] = v
                except: pass

        # Fallback: GroupTot
        if r["net_sales"] is None:
            m = re.search(r'[Gg]roup[Tt]ot\s+([\d.,]+)\s+([\d.,]+)', txt)
            if m:
                try: r["net_sales"] = parse_num(m.group(2))
                except: pass

        # Πελάτες: NumOfCus (= αριθμός πελατών, όχι items!)
        if r["customers"] is None:
            for pat in [r'[Nn]um[Oo]f[Cc]us\s+([\d,.]+)',
                        r'NumOfCus\s+([\d,.]+)']:
                m = re.search(pat, txt)
                if m:
                    try:
                        v = int(m.group(1).replace(",","").replace(".",""))
                        if 10 <= v <= 2000: r["customers"] = v; break
                    except: pass

        # ΜΟ Καλαθιού: AvgSalCus (= € ανά πελάτη, όχι items/πελάτη!)
        for pat in [r'[Aa]vg[Ss]al[Cc]us\s+([\d.,]+)',
                    r'AvgSalCus\s+([\d.,]+)']:
            m = re.search(pat, txt)
            if m:
                try:
                    v = parse_num(m.group(1))
                    if 5 <= v <= 500: r["avg_basket"] = v; break
                except: pass

    except: pass
    return r

# ── EMAIL FETCH ────────────────────────────────────────────────────────────────
def email_preview(pw: str) -> tuple:
    """5 emails χωρίς OCR — μόνο για έλεγχο σύνδεσης."""
    rows, errs = [], []
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            for msg in mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                limit=5, reverse=True, mark_seen=False):
                atts = [a.filename for a in msg.attachments if a.filename] or ["—"]
                rows.append({"Ημερομηνία": msg.date.strftime("%d/%m/%Y %H:%M") if msg.date else "—",
                             "Θέμα": (msg.subject or "")[:55],
                             "PDF": atts[0]})
    except Exception as e: errs.append(str(e))
    return rows, errs

def fetch_days(pw: str, days: int) -> tuple:
    """OCR emails των τελευταίων N ημερών."""
    since = date.today() - timedelta(days=days)
    recs, errs, n = [], [], 0
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            for msg in mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                limit=days+15, reverse=True, mark_seen=False):
                d = msg.date.date() if msg.date else None
                if d and d < since: continue
                s = (msg.subject or "").upper()
                if SALES_SUBJECT_KW not in s and "SKYROS" not in s: continue
                pdf = next((a for a in msg.attachments
                            if a.filename and a.filename.lower().endswith(".pdf")), None)
                if not pdf: continue
                n += 1
                rec = extract_pdf(pdf.payload)
                if rec["date"] and rec["net_sales"] is not None:
                    recs.append(rec)
    except Exception as e: errs.append(str(e))
    return recs, errs, n

def fetch_since_last(pw: str) -> tuple:
    """OCR emails από την τελευταία αποθηκευμένη ημερομηνία."""
    ld = last_date()
    if ld is None: return fetch_days(pw, 7)
    since = ld - timedelta(days=3)
    recs, errs, n = [], [], 0
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            for msg in mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                limit=60, reverse=True, mark_seen=False):
                d = msg.date.date() if msg.date else None
                if d and d < since: continue
                s = (msg.subject or "").upper()
                if SALES_SUBJECT_KW not in s and "SKYROS" not in s: continue
                pdf = next((a for a in msg.attachments
                            if a.filename and a.filename.lower().endswith(".pdf")), None)
                if not pdf: continue
                n += 1
                rec = extract_pdf(pdf.payload)
                if rec["date"] and rec["net_sales"] is not None:
                    recs.append(rec)
    except Exception as e: errs.append(str(e))
    return recs, errs, n

def deep_scan(pw: str):
    """Generator — βαθιά σάρωση 2 ετών με batch αποθήκευση."""
    cutoff = date.today() - timedelta(days=365*DEEP_SCAN_YEARS)
    st_ = {"phase":"connect","total":0,"done":0,"saved":0,"cur":"","err":None,"ok":False}
    yield st_.copy()
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            st_["phase"] = "listing"; yield st_.copy()

            # headers only — γρήγορο
            all_h = list(mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                  limit=3000, reverse=True, mark_seen=False,
                                  headers_only=True))
            to_do = []
            for h in all_h:
                d = h.date.date() if h.date else None
                if not d or d < cutoff: continue
                s = (h.subject or "").upper()
                if SALES_SUBJECT_KW not in s and "SKYROS" not in s: continue
                to_do.append(h)

            st_["total"] = len(to_do)
            st_["phase"] = "ocr"; yield st_.copy()

            if not to_do:
                st_["ok"] = True; yield st_.copy(); return

            batch = []
            for i, h in enumerate(to_do):
                st_["done"] = i+1
                st_["cur"]  = (h.subject or "")[:45]
                yield st_.copy()
                try:
                    full = list(mb.fetch(AND(uid=str(h.uid)), mark_seen=False))
                    if not full: continue
                    pdf = next((a for a in full[0].attachments
                                if a.filename and a.filename.lower().endswith(".pdf")), None)
                    if not pdf: continue
                    rec = extract_pdf(pdf.payload)
                    if rec["date"] and rec["net_sales"] is not None:
                        batch.append(rec)
                    if len(batch) >= BATCH_SAVE_EVERY:
                        saved = merge_records(batch)
                        st_["saved"] += saved
                        batch = []
                        yield st_.copy()
                except: continue

            if batch:
                st_["saved"] += merge_records(batch)

            st_["ok"] = True; yield st_.copy()

    except Exception as e:
        st_["err"] = str(e); st_["ok"] = True; yield st_.copy()

# ── AUTO-UPDATE on page load ───────────────────────────────────────────────────
def try_auto_update(pw: str) -> str:
    """
    Εκτελείται αυτόματα κάθε φορά που φορτώνει η σελίδα.
    Φέρνει μόνο τα νέα emails (από την τελευταία ημερομηνία).
    Γρήγορο — δεν εμποδίζει τη φόρτωση.
    """
    if not pw: return "no_pw"
    ld = last_date()
    if ld and ld >= date.today(): return "up_to_date"
    try:
        recs, errs, n = fetch_since_last(pw)
        if errs: return f"error: {errs[0]}"
        if recs:
            saved = merge_records(recs)
            return f"updated:{saved}"
        return "no_new"
    except Exception as e:
        return f"error: {e}"

# ── DATA ─────────────────────────────────────────────────────────────────────
today      = date.today()
week_start = today - timedelta(days=today.weekday())
week_end   = week_start + timedelta(days=6)
week_lbl   = f"{week_start.strftime('%d/%m')} – {week_end.strftime('%d/%m')}"

# ── AUTO-UPDATE (σιωπηλά στο background) ─────────────────────────────────────
if "auto_done" not in st.session_state:
    st.session_state.auto_done = False
    st.session_state.auto_result = ""

if not st.session_state.auto_done and _PW:
    with st.spinner("🔄 Αυτόματη ενημέρωση..."):
        result = try_auto_update(_PW)
        st.session_state.auto_done   = True
        st.session_state.auto_result = result

df = load_all()
ld = last_date()

# ── HEADER ───────────────────────────────────────────────────────────────────
col_t, col_b = st.columns([5,1])
with col_t:
    st.markdown('<div class="page-title">📊 Πωλήσεις Καταστήματος</div>', unsafe_allow_html=True)
with col_b:
    st.markdown('<div class="btn-back">', unsafe_allow_html=True)
    if st.button("← Αρχική", key="back"):
        st.switch_page("Home.py")
    st.markdown("</div>", unsafe_allow_html=True)

# Auto-update status banner
ar = st.session_state.auto_result
if ar.startswith("updated:"):
    n = ar.split(":")[1]
    st.markdown(f'<div class="auto-banner"><div class="auto-ico">✅</div><div><div class="auto-text">Αυτόματη ενημέρωση — {n} νέες εγγραφές προστέθηκαν</div><div class="auto-sub">Τελευταία: {ld.strftime("%d/%m/%Y") if ld else "—"}</div></div></div>', unsafe_allow_html=True)
elif ar == "up_to_date":
    st.markdown(f'<div class="auto-banner"><div class="auto-ico">✅</div><div><div class="auto-text">Ενημερωμένο — δεν υπάρχουν νέα δεδομένα</div><div class="auto-sub">Τελευταία: {ld.strftime("%d/%m/%Y") if ld else "—"}</div></div></div>', unsafe_allow_html=True)
elif ar == "no_new":
    st.markdown(f'<div class="auto-banner"><div class="auto-ico">✅</div><div><div class="auto-text">Ενημερωμένο</div><div class="auto-sub">Τελευταία: {ld.strftime("%d/%m/%Y") if ld else "—"}</div></div></div>', unsafe_allow_html=True)
elif ar == "no_pw":
    st.markdown('<div class="wbox">⚠️ Δεν βρέθηκε App Password στα Secrets — η αυτόματη ενημέρωση δεν λειτουργεί.</div>', unsafe_allow_html=True)

# ── ΙΣΤΟΡΙΚΟ + ΕΝΗΜΕΡΩΣΗ ─────────────────────────────────────────────────────
st.markdown('<div class="sh">Ιστορικό Πωλήσεων</div>', unsafe_allow_html=True)

# ── Φίλτρα + κουμπιά ────────────────────────────────────────────────────────
fc1, fc2, fc3, fc4, fc5 = st.columns([2,2,1,1,1])
with fc1:
    years = sorted({r.year for r in df["date"]}, reverse=True) if not df.empty else [today.year]
    sel_y = st.selectbox("Έτος", years, key="sel_y")
with fc2:
    sel_m = st.selectbox("Μήνας", range(1,13), format_func=lambda x: MN[x-1],
                         index=today.month-1, key="sel_m")
with fc3:
    st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
    btn_refresh = st.button("🔄 Ενημέρωση", use_container_width=True, key="btn_refresh",
                            help="Φέρνει νέα emails από την τελευταία αποθηκευμένη ημερομηνία")
    st.markdown("</div>", unsafe_allow_html=True)
with fc4:
    st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
    btn_5d = st.button("📅 5 Μέρες", use_container_width=True, key="btn_5d",
                       help="OCR τελευταίων 5 ημερών")
    st.markdown("</div>", unsafe_allow_html=True)
with fc5:
    st.markdown('<div class="btn-deep">', unsafe_allow_html=True)
    btn_deep = st.button("🔍 2 Χρόνια", use_container_width=True, key="btn_deep",
                         help="Βαθιά σάρωση — αργεί, μείνετε στη σελίδα")
    st.markdown("</div>", unsafe_allow_html=True)

# Password field (μόνο αν δεν υπάρχει στα secrets)
pw = _PW
if not _PW:
    pw = st.text_input("🔐 App Password (ftoulisgm@gmail.com)", type="password", key="manual_pw")

# ── Ενέργειες κουμπιών ──────────────────────────────────────────────────────
if btn_refresh or btn_5d or btn_deep:
    if not pw:
        st.markdown('<div class="wbox">⚠️ Εισάγετε App Password.</div>', unsafe_allow_html=True)
    elif btn_refresh:
        ld_info = ld.strftime("%d/%m/%Y") if ld else "—"
        with st.spinner(f"Ενημέρωση από {ld_info}..."):
            recs, errs, n = fetch_since_last(pw)
        if errs: st.error(f"❌ {errs[0]}")
        else:
            saved = merge_records(recs)
            if saved:
                st.success(f"✅ {saved} νέες εγγραφές!")
                st.session_state.auto_done = False  # reset για επανέλεγχο
                st.rerun()
            else:
                st.markdown('<div class="ibox">✅ Δεν υπάρχουν νέα δεδομένα.</div>', unsafe_allow_html=True)
    elif btn_5d:
        with st.spinner("OCR τελευταίων 5 ημερών..."):
            recs, errs, n = fetch_days(pw, 5)
        if errs: st.error(f"❌ {errs[0]}")
        else:
            saved = merge_records(recs)
            if saved:
                st.success(f"✅ {saved} εγγραφές αποθηκεύτηκαν!")
                st.rerun()
            else:
                st.markdown('<div class="ibox">Δεν βρέθηκαν νέα δεδομένα τις τελευταίες 5 μέρες.</div>', unsafe_allow_html=True)
    elif btn_deep:
        st.markdown('<div class="wbox">⏳ Βαθιά σάρωση — <b>μείνετε στη σελίδα</b>. Αποθήκευση κάθε 25 records.</div>', unsafe_allow_html=True)
        prog = st.progress(0)
        info = st.empty()
        for s in deep_scan(pw):
            if s["err"]: st.error(f"❌ {s['err']}"); break
            if s["phase"] == "connect": info.markdown("🔌 Σύνδεση...")
            elif s["phase"] == "listing": info.markdown("📋 Ανάκτηση λίστας...")
            elif s["phase"] == "ocr":
                t = s["total"]; d = s["done"]
                if t > 0: prog.progress(int(d/t*100))
                info.markdown(f"🔍 **{d}/{t}** | 💾 {s['saved']} αποθηκεύτηκαν | _{s['cur']}_")
            if s["ok"]:
                prog.progress(100)
                info.markdown(f"✅ Ολοκλήρωση — **{s['saved']}** εγγραφές αποθηκεύτηκαν")
                st.success(f"🎉 Βαθιά σάρωση ολοκληρώθηκε! {s['total']} emails → {s['saved']} εγγραφές.")
                break
        df = load_all()

# ── Φιλτράρισμα & εμφάνιση ─────────────────────────────────────────────────
if df.empty:
    st.markdown('<div class="wbox">⚠️ Δεν υπάρχουν δεδομένα. Πατήστε <b>5 Μέρες</b> για πρώτη φόρτωση.</div>', unsafe_allow_html=True)
else:
    filt = df[(df["date"].apply(lambda d: d.year) == sel_y) &
              (df["date"].apply(lambda d: d.month) == sel_m)].copy()

    # ── KPIs μήνα ────────────────────────────────────────────────────────────
    if not filt.empty:
        tot  = filt["net_sales"].sum()
        avg  = filt["net_sales"].mean()
        best = filt["net_sales"].max()
        days = len(filt)

        # Σύγκριση με προηγούμενο μήνα
        pm = sel_m - 1 if sel_m > 1 else 12
        py = sel_y if sel_m > 1 else sel_y - 1
        pm_df = df[(df["date"].apply(lambda d:d.year)==py) &
                   (df["date"].apply(lambda d:d.month)==pm)]
        pm_tot = pm_df["net_sales"].sum() if not pm_df.empty else None

        def dlt(now, pv):
            if not pv or pv==0: return ""
            d = now-pv; p = d/pv*100
            return f'<div class="kdelta {"up" if d>=0 else "dn"}>{"▲" if d>=0 else "▼"} {abs(p):.1f}%</div>'

        st.markdown(f"""<div class="kr kr4">
          <div class="kc" style="--a:#48bb78"><div class="kl">Σύνολο {MN[sel_m-1]}</div>
            <div class="kv kv-g">{fmt(tot)}</div>{dlt(tot,pm_tot)}</div>
          <div class="kc" style="--a:#3182ce"><div class="kl">Ημερήσιος ΜΟ</div>
            <div class="kv">{fmt(avg)}</div></div>
          <div class="kc" style="--a:#805ad5"><div class="kl">Καλύτερη Μέρα</div>
            <div class="kv">{fmt(best)}</div></div>
          <div class="kc" style="--a:#dd6b20"><div class="kl">Ημέρες</div>
            <div class="kv">{days}</div></div>
        </div>""", unsafe_allow_html=True)

        # ── Εβδομαδιαίο σύνολο (αν ο μήνας = τρέχων) ───────────────────────
        if sel_m == today.month and sel_y == today.year:
            w_df  = filt[(filt["date"] >= week_start) & (filt["date"] <= today)]
            w_tot = w_df["net_sales"].sum() if not w_df.empty else 0
            pw_s  = week_start - timedelta(days=7)
            pw_df = df[(df["date"]>=pw_s)&(df["date"]<week_start)]
            pw_t  = pw_df["net_sales"].sum() if not pw_df.empty else None
            st.markdown(f"""<div class="kr" style="grid-template-columns:1fr 1fr 1fr;margin-top:.3rem;">
              <div class="kc" style="--a:#48bb78"><div class="kl">📅 Εβδ. {week_lbl}</div>
                <div class="kv kv-g">{fmt(w_tot)}</div>{dlt(w_tot,pw_t)}</div>
              <div class="kc" style="--a:#3182ce"><div class="kl">Ημέρες εβδ.</div>
                <div class="kv">{len(w_df)} / 7</div></div>
              <div class="kc" style="--a:#805ad5"><div class="kl">ΜΟ εβδ.</div>
                <div class="kv">{fmt(w_df["net_sales"].mean()) if not w_df.empty else "—"}</div></div>
            </div>""", unsafe_allow_html=True)

        # ── Πίνακας ──────────────────────────────────────────────────────────
        disp = filt.copy()
        disp["date"] = disp["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
        disp.columns = ["Ημερομηνία","Καθαρές Πωλήσεις","Πελάτες","ΜΟ Καλαθιού"]
        st.dataframe(disp, use_container_width=True, hide_index=True)

        csv = filt.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 Λήψη CSV", csv, f"sales_{sel_y}_{sel_m:02d}.csv", "text/csv")
    else:
        st.markdown('<div class="wbox">Δεν υπάρχουν δεδομένα για αυτή την περίοδο.</div>', unsafe_allow_html=True)

    # ── Γράφημα τελευταίων 30 ημερών ─────────────────────────────────────────
    st.markdown('<div class="sh">Τελευταίες 30 Ημέρες</div>', unsafe_allow_html=True)
    ch = df[df["date"] >= (today-timedelta(days=29))].sort_values("date").copy()
    if not ch.empty:
        ch.index = ch["date"].apply(lambda d: d.strftime("%d/%m"))
        st.bar_chart(ch["net_sales"], color="#48bb78", height=200)
