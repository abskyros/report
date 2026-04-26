import streamlit as st
import pandas as pd
import os, re, io
from datetime import datetime, date, timedelta
from imap_tools import MailBox, AND
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image

st.set_page_config(page_title="Πωλήσεις — AB Σκύρος", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

# ── CONFIG ────────────────────────────────────────────────────────────────────
SALES_EMAIL_USER   = "ftoulisgm@gmail.com"
SALES_EMAIL_SENDER = "abf.skyros@gmail.com"
SALES_SUBJECT_KW   = "ΑΒ ΣΚΥΡΟΣ"
SALES_CACHE        = "sales_cache.csv"
SALES_ARCHIVE      = "sales_archive.csv"   # παλαιότερα από 2 χρόνια
DEEP_SCAN_YEARS    = 2                     # βαθιά σάρωση τελευταίων 2 ετών

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
.kd{font-size:.62rem;color:#6b7280;margin-top:.1rem;}
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
</style>
""", unsafe_allow_html=True)

# ── HELPERS ───────────────────────────────────────────────────────────────────
MONTHS_GR = ["Ιαν","Φεβ","Μαρ","Απρ","Μαι","Ιουν","Ιουλ","Αυγ","Σεπ","Οκτ","Νοε","Δεκ"]

def fmt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}€".replace(",","X").replace(".",",").replace("X",".")

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
            existing = pd.read_csv(SALES_ARCHIVE)
            existing["date"] = pd.to_datetime(existing["date"]).dt.date
            old = pd.concat([existing, old]).drop_duplicates("date").sort_values("date", ascending=False)
        old.to_csv(SALES_ARCHIVE, index=False)

def load_all():
    parts = []
    if os.path.exists(SALES_CACHE):
        df = pd.read_csv(SALES_CACHE)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
            parts.append(df)
    if os.path.exists(SALES_ARCHIVE):
        df = pd.read_csv(SALES_ARCHIVE)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
            parts.append(df)
    if parts:
        return pd.concat(parts).drop_duplicates("date").sort_values("date", ascending=False).reset_index(drop=True)
    return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])

def parse_greek_number(s):
    s = s.strip().replace(" ", "").replace("€", "")
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    return float(s)

def extract_sales_from_pdf(pdf_bytes):
    result = {"date": None, "net_sales": None, "customers": None, "avg_basket": None}
    try:
        images    = convert_from_bytes(pdf_bytes, dpi=220)
        full_text = ""
        for img in images:
            full_text += pytesseract.image_to_string(img, lang="ell+eng") + "\n"

        # DATE
        date_patterns = [
            r'[Ff]or\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'[Ff]or\s*[:\-]?\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        ]
        for pat in date_patterns:
            m = re.search(pat, full_text)
            if m:
                raw = m.group(1).replace(".", "/")
                try:
                    result["date"] = datetime.strptime(raw, "%d/%m/%Y").date()
                    break
                except:
                    pass

        if result["date"] is None:
            m = re.search(r'(\d{2}/\d{2}/\d{4})', full_text)
            if m:
                try: result["date"] = datetime.strptime(m.group(1), "%d/%m/%Y").date()
                except: pass

        # NET SALES
        net_patterns = [
            r'[Nn]e[it]{1,3}[Dd]ay[Ss]al[Dd]is\s+([\d.,]+)',
            r'[Nn]et[Dd]ay[Ss]al[Dd]is\s+([\d.,]+)',
            r'[Nn]e[it]{1,3}Day\s*Sal\s*Dis\s+([\d.,]+)',
        ]
        for pat in net_patterns:
            m = re.search(pat, full_text)
            if m:
                try:
                    result["net_sales"] = parse_greek_number(m.group(1))
                    break
                except:
                    pass

        if result["net_sales"] is None:
            m = re.search(r'[Tt]otals?\s*[:\-]?\s*([\d.,]+)\s+100[.,]00\s+([\d]+)', full_text)
            if m:
                try:
                    result["net_sales"] = parse_greek_number(m.group(1))
                    if result["customers"] is None:
                        result["customers"] = int(m.group(2))
                except:
                    pass

        if result["net_sales"] is None:
            m = re.search(r'[Gg]roup[Tt]ot\s+([\d.,]+)\s+([\d.,]+)', full_text)
            if m:
                try: result["net_sales"] = parse_greek_number(m.group(2))
                except: pass

        # CUSTOMERS
        if result["customers"] is None:
            m = re.search(r'[Nn]um[Ii]tm[Ss]old\s+([\d,. ]+)', full_text)
            if m:
                try: result["customers"] = int(m.group(1).replace(",","").replace(".","").strip())
                except: pass

        if result["customers"] is None:
            m = re.search(r'[Nn]um[Oo]f[Cc]us\s+([\d,. ]+)', full_text)
            if m:
                try: result["customers"] = int(m.group(1).replace(",","").replace(".","").strip())
                except: pass

        # AVG BASKET
        avg_patterns = [
            r'[Aa]vg[Ii]tm[Pp]er[Cc]us\s+([\d.,]+)',
            r'[Aa]vg[Ii]tm[Pp]ric\s+([\d.,]+)',
            r'[Aa]vg\s*[Ii]tm\s*[Pp]er\s*[Cc]us\s+([\d.,]+)',
        ]
        for pat in avg_patterns:
            m = re.search(pat, full_text)
            if m:
                try:
                    result["avg_basket"] = parse_greek_number(m.group(1))
                    break
                except:
                    pass

    except Exception as e:
        st.warning(f"OCR error: {e}")

    return result

def fetch_emails_incremental(password, full_scan=False):
    """
    Διαβάζει τα emails, ένα-ένα, χωρίς να τα φορτώνει όλα στη μνήμη.
    """
    df_existing = load_cache()
    cutoff_date = None

    if not full_scan and not df_existing.empty:
        last_date   = df_existing["date"].max()
        cutoff_date = last_date - timedelta(days=5) # Ψάχνει μόνο 5 μέρες πίσω (ΤΑΧΥΤΑΤΟ!)

    cutoff_year = date.today().year - DEEP_SCAN_YEARS if full_scan else None

    new_records = []
    errors = []
    
    limit = None if full_scan else 20
    
    print(f"\n--- ΕΝΑΡΞΗ {'ΒΑΘΙΑΣ' if full_scan else 'ΓΡΗΓΟΡΗΣ'} ΣΑΡΩΣΗΣ ---")

    try:
        # TIMEOUT στα 15 δευτερόλεπτα
        with MailBox("imap.gmail.com").login(SALES_EMAIL_USER, password, timeout=15) as mb:
            print("✅ Σύνδεση στο Gmail επιτυχής. Ξεκινάει η αναζήτηση...")
            
            # --- ΕΔΩ ΕΙΝΑΙ ΤΟ ΜΥΣΤΙΚΟ ΤΗΣ ΤΑΧΥΤΗΤΑΣ ---
            # Λέμε στον server του Gmail να ψάξει ΜΟΝΟ τα πρόσφατα email
            if not full_scan and cutoff_date:
                criteria = AND(from_=SALES_EMAIL_SENDER, date_gte=cutoff_date)
                print(f"🔍 Αναζήτηση στο Gmail ΑΥΣΤΗΡΑ από: {cutoff_date.strftime('%d/%m/%Y')}")
            elif full_scan and cutoff_year:
                criteria = AND(from_=SALES_EMAIL_SENDER, date_gte=date(cutoff_year, 1, 1))
                print(f"🔍 Βαθιά αναζήτηση στο Gmail από το έτος {cutoff_year}")
            else:
                criteria = AND(from_=SALES_EMAIL_SENDER)
            
            for i, msg in enumerate(mb.fetch(criteria, reverse=True, limit=limit)):
                msg_date = msg.date.date() if msg.date else None
                print(f"[{i+1}] Ελέγχεται email από: {msg_date}")

                if full_scan and cutoff_year and msg_date and msg_date.year < cutoff_year:
                    continue

                if not full_scan and cutoff_date and msg_date and msg_date < cutoff_date:
                    print("  ↳ Παλιό email. Προσπέραση.")
                    continue

                subj = msg.subject or ""
                if SALES_SUBJECT_KW.lower() not in subj.lower() and "skyros" not in subj.lower():
                    continue

                pdf_att = next((a for a in msg.attachments if a.filename and a.filename.lower().endswith(".pdf")), None)
                
                if pdf_att:
                    print(f"  ↳ Διαβάζεται το PDF: {pdf_att.filename}...")
                    rec = extract_sales_from_pdf(pdf_att.payload)
                    
                    if rec["date"] and rec["net_sales"] is not None:
                        if not df_existing.empty and rec["date"] in df_existing["date"].values:
                            print(f"  ↳ Τα δεδομένα της {rec['date']} υπάρχουν ήδη.")
                            continue
                        new_records.append(rec)
                        print(f"  ↳ ✅ ΕΠΙΤΥΧΙΑ: {rec['date']} -> {rec['net_sales']}€")

            print(f"--- ΟΛΟΚΛΗΡΩΣΗ: Προστέθηκαν {len(new_records)} νέες εγγραφές ---")

    except Exception as e:
        print(f"❌ ΣΦΑΛΜΑ GMAIL: {e}")
        errors.append(str(e))

    return new_records, errors


# ── CACHE LOAD ────────────────────────────────────────────────────────────────
df = load_all()
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
    

# ── TABS ─────────────────────────────────────────────────────────────────────
tab_dash, tab_history, tab_update = st.tabs(["📈 Dashboard", "📋 Ιστορικό", "🔄 Ενημέρωση"])

# ═══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    if df.empty:
        st.markdown('<div class="warn-box">⚠️ Δεν υπάρχουν δεδομένα. Μεταβείτε στην καρτέλα <b>Ενημέρωση</b> για φόρτωση από email.</div>', unsafe_allow_html=True)
    else:
        last = df.iloc[0]
        prev = df.iloc[1] if len(df) > 1 else None

        def delta_str(now, pv):
            if pv is None or pv == 0: return ""
            d = now - pv; pct = d/pv*100
            sym = "▲" if d >= 0 else "▼"
            col = "#5a9f7a" if d >= 0 else "#c04a4a"
            return f'<div style="font-size:.62rem;color:{col};margin-top:.15rem;">{sym} {abs(pct):.1f}%</div>'

        p_ns = prev["net_sales"]  if prev is not None else None
        p_cu = prev["customers"]  if prev is not None and pd.notna(prev.get("customers")) else None
        p_ab = prev["avg_basket"] if prev is not None and pd.notna(prev.get("avg_basket")) else None

        days_old = (today - last["date"]).days
        date_label = last["date"].strftime("%d/%m/%Y")

        st.markdown('<div class="sh">Τελευταία Ημέρα</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="kr kr4">
          <div class="kc" style="--a:#5a9f7a">
            <div class="kl">Πωλήσεις · {date_label}</div>
            <div class="kv">{fmt(last['net_sales'])}</div>
            {delta_str(last['net_sales'], p_ns)}
          </div>
          <div class="kc" style="--a:#7c5abf">
            <div class="kl">Πελάτες</div>
            <div class="kv">{int(last['customers']) if pd.notna(last.get('customers')) else '—'}</div>
            {delta_str(int(last['customers']) if pd.notna(last.get('customers')) else 0, p_cu)}
          </div>
          <div class="kc" style="--a:#6b8fd4">
            <div class="kl">ΜΟ Καλαθιού</div>
            <div class="kv">{fmt(last.get('avg_basket'))}</div>
            {delta_str(last.get('avg_basket') or 0, p_ab)}
          </div>
          <div class="kc" style="--a:#c9874a">
            <div class="kl">Τελευταία Ενημέρωση</div>
            <div class="kv" style="font-size:.85rem;">{'Σήμερα' if days_old==0 else f'Πριν {days_old}μ.'}</div>
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="sh">Τρέχων Μήνας</div>', unsafe_allow_html=True)
        m_df  = df[(df["date"] >= date(today.year, today.month, 1)) & (df["date"] <= today)]
        m_tot = m_df["net_sales"].sum() if not m_df.empty else 0
        m_avg = m_df["net_sales"].mean() if not m_df.empty else 0
        m_days = len(m_df)

        first_this = date(today.year, today.month, 1)
        last_prev  = first_this - timedelta(days=1)
        pm_df  = df[(df["date"] >= date(last_prev.year, last_prev.month, 1)) & (df["date"] <= last_prev)]
        pm_tot = pm_df["net_sales"].sum() if not pm_df.empty else None

        mn = MONTHS_GR[today.month-1]
        st.markdown(f"""<div class="kr kr3">
          <div class="kc" style="--a:#5a9f7a">
            <div class="kl">Σύνολο {mn}</div>
            <div class="kv">{fmt(m_tot)}</div>
            {delta_str(m_tot, pm_tot)}
          </div>
          <div class="kc" style="--a:#6b8fd4">
            <div class="kl">Ημερήσιος ΜΟ</div>
            <div class="kv">{fmt(m_avg)}</div>
          </div>
          <div class="kc" style="--a:#7c5abf">
            <div class="kl">Ημέρες με δεδομένα</div>
            <div class="kv">{m_days}</div>
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="sh">Τελευταίες 14 ημέρες</div>', unsafe_allow_html=True)
        chart_df = df[df["date"] >= (today - timedelta(days=13))].sort_values("date").copy()
        if not chart_df.empty:
            chart_df.index = chart_df["date"].apply(lambda d: d.strftime("%d/%m"))
            st.bar_chart(chart_df["net_sales"], color="#5a9f7a", height=200)

# ═══════════════════════════════════════════════════════════════════════════════
with tab_history:
    if df.empty:
        st.markdown('<div class="warn-box">Δεν υπάρχουν δεδομένα.</div>', unsafe_allow_html=True)
    else:
        c1, c2 = st.columns(2)
        with c1:
            years = sorted(set(r.year for r in df["date"]), reverse=True)
            sel_y = st.selectbox("Έτος", years)
        with c2:
            month_names = [MONTHS_GR[i] for i in range(12)]
            sel_m = st.selectbox("Μήνας", range(1,13), format_func=lambda x: MONTHS_GR[x-1], index=today.month-1)

        filtered = df[(df["date"].apply(lambda d: d.year) == sel_y) &
                      (df["date"].apply(lambda d: d.month) == sel_m)].copy()

        if not filtered.empty:
            total = filtered["net_sales"].sum()
            avg   = filtered["net_sales"].mean()
            st.markdown(f"""<div class="kr kr3" style="margin:1rem 0;">
              <div class="kc" style="--a:#5a9f7a"><div class="kl">Σύνολο</div><div class="kv">{fmt(total)}</div></div>
              <div class="kc" style="--a:#6b8fd4"><div class="kl">Ημ. ΜΟ</div><div class="kv">{fmt(avg)}</div></div>
              <div class="kc" style="--a:#7c5abf"><div class="kl">Ημέρες</div><div class="kv">{len(filtered)}</div></div>
            </div>""", unsafe_allow_html=True)

            display = filtered.copy()
            display["date"] = display["date"].apply(lambda d: d.strftime("%d/%m/%Y"))
            display.columns = ["Ημερομηνία","Καθαρές Πωλήσεις","Πελάτες","ΜΟ Καλαθιού"]
            st.dataframe(display.style.format({
                "Καθαρές Πωλήσεις": lambda v: fmt(v) if pd.notna(v) else "—",
                "ΜΟ Καλαθιού": lambda v: fmt(v) if pd.notna(v) else "—",
            }), use_container_width=True, hide_index=True)

            csv = filtered.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 Λήψη CSV", csv, f"sales_{sel_y}_{sel_m:02d}.csv", "text/csv")
        else:
            st.markdown('<div class="warn-box">Δεν υπάρχουν δεδομένα για αυτή την περίοδο.</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
with tab_update:
    st.markdown('<div class="sh">Σύνδεση Email</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="info-box">📧 Λογαριασμός: <b>{SALES_EMAIL_USER}</b> — Χρησιμοποιήστε <b>App Password</b> του Gmail.</div>', unsafe_allow_html=True)

    password = st.text_input("🔐 Gmail App Password", type="password", key="sales_pw")

    col_inc, col_full = st.columns(2)
    run_inc  = False
    run_full = False

    with col_inc:
        if st.button("⚡ Γρήγορη Ενημέρωση (Νέα μόνο)", use_container_width=True):
            run_inc = True
    with col_full:
        if st.button("🔍 Βαθιά Σάρωση (2 χρόνια)", use_container_width=True):
            run_full = True

    if (run_inc or run_full) and password:
        lbl = "Βαθιά σάρωση 2 ετών..." if run_full else "Φόρτωση νέων emails (max 20)..."

        with st.spinner(lbl):
            new_recs, errs = fetch_emails_incremental(password, full_scan=run_full)

        if errs:
            st.error(f"❌ Σφάλμα σύνδεσης: {errs[0]}")
        elif not new_recs:
            st.markdown('<div class="info-box">✅ Δεν βρέθηκαν νέα δεδομένα — το σύστημα είναι ενημερωμένο.</div>', unsafe_allow_html=True)
        else:
            st.success(f"✅ Βρέθηκαν {len(new_recs)} νέες εγγραφές!")
            new_df = pd.DataFrame(new_recs)
            old_df = load_cache()
            merged = pd.concat([old_df, new_df]).drop_duplicates("date").sort_values("date", ascending=False).reset_index(drop=True)
            save_cache(merged)
            st.markdown(f'<div class="info-box">💾 Αποθηκεύτηκαν {len(new_recs)} νέες εγγραφές.</div>', unsafe_allow_html=True)
            st.rerun()

    elif (run_inc or run_full) and not password:
        st.error("Εισάγετε App Password.")

    # Manual entry
    st.markdown('<div class="sh">Χειροκίνητη Εισαγωγή</div>', unsafe_allow_html=True)
    with st.form("manual_sales"):
        c1, c2, c3, c4 = st.columns(4)
        with c1: entry_date = st.date_input("Ημερομηνία", value=today)
        with c2: net_s = st.number_input("Καθαρές Πωλήσεις (€)", min_value=0.0, step=0.01, format="%.2f")
        with c3: custs = st.number_input("Πελάτες", min_value=0, step=1)
        with c4: avg_b = st.number_input("ΜΟ Καλαθιού (€)", min_value=0.0, step=0.01, format="%.2f")
        if st.form_submit_button("✅ Αποθήκευση", use_container_width=True):
            new_row = pd.DataFrame([{"date": entry_date, "net_sales": net_s, "customers": custs, "avg_basket": avg_b if avg_b > 0 else None}])
            old_df  = load_cache()
            merged  = pd.concat([old_df, new_row]).drop_duplicates("date").sort_values("date", ascending=False).reset_index(drop=True)
            save_cache(merged)
            st.success(f"✅ Αποθηκεύτηκε: {entry_date.strftime('%d/%m/%Y')} — {fmt(net_s)}")
            st.rerun()
