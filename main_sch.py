from config import COMPANIES
from schemes import scrape_current_month_schemes
from datetime import datetime
import pandas as pd
from pathlib import Path

# ==============================
# OUTPUT FILE SETUP
# ==============================
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_FILE = Path(f"output/schemes_data_{timestamp}.xlsx")
OUTPUT_FILE.parent.mkdir(exist_ok=True)

print("Starting Scheme Scraping Pipeline...")

# Scrape all companies at once
all_schemes_df = scrape_current_month_schemes()

sheets_written = 0

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl", mode="w") as writer:
    for company in COMPANIES:
        print(f"Writing sheet for {company}...")

        company_df = all_schemes_df[all_schemes_df["Company"] == company]

        if company_df.empty:
            # Safety fallback
            company_df = pd.DataFrame([{
                "Company": company,
                "Month": datetime.now().strftime("%B"),
                "Offer Details": "No active schemes found",
                "Link": "",
                "Source": "AutoPunditz"
            }])

        sheet_name = company[:31]  # Excel sheet name limit
        company_df.to_excel(writer, sheet_name=sheet_name, index=False)
        sheets_written += 1

# ==============================
# FINAL SAFETY CHECK
# ==============================
if sheets_written == 0:
    raise RuntimeError("❌ No sheets were written. Excel file not created.")

print(f"\n✅ Schemes data successfully saved to: {OUTPUT_FILE}")
