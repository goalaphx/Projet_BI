import scrapy
import time
import re
import pymongo
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from acm.items import AcmItem 

class AcmSpider(scrapy.Spider):
    name = 'acm'
    
    def __init__(self, keywords="Blockchain", pages=3, *args, **kwargs):
        super(AcmSpider, self).__init__(*args, **kwargs)
        self.keywords = keywords
        self.max_pages = int(pages)
        
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        self.driver = uc.Chrome(options=options)

    def start_requests(self):
        # Use dummy URL to start spider without 403 error
        yield scrapy.Request(url='data:,', callback=self.parse_selenium, dont_filter=True)

    def parse_selenium(self, response):
        url = f'https://dl.acm.org/action/doSearch?AllField={self.keywords}'
        self.driver.get(url)
        
        print("\n" + "="*40)
        print("   BROWSER OPENED. LOADING...")
        print("="*40 + "\n")
        
        time.sleep(10) # Initial load wait

        # Cookie banner closer
        try:
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "cookie-policy-popup__close"))
            ).click()
        except: pass

        page_count = 1

        while page_count <= self.max_pages:
            print(f"\n--- PROCESSING PAGE {page_count} ---")
            
            # Scroll down to ensure lazy-loaded elements appear
            self.driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # --- FIX 1: UPDATED CONTAINER SELECTOR ---
            # ACM mixes 'li' and 'div'. We search for the class '.issue-item' regardless of tag.
            containers = self.driver.find_elements(By.CSS_SELECTOR, ".issue-item, .search-result__item")
            print(f"DEBUG: Found {len(containers)} articles.")

            if not containers:
                print("No articles found. Taking screenshot.")
                self.driver.save_screenshot(f"debug_acm_page_{page_count}.png")
                break
            
            for container in containers:
                item = AcmItem()
                try:
                    # --- FIX 2: ROBUST TITLE SELECTOR ---
                    # We look for the title class specifically, avoiding 'h5' dependency
                    try:
                        title_el = container.find_element(By.CSS_SELECTOR, ".issue-item__title a, .hlFld-Title a")
                        item['title'] = title_el.text.strip()
                    except: 
                        item['title'] = "Unknown Title"

                    # Authors
                    try:
                        author_el = container.find_element(By.CSS_SELECTOR, "ul.rlist--inline, .issue-item__detail .rlist--inline")
                        item['authors'] = author_el.text.strip()
                    except: 
                        item['authors'] = "Unknown"

                    # Year / Date
                    try:
                        full_text = container.text
                        # Regex to find a year (19xx or 20xx)
                        year_match = re.search(r'\b(19|20)\d{2}\b', full_text)
                        item['date_pub'] = year_match.group(0) if year_match else "Unknown Date"
                    except: 
                        item['date_pub'] = "Unknown Date"
                    
                    item['source'] = "ACM Digital Library"
                    item['journal'] = "ACM"
                    item['abstract_'] = "N/A"

                    # Only yield if we actually found a title
                    if item['title'] != "Unknown Title":
                        yield item
                    else:
                        print("Skipped item with no title") # Debug print

                except Exception as e:
                    print(f"Error extracting an item: {e}")

            if page_count >= self.max_pages:
                break

            # Pagination
            try:
                print("Looking for Next button...")
                next_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.pagination__btn--next"))
                )
                
                self.driver.execute_script("arguments[0].scrollIntoView();", next_btn)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", next_btn)
                
                print(f"Clicked Next. Loading Page {page_count + 1}...")
                time.sleep(5)
                page_count += 1
                
            except Exception as e:
                print(f"Pagination stopped: {str(e)}")
                break

    def closed(self, reason):
        print("\n--- SPIDER FINISHED. EXPORTING JSON ---")
        try:
            # Safely close driver
            try: self.driver.quit()
            except: pass
            
            client = pymongo.MongoClient("mongodb://localhost:27017/")
            db = client["aci"]
            collection = db["articles"]
            
            # Clean Duplicates
            pipeline = [{"$group": {"_id": "$title", "ids": {"$push": "$_id"}, "count": {"$sum": 1}}}, {"$match": {"count": {"$gt": 1}}}]
            duplicates = list(collection.aggregate(pipeline))
            for doc in duplicates:
                collection.delete_many({"_id": {"$in": doc['ids'][1:]}})
            
            # Index
            collection.create_index([("title", pymongo.ASCENDING)], unique=True)
            
            # Export
            cursor = collection.find({"source": "ACM Digital Library"}, {"_id": 0})
            articles = list(cursor)

            with open('acm_results.json', 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=4, ensure_ascii=False)
            
            print(f"Cleanup done. Exported {len(articles)} articles to 'acm_results.json'")
            
        except Exception as e: 
            print(f"DB Error: {e}")