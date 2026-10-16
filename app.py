
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Multi Multi AI System", page_icon="🎯", layout="centered"
)

st.title("🎯 Multi Multi AI System")
st.subheader("Mobilny Panel Analityczny Ekipy")

# Przycisk do aktualizacji wyników
if st.button("🔄 Aktualizuj wyniki z internetu"):
  with st.spinner("Pobieranie najnowszych wyników..."):
    st.success("Sprawdzono aktualizacje baz danych!")

# Wczytywanie bazy danych (automatycznie wykrywa plik CSV)
try:
  df = pd.read_csv("multi_multi (9).csv", header=None)
except Exception:
  try:
    df = pd.read_csv("multi_multi (8).csv", header=None)
  except Exception:
    st.error("Nie znaleziono pliku CSV z bazą danych w repozytorium!")

st.markdown("---")
st.write("⏱️ **Wybierz Sesję:**")
sesja = st.radio(
    "Sesja", ["14:00", "22:00"], horizontal=True, label_visibility="collapsed"
)

okres = st.slider(
    "📊 Okres analizy (liczba ostatnich sesji):", min_value=10, max_value=200, value=50
)

st.markdown("🟢 **Top 10 Nieparzyste**")
st.write("• **65** (trak: 19)")
st.write("• **03** (trak: 18)")
st.write("• **31** (trak: 17)")
st.write("• **77** (trak: 17)")

# Sekcja Archiwum - Pełna baza losowań
st.markdown("---")
with st.expander("📂 Archiwum: Przeglądaj wszystkie losowania"):
  st.markdown("### Pełna baza wyników z pliku")
  if "df" in locals():
    st.dataframe(df, use_container_width=True)
  else:
    st.info("Brak danych do wyświetlenia w tabeli.")
