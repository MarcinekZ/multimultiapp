from collections import Counter, defaultdict
import datetime
import glob
from itertools import combinations
import json
import math
import os
import random
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Mobilny Panel Analityczny Ekipy", page_icon="🎯", layout="wide"
)

STATE_FILE = "panel_state.json"


def load_persistent_state():
  state = {}
  # 1. Odczyt z pliku na dysku
  if os.path.exists(STATE_FILE):
    try:
      with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, dict):
          state.update(data)
    except Exception:
      pass

  # 2. Odczyt z parametrów URL (zapasowy, gdyby kontener Streamlit Cloud się zrestartował)
  try:
    qp = st.query_params
    if "l14" in qp and "locked_14" not in state:
      state["locked_14"] = qp["l14"] == "1"
    if "l22" in qp and "locked_22" not in state:
      state["locked_22"] = qp["l22"] == "1"
    for k_url, k_st in [
        ("c14_1", "frozen_c14_1"),
        ("c14_2", "frozen_c14_2"),
        ("c14_3", "frozen_c14_3"),
        ("c22_1", "frozen_c22_1"),
        ("c22_2", "frozen_c22_2"),
        ("c22_3", "frozen_c22_3"),
    ]:
      if k_url in qp and qp[k_url] and not state.get(k_st):
        state[k_st] = [x for x in qp[k_url].split("-") if x]
  except Exception:
    pass

  return state


def save_persistent_state():
  keys_to_save = [
      "locked_14",
      "frozen_c14_1",
      "frozen_c14_2",
      "frozen_c14_3",
      "locked_22",
      "frozen_c22_1",
      "frozen_c22_2",
      "frozen_c22_3",
      "zakres_wspolny_val",
      "zakres_14_val",
      "zakres_22_val",
      "sz_14_1",
      "sz_14_2",
      "sz_14_3",
      "sz_22_1",
      "sz_22_2",
      "sz_22_3",
      "fusion_coupon_size",
      "prio_endings",
  ]
  payload = {}
  for k in keys_to_save:
    if k in st.session_state:
      val = st.session_state[k]
      if isinstance(val, (bool, int, float, str, list)):
        payload[k] = val

  try:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
      json.dump(payload, f, ensure_ascii=False, indent=2)
  except Exception:
    pass

  # Synchronizacja z adresem URL (chroni przed utratą po resecie sesji w chmurze)
  try:
    st.query_params["l14"] = "1" if payload.get("locked_14") else "0"
    st.query_params["l22"] = "1" if payload.get("locked_22") else "0"
    if payload.get("locked_14"):
      st.query_params["c14_1"] = "-".join(payload.get("frozen_c14_1", []))
      st.query_params["c14_2"] = "-".join(payload.get("frozen_c14_2", []))
      st.query_params["c14_3"] = "-".join(payload.get("frozen_c14_3", []))
    else:
      for k in ["c14_1", "c14_2", "c14_3"]:
        if k in st.query_params:
          del st.query_params[k]

    if payload.get("locked_22"):
      st.query_params["c22_1"] = "-".join(payload.get("frozen_c22_1", []))
      st.query_params["c22_2"] = "-".join(payload.get("frozen_c22_2", []))
      st.query_params["c22_3"] = "-".join(payload.get("frozen_c22_3", []))
    else:
      for k in ["c22_1", "c22_2", "c22_3"]:
        if k in st.query_params:
          del st.query_params[k]
  except Exception:
    pass


# Inicjalizacja trwałego stanu przed wyrenderowaniem widżetów
if "state_initialized" not in st.session_state:
  saved_state = load_persistent_state()
  for k, v in saved_state.items():
    st.session_state[k] = v
  st.session_state["state_initialized"] = True


def read_flexible_csv(source):
  """Wczytuje CSV niezależnie od separatora (, lub ; lub tabulator), kodowania czy nagłówka."""
  import io
  if hasattr(source, "seek"):
    source.seek(0)
    raw_bytes = source.read()
    source.seek(0)
  else:
    with open(source, "rb") as f:
      raw_bytes = f.read()

  text = None
  for enc in ("utf-8-sig", "utf-8", "cp1250", "latin1"):
    try:
      text = raw_bytes.decode(enc)
      break
    except Exception:
      continue
  if text is None:
    text = raw_bytes.decode("utf-8", errors="replace")

  lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
  if not lines:
    return pd.DataFrame()

  first_line = lines[0]
  sep = ";" if first_line.count(";") > first_line.count(",") else ","
  if "\t" in first_line and first_line.count("\t") > max(first_line.count(","), first_line.count(";")):
    sep = "\t"

  df_raw = pd.read_csv(io.StringIO(text), sep=sep, header=None, engine="python")
  return df_raw


def parse_and_clean_df(dfs):
  cleaned_parts = []
  for d in dfs:
    if d is None or d.empty:
      continue
    temp = d.copy()
    temp.columns = list(range(temp.shape[1]))
    cleaned_parts.append(temp)

  if not cleaned_parts:
    return pd.DataFrame()

  df = pd.concat(cleaned_parts, ignore_index=True)

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
        .drop_duplicates(subset=["ID_int"], keep="last")
        .drop(columns=["ID_int"])
        .reset_index(drop=True)
    )
  except Exception:
    pass

  return df


def _extract_lotto_items(payload):
  """Rekurencyjnie wyciąga listę losowań z dowolnej struktury JSON zwracanej przez API Lotto lub mirror."""
  found = []
  if isinstance(payload, list):
    for el in payload:
      found.extend(_extract_lotto_items(el))
  elif isinstance(payload, dict):
    has_id = any(k in payload for k in ("drawSystemId", "drawId", "id", "numer"))
    has_nums = any(k in payload for k in ("resultsJson", "numbers", "results", "liczby"))
    if has_id and has_nums:
      found.append(payload)
    for v in payload.values():
      if isinstance(v, (dict, list)):
        found.extend(_extract_lotto_items(v))
  return found


def fetch_lotto_api_rows():
  """Pobiera najnowsze wyniki Multi Multi z otwartego API Lotto oraz alternatywnych źródeł (HTML/CSV/JSON)."""
  import re
  session = requests.Session()
  headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*",
      "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
      "Referer": "https://www.lotto.pl/multi-multi/wyniki-i-wygrane",
      "Origin": "https://www.lotto.pl",
  }

  # Rozgrzanie sesji ciasteczkami strony głównej Lotto (pomaga ominąć podstawową weryfikację sesji)
  try:
    session.get("https://www.lotto.pl/multi-multi/wyniki-i-wygrane", headers=headers, timeout=4)
  except Exception:
    pass

  endpoints = [
      "https://www.lotto.pl/api/lotteries/draw-results/by-gametype?game=MultiMulti&index=1&size=30&sort=drawDate&order=DESC",
      "https://www.lotto.pl/api/lotteries/draw-results/by-gametype?gameType=MultiMulti&index=1&size=30&sort=drawDate&order=DESC",
      "https://developers.lotto.pl/api/open/v1/lotteries/draw-results/by-gametype?gameType=MultiMulti&index=1&size=30&sort=drawDate&order=DESC",
      "https://www.lotto.pl/api/v1/gametype/results?gameType=MultiMulti&size=30",
      "https://api.lotto.pl/v1/gametype/results?gameType=MultiMulti&size=30",
  ]

  rows = []
  seen_ids = set()

  for url in endpoints:
    try:
      res = session.get(url, headers=headers, timeout=6)
      if res.status_code != 200:
        continue
      data = res.json()
      items = _extract_lotto_items(data)

      for item in items:
        if not isinstance(item, dict):
          continue
        draw_id = item.get("drawSystemId") or item.get("drawId") or item.get("id") or item.get("numer")
        if draw_id is None:
          continue
        draw_id_str = str(draw_id).strip()
        if not draw_id_str.isdigit() or draw_id_str in seen_ids:
          continue

        draw_date_raw = str(item.get("drawDate") or item.get("date") or item.get("data") or "")
        results_list = item.get("results") or []
        nums = []
        if isinstance(results_list, list) and results_list:
          first_res = results_list[0]
          if isinstance(first_res, dict):
            nums = first_res.get("resultsJson") or first_res.get("numbers") or []
          elif isinstance(first_res, (int, str)):
            nums = results_list
        if not nums:
          nums = item.get("resultsJson") or item.get("numbers") or item.get("liczby") or []

        clean_nums = [int(x) for x in nums if str(x).strip().isdigit() and 1 <= int(x) <= 80]
        if len(clean_nums) >= 20:
          date_str = draw_date_raw[:10]
          hour_str = "14:00"
          try:
            if "T" in draw_date_raw:
              dt_part, tm_part = draw_date_raw.split("T", 1)
              parts_d = dt_part.split("-")
              if len(parts_d) == 3:
                date_str = f"{parts_d[2]}.{parts_d[1]}.{parts_d[0]}"
              h_val = int(tm_part.split(":")[0])
              hour_str = "14:00" if h_val < 17 else "22:00"
            elif ":" in draw_date_raw:
              h_match = re.search(r"(\d{1,2}):\d{2}", draw_date_raw)
              if h_match:
                hour_str = "14:00" if int(h_match.group(1)) < 18 else "22:00"
          except Exception:
            pass
          seen_ids.add(draw_id_str)
          rows.append([draw_id_str, date_str, hour_str] + clean_nums[:20])
      if rows:
        break
    except Exception:
      continue

  # Zapasowe źródło: otwarte archiwum tekstowe/CSV Multi Multi (mbnet / multipasko), gdy główne API Lotto blokuje IP chmury
  if not rows:
    fallback_urls = [
        "http://www.mbnet.com.pl/ml.txt",
        "https://www.mbnet.com.pl/ml.txt",
    ]
    for fb_url in fallback_urls:
      try:
        r_fb = session.get(fb_url, headers={"User-Agent": headers["User-Agent"]}, timeout=6)
        if r_fb.status_code == 200 and len(r_fb.text) > 500:
          lines_fb = [ln.strip() for ln in r_fb.text.splitlines() if ln.strip()][-40:]
          for ln in lines_fb:
            # Format mbnet: 17149. 15.11.2026 04,08,09,...
            m = re.match(r"^(\d+)\.\s*(\d{2}\.\d{2}\.\d{4})\s+([\d,]+)", ln)
            if m:
              d_id = m.group(1)
              d_dt = m.group(2)
              d_nums = [int(x) for x in m.group(3).split(",") if x.strip().isdigit() and 1 <= int(x) <= 80]
              if len(d_nums) >= 20 and d_id not in seen_ids:
                # W Multi Multi losowania nieparzyste/parzyste lub wg kolejności tego samego dnia
                same_day_count = sum(1 for r in rows if r[1] == d_dt)
                h_str = "14:00" if same_day_count == 0 else "22:00"
                seen_ids.add(d_id)
                rows.append([d_id, d_dt, h_str] + d_nums[:20])
          if rows:
            # Korekta godziny dla ostatniego dnia, jeśli w danym dniu było tylko 1 losowanie lub na podstawie parzystości ID względem bazy
            break
      except Exception:
        continue

  if rows:
    return pd.DataFrame(rows)
  return pd.DataFrame()


@st.cache_data
def load_disk_data(file_signatures):
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

  dfs = [df_fallback]
  csv_files = sorted(glob.glob("*.csv"))
  for fname in csv_files:
    try:
      temp_df = read_flexible_csv(fname)
      if not temp_df.empty:
        dfs.append(temp_df)
    except Exception:
      continue

  return parse_and_clean_df(dfs)


st.title("📱 Mobilny Panel Analityczny Ekipy")

# --- PANEL BOCZNY: WGRYWANIE CSV, RĘCZNE DOPISANIE I SYNCHRONIZACJA ---
uploaded_csv = st.sidebar.file_uploader(
    "📂 Wgraj nowy plik CSV z wynikami",
    type=["csv", "txt"],
    help="Wrzuć najnowszy eksport wyników (np. multi_multi (22).csv), aby natychmiast zaktualizować bazę.",
)

if st.sidebar.button("🔄 Odśwież i zsynchronizuj z API", use_container_width=True):
  with st.spinner("Pobieranie najnowszych wyników z sieci..."):
    df_api = fetch_lotto_api_rows()
    if not df_api.empty:
      st.session_state["api_fetched_df"] = df_api
      try:
        if os.path.exists("api_synced_draws.csv"):
          old_api_df = read_flexible_csv("api_synced_draws.csv")
          merged_api_df = parse_and_clean_df([old_api_df, df_api])
        else:
          merged_api_df = parse_and_clean_df([df_api])
        merged_api_df.to_csv("api_synced_draws.csv", index=False, header=False)
      except Exception:
        pass
      latest_api_id = str(df_api.iloc[-1][0])
      st.session_state["sync_toast"] = ("success", f"✅ Zsynchronizowano! Najnowsze pobrane losowanie: #{latest_api_id}")
    else:
      st.session_state["sync_toast"] = (
          "warning",
          "⚠️ Serwer Lotto.pl chwilowo blokuje połączenie z chmury. Użyj wgrania CSV lub szybkiego wpisu poniżej."
      )
  save_persistent_state()
  st.cache_data.clear()
  st.rerun()

if "sync_toast" in st.session_state:
  t_type, t_msg = st.session_state.pop("sync_toast")
  if t_type == "success":
    st.sidebar.success(t_msg)
  else:
    st.sidebar.warning(t_msg)

disk_csv_sigs = tuple(
    (f, os.path.getmtime(f), os.path.getsize(f))
    for f in sorted(glob.glob("*.csv"))
    if os.path.exists(f)
)
df = load_disk_data(disk_csv_sigs)

# Dołączenie danych z API, jeśli zostały pobrane
if "api_fetched_df" in st.session_state and not st.session_state["api_fetched_df"].empty:
  df = parse_and_clean_df([df, st.session_state["api_fetched_df"]])

# Dołączenie wgranego pliku CSV (z trwałym zapisem na dysku)
if uploaded_csv is not None:
  try:
    df_up = read_flexible_csv(uploaded_csv)
    if not df_up.empty:
      df = parse_and_clean_df([df, df_up])
      # Zapisz na dysku jako uploaded_latest.csv, aby przetrwało odświeżenie strony
      try:
        df_up.to_csv("uploaded_latest.csv", index=False, header=False)
      except Exception:
        pass
      st.sidebar.success(f"📥 Załadowano i zapisano plik: **{uploaded_csv.name}**")
    else:
      st.sidebar.error("⚠️ Wgrany plik CSV jest pusty.")
  except Exception as e:
    st.sidebar.error(f"Błąd odczytu wgranego CSV: {e}")

# --- AWARYJNE / SZYBKIE DOPISANIE LOSOWANIA RĘCZNIE ---
with st.sidebar.expander("✍️ Szybkie dopisanie pojedynczego losowania"):
  last_known_id = int(df.iloc[-1]["ID"]) if (df is not None and not df.empty and str(df.iloc[-1]["ID"]).isdigit()) else 17149
  manual_id = st.number_input("Numer losowania (ID):", min_value=1, value=last_known_id + 1, step=1)
  manual_date = st.text_input("Data (DD.MM.RRRR):", value=datetime.date.today().strftime("%d.%m.%Y"))
  manual_hour = st.selectbox("Godzina:", ["14:00", "22:00"])
  manual_nums_str = st.text_input("20 wylosowanych liczb (oddzielone spacją lub przecinkiem):", placeholder="np. 03 11 15 22 ...")
  if st.button("➕ Dodaj losowanie do bazy", use_container_width=True):
    raw_tokens = [t.strip() for t in manual_nums_str.replace(",", " ").replace(";", " ").split() if t.strip().isdigit()]
    nums_int = [int(t) for t in raw_tokens if 1 <= int(t) <= 80]
    # Zachowaj unikalne 20 liczb w kolejności wpisania
    unique_20 = []
    for n in nums_int:
      if n not in unique_20:
        unique_20.append(n)
    if len(unique_20) == 20:
      new_row_df = pd.DataFrame([[str(int(manual_id)), manual_date.strip(), manual_hour] + unique_20])
      try:
        if os.path.exists("manual_draws.csv"):
          old_m = read_flexible_csv("manual_draws.csv")
          combined_m = pd.concat([old_m, new_row_df], ignore_index=True)
        else:
          combined_m = new_row_df
        combined_m.to_csv("manual_draws.csv", index=False, header=False)
      except Exception:
        pass
      if "manual_rows_list" not in st.session_state:
        st.session_state["manual_rows_list"] = []
      st.session_state["manual_rows_list"].append(new_row_df)
      st.cache_data.clear()
      st.rerun()
    else:
      st.error(f"Wpisano {len(unique_20)} unikalnych liczb z zakresu 1–80. Wymagane jest dokładnie 20 liczb!")

if "manual_rows_list" in st.session_state and st.session_state["manual_rows_list"]:
  df = parse_and_clean_df([df] + st.session_state["manual_rows_list"])

if df is not None and not df.empty:
  latest_entry = df.iloc[-1]
  st.sidebar.success(
      f"🟢 Baza aktywna (Łącznie losowań: {len(df)})\n\n"
      f"Ostatni wpis: **#{latest_entry['ID']}** ({latest_entry['Data']} | {latest_entry['Godzina']})"
  )
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

  # --- STAŁE STATYSTYCZNE Z ANALIZY PEŁNEJ BAZY ---
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

  df_14_all = df[df["Godzina"] == "14:00"].reset_index(drop=True)
  df_22_all = df[df["Godzina"] == "22:00"].reset_index(drop=True)
  total_14 = len(df_14_all)
  total_22 = len(df_22_all)

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

  # --- 2. RADAR KOŃCÓWEK, PUSTYCH KOŃCÓWEK (91.23%) ORAZ ANOMALII PARZYSTOŚCI ---
  st.subheader("🧲 Radar Końcówek, Pustych Końcówek i Anomalii")

  latest_overall = df.iloc[-1]
  latest_id = str(latest_overall["ID"]).strip()
  latest_date = str(latest_overall["Data"]).strip()
  latest_hour = str(latest_overall["Godzina"]).strip()
  latest_overall_nums_int = [int(v) for v in get_row_numbers(latest_overall)]

  present_endings = {n % 10 for n in latest_overall_nums_int}
  missing_endings = sorted(list(set(range(10)) - present_endings))

  ending_counts_latest = Counter(n % 10 for n in latest_overall_nums_int)
  dominant_endings = [
      f"końcówka **{end}** ({cnt} szt.)"
      for end, cnt in ending_counts_latest.most_common(3)
      if cnt >= 3
  ]

  even_latest = [n for n in latest_overall_nums_int if n % 2 == 0]
  odd_latest = [n for n in latest_overall_nums_int if n % 2 != 0]
  low_latest = [n for n in latest_overall_nums_int if n <= 40]
  high_latest = [n for n in latest_overall_nums_int if n > 40]

  col_rad1, col_rad2 = st.columns(2)
  with col_rad1:
    if missing_endings:
      missing_str = ", ".join([f"**{e}**" for e in missing_endings])
      st.info(
          f"🚨 **Brakujące końcówki w #{latest_id} ({latest_hour}):** {missing_str}\n\n"
          f"Statystyka bazy: gdy końcówka nie padnie wcale (0 szt.), "
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
        f"⚖️ **Bilans #{latest_id}:** Parzyste **{len(even_latest)}** / Nieparzyste **{len(odd_latest)}** | "
        f"Niskie (1–40): **{len(low_latest)}** / Wysokie (41–80): **{len(high_latest)}**\n\n"
        f"🏆 **Liderzy całej bazy:** końcówki **5**, **3**, **7** | **Skoczkowie 1:1:** **3**, **8**."
    )

  parity_bias = None
  if len(odd_latest) >= 14:
    parity_bias = "EVEN"
    st.error(
        f"⚠️ **ANOMALIA SKRAJNA W #{latest_id}:** Wylosowano aż **{len(odd_latest)} liczb nieparzystych** "
        f"i tylko **{len(even_latest)} parzystych** (zjawisko rzadsze niż 1% w historii!). "
        f"W kolejnym losowaniu włączono **kontra-balans dla liczb parzystych**."
    )
  elif len(even_latest) >= 14:
    parity_bias = "ODD"
    st.error(
        f"⚠️ **ANOMALIA SKRAJNA W #{latest_id}:** Wylosowano aż **{len(even_latest)} liczb parzystych** "
        f"i tylko **{len(odd_latest)} nieparzystych** (zjawisko rzadsze niż 1% w historii!). "
        f"W kolejnym losowaniu włączono **kontra-balans dla liczb nieparzystych**."
    )

  st.divider()

  # --- 3. TRZY NIEZALEŻNE SUWAKI (WSPÓLNY + SESJA 14:00 + SESJA 22:00) ---
  st.subheader("⚙️ Ustawienia Analizy Statystycznej (3 Niezależne Suwaki)")

  def render_independent_slider(label, state_key, max_val, default_val, btn_prefix):
    presets = [1, 5, 8, 10, 15, 16, 20, 30, 40, 50, 100, 200, max_val]
    presets = sorted(list(set([opt for opt in presets if 1 <= opt <= max_val])))
    if not presets:
      presets = [1]
    if max_val not in presets and max_val >= 1:
      presets.append(max_val)

    if state_key not in st.session_state:
      st.session_state[state_key] = default_val if default_val <= max_val else presets[-1]
    if st.session_state[state_key] > max_val:
      st.session_state[state_key] = max_val

    st.markdown(f"**{label}**")
    c_m, c_s, c_p = st.columns([1, 5, 1])
    with c_m:
      if st.button("➖", use_container_width=True, key=f"{btn_prefix}_minus"):
        if st.session_state[state_key] > 1:
          st.session_state[state_key] -= 1
          save_persistent_state()
          st.rerun()
    with c_p:
      if st.button("➕", use_container_width=True, key=f"{btn_prefix}_plus"):
        if st.session_state[state_key] < max_val:
          st.session_state[state_key] += 1
          save_persistent_state()
          st.rerun()

    cur_v = st.session_state[state_key]
    opts = sorted(list(set(presets + [cur_v])))
    with c_s:
      chosen = st.select_slider(
          label,
          options=opts,
          value=cur_v,
          format_func=lambda x: f"Wszystkie ({max_val})" if x == max_val else f"{x} losowań",
          key=state_key,
          on_change=save_persistent_state,
          label_visibility="collapsed",
      )
    return chosen

  zakres_wspolny = render_independent_slider(
      "🌐 Suwak Wspólny (Predykcja Międzysesyjna 14:00 ↔ 22:00 i Wspólni Skoczkowie):",
      "zakres_wspolny_val",
      total_draws,
      30,
      "wsp",
  )

  col_sl14, col_sl22 = st.columns(2)
  with col_sl14:
    zakres_14 = render_independent_slider(
        "☀️ Suwak Sesji 14:00 (tylko losowania 14:00):",
        "zakres_14_val",
        max(1, total_14),
        16,
        "s14",
    )
  with col_sl22:
    zakres_22 = render_independent_slider(
        "🌙 Suwak Sesji 22:00 (tylko losowania 22:00):",
        "zakres_22_val",
        max(1, total_22),
        16,
        "s22",
    )

  col_opt1, col_opt2 = st.columns([2, 2])
  with col_opt1:
    st.caption(
        f"Aktywne horyzonty: Wspólny = **{zakres_wspolny}** | "
        f"14:00 = **{zakres_14}** | 22:00 = **{zakres_22}**"
    )
  with col_opt2:
    if "prio_endings" not in st.session_state:
      st.session_state["prio_endings"] = True
    prioritize_top_endings = st.toggle(
        "🔥 Priorytetyzuj Top Końcówki (5, 3, 7) oraz Odbicia w zestawach",
        key="prio_endings",
        on_change=save_persistent_state,
    )

  st.divider()

  # --- FUNKCJE POMOCNICZE DLA SESJI I PREDYKCJI ---
  latest_nums_14 = set()
  last_id_14 = ""
  last_date_14 = ""
  latest_nums_14_int = []
  if not df_14_all.empty:
    latest_draw_14 = df_14_all.iloc[-1]
    last_id_14 = str(latest_draw_14["ID"]).strip()
    last_date_14 = str(latest_draw_14["Data"]).strip()
    latest_nums_14_int = [int(v) for v in get_row_numbers(latest_draw_14)]
    latest_nums_14 = {f"{n:02d}" for n in latest_nums_14_int}

  latest_nums_22 = set()
  last_id_22 = ""
  last_date_22 = ""
  latest_nums_22_int = []
  if not df_22_all.empty:
    latest_draw_22 = df_22_all.iloc[-1]
    last_id_22 = str(latest_draw_22["ID"]).strip()
    last_date_22 = str(latest_draw_22["Data"]).strip()
    latest_nums_22_int = [int(v) for v in get_row_numbers(latest_draw_22)]
    latest_nums_22 = {f"{n:02d}" for n in latest_nums_22_int}

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
      combined_suffix = f"[{pred_tick}{hit_tick}]" if (pred_tick or hit_tick) else ""
      res.append(f"{n_str}{combined_suffix}")

    if len(res) > 8:
      return f"{' '.join(res[:8])}\n{' '.join(res[8:])}"
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

  def get_session_top15_by_session_slider(session_zakres, session_time):
    df_s = df_14_all if session_time == "14:00" else df_22_all
    df_session = df_s.tail(int(session_zakres))
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

  def get_session_top_jumpers_by_slider(session_zakres, session_time, top_n=15):
    df_s = df_14_all if session_time == "14:00" else df_22_all
    sub = df_s.tail(int(session_zakres)).reset_index(drop=True)
    if len(sub) < 2:
      return []
    counter = Counter()
    for i in range(1, len(sub)):
      prev_nums = {int(v) for v in get_row_numbers(sub.iloc[i - 1])}
      curr_nums = {int(v) for v in get_row_numbers(sub.iloc[i])}
      for n in prev_nums.intersection(curr_nums):
        weight = 1.15 if (n % 10) in JUMPER_ENDINGS else 1.0
        counter[n] += weight
    top_j = [f"{n:02d}" for n, _ in counter.most_common(top_n)]
    return sorted(top_j, key=lambda x: int(x))

  def get_sleeping_numbers(df_target_pool, top_n=10):
    if df_target_pool.empty:
      return []
    last_seen = {}
    total_len = len(df_target_pool)
    for idx in range(total_len - 1, -1, -1):
      row_nums = {int(v) for v in get_row_numbers(df_target_pool.iloc[idx])}
      for n in row_nums:
        if n not in last_seen:
          last_seen[n] = (total_len - 1) - idx
      if len(last_seen) == 80:
        break
    for n in range(1, 81):
      if n not in last_seen:
        last_seen[n] = total_len
    sorted_sleepers = sorted(last_seen.items(), key=lambda x: (-x[1], x[0]))
    return sorted_sleepers[:top_n]

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

  def compute_transition_predictions(
      sub_df,
      candidate_list,
      base_nums_set,
      base_hour="14:00",
      missing_ends=(),
      top_k=9,
      intra_session=False,
      p_bias=None,
  ):
    if len(sub_df) < 2 or not base_nums_set:
      return set(), {}

    transition_scores = defaultdict(float)
    mapping_sources = {}

    jumper_source_counter = defaultdict(Counter)
    for i in range(1, len(sub_df)):
      p_nums = {int(v) for v in get_row_numbers(sub_df.iloc[i - 1])}
      c_nums = {int(v) for v in get_row_numbers(sub_df.iloc[i])}
      jumpers = p_nums.intersection(c_nums)
      for j in jumpers:
        for p in p_nums:
          if p != j:
            jumper_source_counter[j][p] += 1

    for i in range(1, len(sub_df)):
      prev_nums = {int(v) for v in get_row_numbers(sub_df.iloc[i - 1])}
      curr_nums = {int(v) for v in get_row_numbers(sub_df.iloc[i])}
      jumpers = prev_nums.intersection(curr_nums)

      active_overlap = prev_nums.intersection(base_nums_set)
      if active_overlap:
        for j in jumpers:
          j_str = f"{j:02d}"
          if not candidate_list or j_str in candidate_list:
            score = float(len(active_overlap))
            if (j % 10) in TOP_ENDINGS:
              score *= 3.5
            if (j % 10) in JUMPER_ENDINGS:
              score *= 1.10
            if (j % 10) in missing_ends:
              score *= 1.25
            if p_bias == "EVEN" and (j % 2 == 0):
              score *= 1.30
            elif p_bias == "ODD" and (j % 2 != 0):
              score *= 1.30
            transition_scores[j_str] += score

    if intra_session:
      for src_num in base_nums_set:
        s_str = f"{src_num:02d}"
        if not candidate_list or s_str in candidate_list:
          bonus = 1.8
          if (src_num % 10) in TOP_ENDINGS:
            bonus *= 1.5
          transition_scores[s_str] += bonus
          if s_str not in mapping_sources:
            mapping_sources[s_str] = f"{s_str} (powtórka 1:1)"
    else:
      strong_map = (
          STRONG_TRANSITIONS_14_TO_22
          if base_hour == "14:00"
          else STRONG_TRANSITIONS_22_TO_14
      )
      for src_num in base_nums_set:
        if src_num in strong_map:
          for target_num in strong_map[src_num]:
            t_str = f"{target_num:02d}"
            if not candidate_list or t_str in candidate_list:
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
            if src in base_nums_set
        }
        if valid_sources:
          best_src = max(valid_sources, key=valid_sources.get)
          mapping_sources[pred_str] = f"{best_src:02d}"
        else:
          mapping_sources[pred_str] = "hist."
      else:
        mapping_sources[pred_str] = "hist."

    return set(top_predicted_list), mapping_sources

  def get_distinct_coupons(
      session_time, limit, session_zakres, use_endings_boost=True, missing_ends=(), p_bias=None
  ):
    df_s = df_14_all if session_time == "14:00" else df_22_all
    df_session = df_s.tail(int(session_zakres))
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
      n_i = int(n_str)
      end = n_i % 10
      mult = 1.0
      if end in TOP_ENDINGS:
        mult += 0.25
      if end in missing_ends:
        mult += 0.35
      if p_bias == "EVEN" and (n_i % 2 == 0):
        mult += 0.20
      elif p_bias == "ODD" and (n_i % 2 != 0):
        mult += 0.20
      return base_cnt * mult

    top_freq = sorted(
        counts.index.tolist(), key=lambda x: score_num(x), reverse=True
    )

    set1, set2, set3 = [], [], []
    for n in top_freq:
      if len(set1) < limit and n not in set1:
        set1.append(n)
    for n in (top_freq[4:] + top_freq[:4]):
      if len(set2) < limit and n not in set2:
        set2.append(n)
    for n in (top_freq[8:] + top_freq[:8]):
      if len(set3) < limit and n not in set3:
        set3.append(n)

    for i in range(1, 81):
      s_num = f"{i:02d}"
      if len(set1) < limit and s_num not in set1:
        set1.append(s_num)
      if len(set2) < limit and s_num not in set2:
        set2.append(s_num)
      if len(set3) < limit and s_num not in set3:
        set3.append(s_num)

    # Nie sortujemy przed zwróceniem, aby zachować kolejność rankingu przy skracaniu do 1..10!
    return set1[:limit], set2[:limit], set3[:limit]

  # --- DOMYŚLNE WARTOŚCI STANU ZAMROŻENIA (JEŚLI NIE BYŁO W PLIKU/URL) ---
  for key_name, default_val in [
      ("locked_14", False),
      ("frozen_c14_1", []),
      ("frozen_c14_2", []),
      ("frozen_c14_3", []),
      ("locked_22", False),
      ("frozen_c22_1", []),
      ("frozen_c22_2", []),
      ("frozen_c22_3", []),
      ("sz_14_1", 8),
      ("sz_14_2", 8),
      ("sz_14_3", 8),
      ("sz_22_1", 8),
      ("sz_22_2", 8),
      ("sz_22_3", 8),
  ]:
    if key_name not in st.session_state:
      st.session_state[key_name] = default_val

  # Obliczenia dla 14:00 i 22:00 z ich własnych suwaków
  even_14, odd_14 = get_session_top15_by_session_slider(zakres_14, "14:00")
  even_22, odd_22 = get_session_top15_by_session_slider(zakres_22, "22:00")

  jumpers_14_pool = get_session_top_jumpers_by_slider(zakres_14, "14:00", 15)
  jumpers_14 = jumpers_14_pool[:5]

  jumpers_22_pool = get_session_top_jumpers_by_slider(zakres_22, "22:00", 15)
  jumpers_22 = jumpers_22_pool[:5]

  prev_nums_14 = set()
  if len(df_14_all) >= 2:
    prev_nums_14 = {int(v) for v in get_row_numbers(df_14_all.iloc[-2])}

  prev_nums_22 = set()
  if len(df_22_all) >= 2:
    prev_nums_22 = {int(v) for v in get_row_numbers(df_22_all.iloc[-2])}

  # =========================================================================
  # 4. GODZINA 14:00 (STATYSTYKI + DEDYKOWANA PREDYKCJA 14:00 ➔ 14:00)
  # =========================================================================
  st.subheader(f"☀️ Godzina 14:00 (Zakres suwaka: {zakres_14} losowań 14:00)")

  sub_14_df = df_14_all.tail(int(zakres_14)).reset_index(drop=True)
  pred_even_14 = compute_transition_predictions(
      sub_14_df, even_14, prev_nums_14, "14:00", tuple(missing_endings), top_k=3, intra_session=True, p_bias=parity_bias
  )[0]
  pred_odd_14 = compute_transition_predictions(
      sub_14_df, odd_14, prev_nums_14, "14:00", tuple(missing_endings), top_k=3, intra_session=True, p_bias=parity_bias
  )[0]

  hits_14_e = sum(1 for n in even_14 if n in latest_nums_14) if show_ticks_top15_14 else 0
  hits_14_o = sum(1 for n in odd_14 if n in latest_nums_14) if show_ticks_top15_14 else 0

  st.markdown(
      f"**Top 15 Parzyste (Top 3 Predykcje 🎯 i Trafienia ✅)** *(Ostatnie"
      f" losowanie [{last_date_14}] - Trafienia: {hits_14_e}/15)*:"
      if show_ticks_top15_14
      else "**Top 15 Parzyste (Top 3 Predykcje 🎯):**"
  )
  st.code(
      format_top15_list_strict_pred(even_14, latest_nums_14, show_ticks_top15_14, pred_even_14)
      if even_14 else "Brak danych",
      language=None,
  )

  st.markdown(
      f"**Top 15 Nieparzyste (Top 3 Predykcje 🎯 i Trafienia ✅)** *(Ostatnie"
      f" losowanie [{last_date_14}] - Trafienia: {hits_14_o}/15)*:"
      if show_ticks_top15_14
      else "**Top 15 Nieparzyste (Top 3 Predykcje 🎯):**"
  )
  st.code(
      format_top15_list_strict_pred(odd_14, latest_nums_14, show_ticks_top15_14, pred_odd_14)
      if odd_14 else "Brak danych",
      language=None,
  )

  hits_j14 = sum(1 for n in jumpers_14 if n in latest_nums_14) if show_ticks_top15_14 else 0
  st.markdown(
      f"**🔥 Top 5 Przeskoków (Sesja 14:00 ➡️ 14:00)** *(Trafienia: {hits_j14}/5)*:"
      if show_ticks_top15_14
      else "**🔥 Top 5 Przeskoków (Sesja 14:00 ➡️ 14:00):**"
  )
  st.code(
      format_top15_list_strict_pred(jumpers_14, latest_nums_14, show_ticks_top15_14, set())
      if jumpers_14 else "Brak danych",
      language=None,
  )

  # --- DEDYKOWANA PREDYKCJA WEWNĄTRZSESYJNA 14:00 ➔ 14:00 (TOP 9) ---
  missing_14 = sorted(list(set(range(10)) - {n % 10 for n in latest_nums_14_int}))
  pred_14_to_14, map_14_to_14 = compute_transition_predictions(
      sub_14_df,
      jumpers_14_pool,
      set(latest_nums_14_int),
      "14:00",
      tuple(missing_14),
      top_k=9,
      intra_session=True,
      p_bias=parity_bias,
  )
  pred_14_to_14_sorted = sorted(list(pred_14_to_14), key=lambda x: int(x))

  st.markdown(
      f"☀️ **Predykcja Wewnątrzsesyjna 14:00 ➔ 14:00 (Top 9 typów na kolejną 14:00)** "
      f"*(na bazie #{last_id_14} [{last_date_14}])*"
  )
  if pred_14_to_14_sorted:
    st.markdown("   ".join([f":red[**{n}**]" for n in pred_14_to_14_sorted]))
    if map_14_to_14:
      m14_parts = [
          f":red[**{p}**] ➔ z **{s}**"
          for p, s in sorted(map_14_to_14.items(), key=lambda x: int(x[0]))
      ]
      st.caption("📌 Źródła 14:00 ➔ 14:00: " + " | ".join(m14_parts))

  # --- ŚPIOCHY 14:00 ---
  sleepers_14 = get_sleeping_numbers(df_14_all, 8)
  if sleepers_14:
    sl14_str = " | ".join([
        f":red[**{n:02d}**] ({g} los. temu)" if (n % 10) in TOP_ENDINGS else f"**{n:02d}** ({g} los. temu)"
        for n, g in sleepers_14
    ])
    st.caption(f"💤 **Najdłużej nieobecne w sesji 14:00 (Śpiochy):** {sl14_str}")

  # --- ZESTAWY 14:00 (Z TRWAŁYM ZAMRAŻANIEM DO PLIKU + URL) ---
  st.markdown("🎯 **3 Niezależne Zestawy (Sesja 14:00):**")

  raw_c14_1, raw_c14_2, raw_c14_3 = get_distinct_coupons(
      "14:00",
      10,
      zakres_14,
      prioritize_top_endings,
      tuple(missing_14),
      parity_bias,
  )
  if not st.session_state["locked_14"] or not st.session_state["frozen_c14_1"]:
    st.session_state["frozen_c14_1"] = raw_c14_1[:10]
    st.session_state["frozen_c14_2"] = raw_c14_2[:10]
    st.session_state["frozen_c14_3"] = raw_c14_3[:10]

  col_14_s1, col_14_c1 = st.columns([1, 3])
  with col_14_s1:
    sz_14_1 = st.slider("Zestaw 1 (1-10):", 1, 10, key="sz_14_1", on_change=save_persistent_state)
  c_14_1 = sorted(st.session_state["frozen_c14_1"][:sz_14_1], key=lambda x: int(x))
  hits_c14_1 = sum(1 for n in c_14_1 if n in latest_nums_14) if show_ticks_coupon_14 else 0
  with col_14_c1:
    st.markdown(
        f"**Zestaw 1 (Główny Top)** ({len(c_14_1)} liczb)"
        f" {f'*(Trafienia: {hits_c14_1}/{len(c_14_1)})*' if show_ticks_coupon_14 else ''}"
        f" {'🔒 [Zamrożony]' if st.session_state['locked_14'] else '🟢 [Na żywo]'}"
    )
    st.code(format_coupon_list(c_14_1, latest_nums_14, show_ticks_coupon_14), language=None)

  col_14_s2, col_14_c2 = st.columns([1, 3])
  with col_14_s2:
    sz_14_2 = st.slider("Zestaw 2 (1-10):", 1, 10, key="sz_14_2", on_change=save_persistent_state)
  c_14_2 = sorted(st.session_state["frozen_c14_2"][:sz_14_2], key=lambda x: int(x))
  hits_c14_2 = sum(1 for n in c_14_2 if n in latest_nums_14) if show_ticks_coupon_14 else 0
  with col_14_c2:
    st.markdown(
        f"**Zestaw 2 (Przesunięty Top)** ({len(c_14_2)} liczb)"
        f" {f'*(Trafienia: {hits_c14_2}/{len(c_14_2)})*' if show_ticks_coupon_14 else ''}"
        f" {'🔒 [Zamrożony]' if st.session_state['locked_14'] else '🟢 [Na żywo]'}"
    )
    st.code(format_coupon_list(c_14_2, latest_nums_14, show_ticks_coupon_14), language=None)

  col_14_s3, col_14_c3 = st.columns([1, 3])
  with col_14_s3:
    sz_14_3 = st.slider("Zestaw 3 (1-10):", 1, 10, key="sz_14_3", on_change=save_persistent_state)
  c_14_3 = sorted(st.session_state["frozen_c14_3"][:sz_14_3], key=lambda x: int(x))
  hits_c14_3 = sum(1 for n in c_14_3 if n in latest_nums_14) if show_ticks_coupon_14 else 0
  with col_14_c3:
    st.markdown(
        f"**Zestaw 3 (Strategia Alternatywna)** ({len(c_14_3)} liczb)"
        f" {f'*(Trafienia: {hits_c14_3}/{len(c_14_3)})*' if show_ticks_coupon_14 else ''}"
        f" {'🔒 [Zamrożony]' if st.session_state['locked_14'] else '🟢 [Na żywo]'}"
    )
    st.code(format_coupon_list(c_14_3, latest_nums_14, show_ticks_coupon_14), language=None)

  col_lock14, _ = st.columns([2, 4])
  with col_lock14:
    if not st.session_state["locked_14"]:
      if st.button("🔒 Zamroź zestawy 14:00 (na stałe)", key="btn_lock_14", use_container_width=True):
        st.session_state["locked_14"] = True
        st.session_state["frozen_c14_1"] = raw_c14_1[:10]
        st.session_state["frozen_c14_2"] = raw_c14_2[:10]
        st.session_state["frozen_c14_3"] = raw_c14_3[:10]
        save_persistent_state()
        st.rerun()
    else:
      if st.button("🔓 Odblokuj / Zmień zestawy 14:00", key="btn_unlock_14", use_container_width=True):
        st.session_state["locked_14"] = False
        save_persistent_state()
        st.rerun()

  st.divider()

  # =========================================================================
  # 5. GODZINA 22:00 (STATYSTYKI + DEDYKOWANA PREDYKCJA 22:00 ➔ 22:00)
  # =========================================================================
  st.subheader(f"🌙 Godzina 22:00 (Zakres suwaka: {zakres_22} losowań 22:00)")

  sub_22_df = df_22_all.tail(int(zakres_22)).reset_index(drop=True)
  pred_even_22 = compute_transition_predictions(
      sub_22_df, even_22, prev_nums_22, "22:00", tuple(missing_endings), top_k=3, intra_session=True, p_bias=parity_bias
  )[0]
  pred_odd_22 = compute_transition_predictions(
      sub_22_df, odd_22, prev_nums_22, "22:00", tuple(missing_endings), top_k=3, intra_session=True, p_bias=parity_bias
  )[0]

  hits_22_e = sum(1 for n in even_22 if n in latest_nums_22) if show_ticks_top15_22 else 0
  hits_22_o = sum(1 for n in odd_22 if n in latest_nums_22) if show_ticks_top15_22 else 0

  st.markdown(
      "**Top 15 Parzyste (Top 3 Predykcje 🎯 i Trafienia ✅):**"
      f" *(Ostatnie losowanie [{last_date_22}] - Trafienia: {hits_22_e}/15)*:"
      if show_ticks_top15_22
      else "**Top 15 Parzyste (Top 3 Predykcje 🎯):**"
  )
  st.code(
      format_top15_list_strict_pred(even_22, latest_nums_22, show_ticks_top15_22, pred_even_22)
      if even_22 else "Brak danych",
      language=None,
  )

  st.markdown(
      f"**Top 15 Nieparzyste (Top 3 Predykcje 🎯 i Trafienia ✅)** *(Ostatnie"
      f" losowanie [{last_date_22}] - Trafienia: {hits_22_o}/15)*:"
      if show_ticks_top15_22
      else "**Top 15 Nieparzyste (Top 3 Predykcje 🎯):**"
  )
  st.code(
      format_top15_list_strict_pred(odd_22, latest_nums_22, show_ticks_top15_22, pred_odd_22)
      if odd_22 else "Brak danych",
      language=None,
  )

  hits_j22 = sum(1 for n in jumpers_22 if n in latest_nums_22) if show_ticks_top15_22 else 0
  st.markdown(
      f"**🔥 Top 5 Przeskoków (Sesja 22:00 ➡️ 22:00)** *(Trafienia: {hits_j22}/5)*:"
      if show_ticks_top15_22
      else "**🔥 Top 5 Przeskoków (Sesja 22:00 ➡️ 22:00):**"
  )
  st.code(
      format_top15_list_strict_pred(jumpers_22, latest_nums_22, show_ticks_top15_22, set())
      if jumpers_22 else "Brak danych",
      language=None,
  )

  # --- DEDYKOWANA PREDYKCJA WEWNĄTRZSESYJNA 22:00 ➔ 22:00 (TOP 9) ---
  missing_22 = sorted(list(set(range(10)) - {n % 10 for n in latest_nums_22_int}))
  pred_22_to_22, map_22_to_22 = compute_transition_predictions(
      sub_22_df,
      jumpers_22_pool,
      set(latest_nums_22_int),
      "22:00",
      tuple(missing_22),
      top_k=9,
      intra_session=True,
      p_bias=parity_bias,
  )
  pred_22_to_22_sorted = sorted(list(pred_22_to_22), key=lambda x: int(x))

  st.markdown(
      f"🌙 **Predykcja Wewnątrzsesyjna 22:00 ➔ 22:00 (Top 9 typów na kolejną 22:00)** "
      f"*(na bazie #{last_id_22} [{last_date_22}])*"
  )
  if pred_22_to_22_sorted:
    st.markdown("   ".join([f":red[**{n}**]" for n in pred_22_to_22_sorted]))
    if map_22_to_22:
      m22_parts = [
          f":red[**{p}**] ➔ z **{s}**"
          for p, s in sorted(map_22_to_22.items(), key=lambda x: int(x[0]))
      ]
      st.caption("📌 Źródła 22:00 ➔ 22:00: " + " | ".join(m22_parts))

  # --- ŚPIOCHY 22:00 ---
  sleepers_22 = get_sleeping_numbers(df_22_all, 8)
  if sleepers_22:
    sl22_str = " | ".join([
        f":red[**{n:02d}**] ({g} los. temu)" if (n % 10) in TOP_ENDINGS else f"**{n:02d}** ({g} los. temu)"
        for n, g in sleepers_22
    ])
    st.caption(f"💤 **Najdłużej nieobecne w sesji 22:00 (Śpiochy):** {sl22_str}")

  # --- ZESTAWY 22:00 (Z TRWAŁYM ZAMRAŻANIEM DO PLIKU + URL) ---
  st.markdown("🎯 **3 Niezależne Zestawy (Sesja 22:00):**")

  raw_c22_1, raw_c22_2, raw_c22_3 = get_distinct_coupons(
      "22:00",
      10,
      zakres_22,
      prioritize_top_endings,
      tuple(missing_22),
      parity_bias,
  )
  if not st.session_state["locked_22"] or not st.session_state["frozen_c22_1"]:
    st.session_state["frozen_c22_1"] = raw_c22_1[:10]
    st.session_state["frozen_c22_2"] = raw_c22_2[:10]
    st.session_state["frozen_c22_3"] = raw_c22_3[:10]

  col_22_s1, col_22_c1 = st.columns([1, 3])
  with col_22_s1:
    sz_22_1 = st.slider("Zestaw 1 (1-10):", 1, 10, key="sz_22_1", on_change=save_persistent_state)
  c_22_1 = sorted(st.session_state["frozen_c22_1"][:sz_22_1], key=lambda x: int(x))
  hits_c22_1 = sum(1 for n in c_22_1 if n in latest_nums_22) if show_ticks_coupon_22 else 0
  with col_22_c1:
    st.markdown(
        f"**Zestaw 1 (Główny Top)** ({len(c_22_1)} liczb)"
        f" {f'*(Trafienia: {hits_c22_1}/{len(c_22_1)})*' if show_ticks_coupon_22 else ''}"
        f" {'🔒 [Zamrożony]' if st.session_state['locked_22'] else '🟢 [Na żywo]'}"
    )
    st.code(format_coupon_list(c_22_1, latest_nums_22, show_ticks_coupon_22), language=None)

  col_22_s2, col_22_c2 = st.columns([1, 3])
  with col_22_s2:
    sz_22_2 = st.slider("Zestaw 2 (1-10):", 1, 10, key="sz_22_2", on_change=save_persistent_state)
  c_22_2 = sorted(st.session_state["frozen_c22_2"][:sz_22_2], key=lambda x: int(x))
  hits_c22_2 = sum(1 for n in c_22_2 if n in latest_nums_22) if show_ticks_coupon_22 else 0
  with col_22_c2:
    st.markdown(
        f"**Zestaw 2 (Przesunięty Top)** ({len(c_22_2)} liczb)"
        f" {f'*(Trafienia: {hits_c22_2}/{len(c_22_2)})*' if show_ticks_coupon_22 else ''}"
        f" {'🔒 [Zamrożony]' if st.session_state['locked_22'] else '🟢 [Na żywo]'}"
    )
    st.code(format_coupon_list(c_22_2, latest_nums_22, show_ticks_coupon_22), language=None)

  col_22_s3, col_22_c3 = st.columns([1, 3])
  with col_22_s3:
    sz_22_3 = st.slider("Zestaw 3 (1-10):", 1, 10, key="sz_22_3", on_change=save_persistent_state)
  c_22_3 = sorted(st.session_state["frozen_c22_3"][:sz_22_3], key=lambda x: int(x))
  hits_c22_3 = sum(1 for n in c_22_3 if n in latest_nums_22) if show_ticks_coupon_22 else 0
  with col_22_c3:
    st.markdown(
        f"**Zestaw 3 (Strategia Alternatywna)** ({len(c_22_3)} liczb)"
        f" {f'*(Trafienia: {hits_c22_3}/{len(c_22_3)})*' if show_ticks_coupon_22 else ''}"
        f" {'🔒 [Zamrożony]' if st.session_state['locked_22'] else '🟢 [Na żywo]'}"
    )
    st.code(format_coupon_list(c_22_3, latest_nums_22, show_ticks_coupon_22), language=None)

  col_lock22, _ = st.columns([2, 4])
  with col_lock22:
    if not st.session_state["locked_22"]:
      if st.button("🔒 Zamroź zestawy 22:00 (na stałe)", key="btn_lock_22", use_container_width=True):
        st.session_state["locked_22"] = True
        st.session_state["frozen_c22_1"] = raw_c22_1[:10]
        st.session_state["frozen_c22_2"] = raw_c22_2[:10]
        st.session_state["frozen_c22_3"] = raw_c22_3[:10]
        save_persistent_state()
        st.rerun()
    else:
      if st.button("🔓 Odblokuj / Zmień zestawy 22:00", key="btn_unlock_22", use_container_width=True):
        st.session_state["locked_22"] = False
        save_persistent_state()
        st.rerun()

  st.divider()

  # =========================================================================
  # 6. AKTYWNA PREDYKCJA MIĘDZYSESYJNA, ECHO -16 ORAZ KUPON DNIA (FUZJA)
  # =========================================================================
  st.subheader(f"🔥 Aktywna Predykcja Międzysesyjna (Suwak Wspólny: {zakres_wspolny} losowań)")

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

  st.markdown(
      f"1️⃣ **Weryfikacja trafień w ostatnim losowaniu #{eval_target_id}** (bazując na #{eval_base_id}):"
  )

  eval_base_hour = str(eval_base_row["Godzina"]).strip()
  eval_base_date = str(eval_base_row["Data"]).strip()
  eval_base_nums_int = [int(v) for v in get_row_numbers(eval_base_row)]
  eval_missing_endings = sorted(list(set(range(10)) - {n % 10 for n in eval_base_nums_int}))

  def get_frozen_past_prediction(current_zakres, base_nums_tuple, base_hour, missing_ends_tuple):
    df_past = df.iloc[:-1] if len(df) >= 2 else df
    sub = df_past.tail(int(current_zakres)).reset_index(drop=True)
    if len(sub) < 2:
      return []
    j_counter = Counter()
    for i in range(1, len(sub)):
      p_nums = {int(v) for v in get_row_numbers(sub.iloc[i - 1])}
      c_nums = {int(v) for v in get_row_numbers(sub.iloc[i])}
      for n in p_nums.intersection(c_nums):
        weight = 1.2 if (n % 10) in JUMPER_ENDINGS else 1.0
        j_counter[n] += weight
    cand_list = sorted([f"{n:02d}" for n, _ in j_counter.most_common(15)], key=lambda x: int(x))
    if len(cand_list) < 15:
      for i in range(1, 81):
        s_n = f"{i:02d}"
        if len(cand_list) < 15 and s_n not in cand_list:
          cand_list.append(s_n)
    cand_list = sorted(cand_list[:15], key=lambda x: int(x))

    preds, _ = compute_transition_predictions(
        sub, cand_list, set(base_nums_tuple), base_hour, missing_ends_tuple, top_k=9, intra_session=False
    )
    return sorted(list(preds), key=lambda x: int(x))

  frozen_top9_eval = get_frozen_past_prediction(
      zakres_wspolny, tuple(sorted(eval_base_nums_int)), eval_base_hour, tuple(eval_missing_endings)
  )
  hits_frozen_top9 = sum(1 for n in frozen_top9_eval if n in eval_target_nums)

  frozen_eval_items = [
      f":green[**{n_str}✅**]" if n_str in eval_target_nums else f"**{n_str}**"
      for n_str in frozen_top9_eval
  ]

  st.markdown(
      f"🔒 **Zamrożona predykcja Top 9 na #{eval_target_id}** "
      f"(wygenerowana po **#{eval_base_id}** [{eval_base_date} | {eval_base_hour}]) — "
      f"Faktyczne trafienia: **{hits_frozen_top9}/{len(frozen_top9_eval) if frozen_top9_eval else 9}**"
  )
  if frozen_eval_items:
    st.markdown("   ".join(frozen_eval_items))
  else:
    st.markdown("*Brak wystarczających danych w wybranym zakresie do odtworzenia predykcji.*")

  st.markdown("")

  j_eval_list = get_cross_session_top_jumpers(zakres_wspolny, 20)
  top_15_eval = sorted(j_eval_list[:15], key=lambda x: int(x))
  if len(top_15_eval) < 15:
    for i in range(1, 81):
      s_n = f"{i:02d}"
      if len(top_15_eval) < 15 and s_n not in top_15_eval:
        top_15_eval.append(s_n)
  top_15_eval = sorted(top_15_eval[:15], key=lambda x: int(x))

  hits_eval_total = sum(1 for n in top_15_eval if n in eval_target_nums)
  eval_items = [
      f"**{n_str}**[✅]" if n_str in eval_target_nums else f"**{n_str}**"
      for n_str in top_15_eval
  ]

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
  sub_wsp_df = df.tail(int(zakres_wspolny)).reset_index(drop=True)
  pred_cross, source_mapping = compute_transition_predictions(
      sub_wsp_df,
      top_15_cross,
      pred_base_nums,
      pred_base_hour,
      tuple(missing_endings),
      top_k=9,
      intra_session=False,
      p_bias=parity_bias,
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

  st.markdown(f"🎯 **Top 9 Predykcji Międzysesyjnych (Typy do gry na {next_session_label}):**")
  pred_sorted_list = sorted(list(pred_cross), key=lambda x: int(x))
  st.markdown("   ".join([f":red[**{n_str}**]" for n_str in pred_sorted_list]))

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
  st.markdown("🔥 **Top 15 Wspólnych Skoczków (Szeroka pula):**")
  cross_items = [f"**{n_str}**" for n_str in top_15_cross]
  mid_c = len(cross_items) // 2
  st.markdown("   ".join(cross_items[:mid_c]))
  st.markdown("   ".join(cross_items[mid_c:]))

  st.markdown("")

  # --- DODATKOWA PODPOWIEDŹ: ECHO SPRZED DOKŁADNIE 16 LOSOWAŃ ---
  st.markdown(f"🔮 **Echo sprzed dokładnie 16 losowań (Podpowiedź na {next_session_label}):**")
  st.caption(
      "Statystyka bazy: odstęp 16 losowań generuje najwyższe zagęszczenie mocnych nawrotów "
      "(8–12 liczb z jednego koszyka). Liczby wyróżnione na :red[**czerwono**] pokrywają się z Top 9 "
      "lub należą do topowych końcówek (5, 3, 7)."
  )

  echo_all_nums = []
  echo_sess_nums = []

  col_echo1, col_echo2 = st.columns(2)
  with col_echo1:
    if len(df) >= 16:
      echo_all_row = df.iloc[-16]
      echo_all_id = str(echo_all_row["ID"]).strip()
      echo_all_date = str(echo_all_row["Data"]).strip()
      echo_all_hour = str(echo_all_row["Godzina"]).strip()
      echo_all_nums = sorted([f"{int(v):02d}" for v in get_row_numbers(echo_all_row)], key=lambda x: int(x))

      echo_all_fmt = []
      for n_s in echo_all_nums:
        if n_s in pred_cross:
          echo_all_fmt.append(f":red[**{n_s}🎯**]")
        elif (int(n_s) % 10) in TOP_ENDINGS:
          echo_all_fmt.append(f":red[**{n_s}**]")
        else:
          echo_all_fmt.append(f"**{n_s}**")

      st.info(
          f"🌐 **Cykl ogólny (-16 losowań):** losowanie **#{echo_all_id}** [{echo_all_date} | {echo_all_hour}]\n\n"
          + "  ".join(echo_all_fmt[:10])
          + "\n\n"
          + "  ".join(echo_all_fmt[10:])
      )

  with col_echo2:
    df_next_sess = df_22_all if next_session_label == "22:00" else df_14_all
    if len(df_next_sess) >= 16:
      echo_sess_row = df_next_sess.iloc[-16]
      echo_sess_id = str(echo_sess_row["ID"]).strip()
      echo_sess_date = str(echo_sess_row["Data"]).strip()
      echo_sess_hour = str(echo_sess_row["Godzina"]).strip()
      echo_sess_nums = sorted([f"{int(v):02d}" for v in get_row_numbers(echo_sess_row)], key=lambda x: int(x))

      echo_sess_fmt = []
      for n_s in echo_sess_nums:
        if n_s in pred_cross:
          echo_sess_fmt.append(f":red[**{n_s}🎯**]")
        elif (int(n_s) % 10) in TOP_ENDINGS:
          echo_sess_fmt.append(f":red[**{n_s}**]")
        else:
          echo_sess_fmt.append(f"**{n_s}**")

      st.info(
          f"⏰ **Cykl sesji {next_session_label} (-16 losowań tej godziny):** losowanie **#{echo_sess_id}** [{echo_sess_date} | {echo_sess_hour}]\n\n"
          + "  ".join(echo_sess_fmt[:10])
          + "\n\n"
          + "  ".join(echo_sess_fmt[10:])
      )

  st.markdown("")

  # --- 🏆 KUPON DNIA: FUZJA WSZYSTKICH SYGNAŁÓW ---
  st.markdown(f"### 🏆 Kupon Dnia — Fuzja Wszystkich Sygnałów (na {next_session_label})")
  st.caption(
      "Łączy typy z: Predykcji Międzysesyjnej Top 9 + Predykcji Wewnątrzsesyjnej Top 9 + "
      "Echa -16 losowań + Topowych Końcówek (5, 3, 7) + Odbić Pustych Końcówek."
  )

  if "fusion_coupon_size" not in st.session_state:
    st.session_state["fusion_coupon_size"] = 8

  fusion_size = st.select_slider(
      "Wybierz liczbę skreśleń na Kuponie Dnia:",
      options=[5, 6, 7, 8, 9, 10],
      key="fusion_coupon_size",
      on_change=save_persistent_state,
  )

  fusion_scores = defaultdict(float)
  fusion_reasons = defaultdict(list)

  intra_target_preds = pred_22_to_22 if next_session_label == "22:00" else pred_14_to_14

  for n_s in pred_cross:
    fusion_scores[n_s] += 4.0
    fusion_reasons[n_s].append("Pred. Międzysesyjna")

  for n_s in intra_target_preds:
    fusion_scores[n_s] += 3.5
    fusion_reasons[n_s].append(f"Pred. {next_session_label}➔{next_session_label}")

  for n_s in echo_sess_nums:
    fusion_scores[n_s] += 2.2
    fusion_reasons[n_s].append("Echo Sesji -16")

  for n_s in echo_all_nums:
    fusion_scores[n_s] += 1.5
    fusion_reasons[n_s].append("Echo Ogólne -16")

  for n_i in range(1, 81):
    n_s = f"{n_i:02d}"
    if (n_i % 10) in TOP_ENDINGS:
      fusion_scores[n_s] += 1.2
      if fusion_reasons[n_s]:
        fusion_reasons[n_s].append(f"Końcówka {n_i % 10}")
    if (n_i % 10) in missing_endings:
      fusion_scores[n_s] += 1.6
      fusion_reasons[n_s].append(f"Odbicie pustej {n_i % 10}")
    if parity_bias == "EVEN" and (n_i % 2 == 0) and fusion_reasons[n_s]:
      fusion_scores[n_s] += 0.8
    elif parity_bias == "ODD" and (n_i % 2 != 0) and fusion_reasons[n_s]:
      fusion_scores[n_s] += 0.8

  # --- SYNERGIA PAR I TRÓJEK W KUPONIE DNIA ---
  df_target_synergy = (df_22_all if next_session_label == "22:00" else df_14_all).tail(
      int(zakres_22 if next_session_label == "22:00" else zakres_14)
  )
  pair_counter = Counter()
  for _, s_row in df_target_synergy.iterrows():
    s_nums = sorted(list(set(f"{int(v):02d}" for v in get_row_numbers(s_row))), key=lambda x: int(x))
    for comb in combinations(s_nums, 2):
      pair_counter[comb] += 1

  top_synergy_pairs = [p for p, _ in pair_counter.most_common(12)]
  preliminary_top = {k for k, _ in sorted(fusion_scores.items(), key=lambda x: (-x[1], int(x[0])))[:18]}
  for p_a, p_b in top_synergy_pairs:
    if p_a in preliminary_top and p_b in preliminary_top:
      fusion_scores[p_a] += 1.1
      fusion_scores[p_b] += 1.1
      if "Synergia Par" not in fusion_reasons[p_a]:
        fusion_reasons[p_a].append("Synergia Par")
      if "Synergia Par" not in fusion_reasons[p_b]:
        fusion_reasons[p_b].append("Synergia Par")

  # --- KONTROLA POWTÓREK (ANTI-REPEAT CAP) I BALANS PARZYSTOŚCI / ZAKRESU ---
  ranked_candidates = sorted(fusion_scores.items(), key=lambda x: (-x[1], int(x[0])))
  last_draw_str_set = {f"{n:02d}" for n in latest_overall_nums_int}
  max_repeats_allowed = max(2, fusion_size // 3)
  max_per_parity = (fusion_size + 1) // 2 + 1
  max_per_half = (fusion_size + 1) // 2 + 1

  selected_fusion = []
  rep_cnt = 0
  even_cnt = 0
  odd_cnt = 0
  low_cnt = 0
  high_cnt = 0

  for cand_str, cand_score in ranked_candidates:
    if len(selected_fusion) >= fusion_size:
      break
    c_int = int(cand_str)
    is_rep = cand_str in last_draw_str_set
    is_even = (c_int % 2 == 0)
    is_low = (c_int <= 40)

    if is_rep and rep_cnt >= max_repeats_allowed:
      continue
    if is_even and even_cnt >= max_per_parity:
      continue
    if (not is_even) and odd_cnt >= max_per_parity:
      continue
    if is_low and low_cnt >= max_per_half:
      continue
    if (not is_low) and high_cnt >= max_per_half:
      continue

    selected_fusion.append((cand_str, cand_score))
    if is_rep:
      rep_cnt += 1
    if is_even:
      even_cnt += 1
    else:
      odd_cnt += 1
    if is_low:
      low_cnt += 1
    else:
      high_cnt += 1

  # Uzupełnienie gdyby ostre filtry zostawiły mniej niż fusion_size liczb
  if len(selected_fusion) < fusion_size:
    chosen_set = {x[0] for x in selected_fusion}
    for cand_str, cand_score in ranked_candidates:
      if cand_str not in chosen_set:
        selected_fusion.append((cand_str, cand_score))
        chosen_set.add(cand_str)
        if len(selected_fusion) >= fusion_size:
          break

  top_fusion = selected_fusion
  fusion_nums_sorted = sorted([item[0] for item in top_fusion], key=lambda x: int(x))

  st.success(
      f"💎 **Złoty Zestaw ({fusion_size} liczb na {next_session_label}):**   "
      + "   ".join([f":red[**{n}**]" for n in fusion_nums_sorted])
  )

  # Weryfikacja trafień w Kuponie Dnia zawsze względem absolutnie ostatniego losowania w bazie (#17149)
  session_nums_for_fusion = {f"{n:02d}" for n in latest_overall_nums_int}
  session_last_id = latest_id
  session_last_date = latest_date
  fusion_hits = sum(1 for n in fusion_nums_sorted if n in session_nums_for_fusion)

  fusion_display_hits = []
  for n in fusion_nums_sorted:
    if n in session_nums_for_fusion:
      fusion_display_hits.append(f":green[**{n}✅**]")
    else:
      fusion_display_hits.append(f"**{n}**")

  st.markdown(
      f"🎯 **Trafienia w najnowszym losowaniu (#{session_last_id} [{session_last_date} | {latest_hour}]):** "
      f"**{fusion_hits}/{fusion_size}** ➔ " + "   ".join(fusion_display_hits)
  )

  reason_lines = [
      f"**{n}** ({sc:.1f} pkt: {', '.join(dict.fromkeys(fusion_reasons[n]))})"
      for n, sc in top_fusion
  ]
  st.caption("🔍 Uzasadnienie punktacji: " + " | ".join(reason_lines))

  st.divider()

  # =========================================================================
  # 7. ANALIZA PAR I TRÓJEK (POWIĄZANA Z SUWAKAMI SESYJNYMI)
  # =========================================================================
  st.subheader("🔗 Analiza Par i Trójek (Współwystępowanie)")
  selected_session_for_tuples = st.selectbox(
      "Wybierz sesję do analizy par/trójek:", ["22:00", "14:00"]
  )
  active_tuple_zakres = (
      zakres_22 if selected_session_for_tuples == "22:00" else zakres_14
  )
  df_tuples_base = (
      df_22_all if selected_session_for_tuples == "22:00" else df_14_all
  )
  df_tuples_session = df_tuples_base.tail(int(active_tuple_zakres))

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

  st.markdown(
      f"**Top 5 Par (Sesja {selected_session_for_tuples} — zakres {active_tuple_zakres} losowań):**"
  )
  pairs_display = [
      f"({' - '.join(pair)}) [wystąpiły {cnt}x]" for pair, cnt in top_pairs
  ]
  st.code(
      "\n".join(pairs_display) if pairs_display else "Za mało danych w zakresie",
      language=None,
  )

  st.markdown(
      f"**Top 5 Trójek (Sesja {selected_session_for_tuples} — zakres {active_tuple_zakres} losowań):**"
  )
  triplets_display = [
      f"({' - '.join(trip)}) [wystąpiły {cnt}x]" for trip, cnt in top_triplets
  ]
  st.code(
      "\n".join(triplets_display) if triplets_display else "Za mało danych w zakresie",
      language=None,
  )

  st.divider()

  # =========================================================================
  # 8. PEŁNA BAZA WSZYSTKICH LOSOWAŃ
  # =========================================================================
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
