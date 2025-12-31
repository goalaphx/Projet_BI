import json
import os
from pymongo import MongoClient
from bson.json_util import dumps

# --- CONFIGURATION ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "aci"
COLLECTION_NAME = "fact_publications"
OUTPUT_FILE = "final_data_warehouse.json"

def export_clean_json():
    print(f"--- EXPORTING DATA WAREHOUSE ---")
    
    try:
        # Connect to the Cleaned Data (Not the raw scraping!)
        client = MongoClient(MONGO_URI)
        collection = client[DB_NAME][COLLECTION_NAME]
        
        # Exclude the MongoDB '_id' and 'etl_timestamp' for a cleaner JSON
        cursor = collection.find({}, {"_id": 0, "etl_timestamp": 0})
        articles = list(cursor)
        
        count = len(articles)
        if count == 0:
            print("⚠️ Warning: Database is empty. Did you run the Spark script?")
            return

        # Write to file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=4, ensure_ascii=False)
            
        print(f"✅ SUCCESS: Exported {count} cleaned articles to '{os.path.abspath(OUTPUT_FILE)}'")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    export_clean_json()