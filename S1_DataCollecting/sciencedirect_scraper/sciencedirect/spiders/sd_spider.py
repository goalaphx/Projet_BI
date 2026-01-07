import scrapy
from scrapy import signals
import time
import re
import pymongo
import os
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
        self.driver = None

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(SdSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def start_requests(self):
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        self.driver = uc.Chrome(options=options)

        yield scrapy.Request(
            url='data:,', 
            callback=self.parse_selenium, 
            dont_filter=True
        )

    def parse_selenium(self, response):
        if not self.driver: return

        url = f'https://www.sciencedirect.com/search?qs={self.keywords}'
        self.driver.get(url)
        
        print("\n--- BROWSER OPENED: Wait for Cloudflare Check ---")
        time.sleep(10) 
        
        try:
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
        except: pass

        page_count = 1

        while page_count <= self.max_pages:
            print(f"\n--- PROCESSING PAGE {page_count} ---")
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(4) 
            
            containers = self.driver.find_elements(By.CSS_SELECTOR, "div.result-item-content")
            print(f"DEBUG: Found {len(containers)} articles on Page {page_count}.")
            
            if not containers:
                self.driver.save_screenshot(f"debug_sd_page_{page_count}.png")
                break

            for container in containers:
                item = SciencedirectItem()
                try:
                    try:
                        title_el = container.find_element(By.CSS_SELECTOR, "a.result-list-title-link, h2")
                        item['title'] = title_el.text.strip()
                    except: 
                        item['title'] = "Unknown Title"

                    try:
                        author_el = container.find_element(By.CSS_SELECTOR, "ol.authors-list, div.Authors")
                        item['authors'] = author_el.text.strip()
                    except: 
                        item['authors'] = "Unknown"

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

    def spider_closed(self, spider):
        print("\n--- SPIDER CLOSING... ---")
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except OSError:
                pass
            except Exception:
                pass
            finally:
                self.driver = None
        
        print("--- CLEANING DB ---")
        try:
            client = pymongo.MongoClient("mongodb://localhost:27017/")
            db = client["aci"]
            collection = db["articles"]
            
            pipeline = [{"$group": {"_id": "$title", "ids": {"$push": "$_id"}, "count": {"$sum": 1}}}, {"$match": {"count": {"$gt": 1}}}]
            duplicates = list(collection.aggregate(pipeline))
            for doc in duplicates:
                collection.delete_many({"_id": {"$in": doc['ids'][1:]}})
            
            collection.create_index([("title", pymongo.ASCENDING)], unique=True)
            
            count = collection.count_documents({"source": "ScienceDirect"})
            print(f"Cleanup done. Total ScienceDirect Articles: {count}")
        except Exception as e: print(e)