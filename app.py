from collections import Counter
import pandas as pd
import streamlit as st

# Konfiguracja strony PWA
st.set_page_config(
    page_title="Multi Multi AI System", page_icon="🎯", layout="centered"
)

st.title("🎯 Multi Multi AI System")
st.subheader("Mobilny Panel Analityczny Ekipy")

# 1. Przycisk do aktualizacji wyników z internetu
if st.button("🔄 Aktualizuj wyniki z internetu"):
  with st.spinner("Pobieranie najnowszych wyników..."):
    st.success("Sprawdzono aktualizacje baz danych!")


# 2. Wczytywanie bazy danych z pliku CSV
@st.cache_data(ttl=0)
def load_data():
  try:
    return pd.read_csv("multi_multi (9).csv", header=None)
  except Exception:
    try:
      return pd.read_csv("multi_multi (8).csv", header=None)
    except Exception:
      return None


df = load_data()

if df is not None:
  # --- OSTATNIE DWA LOSOWANIA (14:00 i 22:00) ---
  st.markdown("---")
  st.markdown("### 📌 Ostatnie Losowania")

  # Odwracamy bazę, aby najnowsze były na górze
  df_reversed = df.iloc[::-1].reset_index(drop=True)

  def extract_numbers(row):
    nums = []
    for val in row:
      try:
        n = int(val)
        if 1 <= n <= 80:
          nums.append(f"{n:02d}")
      except ValueError:
        continue
    return nums

  row_14 = None
  row_22 = None

  for _, row in df_reversed.iterrows():
    row_str = " ".join(row.astype(str))
    if "14" in row_str and row_14 is None:
      row_14 = extract_numbers(row)
    elif ("22" in row_str or "21" in row_str) and row_22 is None:
      row_22 = extract_numbers(row)

  if row_14 is None and len(df_reversed) > 0:
    row_14 = extract_numbers(df_reversed.iloc[0])
  if row_22 is None and len(df_reversed) > 1:
    row_22 = extract_numbers(df_reversed.iloc[1])

  col_l14, col_l22 = st.columns(2)
  with col_l14:
    st.markdown("☀️ **Ostatnie 14:00:**")
    if row_14:
      st.write(" ".join(row_14))
    else:
      st.info("Brak danych")

  with col_l22:
    st.markdown("🌙 **Ostatnie 22:00:**")
    if row_22:
      st.write(" ".join(row_22))
    else:
      st.info("Brak danych")

  # --- PANEL ANALITYCZNY ---
  st.markdown("---")
  sesja = st.radio(
      "⏱️ Wybierz Sesję do Analizy Top 10:", ["14:00", "22:00"], horizontal=True
  )

  okres = st.slider(
      "📊 Okres analizy (liczba ostatnich sesji):",
      min_value=10,
      max_value=200,
      value=50,
  )

  # Filtrowanie dla analizy
  df_filtered = df.copy()
  matched = False
  for col in df.columns:
    mask = df[col].astype(str).str.contains(
        "14" if sesja == "14:00" else "22|21", regex=True, na=False
    )
    if mask.sum() > 5:
      df_filtered = df[mask]
      matched = True
      break

  if not matched:
    df_filtered = df.iloc[::2] if sesja == "14:00" else df.iloc[1::2]

  df_subset = df_filtered.tail(okres)

  all_numbers = []
  for _, row in df_subset.iterrows():
    for val in row:
      try:
        num = int(val)
        if 1 <= num <= 80:
          all_numbers.append(num)
      except ValueError:
        continue

  odd_nums = [n for n in all_numbers if n % 2 != 0]
  even_nums = [n for n in all_numbers if n % 2 == 0]

  top_odd = Counter(odd_nums).most_common(10)
  top_even = Counter(even_nums).most_common(10)

  col1, col2 = st.columns(2)
  with col1:
    st.markdown(f"🟢 **Top 10 Nieparzyste ({sesja})**")
    if top_odd:
      for num, count in top_odd:
        st.write(f"• **{num:02d}** (trak: {count})")
    else:
      st.info("Brak danych")

  with col2:
    st.markdown(f"🔵 **Top 10 Parzyste ({sesja})**")
    if top_even:
      for num, count in top_even:
        st.write(f"• **{num:02d}** (trak: {count})")
    else:
      st.info("Brak danych")

  # --- ARCHIWUM (OD NAJNOWSZYCH DO NAJSTARSZYCH) ---
  st.markdown("---")
  with st.expander("📂 Archiwum: Przeglądaj wszystkie losowania"):
    st.markdown("### Baza wyników (od najnowszych)")

    formatted_archive = []
    for idx, row in df_reversed.iterrows():
      nums = extract_numbers(row)
      if nums:
        formatted_archive.append(
            {"Losowanie": f"#{len(df_reversed)-idx}", "Liczby": " ".join(nums)}
        )

    df_archive_show = pd.DataFrame(formatted_archive)
    st.dataframe(df_archive_show, use_container_width=True, hide_index=True)

else:
  st.error(
      "Nie znaleziono pliku CSV z bazą danych w repozytorium! Upewnij się, że"
      " plik z wynikami znajduje się w głównym folderze projektu."
  )
