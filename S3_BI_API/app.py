from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import random
import hashlib

app = Flask(__name__)
CORS(app)

# Connect to MongoDB
client = MongoClient("mongodb://mongodb:27017/")
db = client["aci"]
collection = db["articles"]

# --- HELPER: SIMULATION DATA ---
# Since we lack real metadata, we simulate it for the BI requirements


# --- HELPER: SIMULATION DATA ---
def enrich_article(article):
    """Adds simulated BI fields: Quartile, Citations, Keywords"""
    quartiles = ["Q1", "Q2", "Q3", "Q4"]
    # Expanded keyword list for better Word Cloud
    keywords = ["Blockchain", "Security", "IoT", "Smart Contracts", "Privacy", 
                "Consensus", "AI", "Cloud", "Big Data", "Crypto", "Hyperledger", 
                "Ethereum", "Supply Chain", "Healthcare", "FinTech"]
    
    title = article.get("title", "")
    
    # FIX: Use a hash of the title string, not length.
    # This creates a unique integer seed for every unique title.
    hash_object = hashlib.md5(title.encode())
    seed_int = int(hash_object.hexdigest(), 16)
    random.seed(seed_int)
    
    return {
        # Weighted choice: Make Q1/Q2 slightly rarer for realism
        "quartile": random.choices(quartiles, weights=[20, 30, 30, 20], k=1)[0],
        "citations": random.randint(0, 150),
        "keyword": random.choice(keywords)
    }

@app.route('/api/stats/years', methods=['GET'])
def get_year_stats():
    # (Same logic as before - aggregating by year)
    pipeline = [
        {"$match": {"date_pub": {"$ne": "Unknown"}}},
        {"$group": {"_id": "$date_pub", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    data = list(collection.aggregate(pipeline))
    formatted = [{"year": item["_id"], "count": item["count"]} for item in data]
    return jsonify(formatted)

@app.route('/api/stats/countries', methods=['GET'])
def get_country_stats():
    # (Same simulation logic as before)
    countries = ["USA", "China", "India", "UK", "France", "Germany", "Canada", "Australia", "Japan", "Morocco", "Brazil", "Italy", "South Korea", "Singapore", "Spain", "Russia"]
    weights = [18, 18, 12, 8, 6, 6, 4, 4, 4, 3, 3, 2, 3, 2, 2, 2]
    
    total = collection.count_documents({})
    counts = {c: 0 for c in countries}
    
    random.seed(42) # Fixed seed for consistency
    for _ in range(total):
        c = random.choices(countries, weights=weights, k=1)[0]
        counts[c] += 1
        
    formatted = [{"country": k, "count": v} for k, v in counts.items() if v > 0]
    formatted.sort(key=lambda x: x['count'], reverse=True)
    return jsonify(formatted)

@app.route('/api/stats/quartiles', methods=['GET'])
def get_quartile_stats():
    """Returns distribution of articles by Quartile (Q1, Q2, Q3, Q4)"""
    articles = list(collection.find({}, {"title": 1}))
    quartile_counts = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    
    for art in articles:
        data = enrich_article(art)
        quartile_counts[data["quartile"]] += 1
        
    formatted = [{"category": k, "value": v} for k, v in quartile_counts.items()]
    return jsonify(formatted)

@app.route('/api/stats/keywords', methods=['GET'])
def get_keyword_stats():
    """Returns top keywords for the Word Cloud"""
    articles = list(collection.find({}, {"title": 1}))
    keyword_counts = {}
    
    for art in articles:
        data = enrich_article(art)
        kw = data["keyword"]
        keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        
    formatted = [{"text": k, "value": v} for k, v in keyword_counts.items()]
    # Sort for better visualization
    formatted.sort(key=lambda x: x['value'], reverse=True)
    return jsonify(formatted)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)