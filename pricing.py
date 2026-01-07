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
 
            # fuel_type = "Unknown"
            # if card.locator("div.dotlist span").count() > 0:
            #     fuel_type = card.locator("div.dotlist span").first.inner_text().strip()
 
            specs, features = self.get_specs_and_features(model_url)
 
            row = {
                "Section": "Pricing",
                "Model Name": name,
                "Price": price,
                "Key Features": features
            }
 
            # Add all specs as columns
            for k, v in specs.items():
                row[k] = v
 
            model_rows.append(row)
        return {
            "company_summary": company_summary,
            "models": model_rows
        }
 
 
    def get_specs_and_features(self, model_url):
        page = self.browser.new_page()
        page.set_default_timeout(30000)
 
        model_url = self.normalize_model_url(model_url)
 
        possible_urls = [
        model_url + "/specs",
        model_url.replace(".htm", "") + "-specifications.htm"
        ]
 
        specs = {}
        features = []
 
        for url in possible_urls:
            try:
                print(f"[INFO] Trying URL: {url}")
                page.goto(url, wait_until="domcontentloaded")
 
                page.wait_for_timeout(3000)
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(3000)
 
                # =========================
                # KEY SPECIFICATIONS
                # =========================
                page.wait_for_selector("div[id^='Keyspecification']", timeout=15000)
                spec_rows = page.locator("div[id^='Keyspecification'] table.keyfeature tr")
                print(f"[DEBUG] Spec rows found: {spec_rows.count()}")
 
                for i in range(spec_rows.count()):
                    tds = spec_rows.nth(i).locator("td")
                    if tds.count() >= 2:
                        key = tds.nth(0).inner_text().strip()
                        value = tds.nth(1).inner_text().strip()
                        specs[key] = value
                        print(f"[SPEC] {key} = {value}")
 
                # =========================
                # KEY FEATURES
                # =========================
                page.wait_for_selector("div[id^='Keyfeatures']", timeout=15000)
                feature_rows = page.locator("div[id^='Keyfeatures'] table.keyfeature tr")
                print(f"[DEBUG] Feature rows found: {feature_rows.count()}")
 
                for i in range(feature_rows.count()):
                    row = feature_rows.nth(i)
                    tds = row.locator("td")
 
                    if tds.count() < 2:
                        continue
 
                    feature_name = tds.nth(0).inner_text().strip()
 
                    # Check for tick icon inside second column
                    has_check_icon = tds.nth(1).locator("i").count() > 0
 
                    if has_check_icon:
                        features.append(feature_name)
                        print(f"[FEATURE] {feature_name} = YES")
 
                break  # ✅ success, stop trying other URLs
 
            except Exception as e:
                print(f"[WARN] Failed on {url}: {e}")
                continue
 
        page.close()
        return specs, ", ".join(features)
 
    # def get_key_features(self, model_url):
    #     page = self.browser.new_page()
    #     page.set_default_timeout(30000)
    #     model_url = self.normalize_model_url(model_url)
 
    #     possible_urls = [
    #         model_url + "/specs",
    #         model_url.replace(".htm", "") + "-specifications.htm"
    #     ]
 
    #     features = []
 
    #     for url in possible_urls:
    #         try:
    #             print(f"[INFO] Trying Features URL: {url}")
    #             page.goto(url, wait_until="domcontentloaded")
 
    #             page.wait_for_timeout(3000)
    #             page.mouse.wheel(0, 3000)
    #             page.wait_for_timeout(3000)
 
    #             page.wait_for_selector("div[id^='Keyfeatures']", timeout=15000)
 
    #             rows = page.locator("div[id^='Keyfeatures'] table.keyfeature tr")
 
    #             print(f"[DEBUG] Feature rows found: {rows.count()}")
 
           
    #             for i in range(rows.count()):
    #                 tds = rows.nth(i).locator("td")
    #                 if tds.count() >= 2:
    #                     feature_name = tds.nth(0).inner_text().strip()
    #                     value_text = tds.nth(1).inner_text().strip().lower()
 
    #                     # Only include if Yes
    #                     if "yes" in value_text:
    #                         features.append(feature_name)
 
    #             break
 
    #         except Exception as e:
    #             print(f"[WARN] Features not found on {url}: {e}")
    #             continue
 
    #     page.close()
    #     return ", ".join(features)
 
    def close(self):
        if hasattr(self, "model_page"):
            self.model_page.close()
        self.browser.close()
        self.playwright.stop()
 
    def normalize_model_url(self,model_url):
        # carmodels → seo
        if "/carmodels/" in model_url:
            parts = model_url.split("/")
            brand = parts[-2].lower()
            model = parts[-1].lower().replace("_", "-")
            return f"https://www.cardekho.com/{brand}/{model}"
        return model_url.rstrip("/")
 
 
    # def get_key_specifications(self, model_url):
    #     page = self.browser.new_page()
    #     page.set_default_timeout(30000)
    #     model_url = self.normalize_model_url(model_url)
    #     possible_urls = [
    #         model_url + "/specs",
    #         model_url.replace(".htm", "") + "-specifications.htm"
    #     ]
    #     specs={}
    #     for url in possible_urls:
    #         try:
    #             print(f"[INFO] Trying Specs URL: {url}")
    #             page.goto(url, wait_until="domcontentloaded")
 
    #             page.wait_for_timeout(3000)
    #             page.mouse.wheel(0, 2000)
    #             page.wait_for_timeout(3000)
 
    #             # ✅ IMPORTANT FIX
    #             page.wait_for_selector("div[id^='Keyspecification']", timeout=15000)
 
    #             rows = page.locator("div[id^='Keyspecification'] table.keyfeature tr")
    #             print(f"[DEBUG] Spec rows found: {rows.count()}")
 
    #             for i in range(rows.count()):
    #                 tds = rows.nth(i).locator("td")
    #                 if tds.count() >= 2:
    #                     key = tds.nth(0).inner_text().strip()
    #                     value = tds.nth(1).inner_text().strip()
 
    #                     specs[key] = value
    #                     print(f"[SPEC] {key} = {value}")
 
    #             break
 
    #                     # if key in ("body type", "body style"):
    #                     #     print(f"[SUCCESS] Body Type found: {value}")
    #                     #     page.close()
    #                     #     return value
 
    #         except Exception as e:
    #             print(f"[WARN] Specs not found on {url}: {e}")
    #             continue
 
    #     page.close()
    #     return specs
