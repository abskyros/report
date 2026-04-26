import streamlit as st
import pandas as pd
import os, re, io
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
TEST_EMAIL_LIMIT   = 20    # Αριθμός emails για δοκιμαστική λειτουργία
DEEP_SCAN_YEARS    = 2

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
    margin: 1.8rem 0 .7rem;
    border-bottom: 1px solid #f3f4f6;
    padding-bottom: .4rem;
}
.kr { display: grid; gap: .75rem; margin: .5rem 0 1.2rem; }
.kr4 { grid-template-columns: repeat(4,1fr); }
.kr3 { grid-template-columns: repeat(3,1fr); }
.kr2 { grid-template-columns: repeat(2,1fr); }
@media(max-width:900px) { .kr4 { grid-template-columns: repeat(2,1fr); } }
@media(max-width:580px) {
    .kr4, .kr3, .kr2 { grid-template-columns: 1fr; }
    .block-container { padding: 1rem 1rem 3rem !important; }
}
.kc {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: .9rem 1rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.kc::before {
    content: '';
    position: absolute; top: 0; left: 0; bottom: 0;
    width: 3px;
    background: var(--a, #10b981);
}
.kl {
    font-size: .58rem; font-weight: 600; letter-spacing: .1em;
    text-transform: uppercase; color: #9ca3af; margin-bottom: .3rem;
}
.kv { font-size: 1.1rem; font-weight: 700; color: #111827; }
.kv-sm { font-size: .9rem; font-weight: 700; color: #111827; }
.kdelta-up { font-size: .65rem; color: #059669; margin-top: .15rem; }
.kdelta-dn { font-size: .65rem; color: #dc2626; margin-top: .15rem; }

.stButton > button {
    border-radius: 9px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: .82rem !important;
    font-weight: 600 !important;
    padding: .6rem 1rem !important;
    transition: all .15s !important;
}
.btn-g > button { background: #10b981 !important; border: none !important; color: #fff !important; }
.btn-g > button:hover { opacity: .88 !important; }
.btn-back > button {
    background: #fff !important;
    border: 1px solid #d1d5db !important;
    color: #374151 !important;
}
[data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #e5e7eb !important;
    gap: .2rem !important;
}
[data-baseweb="tab"] {
    background: transparent !important; border: none !important;
    color: #6b7280 !important; font-size: .74rem !important;
    font-weight: 600 !important; letter-spacing: .05em !important;
    text-transform: uppercase !important; padding: .5rem .9rem !important;
    border-radius: 8px 8px 0 0 !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #10b981 !important;
    background: #ecfdf5 !important;
    border-bottom: 2px solid #10b981 !important;
}
[data-testid="stDataFrame"] { border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; }
.info-box {
    background: #ecfdf5; border: 1px solid #a7f3d0;
    border-radius: 10px; padding: .8rem 1rem;
    font-size: .73rem; color: #059669; margin: .6rem 0;
}
.warn-box {
    background: #fffbeb; border: 1px solid #fde68a;
    border-radius: 10px; padding: .8rem 1rem;
    font-size: .73rem; color: #92400e; margin: .6rem 0;
}
.test-box {
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-radius: 10px; padding: .8rem 1rem;
    font-size: .73rem; color: #1d4ed8; margin: .6rem 0;
}
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
MONTHS_GR = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

def parse_greek_number(s):
    s = str(s).strip().replace(" ","").replace("€","")
    if "." in s and "," in s:
        s = s.replace(".","").replace(",",".")
    elif "," in s:
        s = s.replace(",",".")
    return float(s)

def load_cache():
    if os.path.exists(SALES_CACHE):
        df = pd.read_csv(SALES_CACHE)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
            return df.sort_values("date", ascending=False).reset_index(drop=True)
    return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])

def save_cache(df):
    cutoff = date.today() - timedelta(days=365*DEEP_SCAN_YEARS)
    recent = df[df["date"] >= cutoff].copy()
    old    = df[df["date"]  < cutoff].copy()
    recent.to_csv(SALES_CACHE, index=False)
    if not old.empty:
        if os.path.exists(SALES_ARCHIVE):
            ex = pd.read_csv(SALES_ARCHIVE)
            ex["date"] = pd.to_datetime(ex["date"]).dt.date
            old = pd.concat([ex, old]).drop_duplicates("date").sort_values("date", ascending=False)
        old.to_csv(SALES_ARCHIVE, index=False)

def load_all():
    parts = []
    for f in [SALES_CACHE, SALES_ARCHIVE]:
        if os.path.exists(f):
            df = pd.read_csv(f)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"]).dt.date
                parts.append(df)
    if parts:
        return pd.concat(parts).drop_duplicates("date").sort_values("date", ascending=False).reset_index(drop=True)
    return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])

def extract_sales_from_pdf(pdf_bytes):
    """Εξαγωγή δεδομένων από Department Report PDF"""
    result = {"date": None, "net_sales": None, "customers": None, "avg_basket": None}
    try:
        images    = convert_from_bytes(pdf_bytes, dpi=220)
        full_text = ""
        for img in images:
            full_text += pytesseract.image_to_string(img, lang="ell+eng") + "\n"

        # Ημερομηνία: "For  25/04/2026"
        for pat in [
            r'[Ff]or\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'[Ff]or\s*[:\-]?\s*(\d{1,2}\.\d{1,2}\.\d{4})',
            r'(\d{2}/\d{2}/\d{4})',
        ]:
            m = re.search(pat, full_text)
            if m:
                try:
                    result["date"] = datetime.strptime(
                        m.group(1).replace(".","/"  ), "%d/%m/%Y"
                    ).date()
                    break
                except: pass

        # Καθαρές πωλήσεις: NeitDaySalDis
        for pat in [
            r'[Nn]e[it]{1,3}[Dd]ay[Ss]al[Dd]is\s+([\d.,]+)',
            r'[Nn]et[Dd]ay[Ss]al[Dd]is\s+([\d.,]+)',
        ]:
            m = re.search(pat, full_text)
            if m:
                try: result["net_sales"] = parse_greek_number(m.group(1)); break
                except: pass

        # Fallback: Hourly Totals
        if result["net_sales"] is None:
            m = re.search(r'[Tt]otals?\s*[:\-]?\s*([\d.,]+)\s+100[.,]00\s+([\d]+)', full_text)
            if m:
                try:
                    result["net_sales"] = parse_greek_number(m.group(1))
                    if result["customers"] is None:
                        result["customers"] = int(m.group(2))
                except: pass

        # Fallback: GroupTot
        if result["net_sales"] is None:
            m = re.search(r'[Gg]roup[Tt]ot\s+([\d.,]+)\s+([\d.,]+)', full_text)
            if m:
                try: result["net_sales"] = parse_greek_number(m.group(2))
                except: pass

        # Πελάτες: NumItmSold
        if result["customers"] is None:
            m = re.search(r'[Nn]um[Ii]tm[Ss]old\s+([\d,.]+)', full_text)
            if m:
                try: result["customers"] = int(m.group(1).replace(",","").replace(".","").strip())
                except: pass

        # ΜΟ Καλαθιού: AvgItmPerCus
        for pat in [
            r'[Aa]vg[Ii]tm[Pp]er[Cc]us\s+([\d.,]+)',
            r'[Aa]vg[Ii]tm[Pp]ric\s+([\d.,]+)',
        ]:
            m = re.search(pat, full_text)
            if m:
                try: result["avg_basket"] = parse_greek_number(m.group(1)); break
                except: pass

    except Exception as e:
        st.warning(f"OCR error: {e}")
    return result

def fetch_emails(password, mode="test"):
    """
    mode='test'  → μόνο τα τελευταία 20 emails (για δοκιμή)
    mode='quick' → emails μετά την τελευταία ημερομηνία
    mode='deep'  → emails τελευταίων 2 ετών
    """
    df_existing = load_cache()
    new_records = []
    errors      = []
    emails_checked = 0

    if mode == "test":
        limit = TEST_EMAIL_LIMIT
        since_date = None
    elif mode == "quick":
        limit = 200
        if not df_existing.empty:
            last_dt   = df_existing["date"].min()
            since_date = last_dt - timedelta(days=3)
        else:
            since_date = None
    else:  # deep
        limit = 1000
        since_date = date.today() - timedelta(days=365*DEEP_SCAN_YEARS)

    try:
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, password) as mb:
            criteria = AND(from_=SALES_EMAIL_SENDER)
            messages = list(mb.fetch(criteria, limit=limit, reverse=True))

            for msg in messages:
                emails_checked += 1
                msg_date = msg.date.date() if msg.date else None

                # Skip αν πολύ παλιό
                if since_date and msg_date and msg_date < since_date:
                    continue

                # Έλεγχος subject
                subj = (msg.subject or "").upper()
                if SALES_SUBJECT_KW not in subj and "SKYROS" not in subj:
                    continue

                # Ένα PDF ανά email
                pdf_att = next(
                    (a for a in msg.attachments
                     if a.filename and a.filename.lower().endswith(".pdf")),
                    None
                )
                if not pdf_att:
                    continue

                rec = extract_sales_from_pdf(pdf_att.payload)
                if rec["date"] and rec["net_sales"] is not None:
                    # Skip αν ήδη στο cache
                    if not df_existing.empty and rec["date"] in df_existing["date"].values:
                        continue
                    new_records.append(rec)

    except Exception as e:
        errors.append(str(e))

    return new_records, errors, emails_checked

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
df    = load_all()
today = date.today()
week_start = today - timedelta(days=today.weekday())
week_end   = week_start + timedelta(days=6)
week_lbl   = f"{week_start.strftime('%d/%m')} – {week_end.strftime('%d/%m')}"

# ── RENDER ───────────────────────────────────────────────────────────────────
# Topbar
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

# ═══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    if df.empty:
        st.markdown('<div class="warn-box">⚠️ Δεν υπάρχουν δεδομένα. Μεταβείτε στην καρτέλα <b>ΕΝΗΜΕΡΩΣΗ</b>.</div>', unsafe_allow_html=True)
    else:
        last = df.iloc[0]
        prev = df.iloc[1] if len(df) > 1 else None

        def delta_html(now, pv, cls_up="kdelta-up", cls_dn="kdelta-dn"):
            if pv is None or (isinstance(pv, float) and pd.isna(pv)) or pv == 0: return ""
            d = float(now) - float(pv); pct = d/float(pv)*100
            sym = "▲" if d >= 0 else "▼"
            cls = cls_up if d >= 0 else cls_dn
            return f'<div class="{cls}">{sym} {abs(pct):.1f}%</div>'

        p_ns  = prev["net_sales"]  if prev is not None else None
        p_cu  = prev["customers"]  if prev is not None and pd.notna(prev.get("customers")) else None
        p_ab  = prev["avg_basket"] if prev is not None and pd.notna(prev.get("avg_basket")) else None
        days_old = (today - last["date"]).days
        date_lbl = last["date"].strftime("%d/%m/%Y")

        # ─── Τελευταία Ημέρα ──────────────────────────────────────────────────
        st.markdown('<div class="sh">Τελευταία Ημέρα</div>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class="kc" style="--a:#10b981">
              <div class="kl">Πωλήσεις · {date_lbl}</div>
              <div class="kv">{fmt(last['net_sales'])}</div>
              {delta_html(last['net_sales'], p_ns)}
            </div>""", unsafe_allow_html=True)
        with c2:
            cust_val = int(last["customers"]) if pd.notna(last.get("customers")) else "—"
            st.markdown(f"""<div class="kc" style="--a:#7c3aed">
              <div class="kl">Πελάτες</div>
              <div class="kv">{cust_val}</div>
              {delta_html(cust_val if cust_val != '—' else 0, p_cu)}
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="kc" style="--a:#3b82f6">
              <div class="kl">ΜΟ Καλαθιού</div>
              <div class="kv">{fmt(last.get('avg_basket'))}</div>
              {delta_html(last.get('avg_basket') or 0, p_ab)}
            </div>""", unsafe_allow_html=True)
        with c4:
            upd = "Σήμερα" if days_old==0 else f"Πριν {days_old}μ."
            st.markdown(f"""<div class="kc" style="--a:#f59e0b">
              <div class="kl">Τελευταία Ενημέρωση</div>
              <div class="kv kv-sm">{upd}</div>
            </div>""", unsafe_allow_html=True)

        # ─── Τρέχουσα Εβδομάδα ────────────────────────────────────────────────
        st.markdown(f'<div class="sh">Τρέχουσα Εβδομάδα · {week_lbl}</div>', unsafe_allow_html=True)

        w_df  = df[(df["date"] >= week_start) & (df["date"] <= today)]
        w_tot = w_df["net_sales"].sum() if not w_df.empty else 0
        w_avg = w_df["net_sales"].mean() if not w_df.empty else 0
        w_days = len(w_df)

        # Προηγούμενη εβδομάδα
        pw_start = week_start - timedelta(days=7)
        pw_end   = week_start - timedelta(days=1)
        pw_df    = df[(df["date"] >= pw_start) & (df["date"] <= pw_end)]
        pw_tot   = pw_df["net_sales"].sum() if not pw_df.empty else None

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="kc" style="--a:#10b981">
              <div class="kl">Σύνολο Εβδομάδας</div>
              <div class="kv">{fmt(w_tot)}</div>
              {delta_html(w_tot, pw_tot)}
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="kc" style="--a:#3b82f6">
              <div class="kl">Ημερήσιος ΜΟ</div>
              <div class="kv">{fmt(w_avg)}</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="kc" style="--a:#7c3aed">
              <div class="kl">Ημέρες με δεδομένα</div>
              <div class="kv">{w_days} / 7</div>
            </div>""", unsafe_allow_html=True)

        # ─── Τρέχων Μήνας ─────────────────────────────────────────────────────
        st.markdown(f'<div class="sh">Τρέχων Μήνας · {MONTHS_GR[today.month-1]} {today.year}</div>', unsafe_allow_html=True)
        m_df  = df[(df["date"] >= date(today.year, today.month, 1)) & (df["date"] <= today)]
        m_tot = m_df["net_sales"].sum() if not m_df.empty else 0
        m_avg = m_df["net_sales"].mean() if not m_df.empty else 0

        first_this = date(today.year, today.month, 1)
        last_prev  = first_this - timedelta(days=1)
        pm_df      = df[(df["date"] >= date(last_prev.year, last_prev.month, 1)) & (df["date"] <= last_prev)]
        pm_tot     = pm_df["net_sales"].sum() if not pm_df.empty else None

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="kc" style="--a:#10b981">
              <div class="kl">Σύνολο Μήνα</div>
              <div class="kv">{fmt(m_tot)}</div>
              {delta_html(m_tot, pm_tot)}
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="kc" style="--a:#3b82f6">
              <div class="kl">Ημερήσιος ΜΟ</div>
              <div class="kv">{fmt(m_avg)}</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="kc" style="--a:#7c3aed">
              <div class="kl">Ημέρες με δεδομένα</div>
              <div class="kv">{len(m_df)}</div>
            </div>""", unsafe_allow_html=True)

        # ─── Chart ────────────────────────────────────────────────────────────
        st.markdown('<div class="sh">Τελευταίες 14 ημέρες</div>', unsafe_allow_html=True)
        ch = df[df["date"] >= (today - timedelta(days=13))].sort_values("date").copy()
        if not ch.empty:
            ch.index = ch["date"].apply(lambda d: d.strftime("%d/%m"))
            st.bar_chart(ch["net_sales"], color="#10b981", height=200)

# ═══════════════════════════════════════════════════════════════════════════════
with tab_hist:
    if df.empty:
        st.markdown('<div class="warn-box">Δεν υπάρχουν δεδομένα.</div>', unsafe_allow_html=True)
    else:
        c1, c2 = st.columns(2)
        with c1:
            years = sorted({r.year for r in df["date"]}, reverse=True)
            sel_y = st.selectbox("Έτος", years)
        with c2:
            sel_m = st.selectbox("Μήνας", range(1,13), format_func=lambda x: MONTHS_GR[x-1], index=today.month-1)

        filt = df[(df["date"].apply(lambda d: d.year) == sel_y) &
                  (df["date"].apply(lambda d: d.month) == sel_m)].copy()

        if not filt.empty:
            tot = filt["net_sales"].sum()
            avg = filt["net_sales"].mean()
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""<div class="kc" style="--a:#10b981">
                  <div class="kl">Σύνολο</div><div class="kv">{fmt(tot)}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="kc" style="--a:#3b82f6">
                  <div class="kl">Ημ. ΜΟ</div><div class="kv">{fmt(avg)}</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="kc" style="--a:#7c3aed">
                  <div class="kl">Ημέρες</div><div class="kv">{len(filt)}</div>
                </div>""", unsafe_allow_html=True)

            disp = filt.copy()
            disp["date"] = disp["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
            disp.columns = ["Ημερομηνία","Καθαρές Πωλήσεις","Πελάτες","ΜΟ Καλαθιού"]
            st.dataframe(disp, use_container_width=True, hide_index=True)
            csv = filt.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 Λήψη CSV", csv, f"sales_{sel_y}_{sel_m:02d}.csv", "text/csv")
        else:
            st.markdown('<div class="warn-box">Δεν υπάρχουν δεδομένα για αυτή την περίοδο.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
with tab_update:
    st.markdown('<div class="sh">Σύνδεση Email</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="info-box">📧 Λογαριασμός: <b>{SALES_EMAIL_USER}</b> — Χρησιμοποιήστε <b>App Password</b> του Gmail.</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="test-box">🧪 <b>Δοκιμαστική λειτουργία:</b> Η "Δοκιμή 20 Emails" διαβάζει μόνο τα τελευταία {TEST_EMAIL_LIMIT} emails για γρήγορο έλεγχο. Μετά χρησιμοποιήστε "Βαθιά Σάρωση" για όλα.</div>', unsafe_allow_html=True)

    password = st.text_input("🔐 Gmail App Password", type="password", key="sales_pw")

    c1, c2, c3 = st.columns(3)
    run_test  = c1.button(f"🧪 Δοκιμή {TEST_EMAIL_LIMIT} Emails", use_container_width=True)
    run_quick = c2.button("⚡ Γρήγορη (Νέα μόνο)", use_container_width=True)
    run_deep  = c3.button("🔍 Βαθιά Σάρωση (2 χρόνια)", use_container_width=True)

    mode = None
    if run_test:  mode = "test"
    if run_quick: mode = "quick"
    if run_deep:  mode = "deep"

    if mode and password:
        labels = {"test": f"Δοκιμή τελευταίων {TEST_EMAIL_LIMIT} emails...",
                  "quick": "Φόρτωση νέων emails...",
                  "deep": "Βαθιά σάρωση 2 ετών..."}
        with st.spinner(labels[mode]):
            new_recs, errs, checked = fetch_emails(password, mode=mode)

        if errs:
            st.error(f"❌ Σφάλμα σύνδεσης: {errs[0]}")
        else:
            st.markdown(f'<div class="info-box">📬 Ελέγχθηκαν: <b>{checked}</b> emails</div>', unsafe_allow_html=True)
            if not new_recs:
                st.markdown('<div class="info-box">✅ Δεν βρέθηκαν νέα δεδομένα — το σύστημα είναι ενημερωμένο.</div>', unsafe_allow_html=True)
            else:
                st.success(f"✅ Βρέθηκαν {len(new_recs)} νέες εγγραφές!")

                # Εμφάνιση προεπισκόπησης
                prev_df = pd.DataFrame(new_recs)
                prev_df["date"] = prev_df["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
                st.dataframe(prev_df, use_container_width=True, hide_index=True)

                # Αποθήκευση
                old_df = load_cache()
                all_new = pd.DataFrame(new_recs)
                merged  = pd.concat([old_df, all_new]).drop_duplicates("date").sort_values("date", ascending=False).reset_index(drop=True)
                save_cache(merged)
                st.rerun()

    elif mode and not password:
        st.error("⚠️ Εισάγετε App Password.")

    # Χειροκίνητη εισαγωγή
    st.markdown('<div class="sh">Χειροκίνητη Εισαγωγή</div>', unsafe_allow_html=True)
    with st.form("manual_sales"):
        c1, c2, c3, c4 = st.columns(4)
        with c1: entry_date = st.date_input("Ημερομηνία", value=today)
        with c2: net_s = st.number_input("Καθαρές Πωλήσεις (€)", min_value=0.0, step=0.01, format="%.2f")
        with c3: custs = st.number_input("Πελάτες", min_value=0, step=1)
        with c4: avg_b = st.number_input("ΜΟ Καλαθιού (€)", min_value=0.0, step=0.01, format="%.2f")
        if st.form_submit_button("✅ Αποθήκευση", use_container_width=True):
            new_row = pd.DataFrame([{"date": entry_date, "net_sales": net_s,
                                     "customers": custs if custs > 0 else None,
                                     "avg_basket": avg_b if avg_b > 0 else None}])
            old_df  = load_cache()
            merged  = pd.concat([old_df, new_row]).drop_duplicates("date").sort_values("date", ascending=False).reset_index(drop=True)
            save_cache(merged)
            st.success(f"✅ Αποθηκεύτηκε: {entry_date.strftime('%d/%m/%Y')} — {fmt(net_s)}")
            st.rerun()
