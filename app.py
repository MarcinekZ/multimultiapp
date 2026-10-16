import pandas as pd
from collections import Counter
import streamlit as st

st.set_page_config(
    page_title="Multi Multi AI System",
    page_icon="🎯",
    layout="centered"
)

st.title("🎯 Multi Multi AI System")
st.markdown("**Mobilny Panel Analityczny Ekipy**")

@st.cache_data(ttl=0)
def load_data():
    try:
        df = pd.read_csv('multi_multi (8).csv', header=None)
        return df
    except Exception as e:
        st.error(f"Błąd ładowania bazy danych: {e}")
        return None

df = load_data()

if df is not None:
    st.markdown("---")
    session_time = st.radio("⏱️ Wybierz Sesję:", ["14:00", "22:00"], horizontal=True)
    window_size = st.slider("📊 Okres analizy (liczba ostatnich sesji):", 20, 100, 50)
    
    number_cols = list(range(3, 23))
    df_session = df[df[2] == session_time].tail(window_size)
    
    counter = Counter()
    for _, row in df_session.iterrows():
        for c in number_cols:
            counter[int(row[c])] += 1
            
    odd_all = [(num, cnt) for num, cnt in counter.items() if num % 2 != 0]
    even_all = [(num, cnt) for num, cnt in counter.items() if num % 2 == 0]
    
    odd_all.sort(key=lambda x: x[1], reverse=True)
    even_all.sort(key=lambda x: x[1], reverse=True)
    
    top10_odd = odd_all[:10]
    top10_even = even_all[:10]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🟢 Top 10 Nieparzyste")
        for n, c in top10_odd:
            st.markdown(f"• **`{n:02d}`** (trak: {c})")
            
    with col2:
        st.markdown("### 🔵 Top 10 Parzyste")
        for n, c in top10_even:
            st.markdown(f"• **`{n:02d}`** (trak: {c})")
            
    st.markdown("---")
    st.markdown("### 🏆 Rekomendowane Zestawy Testowe")
    
    if session_time == "22:00":
        z1 = [31, 73, 76, 80]
        z2 = [7, 29, 52, 72]
        z3 = [31, 73, 76]
    else:
        z1 = [32, 33, 65, 70]
        z2 = [13, 18, 49, 64]
        z3 = [32, 49, 65]
        
    st.success(f"**Zestaw 1 (4M):** `{' — '.join(map(str, z1))}`")
    st.info(f"**Zestaw 2 (4M):** `{' — '.join(map(str, z2))}`")
    st.warning(f"**Zestaw 3 (3M):** `{' — '.join(map(str, z3))}`")
    
    st.markdown("---")
    st.markdown("### ➕ Dodaj Nowe Losowanie")
    with st.form("add_draw_form"):
        last_num = int(df[0].max()) if not df.empty else 17087
        new_draw_num = st.number_input("Numer losowania", value=last_num + 1, step=1)
        new_date = st.text_input("Data (DD.MM.YYYY)", value="16.10.2026")
        new_time = st.selectbox("Czas sesji", ["14:00", "22:00"])
        new_nums_str = st.text_input("Wylosowane 20 liczb (oddzielone spacjami)")
        new_plus = st.number_input("Plus", value=0, min_value=0, max_value=80)
        
        submitted = st.form_submit_button("Zapisz do bazy")
        if submitted:
            try:
                nums = [int(n.strip()) for n in new_nums_str.replace(',', ' ').split() if n.strip()]
                if len(nums) != 20:
                    st.error(f"Podano {len(nums)} liczb! Musi być dokładnie 20.")
                else:
                    row_data = [int(new_draw_num), new_date, new_time] + nums + [int(new_plus)]
                    df.loc[len(df)] = row_data
                    df.to_csv('multi_multi (8).csv', index=False, header=False)
                    st.success(f"Dodano losowanie nr {new_draw_num}! Odśwież stronę.")
            except Exception as ex:
                st.error(f"Błąd: {ex}")
