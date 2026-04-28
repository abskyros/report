import streamlit as st
import pandas as pd
import os, re, io
from datetime import datetime, date, timedelta
from imap_tools import MailBox, AND
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

st.set_page_config(page_title="Πωλήσεις — AB Skyros", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

# ── CONFIG ────────────────────────────────────────────────────────────────────
SALES_EMAIL_USER   = "ftoulisgm@gmail.com"
SALES_EMAIL_SENDER = "abf.skyros@gmail.com"
SALES_SUBJECT_KW   = "ΑΒ ΣΚΥΡΟΣ"
SALES_CACHE        = "sales_cache.csv"
SALES_ARCHIVE      = "sales_archive.csv"
DEEP_SCAN_YEARS    = 2
BATCH_SIZE         = 25

# ── SECRETS ──────────────────────────────────────────────────────────────────
_SECRET_PW = ""
try:
    _SECRET_PW = st.secrets.get("SALES_EMAIL_PASS", "")
    if not _SECRET_PW:
        _SECRET_PW = st.secrets.get("EMAIL_PASS", "")
except:
    pass

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background:#e8f4fb!important;color:#0f172a!important;}
.stApp{background:#e8f4fb!important;}
section[data-testid="stSidebar"]{display:none!important;}
#MainMenu,footer,header{visibility:hidden!important;}
.block-container{padding:1.5rem 1.5rem 4rem!important;max-width:960px!important;margin:0 auto!important;}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:2px solid #bae6fd;}
.ptitle{font-size:1.25rem;font-weight:800;color:#003d6b;}
.sh{font-size:.58rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#0369a1;margin:1.8rem 0 .7rem;border-bottom:1px solid #e0f2fe;padding-bottom:.4rem;}
.kr{display:grid;gap:.75rem;margin:.5rem 0 1.2rem;}
.kr4{grid-template-columns:repeat(4,1fr);}
.kr3{grid-template-columns:repeat(3,1fr);}
@media(max-width:900px){.kr4{grid-template-columns:repeat(2,1fr);}}
@media(max-width:580px){.kr4,.kr3{grid-template-columns:1fr;}.block-container{padding:1rem 1rem 3rem!important;}}
.kc{background:#fff;border:1px solid #e0f2fe;border-radius:12px;padding:.9rem 1rem;position:relative;overflow:hidden;box-shadow:0 2px 8px rgba(0,61,107,0.06);}
.kc::before{content:'';position:absolute;top:0;left:0;bottom:0;width:3px;background:var(--a,#00b5e2);}
.kl{font-size:.58rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#64748b;margin-bottom:.3rem;}
.kv{font-size:1.1rem;font-weight:800;color:#0f172a;}
.kv-green{color:#00b5e2;}
.stButton>button{border-radius:9px!important;font-family:'Inter',sans-serif!important;font-size:.82rem!important;font-weight:700!important;padding:.6rem 1rem!important;transition:all .15s!important;}
.btn-g>button{background:#00b5e2!important;border:none!important;color:#fff!important;}
.btn-g>button:hover{background:#0099c4!important;}
.btn-back>button{background:#fff!important;border:1px solid #bae6fd!important;color:#003d6b!important;font-weight:700!important;}
.btn-back>button:hover{background:#e0f2fe!important;}
[data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid #bae6fd!important;gap:.2rem!important;}
[data-baseweb="tab"]{background:transparent!important;border:none!important;color:#64748b!important;font-size:.74rem!important;font-weight:700!important;letter-spacing:.05em!important;text-transform:uppercase!important;padding:.5rem .9rem!important;border-radius:8px 8px 0 0!important;}
[aria-selected="true"][data-baseweb="tab"]{color:#00b5e2!important;background:#e0f2fe!important;border-bottom:2px solid #00b5e2!important;}
[data-testid="stDataFrame"]{border:1px solid #bae6fd;border-radius:10px;overflow:hidden;}
.info-box{background:#e0f2fe;border:1px solid #bae6fd;border-radius:10px;padding:.8rem 1rem;font-size:.73rem;color:#0369a1;margin:.6rem 0;}
.warn-box{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:.8rem 1rem;font-size:.73rem;color:#92400e;margin:.6rem 0;}
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
MONTHS_GR = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

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

def get_week_range(d):
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)

# ── OCR ENGINE ────────────────────────────────────────────────────────────────
def _num(s: str) -> float:
    if not s: return None
    # Καθαρισμός OCR λαθών (π.χ. O αντί για 0)
    s = s.strip().upper().replace("O", "0").replace("I", "1").replace(" ", "").replace("€", "")
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(re.sub(r'[^0-9.]', '', s))
    except:
        return None

def extract(pdf_bytes: bytes) -> dict:
    r = {"date": None, "net_sales": None, "customers": None, "avg_basket": None}
    try:
        images = convert_from_bytes(pdf_bytes, dpi=200, first_page=1, last_page=3)

        def attempt_extraction(txt):
            res = {"date": None, "net_sales": [None, 0], "customers": [None, 0], "avg_basket": [None, 0]}
            
            # Καθαρισμός κειμένου για ευκολότερη αναζήτηση
            clean_txt = re.sub(r'[ \t]+', ' ', txt)

            # 1. ΗΜΕΡΟΜΗΝΙΑ
            date_m = re.search(r'[Ff]or\s*[:\-]?\s*(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})', clean_txt)
            if date_m:
                try: res["date"] = date(int(date_m.group(3)), int(date_m.group(2)), int(date_m.group(1)))
                except: pass

            # 2. KEYWORD TARGETING (Με βάση τις οδηγίες σου)
            # Πωλήσεις (netdaysaldis)
            ns_m = re.search(r'Ne[t71][ ]?Day[ ]?Sal[ ]?Dis\s*[:\-]?\s*([\d.,]{4,12})', clean_txt, re.IGNORECASE)
            if ns_m: res["net_sales"] = [_num(ns_m.group(1)), 10]
            
            # Πελάτες (numofcus)
            nc_m = re.search(r'Num[ ]?Of[ ]?Cus\s*[:\-]?\s*(\d{2,4})', clean_txt, re.IGNORECASE)
            if nc_m: res["customers"] = [int(nc_m.group(1)), 10]
                
            # ΜΟ Καλαθιού (avgsalcus)
            ab_m = re.search(r'Avg[ ]?Sal[ ]?Cus\s*[:\-]?\s*([\d.,]{2,8})', clean_txt, re.IGNORECASE)
            if ab_m: res["avg_basket"] = [_num(ab_m.group(1)), 10]

            # 3. TOTALS BLOCK (Hourly Productivity - Backup)
            if res["net_sales"][0] is None or res["customers"][0] is None:
                tot_m = re.search(r'Totals?[:\s]+([\d.,]+)\s+100[.,][0Oo]{2}\s+(\d+)\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]+)', clean_txt, re.IGNORECASE)
                if tot_m:
                    if res["net_sales"][0] is None: res["net_sales"] = [_num(tot_m.group(1)), 5]
                    if res["customers"][0] is None: res["customers"] = [int(tot_m.group(2)), 5]
                    if res["avg_basket"][0] is None: res["avg_basket"] = [_num(tot_m.group(3)), 5]
            
            return res

        # 🔄 AUTO-ROTATION ENGINE & SCORING
        rotations = [None, Image.ROTATE_270, Image.ROTATE_90, Image.ROTATE_180]
        final_data = {"date": None, "net_sales": None, "customers": None, "avg_basket": None}
        best_score = -1
        
        for rot in rotations:
            txt_parts = []
            for img in images:
                img_to_ocr = img.transpose(rot) if rot is not None else img
                txt_parts.append(pytesseract.image_to_string(img_to_ocr, lang="ell+eng", config="--psm 6"))
            
            full_txt = "\n".join(txt_parts)
            parsed = attempt_extraction(full_txt)
            
            # Υπολογισμός Score (Ημερομηνία + πόντοι από τα ευρήματα)
            current_score = (10 if parsed["date"] else 0) + parsed["net_sales"][1] + parsed["customers"][1] + parsed["avg_basket"][1]
            
            if current_score > best_score:
                best_score = current_score
                final_data = {
                    "date": parsed["date"],
                    "net_sales": parsed["net_sales"][0],
                    "customers": parsed["customers"][0],
                    "avg_basket": parsed["avg_basket"][0]
                }
            
            if best_score >= 40: break # Τέλειο αποτέλεσμα

        return final_data

    except Exception: pass
    return r

# ── EMAIL FETCHING ────────────────────────────────────────────────────────────
def _is_valid(subj):
    s = (subj or "").upper()
    return SALES_SUBJECT_KW in s or "SKYROS" in s

def fetch(pw, since: date | None = None, limit: int = 60):
    recs, errs, n = [], [], 0
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            for msg in mb.fetch(AND(from_=SALES_EMAIL_SENDER), limit=limit, reverse=True, mark_seen=False):
                d = msg.date.date() if msg.date else None
                if since and d and d < since: continue
                if not _is_valid(msg.subject): continue
                pdf = next((a for a in msg.attachments if a.filename and a.filename.lower().endswith(".pdf")), None)
                if not pdf: continue
                n += 1
                rec = extract(pdf.payload)
                if rec["date"] and rec["net_sales"] is not None:
                    recs.append(rec)
    except Exception as e: errs.append(str(e))
    return recs, errs, n

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
df  = load_all()
today = date.today()

# ── RENDER UI ─────────────────────────────────────────────────────────────────
st.markdown('<div class="topbar"><div class="ptitle">📊 Πωλήσεις Καταστήματος</div></div>', unsafe_allow_html=True)

col_back, _ = st.columns([1, 4])
with col_back:
    if st.button("← Αρχική", key="back"): st.switch_page("Home.py")

tab_week, tab_month, tab_update = st.tabs(["📅 Εβδομαδιαία", "📆 Μηνιαία", "🔄 Ενημέρωση"])

with tab_week:
    if df.empty:
        st.markdown('<div class="warn-box">⚠️ Δεν υπάρχουν δεδομένα. Μεταβείτε στην καρτέλα <b>Ενημέρωση</b>.</div>', unsafe_allow_html=True)
    else:
        sel_date = st.date_input("Επίλεξε ημέρα για εβδομάδα:", today)
        start_w, end_w = get_week_range(sel_date)
        mask_w = (df["date"] >= start_w) & (df["date"] <= end_w)
        w_df   = df[mask_w]
        if not w_df.empty:
            st.markdown(f'<div class="kr kr3"><div class="kc" style="--a:#10b981"><div class="kl">Καθαρό Εβδομάδας</div><div class="kv kv-green">{fmt(w_df["net_sales"].sum())}</div></div><div class="kc" style="--a:#6b8fd4"><div class="kl">Πελάτες</div><div class="kv">{int(w_df["customers"].sum())}</div></div><div class="kc" style="--a:#7c5abf"><div class="kl">ΜΟ Καλαθιού</div><div class="kv">{fmt(w_df["avg_basket"].mean())}</div></div></div>', unsafe_allow_html=True)
            st.dataframe(w_df.rename(columns={"date":"ΗΜΕΡΟΜΗΝΙΑ","net_sales":"ΠΩΛΗΣΕΙΣ","customers":"ΠΕΛΑΤΕΣ","avg_basket":"ΜΟ"}), use_container_width=True, hide_index=True)

with tab_month:
    if not df.empty:
        col_m, col_y = st.columns(2)
        s_m = col_m.selectbox("Μήνας", range(1,13), format_func=lambda x: MONTHS_GR[x-1], index=today.month-1)
        s_y = col_y.selectbox("Έτος", sorted(df["date"].apply(lambda d: d.year).unique(), reverse=True))
        m_df = df[(df["date"].apply(lambda d: d.month) == s_m) & (df["date"].apply(lambda d: d.year) == s_y)]
        if not m_df.empty:
            st.markdown(f'<div class="kr kr3"><div class="kc" style="--a:#10b981"><div class="kl">Σύνολο Μήνα</div><div class="kv kv-green">{fmt(m_df["net_sales"].sum())}</div></div><div class="kc" style="--a:#6b8fd4"><div class="kl">Ημερήσιος ΜΟ</div><div class="kv">{fmt(m_df["net_sales"].mean())}</div></div><div class="kc" style="--a:#7c5abf"><div class="kl">Καλύτερη Ημέρα</div><div class="kv">{fmt(m_df["net_sales"].max())}</div></div></div>', unsafe_allow_html=True)
            st.dataframe(m_df, use_container_width=True, hide_index=True)

with tab_update:
    sales_pw = st.text_input("🔐 Gmail App Password", type="password") if not _SECRET_PW else _SECRET_PW
    col1, col2 = st.columns(2)
    if col1.button("🧪 Δοκιμή (10 Τελευταία)", use_container_width=True):
        recs, errs, n = fetch(sales_pw, limit=10)
        if recs:
            merge_in(recs)
            st.success(f"✅ Επιτυχία! Διαβάστηκαν {len(recs)} αρχεία.")
            st.rerun()
    if col2.button("🔍 Γρήγορη Ενημέρωση", use_container_width=True):
        recs, errs, n = fetch(sales_pw, limit=30)
        if recs: merge_in(recs); st.rerun()
