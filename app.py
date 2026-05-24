import streamlit as st
from database import (
    get_secret, TZ_OFFSET, get_user_by_google_id, create_user, 
    get_user_by_username, save_quote, quote_exists, init_db,
    get_quotes, get_user_activity_dates, log_interaction, 
    get_user_quotes, get_user_vote, update_user_profile_pic, get_recommended_quote, get_db
)
import datetime
from datetime import timedelta, timezone
import calendar
import subprocess
import os
import sys
from ai_agent import verify_quote_with_ai

# Initialize Database Indexes
init_db()

st.set_page_config(
    page_title="Readvibe 🌿",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Default Avatar List (Animal-style mascots)
DEFAULT_AVATARS = {
    "Panda": "https://api.dicebear.com/7.x/big-smile/svg?seed=Panda",
    "Lion": "https://api.dicebear.com/7.x/big-smile/svg?seed=Lion",
    "Rabbit": "https://api.dicebear.com/7.x/big-smile/svg?seed=Rabbit",
    "Bear": "https://api.dicebear.com/7.x/big-smile/svg?seed=Bear",
    "Fox": "https://api.dicebear.com/7.x/big-smile/svg?seed=Fox",
    "Owl": "https://api.dicebear.com/7.x/big-smile/svg?seed=Owl"
}

# Helper to format content
def format_quote(text):
    if not text: return ""
    text = text.strip()
    return text[0].upper() + text[1:]

# Custom CSS for Modern "Calm" Look
st.markdown("""
    <style>
    .stApp { background-color: #fdfaf6; }
    [data-testid="stSidebar"] { background-color: #f0f4f0 !important; border-right: 1px solid #e0eee0; }
    
    /* Unified Card Styling */
    .highlight-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 20px;
        border: 1px solid #f0f0f0;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .highlight-content {
        font-family: 'Georgia', serif;
        font-size: 1.2rem;
        color: #333333;
        line-height: 1.7;
        margin-bottom: 12px;
    }
    .highlight-meta { font-size: 0.85rem; color: #888888; margin-bottom: 15px; }
    .highlight-title { font-weight: bold; color: #5c8d89; }
    .verified-badge { color: #8c8c8c; font-style: italic; font-size: 0.75rem; margin-left: 5px; }
    
    /* Action area inside card */
    .card-actions { border-top: 1px solid #f9f9f9; padding-top: 15px; margin-top: 5px; }

    /* Featured Section */
    .featured-container {
        background: linear-gradient(135deg, #5c8d89 0%, #4a7a76 100%);
        padding: 35px;
        border-radius: 25px;
        color: white !important;
        margin-bottom: 40px;
        box-shadow: 0 10px 25px rgba(92, 141, 137, 0.3);
        text-align: center;
    }
    .featured-content { font-family: 'Georgia', serif; font-size: 1.5rem; font-style: italic; line-height: 1.6; margin-bottom: 20px; }
    .featured-meta { font-size: 0.9rem; opacity: 0.9; font-weight: 500; }
    .featured-badge { background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 15px; display: inline-block; }

    /* Calendar Grid Fix */
    .calendar-container {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 20px;
        border: 1px solid #e0eee0;
        max-width: 400px;
        margin: 0 auto 30px auto;
    }
    .calendar-grid {
        display: grid !important;
        grid-template-columns: repeat(7, 1fr) !important;
        gap: 10px !important;
        text-align: center !important;
    }
    .calendar-day {
        width: 100%; aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
        font-size: 0.85rem; border-radius: 8px; background-color: #ffffff; color: #d1d1d1; border: 1px solid #f0f0f0;
    }
    .day-active {
        background-color: #d4e2d4; color: #5c8d89; font-weight: bold;
        box-shadow: 0 0 10px rgba(212, 226, 212, 0.6); border: 2px solid #5c8d89;
    }
    .calendar-header { font-weight: bold; color: #5c8d89; font-size: 1.5rem; margin-bottom: 20px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

def render_quote_card(q, user_id, key_suffix=""):
    user_vote = get_user_vote(user_id, q["_id"])
    verified_tag = '<span class="verified-badge">✓ verified</span>' if q.get("is_verified") else ""
    
    # Opening white block
    st.markdown(f"""
    <div class="highlight-card">
        <div class="highlight-content">"{q["content"]}"</div>
        <div class="highlight-meta">
            <span class="highlight-title">{q["title"]}</span> by {q["author"]} {verified_tag}
        </div>
    """, unsafe_allow_html=True)
    
    # Voting buttons
    if q["added_by"] != user_id:
        v1, v2, v3 = st.columns([1, 1, 4])
        if v1.button(f"⬆️ {q.get('upvotes', 0)}", key=f"u_{q['_id']}_{key_suffix}", type="primary" if user_vote == "upvote" else "secondary"):
            log_interaction(user_id, q["_id"], "upvote")
            st.session_state.pop('featured_quote', None)
            refresh_feed_quotes_from_db()
            st.rerun()
        if v2.button(f"⬇️ {q.get('downvotes', 0)}", key=f"d_{q['_id']}_{key_suffix}", type="primary" if user_vote == "downvote" else "secondary"):
            log_interaction(user_id, q["_id"], "downvote")
            st.session_state.pop('featured_quote', None)
            refresh_feed_quotes_from_db()
            st.rerun()
    else:
        st.caption(f"✨ Your contribution • ⬆️ {q.get('upvotes', 0)} ⬇️ {q.get('downvotes', 0)}")
    
    # Closing white block
    st.markdown("</div>", unsafe_allow_html=True)

def refresh_feed_quotes_from_db():
    if 'feed_quotes' in st.session_state and st.session_state.feed_quotes:
        db = get_db()
        ids = [q["_id"] for q in st.session_state.feed_quotes]
        # Fetch current state of these quotes
        updated_quotes = {q["_id"]: q for q in db.quotes.find({"_id": {"$in": ids}})}
        # Maintain the original order
        st.session_state.feed_quotes = [updated_quotes[q_id] for q_id in ids if q_id in updated_quotes]

# --- Authentication ---

def login():
    st.title("Welcome to Readvibe 🌿")
    
    is_logged_in = False
    if st.user:
        is_logged_in = getattr(st.user, "is_logged_in", False) or (isinstance(st.user, dict) and st.user.get("is_logged_in", False))

    if not is_logged_in:
        st.markdown('<div style="text-align: center; margin-top: 50px;">', unsafe_allow_html=True)
        if st.button("Log in with Google", type="primary", use_container_width=True):
            st.login("google")
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()
    else:
        # Use email as the unique identifier for Google login
        email = getattr(st.user, "email", None) or (isinstance(st.user, dict) and st.user.get("email"))
        if not email:
            st.error("Could not retrieve your Google email. Please try logging in again.")
            if st.button("Log out"):
                st.logout()
            st.stop()
            
        db_user = get_user_by_google_id(email)
        if db_user:
            return db_user
        else:
            picture = getattr(st.user, "picture", None) or (isinstance(st.user, dict) and st.user.get("picture"))
            return {
                "google_id": email, 
                "email": email, 
                "profile_pic": picture or DEFAULT_AVATARS["Panda"]
            }

def onboarding(temp_user):
    st.title("Join the Community 🌿")
    with st.form("onboarding"):
        username = st.text_input("Username")
        content = st.text_area("First Quote", max_chars=300)
        col1, col2 = st.columns(2)
        title, author = col1.text_input("Title"), col2.text_input("Author")
        if st.form_submit_button("Join"):
            content = format_quote(content)
            if not username or not content:
                st.error("Please provide both a username and a quote.")
            elif get_user_by_username(username):
                st.error("That username is already taken! Please choose another one.")
            elif quote_exists(content):
                st.error("That quote already exists in our community! Please share a different one.")
            else:
                with st.spinner("AI checking..."): ai_res = verify_quote_with_ai(content, title, author)
                user_res = create_user(temp_user["google_id"], username, temp_user["email"], temp_user["profile_pic"])
                save_quote(content, ai_res.get("title", title), ai_res.get("author", author), user_res.inserted_id, is_verified=ai_res.get("verified", False))
                st.rerun()
    if st.button("Log out"):
        st.logout()

user_data = login()
if user_data and "_id" not in user_data:
    onboarding(user_data)
    st.stop()
elif not user_data:
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.markdown(f'<h2 style="color: #5c8d89; margin-left: 20px;">Readvibe 🌿</h2>', unsafe_allow_html=True)
    with st.expander("🛠️ Debug Tools"):
        if st.button("User: Taiman"): 
            st.session_state.user_data_override = get_user_by_google_id("mock_google_123")
            st.rerun()
    if 'user_data_override' in st.session_state:
        user_data = st.session_state.user_data_override
    
    if 'page' not in st.session_state: st.session_state.page = "Feed"
    if st.button("Explore Feed", use_container_width=True, type="primary" if st.session_state.page == "Feed" else "secondary"): st.session_state.page = "Feed"; st.rerun()
    if st.button("My Profile", use_container_width=True, type="primary" if st.session_state.page == "My Profile" else "secondary"): st.session_state.page = "My Profile"; st.rerun()
    st.divider()
    if st.button("Logout", use_container_width=True): 
        st.logout()

# --- Pages ---
def render_feed():
    st.title("Community Feed 🌿")
    with st.expander("✨ Share a New Quote"):
        with st.form("new_quote"):
            content = st.text_area("Quote", max_chars=300)
            c1, c2 = st.columns(2); title, author = c1.text_input("Source"), c2.text_input("Author")
            if st.form_submit_button("Submit"):
                content = format_quote(content)
                if content and not quote_exists(content):
                    with st.spinner("AI checking..."): ai_res = verify_quote_with_ai(content, title, author)
                    save_quote(content, ai_res.get("title", title), ai_res.get("author", author), user_data["_id"], is_verified=ai_res.get("verified", False))
                    st.success("Shared!"); st.rerun()

    st.write("### Consistency Tracker")
    activity = get_user_activity_dates(user_data["_id"])
    if 'f_m' not in st.session_state: st.session_state.f_m, st.session_state.f_y = datetime.datetime.now(timezone.utc).month, datetime.datetime.now(timezone.utc).year
    nav = st.columns([1, 1, 3, 1, 1])
    if nav[0].button("←"): st.session_state.f_m -= 1
    if nav[2].button("Today", use_container_width=True): st.session_state.f_m, st.session_state.f_y = datetime.datetime.now(timezone.utc).month, datetime.datetime.now(timezone.utc).year
    if nav[4].button("→"): st.session_state.f_m += 1
    
    cal = calendar.monthcalendar(st.session_state.f_y, st.session_state.f_m)
    h_html = "".join([f'<div style="font-weight: bold; color: #5c8d89;">{d}</div>' for d in ['M', 'T', 'W', 'T', 'F', 'S', 'S']])
    b_html = ""
    for week in cal:
        for day in week:
            if day == 0: b_html += '<div></div>'
            else:
                d_str = f"{st.session_state.f_y}-{st.session_state.f_m:02d}-{day:02d}"
                b_html += f'<div class="calendar-day {"day-active" if d_str in activity else ""}">{day}</div>'
    st.markdown(f'<div class="calendar-container"><div class="calendar-header">{calendar.month_name[st.session_state.f_m]} {st.session_state.f_y}</div><div class="calendar-grid">{h_html}{b_html}</div></div>', unsafe_allow_html=True)

    if 'featured_quote' not in st.session_state:
        st.session_state.featured_quote = get_recommended_quote(user_data["_id"])
    
    featured = st.session_state.featured_quote
    featured_id = featured["_id"] if featured else None
    if featured:
        st.write("### Top Reflection")
        st.markdown(f"""
        <div class="featured-container">
            <div class="featured-badge">Highly Recommended</div>
            <div class="featured-content">"{featured["content"]}"</div>
            <div class="featured-meta">— {featured["title"]} by {featured["author"]}</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("---")
    st.write("### Community Feed")
    if st.button("Refresh Feed 🔄"): 
        st.session_state.pop('feed_quotes', None)
        st.rerun()

    if 'feed_quotes' not in st.session_state:
        db = get_db()
        pipeline = [{"$match": {"_id": {"$ne": featured_id}}}, {"$sample": {"size": 10}}]
        st.session_state.feed_quotes = list(db.quotes.aggregate(pipeline))

    for q in st.session_state.feed_quotes:
        render_quote_card(q, user_data["_id"], key_suffix="feed")

def render_profile():
    st.title(f"@{user_data['username']} 🌿")
    p1, p2 = st.columns([1, 3])
    with p1:
        st.image(user_data["profile_pic"], width=120)
        with st.expander("Avatar 🐾"):
            for name, url in DEFAULT_AVATARS.items():
                if st.button(name, key=f"av_{name}", use_container_width=True):
                    update_user_profile_pic(user_data["_id"], url); st.session_state.user["profile_pic"] = url; st.rerun()
    with p2:
        st.write(f"**Verified Highlights:** {len([q for q in get_user_quotes(user_data['_id']) if q.get('is_verified')])}")
        st.write(f"**Impact:** ⬆️ {user_data.get('total_upvotes_received', 0)}")
    st.write("---"); st.write("### My Highlights")
    for q in get_user_quotes(user_data["_id"]): render_quote_card(q, user_data["_id"], key_suffix="prof")

if st.session_state.page == "Feed": render_feed()
else: render_profile()
