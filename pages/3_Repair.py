"""
3_Repair.py — One-time data repair για παλιά λάθος δεδομένα.
Τοποθέτησέ το στον φάκελο pages/ δίπλα στα άλλα.
"""

import streamlit as st
import pandas as pd
from gsheets_helper import (
    load_sales, load_invoices,
    _save_sales, _save_invoices,
)

st.set_page_config(page_title="Διόρθωση Δεδομένων", page_icon="🔧", layout="wide")

st.title("🔧 Διόρθωση Παλιών Δεδομένων")
st.caption("Σαρώνει τα Google Sheets για ύποπτες τιμές (100× μεγαλύτερες) και τις διορθώνει.")

# ── SALES ─────────────────────────────────────────────────────────────────────
st.header("📊 Πωλήσεις")

df_s = load_sales()
if df_s.empty:
    st.info("Δεν υπάρχουν δεδομένα πωλήσεων.")
else:
    # Heuristic: σε ένα κατάστημα ΑΒ Σκύρου, daily net_sales > 80.000€ είναι σχεδόν
    # σίγουρα λάθος. ΜΟ καλαθιού > 100€ είναι ύποπτο.
    bad_s = df_s[(df_s["net_sales"] > 80000) | (df_s["avg_basket"] > 200)].copy()

    if bad_s.empty:
        st.success("✅ Καμία ύποπτη εγγραφή πωλήσεων.")
    else:
        st.warning(f"Βρέθηκαν **{len(bad_s)}** ύποπτες εγγραφές. Προεπισκόπηση:")

        preview = bad_s.copy()
        preview["net_sales_διορθωμένο"]  = (preview["net_sales"]  / 100).round(2)
        preview["avg_basket_διορθωμένο"] = (preview["avg_basket"] / 100).round(2)
        st.dataframe(
            preview[["date", "net_sales", "net_sales_διορθωμένο",
                     "customers", "avg_basket", "avg_basket_διορθωμένο"]],
            use_container_width=True, hide_index=True
        )

        if st.button("🔧 Διαίρεσε με 100 αυτές τις γραμμές", type="primary", key="fix_sales"):
            fixed = df_s.copy()
            mask = (fixed["net_sales"] > 80000) | (fixed["avg_basket"] > 200)
            fixed.loc[mask, "net_sales"]  = (fixed.loc[mask, "net_sales"]  / 100).round(2)
            fixed.loc[mask, "avg_basket"] = (fixed.loc[mask, "avg_basket"] / 100).round(2)
            _save_sales(fixed)
            st.success(f"✅ Διορθώθηκαν {mask.sum()} εγγραφές πωλήσεων.")
            st.rerun()

# ── INVOICES ──────────────────────────────────────────────────────────────────
st.header("📄 Τιμολόγια")

df_i = load_invoices()
if df_i.empty:
    st.info("Δεν υπάρχουν δεδομένα τιμολογίων.")
else:
    # Heuristic: μεμονωμένο τιμολόγιο > 50.000€ σε μικρό κατάστημα είναι ύποπτο.
    THRESHOLD = 50000
    bad_i = df_i[df_i["VALUE"] > THRESHOLD].copy()

    if bad_i.empty:
        st.success("✅ Καμία ύποπτη εγγραφή τιμολογίων.")
    else:
        st.warning(f"Βρέθηκαν **{len(bad_i)}** τιμολόγια > {THRESHOLD:,}€. Προεπισκόπηση:")

        preview = bad_i.copy()
        preview["VALUE_διορθωμένο"] = (preview["VALUE"] / 100).round(2)
        preview["DATE"] = preview["DATE"].dt.strftime("%d/%m/%Y")
        st.dataframe(
            preview[["DATE", "TYPE", "VALUE", "VALUE_διορθωμένο"]],
            use_container_width=True, hide_index=True
        )

        col1, col2 = st.columns(2)
        with col1:
            custom_threshold = st.number_input(
                "Προσαρμογή ορίου (€)",
                min_value=1000, max_value=500000, value=THRESHOLD, step=1000,
                help="Αν έχεις πραγματικά μεγάλο τιμολόγιο, αύξησε το όριο."
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔧 Διαίρεσε με 100", type="primary", key="fix_inv"):
                fixed = df_i.copy()
                mask = fixed["VALUE"] > custom_threshold
                fixed.loc[mask, "VALUE"] = (fixed.loc[mask, "VALUE"] / 100).round(2)
                _save_invoices(fixed)
                st.success(f"✅ Διορθώθηκαν {mask.sum()} τιμολόγια.")
                st.rerun()

st.divider()
st.caption("⚠️ Η διαίρεση γίνεται in-place στο Google Sheet. Αν θέλεις backup, αντίγραψε το Sheet πρώτα.")
