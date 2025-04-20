import logging
import re
import time
import random
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
    options.binary_location = '/usr/bin/chromium-browser'
    return webdriver.Chrome(options=options)

def extract_domains(url: str,
                    page_load_timeout: int = 30,
                    delay_min: float = 1.5,
                    delay_max: float = 3.5) -> List[str]:
    """
    Loads all paginated pages via Selenium, extracts first-column domains,
    respects random delays to avoid rate limits and bot detection.
    """
    driver = setup_driver()
    driver.set_page_load_timeout(page_load_timeout)
    domains = []

    try:
        driver.get(url)
        while True:
            WebDriverWait(driver, page_load_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'tbody tr'))
            )
            rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr')
            for row in rows:
                cell = row.find_element(By.TAG_NAME, 'td')
                text = cell.text.strip()
                if not text:
                    continue
                domain = re.sub(r'^https?://', '', text)
                domain = domain.rstrip('/')
                domain = domain.replace('[.]', '.')
                domains.append(domain)

            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, '.paginate_button.next')
                if "disabled" in next_btn.get_attribute("class"):
                    logging.info('No further pages or "Next" disabled. Ending pagination.')
                    break
                else:
                    # Scroll to button and click
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                    time.sleep(random.uniform(0.5, 1.5))
                    next_btn.click()
                    sleep_time = random.uniform(delay_min, delay_max)
                    logging.info(f"Waiting {sleep_time:.2f}s before loading next page")
                    time.sleep(sleep_time)
            except Exception as e:
                logging.warning(f"Could not find or click 'Next' button: {e}")
                break

    except Exception as e:
        logging.error(f"Error during pagination/extraction: {e}")
    finally:
        driver.quit()

    # Deduplicate while preserving order
    seen = set()
    unique_domains = []
    for d in domains:
        if d not in seen:
            seen.add(d)
            unique_domains.append(d)
    return unique_domains

def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    url = "https://www.webamooz.com/ponzi/"
    extracted = extract_domains(url)
    if extracted:
        print("Extracted Domains:")
        for d in extracted:
            print(d)
    else:
        print("No domains extracted.")

if __name__ == '__main__':
    main()
