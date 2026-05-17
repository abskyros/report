import streamlit as st
import pandas as pd
import os, re, io
from datetime import datetime, date, timedelta
from imap_tools import MailBox, AND
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import time

st.set_page_config(page_title="Πωλήσεις — AB Skyros", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

# ── CONFIG ────────────────────────────────────────────────────────────────────
SALES_EMAIL_USER   = "ftoulisgm@gmail.com"
SALES_EMAIL_SENDER = "abf.skyros@gmail.com"
SALES_SUBJECT_KW   = "ΑΒ ΣΚΥΡΟΣ"
SALES_CACHE        = "sales_cache.csv"
SALES_ARCHIVE      = "sales_archive.csv"
DEEP_SCAN_YEARS    = 2
BATCH_SIZE         = 31 

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
.prog-wrap{background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:1rem;margin:.5rem 0;}
.prog-title{font-size:.75rem;font-weight:700;color:#003d6b;margin-bottom:.4rem;}
.prog-sub{font-size:.65rem;color:#64748b;margin-top:.35rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
MONTHS_GR = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

def _dedup(df):
    if df.empty: return df
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return (df.sort_values("net_sales",ascending=False)
              .drop_duplicates("date",keep="first")
              .sort_values("date",ascending=False)
              .reset_index(drop=True))

def _ensure_columns(df):
    for col in ["net_sales", "customers", "avg_basket"]:
        if col not in df.columns:
            df[col] = None
    return df

def load_all():
    parts = []
    for f in [SALES_CACHE, SALES_ARCHIVE]:
        if os.path.exists(f):
            try:
                tmp = pd.read_csv(f)
                if not tmp.empty:
                    tmp = _ensure_columns(tmp)
                    parts.append(tmp)
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
        old.to_csv(SALES_ARCHIVE, index=False)

def merge_in(recs: list) -> int:
    if not recs: return 0
    ndf = pd.DataFrame(recs)
    old = load_all()
    
    added_or_updated = 0
    for _, r in ndf.iterrows():
        d = r['date']
        mask = old['date'] == d
        if not mask.any():
            old = pd.concat([old, pd.DataFrame([r])], ignore_index=True)
            added_or_updated += 1
        else:
            idx = old.index[mask].tolist()[0]
            old_row = old.iloc[idx]
            needs_update = False
            
            # Smart update: διορθώνει παλιές εγγραφές με λάθος OCR
            # π.χ. customers=32 (παλιό OCR) vs 317 (νέο OCR) → ratio=9.9x → update
            _new_c = r['customers']; _old_c = old_row['customers']
            if not pd.isna(_new_c) and _new_c > 0:
                if (pd.isna(_old_c) or _old_c < 10 or
                        (_old_c > 0 and (_new_c/_old_c > 2.5 or _new_c/_old_c < 0.4))):
                    old.at[idx, 'customers'] = _new_c; needs_update = True

            _new_a = r['avg_basket']; _old_a = old_row['avg_basket']
            if not pd.isna(_new_a) and _new_a > 0:
                if (pd.isna(_old_a) or _old_a < 5 or
                        (_old_a > 0 and (_new_a/_old_a > 2.5 or _new_a/_old_a < 0.4))):
                    old.at[idx, 'avg_basket'] = _new_a; needs_update = True
                
            if r['net_sales'] and (pd.isna(old_row['net_sales']) or r['net_sales'] > old_row['net_sales']):
                old.at[idx, 'net_sales'] = r['net_sales']
                needs_update = True
                
            if needs_update:
                added_or_updated += 1
                
    if added_or_updated > 0:
        save_split(old)
    return added_or_updated

def get_week_range(d):
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)

# ── ΑΛΑΝΘΑΣΤΟΣ ΜΗΧΑΝΙΣΜΟΣ ΑΝΑΓΝΩΣΗΣ (V4 MAX) ──────────────────────────────────
def _num(s: str) -> float:
    if not s: return None
    s = s.strip().replace(" ", "").replace("€", "")
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try: return float(s)
    except: return None

def parse_text_robust(txt: str) -> dict:
    """Ο πυρήνας εξαγωγής δεδομένων. Διαβάζει το κείμενο με 4 διαφορετικές τακτικές."""
    res = {"date": None, "net_sales": None, "customers": None, "avg_basket": None}
    
    # 1. ΒΡΙΣΚΟΥΜΕ ΤΗΝ ΠΡΑΓΜΑΤΙΚΗ ΗΜΕΡΟΜΗΝΙΑ
    # ΚΑΝΟΝΑΣ: "Run On: 27/04/2026" = η ΣΩΣΤΗ ημέρα πωλήσεων (πρωταρχική πηγή)
    #           "For 28/04/2026"     = Run On + 1 (ΛΑΘΟΣ αν χρησιμοποιηθεί άμεσα)
    # BUG FIX: [Rr]?[Uu]n πιάνει "un On" όταν το OCR κόβει το "R" στην άκρη
    # BUG FIX: [;:\s]+ πιάνει "Run On;" (OCR γράφει ";" αντί ":")
    run_m = re.search(r'[Rr]?[Uu]n\s*[Oo0]n\s*[;:\s]+?(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})', txt, re.IGNORECASE)
    if run_m:
        try: res["date"] = date(int(run_m.group(3)), int(run_m.group(2)), int(run_m.group(1)))
        except: pass
    # Fallback: "For 28/04/2026" → αφαίρεσε 1 μέρα → 27/04/2026
    if not res["date"]:
        for_m = re.search(r'(?:^|\s)[Ff][Oo0]r\s+(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})', txt, re.MULTILINE)
        if for_m:
            try: res["date"] = date(int(for_m.group(3)), int(for_m.group(2)), int(for_m.group(1))) - timedelta(days=1)
            except: pass

    # 2. ΤΑΚΤΙΚΗ A: ΑΚΡΙΒΗΣ ΓΡΑΜΜΗ "Totals:"
    totals_m = re.search(r'Totals:\s*([\d.,]{4,10})\s+100[.,]00\s+(\d{2,4})\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]{2,6})', txt, re.IGNORECASE)
    if totals_m:
        res["net_sales"] = _num(totals_m.group(1))
        res["customers"] = int(totals_m.group(2))
        res["avg_basket"] = _num(totals_m.group(3))
        return res
        
    # 3. ΤΑΚΤΙΚΗ Β: ΑΝΙΧΝΕΥΤΗΣ ΕΓΓΥΤΗΤΑΣ (Proximity Hunter)
    raw_nums = re.findall(r'\d+[.,\d]*', txt)
    valid_nums = [_num(rn.rstrip('.,')) for rn in raw_nums if _num(rn.rstrip('.,')) is not None]
    
    for i in range(len(valid_nums)):
        v1 = valid_nums[i]
        if 1000 < v1 < 50000 and v1 not in [2024, 2025, 2026]:
            for j in range(i+1, min(i+4, len(valid_nums))):
                v2 = valid_nums[j]
                if 10 < v2 < 3000 and v2.is_integer() and v2 not in [100.0]:
                    for k in range(j+1, min(j+6, len(valid_nums))):
                        v3 = valid_nums[k]
                        if 5 < v3 < 150:
                            res["net_sales"] = v1
                            res["customers"] = int(v2)
                            res["avg_basket"] = v3
                            return res
                            
    # 4. ΤΑΚΤΙΚΗ Γ: ΑΝΙΧΝΕΥΣΗ ΠΙΕΣΜΕΝΩΝ ΑΡΙΘΜΩΝ (Squash Hunter)
    clean_txt = re.sub(r'\s+', '', txt).upper()
    ns_m = re.search(r'NETDAYSAL[A-Z0-9]*[^\d]*([\d.,]{4,12})', clean_txt)
    if ns_m:
        val = _num(ns_m.group(1).rstrip('.,'))
        if val and 1000 < val < 50000: res["net_sales"] = val
        
    sq_m = re.search(r'(\d{1,2}[.,]\d{3}[.,]\d{2})(\d{3,4})(\d{2}[.,]\d{2})', clean_txt)
    if sq_m:
        ns = _num(sq_m.group(1))
        cus = int(sq_m.group(2))
        ab = _num(sq_m.group(3))
        if ns and cus and ab:
            if not res["net_sales"]: res["net_sales"] = ns
            res["customers"] = cus
            res["avg_basket"] = ab

    return res

def _ocr_page(img):
    """
    Smart OCR μιας σελίδας.
    Τα PDFs του AB Σκύρος αποθηκεύονται rotated 90° CCW.
    Δοκιμάζουμε πρώτα χωρίς → αν δεν βρούμε keywords → rotate 90°.
    Αποφεύγουμε 4 passes ανά σελίδα (παλιό) → μέγιστο 2 passes.
    """
    cfg = "--psm 6 --oem 3"
    t = pytesseract.image_to_string(img, lang="ell+eng", config=cfg)
    if any(k in t for k in ("NetDay","TotSal","Run On","un On","Totals","NumOf","For ")):
        return t
    # Γνωστή περίπτωση: rotated 90° CCW
    return pytesseract.image_to_string(img.rotate(90, expand=True), lang="ell+eng", config=cfg)


def extract(pdf_bytes: bytes) -> dict:
    """
    OCR Engine v4 — Σταθερή ανίχνευση.

    • DPI 250 (καλύτερη ανάγνωση footer/μικρού κειμένου)
    • Σελίδες 1-6 (πιάνει Dept Report σελ.1 + Hourly Productivity Totals σελ.5-6)
    • Smart rotation: max 2 passes ανά σελίδα (vs παλιό 4x)
    • Χωρίς native PDF attempt (image PDFs πάντα αποτυγχάνουν, χάσιμο χρόνου)
    """
    r = {"date": None, "net_sales": None, "customers": None, "avg_basket": None}
    try:
        images = convert_from_bytes(pdf_bytes, dpi=250, first_page=1, last_page=6)
        if not images: return r

        all_txt = "\n".join(_ocr_page(img) for img in images)
        r = parse_text_robust(all_txt)
    except Exception:
        pass
    return r

# ── ΕΞΥΠΝΟ FETCHING ───────────────────────────────────────────────────────────
def fetch_smart(pw, date_start=None, date_end=None, max_to_find=30, msg_limit=200):
    recs, n_checked = [], 0
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            criteria_args = {"from_": SALES_EMAIL_SENDER}
            if date_start: criteria_args["date_gte"] = date_start
            if date_end: criteria_args["date_lt"] = date_end
            criteria = AND(**criteria_args)
            
            for msg in mb.fetch(criteria, reverse=True, mark_seen=False, limit=msg_limit):
                if len(recs) >= max_to_find: break
                if not _is_valid(msg.subject): continue
                pdf = next((a for a in msg.attachments if a.filename and a.filename.lower().endswith(".pdf")), None)
                if not pdf: continue
                n_checked += 1
                rec = extract(pdf.payload)
                if rec["date"] and rec["net_sales"]: recs.append(rec)
    except Exception as e: st.error(f"Σφάλμα σύνδεσης: {e}")
    return recs, n_checked

def repair_bad_records(pw, info_box):
    df = load_all()
    if df.empty: return 0, 0
    
    bad_mask = (df['customers'].isna() | df['avg_basket'].isna() | 
                (df['customers'] < 10) | (df['avg_basket'] < 5))
    bad_dates = df[bad_mask]['date'].tolist()
    
    if not bad_dates: return 0, 0
        
    fixed_count = 0
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            for b_date in bad_dates:
                info_box.info(f"🔍 Επιδιόρθωση: Σάρωση email για την ημερομηνία **{b_date.strftime('%d/%m/%Y')}**...")
                d_start = b_date
                d_end = b_date + timedelta(days=3)
                criteria = AND(from_=SALES_EMAIL_SENDER, date_gte=d_start, date_lt=d_end)
                
                for msg in mb.fetch(criteria, limit=5):
                    if not _is_valid(msg.subject): continue
                    pdf = next((a for a in msg.attachments if a.filename and a.filename.lower().endswith(".pdf")), None)
                    if not pdf: continue
                    
                    rec = extract(pdf.payload)
                    if rec["date"] == b_date and rec["customers"] is not None and rec["avg_basket"] is not None:
                        fixed_count += merge_in([rec])
                        break 
    except: pass
    
    return len(bad_dates), fixed_count

def _is_valid(subj):
    s = (subj or "").upper()
    return SALES_SUBJECT_KW in s or "SKYROS" in s

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
df_all = load_all()
today = date.today()

# ── ΑΥΤΟΜΑΤΗ ΕΝΗΜΕΡΩΣΗ — ΠΟΤΕ ΔΕΝ ΚΟΙΜΑΤΑΙ ────────────────────────────────────
# Τρέχει αυτόματα κάθε AUTO_SYNC_MINS.
# BUG FIX: αφαιρέθηκε το "not df_all.empty" — τρέχει ΠΑΝΤΑ, ακόμα και αν το
# cache είναι άδειο (π.χ. μετά από Streamlit Cloud redeploy).

import streamlit.components.v1 as _components
AUTO_SYNC_MINS = 25

# JS auto-reload κάθε AUTO_SYNC_MINS → κρατά τη σελίδα πάντα ενημερωμένη
_components.html(
    f'<script>setTimeout(()=>{{window.parent.location.reload();}},{AUTO_SYNC_MINS*60*1000});</script>',
    height=0,
)

_now_ts = time.time()
if "sales_last_sync_ts" not in st.session_state:
    st.session_state.sales_last_sync_ts = 0

_sync_needed = (
    _SECRET_PW and
    (_now_ts - st.session_state.sales_last_sync_ts > AUTO_SYNC_MINS * 60)
)

if _sync_needed:
    st.session_state.sales_last_sync_ts = _now_ts
    if df_all.empty:
        # Cache άδειο (redeploy ή πρώτη φόρτωση) → φέρε τις τελευταίες 35 μέρες
        _recs, _ = fetch_smart(_SECRET_PW, max_to_find=35, msg_limit=150)
    else:
        # Incremental: από την τελευταία γνωστή ημέρα
        _since = df_all["date"].max() - timedelta(days=2)
        _recs, _ = fetch_smart(_SECRET_PW, date_start=_since, max_to_find=5, msg_limit=30)
    if _recs:
        merge_in(_recs)
        df_all = load_all()


# ── RENDER ────────────────────────────────────────────────────────────────────
st.markdown('<div class="topbar"><div class="ptitle">📊 Πωλήσεις — AB Skyros</div></div>', unsafe_allow_html=True)

col_back, _ = st.columns([1, 4])
with col_back:
    if st.button("← Αρχική", key="back"): st.switch_page("Home.py")

tab_week, tab_month, tab_year, tab_update = st.tabs(["📅 Εβδομαδιαία", "📆 Μηνιαία", "📈 Ετήσια", "🔄 Ενημέρωση"])

# ═══════════════════════════════════════════════════════════════════════════════
with tab_week:
    if df_all.empty:
        st.markdown('<div class="warn-box">⚠️ Δεν υπάρχουν δεδομένα. Πηγαίνετε στην <b>Ενημέρωση</b>.</div>', unsafe_allow_html=True)
    else:
        sel_date = st.date_input("Επίλεξε ημέρα:", today)
        start_w, end_w = get_week_range(sel_date)
        st.markdown(f'<div class="info-box">📅 Εβδομάδα: <b>{start_w.strftime("%d/%m/%Y")}</b> — <b>{end_w.strftime("%d/%m/%Y")}</b></div>', unsafe_allow_html=True)
        w_df = df_all[(df_all["date"] >= start_w) & (df_all["date"] <= end_w)]
        if not w_df.empty:
            st.markdown(f"""<div class="kr kr3">
              <div class="kc" style="--a:#10b981"><div class="kl">Καθαρό</div><div class="kv kv-green">{fmt(w_df["net_sales"].sum())}</div></div>
              <div class="kc" style="--a:#6b8fd4"><div class="kl">Πελάτες</div><div class="kv">{int(w_df["customers"].sum()) if pd.notna(w_df["customers"].sum()) else "—"}</div></div>
              <div class="kc" style="--a:#7c5abf"><div class="kl">ΜΟ Καλαθιού</div><div class="kv">{fmt(w_df["avg_basket"].mean())}</div></div>
            </div>""", unsafe_allow_html=True)
            
            disp = w_df.copy()
            disp["date"] = pd.to_datetime(disp["date"]).dt.strftime("%d/%m/%Y")
            st.dataframe(disp.rename(columns={"date":"ΗΜ/ΝΙΑ","net_sales":"ΠΩΛΗΣΕΙΣ", "customers":"ΠΕΛΑΤΕΣ", "avg_basket":"ΜΟ ΚΑΛΑΘΙΟΥ"}), use_container_width=True, hide_index=True)
        else: st.warning("Δεν βρέθηκαν εγγραφές για αυτή την εβδομάδα.")

# ═══════════════════════════════════════════════════════════════════════════════
with tab_month:
    if df_all.empty: st.markdown('<div class="warn-box">⚠️ Δεν υπάρχουν δεδομένα.</div>', unsafe_allow_html=True)
    else:
        c1, c2 = st.columns(2)
        s_m = c1.selectbox("Μήνας", range(1,13), format_func=lambda x: MONTHS_GR[x-1], index=today.month-1)
        s_y = c2.selectbox("Έτος (Μηνιαία)", sorted({r.year for r in df_all["date"]}, reverse=True))
        m_df = df_all[(df_all["date"].apply(lambda d: d.month) == s_m) & (df_all["date"].apply(lambda d: d.year) == s_y)].copy()
        
        if not m_df.empty:
            st.markdown(f"""<div class="kr kr4">
              <div class="kc" style="--a:#10b981"><div class="kl">Σύνολο</div><div class="kv kv-green">{fmt(m_df["net_sales"].sum())}</div></div>
              <div class="kc" style="--a:#6b8fd4"><div class="kl">Πελάτες</div><div class="kv">{int(m_df["customers"].sum())}</div></div>
              <div class="kc" style="--a:#7c5abf"><div class="kl">ΜΟ Καλαθιού</div><div class="kv">{fmt(m_df["avg_basket"].mean())}</div></div>
              <div class="kc" style="--a:#f59e0b"><div class="kl">Max Ημέρα</div><div class="kv">{fmt(m_df["net_sales"].max())}</div></div>
            </div>""", unsafe_allow_html=True)
            
            st.markdown("---")
            col_chart1, col_chart2 = st.columns(2)
            chart_data = m_df.sort_values("date")
            chart_data["Ημέρα"] = pd.to_datetime(chart_data["date"]).dt.strftime("%d")
            
            with col_chart1:
                st.markdown('<div class="sh">Ημερήσιος Τζίρος</div>', unsafe_allow_html=True)
                st.line_chart(chart_data.set_index("Ημέρα")["net_sales"], use_container_width=True)
                
            with col_chart2:
                st.markdown('<div class="sh">Κίνηση Πελατών (Ημερησίως)</div>', unsafe_allow_html=True)
                st.bar_chart(chart_data.set_index("Ημέρα")["customers"], use_container_width=True)

            st.markdown("---")
            disp_m = m_df.copy()
            disp_m["date"] = pd.to_datetime(disp_m["date"]).dt.strftime("%d/%m/%Y")
            st.dataframe(disp_m.rename(columns={"date":"ΗΜ/ΝΙΑ","net_sales":"ΠΩΛΗΣΕΙΣ", "customers":"ΠΕΛΑΤΕΣ", "avg_basket":"ΜΟ ΚΑΛΑΘΙΟΥ"}), use_container_width=True, hide_index=True)
        else: st.warning("Δεν βρέθηκαν εγγραφές για αυτόν τον μήνα.")

# ═══════════════════════════════════════════════════════════════════════════════
with tab_year:
    if df_all.empty: st.markdown('<div class="warn-box">⚠️ Δεν υπάρχουν δεδομένα.</div>', unsafe_allow_html=True)
    else:
        sel_year = st.selectbox("Επίλεξε Έτος:", sorted({r.year for r in df_all["date"]}, reverse=True))
        y_df = df_all[df_all["date"].apply(lambda d: d.year) == sel_year].copy()
        
        if not y_df.empty:
            st.markdown(f"""<div class="kr kr4">
              <div class="kc" style="--a:#10b981"><div class="kl">Ετήσιος Τζίρος</div><div class="kv kv-green">{fmt(y_df["net_sales"].sum())}</div></div>
              <div class="kc" style="--a:#6b8fd4"><div class="kl">Σύνολο Πελατών</div><div class="kv">{int(y_df["customers"].sum())}</div></div>
              <div class="kc" style="--a:#7c5abf"><div class="kl">ΜΟ Καλαθιού (Έτους)</div><div class="kv">{fmt(y_df["avg_basket"].mean())}</div></div>
              <div class="kc" style="--a:#f59e0b"><div class="kl">Ημέρες Λειτουργίας</div><div class="kv">{len(y_df)}</div></div>
            </div>""", unsafe_allow_html=True)
            
            y_df['month_num'] = y_df['date'].apply(lambda d: d.month)
            monthly_grouped = y_df.groupby('month_num').agg({'net_sales': 'sum', 'customers': 'sum'}).reset_index()
            monthly_grouped['Μήνας'] = monthly_grouped['month_num'].apply(lambda x: MONTHS_GR[x-1])
            monthly_grouped = monthly_grouped.sort_values('month_num').set_index('Μήνας')
            
            st.markdown("---")
            st.markdown('<div class="sh">Μηνιαία Απόδοση Τζίρου</div>', unsafe_allow_html=True)
            st.bar_chart(monthly_grouped['net_sales'], use_container_width=True)
            
            st.markdown('<div class="sh">Επισκεψιμότητα ανά Μήνα (Σύνολο Πελατών)</div>', unsafe_allow_html=True)
            st.line_chart(monthly_grouped['customers'], use_container_width=True)
        else:
            st.warning("Δεν υπάρχουν δεδομένα για αυτό το έτος.")

# ═══════════════════════════════════════════════════════════════════════════════
with tab_update:
    st.markdown('<div class="sh">Έξυπνη Διαχείριση Ενημερώσεων</div>', unsafe_allow_html=True)
    
    if not df_all.empty:
        oldest, newest = df_all["date"].min(), df_all["date"].max()
        st.markdown(f"""<div class="info-box">
            📈 <b>Καλυμμένο Διάστημα:</b> {oldest.strftime('%d/%m/%Y')} έως {newest.strftime('%d/%m/%Y')}<br>
            💾 <b>Σύνολο Αρχείων:</b> {len(df_all)} ημέρες αποθηκευμένες με ασφάλεια.
        </div>""", unsafe_allow_html=True)
    else:
        st.info("Η βάση δεδομένων είναι άδεια. Ξεκινήστε την πρώτη σας ενημέρωση!")

    sales_pw = _SECRET_PW if _SECRET_PW else st.text_input("🔐 App Password", type="password")

    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⚡ Γρήγορη Ενημέρωση (Νέα)", use_container_width=True):
            if not sales_pw: st.error("Βάλτε κωδικό.")
            else:
                with st.spinner("Ψάχνω για νεότερα αρχεία..."):
                    since = df_all["date"].max() if not df_all.empty else None
                    recs, n = fetch_smart(sales_pw, date_start=since, max_to_find=40, msg_limit=200)
                    added = merge_in(recs)
                    if added > 0: st.success(f"Προστέθηκαν/Ενημερώθηκαν {added} μέρες!"); time.sleep(1); st.rerun()
                    else: st.info("Δεν βρέθηκαν νέα email πωλήσεων.")

    with col2:
        if st.button("🔄 Επαναφόρτωση Τελευταίων 10 Ημερών", use_container_width=True):
            if not sales_pw: st.error("Βάλτε κωδικό.")
            else:
                with st.spinner("Έλεγχος των email των τελευταίων 10 ημερών..."):
                    start_10 = today - timedelta(days=10)
                    recs, n = fetch_smart(sales_pw, date_start=start_10, max_to_find=15, msg_limit=50)
                    added = merge_in(recs)
                    st.success(f"Ελέγχθηκαν 10 ημέρες. Επιδιορθώθηκαν/Προστέθηκαν: {added}")
                    time.sleep(2); st.rerun()

    st.markdown("---")
    
    if st.button("⏪ Φόρτωση Προηγούμενου Μήνα (Ιστορικό)", use_container_width=True):
        if not sales_pw: st.error("Βάλτε κωδικό.")
        else:
            with st.spinner("Πηγαίνω 1 μήνα πιο πίσω στο ιστορικό..."):
                until = df_all["date"].min() if not df_all.empty else today
                start = until - timedelta(days=31)
                recs, n = fetch_smart(sales_pw, date_start=start, date_end=until, max_to_find=35, msg_limit=200)
                added = merge_in(recs)
                if added > 0: st.success(f"Φορτώθηκαν {added} μέρες ιστορικού!"); time.sleep(1); st.rerun()
                else: st.warning("Δεν βρέθηκαν παλαιότερα αρχεία σε αυτό το διάστημα.")

    st.markdown("---")
    
    st.markdown('<div class="info-box">ℹ️ <b>Νυχτερινή Επιδιόρθωση:</b> Αν θέλεις η εφαρμογή να ελέγξει όλα τα λάθη μόνη της το βράδυ, απλώς πάτα το παρακάτω κουμπί και <b>μην κλείσεις τον υπολογιστή ή τη σελίδα</b>. Όταν ξυπνήσεις, όλα θα είναι διορθωμένα!</div>', unsafe_allow_html=True)
    if st.button("🛠️ Έλεγχος & Επιδιόρθωση ΟΛΩΝ των Δεδομένων", use_container_width=True):
        if not sales_pw: st.error("Βάλτε κωδικό.")
        else:
            progress_box = st.empty()
            bad_count, fixed_count = repair_bad_records(sales_pw, progress_box)
            
            if bad_count == 0:
                progress_box.success("✅ Όλα τα δεδομένα σας είναι ήδη πλήρη και 100% σωστά! Δεν βρέθηκαν κενά.")
            else:
                progress_box.success(f"✅ Εντοπίστηκαν {bad_count} μέρες με ελλείψεις και **επιδιορθώθηκαν επιτυχώς** οι {fixed_count} από αυτές!")
            time.sleep(4)
            st.rerun()
