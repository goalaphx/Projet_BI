import subprocess
import os
import sys
import pymongo
import time
import json

# --- CONFIGURATION ---
KEYWORD = "Blockchain"
PAGE_LIMITS = {
    "iee": 4,  # IEEE Xplore
    "sd":  4,  # ScienceDirect
    "acm": 4   # ACM Digital Library
}

PROJECTS = [
    ("ieee_scraper", "iee"),
    ("sciencedirect_scraper", "sd"),
    ("acm_scraper", "acm")
]

def run_spider(folder, spider_name):
    pages = PAGE_LIMITS.get(spider_name, 1)
    
    print(f"\n" + "="*60)
    print(f"   STARTING SPIDER: {spider_name.upper()}")
    print(f"   Target: {pages} pages | Keyword: '{KEYWORD}'")
    print("="*60)
    
    cmd = [
        "scrapy", "crawl", spider_name,
        "-a", f"keywords={KEYWORD}",
        "-a", f"pages={pages}"
    ]
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.join(script_dir, folder)
    
    if not os.path.isdir(project_path):
            print(f"\n[ERROR] Path is not a valid directory: {project_path}")
            return

    try:
        # We allow the process to run. If it returns a non-zero exit code (error),
        # we catch it so the script doesn't stop completely.
        subprocess.run(cmd, cwd=project_path, shell=True, check=True)
        print(f"\n[SUCCESS] Spider '{spider_name}' completed.")
        
    except subprocess.CalledProcessError:
        print(f"\n[WARNING] Spider '{spider_name}' encountered an error or was forced closed.")
        print("Continuing to next spider...")
    except KeyboardInterrupt:
        print("\n[STOP] User interrupted the process.")
        sys.exit()
    except Exception as e:
        print(f"\n[CRITICAL] Unexpected error: {e}")

def export_final_json():
    print(f"\n" + "="*60)
    print(f"   EXPORTING FINAL DATABASE")
    print("="*60)
    
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["aci"]
        collection = db["articles"]
        
        cursor = collection.find({}, {"_id": 0})
        articles = list(cursor)
        
        filename = "final_data.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=4, ensure_ascii=False)
            
        print(f"✅ SUCCESS: Total {len(articles)} articles exported to '{filename}'")
        
    except Exception as e:
        print(f"Error exporting JSON: {e}")

if __name__ == "__main__":
    print("--- AUTOMATED DATA COLLECTION SUITE ---")
    start_time = time.time()
    
    # 1. Run Spiders Sequentially
    for folder, spider in PROJECTS:
        run_spider(folder, spider)
        print("Cooling down for 5 seconds to free up ports...")
        time.sleep(5)

    # 2. Final Export
    export_final_json()
    
    elapsed = time.time() - start_time
    print(f"\nTotal Execution Time: {elapsed // 60:.0f}m {elapsed % 60:.0f}s")