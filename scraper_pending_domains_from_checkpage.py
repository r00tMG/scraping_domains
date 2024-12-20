import csv
import time

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
            page.goto("https://www.checkpagerank.net/check-page-rank.php")

            for index, domain in enumerate(domains, 1):
                try:
                    time.sleep(61)

                    if page.get_by_role("textbox", name="Valid link only"):
                        page.get_by_role("textbox", name="Valid link only").fill(domain)
                        page.wait_for_timeout(1000)
                        page.get_by_role("button", name="Submit").click()
                        page.wait_for_timeout(2000)

                        html = page.content()
                        soup = BeautifulSoup(html, 'html.parser')
                        trs = soup.select('div.container.results div.row')
                        metrics = {}

                        for row in trs:

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
                                        elif 'Page Authority' in label:
                                            metrics["PA"] = value

                        metrics_dict[domain] = metrics or {
                            "DA": "N/A", "PA": "N/A",
                            "TF": "N/A", "CF": "N/A"
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
                        "TF": "N/A", "CF": "N/A"
                    }
            # Sauvegarder le dernier lot s'il reste des domaines
            if current_batch:
                save_batch_metrics(metrics_dict, current_batch, domain_rows)

        finally:
            browser.close()

        return metrics_dict

    except Exception as e:
        logger.error(f"Erreur critique lors de l'obtention des métriques SEO: {str(e)}")
        return {domain: {"DA": "N/A", "PA": "N/A", "TF": "N/A", "CF": "N/A"} for domain in domains}
    

def save_batch_metrics(metrics_dict, domains, domain_rows):
    """Sauvegarde un lot de métriques dans un fichier CSV avec toutes les informations"""
    try:
        header = ["domain", "backlinks", "creation_date", "first_seen", "DA", "PA", "TF", "CF", "add_date"]
        with open("domains_pending.csv", mode="a", newline='', encoding="utf-8") as output_file:
            writer = csv.writer(output_file)
            for domain in domains:
                metrics = metrics_dict[domain]
                row = domain_rows.get(domain, [])

                if output_file.tell() == 0:
                    writer.writerow(header)
                
                writer.writerow([
                    domain,
                    row[2] if len(row) > 2 else "N/A",  
                    row[4] if len(row) > 4 else "N/A",  
                    row[5] if len(row) > 5 else "N/A",  
                    metrics.get('DA', 'N/A'),
                    metrics.get('PA', 'N/A'),
                    metrics.get('TF', 'N/A'),
                    metrics.get('CF', 'N/A'),
                    row[16] if len(row) > 16 else "N/A"  
                ])
        logger.info(f"Lot de {len(domains)} domaines sauvegardé avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du lot: {str(e)}")


def main():
    with sync_playwright() as playwright:
        with open("pending_domains_from_expired_domains.csv", mode="r", newline='', encoding="utf-8") as input_file:
            reader = csv.reader(input_file)
            next(reader)
            rows = list(reader)
            domains = [row[0] for row in rows]

            all_metrics = get_bulk_seo_metrics(pw=playwright, domains=domains, rows=rows, headless=True)


if __name__ == '__main__':
    main()
