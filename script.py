import csv
import json
import os
import random
import re
import sys
import warnings

import psutil
import urllib3
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

logger.remove()
logger.add('python.log', rotation="500kb", level="WARNING")
logger.add(sys.stderr, level="INFO")
load_dotenv()

warnings.filterwarnings('ignore', category=urllib3.exceptions.NotOpenSSLWarning)
#warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)
SBR_WS_CDP = os.environ['SBR_WS_CDP']


def random_delay(min_delay=1, max_delay=3):
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)


# Function to fetch and rotate user agents
def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 "
        "Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 "
        "Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0"
    ]
    return random.choice(user_agents)


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


def fetch_yahoo_code(email, password, subject_filter="Your code for ExpiredDomains.net"):
    try:
        #print("debut")
        server = imapclient.IMAPClient("imap.mail.yahoo.com", ssl=True)
        #print(server)
        server.login(email, password)
        #print('login')
        folders = server.list_folders()
        #print("Liste des dossiers disponibles :", folders)
        folders_to_check = ["Inbox", "Bulk"]
        available_folders = [folder[2] for folder in server.list_folders()]
        for folder in folders_to_check:
            if folder not in available_folders:
                print(f"Dossier non trouvé : {folder}")
                continue

            server.select_folder(folder)
            #print(f"Recherche dans le dossier : {folder}")

            messages = server.search(['UNSEEN', 'SUBJECT', subject_filter])
            #print(f"messages: {messages}")
            if messages:
                for msg_id in messages:
                    raw_message = server.fetch(msg_id, ['BODY[]', 'FLAGS', 'RFC822.HEADER'])
                    headers_spam = raw_message[msg_id][b'RFC822.HEADER'].decode('utf-8')
                    # Vérifier si l'email a été marqué comme spam
                    if 'X-Spam-Flag: YES' in headers_spam:
                        print("Cet email est marqué comme spam.")

                    message = pyzmail.PyzMessage.factory(raw_message[msg_id][b'BODY[]'])

                    if message.text_part:
                        content = message.text_part.get_payload().decode(message.text_part.charset)
                        #print("Contenu de l'email :", content)

                        #match = re.search(r'Your Code: (\d+)', content)
                        match = re.search(r'\b\d{6}\b', content)
                        if match:
                            return match.group(0)

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
                        #print("Contenu de l'email :", content)

                        match = re.search(r'\b\d{6}\b', content)

                        # print('extraction du code', match)
                        if match:
                            return match.group(0)

        #print("Aucun email correspondant trouvé dans les dossiers vérifiés.")
        #return None
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
        page.wait_for_selector('xpath=//*[@id="listing"]/div[2]/div[1]/span[1]/a')
        logger.info("Le lien 'Show Filter' est bien apercu")
        if page.get_by_role("link", name="Show Filter"):
            page.get_by_role("link", name="Show Filter").click()
    except Exception as e:
        logger.info(f'Impossibe de trouver le lien "Show Filter": {e}')
        raise Exception from e

    page.wait_for_load_state("domcontentloaded")
    random_delay(min_delay=1, max_delay=3)
    try:
        page.wait_for_selector('xpath=//*[@id="flast24"]')
        if page.get_by_label("only new last 24 hours"):
            page.get_by_label("only new last 24 hours").check()
    except Exception as e:
        logger.info(f"Impossible de voir le checkbox 'only new last 24 hours': {e}")
        raise Exception from e

    random_delay(min_delay=1, max_delay=3)
    try:
        page.wait_for_selector('xpath=//*[@id="flimit"]')
        page.get_by_label("Domains per Page").select_option("200")
    except Exception as e:
        logger.info(f"Impossible de voir la selection 'Domains par Page': {e}")
        raise Exception from e

    random_delay(min_delay=1, max_delay=3)
    try:
        page.wait_for_selector('xpath=//*[@id="fconsephost"]')
        page.get_by_label("no consecutive Hyphens").check()
    except Exception as e:
        logger.info(f"Impossible de trouver le checkbox 'no consecutive Hyphens': {e}")
        raise Exception from e

    random_delay(min_delay=1, max_delay=3)
    try:
        page.wait_for_selector('xpath=//*[@id="fadult"]')
        page.get_by_label("no Adult Names").check()
    except Exception as e:
        logger.info(f"Impossible de trouver le checkbox 'no Adult Names': {e}")
        raise Exception from e

    random_delay(min_delay=1, max_delay=3)
    try:
        #page.wait_for_selector('xpath=')
        page.get_by_label("Backlinks").click()
        page.get_by_label("Backlinks").fill("1")
    except Exception as e:
        logger.info(f"Impossible de trouver le champs 'Backlinks > min ': {e}")
        raise Exception from e

    random_delay(min_delay=1, max_delay=3)
    try:
        page.wait_for_selector('xpath=//*[@id="content"]/div/div[1]/form/ul/li[2]/a')
        page.get_by_text("Additional").click()
    except Exception as e:
        logger.info(f"Impossible de trouver le bouton 'Additional': {e}")
        raise Exception from e

    random_delay(min_delay=1, max_delay=3)
    try:
        page.locator("input[name=\"ftldsblock\"]").click()
        page.locator("input[name=\"ftldsblock\"]").fill(".cn .hk .ru .com.cn")
    except Exception as e:
        logger.info(f'Impossible de trouver le champ \'TLD Blocklist\': {e}')
        raise Exception from e

    random_delay(min_delay=1, max_delay=3)
    try:
        page.wait_for_selector('xpath=//*[@id="content"]/div/div[1]/form/div[2]/div/input')
        if page.get_by_role("button", name="Apply Filter"):
            page.get_by_role("button", name="Apply Filter").click()
    except Exception as e:
        logger.info(f"Impossible de trouver le button 'Apply Filter': {e}")
        raise Exception from e

    random_delay(min_delay=1, max_delay=3)


def navigation_on_expired_domains_page(page, count: int, data: List = []):
    try:
        page.mouse.wheel(0, 500)
        page.set_default_timeout(30000)
        html = page.content()
        logger.info('Récupération de la page html')
        random_delay(min_delay=1, max_delay=2)
        soup = BeautifulSoup(html, 'html.parser')
        logger.info("Analyse du code html récupéré")
        trs = soup.find('table', class_="base1").find('tbody').find_all('tr')
        logger.info('Séléction du tableau')

        unique_domains = set()
        for row in trs:
            try:
                cells = row.find_all("td")
                if not cells or len(cells) < 22:
                    logger.warning(f"Ligne ignorée, colonnes manquantes : {cells}")
                    continue

                domain = cells[0].a.text.strip() if cells[0].a else "-"
                if domain in unique_domains:
                    continue

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
                end_date = cells[21].a.text.strip() if cells[21].a else (
                    cells[21].text.strip() if cells[21].text.strip() else "-")
                status = cells[22].a.text.strip() if cells[18] else "-"

                data.append([
                    domain, length, backlinks, domain_popularity, creation_date,
                    first_seen, saved_results, global_rank, tld_registered,
                    status_com, status_net, status_org, status_biz,
                    status_info, status_de, date_scraping, add_date, end_date, status
                ])
                #logger.info(f"Données extraites de la table à la page {count}")
            except Exception as e:
                logger.warning(f"Erreur lors du traitement du domaine: {str(e)}")
                continue
        return data
    except Exception as e:
        logger.error(f"Erreur lors de la navigation sur la page {count}: {str(e)}")
        return data


def get_total_pages(page):
    try:
        # Trouver la div contenant l'information sur le nombre total de pages
        page_info = page.locator("div.pageinfo.right").first.text_content().strip()
        # Extraire le nombre total de pages avec une expression régulière
        match = re.search(r"Page \d+ of ([\d,]+)", page_info)
        if match:
            total_pages = int(match.group(1).replace(",", ""))  # Supprime les virgules et convertit en entier
            print('nombre total de page:', total_pages)
            return total_pages
        else:
            logger.warning("Impossible de trouver le nombre total de pages.")
            return 0
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du nombre de pages : {e}")
        return 0  # Valeur par défaut en cas d'erreur


def load_cookies_from_file():
    try:
        with open("cookies.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_cookies_to_file(cookies):
    with open("cookies.json", "w") as file:
        json.dump(cookies, file)


def monitor_resources():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_usage = psutil.virtual_memory().percent
    print(f"CPU Usage: {cpu_usage}% | Memory Usage: {memory_usage}%")


def get_domains_from_expired_domains(pw, url: str, username: str, password: str, bright_data: False, headless=False):
    if bright_data:
        browser = pw.firefox.connect_over_cdp(SBR_WS_CDP)
    else:
        browser = pw.chromium.launch(headless=headless)

    user_agent = get_random_user_agent()
    logger.info("Récupération aléatoire du user-agent")
    context = browser.new_context(user_agent=user_agent)
    logger.info("Affectation du user-agent")
    #geolocation={"longitude": 2.3522, "latitude": 48.8566},  # Paris
    #timezone_id="Europe/Paris"  # Fuseau horaire de Paris
    # Récupérer les cookies à partir d'une session précédente si disponible
    cookies = load_cookies_from_file()  # Chargez les cookies sauvegardés d'une session précédente
    logger.info("Chargez les cookies sauvegardés d'une session précédente")
    if cookies:
        context.add_cookies(cookies)
        logger.info("Récupérer les cookies à partir d'une session précédente si disponible")

    # Personnalisation du navigateur pour masquer l'automatisation
    context.add_init_script('''() => {
            // Supprimer l'indicateur de l'automatisation
            delete navigator.webdriver;

            // Masquer les API de détection
            Object.defineProperty(navigator, 'permissions', {
                get: function() {
                    return { query: () => ({ state: 'granted' }) };
                }
            });

            // Masquer la trace des fonctionnalités automatiques
            window.chrome = { runtime: {}, app: {} };
        }''')
    logger.info("Personnalisation du navigateur pour masquer l'automatisation")

    context.set_default_timeout(60000)

    # Test de l'accès au site
    try:
        page = context.new_page()
        logger.info("Ouverture d'une page")
        if bright_data and not headless:
            open_debug_view(page)
        page.goto(url)
        logger.info(f"Acces réussi à {url}")
        page.wait_for_load_state('domcontentloaded')  # Attendre le chargement complet
        logger.info("Attendre le chargement complet")
        # Vérification de l'usage des ressources
        monitor_resources()
        logger.info("Vérification de l'usage des ressources")

    except Exception as e:
        print(f"Erreur de connexion au site : {e}")
        browser.close()
        return []
    #page.pause()
    #page.wait_for_timeout(10000)
    page.wait_for_selector("#topline .link a[href='/login/']")
    logger.info("Lien 'Login' est aperçu avec succés")
    try:
        if page.locator("#topline").get_by_role("link", name="Login"):
            page.locator("#topline").get_by_role("link", name="Login").click()
    except Exception as e:
        logger.info(f'Impossible de trouver le lien login: {e}')
        raise Exception from e

    page.wait_for_selector("#inputLogin")
    try:
        if page.get_by_placeholder("Username"):
            page.get_by_placeholder("Username").click(),
            page.get_by_placeholder("Username").fill(username)
    except Exception as e:
        logger.info(f'Impossible de trouver le champ username: {e}')
        raise Exception from e

    page.wait_for_selector('xpath=//*[@id="inputPassword"]')
    try:
        if page.get_by_placeholder("Password"):
            page.get_by_placeholder("Password").click()
            page.get_by_placeholder("Password").fill(password)
    except Exception as e:
        logger.info(f'Impossible de trouver le champ password {e}')
        raise Exception from e

    page.wait_for_selector('xpath=//*[@id="rememberme"]')
    try:
        if page.get_by_label("Remember Me"):
            page.get_by_label("Remember Me").check()
    except Exception as e:
        logger.info(f'Impossible de trouver le checkbox: {e}')
        raise Exception from e

    page.wait_for_selector('xpath=//*[@id="content"]/div/div[1]/div/div[2]/form/div[4]/div/button')
    print("Bouton selectionné")
    #page.pause()
    try:
        if page.get_by_role("button", name="Login"):
            page.get_by_role("button", name="Login").click()
    except Exception as e:
        logger.info(f'Impossible de trouver le bouton login: {e}')
        raise Exception from e

    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    page.wait_for_timeout(5000)
    email = os.environ['EMAIL_CODE_CONFIRMATION']
    password = os.environ['PASSWORD_CODE_CONFIRMATION']

    code = fetch_gmail_code(email=email, password=password)
    page.wait_for_timeout(10000)
    try:
        if code:
            logger.info(f"Code de verification récupéré {code}")
            page.get_by_placeholder("Your Code").click()
            page.get_by_placeholder("Your Code").fill(code)
            random_delay(min_delay=1, max_delay=3)
            page.get_by_role("button", name="Verify Code").click()
            page.wait_for_load_state("domcontentloaded")
    except Exception as e:
        logger.info(f"Aucun code trouvé: {e}")
        raise Exception from e
    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    #page.pause()
    try:
        page.wait_for_selector('xpath=//*[@id="navlistexpireddomains"]/li[43]/a')
        logger.info("Bouton Pending Delete aperçu avec succés")
        if page.get_by_role("link", name="Pending Delete", exact=True):
            page.get_by_role("link", name="Pending Delete", exact=True).click()
            logger.info("Clique sur le lien 'Pending Delete'")
            page.wait_for_load_state("domcontentloaded")
            logger.info("Chargement complète de la page")
            filterThePage(page)
            logger.info("page pending deleted domains filtrée")
            count = 1
            max_pages = get_total_pages(page)
            data = []
            if max_pages == 0:
                logger.warning("Aucune page disponible ou erreur dans l'extraction du nombre de pages.")
            else:
                while count < min(max_pages, 50):
                    logger.info('On entre bien dans la boucle')

                    navigation_on_expired_domains_page(page=page, count=count, data=data)
                    header = [
                        "Domain", "Length", "Backlinks", "Domain Pop", "Creation Date",
                        "First Seen", "Crawl Results", "Global Rank", "TLD Registered",
                        ".com", ".net", ".org", ".biz", ".info", ".de", "Date Scraping", "Add Date", "End Date",
                        "Status"
                    ]
                    with open("pending_domains_from_expired_domains.csv", "a", newline="", encoding="utf-8") as csvfile:
                        csvwriter = csv.writer(csvfile)
                        if csvfile.tell() == 0:
                            csvwriter.writerow(header)

                        if data:
                            logger.info(f"Écriture de {len(data)} lignes dans le fichier.")
                            csvwriter.writerows(data)
                        else:
                            logger.warning(f"Aucune donnée à écrire pour la page {count}")

                    logger.info(f'les {len(data)} données de la page {count} sont extraites')

                    random_delay(min_delay=2, max_delay=4)
                    try:
                        page.wait_for_selector('xpath=//*[@id="listing"]/div[2]/div[2]/div[1]/a')
                        logger.info("Le lien 'Next Page' est bien aperçu")
                        if page.get_by_role("link", name="Next Page »").first:
                            page.get_by_role("link", name="Next Page »").first.click()
                            # Attendez la page suivante ou une redirection
                            page.wait_for_load_state('domcontentloaded')
                            logger.info("La redirection à la page suivant est effective")
                            # Récupérez les cookies après connexion et sauvegardez-les
                            save_cookies_to_file(
                                context.cookies()
                            )  # Sauvegarder les cookies pour une utilisation future
                            random_delay(min_delay=2, max_delay=4)
                            logger.info("Récupération et sauvegarde des cookies après connexion")
                    except Exception as e:
                        logger.info(f'Impossible de trouver le lien "Next Page": {e}')
                        raise Exception from e
                    # print(count)
                    count += 1
                    logger.info('On sort bien de la boucle')
    except Exception as e:
        logger.info(f'Impossible de trouver le lien Pending Delete {e}')
        raise Exception from e
    page.wait_for_timeout(2000)
    try:
        page.wait_for_selector('xpath=//*[@id="navlistexpireddomains"]/li[1]/a')
        logger.info("Le lien 'Deleted Domain' est bien aperçu")
        if page.get_by_role("link", name="Deleted Domains"):
            page.get_by_role("link", name="Deleted Domains").click()
            logger.info("Clique sur le lien 'Deleted Domains'")
            page.wait_for_load_state("domcontentloaded")
            logger.info("Chargement complète de la page")
            filterThePage(page)
            logger.info("page deleted domains filtrée")
            counter = 1
            datas = []
            if max_pages == 0:
                logger.warning("Aucune page disponible ou erreur dans l'extraction du nombre de pages.")
            else:
                while counter < min(max_pages, 50):
                    logger.info('On est bien entré dans la boucle pour deleted domains')
                    navigation_on_expired_domains_page(page=page, count=counter, data=datas)
                    columns = [
                        "Domain", "Length", "Backlinks", "Domain Pop", "Creation Date",
                        "First Seen", "Crawl Results", "Global Rank", "TLD Registered",
                        ".com", ".net", ".org", ".biz", ".info", ".de", "Date Scraping", "Add Date", "Dropped",
                        "Status"
                    ]

                    with open("deleted_domains_from_expired_domains.csv", mode="a", newline='',
                              encoding="utf-8") as file:
                        writer = csv.writer(file)

                        if file.tell() == 0:
                            writer.writerow(columns)

                        writer.writerows(datas)
                    logger.info(f'{len(datas)}Données extraites à le page {counter}')
                    random_delay(min_delay=2, max_delay=4)
                    try:
                        page.wait_for_selector('xpath=//*[@id="listing"]/div[2]/div[2]/div[1]/a')
                        logger.info("Le lien 'Next Page' est bien aperçu")
                        if page.get_by_role("link", name="Next Page »").first:
                            page.get_by_role("link", name="Next Page »").first.click()
                            # Attendez la page suivante ou une redirection
                            page.wait_for_load_state('domcontentloaded')
                            logger.info("La redirection à la page suivant est effective")
                            # Récupérez les cookies après connexion et sauvegardez-les
                            save_cookies_to_file(
                                context.cookies())  # Sauvegarder les cookies pour une utilisation future
                            random_delay(min_delay=2, max_delay=4)
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


def sent_message(message):
    requests.post("https://api.pushover.net/1/messages.json", {
        "token": os.environ['PUSHOVER_TOKEN'],
        "user": os.environ['PUSHOVER_USER'],
        "message": message
    })


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

        count += 1
        logger.info("Sortie de la boucle")

    browser.close()


def main():
    start_time = time.time()
    expired_domain_url: str = 'https://www.expireddomains.net'
    domain_robot_url = "https://thedomainrobot.com/"
    with sync_playwright() as playwright:
        logger.info('Connexion sur web scraping en cours')
        username = os.environ["USERNAME_EXPIRED_DOMAINS"]
        password = os.environ["PASSWORD_EXPIRED_DOMAINS"]
        #print(username, password)
        get_domains_from_expired_domains(
            pw=playwright,
            url=expired_domain_url,
            username=username,
            password=password,
            bright_data=False,
            headless=True
        )

        # get_domains_from_domains_robot(
        #     pw=playwright,
        #     url=domain_robot_url,
        #     bright_data=False,
        #     headless=False
        # )
    email = os.environ['EMAIL_CODE_CONFIRMATION']
    password = os.environ['PASSWORD_CODE_CONFIRMATION']

    code = fetch_gmail_code(email=email, password=password)
    print(code)
    end_time = time.time()
    execution_time = end_time - start_time
    current_date = datetime.now()
    message = f"Le scraper de {expired_domain_url} a mis {execution_time:.2f} secondes à s'exécuter, ce {current_date}"
    logger.info(message)
    try:
        sent_message(message)
    except Exception as e:
        error = f"Le script retourne une erreur: {e}"
        sent_message(error)
        raise Exception from e


if __name__ == '__main__':
    main()
