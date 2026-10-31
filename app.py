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
    res = session.get(api_url, headers=headers, timeout=5)

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
  csv_files = glob.glob("*.csv")
  for fname in csv_files:
    try:
      df_csv = pd.read_csv(fname, header=None)
      if not df_csv.empty:
        break
    except Exception:
      continue

  if df_live is not None and not df_live.empty:
    st.sidebar.success("🟢 Status: Live API (Zsynchronizowane)")
    df = df_live
  elif df_csv is not None and not df_csv.empty:
    st.sidebar.error(
        "🔴 Status: Plik lokalny CSV (Tryb awaryjny - stabilny)"
    )
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
  today_str = datetime.date.today().strftime("%d.%m.%Y")

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

  # Ostatnie losowanie 14:00 w bazie
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

  # Ostatnie losowanie 22:00 w bazie
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

  show_ticks_top15_14 = True if latest_nums_14 else False
  show_ticks_top15_22 = True if latest_nums_22 else False

  # Dla 14:00 kupony mają ptaszki tylko jeśli dzisiejsze losowanie 14:00 się odbyło
  show_ticks_coupon_14 = True if (last_date_14 == today_str) else False

  # Dla 22:00 kupony pokazują ptaszki dla ostatniego ukończonego wieczornego losowania w bazie (np. z wczoraj)
  # Dopóki dzisiejsze 22:00 nie zostanie pobrane/zaktualizowane, pokazuje wczorajsze trafienia, a po dzisiejszym losowaniu i aktualizacji – czekają na nowe.
  show_ticks_coupon_22 = True if latest_nums_22 else False


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


  def get_session_top15(session_time):
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

    even_sorted = sorted(even_counts.head(15).index.tolist(), key=lambda x: int(x))
    odd_sorted = sorted(odd_counts.head(15).index.tolist(), key=lambda x: int(x))

    return even_sorted, odd_sorted


  even_14, odd_14 = get_session_top15("14:00")
  even_22, odd_22 = get_session_top15("22:00")


  # --- ROZBUDOWANY GENERATOR: PRZESKOKI + ZIMNE LICZBY + ROZPIĘTOŚĆ DEKAD ---
  def get_followers_with_filters(session_time, limit, seed):
    df_session = df[df["Godzina"] == session_time]
    if len(df_session) < 5:
      return [f"{i:02d}" for i in range(1, limit + 1)]

    recent_session_rows = df_session.tail(4)
    recent_session_nums = set()
    for row_vals in recent_session_rows.iloc[:, 3:].values:
      for v in row_vals:
        if pd.notna(v) and str(v).replace(".0", "").strip().isdigit():
          recent_session_nums.add(
              f"{int(str(v).replace('.0', '').strip()):02d}"
          )

    all_80 = [f"{n:02d}" for n in range(1, 81)]
    cold_pool = {n for n in all_80 if n not in recent_session_nums}

    df_analyzed_session = df_session.tail(int(zakres) + 2)
    rows = df_analyzed_session.iloc[:, 3:].values
    followers_score = Counter()

    for i in range(1, len(rows) - 1):
      d_prev = set([
          f"{int(str(v).replace('.0', '').strip()):02d}"
          for v in rows[i - 1]
          if pd.notna(v) and str(v).replace(".0", "").strip().isdigit()
      ])
      d_curr = set([
          f"{int(str(v).replace('.0', '').strip()):02d}"
          for v in rows[i]
          if pd.notna(v) and str(v).replace(".0", "").strip().isdigit()
      ])
      d_next = [
          f"{int(str(v).replace('.0', '').strip()):02d}"
          for v in rows[i + 1]
          if pd.notna(v) and str(v).replace(".0", "").strip().isdigit()
      ]

      jumped = d_prev.intersection(d_curr)
      if jumped:
        for num in d_next:
          followers_score[num] += len(jumped)

    combined_scores = {}
    for n in all_80:
      base_score = followers_score.get(n, 1)
      if n in cold_pool:
        combined_scores[n] = base_score * 1.5
      else:
        combined_scores[n] = base_score

    sorted_candidates = sorted(
        all_80, key=lambda x: combined_scores[x], reverse=True
    )

    rng = random.Random(seed)
    selected = []

    def get_decade(num_str):
      return (int(num_str) - 1) // 10

    if session_time == "22:00":
      if limit == 10:
        even_pool = [c for c in sorted_candidates if int(c) % 2 == 0]
        decade_counts = {d: 0 for d in range(8)}
        for c in even_pool:
          dec = get_decade(c)
          if decade_counts[dec] < 2 and len(selected) < 10:
            selected.append(c)
            decade_counts[dec] += 1
        for c in even_pool:
          if len(selected) < 10 and c not in selected:
            selected.append(c)
      elif limit == 5:
        even_pool = [c for c in sorted_candidates if int(c) % 2 == 0]
        odd_pool = [c for c in sorted_candidates if int(c) % 2 != 0]
        selected = even_pool[:3] + odd_pool[:2]
    else:
      decade_counts = {d: 0 for d in range(8)}
      for c in sorted_candidates:
        dec = get_decade(c)
        if decade_counts[dec] < (2 if limit == 10 else 1) and len(selected) < limit:
          selected.append(c)
          decade_counts[dec] += 1
      for c in sorted_candidates:
        if len(selected) < limit and c not in selected:
          selected.append(c)

    return sorted(selected, key=lambda x: int(x))[:limit]


  # --- 3. TOP 15 ORAZ KUPONY PO PRZESKOKACH (14:00 ➡️ 14:00) ---
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

  st.markdown(f"**Top 15 Parzyste** *(Trafienia: {hits_14_e}/15)*:")
  st.code(
      format_top15_list(even_14, latest_nums_14, show_ticks_top15_14)
      if even_14
      else "Brak danych",
      language=None,
  )
  st.markdown(f"**Top 15 Nieparzyste** *(Trafienia: {hits_14_o}/15)*:")
  st.code(
      format_top15_list(odd_14, latest_nums_14, show_ticks_top15_14)
      if odd_14
      else "Brak danych",
      language=None,
  )

  st.markdown(
      "🎯 **Liczby najczęściej występujące PO PRZESKOKACH + Filtry (Cykl 14:00"
      " ➡️ 14:00):**"
  )

  c_10_14 = get_followers_with_filters("14:00", 10, 100)
  c_5_14 = get_followers_with_filters("14:00", 5, 200)

  hits_c10_14 = (
      sum(
          1
          for n in c_10_14
          if (
              f"{int(n):02d}"
              if str(n).replace(".0", "").isdigit()
              else str(n)
          )
          in latest_nums_14
      )
      if show_ticks_coupon_14
      else 0
  )
  hits_c5_14 = (
      sum(
          1
          for n in c_5_14
          if (
              f"{int(n):02d}"
              if str(n).replace(".0", "").isdigit()
              else str(n)
          )
          in latest_nums_14
      )
      if show_ticks_coupon_14
      else 0
  )

  col_t14_1, col_t14_2 = st.columns(2)
  with col_t14_1:
    label_10_14 = (
        f"*Zakład na 10 liczb (Trafienia: {hits_c10_14}/10):*"
        if show_ticks_coupon_14
        else "*Zakład na 10 liczb (Oczekuje na dzisiejsze losowanie):*"
    )
    st.markdown(label_10_14)
    st.code(
        format_coupon_list(
            c_10_14, latest_nums_14, show_ticks_coupon_14
        ),
        language=None,
    )

  with col_t14_2:
    label_5_14 = (
        f"*Zakład na 5 liczb (Trafienia: {hits_c5_14}/5):*"
        if show_ticks_coupon_14
        else "*Zakład na 5 liczb (Oczekuje na dzisiejsze losowanie):*"
    )
    st.markdown(label_5_14)
    st.code(
        format_coupon_list(c_5_14, latest_nums_14, show_ticks_coupon_14),
        language=None,
    )

  st.divider()

  # --- 4. TOP 15 ORAZ KUPONY PO PRZESKOKACH (22:00 ➡️ 22:00) ---
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
      f" *(Trafienia: {hits_22_e}/15)*:"
  )
  st.code(
      format_top15_list(even_22, latest_nums_22, show_ticks_top15_22)
      if even_22
      else "Brak danych",
      language=None,
  )
  st.markdown(f"**Top 15 Nieparzyste** *(Trafienia: {hits_22_o}/15)*:")
  st.code(
      format_top15_list(odd_22, latest_nums_22, show_ticks_top15_22)
      if odd_22
      else "Brak danych",
      language=None,
  )

  st.markdown(
      "🎯 **Liczby najczęściej występujące PO PRZESKOKACH + Filtry (Cykl 22:00"
      " ➡️ 22:00):**"
  )

  c_10_22 = get_followers_with_filters("22:00", 10, 300)
  c_5_22 = get_followers_with_filters("22:00", 5, 400)

  hits_c10_22 = (
      sum(
          1
          for n in c_10_22
          if (
              f"{int(n):02d}"
              if str(n).replace(".0", "").isdigit()
              else str(n)
          )
          in latest_nums_22
      )
      if show_ticks_coupon_22
      else 0
  )
  hits_c5_22 = (
      sum(
          1
          for n in c_5_22
          if (
              f"{int(n):02d}"
              if str(n).replace(".0", "").isdigit()
              else str(n)
          )
          in latest_nums_22
      )
      if show_ticks_coupon_22
      else 0
  )

  col_t22_1, col_t22_2 = st.columns(2)
  with col_t22_1:
    label_10_22 = f"*Zakład na 10 liczb (Parzyste + Dekady) (Trafienia: {hits_c10_22}/10):*"
    st.markdown(label_10_22)
    st.code(
        format_coupon_list(
            c_10_22, latest_nums_22, show_ticks_coupon_22
        ),
        language=None,
    )

  with col_t22_2:
    label_5_22 = f"*Zakład na 5 liczb (Mieszane + Zimne) (Trafienia: {hits_c5_22}/5):*"
    st.markdown(label_5_22)
    st.code(
        format_coupon_list(c_5_22, latest_nums_22, show_ticks_coupon_22),
        language=None,
    )

  st.divider()

  # --- 5. ANALIZA PAR I TRÓJEK ---
  st.subheader("🔗 Analiza Par i Trójek (Współwystępowanie)")
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
