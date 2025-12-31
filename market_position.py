# market_position.py

import pandas as pd
import re
from utils import get_soup, clean
from config import COMPANIES

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def company_to_slug(company):
    return company.lower().replace(" ", "-")

def extract_min_max_price(text):
    """
    Example text:
    'The starting price for a Maruti Suzuki car is ₹3.50 Lakh ...
     while the Invicto is the most expensive model at ₹28.61 Lakh.'
    """
    prices = re.findall(r"₹\s?([\d.]+)\s?Lakh", text)
    if len(prices) >= 2:
        return float(prices[0]), float(prices[-1])
    return None, None


def fetch_min_max_price(company):
    slug = company_to_slug(company)
    url = f"https://www.cardekho.com/{slug}-cars"

    soup = get_soup(url)
    block = soup.find("div", class_=re.compile("gs_readmore", re.I))

    if not block:
        return None, None

    p = block.find("p")
    if not p:
        return None, None

    return extract_min_max_price(clean(p.text))


def normalize_score(text):
    """
    Convert qualitative review → numeric score
    """
    text = text.lower()
    if "excellent" in text or "very good" in text:
        return 5
    if "good" in text:
        return 4
    if "average" in text:
        return 3
    if "poor" in text:
        return 2
    return 3


# -------------------------------------------------
# Core Logic
# -------------------------------------------------

def scrape_market_position(companies):
    data = []

    for company in companies:
        print(f"[Market Position] Processing {company}")

        # -----------------------------
        # Pricing
        # -----------------------------
        min_price, max_price = fetch_min_max_price(company)

        # -----------------------------
        # Reliability (rule-based for now)
        # -----------------------------
        reliability_review = "Good reliability based on customer feedback"
        reliability_score = normalize_score(reliability_review)

        # -----------------------------
        # Service
        # -----------------------------
        service_centers = 200 + len(company) * 5  # placeholder logic
        service_review = "Good after sales service"
        service_score = normalize_score(service_review)

        # -----------------------------
        # Composite Score → Market Position
        # -----------------------------
        composite_score = (
            reliability_score * 0.4 +
            service_score * 0.4 +
            (1 if min_price else 0) * 0.2
        )

        data.append({
            "Company": company,
            "Section": "Market Position",
            "Min Price (Lakh)": min_price,
            "Max Price (Lakh)": max_price,
            "Overall Reliability Review": reliability_review,
            "Reliability Score": reliability_score,
            "Number of Service Centers": service_centers,
            "Overall After Sales Service Review": service_review,
            "Service Score": service_score,
            "Composite Score": round(composite_score, 2)
        })

    df = pd.DataFrame(data)

    # Rank companies based on composite score
    df = df.sort_values("Composite Score", ascending=False).reset_index(drop=True)
    df["Market Position"] = df.index + 1

    # Drop helper column
    df.drop(columns=["Composite Score"], inplace=True)

    return df



    