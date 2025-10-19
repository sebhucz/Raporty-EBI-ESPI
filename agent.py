import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import csv
import os

# --- Konfiguracja ---
PLIK_ZE_SPOLKAMI = 'companies.txt'
NAZWA_PLIKU = 'news.csv' # Przeniesione globalnie
LISTA_SPOLEK = []

try:
    with open(PLIK_ZE_SPOLKAMI, 'r', encoding='utf-8') as f:
        LISTA_SPOLEK = [linia.strip() for linia in f if linia.strip()]
    
    if not LISTA_SPOLEK:
        print(f"BŁĄD: Plik {PLIK_ZE_SPOLKAMI} jest pusty!")
    else:
        print(f"Wczytano {len(LISTA_SPOLEK)} spółek z pliku {PLIK_ZE_SPOLKAMI}.")
        
except FileNotFoundError:
    print(f"BŁĄD KRYTYCZNY: Nie znaleziono pliku {PLIK_ZE_SPOLKAMI}!")
    LISTA_SPOLEK = []
except Exception as e:
    print(f"BŁĄD: Wystąpił nieoczekiwany błąd podczas wczytywania pliku spółek: {e}")
    LISTA_SPOLEK = []

DATA_OD = datetime(2024, 1, 1)  # Data początkowa (Rok, Miesiąc, Dzień)
DATA_DO = datetime.now() # Ustawiamy datę końcową na "teraz"

# Lista na wszystkie znalezione artykuły
zebrane_artykuly = []

# --- FAZA 1: ODKRYWANIE ---
print("\n--- FAZA 1: ODKRYWANIE LINKÓW ---")

if LISTA_SPOLEK:
    for spolka in LISTA_SPOLEK:
        print(f"\n--- Przetwarzam spółkę: {spolka} ---")
        
        numer_strony = 1
        czy_kontynuowac_paginacje = True
        
        while czy_kontynuowac_paginacje:
            url_listy = f"https://www.stockwatch.pl/wiadomosci/walor/{spolka}?page={numer_strony}"
            print(f"Przetwarzam stronę: {url_listy}")

            try:
                strona = requests.get(url_listy, headers={'User-Agent': 'Mozilla/5.0'})
                strona.raise_for_status()
            except requests.RequestException as e:
                print(f"Błąd pobierania strony {url_listy}: {e}")
                break 

            soup = BeautifulSoup(strona.text, 'html.parser')
            bloki_newsow = soup.select('li.postlist')

            if not bloki_newsow:
                print("Koniec newsów na tej stronie, kończę paginację.")
                break 

            for blok in bloki_newsow:
                element_daty = blok.select_one('time')
                if not element_daty:
                    print("Pominięto blok bez daty")
                    continue
                
                data_artykulu_str = element_daty.get_text(strip=True)
                
                try:
                    data_artykulu = datetime.strptime(data_artykulu_str, '%Y-%m-%d %H:%M:%S')
                except ValueError as e:
                    print(f"Nie udało się przetworzyć daty: {data_artykulu_str}. Błąd: {e}")
                    continue

                if DATA_OD <= data_artykulu <= DATA_DO:
                    element_linku = blok.select_one('a.title')
                    if element_linku:
                        element_tytulu = element_linku.select_one('strong')
                        tytul = element_tytulu.get_text(strip=True) if element_tytulu else "Brak tytułu"
                        link = element_linku['href']
                        
                        if not link.startswith('http'):
                            link = "https://www.stockwatch.pl" + link
                        
                        zebrane_artykuly.append({
                            'spolka': spolka,
                            'tytul': tytul,
                            'data': data_artykulu_str,
                            'link': link,
                            'tresc': ''
                        })
                        print(f"   [Znaleziono] {tytul}")
                
                elif data_artykulu < DATA_OD:
                    print("Znaleziono artykuł starszy niż DATA_OD. Przerywam paginację.")
                    czy_kontynuowac_paginacje = False
                    break 

            if not czy_kontynuowac_paginacje:
                break 

            numer_strony += 1
            time.sleep(1) 
else:
    print("Lista spółek jest pusta. Pomijam Fazę 1.")


# --- FAZA 2: POBIERANIE TREŚCI ---
if zebrane_artykuly:
    print("\n\n--- FAZA 2: POBIERANIE TREŚCI ---")

    for artykul in zebrane_artykuly:
        print(f"Pobieram treść dla: {artykul['tytul'][:50]}...")
        
        try:
            strona_artykulu = requests.get(artykul['link'], headers={'User-Agent': 'Mozilla/5.0'})
            strona_artykulu.raise_for_status()

            soup_artykulu = BeautifulSoup(strona_artykulu.text, 'html.parser')
            
            # === POCZĄTEK POPRAWKI ===
            # Strona używa RÓŻNYCH struktur. Próbujemy znaleźć obie.
            
            # Próba 1: Selektor dla 'satrev' (div.entry)
            element_tresci = soup_artykulu.select_one('div.entry') 
            
            if not element_tresci:
                # Próba 2: Selektor dla 'bact' (div#article-content-body)
                print("   Nie znaleziono 'div.entry', próbuję 'div#article-content-body'...")
                element_tresci = soup_artykulu.select_one('div#article-content-body')
            # === KONIEC POPRAWKI ===
                
            if element_tresci:
                tresc = element_tresci.get_text(strip=True, separator=' ')
                artykul['tresc'] = tresc
            else:
                artykul['tresc'] = "BŁĄD: Nie znaleziono treści (sprawdzono 'div.entry' i 'div#article-content-body')"

        except requests.RequestException as e:
            print(f"Błąd pobierania artykułu {artykul['link']}: {e}")
            artykul['tresc'] = f"BŁĄD: {e}"
        
        time.sleep(1) 
else:
    print("\nNie znaleziono żadnych nowych artykułów do pobrania.")

# --- FAZA 3: ZAPISYWANIE DO PLIKU ---
print("\n\n--- FAZA 3: ZAPISYWANIE DO PLIKU ---")

czy_plik_istnieje = os.path.exists(NAZWA_PLIKU)

try:
    with open(NAZWA_PLIKU, 'a', newline='', encoding='utf-8') as plik_csv:
        pola = ['spolka', 'tytul', 'data', 'link', 'tresc']
        writer = csv.DictWriter(plik_csv, fieldnames=pola)

        if not czy_plik_istnieje:
            writer.writeheader()
            print(f"Utworzono nowy plik {NAZWA_PLIKU} i dodano nagłówki.")
            
        if not zebrane_artykuly:
            print("Brak nowych artykułów do dopisania.")
        else:
            licznik = 0
            for artykul in zebrane_artykuly:
                writer.writerow(artykul)
                licznik += 1
            print(f"Pomyślnie dopisano {licznik} nowych artykułów do {NAZWA_PLIKU}")

except Exception as e:
    print(f"Błąd podczas zapisywania do pliku CSV: {e}")

print("\n--- Scraper zakończył pracę ---")
