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
# from paddleocr import PaddleOCR
from paddleocr import PPStructure
import tempfile
 
 
# ------------------ EASYOCR INIT ------------------
table_engine = PPStructure(show_log=False, layout=False, ocr=True, table=True)
 
 
# ------------------ CONFIG ------------------
 
COMPANY_NAME_MAP = {
    "Maruti Suzuki": ["maruti", "nexa"],
    "Hyundai": ["hyundai"],
    "Mahindra": ["mahindra"],
    "Kia": ["kia"],
    "MG Motor": ["mg"],
    "Toyota": ["toyota"],
    "Honda": ["honda"],
    "Renault": ["renault"],
    "Nissan": ["nissan"],
    "Skoda": ["skoda"],
    "Volkswagen": ["volkswagen", "vw"],
    "BYD": ["byd"],
    "Volvo": ["volvo"],
    "Tata Motors": ["tata"]
}
 
URL_PATTERNS = {
    "Maruti Suzuki": "discounts-and-offers-on-maruti-suzuki-nexa-cars-for-{month}-{year}",
    "Hyundai": "discounts-and-offers-on-hyundai-cars-for-{month}-{year}",
    "Mahindra": "discounts-and-offers-on-mahindra-cars-for-{month}-{year}",
    "Kia": "discounts-and-offers-on-kia-cars-in-{month}-{year}",
    "MG Motor": "discounts-and-offers-on-mg-cars-for-{month}-{year}",
    "Toyota": "discounts-and-offers-on-toyota-cars-for-{month}-{year}",
    "Honda": "discounts-and-offers-on-honda-cars-for-{month}-{year}",
    "Renault": "discounts-and-offers-on-renault-cars-for-{month}-{year}",
    "Nissan": "discounts-and-offers-on-nissan-cars-for-{month}-{year}",
    "Skoda": "skoda-discounts-offers-for-{month}-{year}",
    "Volkswagen": "discounts-and-offers-on-volkswagen-cars-for-{month}-{year}",
    "BYD": "discounts-and-offers-on-byd-cars-for-{month}-{year}",
    "Volvo": "discounts-and-offers-on-volvo-cars-for-{month}-{year}",
    "Tata Motors": "discounts-and-offers-on-tata-cars-for-{month}-{year}"
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
 
 
def find_latest_post_for_company(posts, company):
    """
    From index page posts, find latest post for company based on title date.
    """
    matched = [p for p in posts if is_company_match(p["title"], company)]
 
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
 
    if not matched:
        return None
 
    matched.sort(key=lambda x: extract_year_month(x["title"]), reverse=True)
    return matched[0]
 
 
 
# ------------------ STEP 2: IMAGE TABLE OCR (EASYOCR) ------------------
# def extract_table_from_image_url(image_url):
#     print(f"   Downloading image: {image_url}")
 
#     try:
#         response = requests.get(image_url, timeout=30)
#         image = Image.open(BytesIO(response.content)).convert("RGB")
 
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
#             image.save(tmp.name)
#             image_path = tmp.name
 
#         result = table_engine(image_path)
 
#         tables = []
 
#         for res in result:
#             if res["type"] == "table":
#                 html = res["res"]["html"]
#                 dfs = pd.read_html(html)
#                 for df in dfs:
#                     tables.append(df)
 
#         if not tables:
#             print("   ❌ No table detected by PaddleOCR")
#             return pd.DataFrame()
 
#         final_df = pd.concat(tables, ignore_index=True)
 
#         # ---------------- CLEANUP ----------------
#         final_df = final_df.dropna(how="all")
#         final_df = final_df.loc[:, ~final_df.columns.astype(str).str.contains("^Unnamed")]
#         final_df.columns = [str(c).strip() for c in final_df.columns]
 
#         # ---------------- CRITICAL FIX ----------------
#         model_col = final_df.columns[0]
 
#         # Normalize
#         final_df[model_col] = final_df[model_col].astype(str).str.strip()
#         final_df[model_col] = final_df[model_col].replace(["", "nan", "None"], np.nan)
 
#         # Forward fill
#         final_df[model_col] = final_df[model_col].ffill()
 
#         # ---------------- HARD BOUNDARY FIX ----------------
#         # If a row contains a new model name, force overwrite
#         known_models = final_df[model_col].dropna().unique().tolist()
 
#         current_model = None
#         cleaned_models = []
 
#         for val in final_df[model_col]:
#             if val in known_models:
#                 current_model = val
#                 cleaned_models.append(val)
#             else:
#                 cleaned_models.append(current_model)
 
#         final_df[model_col] = cleaned_models
 
#         # ---------------- REMOVE GARBAGE ----------------
#         final_df = final_df[~final_df[model_col].str.contains(
#             "either scrap|exchange|t&c|conditions apply", case=False, na=False
#         )]
 
#         final_df = final_df.reset_index(drop=True)
 
#         return final_df
 
#     except Exception as e:
#         print("   ❌ PaddleOCR error:", e)
#         return pd.DataFrame()
 
#     finally:
#         try:
#             os.remove(image_path)
#         except:
#             pass
 
def extract_table_from_image_url(image_url):
    print(f"   Downloading image: {image_url}")
 
    try:
        response = requests.get(image_url, timeout=30)
        image = Image.open(BytesIO(response.content)).convert("RGB")
 
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            image.save(tmp.name)
            image_path = tmp.name
 
        result = table_engine(image_path)
        tables = []
 
        for res in result:
            if res["type"] == "table":
                html = res["res"]["html"]
                dfs = pd.read_html(html)
                for df in dfs:
                    tables.append(df)
 
        if not tables:
            print("   ❌ No table detected by PaddleOCR")
            return pd.DataFrame()
 
        # Combine all detected table fragments
        final_df = pd.concat(tables, ignore_index=True)
 
        # ---------------- 1. CLEANUP UNNAMED & EMPTY ----------------
        final_df = final_df.dropna(how="all")
        # Remove columns that are 100% "Unnamed"
        final_df = final_df.loc[:, ~final_df.columns.astype(str).str.contains("^Unnamed")]
        final_df.columns = [str(c).strip() for c in final_df.columns]
 
        # Identify key columns by index (Model is usually 0, Variant is 1)
        model_col = final_df.columns[0]
        variant_col = final_df.columns[1] if len(final_df.columns) > 1 else model_col
 
        # ---------------- 2. STRIP HEADERS CAPTURED AS DATA ----------------
        # This prevents the "Row Shift" you see in your Excel
        header_keywords = ["MODEL", "VARIANT", "GROUP", "CONSUMER", "EXCHANGE"]
        final_df = final_df[~final_df[model_col].astype(str).str.upper().isin(header_keywords)]
       
        # Normalize strings
        final_df[model_col] = final_df[model_col].astype(str).str.strip().replace(["", "nan", "None", "None None"], np.nan)
        if variant_col != model_col:
            final_df[variant_col] = final_df[variant_col].astype(str).str.strip().replace(["", "nan", "None"], np.nan)
 
        # ---------------- 3. CONDITIONAL FORWARD FILL (THE FIX) ----------------
        # Instead of global .ffill(), we only fill the Model if a Variant exists
        # in that row. This keeps Ignis variants with Ignis and Baleno with Baleno.
        for i in range(1, len(final_df)):
            current_model = final_df.iloc[i][model_col]
            current_variant = final_df.iloc[i][variant_col]
           
            # If Model is empty but Variant has data, it belongs to the previous Model
            if pd.isna(current_model) and pd.notna(current_variant):
                final_df.iloc[i, final_df.columns.get_loc(model_col)] = final_df.iloc[i-1][model_col]
 
        # ---------------- 4. REMOVE FOOTER GARBAGE ----------------
        # Clean up disclaimer text that PaddleOCR often puts in the Model column
        garbage_mask = final_df[model_col].astype(str).str.contains(
            "either scrap|exchange|t&c|conditions apply|applicable|policy|total max",
            case=False, na=False
        )
        final_df = final_df[~garbage_mask]
 
        # Final check: Drop rows where all numerical data is missing
        # (Keeps the table clean of OCR noise)
        final_df = final_df.dropna(subset=final_df.columns[2:], how='all')
 
        final_df = final_df.reset_index(drop=True)
        return final_df
 
    except Exception as e:
        print("   ❌ PaddleOCR error:", e)
        return pd.DataFrame()
 
    finally:
        try:
            if 'image_path' in locals():
                os.remove(image_path)
        except:
            pass
# ------------------ STEP 3: MAIN SCRAPER ------------------
def scrape_schemes(company):
    posts = fetch_all_posts()
    all_results = []
 
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
 
        print(f"\nProcessing company: {company}")
 
        now = datetime.now()
        current_month = now.strftime("%B").lower()
        current_year = now.year
 
        # 1️⃣ Try current month direct URL first
        post_url = construct_direct_url(company, current_year, current_month)
        month = current_month.title()
 
        print(f"   Trying current month URL: {post_url}")
 
        page.goto(post_url, timeout=60000)
        page.wait_for_timeout(3000)
 
        images = page.query_selector_all("wow-image img")
 
        # 2️⃣ If no images → fallback to latest available post
        if not images:
            print(f"   ⚠️ No data for current month. Falling back to latest available post...")
 
            latest_post = find_latest_post_for_company(posts, company)
 
            if not latest_post:
                print(f"   ❌ No posts found at all for {company}. Skipping.")
                browser.close()
                return pd.DataFrame()
 
            post_url = latest_post["link"]
            month = get_month_from_title(latest_post["title"])
 
            print(f"   Using fallback post: {post_url}")
 
            page.goto(post_url, timeout=60000)
            page.wait_for_timeout(3000)
 
            images = page.query_selector_all("wow-image img")
 
            if not images:
                print(f"   ❌ Even fallback post has no images. Skipping {company}.")
                browser.close()
                return pd.DataFrame()
 
        print(f"   Using post: {post_url}")
 
        # ------------------ IMAGE EXTRACTION ------------------
        image_urls = []
 
        for el in images:
            src = el.get_attribute("src")
            style = el.get_attribute("style")
 
            if src and "wixstatic" in src.lower():
                src_lower = src.lower()
 
                if any(x in src_lower for x in ["logo", "icon", "facebook", "twitter", "google", "insta"]):
                    continue
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
 
        # ------------------ OCR TABLE EXTRACTION ------------------
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
 
 