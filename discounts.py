# discounts.py
# Company-specific discount scraping using Google News RSS
# Fetches ONLY last 2 months of discount news

import feedparser
import pandas as pd
import time
from datetime import datetime, timedelta
from urllib.parse import quote_plus


def scrape_discounts(company):
    """
    Fetch company-specific car discount / offer news
    from the last 2 months using Google News RSS.
    """

    # Better, more specific query
    query = f"{company} car discount OR offer OR benefits India"
    encoded_query = quote_plus(query)

    feed_url = (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    )

    rows = []

    # Cutoff date → last 2 months
    cutoff_date = datetime.now() - timedelta(days=60)

    try:
        feed = feedparser.parse(feed_url)
    except Exception:
        return pd.DataFrame()

    for entry in feed.entries:
        published_dt = None

        # Parse published date safely
        try:
            published_dt = datetime(*entry.published_parsed[:6])
        except Exception:
            continue

        # Keep only last 2 months data
        if published_dt >= cutoff_date:
            rows.append({
                "Section": "Discounts",
                "Discount Info": entry.title,
                "Published Date": published_dt.strftime("%d-%b-%Y"),
                "Source": "Google News",
                "Link": entry.link
            })

    # If no recent discounts found
    if not rows:
        rows.append({
            "Section": "Discounts",
            "Discount Info": "No discount news found in last 2 months",
            "Published Date": "",
            "Source": "Google News",
            "Link": ""
        })

    # Polite delay (avoid RSS throttling)
    time.sleep(1)

    return pd.DataFrame(rows)
