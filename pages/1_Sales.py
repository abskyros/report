import streamlit as st
import pandas as pd
import os, re, io
from datetime import datetime, date, timedelta
from imap_tools import MailBox, AND
from pdf2image import convert_from_bytes
import pytesseract

st.set_page_config(page_title="Πωλήσεις — AB Skyros", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

from gsheets_helper import load_sales, merge_sales

# ── CONFIG ────────────────────────────────────────────────────────────────────
SALES_EMAIL_USER   = "ftoulisgm@gmail.com"
SALES_EMAIL_SENDER = "abf.skyros@gmail.com"
SALES_SUBJECT_KW   = "ΑΒ ΣΚΥΡΟΣ"
BATCH_SIZE         = 25
DEEP_SCAN_YEARS    = 2

# ── SECRETS ───────────────────────────────────────────────────────────────────
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background:#f8f9fb!important;color:#111827!important;}
.stApp{background:#f8f9fb!important;}
section[data-testid="stSidebar"]{display:none!important;}
#MainMenu,footer,header{visibility:hidden!important;}
.block-container{padding:1.5rem 1.5rem 4rem!important;max-width:960px!important;margin:0 auto!important;}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:1px solid #e5e7eb;}
.ptitle{font-size:1.3rem;font-weight:700;color:#111827;}
.sh{font-size:.58rem;font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:#9ca3af;margin:1.8rem 0 .7rem;border-bottom:1px solid #f3f4f6;padding-bottom:.4rem;}
.kr{display:grid;gap:.75rem;margin:.5rem 0 1.2rem;}
.kr4{grid-template-columns:repeat(4,1fr);}
.kr3{grid-template-columns:repeat(3,1fr);}
@media(max-width:900px){.kr4{grid-template-columns:repeat(2,1fr);}}
@media(max-width:580px){.kr4,.kr3{grid-template-columns:1fr;}.block-container{padding:1rem 1rem 3rem!important;}}
.kc{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:.9rem 1rem;position:relative;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04);}
.kc::before{content:'';position:absolute;top:0;left:0;bottom:0;width:3px;background:var(--a,#10b981);}
.kl{font-size:.58rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#9ca3af;margin-bottom:.3rem;}
.kv{font-size:1.1rem;font-weight:700;color:#111827;}
.kv-green{color:#059669;}
.stButton>button{border-radius:9px!important;font-family:'Inter',sans-serif!important;font-size:.82rem!important;font-weight:600!important;padding:.6rem 1rem!important;transition:all .15s!important;}
.btn-g>button{background:#10b981!important;border:none!important;color:#fff!important;}
.btn-g>button:hover{opacity:.88!important;}
.btn-back>button{background:#fff!important;border:1px solid #d1d5db!important;color:#374151!important;}
[data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid #e5e7eb!important;gap:.2rem!important;}
[data-baseweb="tab"]{background:transparent!important;border:none!important;color:#6b7280!important;font-size:.74rem!important;font-weight:600!important;letter-spacing:.05em!important;text-transform:uppercase!important;padding:.5rem .9rem!important;border-radius:8px 8px 0 0!important;}
[aria-selected="true"][data-baseweb="tab"]{color:#10b981!important;background:#ecfdf5!important;border-bottom:2px solid #10b981!important;}
[data-testid="stDataFrame"]{border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;}
.info-box{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:10px;padding:.8rem 1rem;font-size:.73rem;color:#059669;margin:.6rem 0;}
.warn-box{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:.8rem 1rem;font-size:.73rem;color:#92400e;margin:.6rem 0;}
.prog-wrap{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:1rem;margin:.5rem 0;}
.prog-title{font-size:.75rem;font-weight:600;color:#0f172a;margin-bottom:.4rem;}
.prog-sub{font-size:.65rem;color:#94a3b8;margin-top:.35rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
MONTHS_GR = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    rounded = round(float(v), 2)
    if rounded == int(rounded):
        return f"{int(rounded):,}€".replace(",",".")
    return f"{rounded:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

def get_week_range(d):
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)

# ── OCR ENGINE V5 ─────────────────────────────────────────────────────────────
def _num(s: str):
    if not s: return None
    s = s.strip().replace(" ","").replace("€","").rstrip(".,")
    if not s: return None
    if "." in s and "," in s:
        s = s.replace(".","").replace(",",".") if s.rfind(",") > s.rfind(".") else s.replace(",","")
    elif "," in s:
        s = s.replace(",",".")
    try: return float(s)
    except: return None

def _find(txt: str, patterns: list, lo=None, hi=None, exclude=None):
    for pat in patterns:
        m = re.search(pat, txt, re.IGNORECASE)
        if m:
            try:
                v = _num(m.group(1))
                if v is None: continue
                if lo is not None and v < lo: continue
                if hi is not None and v > hi: continue
                if exclude and any(abs(v - ex) < 0.5 for ex in exclude): continue
                return v
            except: continue
    return None

_NS_EXCLUDE = [1082.0]
_YEAR_GUARD = set(range(2018, 2032))

def _ocr_page(img):
    cfg = "--psm 6 --oem 3"
    t = pytesseract.image_to_string(img, lang="ell+eng", config=cfg)
    if any(k in t for k in ("NetDay","TotSal","Run On","un On","Totals","NumOf","For ")):
        return t
    return pytesseract.image_to_string(img.rotate(90, expand=True), lang="ell+eng", config=cfg)

def extract(pdf_bytes: bytes) -> dict:
    r = {"date":None,"net_sales":None,"customers":None,"avg_basket":None}
    try:
        images = convert_from_bytes(pdf_bytes, dpi=250, first_page=1, last_page=6)
        if not images: return r
        txt = "\n".join(_ocr_page(img) for img in images)

        m = re.search(r'[Rr]?[Uu]n\s*[Oo0]n\s*[;:\s]+?(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', txt, re.IGNORECASE)
        if m:
            try: r["date"] = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except: pass
        if not r["date"]:
            m = re.search(r'(?:^|\s)[Ff][Oo0]r\s+(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', txt, re.MULTILINE)
            if m:
                try: r["date"] = date(int(m.group(3)), int(m.group(2)), int(m.group(1))) - timedelta(days=1)
                except: pass

        m = re.search(
            r'[Tt]otals?\s*:?\s*([\d.,]{4,10})\s+100[.,]00\s+(\d{2,4})'
            r'\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+\s+([\d.,]{3,7})\s+\d+', txt)
        if m:
            ns  = _num(m.group(1))
            cus = int(m.group(2))
            ab  = _num(m.group(3))
            if ns and 2000 < ns < 80000 and ns not in _NS_EXCLUDE:
                r["net_sales"] = ns
            if 50 < cus < 2000 and cus not in _YEAR_GUARD:
                r["customers"] = cus
            if ab and 5 < ab < 200:
                r["avg_basket"] = ab

        clean = re.sub(r'\s+', '', txt).upper()

        if not r["net_sales"]:
            r["net_sales"] = _find(txt, [
                r'NetDaySalDis\s+([\d.,]+)',
                r'Ne[t7][Dd]ay[Ss]al[Dd][i1][s5]\s+([\d.,]+)',
                r'Ne[i1]tDay[Ss]al[Dd][i1][s5]\s+([\d.,]+)',
            ], lo=2000, hi=80000, exclude=_NS_EXCLUDE)

        if not r["customers"]:
            m = re.search(r'Num[O0]fCus\s+([\d.,\s]+)', txt, re.IGNORECASE)
            if m:
                try:
                    raw = re.sub(r'[.,\s]', '', m.group(1).strip())
                    v = int(raw)
                    if 50 < v < 2000 and v not in _YEAR_GUARD:
                        r["customers"] = v
                except: pass

        if not r["avg_basket"]:
            r["avg_basket"] = _find(txt, [
                r'AvgSalCus\s+([\d.,]+)',
                r'Avg[Ss]a[il][Cc]us\s+([\d.,]+)',
            ], lo=5, hi=200)

        if r["net_sales"] and (not r["customers"] or not r["avg_basket"]):
            nums = [v for x in re.findall(r'\d+[.,\d]*', txt)
                    if (v := _num(x)) is not None]
            for i, v in enumerate(nums):
                if abs(v - r["net_sales"]) < 0.02:
                    for j in range(i+1, min(i+15, len(nums))):
                        nv = nums[j]
                        if not r["customers"] and 50 < nv < 2000 and float(nv).is_integer() and int(nv) not in _YEAR_GUARD:
                            r["customers"] = int(nv)
                        elif r["customers"] and not r["avg_basket"] and 5 < nv < 200:
                            r["avg_basket"] = nv; break
                    break
    except Exception: pass
    return r

# ── EMAIL FETCHING ─────────────────────────────────────────────────────────────
def _is_valid(subj):
    s = (subj or "").upper()
    return SALES_SUBJECT_KW in s or "SKYROS" in s

def fetch(pw, since: date | None = None, want_records: int = 60, email_scan_limit: int = 400):
    recs, errs, n = [], [], 0
    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, pw) as mb:
            for msg in mb.fetch(AND(from_=SALES_EMAIL_SENDER), limit=email_scan_limit, reverse=True, mark_seen=False):
                if len(recs) >= want_records: break
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
                s["done"] = i+1; s["cur"] = (h.subject or "")[:50]; yield s.copy()
                try:
                    full = list(mb.fetch(AND(uid=str(h.uid)), mark_seen=False))
                    if not full: continue
                    pdf = next((a for a in full[0].attachments if a.filename and a.filename.lower().endswith(".pdf")), None)
                    if not pdf: continue
                    rec = extract(pdf.payload)
                    if rec["date"] and rec["net_sales"] is not None:
                        batch.append(rec)
                    if len(batch) >= BATCH_SIZE:
                        s["saved"] += merge_sales(batch); batch = []; yield s.copy()
                except: continue
            if batch: s["saved"] += merge_sales(batch)
            s["ok"] = True; yield s.copy()
    except Exception as e:
        s["err"] = str(e); s["ok"] = True; yield s.copy()

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
df    = load_sales()
today = date.today()

import time as _time
# Auto-sync αφαιρέθηκε — έκανε OCR στο page load και κολλούσε η σελίδα.
# Ενημέρωση μόνο από την καρτέλα "Ενημέρωση".

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
                disp.rename(columns={"date":"ΗΜΕΡΟΜΗΝΙΑ","net_sales":"ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ","customers":"ΠΕΛΑΤΕΣ","avg_basket":"ΜΟ ΚΑΛΑΘΙΟΥ"})
                    .style.format({
                        "ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ": lambda v: fmt(v),
                        "ΜΟ ΚΑΛΑΘΙΟΥ":       lambda v: fmt(v) if pd.notna(v) else "—",
                        "ΠΕΛΑΤΕΣ":           lambda v: f"{int(v)}" if pd.notna(v) else "—"
                    }),
                use_container_width=True, hide_index=True)
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
                disp.rename(columns={"date":"ΗΜΕΡΟΜΗΝΙΑ","net_sales":"ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ","customers":"ΠΕΛΑΤΕΣ","avg_basket":"ΜΟ ΚΑΛΑΘΙΟΥ"})
                    .style.format({
                        "ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ": lambda v: fmt(v),
                        "ΜΟ ΚΑΛΑΘΙΟΥ":       lambda v: fmt(v) if pd.notna(v) else "—",
                        "ΠΕΛΑΤΕΣ":           lambda v: f"{int(v)}" if pd.notna(v) else "—"
                    }),
                use_container_width=True, hide_index=True)

            csv = m_df.rename(columns={"date":"ΗΜΕΡΟΜΗΝΙΑ","net_sales":"ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ","customers":"ΠΕΛΑΤΕΣ","avg_basket":"ΜΟ ΚΑΛΑΘΙΟΥ"}).to_csv(index=False).encode("utf-8-sig")
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
    run_inc  = col_inc.button("⚡ Γρήγορη (Νέα μόνο)",    use_container_width=True)
    run_full = col_full.button("🔍 Βαθιά (2 χρόνια)",     use_container_width=True)

    if run_test and sales_pw:
        with st.spinner("Ανάγνωση των 10 τελευταίων email & OCR..."):
            recs, errs, n_checked = fetch(sales_pw, since=None, want_records=10, email_scan_limit=100)
        if errs:
            st.error(f"❌ Σφάλμα: {errs[0]}")
        else:
            if recs:
                st.success(f"✅ Η Δοκιμή πέτυχε! Διαβάστηκαν {len(recs)} εγγραφές.")
                test_df = pd.DataFrame(recs)
                test_df = test_df.sort_values("net_sales", ascending=False).drop_duplicates("date").sort_values("date", ascending=False)
                test_display = test_df.copy()
                test_display["date"] = pd.to_datetime(test_display["date"]).dt.strftime("%d/%m/%Y")
                st.dataframe(
                    test_display.rename(columns={"date":"ΗΜΕΡΟΜΗΝΙΑ","net_sales":"ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ","customers":"ΠΕΛΑΤΕΣ","avg_basket":"ΜΟ ΚΑΛΑΘΙΟΥ"})
                        .style.format({
                            "ΚΑΘΑΡΕΣ ΠΩΛΗΣΕΙΣ": lambda v: fmt(v),
                            "ΜΟ ΚΑΛΑΘΙΟΥ":       lambda v: fmt(v) if pd.notna(v) else "—",
                            "ΠΕΛΑΤΕΣ":           lambda v: f"{int(v)}" if pd.notna(v) else "—"
                        }),
                    use_container_width=True, hide_index=True)
                saved = merge_sales(recs)
                st.info(f"💾 Αποθηκεύτηκαν {saved} νέες εγγραφές στο Google Sheets.")
                if st.button("🔄 Ανανέωση Γραφημάτων", use_container_width=True):
                    st.rerun()
            else:
                st.warning(f"⚠️ Ελέγχθηκαν {n_checked} αρχεία PDF αλλά δεν μπόρεσε να διαβάσει δεδομένα.")

    elif run_inc and sales_pw:
        with st.spinner("Ανάγνωση πρόσφατων email & OCR..."):
            existing = load_sales()
            since_dt = (existing["date"].max() - timedelta(days=5)) if not existing.empty else None
            recs, errs, n_checked = fetch(sales_pw, since=since_dt, want_records=30, email_scan_limit=150)
        if errs:
            st.error(f"❌ Σφάλμα: {errs[0]}")
        else:
            saved = merge_sales(recs)
            if saved > 0:
                st.success(f"✅ Ενημερώθηκε! {saved} νέες εγγραφές από {n_checked} PDF.")
                st.rerun()
            else:
                st.markdown(f'<div class="info-box">✅ Ελέγχθηκαν {n_checked} αρχεία PDF — δεν βρέθηκαν νέα δεδομένα.</div>', unsafe_allow_html=True)

    elif run_full and sales_pw:
        st.markdown('<div class="warn-box">⏳ Βαθιά Σάρωση σε εξέλιξη. Μην κλείσετε τη σελίδα.</div>', unsafe_allow_html=True)
        prog_bar = st.progress(0)
        info_box = st.empty()
        for s in deep_scan(sales_pw):
            if s["err"]:
                info_box.error(f"Σφάλμα: {s['err']}"); break
            ph = s["phase"]
            if ph == "connect":
                info_box.markdown('<div class="prog-wrap"><div class="prog-title">Σύνδεση στο email...</div></div>', unsafe_allow_html=True)
            elif ph == "listing":
                info_box.markdown('<div class="prog-wrap"><div class="prog-title">Ανάκτηση λίστας emails (2 έτη)...</div></div>', unsafe_allow_html=True)
            elif ph == "ocr":
                t = s["total"]; d = s["done"]
                pct = int(d/t*100) if t else 0
                prog_bar.progress(pct)
                info_box.markdown(f"""<div class="prog-wrap">
                  <div class="prog-title">OCR: {d} / {t} emails</div>
                  <div class="prog-sub">💾 {s['saved']} εγγραφές αποθηκεύτηκαν ({pct}%)</div>
                  <div class="prog-sub">Επεξεργασία: {s['cur']}</div>
                </div>""", unsafe_allow_html=True)
            if s["ok"]:
                prog_bar.progress(100)
                st.success(f"✅ Ολοκληρώθηκε! {s['total']} emails → {s['saved']} εγγραφές στο Google Sheets.")
                break

    elif (run_test or run_inc or run_full) and not sales_pw:
        st.error("Εισάγετε App Password.")

    if not df.empty:
        st.markdown('<div class="sh">Στατιστικά Google Sheets</div>', unsafe_allow_html=True)
        oldest = df["date"].min().strftime("%d/%m/%Y")
        newest = df["date"].max().strftime("%d/%m/%Y")
        st.markdown(f"""<div class="kr kr3">
          <div class="kc" style="--a:#10b981"><div class="kl">Σύνολο Εγγραφών</div><div class="kv">{len(df)}</div></div>
          <div class="kc" style="--a:#6b8fd4"><div class="kl">Από</div><div class="kv" style="font-size:.85rem;">{oldest}</div></div>
          <div class="kc" style="--a:#6b8fd4"><div class="kl">Έως</div><div class="kv" style="font-size:.85rem;">{newest}</div></div>
        </div>""", unsafe_allow_html=True)
