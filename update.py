import os
import requests

DATA_URL = "http://mbnet.com.pl/dl.txt"
FILE_NAME = "multi_multi (10).csv"

try:
  response = requests.get(DATA_URL, timeout=15)
  response.encoding = "utf-8"
  if response.status_code == 200:
    with open(FILE_NAME, "w", encoding="utf-8") as f:
      f.write(response.text)
    print("Pomyślnie pobrano i zaktualizowano bazę wyników.")
  else:
    print(f"Błąd pobierania: status {response.status_code}")
except Exception as e:
  print(f"Wystąpił błąd: {e}")
