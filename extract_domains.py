import requests
from bs4 import BeautifulSoup
import time
import socket
import urllib3.exceptions
import logging
from typing import List
from urllib.parse import urlparse
import re

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def extract_domains(url: str,
                    max_retries: int = 3,
                    delay: int = 2) -> List[str]:
    """
    Extracts clean domain names from the first column of the "لیست هشدار" table on the given URL.
    Handles retries, pagination, and de-obfuscation of domains (replacing "[.]" with ".").
    """
    domains = []
    retries = 0

    while retries < max_retries:
        try:
            logging.info(f"Requesting URL: {url}")
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                    ' AppleWebKit/537.36 (KHTML, like Gecko)'
                    ' Chrome/123.0.0.0 Safari/537.36'
                )
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Locate the warning list table (TablePress plugin)
            table = soup.find('table', class_='tablepress')
            if not table:
                logging.warning('No TablePress table found on the page.')
                return []

            tbody = table.find('tbody') or table
            rows = tbody.find_all('tr')
            logging.info(f"Found {len(rows)} rows in the table.")

            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue
                raw_text = cells[0].get_text(strip=True)
                if not raw_text:
                    continue

                # Remove protocol prefix
                domain = re.sub(r'^https?://', '', raw_text)
                # Remove trailing slash
                domain = domain.rstrip('/')
                # De-obfuscate dots
                domain = domain.replace('[.]', '.')

                # Validate domain-like string
                parsed = urlparse('//' + domain)
                if parsed.netloc:
                    domains.append(parsed.netloc)

            # Handle pagination if any (unlikely on this page)
            next_link = soup.find('a', class_='next-page')
            if next_link and next_link.get('href'):
                next_url = next_link['href']
                if not next_url.startswith(('http://', 'https://')):
                    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                    next_url = base + next_url
                url = next_url
                logging.info(f"Following next page: {url}")
                time.sleep(delay)
                retries = 0
                continue

            break

        except (requests.RequestException, socket.error,
                urllib3.exceptions.ReadTimeoutError) as e:
            retries += 1
            logging.error(f"Error ({retries}/{max_retries}) requesting {url}: {e}")
            time.sleep(delay * retries)
        except Exception as e:
            logging.critical(f"Unexpected error: {e}")
            break

    # Deduplicate while preserving order
    seen = set()
    unique_domains = []
    for d in domains:
        if d not in seen:
            seen.add(d)
            unique_domains.append(d)

    return unique_domains


def main():
    target_url = "https://www.webamooz.com/ponzi/"
    extracted = extract_domains(target_url)

    if extracted:
        print("Extracted Domains:")
        for d in extracted:
            print(d)
    else:
        print("No domains extracted.")


if __name__ == '__main__':
    main()
