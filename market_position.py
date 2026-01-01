import pandas as pd
import re
from playwright.sync_api import sync_playwright

# -------------------------------------------------
# Helpers
# -------------------------------------------------
COMPANY_URLS = {
    "Maruti Suzuki": "maruti-suzuki-cars",
    "Hyundai": "cars/Hyundai",
    "Mahindra": "cars/Mahindra",
    "Kia": "cars/Kia",
    "MG Motor": "cars/MG",
    "Toyota": "toyota-cars",
    "Honda": "cars/Honda",
    "Renault": "cars/Renault",
    "Nissan": "cars/Nissan",
    "Skoda": "cars/Skoda",
    "Volkswagen": "cars/Volkswagen",
    "BYD": "cars/BYD",
    "Volvo": "cars/Volvo",
    "Tata Motors": "cars/Tata"
}

# -------------------------------------------------
# Pricing SCRAPER
# -------------------------------------------------

def fetch_min_max_price(page, company: str):
    slug = COMPANY_URLS.get(company)
    if not slug:
        return None, None

    url = f"https://www.cardekho.com/{slug}"

    page.goto(url, timeout=60000)

    try:
        page.wait_for_selector("div.gs_readmore p", timeout=15000)
    except:
        print(f"[WARN] gs_readmore not found for {company}")
        return None, None

    para_text = page.locator("div.gs_readmore p").first.inner_text()

    match = re.search(
        r"The starting price.*?₹\s*([\d.]+)\s*Lakh.*?₹\s*([\d.]+)\s*Lakh",
        para_text,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        print(f"[WARN] Price sentence not found for {company}")
        return None, None

    return float(match.group(1)), float(match.group(2))


# -------------------------------------------------
# RELIABILITY SCRAPER (MODEL-LEVEL)
# -------------------------------------------------

def fetch_brand_overall_rating(page, company):
    slug = COMPANY_URLS.get(company)
    if not slug:
        return None, None, 3

    page.goto(f"https://www.cardekho.com/{slug}", timeout=60000)

    try:
        page.wait_for_selector("div.startRating", timeout=15000)

        rating_text = page.locator("span.ratingStarNew").first.inner_text()
        rating = float(re.findall(r"[\d.]+", rating_text)[0])

        reviews_text = page.locator("span.bottomText").first.inner_text()
        reviews = reviews_text.replace("|", "").strip()  # "9.2K reviews"

        score = rating_to_score(rating, reviews)

        return rating, reviews, score

    except:
        return None, None, 3

def rating_to_score(rating, reviews_text):
    try:
        reviews_text = reviews_text.lower()

        if "k" in reviews_text:
            count = float(re.findall(r"[\d.]+", reviews_text)[0]) * 1000
        else:
            count = float(re.findall(r"\d+", reviews_text)[0])
    except:
        count = 0  # fallback

    if rating >= 4.5 and count >= 5000:
        return 5
    elif rating >= 4.0 and count >= 3000:
        return 4
    elif rating >= 3.5:
        return 3
    else:
        return 2



# -------------------------------------------------
# Service SCRAPER 
# -------------------------------------------------

def fetch_service_centers(page, company: str):
    slug = COMPANY_URLS.get(company)
    if not slug:
        return None

    url = f"https://www.cardekho.com/{slug}"
    page.goto(url, timeout=60000)

    try:
        page.wait_for_selector("section.KeyHighlights table", timeout=15000)
    except:
        print(f"[WARN] Key Highlights not found for {company}")
        return None

    rows = page.locator("section.KeyHighlights table tbody tr")

    for i in range(rows.count()):
        key = rows.nth(i).locator("td").nth(0).inner_text().strip().lower()
        value = rows.nth(i).locator("td").nth(1).inner_text().strip()

        if key == "service centers":
            # Extract number safely
            match = re.search(r"\d+", value.replace(",", ""))
            return int(match.group()) if match else None

    print(f"[WARN] Service Centers row missing for {company}")
    return None

def service_centers_to_review_and_score(count):
    if count is None:
        return "After sales service data not available", 3
    elif count >= 1000:
        return "Excellent after sales service network", 5
    elif count >= 500:
        return "Very good after sales service network", 4
    elif count >= 250:
        return "Good after sales service network", 4
    elif count >= 100:
        return "Average after sales service network", 3
    else:
        return "Limited after sales service network", 2


# -------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------

def scrape_market_position(companies):
    data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for company in companies:
            print(f"[Market Position] {company}")

            min_p, max_p = fetch_min_max_price(page, company)
            overall_rating, review_count, review_score = fetch_brand_overall_rating(page, company)


            service_centers = fetch_service_centers(page, company)
            service_review, service_score = service_centers_to_review_and_score(service_centers)


            composite = (
                review_score * 0.4 +
                service_score * 0.4 +
                (1 if min_p else 0) * 0.2
            )


            data.append({
                "Company": company,
                "Section": "Market Position",
                "Min Price (Lakh)": min_p,
                "Max Price (Lakh)": max_p,
                "Overall Rating": overall_rating,
                "Overall Reviews Count": review_count,
                "Review Score": review_score,
                "Number of Service Centers": service_centers,
                "Overall After Sales Service Review": service_review,
                "Service Score": service_score,
                "Composite Score": round(composite, 2)
            })

        browser.close()

    df = pd.DataFrame(data)
    df = df.sort_values("Composite Score", ascending=False).reset_index(drop=True)
    df["Market Position"] = df.index + 1
    df.drop(columns=["Composite Score"], inplace=True)

    return df