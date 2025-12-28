# main.py

from config import COMPANIES
from market_position import scrape_market_position
from pricing import PricingScraper
from schemes import scrape_schemes
from discounts import scrape_discounts

import pandas as pd
from pathlib import Path

OUTPUT_FILE = Path("output/auto_market_data.xlsx")
OUTPUT_FILE.parent.mkdir(exist_ok=True)

print("Fetching Market Position once...")
market_df = scrape_market_position(COMPANIES)

# ✅ START HEADLESS PRICING SCRAPER ONCE
pricing_scraper = PricingScraper()


with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl", mode="w") as writer:

    for company in COMPANIES:
        print(f"Scraping {company}...")
        start_row = 0
        pricing_data = pricing_scraper.get_company_pricing(company)
        sheet = company[:31]
        written = False

        # -----------------------------
        # Market Position + Pricing
        # -----------------------------
        mp_df = market_df[market_df["Company"] == company]

        if not mp_df.empty:
            combined = mp_df.reset_index(drop=True)

            combined.insert(0, "Section", "Market Position")

            combined.to_excel(
                writer,
                sheet_name=sheet,
                startrow=start_row,
                index=False
            )

            start_row += len(combined) + 3
            written = True

        # -----------------------------
        # Discounts
        # -----------------------------
        discounts_df = scrape_discounts(company)
        if not discounts_df.empty:
            

            discounts_df.to_excel(
                writer,
                sheet_name=sheet,
                startrow=start_row,
                index=False
            )

            start_row += len(discounts_df) + 3
            written = True

        # -----------------------------
        # Schemes
        # -----------------------------
        schemes_df = scrape_schemes(company)
        if not schemes_df.empty:
            schemes_df.insert(0, "Section", "Schemes")

            schemes_df.to_excel(
                writer,
                sheet_name=sheet,
                startrow=start_row,
                index=False
            )
            start_row += len(schemes_df) + 3

        # -----------------------------
        # Pricing (Structured)
        # -----------------------------
        if pricing_data:
        # Company-level summary
            summary_df = pd.DataFrame([pricing_data["company_summary"]])
            summary_df.to_excel(
                writer,
                sheet_name=sheet,
                startrow=start_row,
                index=False
            )

            start_row += len(summary_df) + 2

            # Model-level pricing
            models_df = pd.DataFrame(pricing_data["models"])

            models_df.to_excel(
                writer,
                sheet_name=sheet,
                startrow=start_row,
                index=False
            )

            start_row += len(models_df) + 4


# ✅ CLOSE BROWSER ONCE AT END
pricing_scraper.close()

print("✅ auto_market_data.xlsx generated successfully")
