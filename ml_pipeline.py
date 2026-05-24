import os
import pandas as pd
import numpy as np
import joblib
from sklearn.neighbors import NearestNeighbors
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.metrics.pairwise import cosine_similarity
from database import get_db

MODEL_DIR = "models"
if not os.path.exists(MODEL_DIR):
    os.makedirs(MODEL_DIR)

def fetch_training_data():
    db = get_db()
    # 1. Fetch interactions (Data Curation)
    interactions = list(db.interactions.find({"action": {"$in": ["upvote", "downvote"]}}))
    df_inter = pd.DataFrame(interactions)
    if not df_inter.empty:
        df_inter['user_id'] = df_inter['user_id'].astype(str)
        df_inter['quote_id'] = df_inter['quote_id'].astype(str)
        df_inter['rating'] = df_inter['action'].apply(lambda x: 1 if x == 'upvote' else -1)
    
    # 2. Fetch verified quotes with embeddings
    quotes = list(db.quotes.find({"is_verified": True, "embedding": {"$ne": None}}))
    df_quotes = pd.DataFrame(quotes)
    if not df_quotes.empty:
        df_quotes['_id'] = df_quotes['_id'].astype(str)
        df_quotes.set_index('_id', inplace=True)

    return df_inter, df_quotes

def train_pipeline():
    """
    Executes the Hybrid Recommendation Batch Training:
    1. Generates User-Item matrix and fits Collaborative Filtering KNN.
    2. Fits Semantic Content-Based KNN on HuggingFace embeddings.
    3. Trains Logistic Regression Ranker using Cross-Validation to dynamically weight scores.
    """
    print("Fetching training data from MongoDB...")
    df_inter, df_quotes = fetch_training_data()
    
    if df_inter.empty or len(df_inter) < 5 or df_quotes.empty:
        print("Not enough interaction data to train models. Waiting for more community activity.")
        return False
        
    print(f"Data fetched: {len(df_inter)} interactions, {len(df_quotes)} verified quotes.")
    
    # --- 1. TopPop Fallback (COSC2670) ---
    print("Caching TopPop Baseline...")
    top_pop_ids = df_inter[df_inter['rating'] == 1]['quote_id'].value_counts().index.tolist()
    joblib.dump(top_pop_ids, os.path.join(MODEL_DIR, "top_pop.pkl"))

    # --- 2. Collaborative Filtering / User-User KNN (MATH2319 / COSC2670) ---
    print("Training CF KNN Model...")
    user_item_matrix = df_inter.pivot_table(index='user_id', columns='quote_id', values='rating').fillna(0)
    
    k_cf = min(5, len(user_item_matrix)) 
    
    if k_cf > 1:
        cf_knn = NearestNeighbors(n_neighbors=k_cf, metric='cosine')
        cf_knn.fit(user_item_matrix)
        joblib.dump(cf_knn, os.path.join(MODEL_DIR, "cf_knn.pkl"))
        joblib.dump(user_item_matrix, os.path.join(MODEL_DIR, "user_item_matrix.pkl"))
    
    # --- 3. Content-Based Filtering / Item-Item KNN (MATH2319) ---
    print("Training CBF KNN Model...")
    embeddings = np.array(df_quotes['embedding'].tolist())
    quote_ids = df_quotes.index.tolist()
    
    k_cbf = min(10, len(embeddings))
    if k_cbf > 1:
        cbf_knn = NearestNeighbors(n_neighbors=k_cbf, metric='cosine')
        cbf_knn.fit(embeddings)
        joblib.dump(cbf_knn, os.path.join(MODEL_DIR, "cbf_knn.pkl"))
        joblib.dump(quote_ids, os.path.join(MODEL_DIR, "quote_ids.pkl"))
        joblib.dump(embeddings, os.path.join(MODEL_DIR, "embeddings.pkl"))

    # --- 4. Ranker / Logistic Regression (MATH2319) ---
    print("Training Logistic Regression Ranker via Cross-Validation...")
    X = []
    y = []
    
    if k_cf > 1 and k_cbf > 1:
        # Generate training features from historical interactions
        for idx, row in df_inter.iterrows():
            u_id = row['user_id']
            q_id = row['quote_id']
            rating = 1 if row['rating'] == 1 else 0 
            
            # Feature 1: Collaborative Score (Average rating from Similar Users)
            cf_score = 0
            if u_id in user_item_matrix.index and q_id in user_item_matrix.columns:
                user_idx = user_item_matrix.index.get_loc(u_id)
                distances, indices = cf_knn.kneighbors(user_item_matrix.iloc[user_idx].values.reshape(1, -1))
                sim_users = user_item_matrix.index[indices[0][1:]] 
                if len(sim_users) > 0:
                    cf_score = user_item_matrix.loc[sim_users, q_id].mean()
            
            # Feature 2: Content-Based Score (Max similarity to user's other upvotes)
            cbf_score = 0
            past_upvotes = df_inter[(df_inter['user_id'] == u_id) & (df_inter['rating'] == 1) & (df_inter['quote_id'] != q_id)]['quote_id'].tolist()
            if past_upvotes and q_id in quote_ids:
                q_idx = quote_ids.index(q_id)
                target_emb = embeddings[q_idx].reshape(1, -1)
                
                past_idx = [quote_ids.index(pid) for pid in past_upvotes if pid in quote_ids]
                if past_idx:
                    past_embs = embeddings[past_idx]
                    sims = cosine_similarity(target_emb, past_embs)
                    cbf_score = sims.max()
                    
            X.append([cf_score, cbf_score])
            y.append(rating)
            
    X = np.array(X)
    y = np.array(y)
    
    if len(np.unique(y)) > 1 and len(X) >= 5:
        # We have enough data to run Logistic Regression with GridSearchCV
        param_grid = {'C': [0.1, 1.0, 10.0]}
        lr = LogisticRegression(class_weight='balanced')
        clf = GridSearchCV(lr, param_grid, cv=min(3, len(y)//2))
        clf.fit(X, y)
        print(f"Logistic Regression trained! Optimal Hyperparameters: {clf.best_params_}")
        joblib.dump(clf.best_estimator_, os.path.join(MODEL_DIR, "ranker.pkl"))
    else:
        print("Not enough variance in target variable. Using default static 50/50 fallback weights.")
        dummy_lr = LogisticRegression()
        dummy_lr.coef_ = np.array([[0.5, 0.5]])
        dummy_lr.intercept_ = np.array([0.0])
        dummy_lr.classes_ = np.array([0, 1])
        joblib.dump(dummy_lr, os.path.join(MODEL_DIR, "ranker.pkl"))

    print("Pipeline training completed and models saved!")
    return True

if __name__ == "__main__":
    train_pipeline()
