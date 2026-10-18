import requests

# Zewnętrzne źródło wyników
url = "http://mbnet.com.pl/dl.txt"
file_name = "multi_multi (10).csv"

try:
    print(f"Pobieranie danych z {url}...")
    response = requests.get(url, timeout=15)
    response.encoding = 'utf-8'
    response.raise_for_status()

    # Zapisujemy pobraną treść do właściwego pliku CSV
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"Sukces: Plik {file_name} został pomyślnie zaktualizowany!")

except Exception as e:
    print(f"Błąd podczas pobierania lub zapisu danych: {e}")
    exit(1)
