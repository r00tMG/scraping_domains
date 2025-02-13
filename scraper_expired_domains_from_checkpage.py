import csv
import time
from datetime import datetime

from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import sync_playwright

from script import SBR_WS_CDP


def get_bulk_seo_metrics(pw, domains, rows, bright_data=False, headless=False):
    """Récupère les métriques SEO pour plusieurs domaines en une seule session"""
    try:
        if bright_data:
            browser = pw.firefox.connect_over_cdp(SBR_WS_CDP)
        else:
            browser = pw.chromium.launch(headless=headless)
        context = browser.new_context()
        context.set_default_timeout(40000)
        page = context.new_page()

        metrics_dict = {}
        batch_size = 5
        current_batch = []
        domain_rows = {row[0]: row for row in rows}  

        try:
            page.goto("https://www.checkpagerank.net/check-page-rank.php", wait_until="domcontentloaded", timeout=60000)
            #page.goto('https://www.checkpagerank.net/index.php', wait_until="domcontentloaded", timeout=60000)
            for index, domain in enumerate(domains, 1):
                try:
                    time.sleep(61)

                    if page.get_by_role("textbox", name="Valid link only"):
                        page.get_by_role("textbox", name="Valid link only").fill(domain)
                        page.wait_for_timeout(1000)
                        page.get_by_role("button", name="Submit").click()
                        page.wait_for_timeout(2000)

                        html = page.content()
                        #print(html)
                        soup = BeautifulSoup(html, 'html.parser')
                        trs = soup.select('div.container.results div.row')
                        #print(trs)
                        metrics = {}

                        for row in trs:
                            #print(row)
                            ip_col = row.find('div', class_='col-sm-11')
                            if ip_col and 'Root IP:' in ip_col.text:
                                metrics["root_ip"] = ip_col.text.split("Root IP:")[1].strip()

                            cols = row.find_all('div', class_='col-md-5')
                            if len(cols) == 2:
                                for col in cols:
                                    text = col.get_text(strip=True)
                                    if ":" in text:
                                        label, value = map(str.strip, text.split(":", 1))
                                        if 'Domain Authority' in label:
                                            metrics["DA"] = value
                                        elif 'Trust Flow' in label:
                                            metrics["TF"] = value
                                        elif 'Citation Flow' in label:
                                            metrics["CF"] = value
                                        elif 'External Backlinks' in label:
                                            metrics["external_link"] = value
                                        elif 'Page Authority' in label:
                                            metrics["PA"] = value
                                        elif 'Spam Score' in label:
                                            metrics["spam_rating"] = value
                                        elif 'Referring Domains' in label:
                                            metrics["referring_domains"] = value
                                        elif 'Root IP' in label:
                                            metrics["root_ip"] = value

                        metrics_dict[domain] = metrics or {
                            "DA": "N/A", "PA": "N/A",
                            "TF": "N/A", "CF": "N/A",
                            "external_link": "N/A", "spam_rating": "N/A",
                            "referring_domains": "N/A", "root_ip": "N/A"
                        }
                        current_batch.append(domain)
                        logger.info(f"Métriques récupérées pour {domain} : {metrics}")

                        # Sauvegarder après chaque lot de 10 domaines
                        if index % batch_size == 0:
                            save_batch_metrics(metrics_dict, current_batch, domain_rows)
                            current_batch = []  # Réinitialiser le lot courant

                except Exception as e:
                    logger.warning(f"Erreur lors de la récupération des métriques pour {domain}: {str(e)}")
                    metrics_dict[domain] = {
                        "DA": "N/A", "PA": "N/A",
                        "TF": "N/A", "CF": "N/A",
                        "external_link": "N/A", "spam_rating": "N/A",
                        "referring_domains": "N/A", "root_ip": "N/A"
                    }
            # Sauvegarder le dernier lot s'il reste des domaines
            if current_batch:
                save_batch_metrics(metrics_dict, current_batch, domain_rows)

        finally:
            browser.close()

        return metrics_dict

    except Exception as e:
        logger.error(f"Erreur critique lors de l'obtention des métriques SEO: {str(e)}")
        return {domain: {"DA": "N/A", "PA": "N/A", "TF": "N/A", "CF": "N/A", "external_link": "N/A",
                         "spam_rating": "N/A", "referring_domains": "N/A", "root_ip": "N/A"} for domain in domains}
    

def save_batch_metrics(metrics_dict, domains, domain_rows):
    """Sauvegarde un lot de métriques dans un fichier CSV avec toutes les informations"""
    try:
        start_time = time.time()
        header = ["domain", "backlinks", "creation_date", "first_seen", "DA", "PA", "TF", "CF",
                  "external_link", "spam_rating", "referring_domains", "add_date", "end_date", "status",
                  "tld_registered", "crawl_results", "global_rank", "length", "com_tld", "net_tld",
                  "org_tld", "biz_tld", "info_tld", "de_tld", "root_ip"
                  ]
        with open("domain_expired.csv", mode="a", newline='', encoding="utf-8") as output_file:
            writer = csv.writer(output_file)
            for domain in domains:
                metrics = metrics_dict[domain]
                row = domain_rows.get(domain, [])

                if output_file.tell() == 0:
                    writer.writerow(header)
                
                writer.writerow([
                    domain,
                    row[2] if len(row) > 2 else "N/A",  # backlinks
                    row[4] if len(row) > 4 else "N/A",  # creation_date
                    row[5] if len(row) > 5 else "N/A",  # first_seen
                    metrics.get('DA', 'N/A'),
                    metrics.get('PA', 'N/A'),
                    metrics.get('TF', 'N/A'),
                    metrics.get('CF', 'N/A'),
                    metrics.get('external_link', 'N/A'),
                    metrics.get('spam_rating', 'N/A'),
                    metrics.get('referring_domains', 'N/A'),
                    row[16] if len(row) > 16 else "N/A",  # add_date
                    row[17] if len(row) > 17 else "N/A",  # end_date
                    row[18] if len(row) > 18 else "N/A",  # status
                    row[8] if len(row) > 8 else "N/A",  # TLD Registered
                    row[6] if len(row) > 6 else "N/A",  # Crawl Results
                    row[7] if len(row) > 7 else "N/A",  # Global Rank
                    row[1] if len(row) > 1 else "N/A",  # Length
                    row[9] if len(row) > 9 else "N/A",  # .com
                    row[10] if len(row) > 10 else "N/A",  # .net
                    row[11] if len(row) > 11 else "N/A",  # .org
                    row[12] if len(row) > 12 else "N/A",  # .biz
                    row[13] if len(row) > 13 else "N/A",  # .info
                    row[14] if len(row) > 14 else "N/A",  # .de
                    metrics.get('root_ip', 'N/A') # addressIp

                ])
        logger.info(f"Lot de {len(domains)} domaines sauvegardé avec succès")
        end_time = time.time()
        execution_time = end_time - start_time
        current_date = datetime.now()
        message = f"Le scraper a mis {execution_time:.2f} secondes à s'exécuter, ce {current_date}"
        print(message)
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du lot: {str(e)}")


def main():

    with sync_playwright() as playwright:
        with open("deleted_domains_from_expired_domains.csv", mode="r", newline='', encoding="utf-8") as input_file:
            reader = csv.reader(input_file)
            next(reader)
            rows = list(reader)
            domains = [row[0] for row in rows]

            get_bulk_seo_metrics(pw=playwright, domains=domains, rows=rows, headless=True)


if __name__ == '__main__':
    main()
