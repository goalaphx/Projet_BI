import scrapy
import time
import re
import pymongo
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from iee.items import IeeItem

class IeeSpider(scrapy.Spider):
    name = 'iee'
    
    def __init__(self, keywords="Blockchain", pages=3, *args, **kwargs):
        super(IeeSpider, self).__init__(*args, **kwargs)
        self.keywords = keywords
        self.max_pages = int(pages)
        
        # 1. Stealth Settings
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        self.driver = uc.Chrome(options=options)

    def start_requests(self):
        yield scrapy.Request(url='data:,', callback=self.parse_selenium, dont_filter=True)

    def parse_selenium(self, response):
        url = f'https://ieeexplore.ieee.org/search/searchresult.jsp?newsearch=true&queryText={self.keywords}'
        self.driver.get(url)
        
        print("\n" + "="*40)
        print("   BROWSER OPENED. LOADING IEEE XPLORE...")
        print("="*40 + "\n")

        # Wait specifically for the results LIST to appear
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "List-results-items"))
            )
        except:
            print("Action Required: Please check browser for CAPTCHA.")
            time.sleep(10)

        # Close Cookie Banner
        try:
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "cc-btn-accept-all"))
            ).click()
        except: pass

        page_count = 1

        while page_count <= self.max_pages:
            print(f"\n--- PROCESSING PAGE {page_count} ---")
            
            # Scroll to trigger lazy loading
            self.driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # --- FIX 1: CORRECT CONTAINER SELECTOR ---
            # We select the individual items inside the main list wrapper
            containers = self.driver.find_elements(By.CSS_SELECTOR, "div.List-results-items .xpl-results-item, div.result-item")
            print(f"DEBUG: Found {len(containers)} articles.")

            if not containers:
                self.driver.save_screenshot(f"debug_ieee_page_{page_count}.png")
                break
            
            for container in containers:
                item = IeeItem()
                try:
                    # --- FIX 2: UPDATED TITLE SELECTOR (IEEE uses h3 or 'result-item-title') ---
                    try:
                        title_el = container.find_element(By.CSS_SELECTOR, "h3.text-md-md-lh a, h2 a, .result-item-title a")
                        item['title'] = title_el.text.strip()
                    except: 
                        item['title'] = "Unknown Title"

                    # --- FIX 3: UPDATED AUTHORS SELECTOR ---
                    try:
                        author_el = container.find_element(By.CSS_SELECTOR, "p.author, .xpl-authors-name-list")
                        item['authors'] = author_el.text.strip()
                    except: 
                        item['authors'] = "Unknown"

                    # Year extraction (Regex is safest)
                    try:
                        full_text = container.text
                        year_match = re.search(r'\b(19|20)\d{2}\b', full_text)
                        item['date_pub'] = year_match.group(0) if year_match else "Unknown Date"
                    except: 
                        item['date_pub'] = "Unknown Date"
                    
                    item['source'] = "IEEE Xplore"
                    item['journal'] = "IEEE"
                    item['abstract_'] = "N/A"

                    if item['title'] != "Unknown Title":
                        yield item
                except: pass

            if page_count >= self.max_pages:
                break

            # --- FIX 4: ROBUST PAGINATION ---
            try:
                print("Looking for Next button...")
                # IEEE 'Next' is usually an icon inside a list item with class 'next-btn'
                next_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "li.next-btn button, li.next-btn a"))
                )
                
                self.driver.execute_script("arguments[0].scrollIntoView();", next_btn)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", next_btn)
                
                print(f"Clicked Next. Loading Page {page_count + 1}...")
                
                # Wait for content to change
                time.sleep(5)
                page_count += 1
                
            except Exception as e:
                print(f"Pagination stopped: {str(e)}")
                break

    def closed(self, reason):
        print("\n--- SPIDER FINISHED. EXPORTING JSON ---")
        try:
            self.driver.quit()
        except: pass
        
        try:
            client = pymongo.MongoClient("mongodb://localhost:27017/")
            db = client["aci"]
            collection = db["articles"]
            
            # Deduplicate
            pipeline = [{"$group": {"_id": "$title", "ids": {"$push": "$_id"}, "count": {"$sum": 1}}}, {"$match": {"count": {"$gt": 1}}}]
            duplicates = list(collection.aggregate(pipeline))
            for doc in duplicates:
                collection.delete_many({"_id": {"$in": doc['ids'][1:]}})
            
            collection.create_index([("title", pymongo.ASCENDING)], unique=True)
            
            # Export
            cursor = collection.find({"source": "IEEE Xplore"}, {"_id": 0})
            articles = list(cursor)

            with open('ieee_results.json', 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=4, ensure_ascii=False)
            
            print(f"Cleanup done. Exported {len(articles)} articles to 'ieee_results.json'")
            
        except Exception as e: 
            print(f"DB/Export Error: {e}")