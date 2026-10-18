import os
import pandas as pd
import streamlit as st
from collections import Counter

st.set_page_config(page_title="Multi Multi AI System", page_icon="🎯", layout="centered")

st.title("🎯 Multi Multi AI System")
st.subheader("Mobilny Panel Analityczny Ekipy")

FILE_NAME = "multi_multi (10).csv"

def parse_row(row):
    try:
        d_str = str(row[1]).strip() if len(row) > 1 else ""
        t_str = str(row[2]).strip() if len(row) > 2 else ""
        nums = [f"{int(x):02d}" for x in row[3:] if pd.notna(x) and str(x).strip().isdigit()]
        return d_str, t_str, nums
    except Exception:
        return "", "", []

@st.cache_data(ttl=300)
def load_data():
    if os.path.exists(FILE_NAME):
        df = pd.read_csv(FILE_NAME, header=None)
        return df
    else:
        return None

df = load_data()

if df is not None and not df.empty:
    df_reversed = df.iloc[::-1].reset_index(drop=True)

    # --- OSTATNIE LOSOWANIA ---
    st.markdown("### 📌 4 Ostatnie Losowania (Przeskoki)")
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

    st.markdown("---")

    # --- ANALIZA ZESTAWÓW I SUWAKI ---
    st.markdown("### 🎲 Generator Rekomendowanych Zakładów")

    # Zbieranie statystyk ze wszystkich losowań
    all_numbers = []
    for _, row in df.iterrows():
        _, _, nums = parse_row(row)
        all_numbers.extend(nums)

    counter_all = Counter(all_numbers)
    most_common = [num for num, _ in counter_all.most_common()]
    least_common = [num for num, _ in counter_all.most_common()[::-1]]

    # Suwak rekomendowanych zakładów
    n_skreslen = st.slider("Wybierz liczbę skreśleń w zakładasz (1-10):", min_value=1, max_value=10, value=6)

    st.markdown(f"#### 🟢 Zestaw 1: Najczęściej Losowane Liczby ({n_skreslen} skreśleń)")
    zestaw1 = most_common[:n_skreslen]
    st.code(" ".join(sorted(zestaw1)))

    st.markdown(f"#### 🔵 Zestaw 2: Najrzadziej Losowane / Najbardziej 'Głodne' Liczby ({n_skreslen} skreśleń)")
    zestaw2 = least_common[:n_skreslen]
    st.code(" ".join(sorted(zestaw2)))

    # Zestaw Parzyste / Nieparzyste
    n_parity = st.slider("Liczba skreśleń w Zestawie Synergii / Mieszanym:", min_value=1, max_value=10, value=5)
    
    parzyste = [n for n in most_common if int(n) % 2 == 0][:n_parity]
    nieparzyste = [n for n in most_common if int(n) % 3 == 0][:n_parity]

    st.markdown(f"#### 🟣 Zestaw 3: Zbalansowany / Synergia")
    st.code(" ".join(sorted(parzyste)))

    st.markdown(f"#### 🟡 Zestaw 4: Alternatywne Wzorce")
    st.code(" ".join(sorted(nieparzyste)))

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
    st.error(f"Nie znaleziono pliku {FILE_NAME} w repozytorium.")
