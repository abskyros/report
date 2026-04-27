# 🔐 Οδηγίες για Streamlit Secrets

## Τι είναι τα Secrets;
Αντί να γράφεις τα passwords κάθε φορά στην εφαρμογή,
τα αποθηκεύεις μια φορά στο Streamlit Cloud και φορτώνουν αυτόματα.

---

## Βήμα-βήμα οδηγίες:

### 1. Πήγαινε στο Streamlit Cloud
→ https://share.streamlit.io/

### 2. Βρες την εφαρμογή σου (report)
Κλίκ στα **3 τελείες (⋮)** δίπλα στο app σου

### 3. Κλίκ "Settings"

### 4. Κλίκ "Secrets" (αριστερό menu)

### 5. Επικόλλησε αυτό (με τα ΠΡΑΓΜΑΤΙΚΑ passwords):

```toml
SALES_EMAIL_PASS = "abcd efgh ijkl mnop"
EMAIL_PASS = "xxxx xxxx xxxx xxxx"
```

### 6. Κλίκ "Save"

Η εφαρμογή θα κάνει restart αυτόματα!

---

## Πώς να φτιάξεις App Password στο Gmail:

### Για ftoulisgm@gmail.com (Πωλήσεις):
1. Πήγαινε: https://myaccount.google.com/apppasswords
2. Συνδέσου με ftoulisgm@gmail.com
3. "Select app" → **Mail**
4. "Select device" → **Other** → γράψε "Streamlit"
5. Κλίκ **Generate**
6. Αντιγράψε το 16-ψήφιο password (μορφή: "abcd efgh ijkl mnop")
7. Βάλε το ως `SALES_EMAIL_PASS` στα Secrets

### Για abf.skyros@gmail.com (Τιμολόγια):
1. Ίδια διαδικασία με το abf.skyros@gmail.com
2. Βάλε το ως `EMAIL_PASS` στα Secrets

---

## Σημείωση:
- Τα App Passwords λειτουργούν μόνο αν έχεις ενεργοποιήσει **2-Step Verification**
- Κάθε App Password είναι 16 χαρακτήρες (με κενά: "xxxx xxxx xxxx xxxx")
- ΠΟΤΕ μην ανεβάζεις τα πραγματικά passwords στο GitHub!

