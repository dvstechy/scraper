# main.py

from config import COMPANIES
from market_position import scrape_market_position
from pricing import PricingScraper
from schemes import scrape_schemes
from discounts import scrape_discounts


import pandas as pd
from pathlib import Path
def parse_pricing_text(company, pricing_text):
    rows = []

    # Total models
    if "total of" in pricing_text and "car models" in pricing_text:
        total_models = pricing_text.split("total of")[1].split("car models")[0].strip()
    else:
        total_models = "Not found"

    # Types of cars
    if "including" in pricing_text:
        types = pricing_text.split("including")[1].split(".")[0].strip()
    else:
        types = "Not found"

    # Extract model-price pairs
    import re
    model_price_matches = re.findall(
        r'([A-Za-z ]+)\s*\(₹([0-9\.\- ]+Lakh)\)',
        pricing_text
    )

    if not model_price_matches:
        rows.append({
            "Section": "Pricing",
            "Total Models": total_models,
            "Types of Cars": types,
            "Model Name": "All models",
            "Price": pricing_text
        })
    else:
        for model, price in model_price_matches:
            rows.append({
                "Section": "Pricing",
                "Total Models": total_models,
                "Types of Cars": types,
                "Model Name": model.strip(),
                "Price": f"₹{price}"
            })

    return pd.DataFrame(rows)


OUTPUT_FILE = Path("output/auto_market_data.xlsx")
OUTPUT_FILE.parent.mkdir(exist_ok=True)

print("Fetching Market Position once...")
market_df = scrape_market_position(COMPANIES)

# ✅ START HEADLESS PRICING SCRAPER ONCE
pricing_scraper = PricingScraper()


with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl", mode="w") as writer:
    pd.DataFrame([{"Info": "Scraping started"}]).to_excel(
        writer, sheet_name="INFO", index=False
    )

    for company in COMPANIES:
        print(f"Scraping {company}...")
        start_row = 0
        sheet = company[:31]
        written = False

        # -----------------------------
        # Market Position + Pricing
        # -----------------------------
        mp_df = market_df[market_df["Company"] == company]

        if not mp_df.empty:
            combined = mp_df.reset_index(drop=True)

            car_dekho_price = pricing_scraper.get_company_pricing(company)
            #combined["Pricing (CarDekho)"] = car_dekho_price
            pricing_text = car_dekho_price

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
            schemes_df = schemes_df.copy()
            schemes_df.insert(0, "Section", "Schemes")

            schemes_df.to_excel(
                writer,
                sheet_name=sheet,
                startrow=start_row,
                index=False
            )

        # -----------------------------
        # Pricing Parsed Table
        # -----------------------------
        pricing_table_df = parse_pricing_text(company, pricing_text)

        pricing_table_df.to_excel(
        writer,
        sheet_name=sheet,
        startrow=start_row + len(schemes_df) + 3,
        index=False
        )

        start_row = start_row + len(schemes_df) + len(pricing_table_df) + 6

        written = True
        if not written:
            pd.DataFrame([{
                "Info": f"No data available for {company}"
            }]).to_excel(
                writer, sheet_name=sheet, index=False
            )

# ✅ CLOSE BROWSER ONCE AT END
pricing_scraper.close()

print("✅ auto_market_data.xlsx generated successfully")
