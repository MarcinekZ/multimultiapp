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

    for line in lines:
      line = line.strip()
      if not line:
        continue

      # Rozdzielamy linie po spacji / średniku / przecinku
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

        # Drugi element po dacie to najczęściej godzina lub numer losowania w danym dniu
        time_candidate = parts[date_idx + 1]

        # Określamy godzinę 14:00 vs 22:00
        if ":" in time_candidate:
          time_str = time_candidate
          nums_start = date_idx + 2
        elif time_candidate == "1":
          time_str = "14:00"
          nums_start = date_idx + 2
        elif time_candidate == "2":
          time_str = "22:00"
          nums_start = date_idx + 2
        else:
          time_str = "14:00"
          nums_start = date_idx + 1

        raw_nums = parts[nums_start:]
        # Formatujemy liczby do postaci 2-cyfrowej (np. "01", "04")
        formatted_nums = []
        for n in raw_nums:
          if n.isdigit():
            formatted_nums.append(f"{int(n):02d}")

        if len(formatted_nums) >= 15:  # Upewniamy się, że mamy komplet liczb
          row = [draw_id, date_str, time_str] + formatted_nums
          new_rows.append(row)

    if new_rows:
      df_new = pd.DataFrame(new_rows)
      df_new.to_csv(FILE_NAME, index=False, header=False)
      print(
          f"Pomyślnie zaktualizowano i sformatowano bazę Multi Multi. Łącznie"
          f" wierszy: {len(df_new)}"
      )
    else:
      print("Błąd: Nie udało się sparsować wierszy z pliku ml.txt")
  else:
    print(f"Błąd pobierania: status {response.status_code}")
except Exception as e:
  print(f"Wystąpił błąd: {e}")
