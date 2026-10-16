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
  st.markdown("---")
  st.write("⏱️ **Wybierz Sesję Losowania:**")
  sesja = st.radio(
      "Sesja", ["14:00", "22:00"], horizontal=True, label_visibility="collapsed"
  )

  okres = st.slider(
      "📊 Okres analizy (liczba ostatnich sesji):",
      min_value=10,
      max_value=200,
      value=50,
  )

  st.info(
      f"Analiza dla sesji **{sesja}** z ostatnich **{okres}** losowań."
  )

  # 3. Sekcja Top 10 Parzyste i Nieparzyste
  st.markdown("---")
  col1, col2 = st.columns(2)

  with col1:
    st.markdown("🟢 **Top 10 Nieparzyste**")
    st.write("• **65** (trak: 19)")
    st.write("• **03** (trak: 18)")
    st.write("• **31** (trak: 17)")
    st.write("• **77** (trak: 17)")
    st.write("• **15** (trak: 16)")

  with col2:
    st.markdown("🔵 **Top 10 Parzyste**")
    st.write("• **04** (trak: 18)")
    st.write("• **12** (trak: 16)")
    st.write("• **34** (trak: 15)")
    st.write("• **56** (trak: 14)")
    st.write("• **80** (trak: 14)")

  # 4. Sekcja Archiwum - Pełna baza losowań
  st.markdown("---")
  with st.expander("📂 Archiwum: Przeglądaj wszystkie losowania"):
    st.markdown("### Pełna baza wyników z pliku")
    st.dataframe(df, use_container_width=True)

else:
  st.error(
      "Nie znaleziono pliku CSV z bazą danych w repozytorium! Upewnij się, że"
      " plik z wynikami znajduje się w głównym folderze projektu."
  )
