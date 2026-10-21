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

  # 1. ARCHIWUM OSTATNICH LOSOWAŃ (PODZIELONE NA 2 LINIE PO 10 LICZB)
  st.subheader("📌 Archiwum: Ostatnie Losowania (Przeskoki)")
  st.caption(
      "Liczby oznaczone 🔄 powtórzyły się z poprzedniego losowania."
  )

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

    # Dzielimy 20 liczb na dwie równe linie po 10, żeby idealnie mieściły się na telefonie
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

  st.write(f"Wybrany zakres: **{int(zakres)}** losowań")

  st.divider()

  # 3. ANALIZA SESYJNA (14:00 i 22:00) Z OSOBNYMI SUWAKAMI 1-10
  st.subheader(f"⏰ Analiza Sesyjna (Zakres bazy: {int(zakres)} losowań)")
  st.caption(
      "Każdy zakład posiada własny suwak (1–10 liczb). Trafienia w najnowszym"
      " losowaniu oznaczono ✅"
  )

  latest_draw = df.iloc[-1]
  latest_nums = {
      str(v).replace(".0", "").strip()
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


  for session_time, session_label, icon in [
      ("14:00", "Godzina 14:00", "☀️"),
      ("22:00", "Godzina 22:00", "🌙"),
  ]:
    st.markdown(f"### {icon} {session_label}")

    df_session = df_analyzed[df_analyzed["Godzina"] == session_time]

    if not df_session.empty:
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

      all_even = even_counts.index.tolist()
      all_odd = odd_counts.index.tolist()

      col1, col2 = st.columns(2)

      with col1:
        st.markdown("**Top Parzyste**")
        limit_even = st.slider(
            f"Parzyste {session_time}",
            min_value=1,
            max_value=10,
            value=min(5, len(all_even)) if all_even else 1,
            key=f"slider_even_{session_time}",
            step=1,
            label_visibility="collapsed",
        )
        selected_even = all_even[:limit_even]
        st.code(
            format_list(selected_even) if selected_even else "Brak danych",
            language=None,
        )

      with col2:
        st.markdown("**Top Nieparzyste**")
        limit_odd = st.slider(
            f"Nieparzyste {session_time}",
            min_value=1,
            max_value=10,
            value=min(5, len(all_odd)) if all_odd else 1,
            key=f"slider_odd_{session_time}",
            step=1,
            label_visibility="collapsed",
        )
        selected_odd = all_odd[:limit_odd]
        st.code(
            format_list(selected_odd) if selected_odd else "Brak danych",
            language=None,
        )

      # Rekomendowany zakład sesyjny
      st.markdown(
          f"🎯 **Rekomendowany Zakład Sesyjny ({session_time}):**"
      )
      rec_combo = sorted(selected_even + selected_odd, key=lambda x: int(x))
      st.code(
          format_list(rec_combo) if rec_combo else "Brak danych", language=None
      )
      st.divider()

    else:
      st.info(f"Brak losowań z godziny {session_time} w wybranym zakresie.")
else:
  st.warning("Oczekiwanie na ładowanie bazy danych...")
