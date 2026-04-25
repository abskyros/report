import streamlit as st
import pandas as pd
import os, sys
from imap_tools import MailBox, AND
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import CSS, MONTHS_GR, fmt_euro, find_header_and_load

st.set_page_config(page_title="Invoices — AB Skyros",
                   layout="wide", page_icon=None, initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)

EMAIL_USER   = "abf.skyros@gmail.com"
EMAIL_PASS   = st.secrets["EMAIL_PASS"]
SENDER_EMAIL = "Notifications@WeDoConnect.com"

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

# ── Load invoices ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_invoices():
    all_data = pd.DataFrame()
    try:
        with MailBox("imap.gmail.com").login(EMAIL_USER, EMAIL_PASS) as mb:
            for msg in mb.fetch(AND(from_=SENDER_EMAIL), limit=30, reverse=True):
                for att in msg.attachments:
                    if not att.filename.lower().endswith((".xlsx",".csv",".xls")): continue
                    df = find_header_and_load(att.payload, att.filename)
                    if df is None: continue
                    col_d = next((c for c in df.columns if "ΗΜΕΡΟΜΗΝΙΑ" in c), None)
                    col_v = next((c for c in df.columns if "ΑΞΙΑ" in c or "ΣΥΝΟΛΟ" in c), None)
                    col_t = next((c for c in df.columns if "ΤΥΠΟΣ" in c), None)
                    if not (col_d and col_v and col_t): continue
                    tmp = df[[col_d, col_t, col_v]].copy()
                    tmp.columns = ["DATE","TYPE","VALUE"]
                    tmp["DATE"] = pd.to_datetime(tmp["DATE"], errors="coerce")
                    if tmp["VALUE"].dtype == object:
                        tmp["VALUE"] = (tmp["VALUE"].astype(str)
                                        .str.replace("€","").str.replace(",",".").str.strip())
                    tmp["VALUE"] = pd.to_numeric(tmp["VALUE"], errors="coerce").fillna(0)
                    all_data = pd.concat([all_data, tmp.dropna(subset=["DATE"])], ignore_index=True)
        st.session_state["invoice_data"] = all_data
        return all_data
    except Exception as e:
        st.error(f"Σφάλμα σύνδεσης: {e}")
        return pd.DataFrame()

# ── UI ────────────────────────────────────────────────────────────────────────
today = date.today()
st.markdown(f"""
<div class="page-header" style="border-left:4px solid #0891b2;">
  <div class="page-header-left">
    <div class="eyebrow" style="color:#0891b2;">AB Skyros — Κατάστημα 1082</div>
    <h1>Ελεγχος Τιμολογιων</h1>
  </div>
  <div class="page-header-right">
    <div class="ts-label">Ανανεωση</div>
    <div class="ts-val">{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

rc1, rc2 = st.columns([1, 3])
with rc1:
    if st.button("Φορτωση / Ανανεωση", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

df = load_invoices()

if df.empty:
    st.markdown('<div class="banner banner-warn" style="margin-top:1rem;">Δεν βρέθηκαν δεδομένα. Πατήστε «Φόρτωση».</div>', unsafe_allow_html=True)
    st.stop()

n_rows = len(df)
d_from = df["DATE"].min().strftime("%d/%m/%Y")
d_to   = df["DATE"].max().strftime("%d/%m/%Y")
st.markdown(f'<div class="banner banner-ok">Φορτωθηκαν {n_rows:,} εγγραφες · {d_from} — {d_to}</div>', unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tw, tm, tall = st.tabs(["Εβδομαδιαια", "Μηνιαια", "Συνολικη Εικονα"])

# ── Εβδομαδιαία ──────────────────────────────────────────────────────────────
with tw:
    st.markdown('<div class="sec-hdr">Εβδομαδιαια Εικονα</div>', unsafe_allow_html=True)
    sel = st.date_input("Ημέρα εβδομάδας:", today, label_visibility="collapsed")
    ws  = sel - timedelta(days=sel.weekday())
    we  = ws + timedelta(days=6)
    st.markdown(f'<p style="font-size:.78rem;color:#94a3b8;margin-bottom:1rem;">Εβδομάδα: {ws.strftime("%d/%m/%Y")} — {we.strftime("%d/%m/%Y")}</p>', unsafe_allow_html=True)

    wdf = df[(df["DATE"] >= pd.Timestamp(ws)) & (df["DATE"] <= pd.Timestamp(we))]
    if not wdf.empty:
        inv = wdf[~wdf["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        crd = wdf[ wdf["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        st.markdown(f"""<div class="kpi-row kpi-row-3">
          <div class="kpi" style="--a:#0891b2"><div class="kpi-lbl">Τιμολογια</div><div class="kpi-val">{fmt_euro(inv)}</div></div>
          <div class="kpi" style="--a:#dc2626"><div class="kpi-lbl">Πιστωτικα</div><div class="kpi-val">{fmt_euro(crd)}</div></div>
          <div class="kpi" style="--a:#059669"><div class="kpi-lbl">Καθαρο Συνολο</div><div class="kpi-val">{fmt_euro(inv-crd)}</div></div>
        </div>""", unsafe_allow_html=True)
        st.markdown('<div class="sec-hdr">Αναλυτικα</div>', unsafe_allow_html=True)
        dsp = wdf.copy(); dsp["DATE"] = dsp["DATE"].dt.strftime("%d/%m/%Y")
        dsp.columns = ["Ημερομηνια","Τυπος","Αξια (EUR)"]
        st.dataframe(dsp, use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="banner banner-info">Δεν υπάρχουν εγγραφές αυτή την εβδομάδα.</div>', unsafe_allow_html=True)

# ── Μηνιαία ──────────────────────────────────────────────────────────────────
with tm:
    st.markdown('<div class="sec-hdr">Μηνιαια Εικονα</div>', unsafe_allow_html=True)
    mc1, mc2 = st.columns(2)
    with mc1:
        s_m = st.selectbox("Μήνας", range(1,13),
                           format_func=lambda x: MONTHS_GR[x-1],
                           index=today.month-1, label_visibility="collapsed")
    with mc2:
        years = sorted(df["DATE"].dt.year.dropna().unique().astype(int), reverse=True)
        s_y   = st.selectbox("Ετος", years, label_visibility="collapsed")

    mdf = df[(df["DATE"].dt.month == s_m) & (df["DATE"].dt.year == s_y)]
    if not mdf.empty:
        inv_m = mdf[~mdf["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        crd_m = mdf[ mdf["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
        st.markdown(f"""<div class="kpi-row kpi-row-3">
          <div class="kpi" style="--a:#0891b2"><div class="kpi-lbl">Τιμολογια {MONTHS_GR[s_m-1][:3]}.</div><div class="kpi-val">{fmt_euro(inv_m)}</div></div>
          <div class="kpi" style="--a:#dc2626"><div class="kpi-lbl">Πιστωτικα {MONTHS_GR[s_m-1][:3]}.</div><div class="kpi-val">{fmt_euro(crd_m)}</div></div>
          <div class="kpi" style="--a:#059669"><div class="kpi-lbl">Καθαρο {MONTHS_GR[s_m-1][:3]}.</div><div class="kpi-val">{fmt_euro(inv_m-crd_m)}</div></div>
        </div>""", unsafe_allow_html=True)

        # Εβδομαδιαία ανάλυση μέσα στον μήνα
        st.markdown('<div class="sec-hdr">Αναλυση ανα Εβδομαδα</div>', unsafe_allow_html=True)
        mdf2  = mdf.copy()
        mdf2["wk"] = mdf2["DATE"].dt.isocalendar().week.astype(int)

        rows = []
        for wk, grp in mdf2.groupby("wk"):
            i = grp[~grp["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
            c = grp[ grp["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
            rows.append({"Εβδομαδα": int(wk), "Τιμολογια": i, "Πιστωτικα": c, "Καθαρο": i-c})
        wk_df = pd.DataFrame(rows)
        st.dataframe(wk_df, use_container_width=True, hide_index=True)

        st.markdown('<hr class="divider"/>', unsafe_allow_html=True)
        csv = mdf.copy(); csv["DATE"] = csv["DATE"].dt.strftime("%d/%m/%Y")
        csv.columns = ["ΗΜΕΡΟΜΗΝΙΑ","ΤΥΠΟΣ","ΑΞΙΑ"]
        st.download_button("Εξαγωγη CSV Μηνα",
                           csv.to_csv(index=False).encode("utf-8-sig"),
                           f"invoices_{s_m}_{s_y}.csv", "text/csv")
    else:
        st.markdown('<div class="banner banner-info">Δεν υπάρχουν εγγραφές αυτόν τον μήνα.</div>', unsafe_allow_html=True)

# ── Συνολική ─────────────────────────────────────────────────────────────────
with tall:
    st.markdown('<div class="sec-hdr">Συνολικα Στοιχεια</div>', unsafe_allow_html=True)
    tot_inv = df[~df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
    tot_crd = df[ df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)]["VALUE"].sum()
    st.markdown(f"""<div class="kpi-row kpi-row-3">
      <div class="kpi" style="--a:#0891b2"><div class="kpi-lbl">Συνολο Τιμολογιων</div><div class="kpi-val">{fmt_euro(tot_inv)}</div></div>
      <div class="kpi" style="--a:#dc2626"><div class="kpi-lbl">Συνολο Πιστωτικων</div><div class="kpi-val">{fmt_euro(tot_crd)}</div></div>
      <div class="kpi" style="--a:#059669"><div class="kpi-lbl">Καθαρο Συνολο</div><div class="kpi-val">{fmt_euro(tot_inv-tot_crd)}</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec-hdr">Μηνιαια Εξελιξη</div>', unsafe_allow_html=True)
    monthly = df[~df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ", na=False)].copy()
    monthly["M"] = monthly["DATE"].dt.to_period("M").astype(str)
    mch = monthly.groupby("M")["VALUE"].sum().reset_index()
    if not mch.empty:
        st.bar_chart(mch.set_index("M")["VALUE"], color="#0891b2", use_container_width=True, height=200)

    st.markdown('<div class="sec-hdr">Ολες οι Εγγραφες</div>', unsafe_allow_html=True)
    dsp2 = df.copy(); dsp2["DATE"] = dsp2["DATE"].dt.strftime("%d/%m/%Y")
    dsp2.columns = ["Ημερομηνια","Τυπος","Αξια (EUR)"]
    st.dataframe(dsp2, use_container_width=True, hide_index=True, height=400)
