import os
import pandas as pd
import requests

DATA_URL = "http://mbnet.com.pl/dl.txt"
FILE_NAME = "multi_multi (10).csv"

try:
  response = requests.get(DATA_URL, timeout=15)
  response.encoding = "utf-8"
  if response.status_code == 200:
    lines = response.text.strip().split("\n")
    new_rows = []

    for line in lines:
      parts = line.replace(";", " ").split()
      if len(parts) >= 4:
        draw_id = parts[0]
        date_str = parts[1]
        time_str = parts[2]
        nums = parts[3:]
        # Poprawna kolejność: ID, Data, Godzina, Liczby
        row = [draw_id, date_str, time_str] + nums
        new_rows.append(row)

    if new_rows:
      df_new = pd.DataFrame(new_rows)
      df_new.to_csv(FILE_NAME, index=False, header=False)
      print(
          f"Pomyślnie zaktualizowano i sformatowano bazę. Łącznie wierszy:"
          f" {len(df_new)}"
      )
    else:
      print("Błąd: Pusty lub niepoprawny format danych.")
  else:
    print(f"Błąd pobierania: status {response.status_code}")
except Exception as e:
  print(f"Wystąpił błąd: {e}")
