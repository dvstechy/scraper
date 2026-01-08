import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime

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


def is_company_match(text, company):
    text = text.lower()
    for keyword in COMPANY_NAME_MAP.get(company, []):
        if re.search(rf"\b{re.escape(keyword)}\b", text):
            return True
    return False


def get_month_from_title(title):
    m = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)", title.lower())
    if m:
        return m.group(1).title()
    return datetime.now().strftime("%B")


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

    # Remove duplicates
    unique = {}
    for p in posts:
        unique[p["link"]] = p
    return list(unique.values())


def extract_tables_from_post(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    all_rows = []
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if not headers:
            continue
        for tr in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) == len(headers):
                row = dict(zip(headers, cells))
                all_rows.append(row)
    return all_rows


def scrape_current_month_schemes():
    posts = fetch_all_posts()
    results = []

    for company in COMPANY_NAME_MAP:
        # Filter posts matching company
        matched = [p for p in posts if is_company_match(p["title"], company)]
        if not matched:
            results.append({
                "Company": company,
                "Source": "AutoPunditz",
                "Month": datetime.now().strftime("%B"),
                "Model": "",
                "Offer Type": "",
                "Offer Details": "No post found for this company",
                "Link": ""
            })
            continue

        # Work through matched posts (usually the latest will be first)
        for post in matched:
            month = get_month_from_title(post["title"])
            table_rows = extract_tables_from_post(post["link"])

            if not table_rows:
                results.append({
                    "Company": company,
                    "Source": "AutoPunditz",
                    "Month": month,
                    "Model": "",
                    "Offer Type": "",
                    "Offer Details": "No table found in post",
                    "Link": post["link"]
                })
                continue

            for row in table_rows:
                results.append({
                    "Company": company,
                    "Source": "AutoPunditz",
                    "Month": month,
                    **row,
                    "Link": post["link"]
                })

    return pd.DataFrame(results)


if __name__ == "__main__":
    df = scrape_current_month_schemes()
    print(df)
