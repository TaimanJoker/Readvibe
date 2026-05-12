import os
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def get_secret(key, default=None):
    # Try Streamlit secrets first (for Cloud)
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass
    # Fallback to Environment Variables (for Local)
    return os.getenv(key, default)

MONGODB_URI = get_secret("MONGODB_URI")
TZ_OFFSET = int(get_secret("TIMEZONE_OFFSET", 0))
DB_NAME = "readvibe"
COLLECTION_NAME = "highlights"

def get_collection():
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI not found")
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]

def save_highlight(content, title=None, author=None, tags=None):
    collection = get_collection()
    highlight = {
        "content": content,
        "title": title or "Untitled",
        "author": author or "Unknown",
        "tags": tags or [],
        "created_at": datetime.now(timezone.utc) # Store real UTC
    }
    return collection.insert_one(highlight)

def get_highlights(search_query=None):
    collection = get_collection()
    query = {}
    if search_query:
        query = {
            "$or": [
                {"content": {"$regex": search_query, "$options": "i"}},
                {"title": {"$regex": search_query, "$options": "i"}},
                {"author": {"$regex": search_query, "$options": "i"}},
                {"tags": {"$regex": search_query, "$options": "i"}}
            ]
        }
    return list(collection.find(query).sort("created_at", -1))

def get_activity_dates():
    collection = get_collection()
    # Apply offset inside the MongoDB aggregation
    pipeline = [
        {
            "$project": {
                "local_date": {
                    "$dateToString": { 
                        "format": "%Y-%m-%d", 
                        "date": { "$add": ["$created_at", TZ_OFFSET * 3600000] } 
                    }
                }
            }
        },
        {
            "$group": {
                "_id": "$local_date",
                "count": { "$sum": 1 }
            }
        }
    ]
    results = list(collection.aggregate(pipeline))
    return {item["_id"]: item["count"] for item in results}

def get_random_highlight():
    collection = get_collection()
    count = collection.count_documents({})
    if count == 0:
        return None
    import random
    skip = random.randint(0, count - 1)
    return collection.find().limit(1).skip(skip)[0]
