import math
import random
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Multi Multi Analytics PWA", page_icon="🎯", layout="wide"
)


@st.cache_data(ttl=60)
def load_data():
  try:
    for fname in [
        "multi_multi (11).csv",
        "multi_multi (10).csv",
        "multi_multi.csv",
    ]:
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

  # --- 1. ARCHIWUM OSTATNICH LOSOWAŃ NA SAMEJ GÓRZE ---
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

  # --- 2. USTAWIENIA ANALIZY (PŁYNNY SUWAK Z PRZYCISKAMI [-] / [+] CO 1) ---
  st.subheader("⚙️ Ustawienia Analizy Statystycznej")

  if "zakres_val" not in st.session_state:
    st.session_state["zakres_val"] = 20 if total_draws >= 20 else total_draws

  col_minus, col_slider, col_plus = st.columns([1, 4, 1])

  with col_minus:
    if st.button("➖", use_container_width=True, key="main_minus"):
      if st.session_state["zakres_val"] > 1:
        st.session_state["zakres_val"] -= 1

  with col_plus:
    if st.button("➕", use_container_width=True, key="main_plus"):
      if st.session_state["zakres_val"] < total_draws:
        st.session_state["zakres_val"] += 1

  with col_slider:
    zakres = st.slider(
        "Zakres losowań:",
        min_value=1,
        max_value=total_draws,
        value=st.session_state["zakres_val"],
        step=1,
        key="zakres_val",
        label_visibility="collapsed",
    )

  st.write(f"Wybrany zakres bazy: **{zakres}** losowań")

  st.divider()

  # Weryfikacja historyczna dla Top 10
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
            draw_nums.append(f"{num_int:02d}")
            all_session_nums.append(f"{num_int:02d}")
      if draw_nums:
        draws_lists.append(set(draw_nums))

    if not all_session_nums:
      return []

    counts = pd.Series(all_session_nums).value_counts()
    top_frequent = counts.head(10).index.tolist()

    even_cands = {}
    odd_cands = {}

    for cand in counts.index.tolist():
      base_freq = counts[cand]
      co_occur = 0
      for d_set in draws_lists:
        if cand in d_set:
          co_occur += len(d_set.intersection(top_frequent))
      score = base_freq * 1.0 + co_occur * 2.5

      if int(cand) % 2 == 0:
        even_cands[cand] = score
      else:
        odd_cands[cand] = score

    sorted_even = sorted(
        even_cands.keys(), key=lambda x: even_cands[x], reverse=True
    )
    sorted_odd = sorted(
        odd_cands.keys(), key=lambda x: odd_cands[x], reverse=True
    )

    rng = random.Random(seed)

    if parity_type == "even":
      pool = sorted_even[: max(15, limit * 2)]
      selected = (
          rng.sample(pool, min(limit, len(pool)))
          if len(pool) > limit
          else pool[:limit]
      )
    elif parity_type == "odd":
      pool = sorted_odd[: max(15, limit * 2)]
      selected = (
          rng.sample(pool, min(limit, len(pool)))
          if len(pool) > limit
          else pool[:limit]
      )
    else:  # mieszany - proporcje oparte na analizie bazy
      if session_time == "14:00":
        num_even = math.ceil(limit / 2.0)
        num_odd = limit - num_even
      else:
        # 22:00 - Przewaga parzystych (~52%)
        num_even = math.ceil(limit * 0.52)
        num_odd = limit - num_even

      pool_e = sorted_even[: max(10, num_even * 2)]
      pool_o = sorted_odd[: max(10, num_odd * 2)]

      sel_e = (
          rng.sample(pool_e, min(num_even, len(pool_e)))
          if len(pool_e) > num_even
          else pool_e[:num_even]
      )
      sel_o = (
          rng.sample(pool_o, min(num_odd, len(pool_o)))
          if len(pool_o) > num_odd
          else pool_o[:num_odd]
      )

      selected = sel_e + sel_o

    return sorted(selected, key=lambda x: int(x))


  even_14, odd_14 = get_session_top10("14:00")
  even_22, odd_22 = get_session_top10("22:00")

  # --- 3. TOP 10 Z OZNACZENIAMI PRIORYTETÓW (✅) ---
  st.subheader("☀️ Godzina 14:00 (Statystyki Historyczne)")
  st.caption("ℹ️ Bilans 14:00: Zrównoważony rozkład (50% Parzyste / 50% Nieparzyste)")

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

  st.subheader("🌙 Godzina 22:00 (Statystyki Historyczne)")
  st.caption(
      "ℹ️ Bilans 22:00: Wyraźny priorytet i przewaga liczb **Parzystych**"
      " (~52%)"
  )

  st.markdown("**Top 10 Parzyste: `✅ [Rekomendowany Priorytet]`**")
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

  # --- 4. GENERATORY ZAKŁADÓW NA PRZYSZŁE LOSOWANIE Z OZNACZENIAMI ✅ ---
  st.subheader(
      "🎯 Generator Rekomendowanych Zakładów (Na Nadchodzące Losowanie)"
  )
  st.caption(
      "Oznaczenia ✅ wskazują rekomendowany priorytet parzystości wynikający z"
      " bazy historycznej."
  )


  def render_generator_section(
      title, session_time, parity_type, key_prefix, has_priority=False
  ):
    priority_badge = " ✅ [Rekomendowany Priorytet]" if has_priority else ""
    st.markdown(f"🎯 **{title}{priority_badge}**")

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
      "Rekomendowany Zakład: Parzyste (14:00)", "14:00", "even", "e14", False
  )
  render_generator_section(
      "Rekomendowany Zakład: Nieparzyste (14:00)", "14:00", "odd", "o14", False
  )
  render_generator_section(
      "Rekomendowany Zakład: Mieszany (14:00) [Zrównoważony 50/50]",
      "14:00",
      "mixed",
      "m14",
      True,
  )

  render_generator_section(
      "Rekomendowany Zakład: Parzyste (22:00)",
      "22:00",
      "even",
      "e22",
      True,
  )
  render_generator_section(
      "Rekomendowany Zakład: Nieparzyste (22:00)", "22:00", "odd", "o22", False
  )
  render_generator_section(
      "Rekomendowany Zakład: Mieszany (22:00) [Zbalansowany z przewagą"
      " parzystych]",
      "22:00",
      "mixed",
      "m22",
      True,
  )

  st.divider()

  # --- 5. PEŁNA BAZA WSZYSTKICH LOSOWAŃ NA SAMYM DOLE ---
  st.subheader("📊 Pełna Baza Wszystkich Losowań")
  st.caption(
      "Poniżej znajduje się kompletny zestaw historycznych losowań z bazy"
      " danych."
  )
  st.dataframe(df, use_container_width=True)

else:
  st.warning("Oczekiwanie na ładowanie bazy danych...")
