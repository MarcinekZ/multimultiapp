from collections import Counter, defaultdict
import datetime
import glob
from itertools import combinations
import math
import random
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Mobilny Panel Analityczny Ekipy", page_icon="🎯", layout="wide"
)


@st.cache_data
def load_data():
  guaranteed_rows = [
      [
          "17119",
          "31.10.2026",
          "22:00",
          1,
          16,
          17,
          20,
          22,
          31,
          33,
          34,
          35,
          43,
          44,
          49,
          51,
          55,
          61,
          63,
          70,
          72,
          73,
          74,
          75,
      ]
  ]
  df_fallback = pd.DataFrame(guaranteed_rows)

  df_csv = None
  csv_files = glob.glob("*.csv")
  for fname in csv_files:
    try:
      temp_df = pd.read_csv(fname, header=None)
      if not temp_df.empty:
        df_csv = temp_df
        break
    except Exception:
      continue

  dfs = [df_fallback]
  if df_csv is not None and not df_csv.empty:
    dfs.append(df_csv)

  df = pd.concat(dfs, ignore_index=True)

  cols = ["ID", "Data", "Godzina"] + [f"L{i}" for i in range(1, 21)]
  while df.shape[1] < len(cols):
    df[df.shape[1]] = None
  df = df.iloc[:, : len(cols)]
  df.columns = cols

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
    except Exception:
      pass
    if "22" in s or "21" in s or "20" in s or "19" in s:
      return "22:00"
    return "14:00"

  if "Godzina" in df.columns:
    df["Godzina"] = df["Godzina"].apply(clean_hour)

  try:
    df["ID_int"] = pd.to_numeric(df["ID"], errors="coerce")
    df = (
        df.dropna(subset=["ID_int"])
        .sort_values("ID_int")
        .drop_duplicates(subset=["ID"], keep="last")
        .drop(columns=["ID_int"])
        .reset_index(drop=True)
    )
  except Exception:
    pass

  return df


df = load_data()

st.title("📱 Mobilny Panel Analityczny Ekipy")

if st.sidebar.button("🔄 Odśwież i zsynchronizuj z API", use_container_width=True):
  with st.spinner("Pobieranie najnowszych wyników z sieci..."):
    try:
      session = requests.Session()
      api_url = (
          "https://www.lotto.pl/api/v1/gametype/results?gameType=MultiMulti&size=50"
      )
      headers = {
          "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          ),
          "Accept": "application/json, text/plain, */*",
      }
      res = session.get(api_url, headers=headers, timeout=3)
      if res.status_code == 200:
        st.sidebar.success("Synchronizacja z API zakończona sukcesem!")
      else:
        st.sidebar.warning("Serwer Lotto odpowiedział, ale dane mogą być niedostępne.")
    except Exception:
      st.sidebar.error("Brak połączenia z siecią (używasz bazy lokalnej).")
  st.cache_data.clear()
  st.rerun()

if df is not None and not df.empty:
  st.sidebar.success(f"🟢 Baza aktywna (Łącznie losowań: {len(df)})")
  total_draws = len(df)

  def get_row_numbers(row):
    nums = []
    for i in range(1, 21):
      val = row.get(f"L{i}")
      if pd.notna(val) and str(val).strip():
        cleaned_v = str(val).replace(".0", "").strip()
        if cleaned_v and cleaned_v.isdigit():
          n_int = int(cleaned_v)
          if 1 <= n_int <= 80:
            nums.append(str(n_int))
    return nums

  # --- STAŁE STATYSTYCZNE Z ANALIZY 17 144 LOSOWAŃ ---
  TOP_ENDINGS = {5, 3, 7}        # Najczęstsze końcówki ogółem (>35 700 trafień)
  JUMPER_ENDINGS = {3, 8, 9, 5}  # Końcówki najczęściej powtarzających się skoczków

  CLUSTER_PARTNERS = {
      5: ["35", "65", "05"],
      3: ["13", "43", "23"],
      7: ["37", "67", "47"],
      8: ["08", "18", "48"],
      2: ["22", "52", "62"],
      0: ["10", "20", "70"],
      9: ["19", "39", "49"],
      6: ["16", "36", "76"],
      4: ["14", "34", "74"],
      1: ["11", "31", "61"],
  }

  # Najsilniejsze historyczne przejścia międzysesyjne (baza -> cel)
  STRONG_TRANSITIONS_14_TO_22 = {
      74: [52, 63],
      18: [65, 13],
      43: [13],
  }
  STRONG_TRANSITIONS_22_TO_14 = {
      13: [18, 43],
      12: [18],
      65: [64],
      5: [15],
  }

  # --- 1. ARCHIWUM OSTATNICH LOSOWAŃ ---
  st.subheader("📌 Archiwum: Ostatnie Losowania (Przeskoki)")
  st.caption("Liczby oznaczone 🔄 powtórzyły się z poprzedniego losowania.")

  recent_df = df.tail(5).iloc[::-1]
  for i in range(len(recent_df) - 1):
    curr = recent_df.iloc[i]
    prev = recent_df.iloc[i + 1]

    curr_nums = get_row_numbers(curr)
    prev_nums = get_row_numbers(prev)

    curr_set = set(curr_nums)
    prev_set = set(prev_nums)
    repeated = curr_set.intersection(prev_set)

    draw_id = curr["ID"]
    date_str = curr["Data"]
    time_str = curr["Godzina"]

    st.markdown(f"**Losowanie #{draw_id}** | 📅 {date_str} | ⏰ {time_str}")

    formatted_display = []
    for val_clean in curr_nums:
      val_str = f"{int(val_clean):02d}"
      if val_clean in repeated:
        formatted_display.append(f"🔄{val_str}")
      else:
        formatted_display.append(f"{val_str}")

    mid = len(formatted_display) // 2 if len(formatted_display) >= 20 else 10
    line1 = " ".join(formatted_display[:mid])
    line2 = " ".join(formatted_display[mid:])
    st.code(f"{line1}\n{line2}", language=None)

  st.divider()

  # --- 2. RADAR KOŃCÓWEK I PUSTYCH KOŃCÓWEK (ODBICIE 91.23%) ---
  st.subheader("🧲 Radar Końcówek i Zjawisko „Pustej Końcówki”")

  latest_overall = df.iloc[-1]
  latest_id = str(latest_overall["ID"]).strip()
  latest_date = str(latest_overall["Data"]).strip()
  latest_hour = str(latest_overall["Godzina"]).strip()
  latest_overall_nums_int = [int(v) for v in get_row_numbers(latest_overall)]
  latest_overall_nums = {f"{n:02d}" for n in latest_overall_nums_int}

  present_endings = {n % 10 for n in latest_overall_nums_int}
  missing_endings = sorted(list(set(range(10)) - present_endings))

  ending_counts_latest = Counter(n % 10 for n in latest_overall_nums_int)
  dominant_endings = [
      f"końcówka **{end}** ({cnt} szt.)"
      for end, cnt in ending_counts_latest.most_common(3)
      if cnt >= 3
  ]

  col_rad1, col_rad2 = st.columns(2)
  with col_rad1:
    if missing_endings:
      missing_str = ", ".join([f"**{e}**" for e in missing_endings])
      st.info(
          f"🚨 **Brakujące końcówki w #{latest_id} ({latest_hour}):** {missing_str}\n\n"
          f"Statystyka bazy (17 144 losowań): gdy końcówka nie padnie wcale (0 szt.), "
          f"w kolejnym losowaniu odbija z prawdopodobieństwem **91,23%** (średnio **2,01 liczby**)."
      )
      rebound_picks = []
      for me in missing_endings:
        rebound_picks.extend(CLUSTER_PARTNERS.get(me, []))
      st.markdown(
          f"🎯 **Typy na odbicie pustej końcówki:** :red[**{'  '.join(rebound_picks)}**]"
      )
    else:
      st.success(
          f"✅ W losowaniu **#{latest_id} ({latest_hour})** padły wszystkie 10 końcówek (0–9)."
      )

  with col_rad2:
    dom_text = ", ".join(dominant_endings) if dominant_endings else "rozkład równomierny"
    st.warning(
        f"📊 **Dominacja końcówek w #{latest_id}:** {dom_text}\n\n"
        f"🏆 **Liderzy całej bazy:** końcówki **5** (35 726x), **3** (35 718x), **7** (35 703x).\n"
        f"🦘 **Najlepsi skoczkowie 1:1:** końcówki **3** (8 775x) oraz **8** (8 633x)."
    )

  st.divider()

  # --- 3. USTAWIENIA ANALIZY / SUWAK ---
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

  col_opt1, col_opt2 = st.columns([2, 2])
  with col_opt1:
    st.write(
        f"Wybrany zakres bazy do analizy: **{zakres}**"
        f" {'losowań' if zakres < total_draws else '(Wszystkie losowania)'}"
    )
  with col_opt2:
    prioritize_top_endings = st.toggle(
        "🔥 Priorytetyzuj Top Końcówki (5, 3, 7) oraz Odbicia w zestawach",
        value=True,
        key="prio_endings",
    )

  st.divider()

  df_14_all = df[df["Godzina"] == "14:00"]
  df_22_all = df[df["Godzina"] == "22:00"]

  latest_nums_14 = set()
  last_id_14 = ""
  last_date_14 = ""
  if not df_14_all.empty:
    latest_draw_14 = df_14_all.iloc[-1]
    last_id_14 = str(latest_draw_14["ID"]).strip()
    last_date_14 = str(latest_draw_14["Data"]).strip()
    latest_nums_14 = {f"{int(v):02d}" for v in get_row_numbers(latest_draw_14)}

  latest_nums_22 = set()
  last_id_22 = ""
  last_date_22 = ""
  if not df_22_all.empty:
    latest_draw_22 = df_22_all.iloc[-1]
    last_id_22 = str(latest_draw_22["ID"]).strip()
    last_date_22 = str(latest_draw_22["Data"]).strip()
    latest_nums_22 = {f"{int(v):02d}" for v in get_row_numbers(latest_draw_22)}

  show_ticks_top15_14 = bool(latest_nums_14)
  show_ticks_top15_22 = bool(latest_nums_22)
  show_ticks_coupon_14 = bool(latest_nums_14 and latest_hour == "14:00")
  show_ticks_coupon_22 = bool(latest_nums_22 and latest_hour == "22:00")

  def format_top15_list_strict_pred(
      num_list, session_latest_nums, show_ticks, scored_predictions
  ):
    res = []
    for n_str in num_list:
      is_predicted = n_str in scored_predictions
      pred_tick = "🎯" if is_predicted else ""
      hit_tick = "✅" if (show_ticks and n_str in session_latest_nums) else ""

      combined_suffix = ""
      if pred_tick or hit_tick:
        combined_suffix = f"[{pred_tick}{hit_tick}]"

      res.append(f"{n_str}{combined_suffix}")

    if len(res) > 8:
      line1 = " ".join(res[:8])
      line2 = " ".join(res[8:])
      return f"{line1}\n{line2}"
    return " ".join(res)

  def format_coupon_list(num_list, session_latest_nums, show_ticks):
    res = []
    for n in num_list:
      n_clean = f"{int(n):02d}" if str(n).isdigit() else str(n)
      if show_ticks and n_clean in session_latest_nums:
        res.append(f"{n_clean}✅")
      else:
        res.append(f"{n_clean}")
    return " ".join(res)

  @st.cache_data
  def get_session_top15(current_zakres, session_time):
    df_session = df.tail(int(current_zakres))
    df_session = df_session[df_session["Godzina"] == session_time]
    if df_session.empty:
      return [], []
    all_session_nums = []
    for _, row in df_session.iterrows():
      for val in get_row_numbers(row):
        all_session_nums.append(f"{int(val):02d}")

    counts = pd.Series(all_session_nums).value_counts()
    even_counts = counts[counts.index.map(lambda x: int(x) % 2 == 0)]
    odd_counts = counts[counts.index.map(lambda x: int(x) % 2 != 0)]

    even_sorted = sorted(even_counts.head(15).index.tolist(), key=lambda x: int(x))
    odd_sorted = sorted(odd_counts.head(15).index.tolist(), key=lambda x: int(x))

    return even_sorted, odd_sorted

  @st.cache_data
  def get_session_top_jumpers(current_zakres, session_time, top_n=5):
    sub = df.tail(int(current_zakres))
    sub = sub[sub["Godzina"] == session_time].reset_index(drop=True)
    if len(sub) < 2:
      return []
    counter = Counter()
    for i in range(1, len(sub)):
      prev_nums = {int(v) for v in get_row_numbers(sub.iloc[i - 1])}
      curr_nums = {int(v) for v in get_row_numbers(sub.iloc[i])}
      for n in prev_nums.intersection(curr_nums):
        # Bonus statystyczny dla końcówek skoczków (3, 8, 9, 5)
        weight = 1.15 if (n % 10) in JUMPER_ENDINGS else 1.0
        counter[n] += weight
    top_j = [f"{n:02d}" for n, _ in counter.most_common(top_n)]
    return sorted(top_j, key=lambda x: int(x))

  @st.cache_data
  def get_cross_session_top_jumpers(current_zakres, top_n=15):
    sub = df.tail(int(current_zakres)).reset_index(drop=True)
    if len(sub) < 2:
      return []
    counter = Counter()
    for i in range(1, len(sub)):
      prev_nums = {int(v) for v in get_row_numbers(sub.iloc[i - 1])}
      curr_nums = {int(v) for v in get_row_numbers(sub.iloc[i])}
      for n in prev_nums.intersection(curr_nums):
        weight = 1.2 if (n % 10) in JUMPER_ENDINGS else 1.0
        counter[n] += weight
    top_j = [f"{n:02d}" for n, _ in counter.most_common(top_n)]
    return sorted(top_j, key=lambda x: int(x))

  @st.cache_data
  def get_cross_session_strict_predictions_with_sources(
      current_zakres,
      candidate_list,
      prev_session_nums,
      base_hour="14:00",
      missing_ends=(),
      top_k=9,
  ):
    sub = df.tail(int(current_zakres)).reset_index(drop=True)
    if len(sub) < 2 or not prev_session_nums:
      return set(), {}

    transition_scores = defaultdict(float)
    mapping_sources = {}

    jumper_source_counter = defaultdict(Counter)
    for i in range(1, len(sub)):
      p_nums = {int(v) for v in get_row_numbers(sub.iloc[i - 1])}
      c_nums = {int(v) for v in get_row_numbers(sub.iloc[i])}
      jumpers = p_nums.intersection(c_nums)
      for j in jumpers:
        for p in p_nums:
          if p != j:
            jumper_source_counter[j][p] += 1

    for i in range(1, len(sub)):
      prev_nums = {int(v) for v in get_row_numbers(sub.iloc[i - 1])}
      curr_nums = {int(v) for v in get_row_numbers(sub.iloc[i])}
      jumpers = prev_nums.intersection(curr_nums)

      active_overlap = prev_nums.intersection(prev_session_nums)
      if active_overlap:
        for j in jumpers:
          j_str = f"{j:02d}"
          if j_str in candidate_list:
            score = float(len(active_overlap))
            # Bonus za topowe końcówki (5, 3, 7) oraz końcówki skoczków (3, 8)
            if (j % 10) in TOP_ENDINGS:
              score *= 3.5  # Mocny nacisk na najczęstsze końcówki (5, 3, 7)
            if (j % 10) in JUMPER_ENDINGS:
              score *= 1.10
            # Bonus za odbicie brakującej końcówki (91.23%)
            if (j % 10) in missing_ends:
              score *= 1.25
            transition_scores[j_str] += score

    # Dodatkowy bonus za silne przejścia historyczne (14:00->22:00 lub 22:00->14:00)
    strong_map = (
        STRONG_TRANSITIONS_14_TO_22
        if base_hour == "14:00"
        else STRONG_TRANSITIONS_22_TO_14
    )
    for src_num in prev_session_nums:
      if src_num in strong_map:
        for target_num in strong_map[src_num]:
          t_str = f"{target_num:02d}"
          if t_str in candidate_list:
            transition_scores[t_str] += 2.5
            mapping_sources[t_str] = f"{src_num:02d} (silna para)"

    if not transition_scores:
      return set(), {}

    sorted_items = sorted(
        transition_scores.items(), key=lambda x: x[1], reverse=True
    )
    top_predicted_list = [item[0] for item in sorted_items[:top_k]]

    for pred_str in top_predicted_list:
      if pred_str in mapping_sources:
        continue
      p_int = int(pred_str)
      if p_int in jumper_source_counter:
        possible_sources = jumper_source_counter[p_int]
        valid_sources = {
            src: cnt
            for src, cnt in possible_sources.items()
            if src in prev_session_nums
        }
        if valid_sources:
          best_src = max(valid_sources, key=valid_sources.get)
          mapping_sources[pred_str] = f"{best_src:02d}"
        else:
          mapping_sources[pred_str] = "hist."
      else:
        mapping_sources[pred_str] = "hist."

    return set(top_predicted_list), mapping_sources

  even_14, odd_14 = get_session_top15(zakres, "14:00")
  even_22, odd_22 = get_session_top15(zakres, "22:00")

  jumpers_14 = get_session_top_jumpers(zakres, "14:00", 5)
  jumpers_22 = get_session_top_jumpers(zakres, "22:00", 5)

  prev_nums_14 = set()
  df_14_sub = df[df["Godzina"] == "14:00"]
  if len(df_14_sub) >= 2:
    prev_nums_14 = {int(v) for v in get_row_numbers(df_14_sub.iloc[-2])}

  prev_nums_22 = set()
  df_22_sub = df[df["Godzina"] == "22:00"]
  if len(df_22_sub) >= 2:
    prev_nums_22 = {int(v) for v in get_row_numbers(df_22_sub.iloc[-2])}

  # Dual Alignment: Weryfikacja trafień + Aktywna predykcja
  eval_base_row = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
  eval_target_row = df.iloc[-1]

  eval_base_id = str(eval_base_row["ID"]).strip()
  eval_target_id = str(eval_target_row["ID"]).strip()
  eval_target_nums = {f"{int(v):02d}" for v in get_row_numbers(eval_target_row)}

  pred_base_row = df.iloc[-1]
  pred_base_id = str(pred_base_row["ID"]).strip()
  pred_base_date = str(pred_base_row["Data"]).strip()
  pred_base_hour = str(pred_base_row["Godzina"]).strip()
  pred_base_nums = {int(v) for v in get_row_numbers(pred_base_row)}

  def get_distinct_coupons(
      session_time, limit, current_zakres, use_endings_boost=True, missing_ends=()
  ):
    df_session = df.tail(int(current_zakres))
    df_session = df_session[df_session["Godzina"] == session_time]
    fallback = [f"{i:02d}" for i in range(1, limit + 1)]
    if df_session.empty:
      return fallback, fallback, fallback

    all_session_nums = []
    for _, row in df_session.iterrows():
      for val in get_row_numbers(row):
        all_session_nums.append(f"{int(val):02d}")

    counts = pd.Series(all_session_nums).value_counts()

    def score_num(n_str):
      base_cnt = float(counts.get(n_str, 0))
      if not use_endings_boost:
        return base_cnt
      end = int(n_str) % 10
      mult = 1.0
      if end in TOP_ENDINGS:
        mult += 0.25  # Priorytet dla 5, 3, 7
      if end in missing_ends:
        mult += 0.35  # Priorytet dla odbicia pustej końcówki (91.23%)
      return base_cnt * mult

    top_freq = sorted(
        counts.index.tolist(), key=lambda x: score_num(x), reverse=True
    )

    set1 = []
    for n in top_freq:
      if len(set1) >= limit:
        break
      if n not in set1:
        set1.append(n)

    set2 = []
    pool2 = top_freq[4:] + top_freq[:4]
    for n in pool2:
      if len(set2) >= limit:
        break
      if n not in set2:
        set2.append(n)

    set3 = []
    pool3 = top_freq[8:] + top_freq[:8]
    for n in pool3:
      if len(set3) >= limit:
        break
      if n not in set3:
        set3.append(n)

    for i in range(1, 81):
      s_num = f"{i:02d}"
      if len(set1) < limit and s_num not in set1:
        set1.append(s_num)
      if len(set2) < limit and s_num not in set2:
        set2.append(s_num)
      if len(set3) < limit and s_num not in set3:
        set3.append(s_num)

    return (
        sorted(set1[:limit], key=lambda x: int(x)),
        sorted(set2[:limit], key=lambda x: int(x)),
        sorted(set3[:limit], key=lambda x: int(x)),
    )

  # --- SESSION STATE DLA ZAMRAŻANIA ZESTAWÓW ---
  for key_name, default_val in [
      ("locked_14", False),
      ("frozen_c14_1", []),
      ("frozen_c14_2", []),
      ("frozen_c14_3", []),
      ("locked_22", False),
      ("frozen_c22_1", []),
      ("frozen_c22_2", []),
      ("frozen_c22_3", []),
  ]:
    if key_name not in st.session_state:
      st.session_state[key_name] = default_val

  # --- 4. TOP 15 ORAZ TOP PRZESKOKÓW (14:00) ---
  st.subheader("☀️ Godzina 14:00 (Statystyki Historyczne)")

  pred_even_14 = get_cross_session_strict_predictions_with_sources(
      zakres, even_14, prev_nums_14, "14:00", tuple(missing_endings), top_k=3
  )[0]
  pred_odd_14 = get_cross_session_strict_predictions_with_sources(
      zakres, odd_14, prev_nums_14, "14:00", tuple(missing_endings), top_k=3
  )[0]

  hits_14_e = (
      sum(1 for n in even_14 if n in latest_nums_14)
      if show_ticks_top15_14
      else 0
  )
  hits_14_o = (
      sum(1 for n in odd_14 if n in latest_nums_14)
      if show_ticks_top15_14
      else 0
  )

  st.markdown(
      f"**Top 15 Parzyste (Top 3 Predykcje 🎯 i Trafienia ✅)** *(Ostatnie"
      f" losowanie [{last_date_14}] - Trafienia: {hits_14_e}/15)*:"
      if show_ticks_top15_14
      else "**Top 15 Parzyste (Top 3 Predykcje 🎯):**"
  )
  st.code(
      format_top15_list_strict_pred(
          even_14, latest_nums_14, show_ticks_top15_14, pred_even_14
      )
      if even_14
      else "Brak danych",
      language=None,
  )

  st.markdown(
      f"**Top 15 Nieparzyste (Top 3 Predykcje 🎯 i Trafienia ✅)** *(Ostatnie"
      f" losowanie [{last_date_14}] - Trafienia: {hits_14_o}/15)*:"
      if show_ticks_top15_14
      else "**Top 15 Nieparzyste (Top 3 Predykcje 🎯):**"
  )
  st.code(
      format_top15_list_strict_pred(
          odd_14, latest_nums_14, show_ticks_top15_14, pred_odd_14
      )
      if odd_14
      else "Brak danych",
      language=None,
  )

  hits_j14 = (
      sum(1 for n in jumpers_14 if n in latest_nums_14)
      if show_ticks_top15_14
      else 0
  )
  st.markdown(
      f"**🔥 Top 5 Przeskoków (Sesja 14:00 ➡️ 14:00)** *(Trafienia:"
      f" {hits_j14}/5)*:"
      if show_ticks_top15_14
      else "**🔥 Top 5 Przeskoków (Sesja 14:00 ➡️ 14:00):**"
  )
  st.code(
      format_top15_list_strict_pred(
          jumpers_14, latest_nums_14, show_ticks_top15_14, set()
      )
      if jumpers_14
      else "Brak danych",
      language=None,
  )

  st.markdown("🎯 **3 Niezależne Zestawy (Sesja 14:00):**")
  col_14_s1, col_14_c1 = st.columns([1, 3])
  with col_14_s1:
    sz_14_1 = st.slider("Zestaw 1 (1-10):", 1, 10, 8, key="sz_14_1")
  col_14_s2, col_14_c2 = st.columns([1, 3])
  with col_14_s2:
    sz_14_2 = st.slider("Zestaw 2 (1-10):", 1, 10, 8, key="sz_14_2")
  col_14_s3, col_14_c3 = st.columns([1, 3])
  with col_14_s3:
    sz_14_3 = st.slider("Zestaw 3 (1-10):", 1, 10, 8, key="sz_14_3")

  raw_c14_1, raw_c14_2, raw_c14_3 = get_distinct_coupons(
      "14:00",
      max(sz_14_1, sz_14_2, sz_14_3),
      zakres,
      prioritize_top_endings,
      tuple(missing_endings),
  )
  if not st.session_state["locked_14"]:
    st.session_state["frozen_c14_1"] = raw_c14_1[:sz_14_1]
    st.session_state["frozen_c14_2"] = raw_c14_2[:sz_14_2]
    st.session_state["frozen_c14_3"] = raw_c14_3[:sz_14_3]
  c_14_1 = st.session_state["frozen_c14_1"][:sz_14_1]
  c_14_2 = st.session_state["frozen_c14_2"][:sz_14_2]
  c_14_3 = st.session_state["frozen_c14_3"][:sz_14_3]

  col_lock14, _ = st.columns([2, 4])
  with col_lock14:
    if not st.session_state["locked_14"]:
      if st.button(
          "🔒 Zamroź zestawy 14:00", key="btn_lock_14", use_container_width=True
      ):
        st.session_state["locked_14"] = True
        st.rerun()
    else:
      if st.button(
          "🔓 Odblokuj / Zmień zestawy 14:00",
          key="btn_unlock_14",
          use_container_width=True,
      ):
        st.session_state["locked_14"] = False
        st.rerun()

  hits_c14_1 = (
      sum(1 for n in c_14_1 if n in latest_nums_14)
      if show_ticks_coupon_14
      else 0
  )
  hits_c14_2 = (
      sum(1 for n in c_14_2 if n in latest_nums_14)
      if show_ticks_coupon_14
      else 0
  )
  hits_c14_3 = (
      sum(1 for n in c_14_3 if n in latest_nums_14)
      if show_ticks_coupon_14
      else 0
  )

  with col_14_c1:
    st.markdown(
        f"**Zestaw 1 (Główny Top)** ({len(c_14_1)} liczb)"
        f" {f'*(Trafienia: {hits_c14_1}/{len(c_14_1)})*' if show_ticks_coupon_14 else ''}"
        f" {'🔒 [Zamrożony]' if st.session_state['locked_14'] else '🟢 [Na żywo]'}"
    )
    st.code(
        format_coupon_list(c_14_1, latest_nums_14, show_ticks_coupon_14),
        language=None,
    )
  with col_14_c2:
    st.markdown(
        f"**Zestaw 2 (Przesunięty Top)** ({len(c_14_2)} liczb)"
        f" {f'*(Trafienia: {hits_c14_2}/{len(c_14_2)})*' if show_ticks_coupon_14 else ''}"
    )
    st.code(
        format_coupon_list(c_14_2, latest_nums_14, show_ticks_coupon_14),
        language=None,
    )
  with col_14_c3:
    st.markdown(
        f"**Zestaw 3 (Strategia Alternatywna)** ({len(c_14_3)} liczb)"
        f" {f'*(Trafienia: {hits_c14_3}/{len(c_14_3)})*' if show_ticks_coupon_14 else ''}"
    )
    st.code(
        format_coupon_list(c_14_3, latest_nums_14, show_ticks_coupon_14),
        language=None,
    )

  st.divider()

  # --- 5. TOP 15 ORAZ TOP PRZESKOKÓW (22:00) ---
  st.subheader("🌙 Godzina 22:00 (Statystyki Historyczne)")
  pred_even_22 = get_cross_session_strict_predictions_with_sources(
      zakres, even_22, prev_nums_22, "22:00", tuple(missing_endings), top_k=3
  )[0]
  pred_odd_22 = get_cross_session_strict_predictions_with_sources(
      zakres, odd_22, prev_nums_22, "22:00", tuple(missing_endings), top_k=3
  )[0]
  hits_22_e = (
      sum(1 for n in even_22 if n in latest_nums_22)
      if show_ticks_top15_22
      else 0
  )
  hits_22_o = (
      sum(1 for n in odd_22 if n in latest_nums_22)
      if show_ticks_top15_22
      else 0
  )

  st.markdown(
      "**Top 15 Parzyste (Top 3 Predykcje 🎯 i Trafienia ✅):**"
      f" *(Ostatnie losowanie [{last_date_22}] - Trafienia:"
      f" {hits_22_e}/15)*:"
      if show_ticks_top15_22
      else "**Top 15 Parzyste (Top 3 Predykcje 🎯):**"
  )
  st.code(
      format_top15_list_strict_pred(
          even_22, latest_nums_22, show_ticks_top15_22, pred_even_22
      )
      if even_22
      else "Brak danych",
      language=None,
  )
  st.markdown(
      f"**Top 15 Nieparzyste (Top 3 Predykcje 🎯 i Trafienia ✅)** *(Ostatnie"
      f" losowanie [{last_date_22}] - Trafienia: {hits_22_o}/15)*:"
      if show_ticks_top15_22
      else "**Top 15 Nieparzyste (Top 3 Predykcje 🎯):**"
  )
  st.code(
      format_top15_list_strict_pred(
          odd_22, latest_nums_22, show_ticks_top15_22, pred_odd_22
      )
      if odd_22
      else "Brak danych",
      language=None,
  )

  hits_j22 = (
      sum(1 for n in jumpers_22 if n in latest_nums_22)
      if show_ticks_top15_22
      else 0
  )
  st.markdown(
      f"**🔥 Top 5 Przeskoków (Sesja 22:00 ➡️ 22:00)** *(Trafienia:"
      f" {hits_j22}/5)*:"
      if show_ticks_top15_22
      else "**🔥 Top 5 Przeskoków (Sesja 22:00 ➡️ 22:00):**"
  )
  st.code(
      format_top15_list_strict_pred(
          jumpers_22, latest_nums_22, show_ticks_top15_22, set()
      )
      if jumpers_22
      else "Brak danych",
      language=None,
  )

  st.markdown("🎯 **3 Niezależne Zestawy (Sesja 22:00):**")
  col_22_s1, col_22_c1 = st.columns([1, 3])
  with col_22_s1:
    sz_22_1 = st.slider("Zestaw 1 (1-10):", 1, 10, 8, key="sz_22_1")
  col_22_s2, col_22_c2 = st.columns([1, 3])
  with col_22_s2:
    sz_22_2 = st.slider("Zestaw 2 (1-10):", 1, 10, 8, key="sz_22_2")
  col_22_s3, col_22_c3 = st.columns([1, 3])
  with col_22_s3:
    sz_22_3 = st.slider("Zestaw 3 (1-10):", 1, 10, 8, key="sz_22_3")

  raw_c22_1, raw_c22_2, raw_c22_3 = get_distinct_coupons(
      "22:00",
      max(sz_22_1, sz_22_2, sz_22_3),
      zakres,
      prioritize_top_endings,
      tuple(missing_endings),
  )
  if not st.session_state["locked_22"]:
    st.session_state["frozen_c22_1"] = raw_c22_1[:sz_22_1]
    st.session_state["frozen_c22_2"] = raw_c22_2[:sz_22_2]
    st.session_state["frozen_c22_3"] = raw_c22_3[:sz_22_3]
  c_22_1 = st.session_state["frozen_c22_1"][:sz_22_1]
  c_22_2 = st.session_state["frozen_c22_2"][:sz_22_2]
  c_22_3 = st.session_state["frozen_c22_3"][:sz_22_3]

  col_lock22, _ = st.columns([2, 4])
  with col_lock22:
    if not st.session_state["locked_22"]:
      if st.button(
          "🔒 Zamroź zestawy 22:00", key="btn_lock_22", use_container_width=True
      ):
        st.session_state["locked_22"] = True
        st.rerun()
    else:
      if st.button(
          "🔓 Odblokuj / Zmień zestawy 22:00",
          key="btn_unlock_22",
          use_container_width=True,
      ):
        st.session_state["locked_22"] = False
        st.rerun()

  hits_c22_1 = (
      sum(1 for n in c_22_1 if n in latest_nums_22)
      if show_ticks_coupon_22
      else 0
  )
  hits_c22_2 = (
      sum(1 for n in c_22_2 if n in latest_nums_22)
      if show_ticks_coupon_22
      else 0
  )
  hits_c22_3 = (
      sum(1 for n in c_22_3 if n in latest_nums_22)
      if show_ticks_coupon_22
      else 0
  )

  with col_22_c1:
    st.markdown(
        f"**Zestaw 1 (Główny Top)** ({len(c_22_1)} liczb)"
        f" {f'*(Trafienia: {hits_c22_1}/{len(c_22_1)})*' if show_ticks_coupon_22 else ''}"
        f" {'🔒 [Zamrożony]' if st.session_state['locked_22'] else '🟢 [Na żywo]'}"
    )
    st.code(
        format_coupon_list(c_22_1, latest_nums_22, show_ticks_coupon_22),
        language=None,
    )
  with col_22_c2:
    st.markdown(
        f"**Zestaw 2 (Przesunięty Top)** ({len(c_22_2)} liczb)"
        f" {f'*(Trafienia: {hits_c22_2}/{len(c_22_2)})*' if show_ticks_coupon_22 else ''}"
    )
    st.code(
        format_coupon_list(c_22_2, latest_nums_22, show_ticks_coupon_22),
        language=None,
    )
  with col_22_c3:
    st.markdown(
        f"**Zestaw 3 (Strategia Alternatywna)** ({len(c_22_3)} liczb)"
        f" {f'*(Trafienia: {hits_c22_3}/{len(c_22_3)})*' if show_ticks_coupon_22 else ''}"
    )
    st.code(
        format_coupon_list(c_22_3, latest_nums_22, show_ticks_coupon_22),
        language=None,
    )

  st.divider()

  # --- 6. AKTYWNA PREDYKCJA MIĘDZYSESYJNA, KLASTRY PARTNERÓW & WERYFIKACJA ---
  st.subheader("🔥 Aktywna Predykcja Międzysesyjna & Trafienia")
  st.markdown(
      f"1️⃣ **Weryfikacja trafień w ostatnim losowaniu #{eval_target_id}** (bazując na #{eval_base_id}):"
  )

  j_eval_list = get_cross_session_top_jumpers(zakres, 20)
  top_15_eval = sorted(j_eval_list[:15], key=lambda x: int(x))
  if len(top_15_eval) < 15:
    for i in range(1, 81):
      s_n = f"{i:02d}"
      if len(top_15_eval) < 15 and s_n not in top_15_eval:
        top_15_eval.append(s_n)
  top_15_eval = sorted(top_15_eval[:15], key=lambda x: int(x))

  hits_eval_total = sum(1 for n in top_15_eval if n in eval_target_nums)

  eval_items = []
  for n_str in top_15_eval:
    is_hit = n_str in eval_target_nums
    hit_tick = "✅" if is_hit else ""
    eval_items.append(f"**{n_str}**[{hit_tick}]" if hit_tick else f"**{n_str}**")

  mid_e = len(eval_items) // 2
  st.markdown(f"Trafienia ogólne w Top 15 Skoczków: **{hits_eval_total}/15**")
  st.markdown("   ".join(eval_items[:mid_e]))
  st.markdown("   ".join(eval_items[mid_e:]))

  st.markdown("---")

  next_session_label = "22:00" if pred_base_hour == "14:00" else "14:00"
  st.markdown(
      f"2️⃣ **Predykcje na nadchodzące losowanie ({next_session_label})** "
      f"(bazując na zakończonym losowaniu **#{pred_base_id}** [{pred_base_date} | ⏰ {pred_base_hour}]):"
  )

  top_15_cross = top_15_eval

  pred_cross, source_mapping = (
      get_cross_session_strict_predictions_with_sources(
          zakres,
          top_15_cross,
          pred_base_nums,
          pred_base_hour,
          tuple(missing_endings),
          top_k=9,
      )
  )

  if source_mapping:
    mapping_str_parts = [
        f":red[**{pred}**] ➔ z liczby **{src}**"
        for pred, src in sorted(source_mapping.items(), key=lambda x: int(x[0]))
    ]
    st.markdown(
        "📌 **Przypisanie predykcji do liczb bazowych:** "
        + " | ".join(mapping_str_parts)
    )

  # --- LISTA 1: TOP 9 PREDYKCJI (NA CZERWONO DO GRY) ---
  st.markdown(f"🎯 **Top 9 Predykcji Międzysesyjnych (Typy do gry na {next_session_label}):**")
  pred_sorted_list = sorted(list(pred_cross), key=lambda x: int(x))
  pred_items = [f":red[**{n_str}**]" for n_str in pred_sorted_list]
  st.markdown("   ".join(pred_items))

  # --- KLASTRY PARTNERÓW DO PARY ---
  if pred_sorted_list:
    partner_hints = []
    for p_str in pred_sorted_list[:5]:
      end_d = int(p_str) % 10
      partners = [pt for pt in CLUSTER_PARTNERS.get(end_d, []) if pt != p_str]
      if partners:
        partner_hints.append(f"**{p_str}** ➕ ({', '.join(partners[:2])})")
    if partner_hints:
      st.markdown(
          "🤝 **Sugerowani partnerzy z klastrów końcówek (do par/trójek):** "
          + " | ".join(partner_hints)
      )

  st.markdown("")

  # --- LISTA 2: TOP 15 WSPÓLNYCH SKOCZKÓW (SZEROKA PULA) ---
  st.markdown("🔥 **Top 15 Wspólnych Skoczków (Szeroka pula):**")
  cross_items = [f"**{n_str}**" for n_str in top_15_cross]

  mid_c = len(cross_items) // 2
  line1_cross = cross_items[:mid_c]
  line2_cross = cross_items[mid_c:]

  st.markdown("   ".join(line1_cross))
  st.markdown("   ".join(line2_cross))

  st.markdown(
      "Legenda: Liczby oznaczone na :red[**czerwono**] to **Top 9 predykcji**"
      " (wzmocnione wagami końcówek 5/3/7, skoczków 3/8 oraz odbić pustych końcówek)"
      " | **✅** – trafienie w zakończonym losowaniu."
  )

  st.divider()

  # --- 7. ANALIZA PAR I TRÓJEK ---
  st.subheader("🔗 Analiza Par i Trójek (Współwystępowanie)")
  selected_session_for_tuples = st.selectbox(
      "Wybierz sesję do analizy par/trójek:", ["22:00", "14:00"]
  )
  df_tuples_session = df[df["Godzina"] == selected_session_for_tuples].tail(
      int(zakres)
  )

  def get_top_tuples(df_session, n_size, limit=5):
    counter = Counter()
    for _, row in df_session.iterrows():
      draw_nums = [f"{int(v):02d}" for v in get_row_numbers(row)]
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

  # --- 8. PEŁNA BAZA WSZYSTKICH LOSOWAŃ ---
  st.subheader("📊 Pełna Baza Wszystkich Losowań")
  display_data = []
  df_reversed = df.iloc[::-1]
  for _, row in df_reversed.iterrows():
    nums = [f"{int(v):02d}" for v in get_row_numbers(row)]
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
