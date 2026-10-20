import os
import pandas as pd
import requests

DATA_URL = "http://www.mbnet.com.pl/ml.txt"
FILE_NAME = "multi_multi (10).csv"

try:
  response = requests.get(DATA_URL, timeout=15)
  response.encoding = "utf-8"
  if response.status_code == 200:
    lines = response.text.strip().split("\n")
    new_rows = []
    date_counts = {}

    for line in lines:
      line = line.strip()
      if not line:
        continue

      cleaned = line.replace(";", " ").replace(",", " ")
      parts = cleaned.split()

      # Szukamy daty (format DD.MM.YYYY)
      date_idx = -1
      for idx, part in enumerate(parts):
        if "." in part and len(part) >= 8:
          date_idx = idx
          break

      if date_idx != -1 and len(parts) > date_idx + 1:
        draw_id = parts[date_idx - 1] if date_idx > 0 else ""
        date_str = parts[date_idx]

        # Liczymy wystąpienia tej samej daty:
        # 1. losowanie w danym dniu -> 14:00
        # 2. losowanie w danym dniu -> 22:00
        date_counts[date_str] = date_counts.get(date_str, 0) + 1
        if date_counts[date_str] == 1:
          time_str = "14:00"
        else:
          time_str = "22:00"

        # Sprawdzamy czy po dacie jest informacja o sesji/godzinie
        candidate = parts[date_idx + 1]
        if ":" in candidate:
          time_str = candidate
          nums_start = date_idx + 2
        elif candidate in ["1", "2"]:
          nums_start = date_idx + 2
        else:
          nums_start = date_idx + 1

        raw_nums = parts[nums_start:]
        formatted_nums = []
        for n in raw_nums:
          if n.isdigit():
            formatted_nums.append(f"{int(n):02d}")

        if len(formatted_nums) >= 15:
          row = [draw_id, date_str, time_str] + formatted_nums
          new_rows.append(row)

    if new_rows:
      df_new = pd.DataFrame(new_rows)
      df_new.to_csv(FILE_NAME, index=False, header=False)
      print(
          f"Pomyślnie zaktualizowano bazę. Łącznie wierszy poprawnych:"
          f" {len(df_new)}"
      )
    else:
      print("Błąd: Brak wierszy.")
  else:
    print(f"Błąd pobierania: status {response.status_code}")
except Exception as e:
  print(f"Wystąpił błąd: {e}")
