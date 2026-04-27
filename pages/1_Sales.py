import streamlit as st
import pandas as pd
import os, re, base64, io, json
from datetime import datetime, date, timedelta
from imap_tools import MailBox, AND
from pdf2image import convert_from_bytes
import anthropic

st.set_page_config(
    page_title="Πωλήσεις — AB Skyros 1082",
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

_PW = ""
try: _PW = st.secrets.get("SALES_EMAIL_PASS", "")
except: pass

_ANTHROPIC_KEY = ""
try: _ANTHROPIC_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
except: pass

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=Geist:wght@300;400;500;600&display=swap');

:root {
  --ink:    #0d0d0d;
  --paper:  #f5f3ef;
  --rule:   #d6d2ca;
  --muted:  #8a8680;
  --accent: #1a472a;
  --accent2:#2c5282;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
  font-family: 'Geist', sans-serif !important;
  background: var(--paper) !important;
  color: var(--ink) !important;
}
.stApp { background: var(--paper) !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container {
  padding: 2.5rem 2rem 6rem !important;
  max-width: 900px !important;
  margin: 0 auto !important;
}

.page-rule {
  border-top: 3px solid var(--ink);
  border-bottom: 1px solid var(--rule);
  padding: 1rem 0 .9rem;
  margin-bottom: 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-title {
  font-family: 'DM Serif Display', serif;
  font-size: 1.6rem;
  color: var(--ink);
  letter-spacing: -0.01em;
}
.page-meta {
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem;
  color: var(--muted);
  text-align: right;
  line-height: 1.6;
}

.sh {
  font-size: 0.57rem;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--muted);
  padding-bottom: 0.45rem;
  border-bottom: 1px solid var(--rule);
  margin: 2rem 0 1rem;
}

/* KPI GRID */
.kgrid { display: grid; gap: 0; margin: .5rem 0 1.5rem; }
.kg4 { grid-template-columns: repeat(4,1fr); }
.kg3 { grid-template-columns: repeat(3,1fr); }
.kg2 { grid-template-columns: repeat(2,1fr); }
@media(max-width:860px){ .kg4 { grid-template-columns: repeat(2,1fr); } }
@media(max-width:500px){ .kg4,.kg3,.kg2 { grid-template-columns: 1fr; } }

.kc {
  padding: 1rem 1.2rem;
  border: 1px solid var(--rule);
  border-right: none;
  background: #fff;
  position: relative;
}
.kc:last-child { border-right: 1px solid var(--rule); }
.kc::after {
  content: '';
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 2px;
  background: var(--akz, transparent);
}
.kl {
  font-size: 0.56rem;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 0.5rem;
}
.kv {
  font-family: 'DM Serif Display', serif;
  font-size: 1.15rem;
  color: var(--ink);
  line-height: 1;
}
.kv.pos { color: #1a472a; }
.kv.sm  { font-family: 'DM Mono', monospace; font-size: .85rem; }
.kdelta {
  font-family: 'DM Mono', monospace;
  font-size: 0.62rem;
  margin-top: 0.25rem;
}
.up { color: #1a472a; } .dn { color: #7f1d1d; }

/* TABLE */
[data-testid="stDataFrame"] {
  border: 1px solid var(--rule) !important;
  border-radius: 0 !important;
}

/* STATUS BANNER */
.status-bar {
  border: 1px solid var(--rule);
  border-left: 3px solid var(--lc, var(--rule));
  background: #fff;
  padding: .75rem 1rem;
  margin: .5rem 0 1rem;
  display: flex;
  align-items: center;
  gap: .75rem;
  font-size: .72rem;
  color: var(--ink);
}
.sb-green { --lc: #1a472a; }
.sb-amber { --lc: #92400e; }
.sb-gray  { --lc: var(--rule); color: var(--muted); }
.sb-red   { --lc: #7f1d1d; }
.sb-label { font-weight: 600; font-size: .58rem; letter-spacing: .14em; text-transform: uppercase; }

/* AI badge */
.ai-badge {
  display: inline-block;
  font-size: .55rem;
  font-weight: 600;
  letter-spacing: .14em;
  text-transform: uppercase;
  padding: .2rem .6rem;
  border: 1px solid var(--rule);
  color: var(--muted);
  background: #fff;
  margin-left: .5rem;
  vertical-align: middle;
}
.ai-badge.active { border-color: #1a472a; color: #1a472a; background: #f0fff4; }

/* BUTTONS */
.stButton > button {
  border-radius: 0 !important;
  font-family: 'Geist', sans-serif !important;
  font-size: .78rem !important;
  font-weight: 600 !important;
  letter-spacing: .04em !important;
  padding: .6rem 1.1rem !important;
  transition: all .12s !important;
}
.btn-primary > button {
  background: var(--ink) !important;
  border: 1px solid var(--ink) !important;
  color: var(--paper) !important;
}
.btn-primary > button:hover {
  background: var(--paper) !important;
  color: var(--ink) !important;
}
.btn-outline > button {
  background: #fff !important;
  border: 1px solid var(--rule) !important;
  color: var(--ink) !important;
}
.btn-outline > button:hover {
  border-color: var(--ink) !important;
}
.btn-ghost > button {
  background: transparent !important;
  border: 1px solid var(--rule) !important;
  color: var(--muted) !important;
}

@media(max-width:600px){
  .block-container { padding: 1.5rem 1rem 4rem !important; }
  .page-rule { flex-direction: column; align-items: flex-start; gap: .5rem; }
}
</style>
""", unsafe_allow_html=True)

MN = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]
MN_FULL = ["Ιανουαρίου","Φεβρουαρίου","Μαρτίου","Απριλίου","Μαΐου","Ιουνίου",
           "Ιουλίου","Αυγούστου","Σεπτεμβρίου","Οκτωβρίου","Νοεμβρίου","Δεκεμβρίου"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f} €".replace(",","X").replace(".",",").replace("X",".")

# ── CACHE ─────────────────────────────────────────────────────────────────────
def _dedup(df):
    if df.empty: return df
    return (df.sort_values("net_sales", ascending=False)
              .drop_duplicates("date", keep="first")
              .sort_values("date", ascending=False)
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
    return _dedup(pd.concat(parts, ignore_index=True)) if parts else pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])

def save_and_split(df):
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

def merge_records(new_recs):
    if not new_recs: return 0
    new_df = _dedup(pd.DataFrame(new_recs))
    old_df = load_cache()
    count = 0; to_add = []
    for _, row in new_df.iterrows():
        ex = old_df[old_df["date"] == row["date"]]
        if ex.empty:
            to_add.append(row); count += 1
        elif row["net_sales"] > ex.iloc[0]["net_sales"]:
            old_df = old_df[old_df["date"] != row["date"]]
            to_add.append(row); count += 1
    if to_add:
        save_and_split(_dedup(pd.concat([old_df, pd.DataFrame(to_add)], ignore_index=True)))
    return count

def last_date():
    df = load_cache()
    return df["date"].max() if not df.empty else None

# ── AI EXTRACTION (Claude Vision) ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are a precise data extraction engine for AB Skyros supermarket daily sales reports.
The PDF is a Department Report from a Greek supermarket POS system.
Extract ONLY these fields from the report header section:

- date: the "For" date (format DD/MM/YYYY)
- net_sales: NeitDaySalDis or NetDaySalDis value (net daily sales in euros)
- customers: NumOfCus value (number of customers, typically 50-800)
- avg_basket: AvgSalCus value (average sale per customer in euros, typically 10-150)

IMPORTANT RULES:
- NumOfCus = customers (NOT NumItmSold which is items count)
- AvgSalCus = avg basket in euros (NOT AvgItmPerCus which is items per customer)
- Numbers use European format: periods as thousands separator, comma as decimal (e.g. 9.176,63 = 9176.63)
- If a value is 0.00 or missing, return null
- Sanity checks: customers must be 10-2000, avg_basket must be 5-500, net_sales must be 1000-50000

Return ONLY valid JSON, no explanation:
{"date": "DD/MM/YYYY", "net_sales": 0.00, "customers": 0, "avg_basket": 0.00}"""

def extract_with_ai(pdf_bytes: bytes, api_key: str) -> dict:
    """
    Uses Claude Vision to extract sales data from PDF.
    Converts PDF pages to images, sends to Claude for extraction.
    Handles Greek/English/coded text perfectly.
    """
    result = {"date": None, "net_sales": None, "customers": None, "avg_basket": None}
    try:
        client = anthropic.Anthropic(api_key=api_key)
        # Convert only first 2 pages (header is there)
        images = convert_from_bytes(pdf_bytes, dpi=180, first_page=1, last_page=2)
        if not images: return result

        # Use first page (Department Report header)
        img = images[0]
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        img_b64 = base64.standard_b64encode(buf.getvalue()).decode()

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [{
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}
                }, {
                    "type": "text",
                    "text": "Extract the sales data from this Department Report image."
                }]
            }]
        )

        raw = response.content[0].text.strip()
        # Clean JSON
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)

        # Parse date
        if data.get("date"):
            try:
                result["date"] = datetime.strptime(data["date"], "%d/%m/%Y").date()
            except: pass

        # Parse numbers with sanity checks
        ns = data.get("net_sales")
        if ns and isinstance(ns, (int, float)) and 1000 <= ns <= 50000:
            result["net_sales"] = float(ns)

        cu = data.get("customers")
        if cu and isinstance(cu, (int, float)) and 10 <= cu <= 2000:
            result["customers"] = int(cu)

        ab = data.get("avg_basket")
        if ab and isinstance(ab, (int, float)) and 5 <= ab <= 500:
            result["avg_basket"] = float(ab)

    except Exception:
        pass

    return result

# ── TESSERACT FALLBACK ────────────────────────────────────────────────────────
def extract_with_tesseract(pdf_bytes: bytes) -> dict:
    """Fallback OCR when no AI key available."""
    import pytesseract
    from PIL import Image as PILImage
    r = {"date": None, "net_sales": None, "customers": None, "avg_basket": None}
    try:
        imgs = convert_from_bytes(pdf_bytes, dpi=200)
        txt  = "".join(pytesseract.image_to_string(i, lang="ell+eng") for i in imgs)

        def parse_num(s):
            s = str(s).strip().replace(" ","").replace("€","")
            if "." in s and "," in s: s = s.replace(".","").replace(",",".")
            elif "," in s: s = s.replace(",",".")
            return float(s)

        for pat in [r'[Ff]or\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})', r'(\d{2}/\d{2}/\d{4})']:
            m = re.search(pat, txt)
            if m:
                try: r["date"] = datetime.strptime(m.group(1).replace(".","/"),"%d/%m/%Y").date(); break
                except: pass

        for pat in [r'[Nn]e[it]{1,3}[Dd]ay[Ss]al[Dd]is\s+([\d.,]+)']:
            m = re.search(pat, txt)
            if m:
                try: v=parse_num(m.group(1));
                except: continue
                if 1000<=v<=50000: r["net_sales"]=v; break

        for pat in [r'[Nn]um[Oo]f[Cc]us\s+([\d,.]+)']:
            m = re.search(pat, txt)
            if m:
                try:
                    v=int(m.group(1).replace(",","").replace(".",""))
                    if 10<=v<=2000: r["customers"]=v; break
                except: pass

        for pat in [r'[Aa]vg[Ss]al[Cc]us\s+([\d.,]+)']:
            m = re.search(pat, txt)
            if m:
                try:
                    v=parse_num(m.group(1))
                    if 5<=v<=500: r["avg_basket"]=v; break
                except: pass
    except: pass
    return r

def extract_pdf(pdf_bytes: bytes, api_key: str = "") -> tuple[dict, str]:
    """
    Primary: Claude Vision AI (accurate, multilingual)
    Fallback: Tesseract OCR
    Returns (result, method_used)
    """
    if api_key:
        result = extract_with_ai(pdf_bytes, api_key)
        if result["date"] and result["net_sales"]:
            return result, "ai"
        # AI failed → try tesseract
    result = extract_with_tesseract(pdf_bytes)
    return result, "ocr"

# ── EMAIL ─────────────────────────────────────────────────────────────────────
def email_preview(pw):
    rows, errs = [], []
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            for msg in mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                limit=5, reverse=True, mark_seen=False):
                atts = [a.filename for a in msg.attachments if a.filename] or ["—"]
                rows.append({"Ημερομηνία": msg.date.strftime("%d/%m/%Y %H:%M") if msg.date else "—",
                             "Θέμα": (msg.subject or "")[:55], "PDF": atts[0]})
    except Exception as e: errs.append(str(e))
    return rows, errs

def fetch_emails(pw, since: date | None = None, limit: int = 60) -> tuple:
    recs, errs, n_pdf, n_ai, n_ocr = [], [], 0, 0, 0
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            for msg in mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                limit=limit, reverse=True, mark_seen=False):
                d = msg.date.date() if msg.date else None
                if since and d and d < since: continue
                s = (msg.subject or "").upper()
                if SALES_SUBJECT_KW not in s and "SKYROS" not in s: continue
                pdf = next((a for a in msg.attachments
                            if a.filename and a.filename.lower().endswith(".pdf")), None)
                if not pdf: continue
                n_pdf += 1
                rec, method = extract_pdf(pdf.payload, _ANTHROPIC_KEY)
                if rec["date"] and rec["net_sales"] is not None:
                    recs.append(rec)
                    if method == "ai": n_ai += 1
                    else: n_ocr += 1
    except Exception as e: errs.append(str(e))
    return recs, errs, n_pdf, n_ai, n_ocr

def deep_scan(pw):
    cutoff = date.today() - timedelta(days=365*DEEP_SCAN_YEARS)
    st_ = {"phase":"connect","total":0,"done":0,"saved":0,"n_ai":0,"n_ocr":0,"cur":"","err":None,"ok":False}
    yield st_.copy()
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            st_["phase"] = "listing"; yield st_.copy()
            all_h = list(mb.fetch(AND(from_=SALES_EMAIL_SENDER),
                                  limit=3000, reverse=True, mark_seen=False, headers_only=True))
            to_do = [h for h in all_h
                     if h.date and h.date.date() >= cutoff
                     and (SALES_SUBJECT_KW in (h.subject or "").upper()
                          or "SKYROS" in (h.subject or "").upper())]
            st_["total"] = len(to_do); st_["phase"] = "ocr"; yield st_.copy()
            if not to_do: st_["ok"] = True; yield st_.copy(); return

            batch = []
            for i, h in enumerate(to_do):
                st_["done"] = i+1; st_["cur"] = (h.subject or "")[:45]
                yield st_.copy()
                try:
                    full = list(mb.fetch(AND(uid=str(h.uid)), mark_seen=False))
                    if not full: continue
                    pdf = next((a for a in full[0].attachments
                                if a.filename and a.filename.lower().endswith(".pdf")), None)
                    if not pdf: continue
                    rec, method = extract_pdf(pdf.payload, _ANTHROPIC_KEY)
                    if rec["date"] and rec["net_sales"] is not None:
                        batch.append(rec)
                        if method == "ai": st_["n_ai"] += 1
                        else: st_["n_ocr"] += 1
                    if len(batch) >= BATCH_SAVE_EVERY:
                        st_["saved"] += merge_records(batch); batch = []
                        yield st_.copy()
                except: continue

            if batch: st_["saved"] += merge_records(batch)
            st_["ok"] = True; yield st_.copy()
    except Exception as e:
        st_["err"] = str(e); st_["ok"] = True; yield st_.copy()

def auto_update(pw):
    if not pw: return "no_pw"
    ld = last_date()
    if ld and ld >= date.today(): return "up_to_date"
    since = (ld - timedelta(days=3)) if ld else (date.today() - timedelta(days=7))
    try:
        recs, errs, *_ = fetch_emails(pw, since=since, limit=60)
        if errs: return f"error:{errs[0]}"
        saved = merge_records(recs)
        return f"updated:{saved}" if saved else "no_new"
    except Exception as e: return f"error:{e}"

# ── DATA ─────────────────────────────────────────────────────────────────────
today      = date.today()
week_start = today - timedelta(days=today.weekday())
week_end   = week_start + timedelta(days=6)
week_lbl   = f"{week_start.strftime('%d/%m')} — {week_end.strftime('%d/%m')}"

if "auto_done" not in st.session_state:
    st.session_state.auto_done = False
    st.session_state.auto_result = ""
if not st.session_state.auto_done and _PW:
    with st.spinner("Ενημέρωση..."):
        st.session_state.auto_result = auto_update(_PW)
        st.session_state.auto_done = True

df = load_all()
ld = last_date()
ai_active = bool(_ANTHROPIC_KEY)

# ── HEADER ───────────────────────────────────────────────────────────────────
ld_str = ld.strftime("%d/%m/%Y") if ld else "—"
ai_cls = "active" if ai_active else ""
ai_lbl = "AI · Claude Vision" if ai_active else "OCR · Tesseract"

col_t, col_b = st.columns([6,1])
with col_t:
    st.markdown(f"""
    <div class="page-rule">
      <div class="page-title">Πωλησεις Καταστηματος
        <span class="ai-badge {ai_cls}">{ai_lbl}</span>
      </div>
      <div class="page-meta">
        Τελευταια ενημερωση: {ld_str}<br>
        Εγγραφες: {len(df)}
      </div>
    </div>""", unsafe_allow_html=True)
with col_b:
    st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
    if st.button("Αρχικη", key="back"):
        st.switch_page("Home.py")
    st.markdown("</div>", unsafe_allow_html=True)

# Auto-update status
ar = st.session_state.auto_result
if ar.startswith("updated:"):
    n = ar.split(":")[1]
    st.markdown(f'<div class="status-bar sb-green"><div><span class="sb-label">Αυτοματη ενημερωση</span><br>{n} νεες εγγραφες αποθηκευτηκαν.</div></div>', unsafe_allow_html=True)
elif ar in ("up_to_date","no_new"):
    st.markdown(f'<div class="status-bar sb-gray"><div><span class="sb-label">Ενημερωμενο</span><br>Δεν υπαρχουν νεα δεδομενα · Τελευταια: {ld_str}</div></div>', unsafe_allow_html=True)
elif ar == "no_pw":
    st.markdown('<div class="status-bar sb-amber"><div><span class="sb-label">Προσοχη</span><br>Δεν βρεθηκε App Password στα Secrets — η αυτοματη ενημερωση δεν λειτουργει.</div></div>', unsafe_allow_html=True)
elif ar.startswith("error:"):
    st.markdown(f'<div class="status-bar sb-red"><div><span class="sb-label">Σφαλμα</span><br>{ar[6:]}</div></div>', unsafe_allow_html=True)

# ── FILTERS + ACTIONS ────────────────────────────────────────────────────────
st.markdown('<div class="sh">Ιστορικο Πωλησεων</div>', unsafe_allow_html=True)

fc = st.columns([2,2,1,1,1,1])
with fc[0]:
    years = sorted({r.year for r in df["date"]}, reverse=True) if not df.empty else [today.year]
    sel_y = st.selectbox("Ετος", years, key="sel_y", label_visibility="collapsed")
with fc[1]:
    sel_m = st.selectbox("Μηνας", range(1,13), format_func=lambda x: MN_FULL[x-1],
                         index=today.month-1, key="sel_m", label_visibility="collapsed")
with fc[2]:
    st.markdown('<div class="btn-outline">', unsafe_allow_html=True)
    btn_ref = st.button("Ενημερωση", use_container_width=True, key="br")
    st.markdown("</div>", unsafe_allow_html=True)
with fc[3]:
    st.markdown('<div class="btn-outline">', unsafe_allow_html=True)
    btn_5d = st.button("5 Μερες", use_container_width=True, key="b5")
    st.markdown("</div>", unsafe_allow_html=True)
with fc[4]:
    st.markdown('<div class="btn-outline">', unsafe_allow_html=True)
    btn_prev = st.button("Προεπισκοπηση", use_container_width=True, key="bprev")
    st.markdown("</div>", unsafe_allow_html=True)
with fc[5]:
    st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
    btn_deep = st.button("2 Χρονια", use_container_width=True, key="bd")
    st.markdown("</div>", unsafe_allow_html=True)

pw = _PW or st.text_input("App Password (ftoulisgm@gmail.com)", type="password", key="mpw",
                            label_visibility="collapsed" if _PW else "visible",
                            placeholder="App Password (ftoulisgm@gmail.com)" if not _PW else "")

# ── ACTIONS ───────────────────────────────────────────────────────────────────
if (btn_ref or btn_5d or btn_prev or btn_deep) and not pw:
    st.markdown('<div class="status-bar sb-amber"><span class="sb-label">Απαιτειται App Password</span></div>', unsafe_allow_html=True)

elif btn_prev and pw:
    with st.spinner("Συνδεση..."):
        rows, errs = email_preview(pw)
    if errs: st.markdown(f'<div class="status-bar sb-red"><span class="sb-label">Σφαλμα</span> {errs[0]}</div>', unsafe_allow_html=True)
    elif rows:
        st.markdown(f'<div class="status-bar sb-green"><span class="sb-label">Συνδεση επιτυχης</span> — {len(rows)} emails</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

elif btn_ref and pw:
    ld_info = ld.strftime("%d/%m/%Y") if ld else "—"
    since   = (ld - timedelta(days=3)) if ld else None
    with st.spinner(f"Ενημερωση απο {ld_info}..."):
        recs, errs, n_pdf, n_ai, n_ocr = fetch_emails(pw, since=since, limit=60)
    if errs: st.markdown(f'<div class="status-bar sb-red"><span class="sb-label">Σφαλμα</span> {errs[0]}</div>', unsafe_allow_html=True)
    else:
        saved = merge_records(recs)
        method_info = f"AI: {n_ai} · OCR: {n_ocr}" if (n_ai or n_ocr) else ""
        if saved:
            st.markdown(f'<div class="status-bar sb-green"><span class="sb-label">Ενημερωθηκε</span> — {saved} νεες εγγραφες &nbsp;·&nbsp; {method_info}</div>', unsafe_allow_html=True)
            st.session_state.auto_done = False; st.rerun()
        else:
            st.markdown(f'<div class="status-bar sb-gray"><span class="sb-label">Ενημερωμενο</span> — Δεν υπαρχουν νεα δεδομενα &nbsp;·&nbsp; {n_pdf} PDFs ελεγχθηκαν</div>', unsafe_allow_html=True)

elif btn_5d and pw:
    since5 = today - timedelta(days=5)
    with st.spinner("OCR τελευταιων 5 ημερων..."):
        recs, errs, n_pdf, n_ai, n_ocr = fetch_emails(pw, since=since5, limit=15)
    if errs: st.markdown(f'<div class="status-bar sb-red"><span class="sb-label">Σφαλμα</span> {errs[0]}</div>', unsafe_allow_html=True)
    else:
        saved = merge_records(recs)
        method_info = f"AI: {n_ai} · OCR: {n_ocr}"
        st.markdown(f'<div class="status-bar sb-green"><span class="sb-label">Αποτελεσμα</span> — {n_pdf} PDFs · {saved} αποθηκευτηκαν · {method_info}</div>', unsafe_allow_html=True)
        if saved: st.rerun()

elif btn_deep and pw:
    st.markdown('<div class="status-bar sb-amber"><span class="sb-label">Βαθεια σαρωση</span> — Μεινετε στη σελιδα. Αποθηκευση κάθε 25 εγγραφες.</div>', unsafe_allow_html=True)
    prog = st.progress(0)
    info = st.empty()
    for s in deep_scan(pw):
        if s["err"]: st.markdown(f'<div class="status-bar sb-red">{s["err"]}</div>', unsafe_allow_html=True); break
        if s["phase"] == "connect": info.markdown("Συνδεση...")
        elif s["phase"] == "listing": info.markdown("Ανακτηση λιστας emails...")
        elif s["phase"] == "ocr":
            t=s["total"]; d=s["done"]
            if t>0: prog.progress(int(d/t*100))
            info.markdown(f"**{d}/{t}** emails &nbsp;·&nbsp; AI: {s['n_ai']} &nbsp;·&nbsp; OCR: {s['n_ocr']} &nbsp;·&nbsp; {s['saved']} αποθηκευτηκαν &nbsp;·&nbsp; _{s['cur']}_")
        if s["ok"]:
            prog.progress(100)
            info.markdown(f"Ολοκληρωση — **{s['saved']}** εγγραφες αποθηκευτηκαν")
            break
    df = load_all()

# ── HISTORY TABLE ─────────────────────────────────────────────────────────────
if df.empty:
    st.markdown('<div class="status-bar sb-amber"><span class="sb-label">Χωρις δεδομενα</span> — Πατηστε "5 Μερες" για πρωτη φορτωση.</div>', unsafe_allow_html=True)
else:
    filt = df[(df["date"].apply(lambda d:d.year)==sel_y) &
              (df["date"].apply(lambda d:d.month)==sel_m)].copy()

    if not filt.empty:
        tot  = filt["net_sales"].sum()
        avg  = filt["net_sales"].mean()
        best = filt["net_sales"].max()
        days = len(filt)

        pm = sel_m-1 if sel_m>1 else 12
        py = sel_y if sel_m>1 else sel_y-1
        pm_df = df[(df["date"].apply(lambda d:d.year)==py)&(df["date"].apply(lambda d:d.month)==pm)]
        pm_tot = pm_df["net_sales"].sum() if not pm_df.empty else None

        def dlt(now, pv):
            if not pv or pv==0: return ""
            d=now-pv; p=d/pv*100
            return f'<div class="kdelta {"up" if d>=0 else "dn"}">{"+" if d>=0 else ""}{p:.1f}%</div>'

        st.markdown(f"""<div class="kgrid kg4">
          <div class="kc" style="--akz:#1a472a">
            <div class="kl">Συνολο {MN[sel_m-1]} {sel_y}</div>
            <div class="kv pos">{fmt(tot)}</div>{dlt(tot,pm_tot)}
          </div>
          <div class="kc" style="--akz:#2c5282">
            <div class="kl">Ημερησιος ΜΟ</div>
            <div class="kv">{fmt(avg)}</div>
          </div>
          <div class="kc" style="--akz:#6b21a8">
            <div class="kl">Καλυτερη Ημερα</div>
            <div class="kv">{fmt(best)}</div>
          </div>
          <div class="kc">
            <div class="kl">Ημερες</div>
            <div class="kv sm">{days}</div>
          </div>
        </div>""", unsafe_allow_html=True)

        if sel_m == today.month and sel_y == today.year:
            w_df  = filt[(filt["date"]>=week_start)&(filt["date"]<=today)]
            w_tot = w_df["net_sales"].sum() if not w_df.empty else 0
            pw_s  = week_start - timedelta(days=7)
            pw_df = df[(df["date"]>=pw_s)&(df["date"]<week_start)]
            pw_t  = pw_df["net_sales"].sum() if not pw_df.empty else None
            st.markdown(f"""<div class="kgrid kg3" style="margin-top:0">
              <div class="kc" style="--akz:#1a472a">
                <div class="kl">Εβδομαδα {week_lbl}</div>
                <div class="kv pos">{fmt(w_tot)}</div>{dlt(w_tot,pw_t)}
              </div>
              <div class="kc">
                <div class="kl">Ημερες εβδομαδας</div>
                <div class="kv sm">{len(w_df)} / 7</div>
              </div>
              <div class="kc">
                <div class="kl">ΜΟ εβδομαδας</div>
                <div class="kv">{fmt(w_df["net_sales"].mean()) if not w_df.empty else "—"}</div>
              </div>
            </div>""", unsafe_allow_html=True)

        disp = filt.copy()
        disp["date"] = disp["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
        disp.columns = ["Ημερομηνια","Καθαρες Πωλησεις","Πελατες","ΜΟ Καλαθιου"]
        st.dataframe(disp, use_container_width=True, hide_index=True)

        csv = filt.to_csv(index=False).encode("utf-8-sig")
        st.markdown('<div class="btn-ghost" style="width:160px">', unsafe_allow_html=True)
        st.download_button("Ληψη CSV", csv, f"sales_{sel_y}_{sel_m:02d}.csv", "text/csv")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-bar sb-gray">Δεν υπαρχουν δεδομενα για αυτη την περιοδο.</div>', unsafe_allow_html=True)
