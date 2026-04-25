import streamlit as st
import pandas as pd
import io, os
from imap_tools import MailBox, AND
from datetime import datetime, timedelta, date

# ─── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Invoices — AB Skyros",
                   layout="wide", page_icon=None, initial_sidebar_state="expanded")

EMAIL_USER   = "abf.skyros@gmail.com"
EMAIL_PASS   = st.secrets["EMAIL_PASS"]
SENDER_EMAIL = "Notifications@WeDoConnect.com"
MONTHS_GR = ["Ιανουαριος","Φεβρουαριος","Μαρτιος","Απριλιος","Μαιος","Ιουνιος",
              "Ιουλιος","Αυγουστος","Σεπτεμβριος","Οκτωβριος","Νοεμβριος","Δεκεμβριος"]

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;}
.stApp{background:#f0f2f5;}
.block-container{padding:1.4rem 1.6rem 4rem;max-width:1240px;}
section[data-testid="stSidebar"]{background:#0f172a!important;border-right:1px solid #1e293b!important;min-width:210px!important;max-width:210px!important;}
section[data-testid="stSidebar"] *{color:#64748b!important;}
section[data-testid="stSidebar"] a{display:block;padding:.5rem .85rem;border-radius:6px;color:#64748b!important;font-size:.8rem;font-weight:500;text-decoration:none;transition:all .15s;margin-bottom:2px;}
section[data-testid="stSidebar"] a:hover{background:#1e293b;color:#e2e8f0!important;}
section[data-testid="stSidebar"] a[aria-current="page"]{background:#1e3a5f;color:#60a5fa!important;font-weight:600;}
#MainMenu,footer,header{visibility:hidden;}
.ph{background:#0f172a;border-radius:10px;padding:1.3rem 1.6rem;margin-bottom:1.4rem;display:flex;align-items:center;justify-content:space-between;}
.ph-ey{font-size:.62rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#0ea5e9;margin-bottom:.2rem;}
.ph-h1{font-size:1.5rem;font-weight:700;color:#f8fafc;margin:0;}
.ph-rt{text-align:right;} .ph-lbl{font-size:.62rem;color:#475569;} .ph-val{font-family:'JetBrains Mono';font-size:.73rem;color:#64748b;}
.kr{display:grid;gap:.85rem;margin:.9rem 0;}
.kr3{grid-template-columns:repeat(3,1fr);} .kr4{grid-template-columns:repeat(4,1fr);}
@media(max-width:880px){.kr3,.kr4{grid-template-columns:repeat(2,1fr);}}
@media(max-width:580px){.kr3,.kr4{grid-template-columns:1fr;}}
.kc{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:1rem 1.2rem;position:relative;overflow:hidden;}
.kc::before{content:'';position:absolute;top:0;left:0;bottom:0;width:3px;background:var(--a,#0891b2);}
.kl{font-size:.64rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#94a3b8;margin-bottom:.4rem;}
.kv{font-family:'JetBrains Mono';font-size:1.45rem;font-weight:500;color:#0f172a;line-height:1.1;}
.sh{font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#94a3b8;border-bottom:1px solid #e2e8f0;padding-bottom:.45rem;margin:1.6rem 0 .8rem;}
.bn{border-radius:7px;padding:.65rem 1rem;font-size:.78rem;font-weight:500;margin:.6rem 0;}
.bn-ok{background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;}
.bn-warn{background:#fffbeb;border:1px solid #fde68a;color:#92400e;}
.bn-info{background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;}
[data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid #e2e8f0;gap:.2rem;}
[data-baseweb="tab"]{background:transparent!important;border:none!important;color:#94a3b8!important;font-size:.75rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;padding:.5rem 1rem!important;border-radius:6px 6px 0 0!important;}
[aria-selected="true"][data-baseweb="tab"]{color:#0369a1!important;background:#e0f2fe!important;border-bottom:2px solid #0891b2!important;}
.stButton>button{background:#0891b2!important;color:#fff!important;border:none!important;border-radius:7px!important;font-weight:600!important;font-size:.8rem!important;padding:.48rem 1.1rem!important;}
.stButton>button:hover{background:#0e7490!important;}
button[kind="secondary"]{background:#fff!important;color:#374151!important;border:1px solid #d1d5db!important;}
[data-testid="stDataFrame"]{border:1px solid #e2e8f0;border-radius:9px;overflow:hidden;}
[data-baseweb="select"]>div{background:#fff!important;border-color:#d1d5db!important;}
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1.1rem 0 1.2rem;">
      <div style="font-size:.6rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#60a5fa;margin-bottom:.25rem;">AB SKYROS 1082</div>
      <div style="font-size:.95rem;font-weight:700;color:#f1f5f9;margin-bottom:1.4rem;">Business Hub</div>
      <div style="font-size:.58rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#374151;margin-bottom:.4rem;padding-left:.85rem;">NAVIGATION</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("Home.py",             label="Home")
    st.page_link("pages/1_Sales.py",    label="Sales Analytics")
    st.page_link("pages/2_Invoices.py", label="Invoices")

def fmt_euro(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
    return f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".") + " €"

# ─── LOAD INVOICES ───────────────────────────────────────────────────────────────
def find_and_load(content, filename):
    try:
        if filename.lower().endswith((".xlsx",".xls")):
            dr = pd.read_excel(io.BytesIO(content), header=None)
        else:
            try: dr = pd.read_csv(io.BytesIO(content), header=None, sep=None, engine="python")
            except: dr = pd.read_csv(io.BytesIO(content), header=None, encoding="cp1253", sep=None, engine="python")
        hi=-1
        for i in range(min(40,len(dr))):
            rs=" ".join(str(x).upper() for x in dr.iloc[i].values if pd.notna(x))
            if "ΤΥΠΟΣ" in rs and "ΗΜΕΡΟΜΗΝΙΑ" in rs: hi=i; break
        if hi==-1: return None
        df=dr.iloc[hi+1:].copy()
        df.columns=[str(h).strip().upper() for h in dr.iloc[hi]]
        df=df.loc[:,df.columns.notna()]
        df=df.loc[:,~df.columns.str.contains("NAN|UNNAMED",case=False)]
        return df.reset_index(drop=True)
    except: return None

@st.cache_data(ttl=600)
def load_invoices():
    all_data=pd.DataFrame()
    try:
        with MailBox("imap.gmail.com").login(EMAIL_USER,EMAIL_PASS) as mb:
            for msg in mb.fetch(AND(from_=SENDER_EMAIL),limit=30,reverse=True):
                for att in msg.attachments:
                    if not att.filename.lower().endswith((".xlsx",".csv",".xls")): continue
                    df=find_and_load(att.payload,att.filename)
                    if df is None: continue
                    cd=next((c for c in df.columns if "ΗΜΕΡΟΜΗΝΙΑ" in c),None)
                    cv=next((c for c in df.columns if "ΑΞΙΑ" in c or "ΣΥΝΟΛΟ" in c),None)
                    ct=next((c for c in df.columns if "ΤΥΠΟΣ" in c),None)
                    if not(cd and cv and ct): continue
                    tmp=df[[cd,ct,cv]].copy(); tmp.columns=["DATE","TYPE","VALUE"]
                    tmp["DATE"]=pd.to_datetime(tmp["DATE"],errors="coerce")
                    if tmp["VALUE"].dtype==object:
                        tmp["VALUE"]=tmp["VALUE"].astype(str).str.replace("€","").str.replace(",",".").str.strip()
                    tmp["VALUE"]=pd.to_numeric(tmp["VALUE"],errors="coerce").fillna(0)
                    all_data=pd.concat([all_data,tmp.dropna(subset=["DATE"])],ignore_index=True)
        st.session_state["invoice_data"]=all_data
        return all_data
    except Exception as e:
        st.error(f"Σφαλμα συνδεσης: {e}")
        return pd.DataFrame()

# ─── UI ─────────────────────────────────────────────────────────────────────────
today=date.today()
st.markdown(f"""
<div class="ph">
  <div><div class="ph-ey">AB Skyros — Καταστημα 1082</div><div class="ph-h1">Ελεγχος Τιμολογιων</div></div>
  <div class="ph-rt"><div class="ph-lbl">Ανανεωση</div><div class="ph-val">{datetime.now().strftime('%d/%m/%Y %H:%M')}</div></div>
</div>""",unsafe_allow_html=True)

c1,_=st.columns([1,3])
with c1:
    if st.button("Φορτωση / Ανανεωση",use_container_width=True):
        st.cache_data.clear(); st.rerun()

df=load_invoices()
if df.empty:
    st.markdown('<div class="bn bn-warn">Δεν βρεθηκαν δεδομενα. Πατηστε Φορτωση.</div>',unsafe_allow_html=True)
    st.stop()

n=len(df); df_from=df["DATE"].min().strftime("%d/%m/%Y"); df_to=df["DATE"].max().strftime("%d/%m/%Y")
st.markdown(f'<div class="bn bn-ok">Φορτωθηκαν {n:,} εγγραφες · {df_from} — {df_to}</div>',unsafe_allow_html=True)

tw,tm,tall=st.tabs(["Εβδομαδιαια","Μηνιαια","Συνολικη Εικονα"])

with tw:
    st.markdown('<div class="sh">Εβδομαδιαια Εικονα</div>',unsafe_allow_html=True)
    sel=st.date_input("Ημερα:",today,label_visibility="collapsed")
    ws=sel-timedelta(days=sel.weekday()); we=ws+timedelta(days=6)
    st.markdown(f'<p style="font-size:.76rem;color:#94a3b8;margin-bottom:.8rem;">Εβδομαδα: {ws.strftime("%d/%m/%Y")} — {we.strftime("%d/%m/%Y")}</p>',unsafe_allow_html=True)
    wdf=df[(df["DATE"]>=pd.Timestamp(ws))&(df["DATE"]<=pd.Timestamp(we))]
    if not wdf.empty:
        inv=wdf[~wdf["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        crd=wdf[ wdf["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        st.markdown(f"""<div class="kr kr3">
          <div class="kc" style="--a:#0891b2"><div class="kl">Τιμολογια</div><div class="kv">{fmt_euro(inv)}</div></div>
          <div class="kc" style="--a:#dc2626"><div class="kl">Πιστωτικα</div><div class="kv">{fmt_euro(crd)}</div></div>
          <div class="kc" style="--a:#059669"><div class="kl">Καθαρο Συνολο</div><div class="kv">{fmt_euro(inv-crd)}</div></div>
        </div>""",unsafe_allow_html=True)
        st.markdown('<div class="sh">Αναλυτικα</div>',unsafe_allow_html=True)
        dsp=wdf.copy(); dsp["DATE"]=dsp["DATE"].dt.strftime("%d/%m/%Y")
        dsp.columns=["Ημερομηνια","Τυπος","Αξια (EUR)"]
        st.dataframe(dsp,use_container_width=True,hide_index=True)
    else:
        st.markdown('<div class="bn bn-info">Δεν υπαρχουν εγγραφες αυτη την εβδομαδα.</div>',unsafe_allow_html=True)

with tm:
    st.markdown('<div class="sh">Μηνιαια Εικονα</div>',unsafe_allow_html=True)
    mc1,mc2=st.columns(2)
    with mc1: sm=st.selectbox("Μηνας",range(1,13),format_func=lambda x:MONTHS_GR[x-1],index=today.month-1,label_visibility="collapsed")
    with mc2:
        years=sorted(df["DATE"].dt.year.dropna().unique().astype(int),reverse=True)
        sy=st.selectbox("Ετος",years,label_visibility="collapsed")
    mdf=df[(df["DATE"].dt.month==sm)&(df["DATE"].dt.year==sy)]
    if not mdf.empty:
        im=mdf[~mdf["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        cm=mdf[ mdf["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
        st.markdown(f"""<div class="kr kr3">
          <div class="kc" style="--a:#0891b2"><div class="kl">Τιμολογια {MONTHS_GR[sm-1][:3]}.</div><div class="kv">{fmt_euro(im)}</div></div>
          <div class="kc" style="--a:#dc2626"><div class="kl">Πιστωτικα {MONTHS_GR[sm-1][:3]}.</div><div class="kv">{fmt_euro(cm)}</div></div>
          <div class="kc" style="--a:#059669"><div class="kl">Καθαρο {MONTHS_GR[sm-1][:3]}.</div><div class="kv">{fmt_euro(im-cm)}</div></div>
        </div>""",unsafe_allow_html=True)
        st.markdown('<div class="sh">Αναλυση ανα Εβδομαδα</div>',unsafe_allow_html=True)
        mdf2=mdf.copy(); mdf2["wk"]=mdf2["DATE"].dt.isocalendar().week.astype(int)
        rows2=[]
        for wk,grp in mdf2.groupby("wk"):
            ii=grp[~grp["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
            cc=grp[ grp["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
            rows2.append({"Εβδομαδα":int(wk),"Τιμολογια":fmt_euro(ii),"Πιστωτικα":fmt_euro(cc),"Καθαρο":fmt_euro(ii-cc)})
        st.dataframe(pd.DataFrame(rows2),use_container_width=True,hide_index=True)
        st.markdown('<hr style="border:none;border-top:1px solid #e2e8f0;margin:1.5rem 0;"/>',unsafe_allow_html=True)
        csv2=mdf.copy(); csv2["DATE"]=csv2["DATE"].dt.strftime("%d/%m/%Y"); csv2.columns=["ΗΜΕΡΟΜΗΝΙΑ","ΤΥΠΟΣ","ΑΞΙΑ"]
        st.download_button("Εξαγωγη CSV Μηνα",csv2.to_csv(index=False).encode("utf-8-sig"),f"invoices_{sm}_{sy}.csv","text/csv")
    else:
        st.markdown('<div class="bn bn-info">Δεν υπαρχουν εγγραφες αυτον τον μηνα.</div>',unsafe_allow_html=True)

with tall:
    st.markdown('<div class="sh">Συνολικα Στοιχεια</div>',unsafe_allow_html=True)
    ti=df[~df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
    tc=df[ df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)]["VALUE"].sum()
    st.markdown(f"""<div class="kr kr3">
      <div class="kc" style="--a:#0891b2"><div class="kl">Συνολο Τιμολογιων</div><div class="kv">{fmt_euro(ti)}</div></div>
      <div class="kc" style="--a:#dc2626"><div class="kl">Συνολο Πιστωτικων</div><div class="kv">{fmt_euro(tc)}</div></div>
      <div class="kc" style="--a:#059669"><div class="kl">Καθαρο Συνολο</div><div class="kv">{fmt_euro(ti-tc)}</div></div>
    </div>""",unsafe_allow_html=True)
    st.markdown('<div class="sh">Μηνιαια Εξελιξη</div>',unsafe_allow_html=True)
    mon=df[~df["TYPE"].str.contains("ΠΙΣΤΩΤΙΚΟ",na=False)].copy()
    mon["M"]=mon["DATE"].dt.to_period("M").astype(str)
    mch=mon.groupby("M")["VALUE"].sum().reset_index()
    if not mch.empty: st.bar_chart(mch.set_index("M")["VALUE"],color="#0891b2",use_container_width=True,height=200)
    st.markdown('<div class="sh">Ολες οι Εγγραφες</div>',unsafe_allow_html=True)
    dsp3=df.copy(); dsp3["DATE"]=dsp3["DATE"].dt.strftime("%d/%m/%Y"); dsp3.columns=["Ημερομηνια","Τυπος","Αξια (EUR)"]
    st.dataframe(dsp3,use_container_width=True,hide_index=True,height=380)
