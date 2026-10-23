import random
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Multi Multi Analytics PWA", page_icon="🎯", layout="wide"
)

FILE_NAME = "multi_multi (11.csv"  # lub (10).csv w zależności od pliku bazy


@st.cache_data(ttl=60)
def load_data():
  try:
    # Próbujemy załadować plik bazy (dostosuj nazwę jeśli potrzeba)
    for fname in ["multi_multi (11).csv", "multi_multi (10).csv"]:
      try:
        df = pd.read_csv(fname, header=None)
        break
      except FileNotFoundError:
        continue
    else:
      return None

    num_cols = df.shape[1]
    cols = ["ID", "Data", "Godzina"] + [
        f"L{i}" for i in range(1, num_cols - 2)
    ]
    df.columns = cols
    if "ID" in df.columns:
      df["ID"] = (
          df["ID"]
          .astype(str)
          .str.replace(r"\.0$", "", regex=True)
          .str.strip()
      )
    return df
  except Exception as e:
    st.error(f"Błąd podczas ładowania pliku CSV: {e}")
    return None


df = load_data()

st.title("📱 Mobilny Panel Analityczny Ekipy")

if df is not None and not df.empty:
  total_draws = len(df)

  # 1. ARCHIWUM OSTATNICH LOSOWAŃ NA SAMEJ GÓRZE
  st.subheader("📌 Archiwum: Ostatnie Losowania (Przeskoki)")
  st.caption("Liczby oznaczone 🔄 powtórzyły się z poprzedniego losowania.")

  recent_df = df.tail(5).iloc[::-1]
  for i in range(len(recent_df) - 1):
    curr = recent_df.iloc[i]
    prev = recent_df.iloc[i + 1]

    curr_nums = [
        val
        for val in curr.iloc[3:].values
        if pd.notna(val) and str(val).strip()
    ]
    prev_nums = [
        val
        for val in prev.iloc[3:].values
        if pd.notna(val) and str(val).strip()
    ]

    curr_set = set(curr_nums)
    prev_set = set(prev_nums)
    repeated = curr_set.intersection(prev_set)

    draw_id = curr["ID"]
    date_str = curr["Data"]
    time_str = curr["Godzina"]

    st.markdown(
        f"**Losowanie #{draw_id}** | 📅 {date_str} | ⏰ {time_str}"
    )

    formatted_display = []
    for val in curr_nums:
      val_clean = str(val).replace(".0", "").strip()
      if val_clean.isdigit():
        val_str = f"{int(val_clean):02d}"
      else:
        val_str = val_clean

      if val in repeated or val_clean in repeated:
        formatted_display.append(f"🔄{val_str}")
      else:
        formatted_display.append(f"{val_str}")

    line1 = " ".join(formatted_display[:10])
    line2 = " ".join(formatted_display[10:])
    st.code(f"{line1}\n{line2}", language=None)

  st.divider()

  # 2. USTAWIENIA ANALIZY (SELECT_SLIDER Z PRZYCISKAMI [-] / [+])
  st.subheader("⚙️ Ustawienia Analizy Statystycznej")

  raw_options = [1, 5, 10, 15, 20, 50, 100, 200, total_draws]
  options = sorted(list(set([opt for opt in raw_options if opt <= total_draws])))
  if total_draws not in options:
    options.append(total_draws)

  if "zakres_val" not in st.session_state:
    default_val = 20 if 20 in options else options[-1]
    st.session_state["zakres_val"] = default_val
  else:
    if st.session_state["zakres_val"] not in options:
      st.session_state["zakres_val"] = options[-1]

  col_minus, col_slider, col_plus = st.columns([1, 4, 1])

  with col_minus:
    if st.button("➖", use_container_width=True, key="main_minus"):
      current_idx = options.index(st.session_state["zakres_val"])
      if current_idx > 0:
        st.session_state["zakres_val"] = options[current_idx - 1]

  with col_plus:
    if st.button("➕", use_container_width=True, key="main_plus"):
      current_idx = options.index(st.session_state["zakres_val"])
      if current_idx < len(options) - 1:
        st.session_state["zakres_val"] = options[current_idx + 1]

  with col_slider:
    zakres = st.select_slider(
        "Zakres losowań:",
        options=options,
        value=st.session_state["zakres_val"],
        format_func=lambda x: "Wszystkie losowania"
        if x == total_draws
        else str(x),
        key="zakres_val",
        label_visibility="collapsed",
    )

  st.write(f"Wybrany zakres bazy: **{zakres}** losowań")

  st.divider()

  # Pobieramy liczby z najnowszego losowania TYLKO do historycznej weryfikacji Top 10
  latest_draw = df.iloc[-1]
  latest_nums = {
      f"{int(str(v).replace('.0', '').strip()):02d}"
      if str(v).replace(".0", "").strip().isdigit()
      else str(v).replace(".0", "").strip()
      for v in latest_draw.iloc[3:].values
      if pd.notna(v) and str(v).strip()
  }

  df_analyzed = df.tail(int(zakres))


  def format_top10_list(num_list):
    res = []
    for n_str in num_list:
      if n_str in latest_nums:
        res.append(f"{n_str}✅")
      else:
        res.append(f"{n_str}")
    return " ".join(res)


  def format_clean_list(num_list):
    # Czysta lista bez ptaszków dla przyszłych zakładów
    res = []
    for n_str in num_list:
      if n_str.isdigit():
        res.append(f"{int(n_str):02d}")
      else:
        res.append(n_str)
    return " ".join(res)


  def get_session_top10(session_time):
    df_session = df_analyzed[df_analyzed["Godzina"] == session_time]
    if df_session.empty:
      return [], []
    all_session_nums = []
    for row_vals in df_session.iloc[:, 3:].values:
      for val in row_vals:
        if pd.notna(val) and str(val).strip():
          cleaned_v = str(val).replace(".0", "").strip()
          if cleaned_v.isdigit():
            all_session_nums.append(f"{int(cleaned_v):02d}")

    counts = pd.Series(all_session_nums).value_counts()
    even_counts = counts[
        counts.index.map(lambda x: int(x) % 2 == 0 if x.isdigit() else False)
    ]
    odd_counts = counts[
        counts.index.map(lambda x: int(x) % 2 != 0 if x.isdigit() else False)
    ]
    return even_counts.head(10).index.tolist(), odd_counts.head(10).index.tolist()


  def get_cooccurrence_recommendations(session_time, parity_type, limit, seed):
    df_session = df_analyzed[df_analyzed["Godzina"] == session_time]
    if df_session.empty:
      return []

    draws_lists = []
    all_session_nums = []
    for row_vals in df_session.iloc[:, 3:].values:
      draw_nums = []
      for val in row_vals:
        if pd.notna(val) and str(val).strip():
          cleaned_v = str(val).replace(".0", "").strip()
          if cleaned_v.isdigit():
            num_int = int(cleaned_v)
            is_even = num_int % 2 == 0
            if parity_type == "mixed":
              draw_nums.append(f"{num_int:02d}")
              all_session_nums.append(f"{num_int:02d}")
            elif (parity_type == "even" and is_even) or (
                parity_type == "odd" and not is_even
            ):
              draw_nums.append(f"{num_int:02d}")
              all_session_nums.append(f"{num_int:02d}")
      if draw_nums:
        draws_lists.append(set(draw_nums))

    if not all_session_nums:
      return []

    counts = pd.Series(all_session_nums).value_counts()
    top_frequent = counts.head(10).index.tolist()

    co_scores = {}
    for cand in counts.index.tolist():
      base_freq = counts[cand]
      co_occur = 0
      for d_set in draws_lists:
        if cand in d_set:
          co_occur += len(d_set.intersection(top_frequent))
      co_scores[cand] = base_freq * 1.0 + co_occur * 2.5

    sorted_cands = sorted(
        co_scores.keys(), key=lambda x: co_scores[x], reverse=True
    )

    # Bierzemy pulę najlepszych i generujemy zestaw
    pool = sorted_cands[: max(15, limit * 2)]
    rng = random.Random(seed)
    if len(pool) > limit:
      # Losujemy z zachowaniem preferencji wagowych lub bierzemy top z lekkim przemieszaniem przy ponownym kliknięciu
      selected = rng.sample(pool, min(limit, len(pool)))
      selected = sorted(selected, key=lambda x: int(x))
    else:
      selected = sorted(pool[:limit], key=lambda x: int(x))

    return selected


  even_14, odd_14 = get_session_top10("14:00")
  even_22, odd_22 = get_session_top10("22:00")

  # --- GODZINA 14:00 (TOP 10 CZYSTA CZĘSTOTLIWOŚĆ Z WERYFIKACJĄ HISTORYCZNĄ) ---
  st.subheader("☀️ Godzina 14:00 (Statystyki Historyczne)")

  st.markdown("**Top 10 Parzyste:**")
  st.code(
      format_top10_list(even_14)
      if even_14
      else "Brak danych w wybranym zakresie",
      language=None,
  )

  st.markdown("**Top 10 Nieparzyste:**")
  st.code(
      format_top10_list(odd_14)
      if odd_14
      else "Brak danych w wybranym zakresie",
      language=None,
  )

  st.divider()

  # --- GODZINA 22:00 (TOP 10 CZYSTA CZĘSTOTLIWOŚĆ Z WERYFIKACJĄ HISTORYCZNĄ) ---
  st.subheader("🌙 Godzina 22:00 (Statystyki Historyczne)")

  st.markdown("**Top 10 Parzyste:**")
  st.code(
      format_top10_list(even_22)
      if even_22
      else "Brak danych w wybranym zakresie",
      language=None,
  )

  st.markdown("**Top 10 Nieparzyste:**")
  st.code(
      format_top10_list(odd_22)
      if odd_22
      else "Brak danych w wybranym zakresie",
      language=None,
  )

  st.divider()

  # --- 6 REKOMENDOWANYCH ZAKŁADÓW NA PRZYSZŁE LOSOWANIE (Z PRZYCISKAMI GENEROWANIA) ---
  st.subheader(
      "🎯 Generator Rekomendowanych Zakładów (Na Nadchodzące Losowanie)"
  )
  st.caption(
      "Kliknij „🎲 Generuj zakład”, aby utworzyć czysty zestaw liczb do"
      " obstawienia."
  )


  def render_generator_section(title, session_time, parity_type, key_prefix):
    st.markdown(f"🎯 **{title}**")

    col_btn, col_slider = st.columns([1, 3])
    seed_key = f"seed_{key_prefix}"
    if seed_key not in st.session_state:
      st.session_state[seed_key] = 42

    with col_btn:
      if st.button("🎲 Generuj", key=f"btn_{key_prefix}", use_container_width=True):
        st.session_state[seed_key] = random.randint(1, 10000)

    with col_slider:
      limit = st.slider(
          "Liczba liczb",
          1,
          10,
          5,
          key=f"slider_{key_prefix}",
          label_visibility="collapsed",
      )

    generated_nums = get_cooccurrence_recommendations(
        session_time, parity_type, limit, st.session_state[seed_key]
    )
    st.code(
        format_clean_list(generated_nums)
        if generated_nums
        else "Brak danych w wybranym zakresie",
        language=None,
    )


  render_generator_section(
      "Rekomendowany Zakład: Parzyste (14:00)", "14:00", "even", "e14"
  )
  render_generator_section(
      "Rekomendowany Zakład: Nieparzyste (14:00)", "14:00", "odd", "o14"
  )
  render_generator_section(
      "Rekomendowany Zakład: Mieszany (14:00)", "14:00", "mixed", "m14"
  )

  render_generator_section(
      "Rekomendowany Zakład: Parzyste (22:00)", "22:00", "even", "e22"
  )
  render_generator_section(
      "Rekomendowany Zakład: Nieparzyste (22:00)", "22:00", "odd", "o22"
  )
  render_generator_section(
      "Rekomendowany Zakład: Mieszany (22:00)", "22:00", "mixed", "m22"
  )

  st.divider()

  # --- 📊 CAŁA BAZA WSZYSTKICH LOSOWAŃ NA SAMYM DOLE ---
  st.subheader("📊 Pełna Baza Wszystkich Losowań")
  st.caption(
      "Poniżej znajduje się kompletny zestaw historycznych losowań z bazy"
      " danych."
  )
  st.dataframe(df, use_container_width=True)

else:
  st.warning("Oczekiwanie na ładowanie bazy danych...")
