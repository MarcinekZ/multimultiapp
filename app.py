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


  @st.cache_data
  def get_session_top15(current_zakres, session_time):
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
  def get_session_top_jumpers(current_zakres, session_time, top_n=5):
    sub = df.tail(int(current_zakres))
    sub = sub[sub["Godzina"] == session_time].reset_index(drop=True)
    if len(sub) < 2:
      return []
    counter = Counter()
    for i in range(1, len(sub)):
      prev_nums = set(sub.iloc[i - 1, 3:23].dropna().astype(int))
      curr_nums = set(sub.iloc[i, 3:23].dropna().astype(int))
      for n in prev_nums.intersection(curr_nums):
        counter[n] += 1
    top_j = [f"{n:02d}" for n, _ in counter.most_common(top_n)]
    return sorted(top_j, key=lambda x: int(x))


  even_14, odd_14 = get_session_top15(zakres, "14:00")
  even_22, odd_22 = get_session_top15(zakres, "22:00")

  jumpers_14 = get_session_top_jumpers(zakres, "14:00", 5)
  jumpers_22 = get_session_top_jumpers(zakres, "22:00", 5)


  def get_smart_coupon(session_time, limit, current_zakres, seed_offset=0):
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
    top_freq_sorted = sorted(counts.index.tolist(), key=lambda x: counts[x], reverse=True)
    session_jumpers = get_session_top_jumpers(current_zakres, session_time, 5)

    coupon = []
    # Bierzemy proporcjonalnie skoczków (np. 1 lub 2 w zależności od limitu)
    num_jumpers = min(len(session_jumpers), max(1, limit // 3))
    
    # Rotujemy nieco skoczków dla każdego z 3 zestawów za pomocą seed_offset, żeby zestawy się różniły
    shifted_jumpers = session_jumpers[seed_offset:] + session_jumpers[:seed_offset]
    selected_jumpers = shifted_jumpers[:num_jumpers]
    coupon.extend(selected_jumpers)

    for num in top_freq_sorted:
      if len(coupon) >= limit:
        break
      if num not in coupon:
        coupon.append(num)

    for i in range(1, 81):
      if len(coupon) >= limit:
        break
      s_num = f"{i:02d}"
      if s_num not in coupon:
        coupon.append(s_num)

    return sorted(coupon, key=lambda x: int(x))


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
      f"**🔥 Top 5 Przeskoków (Sesja 14:00 ➡️ 14:00)** *(Trafienia:"
      f" {hits_j14}/5)*:"
      if show_ticks_top15_14
      else "**🔥 Top 5 Przeskoków (Sesja 14:00 ➡️ 14:00):**"
  )
  st.code(
      format_top15_list(jumpers_14, latest_nums_14, show_ticks_top15_14)
      if jumpers_14
      else "Brak danych",
      language=None,
  )

  st.markdown("🎯 **3 Niezależne Zestawy (Sesja 14:00):**")

  # 3 zestawy z osobnymi suwakami
  col_14_s1, col_14_c1 = st.columns([1, 3])
  with col_14_s1:
    sz_14_1 = st.slider("Liczb w Zestawie 1:", 1, 20, 10, key="sz_14_1")
  c_14_1 = get_smart_coupon("14:00", sz_14_1, zakres, seed_offset=0)
  hits_c14_1 = sum(1 for n in c_14_1 if n in latest_nums_14) if show_ticks_coupon_14 else 0
  lbl_14_1 = f"**Zestaw 1** ({sz_14_1} liczb) {f'*(Trafienia: {hits_c14_1}/{sz_14_1})*' if show_ticks_coupon_14 else ''}"
  with col_14_c1:
    st.markdown(lbl_14_1)
    st.code(format_coupon_list(c_14_1, latest_nums_14, show_ticks_coupon_14), language=None)

  col_14_s2, col_14_c2 = st.columns([1, 3])
  with col_14_s2:
    sz_14_2 = st.slider("Liczb w Zestawie 2:", 1, 20, 10, key="sz_14_2")
  c_14_2 = get_smart_coupon("14:00", sz_14_2, zakres, seed_offset=1)
  hits_c14_2 = sum(1 for n in c_14_2 if n in latest_nums_14) if show_ticks_coupon_14 else 0
  lbl_14_2 = f"**Zestaw 2** ({sz_14_2} liczb) {f'*(Trafienia: {hits_c14_2}/{sz_14_2})*' if show_ticks_coupon_14 else ''}"
  with col_14_c2:
    st.markdown(lbl_14_2)
    st.code(format_coupon_list(c_14_2, latest_nums_14, show_ticks_coupon_14), language=None)

  col_14_s3, col_14_c3 = st.columns([1, 3])
  with col_14_s3:
    sz_14_3 = st.slider("Liczb w Zestawie 3:", 1, 20, 10, key="sz_14_3")
  c_14_3 = get_smart_coupon("14:00", sz_14_3, zakres, seed_offset=2)
  hits_c14_3 = sum(1 for n in c_14_3 if n in latest_nums_14) if show_ticks_coupon_14 else 0
  lbl_14_3 = f"**Zestaw 3** ({sz_14_3} liczb) {f'*(Trafienia: {hits_c14_3}/{sz_14_3})*' if show_ticks_coupon_14 else ''}"
  with col_14_c3:
    st.markdown(lbl_14_3)
    st.code(format_coupon_list(c_14_3, latest_nums_14, show_ticks_coupon_14), language=None)

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
      f"**🔥 Top 5 Przeskoków (Sesja 22:00 ➡️ 22:00)** *(Trafienia:"
      f" {hits_j22}/5)*:"
      if show_ticks_top15_22
      else "**🔥 Top 5 Przeskoków (Sesja 22:00 ➡️ 22:00):**"
  )
  st.code(
      format_top15_list(jumpers_22, latest_nums_22, show_ticks_top15_22)
      if jumpers_22
      else "Brak danych",
      language=None,
  )

  st.markdown("🎯 **3 Niezależne Zestawy (Sesja 22:00):**")

  col_22_s1, col_22_c1 = st.columns([1, 3])
  with col_22_s1:
    sz_22_1 = st.slider("Liczb w Zestawie 1:", 1, 20, 10, key="sz_22_1")
  c_22_1 = get_smart_coupon("22:00", sz_22_1, zakres, seed_offset=0)
  hits_c22_1 = sum(1 for n in c_22_1 if n in latest_nums_22) if show_ticks_coupon_22 else 0
  lbl_22_1 = f"**Zestaw 1** ({sz_22_1} liczb) {f'*(Trafienia: {hits_c22_1}/{sz_22_1})*' if show_ticks_coupon_22 else ''}"
  with col_22_c1:
    st.markdown(lbl_22_1)
    st.code(format_coupon_list(c_22_1, latest_nums_22, show_ticks_coupon_22), language=None)

  col_22_s2, col_22_c2 = st.columns([1, 3])
  with col_22_s2:
    sz_22_2 = st.slider("Liczb w Zestawie 2:", 1, 20, 10, key="sz_22_2")
  c_22_2 = get_smart_coupon("22:00", sz_22_2, zakres, seed_offset=1)
  hits_c22_2 = sum(1 for n in c_22_2 if n in latest_nums_22) if show_ticks_coupon_22 else 0
  lbl_22_2 = f"**Zestaw 2** ({sz_22_2} liczb) {f'*(Trafienia: {hits_c22_2}/{sz_22_2})*' if show_ticks_coupon_22 else ''}"
  with col_22_c2:
    st.markdown(lbl_22_2)
    st.code(format_coupon_list(c_22_2, latest_nums_22, show_ticks_coupon_22), language=None)

  col_22_s3, col_22_c3 = st.columns([1, 3])
  with col_22_s3:
    sz_22_3 = st.slider("Liczb w Zestawie 3:", 1, 20, 10, key="sz_22_3")
  c_22_3 = get_smart_coupon("22:00", sz_22_3, zakres, seed_offset=2)
  hits_c22_3 = sum(1 for n in c_22_3 if n in latest_nums_22) if show_ticks_coupon_22 else 0
  lbl_22_3 = f"**Zestaw 3** ({sz_22_3} liczb) {f'*(Trafienia: {hits_c22_3}/{sz_22_3})*' if show_ticks_coupon_22 else ''}"
  with col_22_c3:
    st.markdown(lbl_22_3)
    st.code(format_coupon_list(c_22_3, latest_nums_22, show_ticks_coupon_22), language=None)

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
        if pd.notna(val) and str(val).strip()
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
