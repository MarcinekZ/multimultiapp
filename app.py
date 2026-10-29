from collections import Counter
from itertools import combinations
import math
import random
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Multi Multi Analytics PWA", page_icon="🎯", layout="wide"
)


def load_data():
  df_live = None
  try:
    session = requests.Session()
    api_url = (
        "https://www.lotto.pl/api/v1/gametype/results?gameType=MultiMulti&size=300"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.lotto.pl/multi-multi/wyniki",
    }
    res = session.get(api_url, headers=headers, timeout=10)

    if res.status_code == 200:
      data = res.json()
      rows = []
      for item in data.get("results", []):
        draw_id = str(item.get("drawId", ""))
        draw_date_time = item.get("drawDate", "")

        if "T" in draw_date_time:
          date_str, time_full = draw_date_time.split("T")
          parts = date_str.split("-")
          if len(parts) == 3:
            formatted_date = f"{parts[2]}.{parts[1]}.{parts[0]}"
          else:
            formatted_date = date_str
          time_str = time_full[:5]
        else:
          formatted_date = draw_date_time
          time_str = "14:00"

        hour_val = int(time_str.split(":")[0]) if ":" in time_str else 14
        time_str = "14:00" if hour_val < 18 else "22:00"

        nums = item.get("results", [])
        if not nums and "resultsJson" in item:
          nums = item["resultsJson"]

        if nums:
          row = [draw_id, formatted_date, time_str] + list(nums)
          rows.append(row)

      if rows:
        df_live = pd.DataFrame(rows)
  except Exception:
    pass

  df_csv = None
  for fname in [
      "multi_multi (10).csv",
      "multi_multi (11).csv",
      "multi_multi (12).csv",
      "multi_multi.csv",
  ]:
    try:
      df_csv = pd.read_csv(fname, header=None)
      break
    except FileNotFoundError:
      continue

  if df_live is not None and not df_live.empty:
    st.sidebar.success("🟢 Status: Live API (Zsynchronizowane)")
    df = df_live
  elif df_csv is not None and not df_csv.empty:
    st.sidebar.error("🔴 Status: Plik lokalny CSV (Tryb awaryjny)")
    df = df_csv
  else:
    return None

  num_cols = df.shape[1]
  cols = ["ID", "Data", "Godzina"] + [f"L{i}" for i in range(1, num_cols - 2)]
  if len(df.columns) == len(cols):
    df.columns = cols
  else:
    df.columns = ["ID", "Data", "Godzina"] + [
        f"L{i}" for i in range(1, df.shape[1] - 2)
    ]

  if "ID" in df.columns:
    df["ID"] = (
        df["ID"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    )


  def clean_hour(val):
    s = str(val).strip()
    try:
      if ":" in s:
        h = int(s.split(":")[0])
        return "14:00" if h < 18 else "22:00"
    except:
      pass
    if "22" in s or "21" in s or "20" in s or "19" in s:
      return "22:00"
    return "14:00"


  df["Godzina"] = df["Godzina"].apply(clean_hour)

  try:
    df["ID_int"] = pd.to_numeric(df["ID"], errors="coerce")
    df = (
        df.sort_values("ID_int")
        .drop_duplicates(subset=["ID"])
        .drop(columns=["ID_int"])
        .reset_index(drop=True)
    )
  except Exception:
    pass

  return df


df = load_data()

st.title("📱 Mobilny Panel Analityczny Ekipy")

if st.button("🔄 Odśwież i pobierz najnowsze z sieci", use_container_width=True):
  st.rerun()

if df is not None and not df.empty:
  total_draws = len(df)

  # --- 1. ARCHIWUM OSTATNICH LOSOWAŃ (NA GÓRZE) ---
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
      val_str = f"{int(val_clean):02d}" if val_clean.isdigit() else val_clean
      if val in repeated or val_clean in repeated:
        formatted_display.append(f"🔄{val_str}")
      else:
        formatted_display.append(f"{val_str}")

    line1 = " ".join(formatted_display[:10])
    line2 = " ".join(formatted_display[10:])
    st.code(f"{line1}\n{line2}", language=None)

  st.divider()

  # --- 2. USTAWIENIA ANALIZY / SUWAK (BLISKO STATYSTYK) ---
  st.subheader("⚙️ Ustawienia Analizy Statystycznej")

  preset_steps = [1, 5, 10, 15, 20, 30, 40, 50, 100, 200, total_draws]
  preset_steps = sorted(
      list(set([opt for opt in preset_steps if opt <= total_draws]))
  )
  if total_draws not in preset_steps:
    preset_steps.append(total_draws)

  if "zakres_val" not in st.session_state:
    st.session_state["zakres_val"] = (
        30 if 30 in preset_steps else preset_steps[0]
    )

  col_minus, col_slider, col_plus = st.columns([1, 4, 1])

  with col_minus:
    if st.button("➖", use_container_width=True, key="main_minus"):
      if st.session_state["zakres_val"] > 1:
        st.session_state["zakres_val"] -= 1
        st.rerun()

  with col_plus:
    if st.button("➕", use_container_width=True, key="main_plus"):
      if st.session_state["zakres_val"] < total_draws:
        st.session_state["zakres_val"] += 1
        st.rerun()

  current_val = st.session_state["zakres_val"]
  slider_options = sorted(list(set(preset_steps + [current_val])))

  with col_slider:
    zakres = st.select_slider(
        "Zakres losowań:",
        options=slider_options,
        value=current_val,
        format_func=lambda x: "Wszystkie losowania"
        if x == total_draws
        else f"{x} losowań",
        key="zakres_val",
        label_visibility="collapsed",
    )

  st.write(
      f"Wybrany zakres bazy do analizy: **{zakres}**"
      f" {'losowań' if zakres < total_draws else '(Wszystkie losowania)'}"
  )
  df_analyzed = df.tail(int(zakres))

  st.divider()

  df_14_all = df[df["Godzina"] == "14:00"]
  df_22_all = df[df["Godzina"] == "22:00"]

  latest_nums_14 = set()
  if not df_14_all.empty:
    latest_draw_14 = df_14_all.iloc[-1]
    latest_nums_14 = {
        f"{int(str(v).replace('.0', '').strip()):02d}"
        if str(v).replace(".0", "").strip().isdigit()
        else str(v).replace(".0", "").strip()
        for v in latest_draw_14.iloc[3:].values
        if pd.notna(v) and str(v).strip()
    }

  latest_nums_22 = set()
  if not df_22_all.empty:
    latest_draw_22 = df_22_all.iloc[-1]
    latest_nums_22 = {
        f"{int(str(v).replace('.0', '').strip()):02d}"
        if str(v).replace(".0", "").strip().isdigit()
        else str(v).replace(".0", "").strip()
        for v in latest_draw_22.iloc[3:].values
        if pd.notna(v) and str(v).strip()
    }


  def format_top10_list(num_list, session_latest_nums):
    res = []
    for n_str in num_list:
      if n_str in session_latest_nums:
        res.append(f"{n_str}✅")
      else:
        res.append(f"{n_str}")
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


  even_14, odd_14 = get_session_top10("14:00")
  even_22, odd_22 = get_session_top10("22:00")

  # --- 3. TOP 10 PARZYSTE I NIEPARZYSTE (14:00 oraz 22:00) ---
  st.subheader("☀️ Godzina 14:00 (Statystyki Historyczne)")
  hits_14_e = sum(1 for n in even_14 if n in latest_nums_14)
  hits_14_o = sum(1 for n in odd_14 if n in latest_nums_14)
  st.markdown(
      f"**Top 10 Parzyste** *(Trafienia w ost. losowaniu: {hits_14_e}/10)*:"
  )
  st.code(
      format_top10_list(even_14, latest_nums_14)
      if even_14
      else "Brak danych",
      language=None,
  )
  st.markdown(
      f"**Top 10 Nieparzyste** *(Trafienia w ost. losowaniu: {hits_14_o}/10)*:"
  )
  st.code(
      format_top10_list(odd_14, latest_nums_14) if odd_14 else "Brak danych",
      language=None,
  )

  st.divider()

  st.subheader("🌙 Godzina 22:00 (Statystyki Historyczne)")
  hits_22_e = sum(1 for n in even_22 if n in latest_nums_22)
  hits_22_o = sum(1 for n in odd_22 if n in latest_nums_22)
  st.markdown(
      "**Top 10 Parzyste: `✅ [Rekomendowany Priorytet]`**"
      f" *(Trafienia w ost. losowaniu: {hits_22_e}/10)*:"
  )
  st.code(
      format_top10_list(even_22, latest_nums_22)
      if even_22
      else "Brak danych",
      language=None,
  )
  st.markdown(
      f"**Top 10 Nieparzyste** *(Trafienia w ost. losowaniu: {hits_22_o}/10)*:"
  )
  st.code(
      format_top10_list(odd_22, latest_nums_22) if odd_22 else "Brak danych",
      language=None,
  )

  st.divider()


  # --- 4. ANALIZA PAR I TRÓJEK (WSPÓŁWYSTĘPOWANIE) ---
  st.subheader("🔗 Analiza Par i Trójek (Współwystępowanie)")
  st.caption(
      "Najczęściej występujące kombinacje liczb w tym samym losowaniu z"
      f" wybranego zakresu ({zakres} losowań)."
  )

  selected_session_for_tuples = st.selectbox(
      "Wybierz sesję do analizy par/trójek:", ["22:00", "14:00"]
  )
  df_tuples_session = df_analyzed[
      df_analyzed["Godzina"] == selected_session_for_tuples
  ]


  def get_top_tuples(df_session, n_size, limit=5):
    counter = Counter()
    for row_vals in df_session.iloc[:, 3:].values:
      draw_nums = []
      for val in row_vals:
        if pd.notna(val) and str(val).strip():
          cleaned_v = str(val).replace(".0", "").strip()
          if cleaned_v.isdigit():
            draw_nums.append(f"{int(cleaned_v):02d}")
      if len(draw_nums) >= n_size:
        sorted_nums = sorted(list(set(draw_nums)), key=lambda x: int(x))
        for comb in combinations(sorted_nums, n_size):
          counter[comb] += 1
    return counter.most_common(limit)


  top_pairs = get_top_tuples(df_tuples_session, 2, 5)
  top_triplets = get_top_tuples(df_tuples_session, 3, 5)

  st.markdown(f"**Top 5 Par (Sesja {selected_session_for_tuples}):**")
  pairs_display = [
      f"({' - '.join(pair)}) [wystąpiły {cnt}x]" for pair, cnt in top_pairs
  ]
  st.code(
      "\n".join(pairs_display)
      if pairs_display
      else "Za mało danych w zakresie",
      language=None,
  )

  st.markdown(f"**Top 5 Trójek (Sesja {selected_session_for_tuples}):**")
  triplets_display = [
      f"({' - '.join(trip)}) [wystąpiły {cnt}x]" for trip, cnt in top_triplets
  ]
  st.code(
      "\n".join(triplets_display)
      if triplets_display
      else "Za mało danych w zakresie",
      language=None,
  )

  st.divider()


  # --- 5. INTELIGENTNY GENERATOR OPARTY O PARY W ZAKRESIE ---
  def get_cooccurrence_recommendations(session_time, parity_type, limit, seed):
    df_session = df_analyzed[df_analyzed["Godzina"] == session_time]
    if df_session.empty:
      return []

    pair_counter = Counter()
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
        d_set = sorted(list(set(draw_nums)), key=lambda x: int(x))
        for p in combinations(d_set, 2):
          pair_counter[p] += 1

    counts = (
        pd.Series(all_session_nums).value_counts()
        if all_session_nums
        else pd.Series(dtype=int)
    )

    all_even = [f"{n:02d}" for n in range(2, 81, 2)]
    all_odd = [f"{n:02d}" for n in range(1, 80, 2)]

    if parity_type == "even":
      candidates = [n for n in all_even]
    elif parity_type == "odd":
      candidates = [n for n in all_odd]
    else:
      candidates = all_even + all_odd

    scores = {}
    for c in candidates:
      ind_freq = counts.get(c, 0)
      pair_weight = sum(
          pair_counter[tuple(sorted([c, other], key=lambda x: int(x)))]
          for other in candidates
          if other != c
      )
      scores[c] = ind_freq * 1.0 + pair_weight * 1.5

    sorted_candidates = sorted(
        candidates, key=lambda x: scores.get(x, 0), reverse=True
    )

    rng = random.Random(seed)
    if not sorted_candidates:
      return []

    selected = [sorted_candidates[0]]

    while len(selected) < limit and len(selected) < len(sorted_candidates):
      best_next = None
      best_score = -1
      for cand in sorted_candidates:
        if cand in selected:
          continue

        if parity_type == "mixed":
          current_even = sum(1 for x in selected if int(x) % 2 == 0)
          target_even = (
              math.ceil(limit * 0.52)
              if session_time == "22:00"
              else math.ceil(limit / 2.0)
          )
          if (
              int(cand) % 2 == 0
              and current_even >= target_even
              and (limit - len(selected)) <= (limit - target_even)
          ):
            continue

        synergy = sum(
            pair_counter[tuple(sorted([cand, s], key=lambda x: int(x)))]
            for s in selected
        )
        total_score = scores.get(cand, 0) + synergy * 3.0
        if total_score > best_score:
          best_score = total_score
          best_next = cand

      if best_next:
        selected.append(best_next)
      else:
        remaining = [c for c in sorted_candidates if c not in selected]
        if remaining:
          selected.append(rng.choice(remaining))
        else:
          break

    return sorted(selected, key=lambda x: int(x))[:limit]


  st.subheader(
      "🎯 Generator Zakładów (Analiza Par i Współwystępowania w Zakresie)"
  )
  st.caption(
      "Generator od 1 do 10 liczb, który dobiera numery na podstawie tego, jak"
      " silnie współwystępują w parach w wybranym zakresie losowań."
  )


  def format_clean_list(num_list):
    return " ".join([f"{int(n):02d}" if n.isdigit() else n for n in num_list])


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

  # --- 6. PEŁNA BAZA WSZYSTKICH LOSOWAŃ ---
  st.subheader("📊 Pełna Baza Wszystkich Losowań")
  display_data = []
  df_reversed = df.iloc[::-1]
  for _, row in df_reversed.iterrows():
    nums = [
        f"{int(str(v).replace('.0', '').strip()):02d}"
        if str(v).replace(".0", "").strip().isdigit()
        else str(v).replace(".0", "").strip()
        for v in row.iloc[3:].values
        if pd.notna(v) and str(v).strip()
    ]
    display_data.append({
        "ID": row["ID"],
        "Data": row["Data"],
        "Godzina": row["Godzina"],
        "Wylosowane liczby": " ".join(nums),
    })

  df_compact = pd.DataFrame(display_data)
  st.dataframe(df_compact, use_container_width=True, hide_index=True)

else:
  st.warning("Oczekiwanie na ładowanie bazy danych...")
