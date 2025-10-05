# SNI → Licensanalys v1.2 — Deploy

Den här appen är en Streamlit-app som tar emot en Excel/CSV, gör analys och låter användaren ladda ner resultat.

## Struktur i repo
- `sni_licenser_app_v12.py` (din app)
- `requirements.txt`
- `Procfile` (för Railway/Render)
- `Dockerfile` (för Cloud Run/Fly.io m.fl.)

## 1) Streamlit Community Cloud (snabbast)
1. Lägg filerna i ett GitHub‑repo.
2. Gå till streamlit.io → Sign in → Deploy an app → koppla till ditt repo.
3. Entrypoint: `sni_licenser_app_v12.py`.
4. Dela länken med kollegor (kan begränsas till inloggade GitHub‑konton).

## 2) Hugging Face Spaces
1. Skapa en Space (gradio/streamlit → **Streamlit**).
2. Ladda upp filerna (`sni_licenser_app_v12.py`, `requirements.txt`).
3. Sätt Space som *Private* och ge kollegor access.

## 3) Google Cloud Run (EU‑region)
```bash
gcloud builds submit --tag gcr.io/PROJECT/app-sni
gcloud run deploy app-sni --image gcr.io/PROJECT/app-sni --region=europe-north1 --platform=managed --allow-unauthenticated
```

## Enkel lösenordsspärr (frivillig)
Lägg överst i `sni_licenser_app_v12.py` (innan något skrivs till sidan):

```python
import streamlit as st, os
st.session_state["_auth"] = st.session_state.get("_auth", False)
PASS = os.getenv("APP_PASSWORD", "")
if PASS:
    if not st.session_state["_auth"]:
        pwd = st.text_input("Lösenord", type="password")
        if st.button("Logga in"):
            st.session_state["_auth"] = (pwd == PASS)
        st.stop() if not st.session_state["_auth"] else None
```

Sätt sedan en hemlighet/ENV `APP_PASSWORD` i respektive plattform.

## Krav på uppladdad fil
Kolumner: **Account ID, Account Name, Primary SNI Code, Primary SNI Description, Secondary SNI Code (valfri), Secondary SNI Description (valfri), Product Name**.

## Tips
- Låg trafik → Streamlit Cloud/HF Spaces räcker ofta (gratis el. låg kostnad).
- För GDPR/EU: välj EU‑region (t.ex. `europe-north1` i Cloud Run).
- `openpyxl` krävs för `.xlsx`.