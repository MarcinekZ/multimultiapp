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

  # 1. ARCHIWUM OSTATNICH LOSOWAŃ (PRZESKOKI)
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

    st.code(" ".join(formatted_display), language=None)

  st.divider()

  # 2. USTAWIENIA ANALIZY (KLASYCZNY SUWAK + PRZYCISKI - ORAZ +)
  st.subheader("⚙️ Ustawienia Analizy Statystycznej")

  if "zakres" not in st.session_state:
    st.session_state["zakres"] = min(20, total_draws)

  # Układ w kolumnach: [-] [ Suwak ] [+]
  col_minus, col_slider, col_plus = st.columns([1, 6, 1])

  with col_minus:
    st.text("")
    st.text("")
    if st.button("➖", use_container_width=True):
      if st.session_state["zakres"] > 1:
        st.session_state["zakres"] -= 1

  with col_plus:
    st.text("")
    st.text("")
    if st.button("➕", use_container_width=True):
      if st.session_state["zakres"] < total_draws:
        st.session_state["zakres"] += 1

  with col_slider:
    zakres = st.slider(
        "Wybierz zakres analizowanych ostatnich losowań:",
        min_value=1,
        max_value=total_draws,
        key="zakres",
        step=1,
    )

  st.divider()

  # 3. TOP 10 SESYJNE ORAZ REKOMENDOWANE ZAKŁADY
  st.subheader(f"⏰ Top 10 Sesyjne (Zakres: {int(zakres)} losowań)")
  st.caption("Liczby trafione w najnowszym losowaniu oznaczono ikoną ✅")

  df_analyzed = df.tail(int(zakres))
  latest_draw = df.iloc[-1]
  latest_nums = {
      str(v).replace(".0", "").strip()
      for v in latest_draw.iloc[3:].values
      if pd.notna(v) and str(v).strip()
  }

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

      top_even = even_counts.head(10).index.tolist()
      top_odd = odd_counts.head(10).index.tolist()

      def format_top_list(num_list):
        res = []
        for n_str in num_list:
          if n_str in latest_nums:
            res.append(f"{n_str}✅")
          else:
            res.append(f"{n_str}")
        return " ".join(res)

      st.markdown("**Top 10 Parzyste:**")
      st.code(
          format_top_list(top_even)
          if top_even
          else "Brak danych w wybranym zakresie"
      )

      st.markdown("**Top 10 Nieparzyste:**")
      st.code(
          format_top_list(top_odd)
          if top_odd
          else "Brak danych w wybranym zakresie"
      )

      # REKOMENDOWANY ZAKŁAD SESYJNY
      st.markdown(
          "🎯 **Rekomendowany Zakład (Top 5 Parzyste + Top 5 Nieparzyste):**"
      )
      rec_even = [n for n in top_even[:5]]
      rec_odd = [n for n in top_odd[:5]]
      recommended_combo = sorted(rec_even + rec_odd, key=lambda x: int(x))

      rec_display = []
      for n_str in recommended_combo:
        if n_str in latest_nums:
          rec_display.append(f"{n_str}✅")
        else:
          rec_display.append(n_str)

      st.code(
          " ".join(rec_display) if rec_display else "Brak danych", language=None
      )

    else:
      st.info(
          f"Brak losowań z godziny {session_time} w tym zakresie (zwiększ zakres,"
          " aby objąć tę sesję)."
      )
else:
  st.warning("Oczekiwanie na ładowanie bazy danych...")
