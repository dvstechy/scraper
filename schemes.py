import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from PIL import Image
from io import BytesIO
import numpy as np
import cv2
from paddleocr import PaddleOCR, PPStructure

import tempfile


# ------------------ EASYOCR INIT ------------------
table_engine = PPStructure(show_log=False)


# ------------------ CONFIG ------------------

COMPANY_NAME_MAP = {
    "Maruti Suzuki": ["maruti", "nexa"],
    "Hyundai": ["hyundai"]
    # "Mahindra": ["mahindra"],
    # "Kia": ["kia"],
    # "MG Motor": ["mg"],
    # "Toyota": ["toyota"],
    # "Honda": ["honda"],
    # "Renault": ["renault"],
    # "Nissan": ["nissan"],
    # "Skoda": ["skoda"],
    # "Volkswagen": ["volkswagen", "vw"],
    # "BYD": ["byd"],
    # "Volvo": ["volvo"],
    # "Tata Motors": ["tata"]
}

URL_PATTERNS = {
    "Maruti Suzuki": "discounts-and-offers-on-maruti-suzuki-nexa-cars-for-{month}-{year}",
    "Hyundai": "discounts-and-offers-on-hyundai-cars-for-{month}-{year}"
}

def construct_direct_url(company, year, month):
    pattern = URL_PATTERNS.get(company)
    if not pattern:
        return None
    slug = pattern.format(month=month.lower(), year=year)
    return f"https://www.autopunditz.com/post/{slug}"

# ------------------ UTILS ------------------

def is_company_match(text, company):
    text = text.lower()
    for keyword in COMPANY_NAME_MAP.get(company, []):
        if keyword in text:
            return True
    return False


def get_month_from_title(title):
    m = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)",
        title.lower()
    )
    if m:
        return m.group(1).title()
    return datetime.now().strftime("%B")


# ------------------ STEP 1: FETCH MONTH POSTS ------------------

def fetch_all_posts():
    url = "https://www.autopunditz.com/offers-for-the-month"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    posts = []
    for a in soup.select("a[href*='/post/']"):
        title = a.get_text(strip=True)
        link = a.get("href")
        if title and link:
            if not link.startswith("http"):
                link = "https://www.autopunditz.com" + link
            posts.append({"title": title, "link": link})

    unique = {}
    for p in posts:
        unique[p["link"]] = p

    return list(unique.values())


# ------------------ STEP 2: IMAGE TABLE OCR (EASYOCR) ------------------
def extract_table_from_image_url(image_url):
    print(f"   Downloading image: {image_url}")

    response = requests.get(image_url, timeout=30)
    image = Image.open(BytesIO(response.content)).convert("RGB")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        image.save(tmp.name)
        image_path = tmp.name

    try:
        result = table_engine(image_path)

        tables = []

        for res in result:
            if res['type'] == 'table':
                html = res['res']['html']
                dfs = pd.read_html(html)
                if dfs:
                    tables.append(dfs[0])

        if not tables:
            print("   ❌ No table detected by PaddleOCR")
            return pd.DataFrame()

        final_df = pd.concat(tables, ignore_index=True)
        final_df = final_df.dropna(how="all")
        final_df = final_df.loc[:, ~final_df.columns.str.contains('^Unnamed')]

        return final_df

    except Exception as e:
        print("   ❌ PaddleOCR error:", e)
        return pd.DataFrame()

    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

# ------------------ STEP 3: MAIN SCRAPER ------------------
def scrape_schemes(company):
    posts = fetch_all_posts()
    all_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"\nProcessing company: {company}")

        matched = [p for p in posts if is_company_match(p["title"], company)]

        if not matched:
            print("   No post found.")
            browser.close()
            return pd.DataFrame()


        def extract_year_month(title):
            m = re.search(
                r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})",
                title.lower()
            )
            if m:
                month = m.group(1).title()
                year = int(m.group(2))
                month_num = datetime.strptime(month, "%B").month
                return year, month_num
            return 0, 0

        now = datetime.now()
        current_month = now.strftime("%B").lower()
        current_year = now.year
        post = None

        if matched:
            matched.sort(key=lambda x: extract_year_month(x["title"]), reverse=True)
            post = matched[0]
            latest_title = post["title"].lower()
            if current_month not in latest_title or str(current_year) not in latest_title:
                direct_url = construct_direct_url(company, current_year, current_month)
                print(f"   Index outdated, using DIRECT URL: {direct_url}")
                post_url = direct_url
                month = current_month.title()
            else:
                post_url = post["link"]
                month = get_month_from_title(post["title"])
                print(f"   Using INDEX post: {post_url}")
        else:
            direct_url = construct_direct_url(company, current_year, current_month)
            print(f"   Index missing, using DIRECT URL: {direct_url}")
            post_url = direct_url
            month = current_month.title()


        print(f"   Using post: {post_url}")

        page.goto(post_url, timeout=60000)
        page.wait_for_timeout(4000)

        images = page.query_selector_all(
            "wow-image img"
        )



        if not images:
            print("   No images found.")
            browser.close()
            return pd.DataFrame()

        image_urls = []

        for el in images:
            src = el.get_attribute("src")
            style = el.get_attribute("style")

            if src and "wixstatic" in src.lower():
                src_lower=src.lower()

                if any(x in src_lower for x in ["logo", "icon", "facebook", "twitter", "google", "insta"]):
                    continue
                # remove low quality blur images
                if "blur_" in src_lower or "w_49" in src_lower or "w_30" in src_lower:
                    continue
                image_urls.append(src)

            elif style and "wixstatic" in style.lower():
                m = re.search(r'url\("(.*?)"\)', style)
                if m:
                    real_url = m.group(1)
                    real_lower = real_url.lower()
                    if any(x in real_lower for x in ["logo", "icon", "facebook", "twitter", "google", "insta"]):
                        continue
                    if "blur_" in real_lower or "w_49" in real_lower or "w_30" in real_lower:
                        continue
                    image_urls.append(real_url)

        # remove duplicates
        image_urls = list(set(image_urls))

        print(f"   Found {len(image_urls)} usable image(s)")

        for src in image_urls:
            print(f"   Downloading image: {src}")
            try:
                df_img = extract_table_from_image_url(src)

                if df_img.empty:
                    print("   OCR table empty, skipping.")
                    continue

                df_img.insert(0, "Company", company)
                df_img.insert(1, "Source", "AutoPunditz (Image)")
                df_img.insert(2, "Month", month)
                df_img["Link"] = post_url

                all_results.append(df_img)
                print("   ✔ Table extracted successfully")

            except Exception as e:
                print("   ❌ Error extracting image table:", e)

        browser.close()

    if all_results:
        final_df = pd.concat(all_results, ignore_index=True)
        return final_df
    else:
        return pd.DataFrame()
