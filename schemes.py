import feedparser
import pandas as pd
from urllib.parse import quote_plus

def scrape_schemes(company):
    query = f"{company} site:autopunditz.com offer scheme"
    encoded_query = quote_plus(query)

    feed_url = f"https://news.google.com/rss/search?q={encoded_query}"

    feed = feedparser.parse(feed_url)

    rows = []

    for entry in feed.entries[:5]:
        rows.append({
            "Scheme Details": entry.title,
            "Source": "Google News (AutoPunditz)",
            "Link": entry.link
        })

    return pd.DataFrame(rows)
