import feedparser
import pandas as pd
import time
from urllib.parse import quote_plus
from datetime import datetime, timedelta

def scrape_schemes(company):
    """
    Fetch *only last 2 months* of company-specific car schemes using Google News RSS.
    """

    # Prepare query
    query = f"{company} car scheme OR offer OR benefits India"
    encoded_query = quote_plus(query)

    feed_url = (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    )

    # Calculate cutoff date (today - 2 months)
    cutoff = datetime.now() - timedelta(days=60)

    rows = []

    try:
        feed = feedparser.parse(feed_url)
    except Exception:
        return pd.DataFrame()

    for entry in feed.entries:
        published_str = entry.get("published", "")
        published_dt = None

        # Parse published date (if available)
        try:
            published_dt = datetime(*entry.published_parsed[:6])
        except Exception:
            pass

        # Only add if within last 2 months
        if published_dt and published_dt >= cutoff:
            rows.append({
                "Section": "Schemes",
                "Scheme Details": entry.title,
                "Published Date": published_str,
                "Source": "Google News",
                "Link": entry.link
            })

    # If no recent schemes found
    if not rows:
        rows.append({
            "Section": "Schemes",
            "Scheme Details": "No scheme news found in last 2 months",
            "Published Date": "",
            "Source": "Google News",
            "Link": ""
        })

    # Delay to avoid RSS throttling
    time.sleep(1)

    return pd.DataFrame(rows)
