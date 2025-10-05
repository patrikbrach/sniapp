import streamlit as st
import pandas as pd

st.set_page_config(page_title="SNI → Licensanalys v1.2", layout="wide")
st.title("SNI → Licensanalys v1.2")

st.markdown(
    "Ladda upp din Excel/CSV-fil med kolumnerna **Account ID, Account Name, Primary SNI Code, "
    "Primary SNI Description, Secondary SNI Code, Secondary SNI Description, Product Name**."
)

uploaded = st.file_uploader("Välj fil (.xlsx eller .csv)", type=["xlsx", "csv"])

# --- Helpers ---
def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace("_", " ")
        .str.title()
    )
    return df

REQUIRED = [
    "Account Id",
    "Account Name",
    "Primary Sni Code",
    "Primary Sni Description",
    "Product Name",
]

def load_df(file):
    if file is None:
        return None, "Ingen fil uppladdad."
    try:
        if file.name.lower().endswith(".xlsx"):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file)
        df = norm_cols(df)
        missing = [c for c in REQUIRED if c not in df.columns]
        if missing:
            return None, f"Saknade kolumner: {', '.join(missing)}"
        return df, None
    except Exception as e:
        return None, f"Kunde inte läsa filen: {e}"

if uploaded is None:
    st.info("⚠️ Ladda upp en fil för att börja.")
    st.stop()

df, err = load_df(uploaded)
if err:
    st.error(err)
    st.stop()

# Rensa/standardisera
df["Primary Sni Description"] = df["Primary Sni Description"].astype(str).str.strip()
df["Product Name"] = df["Product Name"].astype(str).str.strip()
df["Account Id"] = df["Account Id"].astype(str).str.strip()
if "Secondary Sni Description" in df.columns:
    df["Secondary Sni Description"] = df["Secondary Sni Description"].astype(str).str.strip()

# --- TOP SNI JUST NU (visas först efter uppladdning) ---
st.header("TOP SNI JUST NU")

mode = st.radio(
    "Räkna som:",
    ["Antal rader (alla förekomster)", "Antal unika konton"],
    horizontal=True,
)

top_n = st.number_input("Top N", min_value=1, max_value=50, value=10, step=1)

req_cols = {"Primary Sni Code", "Primary Sni Description", "Account Id"}
if not req_cols.issubset(df.columns):
    miss = ", ".join(sorted(req_cols - set(df.columns)))
    st.warning(f"Saknar kolumner: {miss}")
else:
    grp = df.groupby(["Primary Sni Code", "Primary Sni Description"], dropna=False)

    if mode == "Antal unika konton":
        counts = grp["Account Id"].nunique().reset_index(name="Antal konton")
        sort_col = "Antal konton"
    else:
        counts = grp.size().reset_index(name="Antal rader")
        sort_col = "Antal rader"

    top = counts.sort_values(sort_col, ascending=False).head(top_n)

    st.dataframe(top, use_container_width=True)
    
# (Graf borttagen – endast tabell visas)

st.divider()  # visuellt avskiljare innan resten av appen


# Välj SNI-description
unique_sni_desc = df["Primary Sni Description"].dropna().unique()
unique_sni_desc = sorted([s for s in unique_sni_desc if s and s != "nan"])

col_select, col_topn = st.columns([3,1])
with col_select:
    sni_choice = st.selectbox("Välj Primary SNI Description", unique_sni_desc)
with col_topn:
    top_n = st.number_input("Antal topp-produkter", min_value=1, max_value=10, value=2, step=1)

if not sni_choice:
    st.stop()

# Filter för vald SNI
df_sni = df[df["Primary Sni Description"] == sni_choice].copy()

# Antal kunder (unika konton) med vald SNI
unique_accounts = df_sni["Account Id"].nunique()

# Topp-produkter (unika konton per produkt)
prod_counts_all = (
    df_sni.groupby("Product Name")["Account Id"].nunique()
    .sort_values(ascending=False)
    .rename("Antal konton")
    .reset_index()
)
if prod_counts_all.empty:
    st.warning("Inga produkter hittades för vald SNI.")
    st.stop()

prod_counts_all["Andel av kunder (%)"] = (
    prod_counts_all["Antal konton"] / unique_accounts * 100
).round(2)
top_products = prod_counts_all.head(top_n)["Product Name"].tolist()

# Konton som saknar ALLA topp N-produkter
accounts_with_top = (
    df_sni[df_sni["Product Name"].isin(top_products)]["Account Id"].drop_duplicates()
)
accounts_without_any_top = unique_accounts - accounts_with_top.nunique()
share_without_any_top = (
    round(accounts_without_any_top / unique_accounts * 100, 2) if unique_accounts > 0 else 0.0
)

# ---- UI: Huvudsammanfattning ----
st.subheader("Sammanfattning")
m1, m2, m3 = st.columns(3)
m1.metric("Antal kunder med vald SNI", f"{unique_accounts:,}".replace(",", " "))
m2.metric("Topp-produkter (antal)", f"{top_n}")
m3.metric("Andel som saknar **alla** topp-produkter", f"{share_without_any_top}%")
st.caption("“Saknar topp-produkter” = kunder inom vald SNI som saknar samtliga av de valda topp-produkterna.")

st.subheader("Vanligaste produkterna")
st.dataframe(prod_counts_all.head(top_n), use_container_width=True)

with st.expander("Visa alla produkter för vald SNI"):
    st.dataframe(prod_counts_all, use_container_width=True)

# ---- v1.2: Analys av de som saknar topprodukterna ----
st.markdown("---")
st.header("v1.2: Vad har de som saknar topprodukterna i stället?")

all_accounts_df = df_sni[["Account Id", "Account Name"]].drop_duplicates()
missing_accounts_df = all_accounts_df[~all_accounts_df["Account Id"].isin(accounts_with_top)].copy()
missing_n = missing_accounts_df["Account Id"].nunique()

if missing_n == 0:
    st.info("Alla kunder har minst en av topp-produkterna – ingen 'saknar'-grupp att analysera.")
else:
    df_missing = df_sni[df_sni["Account Id"].isin(missing_accounts_df["Account Id"])].copy()

    # 1) Alternativ-produkter för 'saknar' (unika konton per produkt)
    alt_counts = (
        df_missing.groupby("Product Name")["Account Id"].nunique()
        .sort_values(ascending=False)
        .rename("Antal konton (saknar-top)")
        .reset_index()
    )
    alt_counts["Andel av 'saknar'-kunder (%)"] = (
        alt_counts["Antal konton (saknar-top)"] / missing_n * 100
    ).round(2)

    # 2) Jämförelse mot hela SNI + lift
    base_share = prod_counts_all.set_index("Product Name")["Andel av kunder (%)"]
    alt_counts = alt_counts.set_index("Product Name")
    alt_counts["Andel i hela SNI (%)"] = base_share.reindex(alt_counts.index).fillna(0)
    alt_counts["Lift (saknar / total)"] = (
        alt_counts["Andel av 'saknar'-kunder (%)"] /
        alt_counts["Andel i hela SNI (%)"].replace(0, pd.NA)
    )
    alt_counts = alt_counts.reset_index()

    # 3) Antal produkter per konto i 'saknar'-segmentet
    prod_per_account = (
        df_missing.groupby("Account Id")["Product Name"].nunique()
        .rename("Antal produkter per konto")
    )
    # Nyckeltal
    st.subheader("Sammanfattning för 'saknar'-segmentet")
    n1, n2 = st.columns(2)
    with n1:
        st.metric("Antal kunder som saknar topprodukter", f"{missing_n:,}".replace(",", " "))
    with n2:
        st.metric("Snitt # produkter per 'saknar'-konto", f"{prod_per_account.mean():.2f}")

    # Tabeller
    st.subheader("Vanligaste produkter bland de som saknar topprodukterna")
    st.dataframe(alt_counts.head(10), use_container_width=True)

    with st.expander("Visa alla alternativ-produkter (saknar-segmentet) + jämförelse"):
        st.dataframe(alt_counts, use_container_width=True)

    with st.expander("Fördelning: antal produkter per 'saknar'-konto"):
        dist = prod_per_account.value_counts().sort_index().reset_index()
        dist.columns = ["Antal produkter", "Antal konton"]
        st.dataframe(dist, use_container_width=True)

    # Export-knappar
    st.subheader("Export")
    alt_csv = alt_counts.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Ladda ner: Alternativ-produkter (CSV)", alt_csv, file_name="alternativ_produkter_saknar.csv")

    miss_csv = missing_accounts_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Ladda ner: Konton som saknar topprodukter (CSV)", miss_csv, file_name="konton_saknar_top.csv")
