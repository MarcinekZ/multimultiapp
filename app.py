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
    return df
  except Exception as e:
    st.error(f"Błąd podczas ładowania pliku CSV: {e}")
    return None


df = load_data()

st.title("📱 Mobilny Panel Analityczny Ekipy")

if df is not None and not df.empty:
  total_draws = len(df)

  # 1. ARCHIWUM / OSTATNIE LOSOWANIA (PRZYWRÓCONE NA GÓRĘ)
  st.subheader("📌 Archiwum: Ostatnie Losowania (Przeskoki)")
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

  # 2. USTAWIENIA ANALIZY (PLUS/MINUS + SZYBKIE PRZYCISKI)
  st.subheader("⚙️ Ustawienia Analizy Statystycznej")
  st.caption("Wybierz zakres losowań (użyj przycisków lub plus/minus):")

  # Szybkie przyciski idealne na telefon
  cols_btn = st.columns(6)
  if cols_btn[0].button("5"):
    st.session_state["zakres_val"] = 5
  if cols_btn[1].button("10"):
    st.session_state["zakres_val"] = 10
  if cols_btn[2].button("20"):
    st.session_state["zakres_val"] = 20
  if cols_btn[3].button("50"):
    st.session_state["zakres_val"] = 50
  if cols_btn[4].button("100"):
    st.session_state["zakres_val"] = 100
  if cols_btn[5].button("Max"):
    st.session_state["zakres_val"] = total_draws

  default_val = st.session_state.get("zakres_val", 20)

  # Precyzyjne pole z plus / minus
  zakres = st.number_input(
      "Zakres losowań:",
      min_value=1,
      max_value=total_draws,
      value=int(default_val),
      step=1,
  )

  st.divider()

  # 3. ANALIZA TOP 10 SESYJNE
  st.subheader(f"⏰ Top 10 Sesyjne (Zakres: {int(zakres)} losowań)")
  st.caption("Liczby trafione w najnowszym losowaniu oznaczono ikoną ✅")

  df_analyzed = df.tail(int(zakres))

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

      even_counts = counts[
          counts.index.map(
              lambda x: int(x) % 2 == 0 if str(x).isdigit() else False
          )
      ]
      odd_counts = counts[
          counts.index.map(
              lambda x: int(x) % 2 != 0 if str(x).isdigit() else False
          )
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
      st.info(
          f"Brak losowań z godziny {session_time} w tym zakresie (zwiększ zakres,"
          " aby objąć tę sesję)."
      )
else:
  st.warning("Oczekiwanie na ładowanie bazy danych...")
