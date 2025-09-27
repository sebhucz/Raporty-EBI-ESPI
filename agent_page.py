# To jest zawartość pliku: agent_page.py
import requests
from bs4 import BeautifulSoup # <-- TA LINIA BYŁA BRAKUJĄCA
import datetime
import os
import urllib3

# --- Konfiguracja ---
DAYS_AGO = 7
OUTPUT_FILENAME = "index.html"
COMPANIES_CONFIG_FILE = "spolki.txt"

# --- Funkcje wczytujące konfigurację z plików ---
def load_companies_from_file(filename):
    """Wczytuje listę spółek z pliku tekstowego."""
    companies = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#'):
                    parts = line.strip().split(',')
                    if len(parts) == 2:
                        companies.append({'name': parts[0].strip(), 'ticker': parts[1].strip()})
                    else:
                        print(f"🟡 Ostrzeżenie: Pomijam nieprawidłową linię w pliku '{filename}': {line.strip()}")
        print(f"✅ Pomyślnie wczytano {len(companies)} spółek z pliku '{filename}'.")
        return companies
    except FileNotFoundError:
        print(f"❌ BŁĄD: Nie znaleziono pliku konfiguracyjnego '{filename}'!")
        return []

# --- Pozostałe funkcje ---

def fetch_reports_from_stockwatch(company_name, ticker, start_date, end_date):
    """Pobiera raporty dla JEDNEJ spółki ze strony stockwatch.pl."""
    target_url = f"https://www.stockwatch.pl/gpw/{company_name.lower()},komunikaty,wskazniki.aspx"
    print(f"\nPobieram raporty dla spółki {company_name}...")
    
    found_reports = []
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' }
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        response = requests.get(target_url, headers=headers, verify=False, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        main_table = soup.find('table', class_='cctabdt')
        
        if not main_table:
            print(f"  -> Nie znaleziono tabeli z raportami dla {company_name}.")
            return []
        rows = main_table.find_all('tr')
        print(f"  -> Znaleziono tabelę i {len(rows)} wierszy. Filtrowanie...")
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3: continue
            try:
                date_text = cells[0].text.strip()
                report_date = datetime.datetime.strptime(date_text, '%Y-%m-%d').date()
                if start_date <= report_date <= end_date:
                    title_element = cells[2].find('a')
                    title = title_element.text.strip()
                    link = title_element['href']
                    if not link.startswith('http'): link = "https://www.stockwatch.pl" + link
                    found_reports.append({'company': company_name, 'date': report_date.strftime('%Y-%m-%d'), 'title': title, 'link': link})
            except (ValueError, IndexError, AttributeError):
                continue
    except requests.exceptions.RequestException as e:
        print(f"Wystąpił błąd podczas połączenia dla {company_name}: {e}")
    return found_reports

def generate_html_page(all_reports_data, monitored_companies, start_date, end_date):
    """
    Generuje stronę HTML z raportami pogrupowanymi według spółek.
    """
    reports_by_company = {}
    for report in all_reports_data:
        company_name = report['company']
        if company_name not in reports_by_company: reports_by_company[company_name] = []
        reports_by_company[company_name].append(report)
    for company_name in reports_by_company:
        reports_by_company[company_name].sort(key=lambda x: x['date'], reverse=True)
        
    company_names_str = ", ".join(monitored_companies)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    html_content = f"""
    <!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8"><title>Raporty ESPI/EBI dla {company_names_str}</title>
    <style>body{{font-family:Segoe UI,system-ui,sans-serif;margin:0;background-color:#f0f2f5}}.container{{max-width:850px;margin:2em auto;padding:1em 2em;background-color:#fff;border:1px solid #ddd;border-radius:8px;box-shadow:0 2px 5px rgba(0,0,0,0.05)}}h1{{color:#1d2d44;border-bottom:2px solid #e0e0e0;padding-bottom:0.5em}}h2{{font-size:1.1em;color:#555;font-weight:normal;line-height:1.6;}}.company-header{{font-size:1.5em;color:#005a87;margin-top:2em;margin-bottom:1em;padding-bottom:0.3em;border-bottom:2px solid #005a87}}.report-item{{border-bottom:1px solid #eee;padding:1.2em .5em;display:flex;align-items:center}}.report-item:last-child{{border-bottom:none}}.report-date{{font-weight:600;color:#333;margin-right:1.5em;min-width:100px}}.report-title a{{text-decoration:none;color:#0d6efd;font-size:1.05em;font-weight:500}}.report-title a:hover{{text-decoration:underline}}.footer{{text-align:center;margin-top:2em;color:#888;font-size:.9em}}</style>
    </head><body><div class="container"><h1>Raporty bieżące i okresowe</h1>
    <h2>
        Monitorowane spółki: {company_names_str}<br>
        Okres: Ostatnie <b>{DAYS_AGO} dni</b> (od {start_date_str} do {end_date_str})
    </h2>
    """
    if not all_reports_data:
        html_content+="<p><strong>Nie znaleziono żadnych nowych raportów w zadanym okresie.</strong></p>"
    else:
        for company_name in monitored_companies:
            if company_name in reports_by_company:
                html_content += f'<div class="company-header">{company_name}</div>'
                for report in reports_by_company[company_name]:
                    html_content+=f"""
                    <div class="report-item">
                        <div class="report-date">{report['date']}</div>
                        <div class="report-title"><a href="{report['link']}" target="_blank" rel="noopener noreferrer">{report['title']}</a></div>
                    </div>
                    """
    html_content+=f"""
    <div class="footer">Strona wygenerowana: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div></div></body></html>
    """
    try:
        with open(OUTPUT_FILENAME,'w',encoding='utf-8') as f:f.write(html_content)
        print(f"\nWygenerowano stronę: {OUTPUT_FILENAME}")
        return True
    except IOError as e:
        print(f"Błąd podczas zapisu pliku: {e}")
        return False

# --- Główna część skryptu ---
if __name__ == '__main__':
    companies_to_monitor = load_companies_from_file(COMPANIES_CONFIG_FILE)
    if not companies_to_monitor:
        print("Zakończono pracę z powodu braku skonfigurowanych spółek.")
    else:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=DAYS_AGO)
        all_found_reports = []
        company_names_list = []
        
        print("✅ Rozpoczynam generowanie strony z raportami...")
        print(f"🗓️ Zakres dat: od {start_date.strftime('%Y-%m-%d')} do {end_date.strftime('%Y-%m-%d')}")

        for company in companies_to_monitor:
            company_names_list.append(company['name'])
            reports = fetch_reports_from_stockwatch(company['name'], company['ticker'], start_date, end_date)
            if reports:
                all_found_reports.extend(reports)
        
        generate_html_page(all_found_reports, company_names_list, start_date, end_date)
