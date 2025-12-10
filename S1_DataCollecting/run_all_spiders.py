import subprocess
import os
import sys
import pymongo
import time
import json

# --- CONFIGURATION ---
KEYWORD = "Blockchain"
PAGE_LIMITS = {
    "iee": 2,  # IEEE Xplore
    "sd":  2,  # ScienceDirect
    "acm": 2   # ACM Digital Library
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
    
    # Get the directory where this script file lives
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.join(script_dir, folder)
    
    try:
        if not os.path.isdir(project_path):
             print(f"\n[ERROR] Path is not a valid directory: {project_path}")
             return

        subprocess.run(cmd, cwd=project_path, shell=True, check=True)
        print(f"\n[SUCCESS] Spider '{spider_name}' completed successfully.")
        
    except subprocess.CalledProcessError:
        print(f"\n[ERROR] Spider '{spider_name}' crashed or was stopped.")
    except Exception as e:
        print(f"\n[CRITICAL] Unexpected error: {e}")

def export_json():
    print(f"\n" + "="*60)
    print(f"   EXPORTING DATABASE TO JSON")
    print("="*60)
    
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["aci"]
        collection = db["articles"]
        
        # Fetch all articles, exclude the internal MongoDB ID
        cursor = collection.find({}, {"_id": 0})
        articles = list(cursor)
        
        if not articles:
            print("⚠️  No data to export.")
            return

        filename = "final_data.json"
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=4, ensure_ascii=False)
            
        print(f"✅ SUCCESS: Exported {len(articles)} articles to '{filename}'")
        
    except Exception as e:
        print(f"Error exporting JSON: {e}")

def verify_database():
    # Reuse your existing verification logic here if you want visuals
    # (Optional, but good for seeing the breakdown in the terminal)
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["aci"]
        collection = db["articles"]
        total = collection.count_documents({})
        print(f"\n[INFO] Total Articles in Database: {total}")
    except: pass

if __name__ == "__main__":
    print("--- AUTOMATED DATA COLLECTION SUITE ---")
    print(f"Keyword: {KEYWORD}\n")
    
    start_time = time.time()
    
    # 1. Run Spiders
    for folder, spider in PROJECTS:
        run_spider(folder, spider)
        print("Cooling down for 5 seconds...")
        time.sleep(5)

    # 2. Verify & Export
    verify_database()
    export_json()  # <--- NEW STEP
    
    elapsed = time.time() - start_time
    print(f"\nTotal Execution Time: {elapsed // 60:.0f}m {elapsed % 60:.0f}s")