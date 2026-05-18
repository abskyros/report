"""
gsheets_helper.py — Κεντρική αποθήκη δεδομένων μέσω Google Sheets.
Αντικαθιστά όλα τα CSV αρχεία. Τα δεδομένα δεν χάνονται ποτέ.

Streamlit Secrets που χρειάζονται:
  SPREADSHEET_ID = "1AbC..."
  [gcp_service_account]
  type = "service_account"
  project_id = "..."
  private_key_id = "..."
  private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
  client_email = "bot@project.iam.gserviceaccount.com"
  client_id = "..."
  auth_uri = "https://accounts.google.com/o/oauth2/auth"
  token_uri = "https://oauth2.googleapis.com/token"
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

SALES_SHEET    = "sales"
INVOICES_SHEET = "invoices"


# ── CONNECTION (cached για όλη τη session) ────────────────────────────────────

@st.cache_resource
def _client():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds)


@st.cache_resource
def _spreadsheet():
    return _client().open_by_key(st.secrets["SPREADSHEET_ID"])


def _ws(sheet_name: str):
    return _spreadsheet().worksheet(sheet_name)


# ── SALES ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def load_sales() -> pd.DataFrame:
    """Φορτώνει όλες τις πωλήσεις από το Google Sheet. Cache 2 λεπτά."""
    try:
        rows = _ws(SALES_SHEET).get_all_records()
        if not rows:
            return pd.DataFrame(columns=["date", "net_sales", "customers", "avg_basket"])
        df = pd.DataFrame(rows)
        df["date"]       = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["net_sales"]  = pd.to_numeric(df["net_sales"],  errors="coerce")
        df["customers"]  = pd.to_numeric(df["customers"],  errors="coerce")
        df["avg_basket"] = pd.to_numeric(df["avg_basket"], errors="coerce")
        df = df.dropna(subset=["date", "net_sales"])
        return (df.sort_values("net_sales", ascending=False)
                  .drop_duplicates("date", keep="first")
                  .sort_values("date", ascending=False)
                  .reset_index(drop=True))
    except Exception:
        return pd.DataFrame(columns=["date", "net_sales", "customers", "avg_basket"])


def _save_sales(df: pd.DataFrame):
    """Γράφει ολόκληρο το DataFrame πωλήσεων στο Sheet."""
    ws  = _ws(SALES_SHEET)
    out = (df.sort_values("date", ascending=False)
             .drop_duplicates("date", keep="first")
             .reset_index(drop=True)
             .copy())
    out["date"] = out["date"].astype(str)
    data = [out.columns.tolist()] + out.fillna("").values.tolist()
    ws.clear()
    ws.update(data)
    load_sales.clear()   # Ακυρώνει το cache ώστε η επόμενη ανάγνωση να φέρει φρέσκα δεδομένα


def merge_sales(recs: list) -> int:
    """
    Συγχωνεύει νέες εγγραφές πωλήσεων με το υπάρχον Sheet.
    Επιστρέφει τον αριθμό εγγραφών που άλλαξαν.
    """
    if not recs:
        return 0

    ndf = pd.DataFrame(recs)
    ndf["date"]      = pd.to_datetime(ndf["date"], errors="coerce").dt.date
    ndf["net_sales"] = pd.to_numeric(ndf["net_sales"], errors="coerce")
    ndf = (ndf.dropna(subset=["date", "net_sales"])
              .sort_values("net_sales", ascending=False)
              .drop_duplicates("date", keep="first"))

    existing = load_sales()
    changed  = 0
    base     = existing.copy()

    for _, r in ndf.iterrows():
        ex = existing[existing["date"] == r["date"]]
        if ex.empty:
            base    = pd.concat([base, r.to_frame().T], ignore_index=True)
            changed += 1
        elif r["net_sales"] > ex.iloc[0]["net_sales"]:
            base    = base[base["date"] != r["date"]]
            base    = pd.concat([base, r.to_frame().T], ignore_index=True)
            changed += 1

    if changed > 0:
        _save_sales(base)
    return changed


# ── INVOICES ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def load_invoices() -> pd.DataFrame:
    """Φορτώνει όλα τα τιμολόγια από το Google Sheet. Cache 2 λεπτά."""
    try:
        rows = _ws(INVOICES_SHEET).get_all_records()
        if not rows:
            return pd.DataFrame(columns=["DATE", "TYPE", "VALUE"])
        df = pd.DataFrame(rows)
        df["DATE"]  = pd.to_datetime(df["DATE"], errors="coerce")
        df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")
        df = df.dropna(subset=["DATE", "VALUE"])
        return df.sort_values("DATE", ascending=False).reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=["DATE", "TYPE", "VALUE"])


def _save_invoices(df: pd.DataFrame):
    """Γράφει ολόκληρο το DataFrame τιμολογίων στο Sheet."""
    ws  = _ws(INVOICES_SHEET)
    out = df.sort_values("DATE", ascending=False).reset_index(drop=True).copy()
    out["DATE"] = out["DATE"].astype(str)
    data = [out.columns.tolist()] + out.fillna("").values.tolist()
    ws.clear()
    ws.update(data)
    load_invoices.clear()


def merge_invoices(new_dfs: list) -> int:
    """
    Συγχωνεύει νέα τιμολόγια (λίστα DataFrames) με το υπάρχον Sheet.
    Επιστρέφει τον αριθμό νέων γραμμών.
    """
    if not new_dfs:
        return 0

    new_df   = pd.concat(new_dfs, ignore_index=True)
    existing = load_invoices()
    merged   = (pd.concat([existing, new_df])
                  .drop_duplicates(subset=["DATE", "TYPE", "VALUE"])
                  .sort_values("DATE", ascending=False)
                  .reset_index(drop=True))
    n_new = len(merged) - len(existing)
    if n_new > 0:
        _save_invoices(merged)
    return max(n_new, 0)
