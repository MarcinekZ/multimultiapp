import os
from collections import Counter
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Multi Multi AI System", page_icon="🎯", layout="centered"
)

st.title("🎯 Multi Multi AI System")
st.subheader("Mobilny Panel Analityczny Ekipy")

FILE_NAME = "multi_multi (10).csv"


def parse_row(row):
  try:
    d_str = str(row[1]).strip() if len(row) > 1 else ""
    t_str = str(row[2]).strip() if len(row) > 2 else ""
    nums = [
        f"{int(x):02d}"
        for x in row[3:]
        if pd.notna(x) and str(x).strip().isdigit()
    ]
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
      line1 = " ".join(
          [f"🔄{n}" if i < 2 else n for i, n in enumerate(nums[:mid])]
      )
      line2 = " ".join(nums[mid:])
      st.code(f"{line1}\n{line2}")

  st.markdown("---")

  # --- ANALIZA: TOP 10 PARZYSTE / NIEPARZYSTE (14:00 vs 22:00) ---
  st.markdown("### ⏰ Analiza Sesyjna: 14:00 vs 22:00")

  numbers_14 = []
  numbers_22 = []

  for _, row in df.iterrows():
    _, t_str, nums = parse_row(row)
    if t_str.startswith("14"):
      numbers_14.extend(nums)
    elif t_str.startswith("22"):
      numbers_22.extend(nums)


  def get_top_even_odd(nums_list):
    counter = Counter(nums_list)
    sorted_nums = [item[0] for item in counter.most_common()]
    even = [n for n in sorted_nums if int(n) % 2 == 0][:10]
    odd = [n for n in sorted_nums if int(n) % 2 != 0][:10]
    return even, odd


  even_14, odd_14 = get_top_even_odd(numbers_14)
  even_22, odd_22 = get_top_even_odd(numbers_22)

  col1, col2 = st.columns(2)

  with col1:
    st.markdown("#### ☀️ Sesja 14:00")
    st.markdown("**Top 10 Parzyste:**")
    st.code(" ".join(even_14))
    st.markdown("**Top 10 Nieparzyste:**")
    st.code(" ".join(odd_14))

  with col2:
    st.markdown("#### 🌙 Sesja 22:00")
    st.markdown("**Top 10 Parzyste:**")
    st.code(" ".join(even_22))
    st.markdown("**Top 10 Nieparzyste:**")
    st.code(" ".join(odd_22))

  st.markdown("---")

  # --- GENERATOR REKOMENDOWANYCH ZAKŁADÓW ---
  st.markdown("### 🎲 Generator Rekomendowanych Zakładów")

  all_numbers = []
  for _, row in df.iterrows():
    _, _, nums = parse_row(row)
    all_numbers.extend(nums)

  counter_all = Counter(all_numbers)
  most_common = [num for num, _ in counter_all.most_common()]
  least_common = [num for num, _ in counter_all.most_common()[::-1]]

  n_skreslen = st.slider(
      "Wybierz liczbę skreśleń w zakładach (1-10):",
      min_value=1,
      max_value=10,
      value=6,
  )

  st.markdown(
      f"#### 🟢 Zestaw 1: Najczęściej Losowane Liczby ({n_skreslen} skreśleń)"
  )
  zestaw1 = most_common[:n_skreslen]
  st.code(" ".join(sorted(zestaw1)))

  st.markdown(
      f"#### 🔵 Zestaw 2: Najrzadziej Losowane / Głodne Liczby ({n_skreslen}"
      " skreśleń)"
  )
  zestaw2 = least_common[:n_skreslen]
  st.code(" ".join(sorted(zestaw2)))

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
