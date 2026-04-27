import streamlit as st
import pandas as pd
import os, re
from datetime import datetime, date, timedelta
from imap_tools import MailBox, AND
from pdf2image import convert_from_bytes
import pytesseract

st.set_page_config(
    page_title="Πωλήσεις — AB Skyros",
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
BATCH_SIZE         = 25

_PW = ""
try: _PW = st.secrets.get("SALES_EMAIL_PASS", "")
except: pass

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

:root {
  --bg:#0f1117; --surface:#181c24; --border:#2a2f3d;
  --muted:#4a5268; --dim:#8892a4; --text:#e8eaf0;
  --green:#22c55e; --blue:#3b82f6; --amber:#f59e0b; --red:#ef4444;
  --mono:'IBM Plex Mono',monospace; --sans:'IBM Plex Sans',sans-serif;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html,body,[class*="css"]{font-family:var(--sans)!important;background:var(--bg)!important;color:var(--text)!important;}
.stApp{background:var(--bg)!important;}
section[data-testid="stSidebar"]{display:none!important;}
#MainMenu,footer,header{visibility:hidden!important;}
.block-container{padding:1.5rem 1.5rem 4rem!important;max-width:900px!important;margin:0 auto!important;}

.topbar{display:flex;justify-content:space-between;align-items:center;
  padding-bottom:.9rem;border-bottom:1px solid var(--border);margin-bottom:1.4rem;}
.page-title{font-family:var(--mono);font-size:1rem;font-weight:600;
  letter-spacing:.04em;color:var(--text);}
.page-meta{font-family:var(--mono);font-size:.6rem;color:var(--muted);text-align:right;line-height:1.7;}

/* KPI GRID */
.kg{display:grid;gap:1px;background:var(--border);border:1px solid var(--border);
  border-radius:5px;overflow:hidden;margin:.4rem 0 1.2rem;}
.kg4{grid-template-columns:repeat(4,1fr);}
.kg3{grid-template-columns:repeat(3,1fr);}
@media(max-width:760px){.kg4{grid-template-columns:repeat(2,1fr);}}
@media(max-width:460px){.kg4,.kg3{grid-template-columns:1fr;}}
.kc{background:var(--surface);padding:.8rem 1rem;}
.kl{font-size:.52rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted);margin-bottom:.3rem;}
.kv{font-family:var(--mono);font-size:.95rem;font-weight:500;color:var(--text);}
.kv.g{color:var(--green);} .kv.sm{font-size:.78rem;}
.kdelta{font-family:var(--mono);font-size:.58rem;margin-top:.15rem;}
.up{color:var(--green);} .dn{color:var(--red);}

/* TABLE */
[data-testid="stDataFrame"]{border:1px solid var(--border)!important;border-radius:5px!important;}

/* STATUS */
.sbar{border:1px solid var(--bc,var(--border));border-left:3px solid var(--bc,var(--border));
  background:var(--surface);padding:.6rem .9rem;margin:.4rem 0;
  font-family:var(--mono);font-size:.68rem;color:var(--text);}
.sbar-g{--bc:var(--green);}
.sbar-a{--bc:var(--amber);color:var(--amber);}
.sbar-r{--bc:var(--red);color:var(--red);}
.sbar-d{--bc:var(--muted);color:var(--dim);}
.sl{font-size:.52rem;font-weight:600;letter-spacing:.12em;
  text-transform:uppercase;color:var(--dim);display:block;margin-bottom:.15rem;}

/* BUTTONS */
.stButton>button{border-radius:4px!important;font-family:var(--mono)!important;
  font-size:.7rem!important;font-weight:600!important;letter-spacing:.04em!important;
  padding:.55rem .9rem!important;transition:all .12s!important;}
.btn-p>button{background:rgba(34,197,94,.1)!important;border:1px solid rgba(34,197,94,.3)!important;color:var(--green)!important;}
.btn-p>button:hover{background:rgba(34,197,94,.2)!important;}
.btn-o>button{background:var(--surface)!important;border:1px solid var(--border)!important;color:var(--dim)!important;}
.btn-o>button:hover{border-color:var(--dim)!important;color:var(--text)!important;}
.btn-d>button{background:rgba(245,158,11,.08)!important;border:1px solid rgba(245,158,11,.25)!important;color:var(--amber)!important;}
.btn-back>button{background:transparent!important;border:1px solid var(--border)!important;color:var(--muted)!important;}

/* SECTION */
.sh{font-size:.52rem;font-weight:600;letter-spacing:.18em;text-transform:uppercase;
  color:var(--muted);padding-bottom:.4rem;border-bottom:1px solid var(--border);margin:1.4rem 0 .8rem;}

/* PROGRESS */
.prog-wrap{background:var(--surface);border:1px solid var(--border);border-radius:5px;
  padding:1rem;margin:.5rem 0;}
.prog-title{font-family:var(--mono);font-size:.68rem;color:var(--text);margin-bottom:.5rem;}
.prog-sub{font-family:var(--mono);font-size:.58rem;color:var(--dim);margin-top:.4rem;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}

@media(max-width:600px){.block-container{padding:1rem 1rem 3rem!important;}
  .topbar{flex-direction:column;align-items:flex-start;gap:.4rem;}}
</style>
""", unsafe_allow_html=True)

MN = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]
MNF = ["Ιανουαρίου","Φεβρουαρίου","Μαρτίου","Απριλίου","Μαΐου","Ιουνίου",
       "Ιουλίου","Αυγούστου","Σεπτεμβρίου","Οκτωβρίου","Νοεμβρίου","Δεκεμβρίου"]

def fmt(v):
    if v is None or (isinstance(v,float) and pd.isna(v)): return "—"
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

# ── CACHE ─────────────────────────────────────────────────────────────────────
def _dedup(df):
    if df.empty: return df
    return (df.sort_values("net_sales",ascending=False)
              .drop_duplicates("date",keep="first")
              .sort_values("date",ascending=False)
              .reset_index(drop=True))

def load_cache():
    if os.path.exists(SALES_CACHE):
        try:
            df = pd.read_csv(SALES_CACHE)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"]).dt.date
                return _dedup(df)
        except: pass
    return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])

def load_all():
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

def save_split(df):
    df = _dedup(df)
    cut = date.today() - timedelta(days=365*DEEP_SCAN_YEARS)
    recent = df[df["date"] >= cut].copy()
    old    = df[df["date"]  < cut].copy()
    recent.to_csv(SALES_CACHE, index=False)
    if not old.empty:
        if os.path.exists(SALES_ARCHIVE):
            try:
                ex = pd.read_csv(SALES_ARCHIVE)
                ex["date"] = pd.to_datetime(ex["date"]).dt.date
                old = _dedup(pd.concat([ex, old], ignore_index=True))
            except: pass
        old.to_csv(SALES_ARCHIVE, index=False)

def merge_in(recs: list) -> int:
    if not recs: return 0
    ndf = _dedup(pd.DataFrame(recs))
    old = load_cache()
    add = []; n = 0
    for _, r in ndf.iterrows():
        ex = old[old["date"] == r["date"]]
        if ex.empty:
            add.append(r); n += 1
        elif r["net_sales"] > ex.iloc[0]["net_sales"]:
            old = old[old["date"] != r["date"]]
            add.append(r); n += 1
    if add:
        save_split(_dedup(pd.concat([old, pd.DataFrame(add)], ignore_index=True)))
    return n

def last_dt():
    df = load_cache()
    return df["date"].max() if not df.empty else None

# ── OCR  ──────────────────────────────────────────────────────────────────────
def _num(s: str) -> float:
    """European/Greek number format: 9.176,63 → 9176.63"""
    s = s.strip().replace(" ","").replace("€","")
    if "." in s and "," in s:   # 9.176,63
        s = s.replace(".","").replace(",",".")
    elif "," in s:               # 9176,63
        s = s.replace(",",".")
    return float(s)

def _find(txt: str, patterns: list, lo=None, hi=None):
    """Try each regex pattern; return first valid match."""
    for pat in patterns:
        m = re.search(pat, txt, re.IGNORECASE)
        if m:
            try:
                v = _num(m.group(1))
                if lo is not None and v < lo: continue
                if hi is not None and v > hi: continue
                return v
            except: continue
    return None

def extract(pdf_bytes: bytes) -> dict:
    """
    Fast, accurate OCR from AB Skyros Department Report PDF.
    Strategy:
      1. Convert PDF → images (200dpi, first 3 pages only)
      2. Run Tesseract with Greek+English on EACH page separately
      3. Use specific patterns per field — bail out as soon as found
      4. Sanity-check every value before accepting
    
    Fields:
      date       → "For DD/MM/YYYY" header
      net_sales  → NeitDaySalDis  (1000–50000)
      customers  → NumOfCus       (10–2000)
      avg_basket → AvgSalCus      (5–500)
    """
    r = {"date":None,"net_sales":None,"customers":None,"avg_basket":None}
    try:
        # Only first 3 pages — header fields are always there
        images = convert_from_bytes(pdf_bytes, dpi=200, first_page=1, last_page=3)
        pages  = [pytesseract.image_to_string(img, lang="ell+eng",
                    config="--psm 6 --oem 3") for img in images]
        txt = "\n".join(pages)

        # ── DATE ────────────────────────────────────────────────────────────
        for pat in [
            r'[Ff]or\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'[Ff]or\s*[:\-]?\s*(\d{1,2}\.\d{1,2}\.\d{4})',
            r'(?:For|FOR)\s+(\d{2}/\d{2}/\d{4})',
        ]:
            m = re.search(pat, txt)
            if m:
                try:
                    r["date"] = datetime.strptime(
                        m.group(1).replace(".","/"), "%d/%m/%Y"
                    ).date()
                    break
                except: pass

        # ── NET SALES: NeitDaySalDis ────────────────────────────────────────
        # Various OCR misreadings: NeitDaySalDis / NetDaySalDis / NeitDaySalDls
        r["net_sales"] = _find(txt, [
            r'Ne[i1]tDay[Ss]al[Dd][i1][s5]\s+([\d.,]+)',
            r'NetDay[Ss]al[Dd]is\s+([\d.,]+)',
            r'Ne[i1][t7]Day.{0,3}al.{0,3}[i1][s5]\s+([\d.,]+)',
        ], lo=1000, hi=50000)

        # Fallback: GroupTot / RepTot last number
        if r["net_sales"] is None:
            m = re.search(r'[Gg]roup[Tt]ot\s+([\d.,]+)\s+([\d.,]+)', txt)
            if m:
                try:
                    v = _num(m.group(2))
                    if 1000 <= v <= 50000: r["net_sales"] = v
                except: pass

        # Fallback: Hourly Totals line: "9176.63   100.00   282"
        if r["net_sales"] is None:
            m = re.search(r'[Tt]otals?\s*:?\s*([\d.,]+)\s+100[.,]00\s+([\d]+)', txt)
            if m:
                try:
                    v = _num(m.group(1))
                    if 1000 <= v <= 50000:
                        r["net_sales"] = v
                        cv = int(m.group(2))
                        if r["customers"] is None and 10 <= cv <= 2000:
                            r["customers"] = cv
                except: pass

        # ── CUSTOMERS: NumOfCus ──────────────────────────────────────────────
        # NumOfCus = πελάτες (ΟΧΙ NumItmSold = αντικείμενα!)
        if r["customers"] is None:
            for pat in [
                r'Num[O0]fCus\s+([\d,. ]+)',
                r'Num[O0]f[Cc]us\s+([\d,. ]+)',
                r'Num0fCus\s+([\d,. ]+)',
            ]:
                m = re.search(pat, txt, re.IGNORECASE)
                if m:
                    try:
                        v = int(m.group(1).replace(",","").replace(".","").replace(" ",""))
                        if 10 <= v <= 2000: r["customers"] = v; break
                    except: pass

        # ── AVG BASKET: AvgSalCus ────────────────────────────────────────────
        # AvgSalCus = € ανά πελάτη (ΟΧΙ AvgItmPerCus = items/πελάτη!)
        r["avg_basket"] = _find(txt, [
            r'Avg[Ss]al[Cc]us\s+([\d.,]+)',
            r'AvgSal[Cc]us\s+([\d.,]+)',
        ], lo=5, hi=500)

    except Exception:
        pass  # silent — caller handles None values
    return r

# ── EMAIL ─────────────────────────────────────────────────────────────────────
def _is_valid(subj):
    s = (subj or "").upper()
    return SALES_SUBJECT_KW in s or "SKYROS" in s

def preview(pw):
    rows, errs = [], []
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            for msg in mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                limit=5, reverse=True, mark_seen=False):
                att = [a.filename for a in msg.attachments if a.filename] or ["—"]
                rows.append({
                    "Ημερομηνία": msg.date.strftime("%d/%m/%Y %H:%M") if msg.date else "—",
                    "Θέμα": (msg.subject or "")[:50],
                    "PDF": att[0]
                })
    except Exception as e: errs.append(str(e))
    return rows, errs

def fetch(pw, since: date | None = None, limit: int = 60):
    recs, errs, n = [], [], 0
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            for msg in mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                limit=limit, reverse=True, mark_seen=False):
                d = msg.date.date() if msg.date else None
                if since and d and d < since: continue
                if not _is_valid(msg.subject): continue
                pdf = next((a for a in msg.attachments
                            if a.filename and a.filename.lower().endswith(".pdf")), None)
                if not pdf: continue
                n += 1
                rec = extract(pdf.payload)
                if rec["date"] and rec["net_sales"] is not None:
                    recs.append(rec)
    except Exception as e: errs.append(str(e))
    return recs, errs, n

def deep_scan(pw):
    """
    Generator — βαθιά σάρωση 2 ετών.
    Αποθηκεύει κάθε BATCH_SIZE records.
    Δεν σβήνει ποτέ — χρησιμοποιεί st.session_state για persistence.
    """
    cutoff = date.today() - timedelta(days=365*DEEP_SCAN_YEARS)
    s = {"phase":"connect","total":0,"done":0,"saved":0,"cur":"","err":None,"ok":False}
    yield s.copy()
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            s["phase"] = "listing"; yield s.copy()

            # Φάση 1: headers only (instant)
            hdrs = [h for h in mb.fetch(
                        AND(from_=SALES_EMAIL_SENDER),
                        limit=3000, reverse=True, mark_seen=False, headers_only=True)
                    if h.date and h.date.date() >= cutoff and _is_valid(h.subject)]

            s["total"] = len(hdrs); s["phase"] = "ocr"; yield s.copy()
            if not hdrs: s["ok"] = True; yield s.copy(); return

            batch = []
            for i, h in enumerate(hdrs):
                s["done"] = i+1
                s["cur"]  = (h.subject or "")[:50]
                yield s.copy()
                try:
                    full = list(mb.fetch(AND(uid=str(h.uid)), mark_seen=False))
                    if not full: continue
                    pdf = next((a for a in full[0].attachments
                                if a.filename and a.filename.lower().endswith(".pdf")), None)
                    if not pdf: continue
                    rec = extract(pdf.payload)
                    if rec["date"] and rec["net_sales"] is not None:
                        batch.append(rec)
                    # Αποθήκευση κάθε BATCH_SIZE
                    if len(batch) >= BATCH_SIZE:
                        s["saved"] += merge_in(batch); batch = []; yield s.copy()
                except: continue

            if batch: s["saved"] += merge_in(batch)
            s["ok"] = True; yield s.copy()
    except Exception as e:
        s["err"] = str(e); s["ok"] = True; yield s.copy()

def auto_update(pw):
    if not pw: return "no_pw"
    ld = last_dt()
    if ld and ld >= date.today(): return "fresh"
    since = (ld - timedelta(days=3)) if ld else (date.today()-timedelta(days=7))
    try:
        recs, errs, n = fetch(pw, since=since, limit=60)
        if errs: return f"err:{errs[0]}"
        saved = merge_in(recs)
        return f"ok:{saved}"
    except Exception as e: return f"err:{e}"

# ── STATE ─────────────────────────────────────────────────────────────────────
today = date.today()
ws    = today - timedelta(days=today.weekday())
we    = ws + timedelta(days=6)
wlbl  = f"{ws.strftime('%d/%m')}–{we.strftime('%d/%m')}"

# Auto-update: runs ONCE per session, silently, only if PW exists
if "auto_done" not in st.session_state:
    st.session_state.auto_done   = False
    st.session_state.auto_result = ""
    st.session_state.auto_ran    = False

# Run auto-update after first render (not during initial load)
if not st.session_state.auto_ran and _PW:
    st.session_state.auto_ran = True
    ld_check = last_dt()
    # Only auto-update if data is stale (not today)
    if ld_check is None or ld_check < date.today():
        try:
            since = (ld_check - timedelta(days=3)) if ld_check else (date.today()-timedelta(days=7))
            recs, errs, n = fetch(_PW, since=since, limit=30)
            if not errs:
                saved = merge_in(recs)
                st.session_state.auto_result = f"ok:{saved}"
            else:
                st.session_state.auto_result = f"err:{errs[0]}"
        except Exception as e:
            st.session_state.auto_result = f"err:{e}"
    else:
        st.session_state.auto_result = "fresh"
    st.session_state.auto_done = True

# Keep deep scan state alive across reruns
if "deep_running" not in st.session_state:
    st.session_state.deep_running = False

df  = load_all()
ld  = last_dt()
lds = ld.strftime("%d/%m/%Y") if ld else "—"

# ── HEADER ───────────────────────────────────────────────────────────────────
c_t, c_b = st.columns([6,1])
with c_t:
    st.markdown(f"""
    <div class="topbar">
      <div class="page-title">ΠΩΛΗΣΕΙΣ ΚΑΤΑΣΤΗΜΑΤΟΣ</div>
      <div class="page-meta">Τελευταία: {lds}<br>Εγγραφές: {len(df)}</div>
    </div>""", unsafe_allow_html=True)
with c_b:
    st.markdown('<div class="btn-back">', unsafe_allow_html=True)
    if st.button("Αρχική", key="back"): st.switch_page("Home.py")
    st.markdown("</div>", unsafe_allow_html=True)

# Auto-update banner
ar = st.session_state.auto_result
if ar.startswith("ok:"):
    n = ar.split(":")[1]
    msg_txt = f"Αυτόματη ενημέρωση — {n} νέες εγγραφές" if n!="0" else "Ενημερωμένο"
    st.markdown(f'<div class="sbar sbar-g"><span class="sl">AUTO UPDATE</span>{msg_txt}</div>', unsafe_allow_html=True)
elif ar == "fresh":
    st.markdown(f'<div class="sbar sbar-d"><span class="sl">STATUS</span>Ενημερωμένο · {lds}</div>', unsafe_allow_html=True)
elif ar == "no_pw":
    st.markdown('<div class="sbar sbar-a"><span class="sl">ΠΡΟΣΟΧΗ</span>App Password δεν βρέθηκε στα Secrets</div>', unsafe_allow_html=True)
elif ar.startswith("err:"):
    st.markdown(f'<div class="sbar sbar-r"><span class="sl">ΣΦΑΛΜΑ</span>{ar[4:]}</div>', unsafe_allow_html=True)

# ── FILTERS + ACTION BUTTONS ─────────────────────────────────────────────────
st.markdown('<div class="sh">ΙΣΤΟΡΙΚΟ ΠΩΛΗΣΕΩΝ</div>', unsafe_allow_html=True)

years = sorted({r.year for r in df["date"]}, reverse=True) if not df.empty else [today.year]
col_y, col_m, col_r, col_5, col_d = st.columns([1.8,2.2,1,1,1])

with col_y:
    sel_y = st.selectbox("", years, key="sy", label_visibility="collapsed")
with col_m:
    sel_m = st.selectbox("", range(1,13), format_func=lambda x: MNF[x-1],
                         index=today.month-1, key="sm", label_visibility="collapsed")
with col_r:
    st.markdown('<div class="btn-p">', unsafe_allow_html=True)
    btn_r = st.button("Ενημέρωση", use_container_width=True, key="br")
    st.markdown("</div>", unsafe_allow_html=True)
with col_5:
    st.markdown('<div class="btn-o">', unsafe_allow_html=True)
    btn_5 = st.button("5 Μέρες", use_container_width=True, key="b5")
    st.markdown("</div>", unsafe_allow_html=True)
with col_d:
    st.markdown('<div class="btn-d">', unsafe_allow_html=True)
    btn_d = st.button("2 Χρόνια", use_container_width=True, key="bd")
    st.markdown("</div>", unsafe_allow_html=True)

# Password input (only if not in secrets)
pw = _PW
if not _PW:
    pw = st.text_input("", placeholder="App Password — ftoulisgm@gmail.com",
                       type="password", key="mpw", label_visibility="collapsed")

# ── ACTIONS ───────────────────────────────────────────────────────────────────
if (btn_r or btn_5 or btn_d) and not pw:
    st.markdown('<div class="sbar sbar-a"><span class="sl">ΑΠΑΙΤΕΙΤΑΙ</span>Εισάγετε App Password</div>', unsafe_allow_html=True)

elif btn_r and pw:
    since = (ld - timedelta(days=3)) if ld else None
    with st.spinner("Ενημέρωση..."):
        recs, errs, n = fetch(pw, since=since)
    if errs:
        st.markdown(f'<div class="sbar sbar-r"><span class="sl">ΣΦΑΛΜΑ</span>{errs[0]}</div>', unsafe_allow_html=True)
    else:
        saved = merge_in(recs)
        cls   = "sbar-g" if saved else "sbar-d"
        msg   = f"{saved} νέες εγγραφές · {n} PDFs" if saved else f"Ενημερωμένο · {n} PDFs ελέγχθηκαν"
        st.markdown(f'<div class="sbar {cls}"><span class="sl">ΑΠΟΤΕΛΕΣΜΑ</span>{msg}</div>', unsafe_allow_html=True)
        if saved: st.session_state.auto_done = False; st.rerun()

elif btn_5 and pw:
    since5 = today - timedelta(days=5)
    with st.spinner("OCR 5 ημερών..."):
        recs, errs, n = fetch(pw, since=since5, limit=15)
    if errs:
        st.markdown(f'<div class="sbar sbar-r"><span class="sl">ΣΦΑΛΜΑ</span>{errs[0]}</div>', unsafe_allow_html=True)
    else:
        saved = merge_in(recs)
        cls   = "sbar-g" if saved else "sbar-d"
        msg   = f"{saved} εγγραφές αποθηκεύτηκαν · {n} PDFs" if saved else f"Δεν βρέθηκαν νέα · {n} PDFs"
        st.markdown(f'<div class="sbar {cls}"><span class="sl">5 ΜΕΡΕΣ</span>{msg}</div>', unsafe_allow_html=True)
        if saved: st.rerun()

elif btn_d and pw:
    # ── DEEP SCAN — δεν σβήνει ποτέ ─────────────────────────────────────────
    st.markdown('<div class="sbar sbar-a"><span class="sl">ΒΑΘΕΙΑ ΣΑΡΩΣΗ</span>Μείνετε στη σελίδα. Αποθήκευση κάθε 25 εγγραφές.</div>', unsafe_allow_html=True)

    prog_bar = st.progress(0)
    info_box = st.empty()

    for s in deep_scan(pw):
        if s["err"]:
            info_box.markdown(f'<div class="sbar sbar-r"><span class="sl">ΣΦΑΛΜΑ</span>{s["err"]}</div>', unsafe_allow_html=True)
            break

        ph = s["phase"]
        if ph == "connect":
            info_box.markdown('<div class="prog-wrap"><div class="prog-title">Σύνδεση στο email...</div></div>', unsafe_allow_html=True)
        elif ph == "listing":
            info_box.markdown('<div class="prog-wrap"><div class="prog-title">Ανάκτηση λίστας emails...</div></div>', unsafe_allow_html=True)
        elif ph == "ocr":
            t = s["total"]; d = s["done"]
            pct = int(d/t*100) if t else 0
            prog_bar.progress(pct)
            info_box.markdown(f"""
            <div class="prog-wrap">
              <div class="prog-title">{d} / {t} emails · {s['saved']} αποθηκεύτηκαν · {pct}%</div>
              <div class="prog-sub">{s['cur']}</div>
            </div>""", unsafe_allow_html=True)

        if s["ok"]:
            prog_bar.progress(100)
            info_box.markdown(f'<div class="sbar sbar-g"><span class="sl">ΟΛΟΚΛΗΡΩΣΗ</span>{s["total"]} emails → {s["saved"]} εγγραφές αποθηκεύτηκαν</div>', unsafe_allow_html=True)
            break

    df = load_all()

# ── TABLE ─────────────────────────────────────────────────────────────────────
if df.empty:
    st.markdown('<div class="sbar sbar-a"><span class="sl">ΧΩΡΙΣ ΔΕΔΟΜΕΝΑ</span>Πατήστε "5 Μέρες" για πρώτη φόρτωση.</div>', unsafe_allow_html=True)
else:
    filt = df[(df["date"].apply(lambda d:d.year)==sel_y) &
              (df["date"].apply(lambda d:d.month)==sel_m)].copy()

    if not filt.empty:
        tot = filt["net_sales"].sum(); avg = filt["net_sales"].mean()
        pm  = sel_m-1 if sel_m>1 else 12; py = sel_y if sel_m>1 else sel_y-1
        pmd = df[(df["date"].apply(lambda d:d.year)==py)&(df["date"].apply(lambda d:d.month)==pm)]
        pmt = pmd["net_sales"].sum() if not pmd.empty else None

        def dlt(now, pv):
            if not pv or pv==0: return ""
            d=now-pv; p=d/pv*100
            return f'<div class="kdelta {"up" if d>=0 else "dn"}">{"+" if d>=0 else ""}{p:.1f}%</div>'

        st.markdown(f"""<div class="kg kg4">
          <div class="kc"><div class="kl">Σύνολο {MN[sel_m-1]}</div>
            <div class="kv g">{fmt(tot)}</div>{dlt(tot,pmt)}</div>
          <div class="kc"><div class="kl">Ημερήσιος ΜΟ</div>
            <div class="kv">{fmt(avg)}</div></div>
          <div class="kc"><div class="kl">Καλύτερη μέρα</div>
            <div class="kv">{fmt(filt['net_sales'].max())}</div></div>
          <div class="kc"><div class="kl">Ημέρες</div>
            <div class="kv sm">{len(filt)}</div></div>
        </div>""", unsafe_allow_html=True)

        # Weekly block (only current month)
        if sel_m == today.month and sel_y == today.year:
            wd = filt[(filt["date"]>=ws)&(filt["date"]<=today)]
            wt = wd["net_sales"].sum() if not wd.empty else 0
            pw7s = ws-timedelta(days=7)
            pw7d = df[(df["date"]>=pw7s)&(df["date"]<ws)]
            pw7t = pw7d["net_sales"].sum() if not pw7d.empty else None
            st.markdown(f"""<div class="kg kg3">
              <div class="kc"><div class="kl">Εβδομάδα {wlbl}</div>
                <div class="kv g">{fmt(wt)}</div>{dlt(wt,pw7t)}</div>
              <div class="kc"><div class="kl">Ημέρες εβδ.</div>
                <div class="kv sm">{len(wd)} / 7</div></div>
              <div class="kc"><div class="kl">ΜΟ εβδ.</div>
                <div class="kv">{fmt(wd['net_sales'].mean()) if not wd.empty else '—'}</div></div>
            </div>""", unsafe_allow_html=True)

        disp = filt.copy()
        disp["date"] = disp["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
        disp.columns = ["Ημερομηνία","Καθαρές Πωλήσεις","Πελάτες","ΜΟ Καλαθιού"]
        st.dataframe(disp, use_container_width=True, hide_index=True)

        csv = filt.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Λήψη CSV", csv, f"sales_{sel_y}_{sel_m:02d}.csv", "text/csv")
    else:
        st.markdown('<div class="sbar sbar-d"><span class="sl">ΚΕΝΟ</span>Δεν υπάρχουν δεδομένα για αυτή την περίοδο.</div>', unsafe_allow_html=True)
