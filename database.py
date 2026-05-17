import os
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient, ASCENDING
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
DB_NAME = "readvibe_v2" # Using v2 database name to avoid conflict during dev

def get_db():
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI not found")
    client = MongoClient(MONGODB_URI)
    return client[DB_NAME]

def init_db():
    db = get_db()
    # Ensure uniqueness index on quote content
    db.quotes.create_index([("content", ASCENDING)], unique=True)
    # Ensure uniqueness on username
    db.users.create_index([("username", ASCENDING)], unique=True)
    # Index for OAuth IDs
    db.users.create_index([("google_id", ASCENDING)], unique=True)

# --- User Management ---

def get_user_by_google_id(google_id):
    db = get_db()
    return db.users.find_one({"google_id": google_id})

def get_user_by_username(username):
    db = get_db()
    return db.users.find_one({"username": username})

def create_user(google_id, username, email, profile_pic):
    db = get_db()
    user = {
        "google_id": google_id,
        "username": username,
        "email": email,
        "profile_pic": profile_pic,
        "created_at": datetime.now(timezone.utc),
        "total_upvotes_received": 0,
        "total_downvotes_received": 0
    }
    return db.users.insert_one(user)

def update_user_profile_pic(user_id, photo_url):
    db = get_db()
    db.users.update_one({"_id": user_id}, {"$set": {"profile_pic": photo_url}})

# --- Machine Learning Helpers ---

_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model

def generate_embedding(text):
    model = get_embedding_model()
    # Convert embedding to list for MongoDB storage
    return model.encode(text).tolist()

# --- Quote Management ---

def quote_exists(content):
    db = get_db()
    return db.quotes.find_one({"content": content}) is not None

def save_quote(content, title, author, user_id, tags=None, is_verified=False):
    db = get_db()
    
    # Generate Embedding for ML
    try:
        embedding = generate_embedding(content)
    except Exception as e:
        print(f"Embedding failed: {e}")
        embedding = None
        
    quote = {
        "content": content,
        "title": title or "Untitled",
        "author": author or "Unknown",
        "tags": tags or [],
        "added_by": user_id,
        "created_at": datetime.now(timezone.utc),
        "embedding": embedding,
        "is_verified": is_verified,
        "net_votes": 0,
        "upvotes": 0,
        "downvotes": 0
    }
    return db.quotes.insert_one(quote)

def get_quotes(search_query=None, limit=20, skip=0):
    db = get_db()
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
    return list(db.quotes.find(query).sort("created_at", -1).skip(skip).limit(limit))

def get_user_quotes(user_id):
    db = get_db()
    return list(db.quotes.find({"added_by": user_id}).sort("created_at", -1))

# --- Interaction Management ---

def get_user_vote(user_id, quote_id):
    db = get_db()
    interaction = db.interactions.find_one({
        "user_id": user_id, 
        "quote_id": quote_id, 
        "action": {"$in": ["upvote", "downvote"]}
    })
    return interaction["action"] if interaction else None

def log_interaction(user_id, quote_id, action_type):
    """
    action_type: 'upvote', 'downvote', 'view'
    Enforces:
    - No self-voting.
    - One vote per user (replaces or removes old vote).
    """
    db = get_db()
    
    # 1. Prevent self-voting
    quote = db.quotes.find_one({"_id": quote_id})
    if not quote: return False
    if quote["added_by"] == user_id:
        return "self_vote" 
    
    # 2. Handle Voting logic (unique per user)
    if action_type in ['upvote', 'downvote']:
        existing_vote = db.interactions.find_one({
            "user_id": user_id, 
            "quote_id": quote_id, 
            "action": {"$in": ["upvote", "downvote"]}
        })
        
        # If user is clicking the same button twice, remove the vote (toggle off)
        if existing_vote and existing_vote["action"] == action_type:
            db.interactions.delete_one({"_id": existing_vote["_id"]})
            dec_field = "upvotes" if action_type == 'upvote' else "downvotes"
            net_dec = -1 if action_type == 'upvote' else 1
            db.quotes.update_one({"_id": quote_id}, {"$inc": {dec_field: -1, "net_votes": net_dec}})
            db.users.update_one({"_id": quote["added_by"]}, {"$inc": {f"total_{action_type}s_received": -1}})
            return "removed"

        # If user is changing vote, decrement old one first
        if existing_vote:
            old_action = existing_vote["action"]
            dec_field = "upvotes" if old_action == 'upvote' else "downvotes"
            net_dec = -1 if old_action == 'upvote' else 1
            db.quotes.update_one({"_id": quote_id}, {"$inc": {dec_field: -1, "net_votes": net_dec}})
            db.users.update_one({"_id": quote["added_by"]}, {"$inc": {f"total_{old_action}s_received": -1}})
            db.interactions.delete_one({"_id": existing_vote["_id"]})

        # Log New Interaction
        interaction = {
            "user_id": user_id,
            "quote_id": quote_id,
            "action": action_type,
            "timestamp": datetime.now(timezone.utc)
        }
        db.interactions.insert_one(interaction)
        
        # Increment new vote counts
        inc_field = "upvotes" if action_type == 'upvote' else "downvotes"
        net_inc = 1 if action_type == 'upvote' else -1
        db.quotes.update_one({"_id": quote_id}, {"$inc": {inc_field: 1, "net_votes": net_inc}})
        db.users.update_one({"_id": quote["added_by"]}, {"$inc": {f"total_{action_type}s_received": 1}})
        return "added"
    
    else:
        # Just a view, log normally
        db.interactions.insert_one({
            "user_id": user_id,
            "quote_id": quote_id,
            "action": action_type,
            "timestamp": datetime.now(timezone.utc)
        })
        return True

def get_user_activity_dates(user_id):
    db = get_db()
    pipeline = [
        {"$match": {"added_by": user_id}},
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
    results = list(db.quotes.aggregate(pipeline))
    return {item["_id"]: item["count"] for item in results}

def get_recommended_quote(user_id):
    db = get_db()
    
    # 1. Find user's latest upvote (only verified)
    last_upvote = db.interactions.find_one(
        {"user_id": user_id, "action": "upvote"},
        sort=[("timestamp", -1)]
    )
    
    # Fallback to most popular VERIFIED
    fallback = db.quotes.find_one({"is_verified": True}, sort=[("net_votes", -1)])
    
    if not last_upvote:
        return fallback
    
    seed_quote = db.quotes.find_one({"_id": last_upvote["quote_id"]})
    if not seed_quote or not seed_quote.get("embedding"):
        return fallback
    
    # 2. Find similar quotes (only verified)
    all_quotes = list(db.quotes.find({"_id": {"$ne": seed_quote["_id"]}, "is_verified": True}))
    
    if not all_quotes: return seed_quote
    
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    
    try:
        seed_vec = np.array(seed_quote["embedding"]).reshape(1, -1)
        eligible = [q for q in all_quotes if q.get("embedding")]
        if not eligible: return fallback
        
        other_vecs = np.array([q["embedding"] for q in eligible])
        similarities = cosine_similarity(seed_vec, other_vecs)[0]
        best_idx = np.argmax(similarities)
        
        return eligible[best_idx]
    except:
        return fallback
