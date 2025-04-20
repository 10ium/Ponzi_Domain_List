from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import re
import time

def setup_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # specify path to Chrome if needed
    return webdriver.Chrome(options=options)


def extract_domains(url: str, timeout: int = 30) -> list[str]:
    """Use Selenium to load the page and extract first-column domains."""
    driver = setup_driver()
    logging.info(f"Loading URL: {url}")
    driver.get(url)

    try:
        # wait for table body rows to appear
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'tbody tr'))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr')
        domains = []
        for row in rows:
            # first cell
            cell = row.find_element(By.TAG_NAME, 'td')
            text = cell.text.strip()
            if not text:
                continue
            # clean text: remove https?:// , trailing slash, deobfuscate
            domain = re.sub(r'^https?://', '', text)
            domain = domain.rstrip('/')
            domain = domain.replace('[.]', '.')
            domains.append(domain)
        return list(dict.fromkeys(domains))  # dedupe preserving order

    except Exception as e:
        logging.error(f"Failed to extract domains: {e}")
        return []
    finally:
        driver.quit()


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    url = "https://www.webamooz.com/ponzi/"
    domains = extract_domains(url)
    if domains:
        print("Extracted Domains:")
        for d in domains:
            print(d)
    else:
        print("No domains extracted.")

if __name__ == '__main__':
    main()import requests
from bs4 import BeautifulSoup
import time
import socket
import urllib3.exceptions
import logging
from typing import List
from urllib.parse import urlparse
import re
import json
from io import BytesIO
from PIL import Image
import pytesseract

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def extract_domains(url: str,
                    max_retries: int = 3,
                    delay: int = 2) -> List[str]:
    """
    Extracts clean domain names from the "لیست هشدار" content on the given URL.
    Supports TablePress JSON, HTML table, and OCR on embedded image.
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
                    domains = [clean_domain(r[0]) for r in rows if r]
                    return unique(domains)
                except json.JSONDecodeError:
                    logging.warning('Invalid TablePress JSON, falling back.')

            # 2. HTML table parsing
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')
                logging.info(f"Found {len(rows)} HTML table rows.")
                for tr in rows:
                    cells = tr.find_all('td')
                    if cells:
                        d = clean_domain(cells[0].get_text(strip=True))
                        if d:
                            domains.append(d)
                if domains:
                    return unique(domains)

            # 3. OCR fallback: find image containing table
            images = soup.find_all('img')
            for img in images:
                src = img.get('src')
                if src and 'webamooz' in src:
                    img_url = src if src.startswith('http') else urlparse(url)._replace(path=src).geturl()
                    logging.info(f"Attempting OCR on image: {img_url}")
                    ocr_text = ocr_image(img_url)
                    domains = parse_domains_from_text(ocr_text)
                    if domains:
                        return unique(domains)

            # no data found
            logging.warning('No domains extracted via any method.')
            return []

        except (requests.RequestException, socket.error,
                urllib3.exceptions.ReadTimeoutError) as e:
            retries += 1
            logging.error(f"Error ({retries}/{max_retries}) fetching {url}: {e}")
            time.sleep(delay * retries)
        except Exception as e:
            logging.critical(f"Unexpected error: {e}")
            break

    return []


def clean_domain(raw: str) -> str:
    """Clean and validate a raw domain string."""
    if not raw:
        return ''
    # Remove URL scheme and trailing slash
    domain = re.sub(r'^https?://', '', raw).rstrip('/')
    # De-obfuscate dots
    domain = domain.replace('[.]', '.')
    # Validate with urlparse
    parsed = urlparse('//' + domain)
    return parsed.netloc or ''


def ocr_image(img_url: str) -> str:
    """Download image and return extracted text via OCR."""
    resp = requests.get(img_url)
    resp.raise_for_status()
    img = Image.open(BytesIO(resp.content))
    text = pytesseract.image_to_string(img, lang='eng+fas')
    return text


def parse_domains_from_text(text: str) -> List[str]:
    """Parse domain-like patterns from OCR text."""
    # pattern matches word chars + [.] + word chars, with optional subdomains
    matches = re.findall(r'([\w\-]+(?:\.[\w\-]+)*\[\.\][\w\-]+(?:\.[\w\-]+)*)', text)
    cleaned = [clean_domain(m) for m in matches]
    return [d for d in cleaned if d]


def unique(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for it in items:
        if it and it not in seen:
            seen.add(it)
            result.append(it)
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
