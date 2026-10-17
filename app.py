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

  # --- 4 OSTATNIE LOSOWANIA Z PODŚWIETLENIEM POWTÓREK ---
  st.markdown("---")
  st.markdown("### 📌 4 Ostatnie Losowania i Powtórki")

  recent_draws = []
  all_4_numbers = []

  for idx, row in df_reversed.head(4).iterrows():
    d_str, t_str, nums = parse_row(row)
    if nums:
      num_draw = len(df_reversed) - idx
      recent_draws.append(
          {"num": num_draw, "date": d_str, "time": t_str, "numbers": nums}
      )
      all_4_numbers.extend(nums)

  # Liczymy powtórki w ostatnich 4 losowaniach
  counts_4 = Counter(all_4_numbers)
  repeats = {num: cnt for num, cnt in counts_4.items() if cnt > 1}

  # Wyświetlamy 4 ostatnie losowania
  for draw in recent_draws:
    header = f"**Losowanie #{draw['num']}**"
    if draw["date"]:
      header += f" | 📅 {draw['date']}"
    if draw["time"]:
      header += f" | ⏱️ {draw['time']}"

    st.markdown(header)

    # Formatujemy liczby - dodajemy oznaczenie 🔥 dla liczb, które się powtórzyły
    formatted_nums = []
    for n in draw["numbers"]:
      if n in repeats:
        formatted_nums.append(f"🔥{n}")
      else:
        formatted_nums.append(n)

    mid = len(formatted_nums) // 2
    st.code(" ".join(formatted_nums[:mid]) + "\n" + " ".join(formatted_nums[mid:]))

  # Podsumowanie powtórzonych liczb
  if repeats:
    st.info("🔥 **Liczby powtórzone w ostatnich 4 losowaniach:**\n\n" + ", ".join(
        [f"**{num}** ({cnt}x)" for num, cnt in sorted(repeats.items(), key=lambda x: (-x[1], x[0]))]
    ))

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
        st.write(f"• **{num:02d}** (trak: {count})")
    else:
      st.info("Brak danych")

  with col2:
    st.markdown(f"🔵 **Top 10 Parzyste ({sesja})**")
    if top_even:
      for num, count in top_even:
        st.write(f"• **{num:02d}** (trak: {count})")
    else:
      st.info("Brak danych")

  # --- REKOMENDOWANE ZESTAWY (1 DO 10 LICZB) ---
  st.markdown("---")
  st.markdown("### 💡 Rekomendowane Zestawy AI")

  ile_liczb = st.slider(
      "🎯 Wybierz ile liczb ma liczyć zestaw:",
      min_value=1,
      max_value=10,
      value=5,
  )

  if counter_all:
    top_overall = [
        f"{num:02d}" for num, _ in counter_all.most_common(ile_liczb)
    ]

    half = ile_liczb // 2
    rem = ile_liczb - half
    bal_odd = [f"{num:02d}" for num, _ in Counter(odd_nums).most_common(rem)]
    bal_even = [f"{num:02d}" for num, _ in Counter(even_nums).most_common(half)]
    balanced_set = sorted(
        bal_odd + bal_even, key=lambda x: int(x) if x.isdigit() else 0
    )

    col_z1, col_z2 = st.columns(2)
    with col_z1:
      st.success(f"🔥 **Zestaw Gorący ({ile_liczb} liczb):**")
      st.code(" ".join(top_overall))

    with col_z2:
      st.info(f"⚖️ **Zestaw Zbalansowany ({ile_liczb} liczb):**")
      st.code(" ".join(balanced_set))

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
