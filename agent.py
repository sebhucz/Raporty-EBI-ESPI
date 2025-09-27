import requests
from bs4 import BeautifulSoup
import datetime
import webbrowser
import os
import urllib3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- Konfiguracja ---
DAYS_AGO = 7
OUTPUT_FILENAME = "raport_gieldowy.html"
COMPANIES_CONFIG_FILE = "spolki.txt"
RECIPIENTS_CONFIG_FILE = "odbiorcy.txt"

# Konfiguracja modułu email
GMAIL_USER = 'sebastian.huczek@gmail.com'
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
RECIPIENT_EMAIL = 'sebastian.huczek@gmail.com'


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

def load_recipients_from_file(filename):
    """Wczytuje listę odbiorców z pliku tekstowego."""
    recipients = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#'):
                    recipients.append(line.strip())
        print(f"✅ Pomyślnie wczytano {len(recipients)} odbiorców z pliku '{filename}'.")
        return recipients
    except FileNotFoundError:
        print(f"❌ BŁĄD: Nie znaleziono pliku z odbiorcami '{filename}'!")
        return []


# --- Pozostałe funkcje ---

def send_email_with_gmail(html_content, subject, recipients_list):
    if GMAIL_USER == 'twoj.adres@gmail.com' or GMAIL_APP_PASSWORD == 'tutaj_wklej_haslo_do_aplikacji':
        print("🟡 Ostrzeżenie: Dane nadawcy maila nie zostały skonfigurowane. Pomijam wysyłkę.")
        return
    if not recipients_list:
        print("🟡 Ostrzeżenie: Lista odbiorców jest pusta. Pomijam wysyłkę.")
        return

    print(f"📧 Przygotowuję email do wysłania do {len(recipients_list)} odbiorców...")
    msg = MIMEMultipart('alternative')
    msg['From'] = GMAIL_USER
    msg['To'] = ", ".join(recipients_list)
    msg['Subject'] = subject
    part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(part)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Email został pomyślnie wysłany!")
    except Exception as e:
        print(f"❌ Wystąpił błąd podczas wysyłania maila: {e}")


def fetch_reports_from_stockwatch(company_name, ticker, start_date, end_date):
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
                    print(f"    -> Znaleziono raport: {title[:60]}...")
                    found_reports.append({'company': company_name, 'date': report_date.strftime('%Y-%m-%d'), 'title': title, 'link': link})
            except (ValueError, IndexError, AttributeError):
                continue
    except requests.exceptions.RequestException as e:
        print(f"Wystąpił błąd podczas połączenia dla {company_name}: {e}")
    return found_reports


# --- ZMIANA W TEJ FUNKCJI ---
def generate_html_report(all_reports_data, monitored_companies, start_date, end_date):
    """
    Generuje JEDEN zbiorczy plik HTML z raportami pogrupowanymi według spółek.
    """
    reports_by_company = {}
    for report in all_reports_data:
        company_name = report['company']
        if company_name not in reports_by_company: reports_by_company[company_name] = []
        reports_by_company[company_name].append(report)
    for company_name in reports_by_company:
        reports_by_company[company_name].sort(key=lambda x: x['date'], reverse=True)
        
    company_names_str = ", ".join(monitored_companies)
    
    # Formatowanie dat do wyświetlenia
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
    <div class="footer">Raport wygenerowano: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div></div></body></html>
    """
    try:
        with open(OUTPUT_FILENAME,'w',encoding='utf-8') as f:f.write(html_content)
        print(f"\nWygenerowano zbiorczy raport: {OUTPUT_FILENAME}")
        return True, html_content
    except IOError as e:
        print(f"Błąd podczas zapisu pliku: {e}")
        return False, None

# --- Główna część skryptu ---
if __name__ == '__main__':
    companies_to_monitor = load_companies_from_file(COMPANIES_CONFIG_FILE)
    email_recipients = load_recipients_from_file(RECIPIENTS_CONFIG_FILE)

    if not companies_to_monitor:
        print("Zakończono pracę z powodu braku skonfigurowanych spółek.")
    else:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=DAYS_AGO)
        
        all_found_reports = []
        company_names_list = []
        
        print("✅ Rozpoczynam wyszukiwanie raportów...")
        print(f"🗓️ Zakres dat: od {start_date.strftime('%Y-%m-%d')} do {end_date.strftime('%Y-%m-%d')}")

        for company in companies_to_monitor:
            company_names_list.append(company['name'])
            reports = fetch_reports_from_stockwatch(company['name'], company['ticker'], start_date, end_date)
            if reports:
                all_found_reports.extend(reports)
        
        # --- ZMIANA W WYWOŁANIU FUNKCJI ---
        success, report_html = generate_html_report(all_found_reports, company_names_list, start_date, end_date)
        
        if success:
            print("Otwieram raport w przeglądarce...")
            try:
                webbrowser.open('file://' + os.path.realpath(OUTPUT_FILENAME))
            except Exception as e:
                print(f"Nie udało się automatycznie otworzyć pliku. Otwórz go ręcznie. Błąd: {e}")

            if all_found_reports:
                email_subject = f"Raport Giełdowy: Nowe komunikaty dla {', '.join(company_names_list)}"

                send_email_with_gmail(report_html, email_subject, email_recipients)

