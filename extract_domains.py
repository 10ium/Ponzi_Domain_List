import logging
import re
import time
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)


def extract_domains(url: str, timeout: int = 30) -> List[str]:
    """Use Selenium to load the page and extract first-column domains."""
    driver = setup_driver()
    logging.info(f"Loading URL: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'tbody tr'))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr')
        domains = []
        for row in rows:
            cell = row.find_element(By.TAG_NAME, 'td')
            text = cell.text.strip()
            if not text:
                continue
            domain = re.sub(r'^https?://', '', text)
            domain = domain.rstrip('/')
            domain = domain.replace('[.]', '.')
            domains.append(domain)
        return list(dict.fromkeys(domains))

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
    main()
