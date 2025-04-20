import requests
from bs4 import BeautifulSoup
import time
import socket
import urllib3.exceptions
import logging
from typing import List
from urllib.parse import urlparse
import re
import json

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def extract_domains(url: str,
                    max_retries: int = 3,
                    delay: int = 2) -> List[str]:
    """
    Extracts clean domain names from the "لیست هشدار" table on the given URL.
    Supports both TablePress JSON data and HTML table parsing.

    Args:
        url (str): Page URL to extract domains from.
        max_retries (int): Number of retries on failure.
        delay (int): Base delay between retries.

    Returns:
        List[str]: List of unique domain names.
    """
    domains = []
    retries = 0

    while retries < max_retries:
        try:
            logging.info(f"Requesting URL: {url}")
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 1. TablePress JSON fallback
            script = soup.find('script', id=re.compile(r'tablepress-\d+-data'))
            if script and script.string:
                try:
                    table_json = json.loads(script.string)
                    rows = table_json.get('data', [])
                    logging.info(f"Parsed {len(rows)} rows from TablePress JSON.")
                    for row in rows:
                        if not row: continue
                        cleaned = clean_domain(row[0])
                        if cleaned:
                            domains.append(cleaned)
                    return unique(domains)
                except json.JSONDecodeError:
                    logging.warning('Invalid TablePress JSON, falling back to HTML table.')

            # 2. HTML table parsing
            table = soup.find('table')
            if not table:
                logging.warning('No HTML <table> found.')
                return []

            rows = table.find_all('tr')
            logging.info(f"Found {len(rows)} HTML table rows.")
            for tr in rows:
                cells = tr.find_all('td')
                if not cells: continue
                cleaned = clean_domain(cells[0].get_text(strip=True))
                if cleaned:
                    domains.append(cleaned)

            break

        except (requests.RequestException, socket.error,
                urllib3.exceptions.ReadTimeoutError) as e:
            retries += 1
            logging.error(f"Error ({retries}/{max_retries}) fetching {url}: {e}")
            time.sleep(delay * retries)
        except Exception as e:
            logging.critical(f"Unexpected error: {e}")
            break

    return unique(domains)


def clean_domain(raw: str) -> str:
    """Clean and validate a raw domain string."""
    if not raw:
        return ''
    # Remove URL scheme and trailing slash
    domain = re.sub(r'^https?://', '', raw).rstrip('/')
    # De-obfuscate dots
    domain = domain.replace('[.]', '.')
    # Validate format
    parsed = urlparse('//' + domain)
    return parsed.netloc or ''


def unique(items: List[str]) -> List[str]:
    """Return unique items preserving order."""
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def main():
    url = "https://www.webamooz.com/ponzi/"
    domains = extract_domains(url)
    if domains:
        print("Extracted Domains:")
        for d in domains:
            print(d)
    else:
        print("No domains extracted.")


if __name__ == '__main__':
    main()
