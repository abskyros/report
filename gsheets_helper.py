"""
gsheets_helper.py — Κεντρική αποθήκη δεδομένων μέσω Google Sheets.
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SALES_SHEET    = "sales"
INVOICES_SHEET = "invoices"


# ── PEM FIX ───────────────────────────────────────────────────────────────────

def _fix_pem(key: str) -> str:
    """
    Διορθώνει το private_key:
    1. Literal \\n → πραγματικό newline
    2. Αν το key είναι PKCS#8 αλλά έχει λανθασμένο 'BEGIN RSA PRIVATE KEY'
       header, το αλλάζει σε 'BEGIN PRIVATE KEY' που είναι το σωστό.
       (Το Google Cloud παράγει PKCS#8 keys — ο σωστός header είναι PRIVATE KEY)
    """
    key = key.strip().replace("\r\n", "\n").replace("\r", "\n")
    if "\\n" in key:
        key = key.replace("\\n", "\n")

    # Διόρθωση header: RSA PRIVATE KEY → PRIVATE KEY για PKCS#8 keys
    if "-----BEGIN RSA PRIVATE KEY-----" in key:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        # Δοκίμασε το RSA header πρώτα
        try:
            load_pem_private_key(key.encode(), password=None)
            # Δουλεύει → αφήνουμε ως έχει
        except Exception:
            # Δεν δουλεύει → δοκίμασε με PKCS#8 header
            alt = (key
                   .replace("-----BEGIN RSA PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----")
                   .replace("-----END RSA PRIVATE KEY-----",   "-----END PRIVATE KEY-----"))
            try:
                load_pem_private_key(alt.encode(), password=None)
                key = alt  # PKCS#8 header δουλεύει → χρησιμοποιούμε αυτό
            except Exception:
                pass  # Αφήνουμε ως έχει, το Google SDK θα δώσει καλύτερο μήνυμα

    return key


# ── CONNECTION ────────────────────────────────────────────────────────────────

def _get_client():
    """Fresh gspread client — χωρίς cache για αποφυγή stale connection errors."""
    raw  = st.secrets["gcp_service_account"]
    info = {k: v for k, v in raw.items()}

    info["private_key"] = _fix_pem(str(info.get("private_key", "")))

    if "token_uri" not in info:
        info["token_uri"] = "https://oauth2.googleapis.com/token"
    if "type" not in info:
        info["type"] = "service_account"

    try:
        return gspread.service_account_from_dict(info)
    except Exception as e:
        raise RuntimeError(f"Google Auth αποτυχία: {e}") from e


def _ws(sheet_name: str):
    return _get_client().open_by_key(st.secrets["SPREADSHEET_ID"]).worksheet(sheet_name)


# ── SALES ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def load_sales() -> pd.DataFrame:
    try:
        rows = _ws(SALES_SHEET).get_all_records()
        if not rows:
            return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])
        df = pd.DataFrame(rows)
        df["date"]       = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["net_sales"]  = pd.to_numeric(df["net_sales"],  errors="coerce")
        df["customers"]  = pd.to_numeric(df["customers"],  errors="coerce")
        df["avg_basket"] = pd.to_numeric(df["avg_basket"], errors="coerce")
        df = df.dropna(subset=["date","net_sales"])
        return (df.sort_values("net_sales", ascending=False)
                  .drop_duplicates("date", keep="first")
                  .sort_values("date", ascending=False)
                  .reset_index(drop=True))
    except Exception as e:
        st.warning(f"⚠️ Σφάλμα φόρτωσης πωλήσεων: {e}")
        return pd.DataFrame(columns=["date","net_sales","customers","avg_basket"])


def _save_sales(df: pd.DataFrame):
    out = (df.sort_values("date", ascending=False)
             .drop_duplicates("date", keep="first")
             .reset_index(drop=True).copy())
    out["date"] = out["date"].astype(str)
    data = [out.columns.tolist()] + out.fillna("").values.tolist()
    ws = _ws(SALES_SHEET)
    ws.clear()
    ws.update(data)
    load_sales.clear()


def merge_sales(recs: list) -> int:
    if not recs:
        return 0
    ndf = pd.DataFrame(recs)
    ndf["date"]      = pd.to_datetime(ndf["date"], errors="coerce").dt.date
    ndf["net_sales"] = pd.to_numeric(ndf["net_sales"], errors="coerce")
    ndf = (ndf.dropna(subset=["date","net_sales"])
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
    try:
        rows = _ws(INVOICES_SHEET).get_all_records()
        if not rows:
            return pd.DataFrame(columns=["DATE","TYPE","VALUE"])
        df = pd.DataFrame(rows)
        df["DATE"]  = pd.to_datetime(df["DATE"], errors="coerce")
        df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")
        df = df.dropna(subset=["DATE","VALUE"])
        return df.sort_values("DATE", ascending=False).reset_index(drop=True)
    except Exception as e:
        st.warning(f"⚠️ Σφάλμα φόρτωσης τιμολογίων: {e}")
        return pd.DataFrame(columns=["DATE","TYPE","VALUE"])


def _save_invoices(df: pd.DataFrame):
    out = df.sort_values("DATE", ascending=False).reset_index(drop=True).copy()
    out["DATE"] = out["DATE"].astype(str)
    data = [out.columns.tolist()] + out.fillna("").values.tolist()
    ws = _ws(INVOICES_SHEET)
    ws.clear()
    ws.update(data)
    load_invoices.clear()


def merge_invoices(new_dfs: list) -> int:
    if not new_dfs:
        return 0
    new_df   = pd.concat(new_dfs, ignore_index=True)
    existing = load_invoices()
    merged   = (pd.concat([existing, new_df])
                  .drop_duplicates(subset=["DATE","TYPE","VALUE"])
                  .sort_values("DATE", ascending=False)
                  .reset_index(drop=True))
    n_new = len(merged) - len(existing)
    if n_new > 0:
        _save_invoices(merged)
    return max(n_new, 0)
