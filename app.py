import os
from collections import Counter
from itertools import combinations
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

  # Pobranie wyników ostatniego losowania do sprawdzania trafień w Top 10
  _, _, last_draw_nums = parse_row(df_reversed.iloc[0])
  last_draw_set = set(last_draw_nums)

  # --- OSTATNIE LOSOWANIA Z PRZESKOKAMI ---
  st.markdown("### 📌 4 Ostatnie Losowania (Przeskoki)")
  st.caption("Liczby oznaczone 🔄 powtórzyły się z poprzedniego losowania.")

  for i in range(4):
    if i >= len(df_reversed):
      break
    row = df_reversed.iloc[i]
    d_str, t_str, nums = parse_row(row)
    num_draw = len(df) - i

    prev_nums_set = set()
    if i + 1 < len(df_reversed):
      _, _, prev_nums = parse_row(df_reversed.iloc[i + 1])
      prev_nums_set = set(prev_nums)

    info_line = f"**Losowanie #{num_draw}**"
    if d_str:
      info_line += f" | 📅 {d_str}"
    if t_str:
      info_line += f" | ⏰ {t_str}"

    st.markdown(info_line)
    if nums:
      formatted_nums = [
          f"🔄{n}" if n in prev_nums_set else n for n in nums
      ]
      mid = len(formatted_nums) // 2
      line1 = " ".join(formatted_nums[:mid])
      line2 = " ".join(formatted_nums[mid:])
      st.code(f"{line1}\n{line2}")

  st.markdown("---")

  # --- SUWAK ZAKRESU ANALIZY ---
  st.markdown("### ⚙️ Ustawienia Analizy Statystycznej")
  limit_option = st.select_slider(
      "Wybierz zakres analizowanych ostatnich losowań:",
      options=[5, 10, 20, 50, 100, "Wszystkie"],
      value=20,
  )

  if limit_option == "Wszystkie":
    df_analyzed = df
  else:
    df_analyzed = df.tail(int(limit_option))

  # --- ANALIZA: TOP 10 PARZYSTE / NIEPARZYSTE (14:00 vs 22:00) ---
  st.markdown(f"### ⏰ Top 10 Sesyjne (Zakres: {limit_option} losowań)")
  st.caption("Liczby trafione w najnowszym losowaniu oznaczono ikoną ✅")

  numbers_14 = []
  numbers_22 = []

  for _, row in df_analyzed.iterrows():
    _, t_str, nums = parse_row(row)
    if t_str.startswith("14"):
      numbers_14.extend(nums)
    elif t_str.startswith("22"):
      numbers_22.extend(nums)


  def get_top_even_odd_highlighted(nums_list):
    counter = Counter(nums_list)
    sorted_nums = [item[0] for item in counter.most_common()]
    even = [n for n in sorted_nums if int(n) % 2 == 0][:10]
    odd = [n for n in sorted_nums if int(n) % 2 != 0][:10]

    even_fmt = [f"{n}✅" if n in last_draw_set else n for n in even]
    odd_fmt = [f"{n}✅" if n in last_draw_set else n for n in odd]
    return even_fmt, odd_fmt


  even_14, odd_14 = get_top_even_odd_highlighted(numbers_14)
  even_22, odd_22 = get_top_even_odd_highlighted(numbers_22)

  col1, col2 = st.columns(2)

  with col1:
    st.markdown("#### ☀️ Godzina 14:00")
    st.markdown("**Top 10 Parzyste:**")
    st.code(" ".join(even_14))
    st.markdown("**Top 10 Nieparzyste:**")
    st.code(" ".join(odd_14))

  with col2:
    st.markdown("#### 🌙 Godzina 22:00")
    st.markdown("**Top 10 Parzyste:**")
    st.code(" ".join(even_22))
    st.markdown("**Top 10 Nieparzyste:**")
    st.code(" ".join(odd_22))

  st.markdown("---")

  # --- CZTERY REKOMENDOWANE ZAKŁADY (Z INDYWIDUALNYMI SUWAKAMI) ---
  st.markdown("### 🎲 4 Rekomendowane Zestawy Zakładów")

  all_analyzed_numbers = []
  pair_counter = Counter()

  for _, row in df_analyzed.iterrows():
    _, _, nums = parse_row(row)
    all_analyzed_numbers.extend(nums)
    for p in combinations(sorted(nums), 2):
      pair_counter[p] += 1

  counter_all = Counter(all_analyzed_numbers)
  most_common = [num for num, _ in counter_all.most_common()]
  least_common = [num for num, _ in counter_all.most_common()[::-1]]

  # Zestaw 1: Najczęstsze
  st.markdown("#### 🟢 Zestaw 1: Najczęstsze Liczby")
  n1 = st.slider("Liczba skreśleń w Zestawie 1:", 1, 10, 6, key="s1")
  zestaw1 = sorted(most_common[:n1])
  st.code(" ".join(zestaw1))

  # Zestaw 2: Najrzadsze / Głodne
  st.markdown("#### 🔵 Zestaw 2: Najrzadsze / 'Głodne' Liczby")
  n2 = st.slider("Liczba skreśleń w Zestawie 2:", 1, 10, 6, key="s2")
  zestaw2 = sorted(least_common[:n2])
  st.code(" ".join(zestaw2))

  # Zestaw 3: Dominujące Parzyste
  st.markdown("#### 🟣 Zestaw 3: Dominujące Parzyste")
  n3 = st.slider("Liczba skreśleń w Zestawie 3:", 1, 10, 6, key="s3")
  parzyste_all = sorted([n for n in most_common if int(n) % 2 == 0][:n3])
  st.code(" ".join(parzyste_all))


  # Zestaw 4: Synergia / Najczęściej razem
  def generate_synergy_set(n):
    if not most_common:
      return []
    best_start = most_common[0]
    selected = [best_start]

    while len(selected) < n:
      candidate_scores = Counter()
      for num in most_common[:40]:
        if num in selected:
          continue
        score = sum(pair_counter[tuple(sorted([num, s]))] for s in selected)
        candidate_scores[num] = score

      if not candidate_scores:
        remaining = [n_item for n_item in most_common if n_item not in selected]
        if remaining:
          selected.append(remaining[0])
        else:
          break
      else:
        best_candidate = candidate_scores.most_common(1)[0][0]
        selected.append(best_candidate)
    return sorted(selected)


  st.markdown("#### 🟡 Zestaw 4: Synergia (Najczęściej razem)")
  n4 = st.slider("Liczba skreśleń w Zestawie 4:", 1, 10, 6, key="s4")
  zestaw4 = generate_synergy_set(n4)
  st.code(" ".join(zestaw4))

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
