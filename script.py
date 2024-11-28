import csv
import os
import random
import re
import sys
import webbrowser
import time

from datetime import datetime, timedelta
from typing import List
from urllib.parse import urljoin

import imapclient
import pyzmail
from PIL import Image, ImageEnhance
import pytesseract
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger
from playwright.sync_api import sync_playwright
from flask import Flask, jsonify

logger.remove()
logger.add('python.log', rotation="500kb", level="WARNING")
logger.add(sys.stderr, level="INFO")
load_dotenv()

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0",
]
headers = {
    "User-Agent": random.choice(user_agents),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "DNT": "1",
}
# base_url = "https://www.webexpire.fr/encheres"

proxyUrl = 'https://cors-anywhere.herokuapp.com/'

SBR_WS_CDP = os.environ['SBR_WS_CDP']


def get_domain_robot(url: str):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(10000)
        html = page.content()
        page.wait_for_timeout(1000)
        soup = BeautifulSoup(html, 'html.parser')
        button_learn_more = page.get_by_text("Load more")
        page.wait_for_timeout(20000)
        if button_learn_more:
            button_learn_more.click()
        page.wait_for_timeout(30000)
        rows_robot = []
        sections = soup.select_one('section.table.latest_expired_domain_table').select('div.tbody div.trow')
        extract_data_from_robot(sections, rows_robot)

        page.wait_for_timeout(10000)

        print(rows_robot)

        with open('domain_data.csv', mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            header = ['Domain Name', 'Last Checked', 'Page Auth', 'Domain Auth', 'Backlinks', 'Rank',
                      'Referring Domains', 'Referring IPs', 'Citation Flow', 'Trust Flow']
            writer.writerow(header)

            writer.writerows(rows_robot)

        print("Données enregistrées dans domain_data.csv")

        browser.close()

    pass


def extract_data_from_robot(noeuds: str, tab: List[List]):
    unique_domains = set()
    print(len(noeuds))
    for section in noeuds:
        domain_cells = section.select('div.upper div.cell.domain')

        for domain_cell in domain_cells:
            row = []

            domain_name = domain_cell.select_one('.name').text.strip()
            row.append(domain_name)

            if domain_name in unique_domains:
                continue
            unique_domains.add(domain_name)

            last_check = domain_cell.find_next('div', class_='lastcheck').text.strip()
            row.append(last_check)

            columns = [
                'pageauth', 'domainauth', 'backlinks', 'rank', 'refdomain',
                'refip', 'CF', 'TF'
            ]
            for col in columns:
                cell = domain_cell.find_next('div', class_=f'cell {col}')
                row.append(cell.text.strip() if cell else "")
            tab.append(row)
    return tab


def get_domain_godaddy(url: str):
    existing_domains = set()
    try:
        with open("domain_godaddy.csv", mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                if row and len(row) > 2:
                    existing_domains.add(row[2])
    except FileNotFoundError:
        pass

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(20000)
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        godaddy_rows = soup.select("table.table-striped tbody tr")
        rows_godaddy = []
        for row in godaddy_rows:
            row_data = []
            cells = row.find_all('td')

            for cell in cells:
                text = cell.get_text(strip=True)
                row_data.append(text)

            if len(row_data) > 2 and row_data[2] not in existing_domains:
                rows_godaddy.append(row_data)
                existing_domains.add(row_data[2])
        print(rows_godaddy)
        with open("domain_godaddy.csv", mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            if file.tell() == 0:
                header = ["", "Select All", "Nom", "Offres", "Prix*", "Trafic", "Ancienneté",
                          "Entrez une enchère/offre (USD)", "Valeur estimée", "Temps restant", "TF Majestic",
                          "CF Majestic",
                          "Backlinks", "Domaines de référence"]
                writer.writerow(header)

            writer.writerows(rows_godaddy)

        print("Les données ont été enregistrées dans 'domain_godaddy.csv'.")
        browser.close()
    pass


def fetch_confirmation_code(email, password, subject_filter="Your code for ExpiredDomains.net"):
    try:
        print("debut")
        server = imapclient.IMAPClient("imap.mail.yahoo.com", ssl=True)
        print(server)
        server.login(email, password)
        print('login')

        folders_to_check = ["INBOX", "Bulk"]
        for folder in folders_to_check:
            server.select_folder(folder)
            print(f"Recherche dans le dossier : {folder}")

            messages = server.search(['UNSEEN', 'SUBJECT', subject_filter])
            print(f"messages: {messages}")
            if messages:
                for msg_id in messages:
                    raw_message = server.fetch(msg_id, ['BODY[]', 'FLAGS'])
                    message = pyzmail.PyzMessage.factory(raw_message[msg_id][b'BODY[]'])
                    print()
                    if message.text_part:
                        content = message.text_part.get_payload().decode(message.text_part.charset)
                        print("Contenu de l'email :", content)

                        match = re.search(r'Your Code: (\d+)', content)
                        if match:
                            return match.group(1)

        print("Aucun email correspondant trouvé dans les dossiers vérifiés.")
        return None
    except Exception as e:
        print(f"Erreur lors de la récupération de l'email : {e}")
        return None


def fetch_gmail_code(email, password, subject_filter="Your code for ExpiredDomains.net"):
    try:
        server = imapclient.IMAPClient("imap.gmail.com", ssl=True)
        server.login(email, password)

        folders_to_check = ["INBOX", "[Gmail]/Spam"]
        for folder in folders_to_check:
            server.select_folder(folder)
            # print(f"Recherche dans le dossier : {folder}")

            messages = server.search(['UNSEEN', 'SUBJECT', subject_filter])

            if messages:
                for msg_id in messages:
                    raw_message = server.fetch(msg_id, ['BODY[]', 'FLAGS'])
                    message = pyzmail.PyzMessage.factory(raw_message[msg_id][b'BODY[]'])

                    if message.text_part:
                        content = message.text_part.get_payload().decode(message.text_part.charset)
                        # print("Contenu de l'email :", content)

                        # match = re.search(r'Your Code: (\d+)', content)
                        match = re.search(r'\b\d{6}\b', content)
                        # match = re.search(r'Your Code: \*?(\d+)\*?', content)

                        # print('extraction du code', match)
                        if match:
                            return match.group(0)

        print("Aucun email correspondant trouvé dans les dossiers vérifiés.")
        return None
    except Exception as e:
        print(f"Erreur lors de la récupération de l'email : {e}")
        return None


def open_debug_view(page):
    client = page.context.new_cdp_session(page)
    logger.debug(f'client {client}')
    frame_tree = client.send('Page.getFrameTree', {})
    frame_id = frame_tree['frameTree']['frame']['id']
    logger.debug(f'frame_id {frame_id}')
    inspect = client.send('Page.inspect', {'frameId': frame_id})
    inspect_url = inspect['url']
    logger.debug(f'inspect {inspect_url}')
    webbrowser.open(inspect_url)


def filterThePage(page):
    try:
        if page.get_by_role("link", name="Show Filter"):
            page.get_by_role("link", name="Show Filter").click()
    except Exception as e:
        logger.info(f'Impossibe de trouver le lien "Show Filter": {e}')
        raise Exception from e

    page.wait_for_timeout(2000)
    try:
        if page.get_by_label("only new last 12 hours"):
            page.get_by_label("only new last 12 hours").check()
    except Exception as e:
        logger.info(f"Impossible de voir le checkbox 'only new last 24 hours': {e}")
        raise Exception from e
    page.wait_for_timeout(2000)
    try:
        page.get_by_label("Domains per Page").select_option("200")
    except Exception as e:
        logger.info(f"Impossible de voir la selection 'Domains par Page': {e}")
        raise Exception from e
    try:
        page.get_by_label("no consecutive Hyphens").check()
    except Exception as e:
        logger.info(f"Impossible de trouver le checkbox 'no consecutive Hyphens': {e}")
        raise Exception from e
    page.wait_for_timeout(2000)
    try:
        page.get_by_label("no Adult Names").check()
    except Exception as e:
        logger.info(f"Impossible de trouver le checkbox 'no Adult Names': {e}")
        raise Exception from e
    page.wait_for_timeout(2000)
    try:
        page.get_by_label("Backlinks").click()
        page.get_by_label("Backlinks").fill("1")
    except Exception as e:
        logger.info(f"Impossible de trouver le champs 'Backlinks > min ': {e}")
        raise Exception from e
    page.wait_for_timeout(2000)
    try:
        page.get_by_text("Additional").click()
    except Exception as e:
        logger.info(f"Impossible de trouver le bouton 'Additional': {e}")
        raise Exception from e
    page.wait_for_timeout(3000)
    try:
        page.locator("input[name=\"ftldsblock\"]").click()
        page.locator("input[name=\"ftldsblock\"]").fill(".cn .hk .ru .com.cn")
    except Exception as e:
        logger.info(f'Impossible de trouver le champ \'TLD Blocklist\': {e}')
        raise Exception from e
    try:
        if page.get_by_role("button", name="Apply Filter"):
            page.get_by_role("button", name="Apply Filter").click()
    except Exception as e:
        logger.info(f"Impossible de trouver le button 'Apply Filter': {e}")
        raise Exception from e
    page.wait_for_timeout(10000)
    page.get_by_role("link", name="Show Filter").click()


def get_domains_from_expired_domains(pw, url: str, username: str, password: str, bright_data: True, headless=False):
    if bright_data:
        browser = pw.firefox.connect_over_cdp(SBR_WS_CDP)
    else:
        browser = pw.chromium.launch(headless=headless)
    context = browser.new_context()
    context.set_default_timeout(60000)

    page = context.new_page()
    # page.set_extra_http_headers(headers)
    if bright_data and not headless:
        open_debug_view(page)
    page.goto(url)
    page.wait_for_timeout(10000)
    try:
        if page.locator("#topline").get_by_role("link", name="Login"):
            page.locator("#topline").get_by_role("link", name="Login").click()
    except Exception as e:
        logger.info(f'Impossible de trouver le lien login: {e}')
        raise Exception from e

    page.wait_for_timeout(2000)
    try:
        if page.get_by_placeholder("Username"):
            page.get_by_placeholder("Username").click(),
            page.get_by_placeholder("Username").fill(username)
    except Exception as e:
        logger.info(f'Impossible de trouver le champ username: {e}')
        raise Exception from e
    page.wait_for_timeout(2000)

    try:
        if page.get_by_placeholder("Password"):
            page.get_by_placeholder("Password").click()
            page.get_by_placeholder("Password").fill(password)
    except Exception as e:
        logger.info(f'Impossible de trouver le champ password {e}')
        raise Exception from e
    page.wait_for_timeout(2000)
    try:
        if page.get_by_label("Remember Me"):
            page.get_by_label("Remember Me").check()
    except Exception as e:
        logger.info(f'Impossible de trouver le checkbox: {e}')
        raise Exception from e
    page.wait_for_timeout(2000)
    try:
        if page.get_by_role("button", name="Login"):
            page.get_by_role("button", name="Login").click()
    except Exception as e:
        logger.info(f'Impossible de trouver le bouton login: {e}')
        raise Exception from e
    page.wait_for_timeout(5000)
    #page.pause()
    email = "melyssachristian476@gmail.com"
    # password = "November172024"
    password = "ekkr vihz safe kadp"
    # code = fetch_confirmation_code(email, password)
    code = fetch_gmail_code(email, password)
    print(f"Code de verification récupéré {code}")
    page.wait_for_timeout(10000)
    try:
        if code:
            #print(code)
            page.get_by_placeholder("Your Code").click()
            page.get_by_placeholder("Your Code").fill(code)
            page.wait_for_timeout(2000)
            page.get_by_role("button", name="Verify Code").click()
            page.wait_for_timeout(10000)
    except Exception as e:
        logger.info(f"Aucun code trouvé: {e}")
        raise Exception from e
    try:
        if page.get_by_role("link", name="Pending Delete", exact=True):
            page.get_by_role("link", name="Pending Delete", exact=True).click()
            page.wait_for_timeout(2000)
            #page.pause()
            filterThePage(page)
            logger.info("page pending deleted domains filtrée")
            count = 0
            while count <= 2:
                logger.info('On entre bien dans la boucle')
                page.set_default_timeout(30000)
                html = page.content()
                page.wait_for_timeout(3000)
                soup = BeautifulSoup(html, 'html.parser')
                page.wait_for_timeout(3000)

                trs = soup.find('table', class_="base1").find('tbody').find_all('tr')

                page.wait_for_timeout(2000)
                # page.pause()
                # print(f'noeud \'trs\' extraite: {trs}')
                data = []
                unique_domains = set()
                for row in trs:
                    cells = row.find_all("td")
                    logger.info(f'Récupérer toutes les cellules{cells}')
                    if not cells:
                        continue
                    domain = cells[0].a.text.strip() if cells[0].a else "-"
                    if domain in unique_domains:
                        continue

                    unique_domains.add(domain)
                    length = cells[3].text.strip()
                    backlinks = cells[4].a.text.strip() if cells[4].a else "-"
                    domain_popularity = cells[5].a.text.strip() if cells[5].a else "-"
                    creation_date = cells[6].text.strip()
                    first_seen = cells[7].a.text.strip() if cells[7].a else "-"
                    saved_results = cells[8].a.text.strip() if cells[8].a else "-"
                    global_rank = cells[9].a.text.strip() if cells[9].a else "-"
                    tld_registered = cells[10].a.text.strip() if cells[10].a else "-"
                    status_com = cells[11].span.text.strip() if cells[11].span else "-"
                    status_net = cells[12].span.text.strip() if cells[12].span else "-"
                    status_org = cells[13].span.text.strip() if cells[13].span else "-"
                    status_biz = cells[14].span.text.strip() if cells[14].span else "-"
                    status_info = cells[15].span.text.strip() if cells[15].span else "-"
                    status_de = cells[16].span.text.strip() if cells[16].span else "-"
                    date_scraping = datetime.now().strftime("%Y-%m-%d")
                    add_date = cells[18].text.strip() if cells[18] else "-"
                    end_date = cells[21].a.text.strip() if cells[21].a else "-"

                    # Ajouter les données à la liste
                    data.append([
                        domain, length, backlinks, domain_popularity, creation_date,
                        first_seen, saved_results, global_rank, tld_registered,
                        status_com, status_net, status_org, status_biz,
                        status_info, status_de, date_scraping, add_date, end_date
                    ])
                    logger.info(f"Données extraites de la table à la page {count}")
                header = [
                    "Domain", "Length", "Backlinks", "Domain Pop", "Creation Date",
                    "First Seen", "Crawl Results", "Global Rank", "TLD Registered",
                    ".com", ".net", ".org", ".biz", ".info", ".de", "Date Scraping", "Add Date", "End Date"
                ]
                with open("pending_delete1.csv", "a", newline="", encoding="utf-8") as csvfile:
                    csvwriter = csv.writer(csvfile)
                    if csvfile.tell() == 0:
                        csvwriter.writerow(header)
                    csvwriter.writerows(data)  # Écrire les données
                logger.info(f'les données de la page {count} sont extraites')

                page.wait_for_timeout(2000)
                # logger.info(f'screenshot_{count} est supprimé avec succés')
                try:
                    if page.get_by_role("link", name="Next Page »").first:
                        page.get_by_role("link", name="Next Page »").first.click()
                except Exception as e:
                    logger.info(f'Impossible de trouver le lien "Next Page": {e}')
                    raise Exception from e
                page.wait_for_timeout(30000)
                # print(count)
                count += 1
                logger.info('On sort bien de la boucle')
    except Exception as e:
        logger.info(f'Impossible de trouver le lien Pending Delete {e}')
        raise Exception from e
    try:
        if page.get_by_role("link", name="Deleted Domains"):
            page.get_by_role("link", name="Deleted Domains").click()
            page.wait_for_timeout(2000)
            filterThePage(page)
            logger.info("page deleted domains filtrée")
            counter = 0
            while counter <= 2:
                logger.info('On est bien entré dans la boucle pour deleted domains')
                page.set_default_timeout(30000)
                html = page.content()
                page.wait_for_timeout(3000)
                soup = BeautifulSoup(html, 'html.parser')
                page.wait_for_timeout(3000)

                trs = soup.find('table', class_="base1").find('tbody').find_all('tr')

                page.wait_for_timeout(2000)
                # print(f'noeud \'trs\' extraite: {trs}')
                # page.pause()
                datas = []
                seen_domains = set()

                for row in trs:
                    cells = row.find_all("td")
                    #logger.info(f'Récupérer toutes les cellules{cells}')
                    if len(cells) < 6:
                        continue

                    domain_name = cells[0].a.text.strip() if cells[0] else '-'
                    if domain_name in seen_domains:
                        continue

                    seen_domains.add(domain_name)
                    creation_date = cells[1].text.strip()
                    backlinks = cells[2].a.text.strip() if cells[2].a else "-"
                    length = cells[3].text.strip()
                    domain_popularity = cells[4].a.text.strip() if cells[4].a else "-"
                    tld_registered = cells[5].a.text.strip() if cells[5].a else "-"
                    date_scraping = datetime.now().strftime("%Y-%m-%d")
                    add_date = cells[18].text.strip() if cells[18] else '-'
                    field_change = cells[21].text.strip() if cells[18] else '-'

                    datas.append([
                        domain_name, creation_date, backlinks, length, domain_popularity, tld_registered, date_scraping,
                        add_date, field_change
                    ])

                columns = ['Domain', 'Creation Date', 'Backlinks', 'Length', 'Domain Popularity', 'TLD Registered',
                           'Date Scraping', 'add_date', 'field_change']
                csv_file = "deleted_domains_expired_net1.csv"

                with open(csv_file, mode="a", newline='', encoding="utf-8") as file:
                    writer = csv.writer(file)

                    if file.tell() == 0:
                        writer.writerow(columns)

                    writer.writerows(datas)
                logger.info(f'Données extraite à le page {counter}')
                page.wait_for_timeout(2000)
                try:
                    if page.get_by_role("link", name="Next Page »").first:
                        page.get_by_role("link", name="Next Page »").first.click()
                        page.wait_for_timeout(30000)
                except Exception as e:
                    logger.info(f'Impossible de trouver le bouton suivant: {e}')
                    raise Exception from e
                # print(count)
                counter += 1
                logger.info('On est bien sortie de la boucle')
    except Exception as e:
        logger.info(f'Impossible de trouver le lien Pending Delete: {e}')
        raise Exception from e
    logger.info('--------Fin d\'execution--------')
    browser.close()


def get_domains_from_expired_domains_com(pw, url: str, bright_data: True, headless=False):
    AUTH1 = 'brd-customer-hl_5b25fc9f-zone-scraping_browser1:qy1ng0c78qjo'
    SBR_WS_CDP1 = f'https://{AUTH1}@brd.superproxy.io:9222'
    if bright_data:
        browser = pw.chromium.connect_over_cdp(SBR_WS_CDP1, timeout=30000)
    else:
        browser = pw.chromium.launch(headless=headless)
    page = browser.new_page()
    # context.set_default_timeout(60000)
    # page = context.new_page()
    # page.set_extra_http_headers(headers)

    if bright_data and not headless:
        open_debug_view(page)
    page.goto(url)
    page.wait_for_timeout(10000)
    if page.get_by_role("link", name="Login"):
        page.get_by_role("link", name="Login").click()
    else:
        logger.info('Impossible de trouver le button login')

    page.wait_for_timeout(2000)
    if page.get_by_placeholder("User Name"):
        page.get_by_placeholder("User Name").click()
        page.get_by_placeholder("User Name").fill("dedaxunoc")
    else:
        logger.info('Impossible de trouver le champ username')
    page.wait_for_timeout(2000)

    if page.get_by_placeholder("Password"):
        page.get_by_placeholder("Password").click()
        page.get_by_placeholder("Password").fill("Pa$$w0rd!")
    else:
        logger.info('Impossible de trouver le champ password')
    page.wait_for_timeout(2000)

    if page.get_by_role("button", name="Login"):
        page.get_by_role("button", name="Login").click()
    else:
        logger.info('Impossible de trouver le bouton login')
    page.wait_for_timeout(10000)
    # page.pause()

    count = 0
    while True:
        logger.info('On entre bien dans la boucle')
        if count == 300:
            break
        page.set_default_timeout(2000)
        print(f'screenshot {count}')
        if page.get_by_role("table"):
            page.get_by_role("table").screenshot(path=f"pages/screenshot_{count}.png")
            logger.info(f'table {count} capturé')
        else:
            logger.info('Impossible de trouver la l\'element "table"')
        # page.pause()
        delay = random.randint(5, 10)
        logger.info(f"Pause de {delay} secondes avant la récupération des données sur screenshot_{count}.png")
        time.sleep(delay)

        img_path = f"pages/screenshot_{count}.png"
        img = Image.open(img_path)
        raw_data = pytesseract.image_to_string(img)
        # print('raw_data:',raw_data)
        lines = raw_data.strip().split('\n')
        # print('lines', lines)
        unique_domains = set()
        domains = []
        backlinks = []
        end_dates = []
        date_plus_10_jours = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

        domain_regex = r'\b[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b'
        date_regex = r'\b\d{4}-\d{2}-\d{2}\b'

        for line in lines:
            domain_match = re.search(domain_regex, line)
            if domain_match:
                domains.append(domain_match.group())
                for domain in domains:
                    unique_domains.add(domain)
            date_match = re.search(date_regex, line)
            if date_match:
                end_dates.append(date_match.group())
                print(end_dates)

        domains = list(unique_domains)
        print("Domains:", domains)
        print("Backlinks:", backlinks)
        print("End Dates:", end_dates)
        # page.pause()
        num_records = min(len(domains), len(end_dates))
        current_date = datetime.now().strftime("%Y-%m-%d")
        data = [
            [domains[i], current_date, end_dates[i]]
            for i in range(num_records)
        ]
        print('date du jour:', datetime.now())
        columns = ["Domain", "Add Date", "End Date"]

        with open("domains_from_expired_domain_com.csv", mode="a", newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            if count == 0 and file.tell() == 0:
                writer.writerow(columns)

            writer.writerows(data)
        os.remove(img_path)
        logger.info(f'screenshot_{count} est supprimé avec succés')
        page.wait_for_timeout(30000)
        if page.get_by_role("link", name="next"):
            page.get_by_role("link", name="next").click()
        else:
            logger.info('Impossible de trouver le button "next"')
        # print(count)
        page.wait_for_timeout(5000)
        count += 1
        logger.info('On sort bien de la boucle')

    logger.info('--------Fin d\'execution--------')
    browser.close()


def save_domains(page: str, count: int):
    section_checked = page.locator("section").filter(has_text="Domain Last checked the exact")
    if section_checked:
        table_height = \
            section_checked.bounding_box()['height']
        page.set_viewport_size({"width": 1200, "height": int(table_height) + 100})

        section_checked.scroll_into_view_if_needed()

        section_checked.screenshot(
            path=f"pages/screenshot_{count}.png")
    else:
        logger.info('Impossible de trouver cette section')

    # section_expiring = page.locator("section").filter(has_text="DomainPaid until Expiring the")
    # if section_expiring:
    #     table_height = \
    #         section_expiring.bounding_box()[
    #             'height']
    #     page.set_viewport_size({"width": 1200, "height": int(table_height) + 100})
    #
    #     section_expiring.scroll_into_view_if_needed()
    #
    #     section_expiring.screenshot(
    #         path=f"pages/screenshot_{count}.png")
    # else:
    #     logger.info('Impossible de trouver cette section')

    img_path = f"pages/screenshot_{count}.png"
    img = Image.open(img_path)
    raw_data = pytesseract.image_to_string(img)

    domain_pattern = r'\b[a-zA-Z0-9-]+\.[a-z]{2,6}\b'
    data_extracts = re.findall(domain_pattern, raw_data)

    unique_domains = set()
    for line in data_extracts:
        if re.match(r'^[a-zA-Z0-9-]+\.[a-z]{2,}$', line):
            unique_domains.add(line.strip())

    existing_domains = set()

    if os.path.exists("domains_from_robot.csv"):
        with open("domains_from_robot.csv", mode="r", newline='', encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                existing_domains.add(row[0])

    new_domains = unique_domains - existing_domains
    print(len(new_domains))
    if new_domains:
        current_date = datetime.now().strftime("%Y-%m-%d")
        data = [
            [domain, current_date]
            for domain in new_domains
        ]

        with open("domains_from_robot.csv", mode="a", newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            if count == 0 and file.tell() == 0:
                writer.writerow(["Domain", "Add Date"])  # Ajouter les en-têtes si le fichier est vide
            writer.writerows(data)

        logger.info(f"Ajout de {len(new_domains)}:{new_domains} nouveaux domaines.")
    else:
        logger.info("Aucun nouveau domaine trouvé.")

    os.remove(img_path)
    logger.info(f'screenshot_{count} est supprimé avec succès')


def navigate_in_the_page(page: str, count: int):
    for i in ['net', 'org', 'fr', 'us']:
        if page.locator(".flag-text > .svg-inline--fa > path"):
            page.locator(".flag-text > .svg-inline--fa > path").click()
            page.wait_for_timeout(3000)
            if page.locator("div").filter(has_text=re.compile(rf"^\.{i}$")).first:
                page.locator("div").filter(has_text=re.compile(rf"^\.{i}$")).first.click()
                logger.info(f'Click sur le button ".{i}"')
                page.wait_for_timeout(3000)
                if page.get_by_text("Load more"):
                    page.get_by_text("Load more").click()
                    logger.info(f'Click sur le button "Load more" apres le click du button ".{i}"')
                    page.wait_for_timeout(2000)
                else:
                    logger.info('Impossible de trouver le button "Load more" apres le click du button ".net"')

                save_domains(page=page, count=count)

                page.wait_for_timeout(10000)
            else:
                logger.info('Impossible de trouver le button ".net" ')
        else:
            logger.info('Impossible de trouver le button dropdown')

    # if page.locator(".flag-text > .svg-inline--fa > path"):
    #     page.locator(".flag-text > .svg-inline--fa > path").click()
    #     page.wait_for_timeout(3000)
    #     if page.locator("div").filter(has_text=re.compile(r"^\.org$")).first:
    #         page.locator("div").filter(has_text=re.compile(r"^\.org$")).first.click()
    #         page.wait_for_timeout(3000)
    #         if page.get_by_text("Load more"):
    #             page.get_by_text("Load more").click()
    #             page.wait_for_timeout(2000)
    #         else:
    #             logger.info('Impossible de trouver le button "Load more" aprés le click du button ".org"')
    #
    #         save_domains(page=page, count=count)
    #
    #         page.wait_for_timeout(10000)
    #     else:
    #         logger.info('Impossible de trouver le button ".org" ')
    # else:
    #     logger.info('Impossible de trouver le button dropdown')


def get_domains_from_domains_robot(pw, url: str, bright_data: True, headless: False):
    if bright_data:
        browser = pw.chromium.connect_over_cdp(SBR_WS_CDP)
    else:
        browser = pw.chromium.launch(headless=headless)

    page = browser.new_page()
    if bright_data and not headless:
        open_debug_view(page)

    page.goto(url)

    count = 0
    while True:
        logger.info("Entrer de la boucle")
        if count == 2:
            break

        count1 = 0
        while count1 <= 5:
            if page.get_by_text("Load more"):
                page.get_by_text("Load more").click()
                logger.info(f"click n°{count1}")
            else:
                logger.info('Impossible de trouver le button "Load more" ')

            page.wait_for_timeout(2000)

            save_domains(page=page, count=count)
            print(f"données recupérées {count1} fois")
            count1 += 1

        page.wait_for_timeout(10000)

        navigate_in_the_page(page=page, count=count)
        logger.info("Finish")

        # if page.get_by_role("link", name="Domains Expiring Soon"):
        #     page.get_by_role("link", name="Domains Expiring Soon").click()
        #     if page.get_by_text("Load more"):
        #         page.get_by_text("Load more").click()
        #         page.wait_for_timeout(2000)
        #         page.pause()
        #         #save_domains(page=page, count=count)
        #         section_expiring = page.locator("section").filter(has_text="DomainPaid until Expiring the")
        #         if section_expiring:
        #             table_height = \
        #                 section_expiring.bounding_box()[
        #                     'height']
        #             page.set_viewport_size({"width": 1200, "height": int(table_height) + 100})
        #
        #             section_expiring.scroll_into_view_if_needed()
        #
        #             section_expiring.screenshot(
        #                 path=f"pages/screenshot_{count}.png")
        #         else:
        #             logger.info('Impossible de trouver cette section')
        #
        #         img_path = f"pages/screenshot_{count}.png"
        #         img = Image.open(img_path)
        #         raw_data = pytesseract.image_to_string(img)
        #
        #         domain_pattern = r'\b[a-zA-Z0-9-]+\.[a-z]{2,6}\b'
        #         data_extracts = re.findall(domain_pattern, raw_data)
        #
        #         unique_domains = set()
        #         for line in data_extracts:
        #             if re.match(r'^[a-zA-Z0-9-]+\.[a-z]{2,}$', line):
        #                 unique_domains.add(line.strip())
        #
        #         existing_domains = set()
        #         if os.path.exists("domains_from_robot.csv"):
        #             with open("domains_from_robot.csv", mode="r", newline='', encoding="utf-8") as file:
        #                 reader = csv.reader(file)
        #                 next(reader)
        #                 for row in reader:
        #                     existing_domains.add(row[0])
        #
        #         new_domains = unique_domains - existing_domains
        #         if new_domains:
        #             current_date = datetime.now().strftime("%Y-%m-%d")
        #             data = [
        #                 [domain, current_date]
        #                 for domain in new_domains
        #             ]
        #
        #             with open("domains_from_robot.csv", mode="a", newline='', encoding="utf-8") as file:
        #                 writer = csv.writer(file)
        #                 if count == 0 and file.tell() == 0:
        #                     writer.writerow(["Domain", "Add Date"])  # Ajouter les en-têtes si le fichier est vide
        #                 writer.writerows(data)
        #
        #             logger.info(f"Ajout de {len(new_domains)}:{new_domains} nouveaux domaines.")
        #         else:
        #             logger.info("Aucun nouveau domaine trouvé.")
        #
        #         os.remove(img_path)
        #         logger.info(f'screenshot_{count} est supprimé avec succès')
        #         navigate_in_the_page(page=page, count=count)
        #
        # else:
        #     logger.info('Impossible de trouver le button "Domains Expiring Soon" ')

        count += 1
        logger.info("Sortie de la boucle")

    browser.close()


def main():
    start_time = time.time()
    expired_domain_url: str = 'https://www.expireddomains.net'
    domain_robot_url = "https://thedomainrobot.com/"
    godaddy_url = "https://auctions.godaddy.com/beta"
    expired_domain_url_com: str = 'https://www.expireddomains.com'
    with sync_playwright() as playwright:
        logger.info('Connexion sur web scraping en cours')
        # get_domains_from_expired_domains_com(pw=playwright, url=expired_domain_url_com, bright_data=False, headless=False)

        # username: sagarroy kateperry aevansnappiah melyssachristian476
        # password: Sagarroy@12 November172024 Omoghana01@
        get_domains_from_expired_domains(pw=playwright, url=expired_domain_url, username="melyssachristian476",
                                         password="melyssachristian476", bright_data=False, headless=False)

        # get_domains_from_domains_robot(pw=playwright, url=domain_robot_url, bright_data=False, headless=False)

    # get_domain_robot(url=domain_robot_url)
    # get_domain_godaddy(url=godaddy_url)

    # Utilisation
    #email = "kateperry017@yahoo.com"
    #email = "melyssachristian476@gmail.com"
    # password = "November172024"
    #password = "ekkr vihz safe kadp"
    # code = fetch_confirmation_code(email, password)
    #code = fetch_gmail_code(email, password)
    #if code:
    #    print(code)
    #else:
    #    print("Aucun code trouvé.")

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Le script a mis {execution_time:.2f} secondes à s'exécuter.")


if __name__ == '__main__':
    main()
