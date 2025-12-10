import scrapy
import time
import re
import pymongo
# 1. NEW IMPORT for bypassing Cloudflare
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sciencedirect.items import SciencedirectItem

class SdSpider(scrapy.Spider):
    name = 'sd'
    
    def __init__(self, keywords="Blockchain", pages=3, *args, **kwargs):
        super(SdSpider, self).__init__(*args, **kwargs)
        self.keywords = keywords
        self.max_pages = int(pages)
        
        # 2. USE UNDETECTED CHROME OPTIONS
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        
        # 3. INITIALIZE UNDETECTED CHROME (Replaces standard webdriver)
        # This automatically downloads the correct driver version
        self.driver = uc.Chrome(options=options)

    def start_requests(self):
        # 4. FIX: Use "data:," to prevent Scrapy from sending a request that gets blocked
        yield scrapy.Request(
            url='data:,', 
            callback=self.parse_selenium, 
            dont_filter=True
        )

    def parse_selenium(self, response):
        url = f'https://www.sciencedirect.com/search?qs={self.keywords}'
        self.driver.get(url)
        
        print("\n--- BROWSER OPENED: Wait for Cloudflare Check ---")
        
        # 5. WAIT FOR HUMAN INTERVENTION OR AUTO-BYPASS
        # undetected-chromedriver often bypasses the check automatically.
        # If it doesn't, this sleep gives you time to click the box manually.
        time.sleep(10) 
        
        # Handle Cookie Banner (if it appears after the check)
        try:
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
        except: pass

        page_count = 1

        while page_count <= self.max_pages:
            print(f"\n--- PROCESSING PAGE {page_count} ---")
            
            # Scroll to trigger loading
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(4) 
            
            # Selectors for ScienceDirect
            containers = self.driver.find_elements(By.CSS_SELECTOR, "div.result-item-content")
            print(f"DEBUG: Found {len(containers)} articles on Page {page_count}.")
            
            if not containers:
                print("No articles found. Taking screenshot.")
                self.driver.save_screenshot(f"debug_sd_page_{page_count}.png")
                # If we are blocked, break the loop
                break

            for container in containers:
                item = SciencedirectItem()
                try:
                    # Title
                    try:
                        title_el = container.find_element(By.CSS_SELECTOR, "a.result-list-title-link, h2")
                        item['title'] = title_el.text.strip()
                    except: 
                        item['title'] = "Unknown Title"

                    # Authors
                    try:
                        author_el = container.find_element(By.CSS_SELECTOR, "ol.authors-list, div.Authors")
                        item['authors'] = author_el.text.strip()
                    except: 
                        item['authors'] = "Unknown"

                    # Date
                    try:
                        full_text = container.text
                        year_match = re.search(r'\b(19|20)\d{2}\b', full_text)
                        item['date_pub'] = year_match.group(0) if year_match else "Unknown"
                    except:
                        item['date_pub'] = "Unknown"
                    
                    item['source'] = "ScienceDirect"
                    item['journal'] = "ScienceDirect Journal"
                    item['abstract_'] = "N/A"

                    if item['title'] != "Unknown Title":
                        yield item
                except Exception:
                    pass

            if page_count >= self.max_pages: break

            # Pagination Logic
            try:
                print("Looking for Next button...")
                next_btn = self.driver.find_element(By.CSS_SELECTOR, "li.pagination-link.next-link a, a[aria-label='Next page']")
                
                self.driver.execute_script("arguments[0].scrollIntoView();", next_btn)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", next_btn)
                
                print(f"Clicked Next. Loading Page {page_count + 1}...")
                time.sleep(5) 
                page_count += 1
            except Exception as e:
                print(f"Pagination stopped: {e}")
                break

    def closed(self, reason):
        print("\n--- SPIDER FINISHED. CLEANING DB ---")
        try:
            # undetected-chromedriver must be closed carefully
            self.driver.quit()
        except: pass
        
        try:
            client = pymongo.MongoClient("mongodb://localhost:27017/")
            db = client["aci"]
            collection = db["articles"]
            
            # Clean Duplicates
            pipeline = [{"$group": {"_id": "$title", "ids": {"$push": "$_id"}, "count": {"$sum": 1}}}, {"$match": {"count": {"$gt": 1}}}]
            duplicates = list(collection.aggregate(pipeline))
            for doc in duplicates:
                collection.delete_many({"_id": {"$in": doc['ids'][1:]}})
            
            # Indexing
            collection.create_index([("title", pymongo.ASCENDING)], unique=True)
            
            count = collection.count_documents({"source": "ScienceDirect"})
            print(f"Cleanup done. Total ScienceDirect Articles: {count}")
        except Exception as e: print(e)