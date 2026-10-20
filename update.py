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
      cleaned = line.replace(",", " ").replace(";", " ")
      parts = cleaned.split()
      if len(parts) >= 3:
        # Inteligentne szukanie daty (ma kropkę) i godziny (ma dwukropek)
        date_idx = -1
        time_idx = -1
        for idx, p in enumerate(parts[:5]):
          if "." in p and len(p) >= 8:
            date_idx = idx
          elif ":" in p:
            time_idx = idx

        if date_idx != -1 and time_idx != -1:
          draw_id = parts[date_idx - 1] if date_idx > 0 else ""
          date_str = parts[date_idx]
          time_str = parts[time_idx]
          nums = parts[time_idx + 1 :]
          row = [draw_id, date_str, time_str] + nums
          new_rows.append(row)
        else:
          if len(parts) >= 4:
            new_rows.append([parts[0], parts[1], parts[2]] + parts[3:])

    if new_rows:
      df_new = pd.DataFrame(new_rows)
      df_new.to_csv(FILE_NAME, index=False, header=False)
      print(
          f"Pomyślnie zaktualizowano i naprawiono bazę. Łącznie wierszy:"
          f" {len(df_new)}"
      )
    else:
      print("Błąd: Nie znaleziono prawidłowych wierszy.")
  else:
    print(f"Błąd pobierania: status {response.status_code}")
except Exception as e:
  print(f"Wystąpił błąd: {e}")
