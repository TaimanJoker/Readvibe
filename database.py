import os
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient, ASCENDING
from pymongo.errors import OperationFailure
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
try:
    TZ_OFFSET = int(get_secret("TIMEZONE_OFFSET", 0))
except (ValueError, TypeError):
    TZ_OFFSET = 0

DB_NAME = "readvibe_v2" # Using v2 database name to avoid conflict during dev

_mongo_client = None

def get_db():
    global _mongo_client
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI not found")
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGODB_URI)
    return _mongo_client[DB_NAME]

def init_db():
    db = get_db()
    # Ensure uniqueness index on quote content
    db.quotes.create_index([("content", ASCENDING)], unique=True)
    # Ensure uniqueness on username
    db.users.create_index([("username", ASCENDING)], unique=True)
    # Index for OAuth IDs (must be sparse so that users without google_id don't trigger duplicates)
    try:
        db.users.create_index([("google_id", ASCENDING)], unique=True, sparse=True)
    except OperationFailure:
        try:
            db.users.drop_index("google_id_1")
            db.users.create_index([("google_id", ASCENDING)], unique=True, sparse=True)
        except Exception as e:
            print(f"Warning: Could not recreate google_id index: {e}")

# --- User Management ---

def get_user_by_google_id(google_id):
    db = get_db()
    # Support looking up mock users whose google_id was set to their email, or normal google_id
    return db.users.find_one({
        "$or": [
            {"google_id": google_id},
            {"email": google_id}
        ]
    })

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

def save_quote(content, title, author, user_id, is_verified=False):
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
                {"author": {"$regex": search_query, "$options": "i"}}
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
    MODEL_DIR = "models"
    from bson.objectid import ObjectId
    
    # Fallback if no models trained yet
    if not os.path.exists(os.path.join(MODEL_DIR, "ranker.pkl")):
        return db.quotes.find_one({"is_verified": True}, sort=[("net_votes", -1)])

    import joblib
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    
    # 1. Load Models safely
    cf_knn = joblib.load(os.path.join(MODEL_DIR, "cf_knn.pkl")) if os.path.exists(os.path.join(MODEL_DIR, "cf_knn.pkl")) else None
    user_item_matrix = joblib.load(os.path.join(MODEL_DIR, "user_item_matrix.pkl")) if os.path.exists(os.path.join(MODEL_DIR, "user_item_matrix.pkl")) else None
    cbf_knn = joblib.load(os.path.join(MODEL_DIR, "cbf_knn.pkl")) if os.path.exists(os.path.join(MODEL_DIR, "cbf_knn.pkl")) else None
    quote_ids = joblib.load(os.path.join(MODEL_DIR, "quote_ids.pkl")) if os.path.exists(os.path.join(MODEL_DIR, "quote_ids.pkl")) else []
    embeddings = joblib.load(os.path.join(MODEL_DIR, "embeddings.pkl")) if os.path.exists(os.path.join(MODEL_DIR, "embeddings.pkl")) else None
    ranker = joblib.load(os.path.join(MODEL_DIR, "ranker.pkl"))
    top_pop_ids = joblib.load(os.path.join(MODEL_DIR, "top_pop.pkl")) if os.path.exists(os.path.join(MODEL_DIR, "top_pop.pkl")) else []

    # Get user interaction history to filter read quotes
    user_interactions = list(db.interactions.find({"user_id": user_id}))
    read_quote_ids = [str(x["quote_id"]) for x in user_interactions]
    user_upvotes = [str(x["quote_id"]) for x in user_interactions if x["action"] == "upvote"]
    
    # --- STAGE 1: Candidate Generation ---
    candidates = set()
    
    # A. Collaborative Candidates
    if cf_knn and user_item_matrix is not None and str(user_id) in user_item_matrix.index:
        user_idx = user_item_matrix.index.get_loc(str(user_id))
        distances, indices = cf_knn.kneighbors(user_item_matrix.iloc[user_idx].values.reshape(1, -1))
        sim_users = user_item_matrix.index[indices[0][1:]]
        for su in sim_users:
            su_upvotes = user_item_matrix.loc[su]
            candidates.update(su_upvotes[su_upvotes == 1].index.tolist())
            
    # B. Content-Based Candidates
    if cbf_knn and embeddings is not None and user_upvotes:
        past_idx = [quote_ids.index(pid) for pid in user_upvotes if pid in quote_ids]
        if past_idx:
            past_embs = embeddings[past_idx]
            distances, indices = cbf_knn.kneighbors(past_embs, n_neighbors=min(5, len(embeddings)))
            for neighbor_list in indices:
                for idx in neighbor_list: candidates.add(quote_ids[idx])
                    
    # C. TopPop Candidates
    for t_id in top_pop_ids[:20]: candidates.add(t_id)
        
    candidates = list(candidates - set(read_quote_ids))
    
    # Fallback if pool is exhausted
    if not candidates:
        fallback = db.quotes.find_one({"is_verified": True, "_id": {"$nin": [ObjectId(qid) for qid in read_quote_ids if len(qid)==24]}}, sort=[("net_votes", -1)])
        return fallback if fallback else db.quotes.find_one({"is_verified": True}, sort=[("net_votes", -1)])

    # --- STAGE 2: Heavy Ranking (Logistic Regression) ---
    X_pred = []
    valid_candidates = []
    
    for q_id in candidates:
        cf_score = 0
        if user_item_matrix is not None and str(user_id) in user_item_matrix.index and q_id in user_item_matrix.columns:
            user_idx = user_item_matrix.index.get_loc(str(user_id))
            distances, indices = cf_knn.kneighbors(user_item_matrix.iloc[user_idx].values.reshape(1, -1))
            sim_users = user_item_matrix.index[indices[0][1:]]
            if len(sim_users) > 0: cf_score = user_item_matrix.loc[sim_users, q_id].mean()
                
        cbf_score = 0
        if embeddings is not None and user_upvotes and q_id in quote_ids:
            q_idx = quote_ids.index(q_id)
            target_emb = embeddings[q_idx].reshape(1, -1)
            past_idx = [quote_ids.index(pid) for pid in user_upvotes if pid in quote_ids]
            if past_idx:
                past_embs = embeddings[past_idx]
                sims = cosine_similarity(target_emb, past_embs)
                cbf_score = sims.max()
                
        X_pred.append([cf_score, cbf_score])
        valid_candidates.append(q_id)
        
    X_pred = np.array(X_pred)
    
    if hasattr(ranker, "predict_proba"): scores = ranker.predict_proba(X_pred)[:, 1]
    else: scores = ranker.decision_function(X_pred)
        
    best_idx = np.argmax(scores)
    best_q_id = valid_candidates[best_idx]
    
    return db.quotes.find_one({"_id": ObjectId(best_q_id)})
