# To jest zawartość pliku: agent_page.py
import requests, bs4, datetime, os, urllib3

DAYS_AGO = 7 # Strona zawsze pokazuje 7 dni wstecz
OUTPUT_FILENAME = "index.html" # Zapisuje jako index.html
COMPANIES_CONFIG_FILE = "spolki.txt"

# --- Tutaj wklejamy tylko te funkcje, które są potrzebne: ---
# load_companies_from_file, fetch_reports_from_stockwatch, generate_html_page
# (Poniżej wklejam kompletny kod dla pewności)
def load_companies_from_file(filename):
    companies = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#'):
                    parts = line.strip().split(',')
                    if len(parts) == 2: companies.append({'name': parts[0].strip(), 'ticker': parts[1].strip()})
        print(f"✅ Wczytano {len(companies)} spółek z '{filename}'.")
        return companies
    except FileNotFoundError:
        print(f"❌ BŁĄD: Nie znaleziono pliku '{filename}'!")
        return []

def fetch_reports_from_stockwatch(company_name, ticker, start_date, end_date):
    target_url = f"https://www.stockwatch.pl/gpw/{company_name.lower()},komunikaty,wskazniki.aspx"
    print(f"\nPobieram raporty dla {company_name}...")
    found_reports = []
    headers = { 'User-Agent': 'Mozilla/5.0 ...' }
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        response = requests.get(target_url, headers=headers, verify=False, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        main_table = soup.find('table', class_='cctabdt')
        if not main_table:
            print(f"  -> Nie znaleziono tabeli dla {company_name}.")
            return []
        rows = main_table.find_all('tr')
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
            except (ValueError, IndexError, AttributeError): continue
    except requests.exceptions.RequestException as e:
        print(f"Wystąpił błąd dla {company_name}: {e}")
    return found_reports

def generate_html_page(all_reports_data, monitored_companies, start_date, end_date):
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
    <style>/* ... style CSS ... */</style>
    </head><body><div class="container"><h1>Raporty bieżące i okresowe</h1>
    <h2>Monitorowane spółki: {company_names_str}<br>Okres: Ostatnie <b>{DAYS_AGO} dni</b> (od {start_date_str} do {end_date_str})</h2>
    """
    if not all_reports_data:
        html_content+="<p><strong>Nie znaleziono żadnych nowych raportów w zadanym okresie.</strong></p>"
    else:
        for company_name in monitored_companies:
            if company_name in reports_by_company:
                html_content += f'<div class="company-header">{company_name}</div>'
                for report in reports_by_company[company_name]:
                    html_content+=f"""
                    <div class="report-item"><div class="report-date">{report['date']}</div>
                    <div class="report-title"><a href="{report['link']}" target="_blank">{report['title']}</a></div></div>"""
    html_content+=f"""
    <div class="footer">Strona wygenerowana: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div></div></body></html>
    """
    try:
        with open(OUTPUT_FILENAME,'w',encoding='utf-8') as f:f.write(html_content)
        print(f"\nWygenerowano stronę: {OUTPUT_FILENAME}")
        return True
    except IOError as e:
        print(f"Błąd zapisu pliku: {e}")
        return False

if __name__ == '__main__':
    companies_to_monitor = load_companies_from_file(COMPANIES_CONFIG_FILE)
    if companies_to_monitor:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=DAYS_AGO)
        all_found_reports = []
        company_names_list = []
        print("✅ Uruchamiam agenta STRONY INTERNETOWEJ...")
        for company in companies_to_monitor:
            company_names_list.append(company['name'])
            reports = fetch_reports_from_stockwatch(company['name'], company['ticker'], start_date, end_date)
            if reports: all_found_reports.extend(reports)
        generate_html_page(all_found_reports, company_names_list, start_date, end_date)