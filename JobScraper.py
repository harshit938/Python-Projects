"""
============================================================
  Automated Job Listings Scraper
  Author : Harshit Kumar Mishra
  Tech   : Python | Selenium | BeautifulSoup | Pandas | JSON
  Desc   : Scrapes job title, company, location, salary, and
           description from Naukri.com (dynamic JS portal).
           Handles pagination, infinite scroll, and exports
           to JSON + Excel. Auto-scheduled for daily runs.
============================================================
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, WebDriverException
)
from bs4 import BeautifulSoup
import pandas as pd
import json
import logging
import time
import os
import schedule
from datetime import datetime

# ─────────────────────────────────────────────
#  LOGGING SETUP
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    handlers=[
        logging.FileHandler("job_scraper.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
BASE_URL    = "https://www.naukri.com/{keyword}-jobs-in-{location}?pageNo={page}"
MAX_PAGES   = 5
OUTPUT_DIR  = "output"
WAIT_TIMEOUT = 15       # seconds to wait for elements
SCROLL_PAUSE = 1.5      # seconds between scrolls

# ─────────────────────────────────────────────
#  SELENIUM DRIVER SETUP
# ─────────────────────────────────────────────
def create_driver() -> webdriver.Chrome:
    """
    Create a headless Chrome WebDriver with anti-detection options.
    """
    options = Options()
    options.add_argument("--headless=new")           # headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    try:
        driver = webdriver.Chrome(options=options)
        # Mask webdriver detection via JS
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        log.info("Chrome WebDriver started successfully.")
        return driver
    except WebDriverException as e:
        log.error(f"Failed to start WebDriver: {e}")
        log.info("Make sure ChromeDriver is installed: pip install webdriver-manager")
        raise

# ─────────────────────────────────────────────
#  SCROLL TO BOTTOM (for infinite scroll pages)
# ─────────────────────────────────────────────
def scroll_to_bottom(driver: webdriver.Chrome):
    """Scroll page to bottom to trigger lazy-loaded content."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    log.info("Scrolled to bottom of page.")

# ─────────────────────────────────────────────
#  WAIT FOR JOB CARDS TO LOAD
# ─────────────────────────────────────────────
def wait_for_jobs(driver: webdriver.Chrome) -> bool:
    """Wait until job cards are visible on the page."""
    try:
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "article.jobTuple, div.cust-job-tuple, div.srp-jobtuple-wrapper")
            )
        )
        return True
    except TimeoutException:
        log.warning("Timed out waiting for job cards.")
        return False

# ─────────────────────────────────────────────
#  PARSE JOB CARDS FROM PAGE SOURCE
# ─────────────────────────────────────────────
def parse_jobs(page_source: str) -> list[dict]:
    """Parse job listings from page HTML using BeautifulSoup."""
    soup = BeautifulSoup(page_source, "html.parser")
    jobs = []

    # Naukri uses article tags with class jobTuple or similar
    cards = (
        soup.find_all("article", class_=lambda c: c and "jobTuple" in c) or
        soup.find_all("div",     class_=lambda c: c and "cust-job-tuple" in c) or
        soup.find_all("div",     class_=lambda c: c and "srp-jobtuple-wrapper" in c)
    )

    log.info(f"  Parsing {len(cards)} job cards …")

    for card in cards:
        job = {}

        # ── Title ─────────────────────────────
        title = card.find("a", class_=lambda c: c and "title" in c.lower()) or \
                card.find("a", attrs={"title": True})
        job["title"] = title.get_text(strip=True) if title else "N/A"

        # ── Company ───────────────────────────
        company = card.find("a", class_=lambda c: c and "company" in c.lower()) or \
                  card.find("span", class_=lambda c: c and "comp-name" in c.lower())
        job["company"] = company.get_text(strip=True) if company else "N/A"

        # ── Location ──────────────────────────
        location = card.find("span", class_=lambda c: c and "location" in c.lower()) or \
                   card.find("li",   class_=lambda c: c and "location" in c.lower())
        job["location"] = location.get_text(strip=True) if location else "N/A"

        # ── Salary ────────────────────────────
        salary = card.find("span", class_=lambda c: c and "salary" in c.lower()) or \
                 card.find("li",   class_=lambda c: c and "salary" in c.lower())
        job["salary"] = salary.get_text(strip=True) if salary else "Not Disclosed"

        # ── Experience ────────────────────────
        exp = card.find("span", class_=lambda c: c and "experience" in c.lower()) or \
              card.find("li",   class_=lambda c: c and "exp" in c.lower())
        job["experience"] = exp.get_text(strip=True) if exp else "N/A"

        # ── Description snippet ───────────────
        desc = card.find("span", class_=lambda c: c and "job-desc" in c.lower()) or \
               card.find("div",  class_=lambda c: c and "job-desc" in c.lower())
        job["description"] = desc.get_text(strip=True) if desc else "N/A"

        # ── Posted date ───────────────────────
        posted = card.find("span", class_=lambda c: c and "date" in c.lower()) or \
                 card.find("span", class_=lambda c: c and "fresh" in c.lower())
        job["posted"] = posted.get_text(strip=True) if posted else "N/A"

        # ── Job URL ───────────────────────────
        link = card.find("a", href=True, class_=lambda c: c and "title" in c.lower()) or \
               card.find("a", href=True, attrs={"title": True})
        job["url"] = link["href"] if link else "N/A"

        job["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if job["title"] != "N/A":
            jobs.append(job)

    return jobs

# ─────────────────────────────────────────────
#  NAVIGATE TO NEXT PAGE
# ─────────────────────────────────────────────
def go_to_next_page(driver: webdriver.Chrome) -> bool:
    """
    Click the 'Next' button to go to the next page.
    Returns True if successful, False if no next page.
    """
    try:
        next_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "a[class*='next'], button[class*='next'], "
                                  "span[class*='next'], a[title='Next']")
            )
        )
        driver.execute_script("arguments[0].click();", next_btn)
        time.sleep(2)
        return True
    except (TimeoutException, NoSuchElementException):
        log.info("No 'Next' button found — reached last page.")
        return False

# ─────────────────────────────────────────────
#  MAIN SCRAPER
# ─────────────────────────────────────────────
def scrape_jobs(keyword: str = "python developer",
                location: str = "india",
                max_pages: int = MAX_PAGES) -> pd.DataFrame:
    """
    Scrape job listings from Naukri for given keyword & location.
    Returns a Pandas DataFrame.
    """
    all_jobs = []
    driver   = create_driver()

    try:
        for page in range(1, max_pages + 1):
            url = BASE_URL.format(
                keyword=keyword.replace(" ", "-"),
                location=location.replace(" ", "-"),
                page=page
            )
            log.info(f"Navigating to page {page}: {url}")
            driver.get(url)

            # Wait for content
            if not wait_for_jobs(driver):
                log.warning(f"No job cards loaded on page {page}. Stopping.")
                break

            # Scroll to trigger lazy-loaded cards
            scroll_to_bottom(driver)

            # Parse HTML
            jobs = parse_jobs(driver.page_source)
            if not jobs:
                log.info("No jobs parsed. Stopping pagination.")
                break

            for j in jobs:
                j["keyword"]  = keyword
                j["page_num"] = page

            all_jobs.extend(jobs)
            log.info(f"Page {page}: +{len(jobs)} jobs (total: {len(all_jobs)})")

            # Try going to next page
            if page < max_pages and not go_to_next_page(driver):
                break

            time.sleep(2)

    except Exception as e:
        log.error(f"Unexpected error during scraping: {e}", exc_info=True)

    finally:
        driver.quit()
        log.info("WebDriver closed.")

    return pd.DataFrame(all_jobs)

# ─────────────────────────────────────────────
#  SAVE TO JSON & EXCEL
# ─────────────────────────────────────────────
def save_results(df: pd.DataFrame, keyword: str):
    """Export DataFrame to both JSON and Excel."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_kw   = keyword.replace(" ", "_")

    # ── Excel ─────────────────────────────────
    xlsx_path = os.path.join(OUTPUT_DIR, f"jobs_{safe_kw}_{timestamp}.xlsx")
    df.to_excel(xlsx_path, index=False, engine="openpyxl")
    log.info(f"Excel saved: {xlsx_path}")

    # ── JSON ──────────────────────────────────
    json_path = os.path.join(OUTPUT_DIR, f"jobs_{safe_kw}_{timestamp}.json")
    records   = df.to_dict(orient="records")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    log.info(f"JSON saved: {json_path}")

    return xlsx_path, json_path

# ─────────────────────────────────────────────
#  SCHEDULED JOB
# ─────────────────────────────────────────────
SEARCH_KEYWORD  = "python developer"
SEARCH_LOCATION = "india"

def run_daily_job():
    """Wrapper called by the scheduler every day."""
    log.info("="*55)
    log.info("Scheduled job started.")
    df = scrape_jobs(keyword=SEARCH_KEYWORD, location=SEARCH_LOCATION)

    if df.empty:
        log.warning("No data collected in this run.")
        return

    # Print summary
    print("\n" + "="*55)
    print(f"  Total jobs scraped  : {len(df)}")
    print(f"  Unique companies    : {df['company'].nunique()}")
    print(f"  Unique locations    : {df['location'].nunique()}")
    print("="*55)
    print(df[["title", "company", "location", "salary"]].head(10).to_string(index=False))
    print()

    save_results(df, SEARCH_KEYWORD)
    log.info("Scheduled job finished.")
    log.info("="*55)

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    # ── Run once immediately ───────────────────
    run_daily_job()

    # ── Then schedule for every day at 09:00 AM ─
    schedule.every().day.at("09:00").do(run_daily_job)
    log.info("Scheduler running — next run at 09:00 AM daily. Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(60)