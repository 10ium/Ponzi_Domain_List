import requests
from bs4 import BeautifulSoup
import time
import socket
import urllib3.exceptions
import logging
from typing import List, Optional
from urllib.parse import urlparse, unquote
import re  # اضافه کردن ماژول re برای عبارات منظم


# تنظیم لاگینگ برای ثبت خطاها و اطلاعات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def extract_domains(url: str, max_retries: int = 3, delay: int = 2) -> List[str]:
    """
    دامنه ها را از یک URL با مدیریت خطا و منطق تکرار استخراج می کند.

    Args:
        url (str): URL برای استخراج دامنه ها.
        max_retries (int, optional): حداکثر تعداد تلاش های مجدد برای درخواست های ناموفق. پیش فرض 3 است.
        delay (int, optional): مدت زمان انتظار بین درخواست ها برای جلوگیری از محدودیت نرخ. پیش فرض 2 ثانیه است.

    Returns:
        List[str]: لیستی از دامنه های استخراج شده.
    """
    domains = []
    retries = 0
    page_number = 1  # برای پیگیری صفحاتی که پردازش می شوند

    while retries < max_retries:
        try:
            logging.info(f"در حال پردازش صفحه: {page_number}, URL: {url}")  # لاگ صفحه فعلی
            # ارسال درخواست HTTP GET با یک user-agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # افزایش خطا برای کدهای وضعیت بد

            # پارس کردن HTML با BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            # پیدا کردن جدول
            table = soup.find('table')  # پیدا کردن اولین جدول

            if table:
                logging.info("جدول پیدا شد.")  # لاگ پیدا شدن جدول
                # پیدا کردن ردیف های جدول
                table_rows = table.find_all('tr')
                logging.info(f"{len(table_rows)} ردیف در جدول پیدا شد.") # تعداد ردیف ها را لاگ کنید

                for row in table_rows:
                    # پیدا کردن سلول های داده در ردیف
                    cells = row.find_all('td')
                    if len(cells) > 0:  # بررسی کنید که ردیف خالی نباشد
                        # فرض می کند که نام دامنه در اولین سلول قرار دارد
                        domain_cell = cells[0]
                        domain_text = domain_cell.text.strip()
                        logging.info(f"مقدار domain_text: {domain_text}")  # محتوای domain_text را لاگ کنید
                        if domain_text:
                            domain = re.sub(r'\[\.\]', '.', domain_text)
                            domains.append(domain)
                            logging.info(f"دامنه اضافه شد: {domain}") # لاگ کردن دامنه اضافه شده
                    else:
                         logging.info("ردیف خالی پیدا شد")

            else:
                logging.warning("هیچ جدولی در صفحه پیدا نشد.")
                break  # اگر جدولی پیدا نشد حلقه را متوقف کنید

            # مدیریت صفحه‌بندی (اگر صفحه بندی وجود دارد)
            next_page = soup.find('a', class_='next-page')  # مثال: صفحه بعدی
            if next_page:
                next_page_url = next_page.get('href')
                if next_page_url:
                    # Combine with base URL if relative URL
                    if not next_page_url.startswith(('http://', 'https://')):
                        base_url = urlparse(url).scheme + "://" + urlparse(url).netloc
                        next_page_url = base_url + next_page_url
                    url = next_page_url
                    logging.info(f"رفتن به صفحه بعدی: {url}")
                    time.sleep(delay)  # رعایت تاخیر
                    retries = 0  # ریست شمارنده
                    page_number += 1
                    continue  # ادامه با صفحه بعدی
                else:
                    logging.info("دیگر هیچ صفحه بعدی وجود ندارد.")
                    break
            else:
                logging.info("دیگر هیچ صفحه بعدی وجود ندارد.")
                break  # اگر صفحه بعدی وجود ندارد، حلقه را بشکنید

        except requests.exceptions.RequestException as e:
            logging.error(f"خطا در درخواست به {url}: {e}")
            retries += 1
            time.sleep(delay * retries)  # تاخیر تصاعدی
        except (socket.error, urllib3.exceptions.ReadTimeoutError) as e:
            logging.error(f"خطا در شبکه در {url}: {e}")
            retries += 1
            time.sleep(delay * retries)
        except Exception as e:
            logging.critical(f"خطای غیرمنتظره در پردازش {url}: {e}")
            break  # برای خطاهای غیرمنتظره متوقف شوید

    if not domains:
        logging.info("هیچ دامنه ای استخراج نشد.")
    return list(set(domains))  # حذف موارد تکراری


def main():
    """
    تابع اصلی برای اجرای اسکریپت.
    """
    target_url = "https://www.webamooz.com/ponzi/"  # URL هدف را اینجا مشخص کنید
    extracted_domains = extract_domains(target_url)

    if extracted_domains:
        print("دامنه های استخراج شده:")
        for domain in extracted_domains:
            print(domain)
    else:
        print("هیچ دامنه ای استخراج نشد.")



if __name__ == "__main__":
    main()

