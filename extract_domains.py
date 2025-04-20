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
from selenium.webdriver.common.action_chains import ActionChains

def setup_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.binary_location = '/usr/bin/chromium-browser'
    return webdriver.Chrome(options=options)

def extract_domains(url: str,
                    page_load_timeout: int = 30,
                    delay_min: float = 1.5,
                    delay_max: float = 3.5) -> List[str]:
    driver = setup_driver()
    driver.set_page_load_timeout(page_load_timeout)
    domains = []

    try:
        driver.get(url)
        wait = WebDriverWait(driver, page_load_timeout)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'tbody tr')))

        while True:
            time.sleep(random.uniform(delay_min, delay_max))
            rows = driver.find_elements(By.CSS_SELECTOR, 'tbody tr')
            for row in rows:
                try:
                    cell = row.find_elements(By.TAG_NAME, 'td')[0]
                    text = cell.text.strip()
                    if not text:
                        continue
                    domain = re.sub(r'^https?://', '', text)
                    domain = domain.rstrip('/')
                    domain = domain.replace('[.]', '.')
                    domains.append(domain)
                except Exception:
                    continue

            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, '.paginate_button.next')
                next_class = next_btn.get_attribute('class')
                if 'disabled' in next_class or 'unavailable' in next_class:
                    logging.info("Reached last page.")
                    break
                else:
                    ActionChains(driver).move_to_element(next_btn).perform()
                    time.sleep(random.uniform(0.5, 1.5))
                    next_btn.click()
            except Exception as e:
                logging.warning(f"Pagination failed: {e}")
                break

    except Exception as e:
        logging.error(f"Error during extraction: {e}")
    finally:
        driver.quit()

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
        for d in extracted:
            print(d)
    else:
        print("No domains extracted.")

if __name__ == '__main__':
    main()
