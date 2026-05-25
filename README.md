# Readvibe 🌿

🌐 **Live Application:** [Join the Community Here!](https://readvibe.streamlit.app)

Readvibe is a community-driven, AI-verified social platform designed for sharing, discovering, and discussing inspiring quotes, reflections, and highlights from books, movies, and historical figures. 

Built with a meritocratic, anonymized feed in mind, Readvibe eliminates the "echo chamber" and "influencer bias" of traditional social media. Instead, it leverages a custom Hybrid Machine Learning Recommendation Engine to surface the most semantically relevant and community-validated thoughts directly to you.

## 🌟 General Usage & Community Guidelines

1. **Share & Verify:** When a user shares a quote, our AI Bouncer (powered by Google Gemini) strictly verifies its authenticity. Quotes must be verbatim from a published source to earn the prestigious `✓ verified` badge.
2. **Build Credibility:** The platform operates on a gamified credibility system. By consistently sharing verified quotes, users level up their profiles from 🌱 *Seedling* all the way to 🌌 *Ascendant*.
3. **Discover:** The Community Feed is anonymized. You vote purely on the quality of the thought, not the person who posted it. The more you interact (upvote/downvote), the smarter your personal "Top Reflection" hero section becomes.

---

## 🧠 Machine Learning Architecture

### The Pain Point of Modern Recommendation Systems
Most modern social platforms rely heavily on either purely Collaborative Filtering (which creates vicious "rich-get-richer" popularity echo chambers) or purely Content-Based Filtering (which traps users in highly specific, repetitive topic loops). Furthermore, many platforms default to using pre-packaged "black box" libraries like LightFM. While LightFM is fantastic for rapid prototyping, it obscures the underlying mathematics and limits our ability to dynamically weight our scoring mechanisms based on real-time community context.

### Our Solution: The Cascaded Pipeline
To solve this, we architected a custom **Cascaded Recommendation Pipeline** utilizing fundamental `scikit-learn` algorithms (K-Nearest Neighbors and Logistic Regression). This mirrors the multi-stage funnels used by industry giants like Netflix and Amazon.

**Stage 1: Candidate Generation (High Recall)**
Instead of scoring the entire database for every user, we generate a high-recall pool of ~50 candidates using independent models:
1. **Collaborative Generation (User-User KNN):** We project users into a latent space based on their historical upvote/downvote matrices and use Cosine Similarity to find "taste neighbors."
2. **Semantic Generation (Item-Item KNN):** We utilize HuggingFace's `sentence-transformers` (`all-MiniLM-L6-v2`) to generate dense vector embeddings of quote text. We then pull quotes that are mathematically proximal to the user's previously liked quotes.
3. **Cold-Start Fallback (TopPop):** For brand new users with sparse matrices, we pad the candidate pool with historically high-net-vote quotes.

**Stage 2: Heavy Ranking (High Precision)**
We avoid rigid `50/50` scoring formulas. Instead, we extract historical interaction features and train a **Logistic Regression** ranker via **GridSearchCV** (Cross-Validation). This model dynamically learns the optimal weighting between the Collaborative score and the Semantic score to predict the exact probability of an upvote.

*Why Logistic Regression over Deep Learning?* For our current dataset size, Logistic Regression provides a highly interpretable, convex loss function that perfectly balances the CF and CBF scores without overfitting, which is a massive risk when deploying Neural Networks on early-stage interaction data.

---

## 🗄️ Database Design

Readvibe utilizes **MongoDB Atlas** for its flexible, document-based NoSQL architecture. This is critical for storing dense vector embeddings alongside standard text metadata.

### Schema Overview
* **`users` Collection:** Stores authentication data (Bcrypt/OAuth), profile customization, and aggregated credibility metrics (Total Upvotes Received).
* **`quotes` Collection:** Stores the raw text, author, source, AI verification status, and the 384-dimensional HuggingFace vector embedding. Indexed for fast text search.
* **`interactions` Collection:** A transactional ledger recording every `upvote`, `downvote`, and `view`. This collection is the sole source of truth for our ML pipeline, allowing us to rebuild user matrices dynamically without mutating the core quote documents.

---

## 🚀 Tech Stack
* **Frontend/Backend:** Python, Streamlit
* **Database:** MongoDB Atlas, PyMongo
* **Machine Learning:** Scikit-Learn, Pandas, NumPy, HuggingFace Sentence-Transformers
* **Artificial Intelligence:** Google Gemini API (Strict Bouncer Verification)
* **Authentication:** Bcrypt, Streamlit Secrets
