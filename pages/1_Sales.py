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

# ── OCR ENGINE ΜΕ KEYWORD + SPEED HUNTER ──────────────────────────────────────
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
    try:
        return float(s)
    except:
        return None

def extract(pdf_bytes: bytes) -> dict:
    r = {"date": None, "net_sales": None, "customers": None, "avg_basket": None}
    try:
        # 🔥 SUPER SPEED: Μετατροπή ΜΟΝΟ της 1ης Σελίδας.
        images = convert_from_bytes(pdf_bytes, dpi=200, first_page=1, last_page=1)
        if not images: return r
        img = images[0]

        def attempt_extraction(txt):
            res = {"date": None, "net_sales": None, "customers": None, "avg_basket": None}
            
            # 1. ΗΜΕΡΟΜΗΝΙΑ
            date_m = re.search(r'[Ff]or\s*[:\-]?\s*(\d{1,2})[/\.-](\d{1,2})[/\.-](\d{4})', txt)
            if date_m:
                try: res["date"] = date(int(date_m.group(3)), int(date_m.group(2)), int(date_m.group(1)))
                except: pass

            # 2. KEYWORD HUNTER (Αφαιρούμε κενά)
            clean_txt = re.sub(r'\s+', '', txt).upper()
            
            ns_m = re.search(r'NETDAYSALDIS[^\d]*([\d.,]{4,12})', clean_txt)
            if ns_m:
                val = _num(ns_m.group(1))
                if val and 1000 < val < 50000: res["net_sales"] = val
                
            nc_m = re.search(r'NUMOFCUS[^\d]*(\d{2,4})', clean_txt)
            if nc_m:
                val = int(nc_m.group(1))
                if 10 < val < 3000: res["customers"] = val
                
            ab_m = re.search(r'AVGSALCUS[^\d]*([\d.,]{2,6})', clean_txt)
            if ab_m:
                val = _num(ab_m.group(1))
                if val and 5 < val < 150: res["avg_basket"] = val

            # 3. SEQUENCE HUNTER (Backup)
            if res["net_sales"] is None or res["customers"] is None or res["avg_basket"] is None:
                raw_nums = re.findall(r'\b\d+[.,\d]*\b', txt)
                valid_nums = []
                for rn in raw_nums:
                    val = _num(rn)
                    if val is not None:
                        valid_nums.append((val, val.is_integer()))

                for i in range(len(valid_nums) - 2):
                    v1, _ = valid_nums[i]
                    if not (1000 < v1 < 50000): continue 
                    
                    for j in range(i+1, min(i+8, len(valid_nums)-1)):
                        v2, is_int2 = valid_nums[j]
                        if not (10 < v2 < 3000 and is_int2): continue 
                        
                        for k in range(j+1, min(j+8, len(valid_nums))):
                            v3, _ = valid_nums[k]
                            if not (5 < v3 < 150): continue 
                            
                            if res["net_sales"] is None: res["net_sales"] = v1
                            if res["customers"] is None: res["customers"] = int(v2)
                            if res["avg_basket"] is None: res["avg_basket"] = v3
                            break
                        if res["net_sales"] is not None and res["customers"] is not None: break
                    if res["net_sales"] is not None and res["customers"] is not None: break

            # 4. FALLBACK
            if res["net_sales"] is None:
                ns_m = re.search(r'NETDAY[^\d]{1,15}?([\d.,]{4,10})', clean_txt)
                if ns_m: 
                    ns = _num(ns_m.group(1))
                    if ns and 1000 < ns < 50000: res["net_sales"] = ns
                    
            return res

        # 🔄 AUTO-ROTATION ENGINE (Fast Mode)
        rotations = [None, Image.ROTATE_270, Image.ROTATE_90, Image.ROTATE_180]
        
        best_result = r
        best_score = -1
        
        for rot in rotations:
            img_to_ocr = img.transpose(rot) if rot is not None else img
            txt = pytesseract.image_to_string(img_to_ocr, lang="ell+eng", config="--psm 6")
            parsed = attempt_extraction(txt)
            
            score = 0
            if parsed["date"]: score += 1
            if parsed["net_sales"]: score += 2  # Δίνουμε βαρύτητα στον τζίρο
            if parsed["customers"]: score += 1
            if parsed["avg_basket"]: score += 1
            
            if score > best_score:
                best_score = score
                best_result = parsed
                
            # 🔥 SUPER-SPEED ΟΠΤΙΜΙΖΑΤΙΟΝ: 
            # Αν βρει Ημερομηνία + Τζίρο (δηλαδή τα βασικά), έχει βρει την ΣΩΣΤΗ ΓΩΝΙΑ.
            # Σταματάει τον κύκλο αμέσως και κερδίζει τεράστιο χρόνο!
            if parsed["date"] is not None and parsed["net_sales"] is not None:
                return best_result
                
        r = best_result

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

def deep_scan(pw):
    cutoff = date.today() - timedelta(days=365*DEEP_SCAN_YEARS)
    s = {"phase":"connect","total":0,"done":0,"saved":0,"cur":"","err":None,"ok":False}
    yield s.copy()
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            s["phase"] = "listing"; yield s.copy()
            hdrs = [h for h in mb.fetch(AND(from_=SALES_EMAIL_SENDER), limit=3000, reverse=True, mark_seen=False, headers_only=True)
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
                    pdf = next((a for a in full[0].attachments if a.filename and a.filename.lower().endswith(".pdf")), None)
                    if not pdf: continue
                    rec = extract(pdf.payload)
                    if rec["date"] and rec["net_sales"] is not None:
                        batch.append(rec)
                    if len(batch) >= BATCH_SIZE:
                        s["saved"] += merge_in(batch); batch = []; yield s.copy()
                except: continue

            if batch: s["saved"] += merge_in(batch)
            s["ok"] = True; yield s.copy()
    except Exception as e:
        s["err"] = str(e); s["ok"] = True; yield s.copy()


# ── LOAD DATA ─────────────────────────────────────────────────────────────────
df  = load_all()
today = date.today()

# ── RENDER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
  <div class="ptitle">📊 Πωλήσεις Καταστήματος</div>
</div>
""", unsafe_allow_html=True)

col_back, _ = st.columns([1, 4])
with col_back:
    st.markdown('<div class="btn-back">', unsafe_allow_html=True)
    if st.button("← Αρχική", key="back"):
        st.switch_page("Home.py")
    st.markdown("</div>", unsafe_allow_html=True)

# ── TABS ─────────────────────────────────────────────────────────────────────
tab_week, tab_month, tab_update = st.tabs(["📅 Εβδομαδιαία", "📆 Μηνιαία", "🔄 Ενημέρωση"])

# ═══════════════════════════════════════════════════════════════════════════════
with tab_week:
    if df.empty:
        st.markdown('<div class="warn-box">⚠️ Δεν υπάρχουν δεδομένα. Μεταβείτε στην καρτέλα <b>Ενημέρωση</b>.</div>', unsafe_allow_html=True)
    else:
        sel_date = st.date_input("Επίλεξε ημέρα για εβδομάδα:", today)
        start_w, end_w = get_week_range(sel_date)
        st.markdown(f'<div class="info-box">📅 Εβδομάδα: <b>{start_w.strftime("%d/%m/%Y")}</b> — <b>{end_w.strftime("%d/%m/%Y")}</b></div>', unsafe_allow_html=True)

        mask_w = (df["date"] >= start_w) & (df["date"] <= end_w)
        w_df   = df[mask_w]

        if not w_df.empty:
            tot_sales = w_df["net_sales"].sum()
            avg_bask  = w_df["avg_basket"].mean()
            tot_cust  = w_df["customers"].sum()

            st.markdown(f"""<div class="kr kr3">
              <div class="kc" style="--a:#10b981"><div class="kl">Καθαρό Εβδομάδας</div><div class="kv kv-green">{fmt(tot_sales)}</div></div>
              <div class="kc" style="--a:#6b8fd4"><div class="kl">Πελάτες Εβδομάδας</div><div class="kv">{int(tot_cust) if pd.notna(tot_cust) else '—'}</div></div>
              <div class="kc" style="--a:#7c5abf"><div class="kl">ΜΟ Καλαθιού</div><div class="kv">{fmt(avg_bask)}</div></div>
            </div>""", unsafe_allow_html=True)

            disp = w_df.copy()
            disp["date"] = disp["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
            st.dataframe(
                disp.rename(columns={"date":"ΗΜΕΡΟΜΗΝΙΑ", "net_sales":"ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ", "customers":"ΠΕΛΑΤΕΣ", "avg_basket":"ΜΟ ΚΑΛΑΘΙΟΥ"})
                    .style.format({
                        "ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ": lambda v: fmt(v),
                        "ΜΟ ΚΑΛΑΘΙΟΥ": lambda v: fmt(v) if pd.notna(v) else "—",
                        "ΠΕΛΑΤΕΣ": lambda v: f"{int(v)}" if pd.notna(v) else "—"
                    }),
                use_container_width=True, hide_index=True
            )
        else:
            st.markdown('<div class="warn-box">Δεν υπάρχουν εγγραφές για αυτή την εβδομάδα.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
with tab_month:
    if df.empty:
        st.markdown('<div class="warn-box">⚠️ Δεν υπάρχουν δεδομένα.</div>', unsafe_allow_html=True)
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            s_m = st.selectbox("Μήνας", range(1,13), format_func=lambda x: MONTHS_GR[x-1], index=today.month-1)
        with col_b:
            available_years = sorted({r.year for r in df["date"]}, reverse=True)
            s_y = st.selectbox("Έτος", available_years)

        mask_m = (df["date"].apply(lambda d: d.month) == s_m) & (df["date"].apply(lambda d: d.year) == s_y)
        m_df   = df[mask_m]

        if not m_df.empty:
            tot_sales = m_df["net_sales"].sum()
            avg_daily = m_df["net_sales"].mean()
            best_day  = m_df["net_sales"].max()

            st.markdown(f"""<div class="kr kr3">
              <div class="kc" style="--a:#10b981"><div class="kl">Σύνολο Μήνα</div><div class="kv kv-green">{fmt(tot_sales)}</div></div>
              <div class="kc" style="--a:#6b8fd4"><div class="kl">Ημερήσιος ΜΟ</div><div class="kv">{fmt(avg_daily)}</div></div>
              <div class="kc" style="--a:#7c5abf"><div class="kl">Καλύτερη Ημέρα</div><div class="kv">{fmt(best_day)}</div></div>
            </div>""", unsafe_allow_html=True)

            disp = m_df.copy()
            disp["date"] = disp["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
            st.dataframe(
                disp.rename(columns={"date":"ΗΜΕΡΟΜΗΝΙΑ", "net_sales":"ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ", "customers":"ΠΕΛΑΤΕΣ", "avg_basket":"ΜΟ ΚΑΛΑΘΙΟΥ"})
                    .style.format({
                        "ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ": lambda v: fmt(v),
                        "ΜΟ ΚΑΛΑΘΙΟΥ": lambda v: fmt(v) if pd.notna(v) else "—",
                        "ΠΕΛΑΤΕΣ": lambda v: f"{int(v)}" if pd.notna(v) else "—"
                    }),
                use_container_width=True, hide_index=True
            )

            csv = m_df.rename(columns={"date":"ΗΜΕΡΟΜΗΝΙΑ", "net_sales":"ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ", "customers":"ΠΕΛΑΤΕΣ", "avg_basket":"ΜΟ ΚΑΛΑΘΙΟΥ"}).to_csv(index=False).encode("utf-8-sig")
            st.download_button(f"📥 Λήψη {MONTHS_GR[s_m-1]} {s_y} CSV", csv, f"sales_{s_y}_{s_m:02d}.csv", "text/csv")
        else:
            st.markdown('<div class="warn-box">Δεν υπάρχουν εγγραφές για αυτόν τον μήνα.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
with tab_update:
    st.markdown('<div class="sh">Σύνδεση Email</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="info-box">📧 Λογαριασμός: <b>{SALES_EMAIL_USER}</b> — Αποστολέας: <b>{SALES_EMAIL_SENDER}</b><br>Χρησιμοποιήστε <b>App Password</b> του Gmail.</div>', unsafe_allow_html=True)

    if _SECRET_PW:
        st.markdown('<div class="info-box">🔐 App Password φορτώθηκε αυτόματα από Streamlit Secrets.</div>', unsafe_allow_html=True)
        sales_pw = _SECRET_PW
    else:
        st.markdown('<div class="warn-box">⚠️ Δεν βρέθηκε <b>SALES_EMAIL_PASS</b> στα Secrets.</div>', unsafe_allow_html=True)
        sales_pw = st.text_input("🔐 Gmail App Password", type="password", key="sales_pw")

    col_test, col_inc, col_full = st.columns(3)
    run_test = col_test.button("🧪 Δοκιμή (10 Τελευταία)", use_container_width=True)
    run_inc  = col_inc.button("⚡ Γρήγορη (Νέα μόνο)", use_container_width=True)
    run_full = col_full.button("🔍 Βαθιά (2 χρόνια)", use_container_width=True)

    if run_test and sales_pw:
        with st.spinner("Ανάγνωση των 10 τελευταίων email & OCR... (Ασφαλής Λειτουργία)"):
            recs, errs, n_checked = fetch(sales_pw, since=None, limit=10)
            
        if errs:
            st.error(f"❌ Σφάλμα: {errs[0]}")
        else:
            if recs:
                st.success(f"✅ Η Δοκιμή πέτυχε! Διαβάστηκαν με επιτυχία {len(recs)} εγγραφές από τα PDF.")
                
                st.markdown("### 📊 Τι διάβασε το OCR (Αποτελέσματα Δοκιμής):")
                test_df = pd.DataFrame(recs)
                # Κρατάμε μόνο τη μία εγγραφή ανά ημερομηνία για τον πίνακα
                test_df = test_df.sort_values("net_sales", ascending=False).drop_duplicates("date").sort_values("date", ascending=False)
                
                test_display = test_df.copy()
                test_display["date"] = pd.to_datetime(test_display["date"]).dt.strftime("%d/%m/%Y")
                
                st.dataframe(
                    test_display.rename(columns={"date":"ΗΜΕΡΟΜΗΝΙΑ", "net_sales":"ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ", "customers":"ΠΕΛΑΤΕΣ", "avg_basket":"ΜΟ ΚΑΛΑΘΙΟΥ"})
                        .style.format({
                            "ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ": lambda v: fmt(v),
                            "ΜΟ ΚΑΛΑΘΙΟΥ": lambda v: fmt(v) if pd.notna(v) else "—",
                            "ΠΕΛΑΤΕΣ": lambda v: f"{int(v)}" if pd.notna(v) else "—"
                        }),
                    use_container_width=True, hide_index=True
                )
                
                saved = merge_in(recs)
                st.info(f"💾 Αποθηκεύτηκαν {saved} καθαρές εγγραφές στο ιστορικό σας.")
                
                if st.button("🔄 Ανανέωση Γραφημάτων", use_container_width=True):
                    st.rerun()
            else:
                st.warning(f"⚠️ Ελέγχθηκαν {n_checked} αρχεία PDF αλλά δεν μπόρεσε να διαβάσει δεδομένα. Δες αν τα αρχεία είναι σωστά.")

    elif run_inc and sales_pw:
        with st.spinner("Ανάγνωση πρόσφατων email & OCR... (Αυτόματη Επιτάχυνση Ενεργή)"):
            df_existing = load_cache()
            since_dt = (df_existing["date"].max() - timedelta(days=5)) if not df_existing.empty else None
            recs, errs, n_checked = fetch(sales_pw, since=since_dt, limit=40)
            
        if errs:
            st.error(f"❌ Σφάλμα: {errs[0]}")
        else:
            saved = merge_in(recs)
            if saved > 0:
                st.success(f"✅ Ενημερώθηκε! Αποθηκεύτηκαν {saved} νέες εγγραφές από {n_checked} ελεγμένα PDF.")
                st.rerun()
            else:
                st.markdown(f'<div class="info-box">✅ Ελέγχθηκαν {n_checked} αρχεία PDF — δεν βρέθηκαν νέα δεδομένα.</div>', unsafe_allow_html=True)

    elif run_full and sales_pw:
        st.markdown('<div class="warn-box">⏳ Βαθιά Σάρωση σε εξέλιξη. Η διαδικασία OCR θα διαρκέσει αρκετά. Μην κλείσετε τη σελίδα.</div>', unsafe_allow_html=True)
        prog_bar = st.progress(0)
        info_box = st.empty()

        for s in deep_scan(sales_pw):
            if s["err"]:
                info_box.error(f"Σφάλμα: {s['err']}")
                break
            
            ph = s["phase"]
            if ph == "connect":
                info_box.markdown('<div class="prog-wrap"><div class="prog-title">Σύνδεση στο email...</div></div>', unsafe_allow_html=True)
            elif ph == "listing":
                info_box.markdown('<div class="prog-wrap"><div class="prog-title">Ανάκτηση λίστας emails (2 έτη)...</div></div>', unsafe_allow_html=True)
            elif ph == "ocr":
                t = s["total"]; d = s["done"]
                pct = int(d/t*100) if t else 0
                prog_bar.progress(pct)
                info_box.markdown(f"""
                <div class="prog-wrap">
                  <div class="prog-title">OCR σε εξέλιξη: {d} / {t} emails ελέγχθηκαν</div>
                  <div class="prog-sub">💾 Έχουν αποθηκευτεί {s['saved']} εγγραφές μέχρι στιγμής... ({pct}%)</div>
                  <div class="prog-sub">Επεξεργασία: {s['cur']}</div>
                </div>""", unsafe_allow_html=True)

            if s["ok"]:
                prog_bar.progress(100)
                st.success(f"✅ Η βαθιά σάρωση ολοκληρώθηκε! Διαβάστηκαν {s['total']} emails και αποθηκεύτηκαν {s['saved']} εγγραφές.")
                break

    elif (run_test or run_inc or run_full) and not sales_pw:
        st.error("Εισάγετε App Password.")

    # Stats
    if not df.empty:
        st.markdown('<div class="sh">Στατιστικά Cache</div>', unsafe_allow_html=True)
        n_cache = len(pd.read_csv(SALES_CACHE)) if os.path.exists(SALES_CACHE) else 0
        n_arch  = len(pd.read_csv(SALES_ARCHIVE)) if os.path.exists(SALES_ARCHIVE) else 0
        oldest  = df["date"].min().strftime("%d/%m/%Y") if not df.empty else "—"
        newest  = df["date"].max().strftime("%d/%m/%Y") if not df.empty else "—"
        st.markdown(f"""<div class="kr kr4">
          <div class="kc" style="--a:#10b981"><div class="kl">Εγγραφές Cache</div><div class="kv">{n_cache}</div></div>
          <div class="kc" style="--a:#7c5abf"><div class="kl">Εγγραφές Archive</div><div class="kv">{n_arch}</div></div>
          <div class="kc" style="--a:#6b8fd4"><div class="kl">Από</div><div class="kv" style="font-size:.85rem;">{oldest}</div></div>
          <div class="kc" style="--a:#6b8fd4"><div class="kl">Έως</div><div class="kv" style="font-size:.85rem;">{newest}</div></div>
        </div>""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
