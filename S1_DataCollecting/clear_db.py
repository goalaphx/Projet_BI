import pymongo

def clear_database():
    # 1. Connect to MongoDB
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    
    # 2. Select the database
    db = client["aci"]
    
    # 3. Drop the 'articles' collection
    # This deletes all documents AND the indexes, resetting it completely.
    db["articles"].drop()
    
    print("✅ SUCCESS: The 'articles' collection has been deleted.")
    
    # 4. Verify it's empty
    count = db["articles"].count_documents({})
    print(f"Current Document Count: {count}")

if __name__ == "__main__":
    confirm = input("Are you sure you want to delete ALL data? (yes/no): ")
    if confirm.lower() == "yes":
        clear_database()
    else:
        print("Operation cancelled.")