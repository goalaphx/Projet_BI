import pymongo

# 1. Connect to MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["aci"]
collection = db["articles"]

print(f"Initial count: {collection.count_documents({})}")

# 2. Identify duplicates using Aggregation
pipeline = [
    {
        "$group": {
            "_id": "$title",  # Group by Title
            "ids": {"$push": "$_id"},  # Collect all IDs for this title
            "count": {"$sum": 1}
        }
    },
    {
        "$match": {
            "count": {"$gt": 1}  # Only look at groups with more than 1 item
        }
    }
]

duplicates = list(collection.aggregate(pipeline))
print(f"Found {len(duplicates)} titles with duplicate entries.")

# 3. Remove the extras
deleted_count = 0
for doc in duplicates:
    # Keep the first one, delete the rest
    ids_to_remove = doc['ids'][1:] 
    result = collection.delete_many({"_id": {"$in": ids_to_remove}})
    deleted_count += result.deleted_count

print(f"Cleaned up! Removed {deleted_count} duplicate documents.")
print(f"Final count: {collection.count_documents({})}")

# 4. Apply the Unique Index (Now safe to do)
try:
    collection.create_index([("title", pymongo.ASCENDING)], unique=True)
    print("SUCCESS: Unique Index created. Future duplicates will be blocked automatically.")
except Exception as e:
    print(f"Index creation failed: {e}")