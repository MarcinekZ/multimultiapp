import os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Multi Multi AI System", page_icon="🎯", layout="centered")

st.title("🎯 Multi Multi AI System")
st.subheader("Mobilny Panel Analityczny Ekipy")

FILE_NAME = "multi_multi (10).csv"

def parse_row(row):
    """Pomocnicza funkcja do parsowania wierszy losowań z pliku CSV."""
    try:
        # Zakładamy format: ID, Data, Godzina, Wyniki...
        d_str = str(row[1]).strip() if len(row) > 1 else ""
        t_str = str(row[2]).strip() if len(row) > 2 else ""
        # Pobieramy numery (od indeksu 3 do końca)
        nums = [f"{int(x):02d}" for x in row[3:] if pd.notna(x) and str(x).strip().isdigit()]
        return d_str, t_str, nums
    except Exception:
        return "", "", []

@st.cache_data(ttl=300)
def load_data():
    if os.path.exists(FILE_NAME):
        # Wczytujemy dane bezpośrednio z lokalnego pliku zaktualizowanego przez GitHub Actions
        df = pd.read_csv(FILE_NAME, header=None)
        return df
    else:
        return None

df = load_data()

if df is not None and not df.empty:
    st.success(f"Baza danych wczytana pomyślnie! Łączna liczba losowań: {len(df)}")
    
    # Odwracamy bazę, aby najnowsze losowania były na samej górze
    df_reversed = df.iloc[::-1].reset_index(drop=True)

    # --- OSTATNIE LOSOWANIA ---
    st.markdown("### 📌 Ostatnie Losowania (Przeskoki)")
    
    for idx, row in df_reversed.head(4).iterrows():
        d_str, t_str, nums = parse_row(row)
        num_draw = len(df) - idx
        
        info_line = f"**Losowanie #{num_draw}**"
        if d_str:
            info_line += f" | 📅 {d_str}"
        if t_str:
            info_line += f" | ⏰ {t_str}"
            
        st.markdown(info_line)
        if nums:
            mid = len(nums) // 2
            line1 = " ".join([f"🔄{n}" if i < 2 else n for i, n in enumerate(nums[:mid])])
            line2 = " ".join(nums[mid:])
            st.code(f"{line1}\n{line2}")

    # --- ARCHIWUM ---
    st.markdown("---")
    with st.expander("📂 Archiwum: Przeglądaj wszystkie wyniki"):
        st.markdown("### Baza wyników (od najnowszych)")
        for idx, row in df_reversed.head(50).iterrows():
            d_str, t_str, nums = parse_row(row)
            if nums:
                num_draw = len(df) - idx
                info_line = f"**Losowanie #{num_draw}**"
                if d_str:
                    info_line += f" | 📅 {d_str}"
                if t_str:
                    info_line += f" | ⏰ {t_str}"
                st.markdown(info_line)
                st.code(" ".join(nums))

else:
    st.error(
        f"Nie znaleziono pliku CSV z bazą danych ({FILE_NAME}) w repozytorium. "
        "Upewnij się, że plik z wynikami znajduje się w głównym folderze."
    )
