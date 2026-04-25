import streamlit as st
import pandas as pd
import json, os, sys
from imap_tools import MailBox, AND
from datetime import datetime, date, timedelta
from pdf2image import convert_from_bytes
import traceback, unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import (CSS, MONTHS_GR, DAYS_GR, fmt_euro, parse_num, delta_html,
                   load_history, save_history, upsert, extract_pdf_data,
                   ocr_page, period_stats)

st.set_page_config(page_title="Sales Analytics — AB Skyros",
                   layout="wide", page_icon=None, initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)

EMAIL_USER    = "ftoulisgm@gmail.com"
EMAIL_PASS    = st.secrets["EMAIL_PASSWORD"]
EMAIL_FROM    = "abf.skyros@gmail.com"
EMAIL_SUBJECT = "ΑΒ ΣΚΥΡΟΣ"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1.2rem 0 1rem;">
      <div style="font-size:.62rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#60a5fa;margin-bottom:.3rem;">AB SKYROS 1082</div>
      <div style="font-size:1rem;font-weight:700;color:#f1f5f9;margin-bottom:1.5rem;">Business Hub</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#4b5563;margin-bottom:.4rem;padding-left:.9rem;">NAVIGATION</div>', unsafe_allow_html=True)
    st.page_link("Home.py",            label="Home")
    st.page_link("pages/1_Sales.py",   label="Sales Analytics")
    st.page_link("pages/2_Invoices.py",label="Invoices")

# ── Email sync ────────────────────────────────────────────────────────────────
def _norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper()

def _pick_folder(mb):
    try:
        for f in mb.folder.list():
            n = f.name.upper()
            if "ALL" in n and ("MAIL" in n or "GMAIL" in n): return f.name
    except: pass
    return "INBOX"

def sync_emails(df, ph):
    logs   = []
    last_d = df["date"].max() if not df.empty else None
    since  = (last_d - timedelta(days=1)) if last_d else (date.today() - timedelta(days=365))
    try:
        ph.markdown('<div class="banner banner-info">Σύνδεση στο Gmail...</div>', unsafe_allow_html=True)
        with MailBox("imap.gmail.com").login(EMAIL_USER, EMAIL_PASS) as mb:
            try:    mb.folder.set(_pick_folder(mb))
            except: mb.folder.set("INBOX")
            hdrs = list(mb.fetch(AND(from_=EMAIL_FROM, date_gte=since),
                                 reverse=True, mark_seen=False, headers_only=True))

        target   = _norm(EMAIL_SUBJECT)
        relevant = [h for h in hdrs if target in _norm(h.subject)]
        logs.append(f"Βρέθηκαν **{len(relevant)}** emails από `{EMAIL_FROM}`")

        if not relevant:
            ph.empty(); return df, logs

        found = 0
        with MailBox("imap.gmail.com").login(EMAIL_USER, EMAIL_PASS) as mb:
            try:    mb.folder.set(_pick_folder(mb))
            except: mb.folder.set("INBOX")
            for i, hdr in enumerate(relevant):
                ph.markdown(f'<div class="banner banner-info">Επεξεργασία {i+1}/{len(relevant)}: {hdr.date.strftime("%d/%m/%Y")} ...</div>', unsafe_allow_html=True)
                full = list(mb.fetch(AND(uid=str(hdr.uid)), mark_seen=False))
                if not full: continue
                for att in full[0].attachments:
                    if not att.filename.lower().endswith(".pdf"): continue
                    data = extract_pdf_data(att.payload)
                    if data["date"] is None: data["date"] = hdr.date.date()
                    if last_d and data["date"] <= last_d and data["date"] != date.today(): break
                    if data["netday"] and data["netday"] > 0:
                        df = upsert(df, data); found += 1
                    break
        ph.empty()
        logs.append(f"Αποθηκεύτηκαν **{found}** νέες αναφορές")
    except Exception as e:
        ph.empty()
        logs.append(f"Σφάλμα IMAP: {e}")
    return df, logs

# ── UI ────────────────────────────────────────────────────────────────────────
df    = load_history()
today = date.today()
last_d = df["date"].max() if not df.empty else None
needs_sync = last_d is None or last_d < today

st.markdown(f"""
<div class="page-header">
  <div class="page-header-left">
    <div class="eyebrow">AB Skyros — Κατάστημα 1082</div>
    <h1>Sales Analytics</h1>
  </div>
  <div class="page-header-right">
    <div class="ts-label">Ανανέωση</div>
    <div class="ts-val">{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

if needs_sync and not df.empty:
    days_old = (today - last_d).days
    st.markdown(f'<div class="banner banner-warn">Τελευταία αναφορά {days_old} {"ημέρα" if days_old==1 else "ημέρες"} πίσω ({last_d.strftime("%d/%m/%Y")}). Κάντε συγχρονισμό.</div>', unsafe_allow_html=True)
elif last_d:
    st.markdown(f'<div class="banner banner-ok">Ενημερωμένο — {last_d.strftime("%d/%m/%Y")}</div>', unsafe_allow_html=True)

c1, c2 = st.columns([1, 1])
with c1: sync_btn   = st.button("Συγχρονισμός Email",  use_container_width=True)
with c2: upload_btn = st.button("Ανεβασμα PDF",        use_container_width=True, type="secondary")

ph = st.empty()

if sync_btn:
    with st.spinner(""):
        df, logs = sync_emails(df, ph)
        save_history(df)
    for l in logs: st.markdown(l)
    st.rerun()

if upload_btn:
    st.session_state["show_up"] = True
if st.session_state.get("show_up"):
    up = st.file_uploader("Επιλογή PDF", type="pdf", label_visibility="collapsed")
    if up:
        raw = up.read()
        pp  = st.empty(); pp.markdown('<div class="banner banner-info">OCR σε εξέλιξη...</div>', unsafe_allow_html=True)
        data = extract_pdf_data(raw); pp.empty()
        if data["netday"] and data["netday"] > 0:
            if data["date"] is None: data["date"] = today
            df = upsert(df, data); save_history(df)
            st.success(f"{data['date'].strftime('%d/%m/%Y')} — {fmt_euro(data['netday'])} · {data['customers']} πελάτες")
            st.session_state["show_up"] = False; st.rerun()
        else:
            st.error("Δεν βρέθηκαν δεδομένα.")
            with st.expander("OCR Debug"):
                imgs = convert_from_bytes(raw, dpi=180, fmt="jpeg")
                st.text(ocr_page(imgs[0])[:3000])

if df.empty:
    st.markdown('<div class="banner banner-warn" style="margin-top:2rem;text-align:center;">Δεν υπάρχουν δεδομένα. Κάντε συγχρονισμό ή ανεβάστε PDF.</div>', unsafe_allow_html=True)
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
t1, t2, t3, t4 = st.tabs(["Τελευταια Αναφορα", "Τασεις", "Συγκρισεις", "Ιστορικο"])

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with t1:
    latest = df.iloc[0]
    prev   = df.iloc[1] if len(df) > 1 else None
    p7r    = df[df["date"] == (latest["date"] - timedelta(days=7))]
    p7     = p7r.iloc[0] if not p7r.empty else None
    ld = latest["date"]
    st.markdown(f'<p style="font-size:.8rem;color:#94a3b8;margin-bottom:.5rem;">{DAYS_GR[ld.weekday()]} · {ld.day} {MONTHS_GR[ld.month-1]} {ld.year}</p>', unsafe_allow_html=True)

    def kpi(lbl, val, pv, acc, euro=True):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return f'<div class="kpi" style="--a:{acc}"><div class="kpi-lbl">{lbl}</div><div class="kpi-val">—</div></div>'
        disp = fmt_euro(val) if euro else f"{int(val):,}".replace(",",".")
        dlt  = delta_html(val, pv, euro) if pv is not None else ""
        return (f'<div class="kpi" style="--a:{acc}"><div class="kpi-lbl">{lbl}</div>'
                f'<div class="kpi-val">{disp}</div>{dlt}</div>')

    st.markdown(f"""<div class="kpi-row kpi-row-4">
      {kpi("Πωλησεις Ημερας",  latest["netday"],    prev["netday"]    if prev is not None else None, "#2563eb")}
      {kpi("Πελατες",          latest["customers"], prev["customers"] if prev is not None else None, "#7c3aed", euro=False)}
      {kpi("ΜΟ Καλαθιου",     latest["avg_basket"],prev["avg_basket"] if prev is not None else None, "#0891b2")}
      {kpi("Πριν 7 Ημερες",   latest["netday"],    p7["netday"]      if p7  is not None else None, "#059669")}
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec-hdr">Αναλυση Τμηματων</div>', unsafe_allow_html=True)
    try:
        depts = json.loads(latest.get("depts","[]") or "[]")
        if depts:
            mx   = depts[0]["sales"]
            rows = "".join(
                f'<div class="dept-row"><div class="dept-rank">{i+1}</div>'
                f'<div class="dept-name">{d["name"]}</div>'
                f'<div class="dept-bar-bg"><div class="dept-bar-fill" style="width:{d["sales"]/mx*100:.0f}%"></div></div>'
                f'<div class="dept-val">{fmt_euro(d["sales"])}</div></div>'
                for i, d in enumerate(depts[:12])
            )
            st.markdown(f'<div class="dept-list">{rows}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="banner banner-info">Δεν υπαρχουν δεδομενα τμηματων.</div>', unsafe_allow_html=True)
    except: pass

# ── Tab 2 ─────────────────────────────────────────────────────────────────────
with t2:
    st.markdown('<div class="sec-hdr">Εξελιξη Πωλησεων</div>', unsafe_allow_html=True)
    p = st.radio("", ["30 ημερες","90 ημερες","Ετος"], horizontal=True, label_visibility="collapsed")
    since = (today - timedelta(days=30 if "30" in p else 90)) if "Ετος" not in p else date(today.year,1,1)
    ch = df[df["date"] >= since].sort_values("date").copy()
    ch["L"] = ch["date"].apply(lambda d: d.strftime("%d/%m"))
    if not ch.empty:
        st.markdown("**Ημερησιες Πωλησεις (EUR)**")
        st.bar_chart(ch.set_index("L")["netday"], color="#2563eb", use_container_width=True, height=200)
        st.markdown("**Πελατες**")
        st.bar_chart(ch.set_index("L")["customers"], color="#7c3aed", use_container_width=True, height=160)
        s = period_stats(df, since, today)
        st.markdown('<div class="sec-hdr">Περιληψη Περιοδου</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="kpi-row kpi-row-3">
          <div class="kpi" style="--a:#2563eb"><div class="kpi-lbl">Συνολο</div><div class="kpi-val-sm">{fmt_euro(s["total"])}</div></div>
          <div class="kpi" style="--a:#7c3aed"><div class="kpi-lbl">ΜΟ Ημερας</div><div class="kpi-val-sm">{fmt_euro(s["avg_day"])}</div></div>
          <div class="kpi" style="--a:#059669"><div class="kpi-lbl">Κορυφη ({s["peak"].strftime("%d/%m") if s["peak"] else "—"})</div><div class="kpi-val-sm">{fmt_euro(s["peak_val"])}</div></div>
        </div>""", unsafe_allow_html=True)

# ── Tab 3 ─────────────────────────────────────────────────────────────────────
with t3:
    def cmp(ta, tb, sa, sb):
        def row(lbl, a, b, euro=True):
            fmt = fmt_euro if euro else lambda v: f"{v:.0f}"
            if b == 0: ph = "—"
            else:
                pct = (a-b)/b*100
                cls = "cmp-pos" if pct >= 0 else "cmp-neg"
                ph  = f'<span class="{cls}">{"+" if pct>=0 else ""}{pct:.1f}%</span>'
            return (f'<tr><td>{lbl}</td><td>{fmt(a)}</td><td style="color:#94a3b8">{fmt(b)}</td><td>{ph}</td></tr>')
        return (f'<table class="cmp-table"><thead><tr>'
                f'<th></th><th class="th-cur">{ta}</th><th>{tb}</th><th>Μεταβολη</th>'
                f'</tr></thead><tbody>'
                + row("Συνολο Πωλησεων", sa["total"],    sb["total"])
                + row("ΜΟ Ημερας",       sa["avg_day"],  sb["avg_day"])
                + row("ΜΟ Πελατων",      sa["avg_cus"],  sb["avg_cus"],  euro=False)
                + row("Ημερες",           sa["days"],     sb["days"],     euro=False)
                + row("Κορυφαια",         sa["peak_val"], sb["peak_val"])
                + "</tbody></table>")

    st.markdown('<div class="sec-hdr">Μηνιαια Συγκριση</div>', unsafe_allow_html=True)
    ms  = date(today.year,today.month,1); pe = ms-timedelta(days=1); ps = date(pe.year,pe.month,1)
    st.markdown(cmp(MONTHS_GR[today.month-1], MONTHS_GR[pe.month-1],
                    period_stats(df,ms,today), period_stats(df,ps,pe)), unsafe_allow_html=True)

    st.markdown('<div class="sec-hdr">Εβδομαδιαια Συγκριση</div>', unsafe_allow_html=True)
    ws = today-timedelta(days=today.weekday()); pws = ws-timedelta(days=7)
    st.markdown(cmp("Τρεχουσα", "Προηγουμενη",
                    period_stats(df,ws,today), period_stats(df,pws,ws-timedelta(days=1))), unsafe_allow_html=True)

# ── Tab 4 ─────────────────────────────────────────────────────────────────────
with t4:
    st.markdown('<div class="sec-hdr">Πληρες Ιστορικο</div>', unsafe_allow_html=True)
    d = df[["date","netday","customers","avg_basket"]].copy()
    d["date"]       = d["date"].apply(lambda x: x.strftime("%d/%m/%Y"))
    d["netday"]     = d["netday"].apply(fmt_euro)
    d["avg_basket"] = d["avg_basket"].apply(fmt_euro)
    d["customers"]  = d["customers"].apply(lambda v: f"{int(v)}" if pd.notna(v) else "—")
    d.columns = ["Ημερομηνια","Πωλησεις","Πελατες","ΜΟ Καλαθιου"]
    st.dataframe(d, use_container_width=True, hide_index=True, height=480)
    st.download_button("Εξαγωγη CSV", df.to_csv(index=False).encode("utf-8"),
                       f"sales_{today}.csv", "text/csv")
