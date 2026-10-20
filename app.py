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
    # Tworzymy nagłówki dla 23 kolumn: ID, Data, Godzina, 20 liczb
    num_cols = df.shape[1]
    cols = ["ID", "Data", "Godzina"] + [f"L{i}" for i in range(1, num_cols - 2)]
    df.columns = cols
    return df
  except Exception as e:
    st.error(f"Błąd podczas ładowania pliku CSV: {e}")
    return None


df = load_data()

st.title("📱 Mobilny Panel Analityczny Ekipy")

if df is not None and not df.empty:
  # Podgląd ostatnich losowań z przeskokami
  st.subheader("📌 4 Ostatnie Losowania (Przeskoki)")
  st.caption("Liczby oznaczone 🔄 powtórzyły się z poprzedniego losowania.")

  recent_df = df.tail(5).iloc[::-1]
  for i in range(len(recent_df) - 1):
    curr = recent_df.iloc[i]
    prev = recent_df.iloc[i + 1]

    curr_nums = set(curr.iloc[3:].values)
    prev_nums = set(prev.iloc[3:].values)
    repeated = curr_nums.intersection(prev_nums)

    draw_id = curr["ID"]
    date_str = curr["Data"]
    time_str = curr["Godzina"]

    st.markdown(
        f"**Losowanie #{draw_id}** | 📅 {date_str} | ⏰ {time_str}"
    )

    formatted_display = []
    for val in curr.iloc[3:].values:
      val_str = f"{int(val):02d}" if str(val).isdigit() else str(val)
      if val in repeated:
        formatted_display.append(f"🔄{val_str}")
      else:
        formatted_display.append(f"{val_str}")

    st.code(" ".join(formatted_display), language=None)

  st.divider()

  # Ustawienia Analizy Statystycznej
  st.subheader("⚙️ Ustawienia Analizy Statystycznej")

  total_draws = len(df)

  # Precyzyjny suwak od 1 z krokiem co 1
  zakres = st.slider(
      "Wybierz zakres analizowanych ostatnich losowań:",
      min_value=1,
      max_value=total_draws,
      value=20,
      step=1,
  )

  st.divider()

  # Analiza Top 10 Sesyjne
  st.subheader(f"⏰ Top 10 Sesyjne (Zakres: {zakres} losowań)")
  st.caption("Liczby trafione w najnowszym losowaniu oznaczono ikoną ✅")

  df_analyzed = df.tail(zakres)

  # Najnowsze wyniki do weryfikacji trafień (✅)
  latest_draw = df.iloc[-1]
  latest_nums = set(latest_draw.iloc[3:].values)

  for session_time, session_label, icon in [
      ("14:00", "Godzina 14:00", "☀️"),
      ("22:00", "Godzina 22:00", "🌙"),
  ]:
    st.markdown(f"### {icon} {session_label}")

    df_session = df_analyzed[df_analyzed["Godzina"] == session_time]

    if not df_session.empty:
      all_session_nums = df_session.iloc[:, 3:].values.flatten()
      counts = pd.Series(all_session_nums).value_counts()

      # Wycinki parzyste i nieparzyste
      even_counts = counts[
          counts.index.map(lambda x: int(x) % 2 == 0 if str(x).isdigit() else False)
      ]
      odd_counts = counts[
          counts.index.map(lambda x: int(x) % 2 != 0 if str(x).isdigit() else False)
      ]

      top_even = even_counts.head(10).index.tolist()
      top_odd = odd_counts.head(10).index.tolist()

      def format_top_list(num_list):
        res = []
        for n in num_list:
          n_str = f"{int(n):02d}" if str(n).isdigit() else str(n)
          if n in latest_nums:
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
    else:
      st.info(f"Brak losowań z godziny {session_time} w wybranym zakresie.")
else:
  st.warning("Oczekiwanie na ładowanie bazy danych...")
