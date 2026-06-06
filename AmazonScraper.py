"""
============================================================
  Amazon Product Price Scraper
  Author : Harshit Kumar Mishra
  Tech   : Python | BeautifulSoup | Requests | Pandas | CSV
============================================================
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging, time, random, os
from datetime import datetime

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    handlers=[logging.FileHandler("amazon_scraper.log"), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────
MAX_PAGES   = 3
RETRY_LIMIT = 3
DELAY_MIN   = 3.0
DELAY_MAX   = 6.0
OUTPUT_DIR  = "output"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

def get_headers() -> dict:
    return {
        "User-Agent"                : random.choice(USER_AGENTS),
        "Accept"                    : "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language"           : "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding"           : "gzip, deflate, br",
        "Connection"                : "keep-alive",
        "Upgrade-Insecure-Requests" : "1",
        "Sec-Fetch-Dest"            : "document",
        "Sec-Fetch-Mode"            : "navigate",
        "Sec-Fetch-Site"            : "none",
        "Sec-Fetch-User"            : "?1",
        "sec-ch-ua"                 : '"Chromium";v="124","Google Chrome";v="124"',
        "sec-ch-ua-mobile"          : "?0",
        "sec-ch-ua-platform"        : '"Windows"',
        "DNT"                       : "1",
    }

# ── Fetch with retry ─────────────────────────────────────
def fetch_page(url: str, session: requests.Session):
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            log.info(f"Fetching (attempt {attempt}): {url}")
            resp = session.get(url, headers=get_headers(), timeout=15)

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                if "captcha" in resp.text.lower() or "Type the characters" in resp.text:
                    log.error("CAPTCHA page detected! Try again later.")
                    return None
                return soup
            elif resp.status_code == 503:
                log.warning("503 – Rate limited. Waiting 15s …")
                time.sleep(15)
            elif resp.status_code == 404:
                log.error("404 – Page not found.")
                return None
            else:
                log.warning(f"Status {resp.status_code}. Retrying …")

        except requests.exceptions.ConnectionError:
            log.error(f"Connection error on attempt {attempt}.")
        except requests.exceptions.Timeout:
            log.error(f"Request timed out on attempt {attempt}.")
        except Exception as e:
            log.error(f"Unexpected error: {e}")

        wait = 2 ** attempt + random.uniform(1, 3)
        log.info(f"Waiting {wait:.1f}s before retry …")
        time.sleep(wait)

    log.error(f"All {RETRY_LIMIT} attempts failed.")
    return None

# ── Parse products ───────────────────────────────────────
def parse_products(soup: BeautifulSoup) -> list:
    products = []

    # Amazon wraps every result in a div with data-asin attribute
    cards = soup.find_all("div", attrs={"data-asin": True})
    # Filter out empty asin (ads / placeholders)
    cards = [c for c in cards if c.get("data-asin", "").strip()]
    log.info(f"  Found {len(cards)} product cards.")

    for card in cards:
        product = {}

        # ── ASIN ──────────────────────────────────────────
        product["asin"] = card.get("data-asin", "N/A")

        # ── Name ──────────────────────────────────────────
        # Try multiple selectors Amazon uses for product title
        name_tag = (
            card.find("span", attrs={"class": lambda c: c and "a-size-medium" in c}) or
            card.find("span", attrs={"class": lambda c: c and "a-size-base-plus" in c}) or
            card.find("h2")
        )
        if name_tag:
            # If it's an h2, dig into the inner span
            inner = name_tag.find("span") if name_tag.name == "h2" else name_tag
            product["name"] = inner.get_text(strip=True) if inner else name_tag.get_text(strip=True)
        else:
            product["name"] = "N/A"

        # ── Price ─────────────────────────────────────────
        # Amazon splits price into whole + fraction spans
        price_symbol = card.find("span", class_="a-price-symbol")
        price_whole  = card.find("span", class_="a-price-whole")
        price_frac   = card.find("span", class_="a-price-fraction")

        if price_whole:
            sym  = price_symbol.get_text(strip=True) if price_symbol else "₹"
            whole = price_whole.get_text(strip=True).replace(",", "").replace(".", "")
            frac  = price_frac.get_text(strip=True) if price_frac else "00"
            product["price"] = f"{sym}{whole}.{frac}"
        else:
            # Fallback: look for any a-price offscreen span
            offscreen = card.find("span", class_="a-offscreen")
            product["price"] = offscreen.get_text(strip=True) if offscreen else "N/A"

        # ── Rating ────────────────────────────────────────
        rating_tag = card.find("span", class_="a-icon-alt")
        if rating_tag:
            txt = rating_tag.get_text(strip=True)           # e.g. "4.2 out of 5 stars"
            product["rating"] = txt.split(" ")[0]
        else:
            product["rating"] = "N/A"

        # ── Reviews count ─────────────────────────────────
        reviews_tag = card.find("span", attrs={"class": lambda c: c and "a-size-base" in c,
                                               "aria-label": True})
        if not reviews_tag:
            # Try finding the review count link
            rev_link = card.find("a", href=lambda h: h and "customerReviews" in str(h))
            reviews_tag = rev_link.find("span") if rev_link else None

        product["reviews"] = reviews_tag.get_text(strip=True) if reviews_tag else "N/A"

        # ── Product URL ───────────────────────────────────
        link = card.find("a", class_=lambda c: c and "a-link-normal" in c, href=True)
        if link:
            href = link["href"]
            product["url"] = ("https://www.amazon.in" + href) if href.startswith("/") else href
        else:
            product["url"] = "N/A"

        # Only add if we got a real product name
        if product["name"] != "N/A":
            products.append(product)

    return products

# ── Main scraper ─────────────────────────────────────────
def scrape_amazon(keyword: str, max_pages: int = MAX_PAGES) -> pd.DataFrame:
    all_products = []
    session = requests.Session()
    log.info(f"Starting Amazon scrape for: '{keyword}'")

    for page in range(1, max_pages + 1):
        url = f"https://www.amazon.in/s?k={keyword.replace(' ', '+')}&page={page}"
        soup = fetch_page(url, session)

        if soup is None:
            log.warning(f"Skipping page {page}.")
            continue

        products = parse_products(soup)

        if not products:
            log.warning(f"No products parsed on page {page}. "
                        "Amazon may have changed HTML — check debug_page.html")
            # Save page source for manual inspection
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            log.info("Page HTML saved to debug_page.html for inspection.")
            break

        for p in products:
            p["page"]       = page
            p["keyword"]    = keyword
            p["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        all_products.extend(products)
        log.info(f"Page {page}: +{len(products)} products (total: {len(all_products)})")

        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        log.info(f"Sleeping {delay:.1f}s …")
        time.sleep(delay)

    df = pd.DataFrame(all_products)
    log.info(f"Scrape complete. Total: {len(df)} products.")
    return df

# ── Save CSV ─────────────────────────────────────────────
def save_to_csv(df: pd.DataFrame, keyword: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_kw  = keyword.replace(" ", "_")
    filepath = os.path.join(OUTPUT_DIR, f"amazon_{safe_kw}_{ts}.csv")
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    log.info(f"Saved: {filepath}")
    return filepath

# ── Entry point ──────────────────────────────────────────
if __name__ == "__main__":
    KEYWORD   = "wireless earphones"
    MAX_PAGES = 3

    df = scrape_amazon(keyword=KEYWORD, max_pages=MAX_PAGES)

    if df.empty:
        log.warning("No data collected.")
        log.info(">>> Open 'debug_page.html' in your browser to see what Amazon returned.")
    else:
        # Clean price for stats
        numeric_prices = pd.to_numeric(
            df["price"].str.replace("[₹,]", "", regex=True), errors="coerce"
        )
        print("\n" + "="*55)
        print(f"  Keyword       : {KEYWORD}")
        print(f"  Total scraped : {len(df)}")
        print(f"  Avg Price     : ₹{numeric_prices.mean():.0f}")
        print(f"  Cheapest      : ₹{numeric_prices.min():.0f}")
        print(f"  Most Expensive: ₹{numeric_prices.max():.0f}")
        print("="*55)
        print(df[["name", "price", "rating", "reviews"]].head(10).to_string(index=False))
        save_to_csv(df, KEYWORD)