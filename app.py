from collections import Counter
from itertools import combinations
import re
import pandas as pd
import streamlit as st

# Konfiguracja strony PWA
st.set_page_config(
    page_title="Multi Multi AI System", page_icon="🎯", layout="centered"
)

st.title("🎯 Multi Multi AI System")
st.subheader("Mobilny Panel Analityczny Ekipy")

# 1. Wczytywanie bazy lokalnej CSV
@st.cache_data(ttl=0)
def load_local_data():
  try:
    return pd.read_csv("multi_multi (9).csv", header=None)
  except Exception:
    try:
      return pd.read_csv("multi_multi (8).csv", header=None)
    except Exception:
      return None


df_base = load_local_data()

# Zarządzaniestanem sesji (pamięć podręczna aplikacji w telefonie/przeglądarce)
if "live_df" not in st.session_state:
  st.session_state["live_df"] = df_base

# --- PANEL SZYBKIEJ AKTUALIZACJI Z TELEFONU ---
with st.expander("⚡ Dodaj najnowsze losowanie (Błyskawiczna aktualizacja)"):
  st.markdown(
      "Wpisz datę, godzinę oraz 20 wylosowanych liczb (oddzielonych spacjami)."
  )
  col_d, col_t = st.columns(2)
  with col_d:
    input_date = st.text_input("Data (np. 18.10.2026)", value="18.10.2026")
  with col_t:
    input_time = st.selectbox("Sesja", ["14:00", "22:00"])

  input_nums_str = st.text_area(
      "Wklej 20 liczb (np. 01 05 12 19 ... 80):",
      placeholder="01 05 12 18 22 25 31 35 40 44 48 52 55 60 63 68 71 75 78 80",
  )

  if st.button("🚀 Dodaj i przelicz system"):
    if input_nums_str:
      # Czyszczenie i wyciąganie liczb
      found_nums = [
          f"{int(n):02d}"
          for n in re.findall(r"\d+", input_nums_str)
          if 1 <= int(n) <= 80
      ]
      if len(found_nums) >= 1:
        new_row = [input_date, input_time] + found_nums[:20]
        # Tworzymy nowy wiersz jako DataFrame i doklejamy na początek
        new_df = pd.DataFrame([new_row])
        st.session_state["live_df"] = pd.concat(
            [st.session_state["live_df"], new_df], ignore_index=True
        )
        st.success(
            "✅ Pomyślnie dodano nowe losowanie! Analityka została"
            " zaktualizowana."
        )
        st.rerun()
      else:
        st.error(
            "⚠️ Podano za mało poprawnych liczb z zakresu 1-80. Wpisz liczby"
            " poprawnie."
        )

df = st.session_state["live_df"]

if df is not None:
  # Odwracamy bazę - najnowsze na samej górze
  df_reversed = df.iloc[::-1].reset_index(drop=True)

  # --- 4 OSTATNIE LOSOWANIA I PRZESKOKI ---
  st.markdown("---")
  st.markdown("### 📌 4 Ostatnie Losowania (Przeskoki)")

  recent_draws = []
  for idx, row in df_reversed.head(5).iterrows():
    # Funkcja pomocnicza do parsowania wiersza
    items = [str(val).strip() for val in row if pd.notna(val)]
    d_str, t_str, nums = "", "", []
    for item in items:
      if re.search(r"\d{2,4}[-.]\d{2}[-.]\d{2,4}", item):
        d_str = item
      elif "14" in item:
        t_str = "14:00"
      elif "22" in item or "21" in item:
        t_str = "22:00"
      else:
        try:
          n = int(item)
          if 1 <= n <= 80:
            nums.append(f"{n:02d}")
        except ValueError:
          continue

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

  # --- PANEL ANALITYCZNY I SUWAK ---
  st.markdown("---")
  sesja = st.radio(
      "⏱️ Wybierz Sesję do Analizy:", ["14:00", "22:00"], horizontal=True
  )

  okres = st.slider(
      "📊 Okres analizy (liczba ostatnich sesji):",
      min_value=5,
      max_value=500,
      value=50,
      step=5,
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

  # Parsor wierszy dla statystyk
  def parse_row_full(row):
    items = [str(val).strip() for val in row if pd.notna(val)]
    d_str, t_str, numbers = "", "", []
    for item in items:
      if re.search(r"\d{2,4}[-.]\d{2}[-.]\d{2,4}", item):
        d_str = item
      elif "14" in item:
        t_str = "14:00"
      elif "22" in item or "21" in item:
        t_str = "22:00"
      else:
        try:
          n = int(item)
          if 1 <= n <= 80:
            numbers.append(f"{n:02d}")
        except ValueError:
          continue
    return d_str, t_str, numbers

  all_numbers_temp = []
  for _, row in df_subset.iterrows():
    _, _, nums = parse_row_full(row)
    for n_str in nums:
      all_numbers_temp.append(int(n_str))

  odd_temp = [n for n in all_numbers_temp if n % 2 != 0]
  even_temp = [n for n in all_numbers_temp if n % 2 == 0]

  top_odd_set = {num for num, _ in Counter(odd_temp).most_common(10)}
  top_even_set = {num for num, _ in Counter(even_temp).most_common(10)}

  even_chart_data = []
  odd_chart_data = []
  table_details = []
  all_numbers = []
  pair_counter = Counter()

  for idx, row in df_subset.iterrows():
    d_str, t_str, nums = parse_row_full(row)
    if nums:
      int_nums = sorted([int(n) for n in nums])

      hits_even = sum(1 for n in int_nums if n in top_even_set)
      hits_odd = sum(1 for n in int_nums if n in top_odd_set)

      even_chart_data.append({"Trafienia Parzyste Top 10": hits_even})
      odd_chart_data.append({"Trafienia Nieparzyste Top 10": hits_odd})

      table_details.append({
          "Data": f"{d_str} {t_str}".strip(),
          "Trafione Parzyste Top 10": hits_even,
          "Trafione Nieparzyste Top 10": hits_odd,
      })

      for n_str in nums:
        all_numbers.append(int(n_str))
      for p in combinations(int_nums, 2):
        pair_counter[p] += 1

  if even_chart_data and odd_chart_data:
    st.markdown("---")
    st.markdown("📈 **Wykres 1: Skuteczność Top 10 Parzyste**")
    st.bar_chart(pd.DataFrame(even_chart_data))

    st.markdown("📈 **Wykres 2: Skuteczność Top 10 Nieparzyste**")
    st.bar_chart(pd.DataFrame(odd_chart_data))

    with st.expander(
        "📋 Zobacz dokładną ilość trafień w poszczególnych losowaniach"
    ):
      df_table = pd.DataFrame(table_details).iloc[::-1].reset_index(drop=True)
      st.dataframe(df_table, use_container_width=True, hide_index=True)

  counter_all = Counter(all_numbers)
  top_odd = Counter(odd_temp).most_common(10)
  top_even = Counter(even_temp).most_common(10)
  top_pairs = pair_counter.most_common(5)

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

  # --- ANALIZA WSPÓŁWYSTĘPOWANIA PAR ---
  st.markdown("---")
  st.markdown(f"🔗 **Top 5 Najczęstszych Par Liczb ({sesja})**")
  if top_pairs:
    for (n1, n2), cnt in top_pairs:
      st.write(f"• Para **{n1:02d}** i **{n2:02d}** (wspólnie w {cnt} losowaniach)")
  else:
    st.info("Brak danych dla par")


  # --- INTELIGENTNY GENERATOR KOMPATYBILNYCH ZESTAWÓW AI ---
  def generate_synergy_set(n_count, cnt_all, p_counter, filter_type="all"):
    if not cnt_all:
      return []

    if filter_type == "even":
      valid_pool = [num for num, _ in cnt_all.most_common(80) if num % 2 == 0]
    elif filter_type == "odd":
      valid_pool = [num for num, _ in cnt_all.most_common(80) if num % 2 != 0]
    else:
      valid_pool = [num for num, _ in cnt_all.most_common(80)]

    if not valid_pool:
      return []

    best_start = valid_pool[0]
    selected = [best_start]

    while len(selected) < n_count and len(selected) < len(valid_pool):
      best_cand = None
      max_score = -1

      candidates = [num for num in valid_pool if num not in selected]
      for cand in candidates:
        co_score = sum(
            p_counter.get(tuple(sorted((cand, s))), 0) for s in selected
        )
        score = co_score * 3 + cnt_all[cand]
        if score > max_score:
          max_score = score
          best_cand = cand

      if best_cand is not None:
        selected.append(best_cand)
      else:
        break

    return sorted([f"{num:02d}" for num in selected], key=lambda x: int(x))


  st.markdown("---")
  st.markdown(
      "### 💡 Rekomendowane Zestawy AI (Kompatybilne i Współwystępujące)"
  )

  if counter_all:
    st.markdown("#### 🔥 Zestaw 1: Gorący (Synergia par)")
    n1 = st.slider(
        "Liczba skreśleń w Zestawie 1:", min_value=1, max_value=10, value=5, key="s1"
    )
    set1 = generate_synergy_set(n1, counter_all, pair_counter, "all")
    st.code(" ".join(set1))

    st.markdown("#### ⚖️ Zestaw 2: Zbalansowany (Parzyste/Nieparzyste)")
    n2 = st.slider(
        "Liczba skreśleń w Zestawie 2:", min_value=1, max_value=10, value=5, key="s2"
    )
    h2 = n2 // 2
    r2 = n2 - h2
    bal_odd = generate_synergy_set(r2, counter_all, pair_counter, "odd")
    bal_even = generate_synergy_set(h2, counter_all, pair_counter, "even")
    set2 = sorted(
        bal_odd + bal_even, key=lambda x: int(x) if x.isdigit() else 0
    )
    st.code(" ".join(set2))

    st.markdown("#### 🔵 Zestaw 3: Tylko Parzyste (Synergia)")
    n3 = st.slider(
        "Liczba skreśleń w Zestawie 3:", min_value=1, max_value=10, value=5, key="s3"
    )
    set3 = generate_synergy_set(n3, counter_all, pair_counter, "even")
    st.code(" ".join(set3))

    st.markdown("#### 🟢 Zestaw 4: Tylko Nieparzyste (Synergia)")
    n4 = st.slider(
        "Liczba skreśleń w Zestawie 4:", min_value=1, max_value=10, value=5, key="s4"
    )
    set4 = generate_synergy_set(n4, counter_all, pair_counter, "odd")
    st.code(" ".join(set4))

  # --- ARCHIWUM ---
  st.markdown("---")
  with st.expander("📂 Archiwum: Przeglądaj wszystkie losowania"):
    st.markdown("### Baza wyników (od najnowszych)")

    for idx, row in df_reversed.head(50).iterrows():
      d_str, t_str, nums = parse_row_full(row)
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
