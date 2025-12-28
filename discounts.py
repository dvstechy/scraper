# discounts.py
# Company-specific discount scraping using Google News RSS
# Stable, safe, no Playwright

import feedparser
import pandas as pd
import time

def scrape_discounts(company):
    """
    Fetch company-specific car discount / offer news
    using Google News RSS.
    """

    # Company-specific search query
    query = f"{company} car discount offers India"

    feed_url = (
        "https://news.google.com/rss/search?"
        f"q={query.replace(' ', '+')}&hl=en-IN&gl=IN&ceid=IN:en"
    )

    rows = []

    try:
        feed = feedparser.parse(feed_url)
    except Exception:
        return pd.DataFrame()

    # Limit to top 5 results to keep Excel clean
    for entry in feed.entries[:5]:
        rows.append({
            "Section": "Discounts",
            "Discount Info": entry.title,
            "Source": "Google News",
            "Link": entry.link
        })

    # If no discounts found
    if not rows:
        rows.append({
            "Section": "Discounts",
            "Discount Info": "No recent discount news found",
            "Source": "Google News",
            "Link": ""
        })

    # Small delay to avoid Google rate limiting
    time.sleep(1)

    return pd.DataFrame(rows)
