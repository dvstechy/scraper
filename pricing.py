# pricing.py
# Headless pricing scraper using CarDekho only

from playwright.sync_api import sync_playwright

class PricingScraper:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True   # ✅ NO BROWSER UI
        )
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        )
        self.page = self.context.new_page()

    def get_company_pricing(self, company):
        cardekho_price = "Not Available"

        try:
            brand = company.split()[0]

            self.page.goto(
                f"https://www.cardekho.com/cars/{brand}",
                timeout=60000
            )

            # wait for JS content
            self.page.wait_for_timeout(7000)

            # trigger lazy load
            self.page.mouse.wheel(0, 3000)
            self.page.wait_for_timeout(3000)

            prices = self.page.locator("text=₹").all_inner_texts()
            prices = list(dict.fromkeys(prices))  # remove duplicates

            if prices:
                cardekho_price = " | ".join(prices[:3])

        except Exception:
            cardekho_price = "Fetch Failed"

        return cardekho_price

    def close(self):
        self.browser.close()
        self.playwright.stop()
