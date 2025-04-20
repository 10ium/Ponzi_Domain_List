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
    Extracts domain names from the first column of a table on the given URL.
    Retries on failure, with exponential backoff.

    Returns a list of unique domains.
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

            # Try to find a table of domains
            table = soup.find('table')
            if not table:
                logging.warning('No <table> found; aborting.')
                break

            rows = table.find_all('tr')
            logging.info(f"Found {len(rows)} rows in table.")

            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue
                text = cells[0].get_text(strip=True)
                if not text:
                    continue
                # Replace obfuscated dots
                domain = re.sub(r'\[\.\]', '.', text)
                domains.append(domain)

            # Pagination logic (if present)
            next_link = soup.find('a', class_='next-page')
            if next_link and next_link.get('href'):
                next_url = next_link['href']
                if not next_url.startswith(('http://', 'https://')):
                    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                    next_url = base + next_url
                url = next_url
                logging.info(f"Following to next page: {url}")
                time.sleep(delay)
                retries = 0
                continue

            # No further pages
            break

        except (requests.RequestException, socket.error,
                urllib3.exceptions.ReadTimeoutError) as e:
            retries += 1
            logging.error(f"Error ({retries}/{max_retries}) requesting {url}: {e}")
            time.sleep(delay * retries)
        except Exception as e:
            logging.critical(f"Unexpected error: {e}")
            break

    # Deduplicate
    return list(dict.fromkeys(domains))


def main():
    target_url = "https://www.webamooz.com/ponzi/"
    domains = extract_domains(target_url)

    if domains:
        print("Extracted Domains:")
        for d in domains:
            print(d)
    else:
        print("No domains extracted.")


if __name__ == '__main__':
    main()
