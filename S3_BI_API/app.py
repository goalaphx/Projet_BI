import sys
import itertools
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

app = Flask(__name__)

# 1. ALLOW ALL ORIGINS
CORS(app, resources={r"/*": {"origins": "*"}})

# 2. CONNECT TO MONGODB (Docker Friendly)
MONGO_URI = "mongodb://localhost:27017/" 

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["aci"]
    collection = db["fact_publications"]
    client.server_info() # Trigger connection check
    print("✅ Connected to MongoDB successfully!")
except ServerSelectionTimeoutError:
    print("❌ ERROR: Could not connect to MongoDB. Ensure 'mongodb' container is running.", file=sys.stderr)
    sys.exit(1)

# --- HELPER: BUILD FILTERS (SLICE & DICE) ---
def build_match_stage():
    """
    Reads query parameters (year, country, quartile) and builds a MongoDB query.
    Example: /api/kpi/summary?year=2021&country=France
    """
    query = {}
    
    # Filter by Year
    year = request.args.get('year')
    if year and year != 'All':
        query['date_pub'] = year
        
    # Filter by Country
    country = request.args.get('country')
    if country and country != 'All':
        query['country'] = country

    # Filter by Quartile
    quartile = request.args.get('quartile')
    if quartile and quartile != 'All':
        query['quartile'] = quartile

    return {"$match": query}

# --- ROUTES ---

@app.route('/api/filters/options', methods=['GET'])
def get_filter_options():
    """Returns available years and countries for the frontend dropdowns"""
    try:
        years = collection.distinct("date_pub")
        countries = collection.distinct("country")
        # Filter out "Unknown" or empty values if necessary
        years = [y for y in years if y and y != "Unknown"]
        countries = [c for c in countries if c]
        return jsonify({"years": sorted(years), "countries": sorted(countries)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/kpi/summary', methods=['GET'])
def get_kpi():
    try:
        match_stage = build_match_stage()
        
        pipeline = [
            match_stage,
            {
                "$group": {
                    "_id": None,
                    "total_pubs": {"$sum": 1},
                    "total_citations": {"$sum": "$citations"},
                    "avg_impact": {"$avg": "$impact_score"},
                    "total_authors": {"$sum": "$nb_authors"}
                }
            }
        ]
        data = list(collection.aggregate(pipeline))
        result = data[0] if data else {"total_pubs": 0, "total_citations": 0, "avg_impact": 0, "total_authors": 0}
        if "_id" in result: del result["_id"]
        return jsonify(result)

    except Exception as e:
        print(f"❌ API ERROR (KPI): {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

@app.route('/api/olap/time_distribution', methods=['GET'])
def olap_time():
    try:
        match_stage = build_match_stage()
        pipeline = [
            match_stage,
            {"$group": {
                "_id": "$date_pub", 
                "count": {"$sum": 1},
                "avg_impact": {"$avg": "$impact_score"}
            }},
            {"$sort": {"_id": 1}}
        ]
        data = list(collection.aggregate(pipeline))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/olap/geo_distribution', methods=['GET'])
def olap_geo():
    try:
        match_stage = build_match_stage()
        pipeline = [
            match_stage,
            {"$group": {"_id": "$country", "value": {"$sum": 1}}},
            {"$sort": {"value": -1}}
        ]
        data = [{"id": str(item["_id"]), "value": item["value"]} for item in collection.aggregate(pipeline) if item["_id"]]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/olap/quality_quartile', methods=['GET'])
def olap_quartile():
    try:
        match_stage = build_match_stage()
        pipeline = [
            match_stage,
            {"$group": {"_id": "$quartile", "count": {"$sum": 1}}}
        ]
        data = list(collection.aggregate(pipeline))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/olap/keywords', methods=['GET'])
def olap_keywords():
    try:
        match_stage = build_match_stage()
        pipeline = [
            match_stage,
            {"$unwind": "$generated_keywords"},
            {"$group": {"_id": "$generated_keywords", "weight": {"$sum": 1}}},
            {"$sort": {"weight": -1}},
            {"$limit": 50}
        ]
        data = [{"text": str(item["_id"]), "weight": item["weight"]} for item in collection.aggregate(pipeline)]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- NEW: CO-AUTHOR NETWORK GRAPH ---
@app.route('/api/olap/network', methods=['GET'])
def olap_network():
    """
    Generates Nodes and Links for a Force-Directed Graph.
    Limits processing to top 50 recent papers to prevent crashing.
    """
    try:
        match_stage = build_match_stage()
        
        # Fetch authors from papers
        pipeline = [
            match_stage,
            {"$project": {"authors_clean": 1}},
            {"$limit": 50} # Limit for performance
        ]
        
        papers = list(collection.aggregate(pipeline))
        
        nodes = {}
        links = []
        
        for paper in papers:
            authors = paper.get("authors_clean", [])
            # Clean author names (remove newlines if any remain)
            authors = [a.strip().replace("\n", "") for a in authors if a and a != "Unknown"]
            
            # Add Nodes
            for author in authors:
                if author not in nodes:
                    nodes[author] = {"id": author, "weight": 1}
                else:
                    nodes[author]["weight"] += 1
            
            # Add Links (Pairs)
            if len(authors) > 1:
                # Generate all unique pairs in this paper
                for a1, a2 in itertools.combinations(authors, 2):
                    # Sort to ensure A->B is same as B->A
                    pair = sorted([a1, a2])
                    links.append({"source": pair[0], "target": pair[1]})

        # Format for amCharts/D3
        node_list = [{"id": k, "value": v["weight"]} for k, v in nodes.items()]
        
        # Deduplicate links (count strength)
        link_counts = {}
        for link in links:
            key = f"{link['source']}|{link['target']}"
            if key in link_counts:
                link_counts[key]["value"] += 1
            else:
                link_counts[key] = {"source": link['source'], "target": link['target'], "value": 1}
                
        link_list = list(link_counts.values())

        return jsonify({"nodes": node_list, "links": link_list})

    except Exception as e:
        print(f"❌ API ERROR (Network): {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

# --- NEW: TOP AUTHORS (Replaces Universities) ---
@app.route('/api/olap/authors', methods=['GET'])
def olap_authors():
    try:
        match_stage = build_match_stage()
        pipeline = [
            match_stage,
            {"$unwind": "$authors_clean"},
            # Clean newline characters if Spark didn't catch all
            {"$project": {"author": {"$trim": {"input": "$authors_clean", "chars": "\n "}}}},
            {"$match": {"author": {"$ne": "Unknown"}}},
            {"$group": {"_id": "$author", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 20}
        ]
        data = list(collection.aggregate(pipeline))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("✅ Flask Server Running on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)