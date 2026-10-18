import requests

url = "http://mbnet.com.pl/dl.txt"

try:
    response = requests.get(url)
    response.encoding = 'utf-8'
    response.raise_for_status()

    with open("multi_multi (9).csv", "w", encoding="utf-8") as f:
        f.write(response.text)

    print("Sukces: Plik multi_multi (9).csv został pomyślnie zaktualizowany!")

except Exception as e:
    print(f"Błąd podczas aktualizacji: {e}")
    exit(1)
