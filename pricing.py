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
            model_url = card.locator("a").first.get_attribute("href")

            if model_url and model_url.startswith("/"):
                model_url = "https://www.cardekho.com" + model_url

            price = "Not Available"

            if card.locator("div.price").count() > 0:
                price = card.locator("div.price").inner_text().strip()

            fuel_type = "Unknown"
            if card.locator("div.dotlist span").count() > 0:
                fuel_type = card.locator("div.dotlist span").first.inner_text().strip()

            body_type = self.get_body_type(model_url) if model_url else "Unknown"

            model_rows.append({
            "Section": "Pricing",
            "Model Name": name,
            "Body Type": body_type,
            "Fuel Type":fuel_type,
            "Price": price
            })


        return {
            "company_summary": company_summary,
            "models": model_rows
        }

    def close(self):
        if hasattr(self, "model_page"):
            self.model_page.close()
        self.browser.close()
        self.playwright.stop()

    def normalize_model_url(model_url):
        # carmodels → seo
        if "/carmodels/" in model_url:
            parts = model_url.split("/")
            brand = parts[-2].lower()
            model = parts[-1].lower().replace("_", "-")
            return f"https://www.cardekho.com/{brand}/{model}"
        return model_url.rstrip("/")


    def get_body_type(self, model_url):
        page = self.browser.new_page()
        page.set_default_timeout(30000)
        model_url = self.normalize_model_url(model_url)
        possible_urls = [
            model_url + "/specs",
            model_url.replace(".htm", "") + "-specifications.htm"
        ]
        for url in possible_urls:
            try:
                print(f"[INFO] Trying URL: {url}")
                page.goto(url, wait_until="domcontentloaded")

                page.wait_for_timeout(3000)
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(3000)

                # ✅ IMPORTANT FIX
                page.wait_for_selector("table.keyfeature", timeout=15000)

                rows = page.locator("table.keyfeature tr")
                print(f"[DEBUG] Rows found: {rows.count()}")

                for i in range(rows.count()):
                    tds = rows.nth(i).locator("td")
                    if tds.count() >= 2:
                        key = tds.nth(0).inner_text().strip().lower()
                        value = tds.nth(1).inner_text().strip()

                        print(f"[TRACE] {key} = {value}")

                        if key in ("body type", "body style"):
                            print(f"[SUCCESS] Body Type found: {value}")
                            page.close()
                            return value

            except Exception as e:
                print(f"[WARN] Failed on {url}: {e}")
                continue

        page.close()
        print("[WARN] Body Type not found for model")
        return "Unknown"

    