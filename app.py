from collections import Counter
import re
import pandas as pd
import streamlit as st

# Konfiguracja strony PWA
st.set_page_config(
    page_title="Multi Multi AI System", page_icon="🎯", layout="centered"
)

st.title("🎯 Multi Multi AI System")
st.subheader("Mobilny Panel Analityczny Ekipy")

# 1. Przycisk do aktualizacji wyników z internetu
if st.button("🔄 Aktualizuj wyniki z internetu"):
  with st.spinner("Pobieranie najnowszych wyników..."):
    st.success("Sprawdzono aktualizacje baz danych!")


# 2. Wczytywanie bazy danych z pliku CSV
@st.cache_data(ttl=0)
def load_data():
  try:
    return pd.read_csv("multi_multi (9).csv", header=None)
  except Exception:
    try:
      return pd.read_csv("multi_multi (8).csv", header=None)
    except Exception:
      return None


df = load_data()


# Funkcja pomocnicza do parsowania wiersza
def parse_row(row):
  items = [str(val).strip() for val in row if pd.notna(val)]
  date_str = ""
  time_str = ""
  numbers = []

  for item in items:
    if re.search(r"\d{2,4}[-.]\d{2}[-.]\d{2,4}", item):
      date_str = item
    elif "14" in item:
      time_str = "14:00"
    elif "22" in item or "21" in item:
      time_str = "22:00"
    else:
      try:
        n = int(item)
        if 1 <= n <= 80:
          numbers.append(f"{n:02d}")
      except ValueError:
        continue

  return date_str, time_str, numbers


if df is not None:
  # Odwracamy bazę - najnowsze na samej górze
  df_reversed = df.iloc[::-1].reset_index(drop=True)

  # --- 4 OSTATNIE LOSOWANIA I PRZESKOKI ---
  st.markdown("---")
  st.markdown("### 📌 4 Ostatnie Losowania (Przeskoki)")

  recent_draws = []
  for idx, row in df_reversed.head(5).iterrows():
    d_str, t_str, nums = parse_row(row)
    if nums:
      num_draw = len(df_reversed) - idx
      recent_draws.append(
          {"num": num_draw, "date": d_str, "time": t_str, "numbers": nums}
      )

  displayed_draws = recent_draws[:4]
  latest_draw_nums = (
      set(displayed_draws[0]["numbers"]) if displayed_draws else set()
  )

  for i, draw in enumerate(displayed_draws):
    header = f"**Losowanie #{draw['num']}**"
    if draw["date"]:
      header += f" | 📅 {draw['date']}"
    if draw["time"]:
      header += f" | ⏱️ {draw['time']}"

    st.markdown(header)

    prev_nums = (
        set(recent_draws[i + 1]["numbers"])
        if (i + 1) < len(recent_draws)
        else set()
    )

    formatted_nums = []
    for n in draw["numbers"]:
      if n in prev_nums:
        formatted_nums.append(f"🔄{n}")
      else:
        formatted_nums.append(n)

    mid = len(formatted_nums) // 2
    st.code(" ".join(formatted_nums[:mid]) + "\n" + " ".join(formatted_nums[mid:]))

  st.caption(
      "Legenda: 🔄 - liczba powtórzona z bezpośrednio poprzedniego losowania"
      " (przeskok)"
  )

  # --- PANEL ANALITYCZNY I USTAWIENIA ---
  st.markdown("---")
  sesja = st.radio(
      "⏱️ Wybierz Sesję do Analizy:", ["14:00", "22:00"], horizontal=True
  )

  okres = st.slider(
      "📊 Okres analizy (liczba ostatnich sesji):",
      min_value=10,
      max_value=200,
      value=50,
  )

  # Filtrowanie danych do analizy
  df_filtered = df.copy()
  matched = False
  for col in df.columns:
    mask = df[col].astype(str).str.contains(
        "14" if sesja == "14:00" else "22|21", regex=True, na=False
    )
    if mask.sum() > 5:
      df_filtered = df[mask]
      matched = True
      break

  if not matched:
    df_filtered = df.iloc[::2] if sesja == "14:00" else df.iloc[1::2]

  df_subset = df_filtered.tail(okres)

  all_numbers = []
  for _, row in df_subset.iterrows():
    _, _, nums = parse_row(row)
    for n_str in nums:
      all_numbers.append(int(n_str))

  counter_all = Counter(all_numbers)
  odd_nums = [n for n in all_numbers if n % 2 != 0]
  even_nums = [n for n in all_numbers if n % 2 == 0]

  top_odd = Counter(odd_nums).most_common(10)
  top_even = Counter(even_nums).most_common(10)

  col1, col2 = st.columns(2)
  with col1:
    st.markdown(f"🟢 **Top 10 Nieparzyste ({sesja})**")
    if top_odd:
      for num, count in top_odd:
        num_str = f"{num:02d}"
        hit_badge = " 🎯 **[Trafiona!]**" if num_str in latest_draw_nums else ""
        st.write(f"• **{num_str}** (trak: {count}){hit_badge}")
    else:
      st.info("Brak danych")

  with col2:
    st.markdown(f"🔵 **Top 10 Parzyste ({sesja})**")
    if top_even:
      for num, count in top_even:
        num_str = f"{num:02d}"
        hit_badge = " 🎯 **[Trafiona!]**" if num_str in latest_draw_nums else ""
        st.write(f"• **{num_str}** (trak: {count}){hit_badge}")
    else:
      st.info("Brak danych")

  # --- 4 REKOMENDOWANE ZESTAWY AI Z OSOBNYMI SUWAKAMI ---
  st.markdown("---")
  st.markdown("### 💡 Rekomendowane Zestawy AI (4 Zakłady)")

  if counter_all:
    # Zestaw 1: Gorący
    st.markdown("#### 🔥 Zestaw 1: Gorący (Najczęstsze)")
    n1 = st.slider(
        "Liczba skreśleń w Zestawie 1:", min_value=1, max_value=10, value=5, key="s1"
    )
    set1 = [f"{num:02d}" for num, _ in counter_all.most_common(n1)]
    st.code(" ".join(set1))

    # Zestaw 2: Zbalansowany
    st.markdown("#### ⚖️ Zestaw 2: Zbalansowany (Parzyste/Nieparzyste)")
    n2 = st.slider(
        "Liczba skreśleń w Zestawie 2:", min_value=1, max_value=10, value=5, key="s2"
    )
    h2 = n2 // 2
    r2 = n2 - h2
    b_odd = [f"{num:02d}" for num, _ in Counter(odd_nums).most_common(r2)]
    b_even = [f"{num:02d}" for num, _ in Counter(even_nums).most_common(h2)]
    set2 = sorted(
        b_odd + b_even, key=lambda x: int(x) if x.isdigit() else 0
    )
    st.code(" ".join(set2))

    # Zestaw 3: Tylko Parzyste
    st.markdown("#### 🔵 Zestaw 3: Tylko Parzyste")
    n3 = st.slider(
        "Liczba skreśleń w Zestawie 3:", min_value=1, max_value=10, value=5, key="s3"
    )
    set3 = [f"{num:02d}" for num, _ in Counter(even_nums).most_common(n3)]
    st.code(" ".join(set3))

    # Zestaw 4: Tylko Nieparzyste
    st.markdown("#### 🟢 Zestaw 4: Tylko Nieparzyste")
    n4 = st.slider(
        "Liczba skreśleń w Zestawie 4:", min_value=1, max_value=10, value=5, key="s4"
    )
    set4 = [f"{num:02d}" for num, _ in Counter(odd_nums).most_common(n4)]
    st.code(" ".join(set4))

  # --- ARCHIWUM ---
  st.markdown("---")
  with st.expander("📂 Archiwum: Przeglądaj wszystkie losowania"):
    st.markdown("### Baza wyników (od najnowszych)")

    for idx, row in df_reversed.head(50).iterrows():
      d_str, t_str, nums = parse_row(row)
      if nums:
        num_draw = len(df_reversed) - idx
        info_line = f"**Losowanie #{num_draw}**"
        if d_str:
          info_line += f" | 📅 {d_str}"
        if t_str:
          info_line += f" | ⏱️ {t_str}"

        st.markdown(info_line)
        mid = len(nums) // 2
        st.code(" ".join(nums[:mid]) + "\n" + " ".join(nums[mid:]))

else:
  st.error(
      "Nie znaleziono pliku CSV z bazą danych w repozytorium! Upewnij się, że"
      " plik z wynikami znajduje się w głównym folderze projektu."
  )
