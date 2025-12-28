# market_position.py

import pandas as pd
import re
from io import StringIO
from utils import get_soup, clean
from config import URLS

def normalize_make(make):
    make = make.lower()
    mapping = {
        "maruti": "Maruti Suzuki",
        "tata": "Tata Motors",
        "hyundai": "Hyundai",
        "mahindra": "Mahindra",
        "kia": "Kia",
        "mg": "MG Motor",
        "toyota": "Toyota",
        "honda": "Honda",
        "renault": "Renault",
        "nissan": "Nissan",
        "skoda": "Skoda",
        "volkswagen": "Volkswagen",
        "byd": "BYD",
        "volvo": "Volvo"
    }
    for key, value in mapping.items():
        if key in make:
            return value
    return None

def extract_period(soup):
    heading = soup.find(["h1", "h2", "h3"], string=re.compile("flash", re.I))
    if not heading:
        return "Unknown Period"

    text = clean(heading.get_text())

    # Try to extract Month Year (e.g. November 2025)
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
        text
    )

    if match:
        return match.group(0)

    return text

def scrape_market_position(companies):
    soup = get_soup(URLS["market_position"])
    period = extract_period(soup)

    tables = pd.read_html(StringIO(str(soup)))
    maker_table = max(tables, key=lambda x: x.shape[0])
    maker_table.columns = [clean(c) for c in maker_table.columns]

    sales_col = maker_table.columns[1]

    company_units = {}
    total_units = 0

    for _, row in maker_table.iterrows():
        raw_make = clean(row.iloc[0])
        if not raw_make or raw_make.lower() in ["total", "others"]:
            continue

        try:
            units = int(str(row[sales_col]).replace(",", ""))
        except:
            units = 0

        normalized = normalize_make(raw_make)
        if normalized:
            company_units[normalized] = units
            total_units += units

    data = []
    for company in companies:
        units = company_units.get(company, 0)
        share = (units / total_units * 100) if total_units else 0
        data.append({
            "Company":company,
            "Units Sold": units,
            "Market Share (%)": round(share, 2),
            "Period": period,
            "Source": URLS["market_position"]
        })

    df = pd.DataFrame(data).sort_values("Units Sold", ascending=False)
    df["Market Position"] = range(1, len(df) + 1)
    return df
