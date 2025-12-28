from playwright.sync_api import sync_playwright
import re

COMPANY_URLS = {
    "Maruti Suzuki": "maruti-suzuki-cars",
    "Hyundai": "cars/Hyundai",
    "Mahindra": "cars/Mahindra",
    "Kia": "cars/Kia",
    "MG Motor": "cars/MG",
    "Toyota": "toyota-cars",
    "Honda": "cars/Honda",
    "Renault": "cars/Renault",
    "Nissan": "cars/Nissan",
    "Skoda": "cars/Skoda",
    "Volkswagen": "cars/Volkswagen",
    "BYD": "cars/BYD",
    "Volvo": "cars/Volvo",
    "Tata Motors": "cars/Tata"
}

class PricingScraper:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()

    def get_company_pricing(self, company):
        slug = COMPANY_URLS.get(company)
        if not slug:
            return None

        self.page.goto(f"https://www.cardekho.com/{slug}", timeout=60000)
        self.page.wait_for_timeout(5000)

        # -------------------------
        # SCRAPE SUMMARY TEXT
        # -------------------------
        summary_text = self.page.locator(
            "div.carSummary p"
        ).first.inner_text()

        total_models = "Not found"
        types_of_cars = "Not found"

        tm = re.search(r"total of (\d+) car models", summary_text)
        if tm:
            total_models = int(tm.group(1))

        tc = re.search(r"including (.+)", summary_text)
        if tc:
            types_of_cars = tc.group(1).strip(".")

        company_summary = {
            "Section": "Pricing Summary",
            "Company": company,
            "Total Models": total_models,
            "Types of Cars": types_of_cars
        }

        # -------------------------
        # SCRAPE MODEL PRICES
        # -------------------------
        for _ in range(5):
            self.page.mouse.wheel(0, 3000)
            self.page.wait_for_timeout(1500)

        cards = self.page.locator("h3").locator("xpath=ancestor::div[contains(@class,'listView')]")

        model_rows = []

        for i in range(cards.count()):
            card = cards.nth(i)

            name = card.locator("h3").inner_text().strip()
            price = "Not Available"

            if card.locator("div.price").count() > 0:
                price = card.locator("div.price").inner_text().strip()

            model_rows.append({
                "Section": "Pricing",
                "Company": company,
                "Model Name": name,
                "Price": price
            })

        return {
            "company_summary": company_summary,
            "models": model_rows
        }

    def close(self):
        self.browser.close()
        self.playwright.stop()
