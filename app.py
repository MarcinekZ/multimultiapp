import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Multi Multi Analytics PWA", page_icon="🎯", layout="wide"
)

FILE_NAME = "multi_multi (10).csv"


@st.cache_data(ttl=60)
def load_data():
  try:
    df = pd.read_csv(FILE_NAME, header=None)
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

  # 1. ARCHIWUM OSTATNICH LOSOWAŃ (2 linie po 10 liczb)
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

  # 2. USTAWIENIA ANALIZY (POZIOMY UKŁAD: [-] [SUWAK] [+])
  st.subheader("⚙️ Ustawienia Analizy Statystycznej")

  if "zakres" not in st.session_state:
    st.session_state["zakres"] = min(20, total_draws)

  col_minus, col_slider, col_plus = st.columns([1, 4, 1])

  with col_minus:
    if st.button("➖", use_container_width=True, key="main_minus"):
      if st.session_state["zakres"] > 1:
        st.session_state["zakres"] -= 1

  with col_plus:
    if st.button("➕", use_container_width=True, key="main_plus"):
      if st.session_state["zakres"] < total_draws:
        st.session_state["zakres"] += 1

  with col_slider:
    zakres = st.slider(
        "Zakres losowań:",
        min_value=1,
        max_value=total_draws,
        key="zakres",
        step=1,
        label_visibility="collapsed",
    )

  st.write(f"Wybrany zakres bazy: **{int(zakres)}** losowań")

  st.divider()

  # Pobieramy liczby z najnowszego losowania do weryfikacji trafień (✅)
  latest_draw = df.iloc[-1]
  latest_nums = {
      f"{int(str(v).replace('.0', '').strip()):02d}"
      if str(v).replace(".0", "").strip().isdigit()
      else str(v).replace(".0", "").strip()
      for v in latest_draw.iloc[3:].values
      if pd.notna(v) and str(v).strip()
  }

  df_analyzed = df.tail(int(zakres))


  def format_list(num_list):
    res = []
    for n_str in num_list:
      if n_str in latest_nums:
        res.append(f"{n_str}✅")
      else:
        res.append(f"{n_str}")
    return " ".join(res)


  def get_session_data(session_time):
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
    return even_counts.index.tolist(), odd_counts.index.tolist()


  even_14, odd_14 = get_session_data("14:00")
  even_22, odd_22 = get_session_data("22:00")

  # --- GODZINA 14:00 (CZYSTE TOP 10 PARZYSTE I NIEPARZYSTE Z ✅) ---
  st.subheader("☀️ Godzina 14:00")

  st.markdown("**Top 10 Parzyste:**")
  top10_even_14 = even_14[:10]
  st.code(
      format_list(top10_even_14)
      if top10_even_14
      else "Brak danych w wybranym zakresie",
      language=None,
  )

  st.markdown("**Top 10 Nieparzyste:**")
  top10_odd_14 = odd_14[:10]
  st.code(
      format_list(top10_odd_14)
      if top10_odd_14
      else "Brak danych w wybranym zakresie",
      language=None,
  )

  st.divider()

  # --- GODZINA 22:00 (CZYSTE TOP 10 PARZYSTE I NIEPARZYSTE Z ✅) ---
  st.subheader("🌙 Godzina 22:00")

  st.markdown("**Top 10 Parzyste:**")
  top10_even_22 = even_22[:10]
  st.code(
      format_list(top10_even_22)
      if top10_even_22
      else "Brak danych w wybranym zakresie",
      language=None,
  )

  st.markdown("**Top 10 Nieparzyste:**")
  top10_odd_22 = odd_22[:10]
  st.code(
      format_list(top10_odd_22)
      if top10_odd_22
      else "Brak danych w wybranym zakresie",
      language=None,
  )

  st.divider()

  # --- 4 REKOMENDOWANE ZAKŁADY Z OSOBNYMI SUWAKAMI (1-10) I TRAFIENIAMI ✅ ---
  st.subheader("🎯 Rekomendowane Zakłady (4 zestawy)")
  st.caption(
      "Każdy zakład posiada osobny suwak od 1 do 10 liczb. Trafienia oznaczono"
      " ✅"
  )

  # Rekomendowany Zakład 1: Parzyste 14:00
  st.markdown("🎯 **1. Rekomendowany Zakład: Parzyste (14:00)**")
  rec_lim_e14 = st.slider(
      "Suwak Rec Parzyste 14:00",
      1,
      10,
      min(5, len(even_14)) if even_14 else 5,
      key="rec_lim_e14",
      label_visibility="collapsed",
  )
  rec_sel_e14 = even_14[:rec_lim_e14]
  st.code(
      format_list(rec_sel_e14)
      if rec_sel_e14
      else "Brak danych w wybranym zakresie",
      language=None,
  )

  # Rekomendowany Zakład 2: Nieparzyste 14:00
  st.markdown("🎯 **2. Rekomendowany Zakład: Nieparzyste (14:00)**")
  rec_lim_o14 = st.slider(
      "Suwak Rec Nieparzyste 14:00",
      1,
      10,
      min(5, len(odd_14)) if odd_14 else 5,
      key="rec_lim_o14",
      label_visibility="collapsed",
  )
  rec_sel_o14 = odd_14[:rec_lim_o14]
  st.code(
      format_list(rec_sel_o14)
      if rec_sel_o14
      else "Brak danych w wybranym zakresie",
      language=None,
  )

  # Rekomendowany Zakład 3: Parzyste 22:00
  st.markdown("🎯 **3. Rekomendowany Zakład: Parzyste (22:00)**")
  rec_lim_e22 = st.slider(
      "Suwak Rec Parzyste 22:00",
      1,
      10,
      min(5, len(even_22)) if even_22 else 5,
      key="rec_lim_e22",
      label_visibility="collapsed",
  )
  rec_sel_e22 = even_22[:rec_lim_e22]
  st.code(
      format_list(rec_sel_e22)
      if rec_sel_e22
      else "Brak danych w wybranym zakresie",
      language=None,
  )

  # Rekomendowany Zakład 4: Nieparzyste 22:00
  st.markdown("🎯 **4. Rekomendowany Zakład: Nieparzyste (22:00)**")
  rec_lim_o22 = st.slider(
      "Suwak Rec Nieparzyste 22:00",
      1,
      10,
      min(5, len(odd_22)) if odd_22 else 5,
      key="rec_lim_o22",
      label_visibility="collapsed",
  )
  rec_sel_o22 = odd_22[:rec_lim_o22]
  st.code(
      format_list(rec_sel_o22)
      if rec_sel_o22
      else "Brak danych w wybranym zakresie",
      language=None,
  )

else:
  st.warning("Oczekiwanie na ładowanie bazy danych...")
