import scrapy
from scrapy import signals
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
        self.driver = None

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(IeeSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def start_requests(self):
        # Initialize Driver
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        # options.add_argument("--headless") # NEVER use headless for IEEE, they block it
        
        self.driver = uc.Chrome(options=options)
        
        # Open a blank page first to set up the driver safely
        yield scrapy.Request(url='data:,', callback=self.parse_selenium, dont_filter=True)

    def parse_selenium(self, response):
        if not self.driver: return

        # 1. Navigate to Search
        url = f'https://ieeexplore.ieee.org/search/searchresult.jsp?newsearch=true&queryText={self.keywords}'
        self.driver.get(url)
        
        print("\n" + "="*50)
        print("   IEEE BROWSER OPENED")
        print("   Waiting for you to solve Captcha (if any)...")
        print("="*50 + "\n")

        # 2. HUMAN INTERVENTION LOOP
        # This prevents the browser from closing if a Captcha appears.
        # It waits up to 60 seconds for the result list to appear.
        try:
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.CLASS_NAME, "List-results-items"))
            )
            print(">>> Results list found! Starting scrape...")
        except:
            print("!!! TIMEOUT: Could not find results. Did you solve the Captcha?")
            self.driver.save_screenshot("ieee_load_fail.png")
            return # Stop here if it failed to load

        # 3. Close Cookie Banner (Optional)
        try:
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "cc-btn-accept-all"))
            ).click()
        except: pass

        # 4. Start Pagination Loop
        page_count = 1
        while page_count <= self.max_pages:
            print(f"\n--- PROCESSING PAGE {page_count} ---")
            
            # Scroll to load images/lazy elements
            self.driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Find articles
            containers = self.driver.find_elements(By.CSS_SELECTOR, "div.List-results-items .xpl-results-item, div.result-item")
            print(f"DEBUG: Found {len(containers)} articles.")

            if not containers:
                print("No articles found on this page. Stopping.")
                break
            
            for container in containers:
                item = IeeItem()
                try:
                    # Extract Title
                    try:
                        title_el = container.find_element(By.CSS_SELECTOR, "h3.text-md-md-lh a, h2 a, .result-item-title a")
                        item['title'] = title_el.text.strip()
                    except: 
                        item['title'] = "Unknown Title"

                    # Extract Authors
                    try:
                        author_el = container.find_element(By.CSS_SELECTOR, "p.author, .xpl-authors-name-list")
                        item['authors'] = author_el.text.strip()
                    except: 
                        item['authors'] = "Unknown"

                    # Extract Date
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

            # 5. Handle Next Page
            try:
                print("Looking for Next button...")
                next_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "li.next-btn button, li.next-btn a"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView();", next_btn)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", next_btn)
                print(f"Clicked Next. Loading Page {page_count + 1}...")
                
                # Wait for the results to refresh
                time.sleep(5)
                page_count += 1
            except Exception as e:
                print(f"Pagination stopped: {str(e)}")
                break

    def spider_closed(self, spider):
        """
        Graceful Shutdown to prevent [WinError 6]
        """
        print("\n--- IEEE SPIDER FINISHED. CLOSING... ---")
        if self.driver:
            try:
                # We defer the quit slightly to ensure signals are clear
                self.driver.quit()
            except OSError:
                pass # Suppress the 'handle is invalid' error
            except Exception:
                pass
            finally:
                self.driver = None # Prevent __del__ from firing

        # DB Cleanup and Export logic
        self.export_data()

    def export_data(self):
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
            
            # Export specific results
            cursor = collection.find({"source": "IEEE Xplore"}, {"_id": 0})
            articles = list(cursor)

            with open('ieee_results.json', 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=4, ensure_ascii=False)
            
            print(f"Exported {len(articles)} IEEE articles.")
            
        except Exception as e: 
            print(f"DB Error: {e}")