# main.py

from config import COMPANIES
from market_position import scrape_market_position
from pricing import PricingScraper
from schemes import scrape_schemes
from discounts import scrape_discounts
from datetime import datetime
import pandas as pd
from pathlib import Path

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

OUTPUT_FILE = Path(f"output/auto_market_data_{timestamp}.xlsx")

OUTPUT_FILE.parent.mkdir(exist_ok=True)

print("Fetching Market Position once...")
market_df = scrape_market_position(COMPANIES)

# ✅ START HEADLESS PRICING SCRAPER ONCE
pricing_scraper = PricingScraper()


with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl", mode="w") as writer:
    all_models = []

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

            for model in pricing_data["models"]:
                all_models.append({
                    "Company": company,
                    "Segment": model.get("Body Type", "Unknown"),
                    "Model Name": model.get("Model Name"),
                    "Price": model.get("Price")
                })
    # -----------------------------
    # Segment-wise Comparison Sheet
    # -----------------------------
    if all_models:
        df_all = pd.DataFrame(all_models)
        segments = sorted(df_all["Segment"].dropna().unique())  # sort segments alphabetically
        start_row = 0

        for segment in segments:
            title_df = pd.DataFrame(
                [[f"Segment: {segment}", "", ""]],
                columns=["Company", "Model Name", "Price"]
            )
            title_df.to_excel(
                writer,
                sheet_name="Segment Comparison",
                startrow=start_row,
                index=False,
                header=False
            )
            start_row += 1

            # Segment data
            segment_df = (
                df_all[df_all["Segment"] == segment]
                [["Company", "Model Name", "Price"]]
                .reset_index(drop=True)
            )

            segment_df.to_excel(
                writer,
                sheet_name="Segment Comparison",
                startrow=start_row,
                index=False,
                header=True
            )

            # Leave space after each segment
            start_row += len(segment_df) + 3

# ✅ CLOSE BROWSER ONCE AT END
pricing_scraper.close()

print(f"✅ {OUTPUT_FILE.name} generated successfully")




