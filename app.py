from collections import Counter
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


@st.cache_data(ttl=300)
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

  df_live = None
  try:
    session = requests.Session()
    api_url = (
        "https://www.lotto.pl/api/v1/gametype/results?gameType=MultiMulti&size=1000"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.lotto.pl/multi-multi/wyniki",
    }
    res = session.get(api_url, headers=headers, timeout=3)

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
        if not nums:
          nums = item.get("resultsJson", [])
        if not nums:
          nums = item.get("drawResults", [])

        if nums:
          row = [draw_id, formatted_date, time_str] + list(nums)[:20]
          rows.append(row)

      if rows:
        df_live = pd.DataFrame(rows)
  except Exception:
    pass

  dfs = [df_fallback]
  if df_live is not None and not df_live.empty:
    dfs.append(df_live)
  if df_csv is not None and not df_csv.empty:
    dfs.append(df_csv)

  df = pd.concat(dfs, ignore_index=True)

  if df.shape[1] >= 23:
    df = df.iloc[:, :23]
    cols = ["ID", "Data", "Godzina"] + [f"L{i}" for i in range(1, 21)]
    df.columns = cols
  else:
    current_cols = ["ID", "Data", "Godzina"] + [
        f"L{i}" for i in range(1, df.shape[1] - 2)
    ]
    df.columns = current_cols[: df.shape[1]]

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

if st.sidebar.button("🔄 Odśwież i zsynchronizuj", use_container_width=True):
  st.cache_data.clear()
  st.rerun()

if df is not None and not df.empty:
  st.sidebar.success(f"🟢 Baza aktywna (Łącznie losowań: {len(df)})")
  total_draws = len(df)

  # --- 1. ARCHIWUM OSTATNICH LOSOWAŃ ---
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

  # --- 2. USTAWIENIA ANALIZY / SUWAK ---
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
  last_date_14 = ""
  if not df_14_all.empty:
    latest_draw_14 = df_14_all.iloc[-1]
    last_date_14 = str(latest_draw_14["Data"]).strip()
    latest_nums_14 = {
        f"{int(str(v).replace('.0', '').strip()):02d}"
        if str(v).replace(".0", "").strip().isdigit()
        else str(v).replace(".0", "").strip()
        for v in latest_draw_14.iloc[3:].values
        if pd.notna(v) and str(v).strip()
    }

  latest_nums_22 = set()
  last_date_22 = ""
  if not df_22_all.empty:
    latest_draw_22 = df_22_all.iloc[-1]
    last_date_22 = str(latest_draw_22["Data"]).strip()
    latest_nums_22 = {
        f"{int(str(v).replace('.0', '').strip()):02d}"
        if str(v).replace(".0", "").strip().isdigit()
        else str(v).strip()
        for v in latest_draw_22.iloc[3:].values
        if pd.notna(v) and str(v).strip()
    }

  today_str = datetime.datetime.now().strftime("%d.%m.%Y")

  show_ticks_top15_14 = True if latest_nums_14 else False
  show_ticks_top15_22 = True if latest_nums_22 else False

  show_ticks_coupon_14 = (
      True if last_date_14 == today_str and latest_nums_14 else False
  )
  show_ticks_coupon_22 = (
      True if last_date_22 == today_str and latest_nums_22 else False
  )


  def format_top15_list(num_list, session_latest_nums, show_ticks):
    res = []
    for n_str in num_list:
      if show_ticks and n_str in session_latest_nums:
        res.append(f"{n_str}✅")
      else:
        res.append(f"{n_str}")
    if len(res) > 8:
      line1 = " ".join(res[:8])
      line2 = " ".join(res[8:])
      return f"{line1}\n{line2}"
    return " ".join(res)


  def format_coupon_list(num_list, session_latest_nums, show_ticks):
    res = []
    for n in num_list:
      n_clean = (
          f"{int(n):02d}" if str(n).replace(".0", "").isdigit() else str(n)
      )
      if show_ticks and n_clean in session_latest_nums:
        res.append(f"{n_clean}✅")
      else:
        res.append(f"{n_clean}")
    return " ".join(res)


  # --- WSZYSTKIE FUNKCJE OBLICZENIOWE W CACHED ---
  @st.cache_data
  def get_session_top15(session_time, current_zakres):
    df_session = df.tail(int(current_zakres))
    df_session = df_session[df_session["Godzina"] == session_time]
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

    even_sorted = sorted(even_counts.head(15).index.tolist(), key=lambda x: int(x))
    odd_sorted = sorted(odd_counts.head(15).index.tolist(), key=lambda x: int(x))

    return even_sorted, odd_sorted


  @st.cache_data
  def get_session_top_jumpers(session_time, top_n=8):
    sub = df[df["Godzina"] == session_time].reset_index(drop=True)
    if len(sub) < 5:
      return []
    counter = Counter()
    for i in range(1, len(sub)):
      prev_nums = set(sub.iloc[i - 1, 3:23].dropna().astype(int))
      curr_nums = set(sub.iloc[i, 3:23].dropna().astype(int))
      for n in prev_nums.intersection(curr_nums):
        counter[n] += 1
    top_j = [f"{n:02d}" for n, _ in counter.most_common(top_n)]
    return sorted(top_j, key=lambda x: int(x))


  even_14, odd_14 = get_session_top15("14:00", zakres)
  even_22, odd_22 = get_session_top15("22:00", zakres)

  jumpers_14 = get_session_top_jumpers("14:00", 8)
  jumpers_22 = get_session_top_jumpers("22:00", 8)


  def get_smart_coupon(session_time, limit, current_zakres):
    df_session = df.tail(int(current_zakres))
    df_session = df_session[df_session["Godzina"] == session_time]
    if df_session.empty:
      return [f"{i:02d}" for i in range(1, limit + 1)]

    all_session_nums = []
    for row_vals in df_session.iloc[:, 3:].values:
      for val in row_vals:
        if pd.notna(val) and str(val).strip():
          cleaned_v = str(val).replace(".0", "").strip()
          if cleaned_v.isdigit():
            all_session_nums.append(f"{int(cleaned_v):02d}")

    counts = pd.Series(all_session_nums).value_counts()
    session_jumpers = set(get_session_top_jumpers(session_time, 8))

    combined = {}
    for num in [f"{n:02d}" for n in range(1, 81)]:
      freq = counts.get(num, 1)
      bonus = 50 if num in session_jumpers else 0
      combined[num] = freq + bonus

    sorted_best = sorted(
        combined.keys(), key=lambda x: combined[x], reverse=True
    )
    return sorted(sorted_best[:limit], key=lambda x: int(x))


  # --- 3. TOP 15 ORAZ TOP PRZESKOKÓW (14:00) ---
  st.subheader("☀️ Godzina 14:00 (Statystyki Historyczne)")

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
      f"**Top 15 Parzyste** *(Ostatnie losowanie [{last_date_14}] - Trafienia:"
      f" {hits_14_e}/15)*:"
      if show_ticks_top15_14
      else "**Top 15 Parzyste:**"
  )
  st.code(
      format_top15_list(even_14, latest_nums_14, show_ticks_top15_14)
      if even_14
      else "Brak danych",
      language=None,
  )

  st.markdown(
      f"**Top 15 Nieparzyste** *(Ostatnie losowanie [{last_date_14}] - Trafienia:"
      f" {hits_14_o}/15)*:"
      if show_ticks_top15_14
      else "**Top 15 Nieparzyste:**"
  )
  st.code(
      format_top15_list(odd_14, latest_nums_14, show_ticks_top15_14)
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
      f"**🔥 Top 8 Przeskoków (Sesja 14:00 ➡️ 14:00)** *(Trafienia:"
      f" {hits_j14}/8)*:"
      if show_ticks_top15_14
      else "**🔥 Top 8 Przeskoków (Sesja 14:00 ➡️ 14:00):**"
  )
  st.code(
      format_top15_list(jumpers_14, latest_nums_14, show_ticks_top15_14)
      if jumpers_14
      else "Brak danych",
      language=None,
  )

  st.markdown("🎯 **Zakłady Wygenerowane (Sesja 14:00):**")

  col_s14_1, col_s14_2, col_s14_3 = st.columns(3)
  with col_s14_1:
    sz_10_14 = st.slider(
        "Suwak duży (14:00):", 1, 10, 10, key="slider_10_14"
    )
  with col_s14_2:
    sz_5_14 = st.slider(
        "Suwak średni (14:00):", 1, 5, 5, key="slider_5_14"
    )
  with col_s14_3:
    sz_3_14 = st.slider("Suwak mały (14:00):", 1, 3, 3, key="slider_3_14")

  c_10_14 = get_smart_coupon("14:00", sz_10_14, zakres)
  c_5_14 = get_smart_coupon("14:00", sz_5_14, zakres)
  c_3_14 = get_smart_coupon("14:00", sz_3_14, zakres)

  hits_c10_14 = (
      sum(1 for n in c_10_14 if n in latest_nums_14)
      if show_ticks_coupon_14
      else 0
  )
  hits_c5_14 = (
      sum(1 for n in c_5_14 if n in latest_nums_14)
      if show_ticks_coupon_14
      else 0
  )
  hits_c3_14 = (
      sum(1 for n in c_3_14 if n in latest_nums_14)
      if show_ticks_coupon_14
      else 0
  )

  label_10_14 = (
      f"*Zakład na {sz_10_14} liczb (Trafienia:"
      f" {hits_c10_14}/{sz_10_14}):*"
      if show_ticks_coupon_14
      else f"*Zakład na {sz_10_14} liczb:*"
  )
  st.markdown(label_10_14)
  st.code(
      format_coupon_list(c_10_14, latest_nums_14, show_ticks_coupon_14),
      language=None,
  )

  col_14_a, col_14_b = st.columns(2)
  with col_14_a:
    label_5_14 = (
        f"*Zakład na {sz_5_14} liczb (Trafienia:"
        f" {hits_c5_14}/{sz_5_14}):*"
        if show_ticks_coupon_14
        else f"*Zakład na {sz_5_14} liczb:*"
    )
    st.markdown(label_5_14)
    st.code(
        format_coupon_list(c_5_14, latest_nums_14, show_ticks_coupon_14),
        language=None,
    )
  with col_14_b:
    label_3_14 = (
        f"*Zakład na {sz_3_14} liczb (Trafienia:"
        f" {hits_c3_14}/{sz_3_14}):*"
        if show_ticks_coupon_14
        else f"*Zakład na {sz_3_14} liczb:*"
    )
    st.markdown(label_3_14)
    st.code(
        format_coupon_list(c_3_14, latest_nums_14, show_ticks_coupon_14),
        language=None,
    )

  st.divider()

  # --- 4. TOP 15 ORAZ TOP PRZESKOKÓW (22:00) ---
  st.subheader("🌙 Godzina 22:00 (Statystyki Historyczne)")

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
      "**Top 15 Parzyste: `✅ [Rekomendowany Priorytet]`**"
      f" *(Ostatnie losowanie [{last_date_22}] - Trafienia:"
      f" {hits_22_e}/15)*:"
      if show_ticks_top15_22
      else "**Top 15 Parzyste: `✅ [Rekomendowany Priorytet]`**:"
  )
  st.code(
      format_top15_list(even_22, latest_nums_22, show_ticks_top15_22)
      if even_22
      else "Brak danych",
      language=None,
  )

  st.markdown(
      f"**Top 15 Nieparzyste** *(Ostatnie losowanie [{last_date_22}] - Trafienia:"
      f" {hits_22_o}/15)*:"
      if show_ticks_top15_22
      else "**Top 15 Nieparzyste:**"
  )
  st.code(
      format_top15_list(odd_22, latest_nums_22, show_ticks_top15_22)
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
      f"**🔥 Top 8 Przeskoków (Sesja 22:00 ➡️ 22:00)** *(Trafienia:"
      f" {hits_j22}/8)*:"
      if show_ticks_top15_22
      else "**🔥 Top 8 Przeskoków (Sesja 22:00 ➡️ 22:00):**"
  )
  st.code(
      format_top15_list(jumpers_22, latest_nums_22, show_ticks_top15_22)
      if jumpers_22
      else "Brak danych",
      language=None,
  )

  st.markdown("🎯 **Zakłady Wygenerowane (Sesja 22:00):**")

  col_s22_1, col_s22_2, col_s22_3 = st.columns(3)
  with col_s22_1:
    sz_10_22 = st.slider(
        "Suwak duży (22:00):", 1, 10, 10, key="slider_10_22"
    )
  with col_s22_2:
    sz_5_22 = st.slider(
        "Suwak średni (22:00):", 1, 5, 5, key="slider_5_22"
    )
  with col_s22_3:
    sz_3_22 = st.slider("Suwak mały (22:00):", 1, 3, 3, key="slider_3_22")

  c_10_22 = get_smart_coupon("22:00", sz_10_22, zakres)
  c_5_22 = get_smart_coupon("22:00", sz_5_22, zakres)
  c_3_22 = get_smart_coupon("22:00", sz_3_22, zakres)

  hits_c10_22 = (
      sum(1 for n in c_10_22 if n in latest_nums_22)
      if show_ticks_coupon_22
      else 0
  )
  hits_c5_22 = (
      sum(1 for n in c_5_22 if n in latest_nums_22)
      if show_ticks_coupon_22
      else 0
  )
  hits_c3_22 = (
      sum(1 for n in c_3_22 if n in latest_nums_22)
      if show_ticks_coupon_22
      else 0
  )

  label_10_22 = (
      f"*Zakład na {sz_10_22} liczb (Parzyste + Dekady) (Trafienia:"
      f" {hits_c10_22}/{sz_10_22}):*"
      if show_ticks_coupon_22
      else f"*Zakład na {sz_10_22} liczb (Parzyste + Dekady):*"
  )
  st.markdown(label_10_22)
  st.code(
      format_coupon_list(c_10_22, latest_nums_22, show_ticks_coupon_22),
      language=None,
  )

  col_22_a, col_22_b = st.columns(2)
  with col_22_a:
    label_5_22 = (
        f"*Zakład na {sz_5_22} liczb (Mieszane + Zimne) (Trafienia:"
        f" {hits_c5_22}/{sz_5_22}):*"
        if show_ticks_coupon_22
        else f"*Zakład na {sz_5_22} liczb (Mieszane + Zimne):*"
    )
    st.markdown(label_5_22)
    st.code(
        format_coupon_list(c_5_22, latest_nums_22, show_ticks_coupon_22),
        language=None,
    )
  with col_22_b:
    label_3_22 = (
        f"*Zakład na {sz_3_22} liczb (Mieszane) (Trafienia:"
        f" {hits_c3_22}/{sz_3_22}):*"
        if show_ticks_coupon_22
        else f"*Zakład na {sz_3_22} liczb (Mieszane):*"
    )
    st.markdown(label_3_22)
    st.code(
        format_coupon_list(c_3_22, latest_nums_22, show_ticks_coupon_22),
        language=None,
    )

  st.divider()

  # --- 5. ANALIZA PAR I TRÓJEK ---
  st.subheader("🔗 Analiza Par i Trójek (Współwystępowanie)")
  selected_session_for_tuples = st.selectbox(
      "Wybierz sesję do analizy par/trójek:", ["22:00", "14:00"]
  )
  df_tuples_session = df[df["Godzina"] == selected_session_for_tuples].tail(
      int(zakres)
  )


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
