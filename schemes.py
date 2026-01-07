import feedparser
import pandas as pd
import time
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re
 
 
def extract_models_from_text(text, company):
    models = set()
    candidates = re.split(r",| and ", text)
 
    for chunk in candidates:
        chunk = chunk.strip()
        words = chunk.split()
        if 1 <= len(words) <= 3:
            name = " ".join(words)
            if name[0].isupper() and company.lower() not in name.lower():
                if not any(x in name.lower() for x in ["india", "price", "offer", "scheme", "discount"]):
                    models.add(name)
 
    return list(models)
 
 
def extract_scheme_details(url, company):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True).lower()
 
        # === SCHEME SIGNAL FILTER (CRITICAL) ===
        scheme_signals = ["exchange", "corporate", "loyalty", "festival", "finance", "emi", "dealer"]
        if not any(word in text for word in scheme_signals):
            return None  # ❌ Not a scheme article
 
        parts = []
 
        # Exchange
        m = re.search(r"exchange.*?₹\s?([\d,]+)", text)
        if m:
            parts.append(f"Exchange Bonus: ₹{m.group(1)}")
 
        # Corporate
        m = re.search(r"corporate.*?₹\s?([\d,]+)", text)
        if m:
            parts.append(f"Corporate Offer: ₹{m.group(1)}")
 
        # Loyalty
        m = re.search(r"loyalty.*?₹\s?([\d,]+)", text)
        if m:
            parts.append(f"Loyalty Bonus: ₹{m.group(1)}")
 
        # Finance
        if "finance" in text or "low emi" in text:
            parts.append("Finance Scheme Available")
 
        # Festival
        if any(x in text for x in ["festival", "diwali", "dussehra", "navratri", "pongal"]):
            parts.append("Festival Scheme")
 
        # Models
        models = extract_models_from_text(text, company)
        if models:
            parts.append("Models: " + ", ".join(models[:5]))
 
        if parts:
            return " | ".join(parts)
 
        return "Scheme mentioned but details not clearly available"
 
    except Exception:
        return None
 
 
def scrape_schemes(company):
    trusted_sites = (
        "site:cardekho.com OR site:carwale.com OR site:zigwheels.com OR "
        "site:autocarindia.com OR site:gaadiwaadi.com OR site:rushlane.com"
    )
 
    scheme_keywords = (
        '"exchange bonus" OR "exchange offer" OR '
        '"corporate scheme" OR "corporate discount" OR '
        '"loyalty bonus" OR "loyalty scheme" OR '
        '"festival offer" OR "festival scheme" OR '
        '"finance scheme" OR "low emi" OR '
        '"dealer scheme" OR "special scheme"'
    )
 
    query = f'{trusted_sites} "{company}" {scheme_keywords}'
    encoded_query = quote_plus(query)
 
    feed_url = (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    )
 
    cutoff = datetime.now() - timedelta(days=60)
    rows = []
 
    try:
        feed = feedparser.parse(feed_url)
    except Exception:
        return pd.DataFrame()
 
    for entry in feed.entries:
        try:
            published_dt = datetime(*entry.published_parsed[:6])
        except Exception:
            continue
 
        if published_dt < cutoff:
            continue
 
        scheme_info = extract_scheme_details(entry.link, company)
 
        # ✅ ONLY add real schemes
        if scheme_info:
            rows.append({
                "Section": "Schemes",
                "Scheme Details": f"{entry.title} | {scheme_info}",
                "Published Date": entry.get("published", ""),
                "Source": "Google News",
                "Link": entry.link
            })
 
    if not rows:
        rows.append({
            "Section": "Schemes",
            "Scheme Details": "No active schemes found in last 2 months",
            "Published Date": "",
            "Source": "Google News",
            "Link": ""
        })
 
    time.sleep(1)
    return pd.DataFrame(rows)
 
 