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
      if not line.strip():
        continue
      # Plik mbnet używa średników jako separatorów kolumn
      parts = [p.strip() for p in line.split(";")]
      if len(parts) >= 4:
        new_rows.append(parts)

    if new_rows:
      df_new = pd.DataFrame(new_rows)
      df_new.to_csv(FILE_NAME, index=False, header=False)
      print(
          f"Pomyślnie zaktualizowano bazę po średnikach. Łącznie wierszy:"
          f" {len(df_new)}"
      )
    else:
      print("Błąd: Pusty format danych.")
  else:
    print(f"Błąd pobierania: status {response.status_code}")
except Exception as e:
  print(f"Wystąpił błąd: {e}")
