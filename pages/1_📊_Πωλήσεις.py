import streamlit as st
import pandas as pd
import json, os, sys
from imap_tools import MailBox, AND
from datetime import datetime, date, timedelta
from pdf2image import convert_from_bytes
import traceback, unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import (
    COMMON_CSS, MONTHS_GR, DAYS_GR,
    fmt_euro, parse_num, delta_html,
    load_history, save_history, upsert,
    extract_pdf_data, ocr_page, period_stats
)

st.set_page_config(page_title="Sales Analytics · ΑΒ ΣΚΥΡΟΣ",
                   layout="wide", page_icon="📊", initial_sidebar_state="expanded")
st.markdown(COMMON_CSS, unsafe_allow_html=True)

EMAIL_USER    = "ftoulisgm@gmail.com"
EMAIL_PASS    = st.secrets["EMAIL_PASSWORD"]
EMAIL_FROM    = "abf.skyros@gmail.com"
EMAIL_SUBJECT = "ΑΒ ΣΚΥΡΟΣ"

# ── Sidebar nav ───────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 1.5rem;">
      <div style="font-size:.65rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#10b981;margin-bottom:.3rem;">ΑΒ ΣΚΥΡΟΣ 1082</div>
      <div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;">Business Hub</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div style="font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#334155;margin-bottom:.5rem;">ΠΛΟΗΓΗΣΗ</div>', unsafe_allow_html=True)
    st.page_link("Home.py",                       label="🏠  Αρχική Σελίδα")
    st.page_link("pages/1_📊_Πωλήσεις.py",        label="📊  Sales Analytics")
    st.page_link("pages/2_📋_Τιμολόγια.py",        label="📋  Τιμολόγια")

# ── Helpers ────────────────────────────────────────────────
def _norm(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').upper()

def _pick_folder(mailbox):
    try:
        for f in mailbox.folder.list():
            n = f.name.upper()
            if 'ALL' in n and ('MAIL' in n or 'GMAIL' in n): return f.name
    except: pass
    return 'INBOX'

def sync_emails(df, progress_ph):
    logs   = []
    last_d = df['date'].max() if not df.empty else None
    since_date = (last_d - timedelta(days=1)) if last_d else (date.today() - timedelta(days=365))
    try:
        progress_ph.markdown("📡 Σύνδεση στο Gmail...")
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
            try:    mailbox.folder.set(_pick_folder(mailbox))
            except: mailbox.folder.set('INBOX')
            criteria = AND(from_=EMAIL_FROM, date_gte=since_date)
            msgs = list(mailbox.fetch(criteria, reverse=True, mark_seen=False, headers_only=True))

        target   = _norm(EMAIL_SUBJECT)
        relevant = [m for m in msgs if target in _norm(m.subject)]
        logs.append(f"📬 Βρέθηκαν **{len(relevant)}** emails")
        if not relevant:
            progress_ph.empty(); return df, logs

        found = 0
        with MailBox('imap.gmail.com').login(EMAIL_USER, EMAIL_PASS) as mailbox:
            try:    mailbox.folder.set(_pick_folder(mailbox))
            except: mailbox.folder.set('INBOX')
            for i, hdr in enumerate(relevant):
                progress_ph.markdown(f"⏳ Επεξεργασία {i+1}/{len(relevant)}: **{hdr.date.strftime('%d/%m/%Y')}** ...")
                full = list(mailbox.fetch(AND(uid=str(hdr.uid)), mark_seen=False))
                if not full: continue
                for att in full[0].attachments:
                    if not att.filename.lower().endswith('.pdf'): continue
                    data = extract_pdf_data(att.payload)
                    if data['date'] is None: data['date'] = hdr.date.date()
                    if last_d and data['date'] <= last_d and data['date'] != date.today(): break
                    if data['netday'] and data['netday'] > 0:
                        df = upsert(df, data); found += 1
                    break
        progress_ph.empty()
        logs.append(f"✅ Αποθηκεύτηκαν **{found}** νέες αναφορές")
    except Exception as e:
        progress_ph.empty()
        logs.append(f"❌ **IMAP σφάλμα:** {e}")
        logs.append("```\n" + traceback.format_exc() + "\n```")
    return df, logs

# ══════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════
df     = load_history()
today  = date.today()
last_d = df['date'].max() if not df.empty else None
needs_sync = (last_d is None) or (last_d < today)

st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.5rem;">
  <div>
    <div style="font-size:.7rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#10b981;margin-bottom:.2rem;">ΑΒ ΣΚΥΡΟΣ · ΚΑΤΑΣΤΗΜΑ 1082</div>
    <h1 style="font-size:1.9rem;font-weight:700;color:#f1f5f9;margin:0;letter-spacing:-.02em;">Sales Analytics</h1>
  </div>
  <div style="text-align:right;">
    <div style="font-size:.7rem;color:#475569;">Τελευταία ενημέρωση</div>
    <div style="font-family:'DM Mono';font-size:.75rem;color:#64748b;">{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

if needs_sync and not df.empty:
    days_old = (today - last_d).days
    st.markdown(f'<div class="stale-banner">⚠ Τελευταία αναφορά: <strong>{last_d.strftime("%d/%m/%Y")}</strong> ({days_old} {"ημέρα" if days_old==1 else "ημέρες"} πίσω)</div>', unsafe_allow_html=True)
elif not needs_sync:
    st.markdown(f'<div class="ok-banner">✓ Ενημερωμένο · {last_d.strftime("%d/%m/%Y")}</div>', unsafe_allow_html=True)

tc1, tc2 = st.columns([1, 1])
with tc1: sync_btn   = st.button("⟳  Συγχρονισμός", use_container_width=True, type="primary")
with tc2: upload_btn = st.button("↑  PDF Upload",    use_container_width=True, type="secondary")

progress_ph = st.empty()

if sync_btn:
    with st.spinner(""):
        df, logs = sync_emails(df, progress_ph)
        save_history(df)
    for l in logs: st.markdown(l)
    st.rerun()

if upload_btn: st.session_state['show_upload_sales'] = True
if st.session_state.get('show_upload_sales'):
    uploaded = st.file_uploader("PDF", type="pdf", label_visibility="collapsed")
    if uploaded:
        raw = uploaded.read()
        prog = st.empty(); prog.markdown("⏳ OCR επεξεργασία...")
        data = extract_pdf_data(raw); prog.empty()
        if data['netday'] and data['netday'] > 0:
            if data['date'] is None: data['date'] = today
            df = upsert(df, data); save_history(df)
            st.success(f"✅ {data['date'].strftime('%d/%m/%Y')} — {fmt_euro(data['netday'])} · {data['customers']} πελάτες")
            st.session_state['show_upload_sales'] = False; st.rerun()
        else:
            st.error("Δεν βρέθηκαν δεδομένα.")
            with st.expander("Debug"):
                imgs = convert_from_bytes(raw, dpi=180, fmt='jpeg')
                st.text(ocr_page(imgs[0])[:3000])

if df.empty:
    st.markdown('<div style="text-align:center;padding:4rem;color:#334155;"><div style="font-size:3rem;">📭</div><div>Δεν υπάρχουν δεδομένα · Πατήστε Συγχρονισμός</div></div>', unsafe_allow_html=True)
    st.stop()

# ── TABS ───────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📍  Τελευταία Αναφορά","📈  Τάσεις","⚖️  Συγκρίσεις","📋  Ιστορικό"])

with tab1:
    latest = df.iloc[0]; prev = df.iloc[1] if len(df) > 1 else None
    prev7r = df[df['date'] == (latest['date'] - timedelta(days=7))]
    prev7  = prev7r.iloc[0] if not prev7r.empty else None
    ld = latest['date']
    st.markdown(f'<div style="font-size:.82rem;color:#475569;margin-bottom:1.2rem;">{DAYS_GR[ld.weekday()]} · {ld.day} {MONTHS_GR[ld.month-1]} {ld.year}</div>', unsafe_allow_html=True)

    def kpi(label, value, prev_val, accent, is_euro=True):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return f'<div class="kpi-card" style="--accent:{accent}"><div class="kpi-label">{label}</div><div class="kpi-value">—</div></div>'
        disp = fmt_euro(value) if is_euro else f"{int(value):,}".replace(",",".")
        dlt  = delta_html(value, prev_val, is_euro) if prev_val is not None else ""
        return (f'<div class="kpi-card" style="--accent:{accent}"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{disp}</div>{dlt}</div>')

    st.markdown(f"""<div class="kpi-grid">
      {kpi("Πωλήσεις Ημέρας",   latest['netday'],    prev['netday']    if prev is not None else None, "#10b981")}
      {kpi("Αριθμός Πελατών",   latest['customers'], prev['customers'] if prev is not None else None, "#3b82f6", False)}
      {kpi("Μ.Ό. Καλαθιού",    latest['avg_basket'],prev['avg_basket'] if prev is not None else None, "#8b5cf6")}
      {kpi("Σύγκριση -7 ημερ.", latest['netday'],    prev7['netday']   if prev7 is not None else None, "#f59e0b")}
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec-header"><span>▍</span> Ανάλυση Τμημάτων</div>', unsafe_allow_html=True)
    try:
        depts = json.loads(latest.get('depts','[]') or '[]')
        if depts:
            mx = depts[0]['sales']
            rows = "".join(
                f'<div class="dept-row"><div class="dept-rank">{i+1}</div>'
                f'<div class="dept-name">{d["name"]}</div>'
                f'<div class="dept-bar-wrap"><div class="dept-bar" style="width:{d["sales"]/mx*100:.0f}%"></div></div>'
                f'<div class="dept-val">{fmt_euro(d["sales"])}</div></div>'
                for i,d in enumerate(depts[:12])
            )
            st.markdown(f'<div style="background:#111827;border:1px solid #1e2d45;border-radius:10px;padding:.5rem 1rem 0;">{rows}</div>', unsafe_allow_html=True)
    except: pass

with tab2:
    st.markdown('<div class="sec-header"><span>▍</span> Εξέλιξη Πωλήσεων</div>', unsafe_allow_html=True)
    p_opt = st.radio("", ["30 ημέρες","90 ημέρες","Όλο το έτος"], horizontal=True, label_visibility="collapsed")
    since = (today - timedelta(days=30 if "30" in p_opt else 90) if "έτος" not in p_opt else date(today.year,1,1))
    ch = df[df['date'] >= since].sort_values('date').copy()
    ch['label'] = ch['date'].apply(lambda d: d.strftime('%d/%m'))
    if not ch.empty:
        st.markdown("**Ημερήσιες Πωλήσεις (€)**")
        st.bar_chart(ch.set_index('label')['netday'], color="#10b981", use_container_width=True, height=220)
        st.markdown("**Αριθμός Πελατών**")
        st.bar_chart(ch.set_index('label')['customers'], color="#3b82f6", use_container_width=True, height=180)
        s = period_stats(df, since, today)
        st.markdown('<div class="sec-header"><span>▍</span> Περίληψη</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="kpi-grid-3">
          <div class="kpi-card" style="--accent:#10b981"><div class="kpi-label">Σύνολο</div><div class="kpi-value-sm">{fmt_euro(s['total'])}</div></div>
          <div class="kpi-card" style="--accent:#3b82f6"><div class="kpi-label">Μ.Ό. Ημέρας</div><div class="kpi-value-sm">{fmt_euro(s['avg_day'])}</div></div>
          <div class="kpi-card" style="--accent:#f59e0b"><div class="kpi-label">Κορυφή ({s['peak'].strftime('%d/%m') if s['peak'] else '—'})</div><div class="kpi-value-sm">{fmt_euro(s['peak_val'])}</div></div>
        </div>""", unsafe_allow_html=True)

with tab3:
    def cmp_table(ta, tb, sa, sb):
        def row(label, a, b, euro=True):
            fmt = fmt_euro if euro else lambda v: f"{v:.0f}"
            if b == 0: ph = "<span style='color:#475569'>—</span>"
            else:
                pct = (a-b)/b*100; clr = "#10b981" if pct >= 0 else "#f43f5e"
                ph = f'<span style="color:{clr}">{"▲" if pct>=0 else "▼"} {abs(pct):.1f}%</span>'
            return (f'<tr style="border-bottom:1px solid #1e2d45;">'
                    f'<td style="padding:.6rem .4rem;font-size:.82rem;color:#94a3b8;">{label}</td>'
                    f'<td style="padding:.6rem .8rem;font-family:DM Mono;font-size:.82rem;color:#f1f5f9;text-align:right;">{fmt(a)}</td>'
                    f'<td style="padding:.6rem .8rem;font-family:DM Mono;font-size:.82rem;color:#64748b;text-align:right;">{fmt(b)}</td>'
                    f'<td style="padding:.6rem .8rem;text-align:right;font-size:.82rem;">{ph}</td></tr>')
        th = (f'<tr style="background:#0f1f2e;"><th style="padding:.7rem .4rem;font-size:.68rem;color:#475569;text-align:left;font-weight:700;text-transform:uppercase;letter-spacing:.1em;"></th>'
              f'<th style="padding:.7rem .8rem;font-size:.68rem;color:#10b981;text-align:right;font-weight:700;text-transform:uppercase;letter-spacing:.1em;">{ta}</th>'
              f'<th style="padding:.7rem .8rem;font-size:.68rem;color:#475569;text-align:right;font-weight:700;text-transform:uppercase;letter-spacing:.1em;">{tb}</th>'
              f'<th style="padding:.7rem .8rem;font-size:.68rem;color:#475569;text-align:right;font-weight:700;text-transform:uppercase;letter-spacing:.1em;">Μεταβολή</th></tr>')
        body = (row("Σύνολο Πωλήσεων",sa['total'],sb['total'])+row("Μ.Ό. Ημέρας",sa['avg_day'],sb['avg_day'])
               +row("Μ.Ό. Πελατών",sa['avg_cus'],sb['avg_cus'],euro=False)+row("Ημέρες",sa['days'],sb['days'],euro=False)
               +row("Κορυφαία Μέρα",sa['peak_val'],sb['peak_val']))
        return f'<table style="width:100%;border-collapse:collapse;background:#111827;border:1px solid #1e2d45;border-radius:10px;overflow:hidden;"><thead>{th}</thead><tbody>{body}</tbody></table>'

    st.markdown('<div class="sec-header"><span>▍</span> Μηνιαία Σύγκριση</div>', unsafe_allow_html=True)
    cur_ms = date(today.year,today.month,1); prev_me = cur_ms-timedelta(days=1); prev_ms = date(prev_me.year,prev_me.month,1)
    st.markdown(cmp_table(MONTHS_GR[today.month-1],MONTHS_GR[prev_me.month-1],period_stats(df,cur_ms,today),period_stats(df,prev_ms,prev_me)), unsafe_allow_html=True)
    st.markdown('<div class="sec-header"><span>▍</span> Εβδομαδιαία Σύγκριση</div>', unsafe_allow_html=True)
    ws = today-timedelta(days=today.weekday()); pws = ws-timedelta(days=7)
    st.markdown(cmp_table("Τρέχουσα","Προηγούμενη",period_stats(df,ws,today),period_stats(df,pws,ws-timedelta(days=1))), unsafe_allow_html=True)

with tab4:
    st.markdown('<div class="sec-header"><span>▍</span> Πλήρες Ιστορικό</div>', unsafe_allow_html=True)
    disp = df[['date','netday','customers','avg_basket']].copy()
    disp['date']       = disp['date'].apply(lambda d: d.strftime('%d/%m/%Y'))
    disp['netday']     = disp['netday'].apply(fmt_euro)
    disp['avg_basket'] = disp['avg_basket'].apply(fmt_euro)
    disp['customers']  = disp['customers'].apply(lambda v: f"{int(v)}" if pd.notna(v) else "—")
    disp.columns = ['Ημερομηνία','Πωλήσεις','Πελάτες','Μ.Ό. Καλαθιού']
    st.dataframe(disp, use_container_width=True, hide_index=True, height=500)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("↓  Εξαγωγή CSV", csv, f"sales_{today}.csv", "text/csv")
