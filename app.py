import streamlit as st
import requests
import urllib.parse
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

# Default Avatar List
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
    .verified-badge { color: #8c8c8c; font-style: italic; font-size: 0.75rem; margin-left: 10px; }
    
    /* Featured Section (Hero) */
    .featured-container {
        background: linear-gradient(135deg, #5c8d89 0%, #4a7a76 100%);
        padding: 35px;
        border-radius: 25px;
        color: white !important;
        margin-bottom: 40px;
        box-shadow: 0 10px 25px rgba(92, 141, 137, 0.3);
        text-align: center;
    }
    .featured-content { font-family: 'Georgia', serif; font-size: 1.5rem; font-style: italic; line-height: 1.6; margin-bottom: 20px; color: white !important; }
    .featured-meta { font-size: 0.9rem; opacity: 0.9; color: white !important; }
    .featured-badge { background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 0.7rem; text-transform: uppercase; margin-bottom: 15px; display: inline-block; color: white !important; }

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
    
    with st.container():
        st.markdown(f"""
        <div class="highlight-card">
            <div class="highlight-content">"{q["content"]}"</div>
            <div class="highlight-meta">
                <span class="highlight-title">{q["title"]}</span> by {q["author"]} {verified_tag}
            </div>
        """, unsafe_allow_html=True)
        
        if q["added_by"] != user_id:
            v1, v2, v3 = st.columns([1, 1, 4])
            if v1.button(f"⬆️ {q.get('upvotes', 0)}", key=f"u_{q['_id']}_{key_suffix}", type="primary" if user_vote == "upvote" else "secondary"):
                log_interaction(user_id, q["_id"], "upvote"); st.rerun()
            if v2.button(f"⬇️ {q.get('downvotes', 0)}", key=f"d_{q['_id']}_{key_suffix}", type="primary" if user_vote == "downvote" else "secondary"):
                log_interaction(user_id, q["_id"], "downvote"); st.rerun()
        else:
            st.caption(f"✨ Your contribution • ⬆️ {q.get('upvotes', 0)} ⬇️ {q.get('downvotes', 0)}")
        
        st.markdown("</div>", unsafe_allow_html=True)

# --- Authentication ---
client_id = get_secret("GOOGLE_CLIENT_ID")
client_secret = get_secret("GOOGLE_CLIENT_SECRET")
redirect_uri = "https://readvibe.streamlit.app/" if not os.getenv("LOCAL_TEST") else "http://localhost:8501"

if 'user' not in st.session_state:
    st.session_state.user = None

def handle_login():
    st.title("Welcome to Readvibe 🌿")
    st.write("Connect with the community of readers.")
    
    # 1. Show Login Button
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}&response_type=code&scope=openid%20email%20profile"
    st.markdown(f'<a href="{auth_url}" target="_self" style="background-color: #5c8d89; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; display: inline-block;">Sign in with Google</a>', unsafe_allow_html=True)
    
    # 2. Check for redirect code
    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
        # Exchange code for token
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        with st.spinner("Logging you in..."):
            response = requests.post(token_url, data=data)
            if response.status_code == 200:
                access_token = response.json().get("access_token")
                # Get user info
                user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
                headers = {"Authorization": f"Bearer {access_token}"}
                user_info_response = requests.get(user_info_url, headers=headers)
                if user_info_response.status_code == 200:
                    user_info = user_info_response.json()
                    # Success!
                    st.query_params.clear() # Clear code from URL
                    existing_user = get_user_by_google_id(user_info['id'])
                    if existing_user:
                        st.session_state.user = existing_user
                    else:
                        st.session_state.user = {
                            "google_id": user_info['id'],
                            "email": user_info['email'],
                            "profile_pic": user_info.get('picture', DEFAULT_AVATARS["Panda"]),
                            "needs_onboarding": True
                        }
                    st.rerun()

def onboarding():
    st.title("Join the Community 🌿")
    with st.form("onboarding"):
        username = st.text_input("Choose a Username")
        content = st.text_area("Share your first unique quote", max_chars=300)
        col1, col2 = st.columns(2)
        title, author = col1.text_input("Source Title"), col2.text_input("Author")
        if st.form_submit_button("Join Community"):
            content = format_quote(content)
            if username and content and not get_user_by_username(username) and not quote_exists(content):
                with st.spinner("AI verifying..."): ai_res = verify_quote_with_ai(content, title, author)
                user_res = create_user(st.session_state.user["google_id"], username, st.session_state.user["email"], st.session_state.user["profile_pic"])
                save_quote(content, ai_res["title"], ai_res["author"], user_res.inserted_id, is_verified=ai_res["verified"])
                st.session_state.user = get_user_by_google_id(st.session_state.user["google_id"])
                st.rerun()
            elif get_user_by_username(username): st.error("Username taken!")

if st.session_state.user is None: handle_login(); st.stop()
if st.session_state.user.get("needs_onboarding"): onboarding(); st.stop()

user_data = st.session_state.user

# --- Sidebar ---
with st.sidebar:
    st.markdown(f'<h2 style="color: #5c8d89; margin-left: 20px;">Readvibe 🌿</h2>', unsafe_allow_html=True)
    with st.expander("🛠️ Switch Account (Debug)"):
        if st.button("User: Taiman", use_container_width=True):
            st.session_state.user = get_user_by_google_id("mock_google_123"); st.rerun()
        if st.button("User: Sarah", use_container_width=True):
            sarah = get_user_by_google_id("mock_google_sarah")
            st.session_state.user = sarah if sarah else {"google_id": "mock_google_sarah", "email": "sarah@test.com", "profile_pic": DEFAULT_AVATARS["Rabbit"]}
            st.rerun()
    if 'page' not in st.session_state: st.session_state.page = "Feed"
    if st.button("Explore Feed", use_container_width=True, type="primary" if st.session_state.page == "Feed" else "secondary"): st.session_state.page = "Feed"; st.rerun()
    if st.button("My Profile", use_container_width=True, type="primary" if st.session_state.page == "My Profile" else "secondary"): st.session_state.page = "My Profile"; st.rerun()
    st.divider()
    if st.button("Logout", use_container_width=True): st.session_state.user = None; st.rerun()

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
    
    cal_data = calendar.monthcalendar(st.session_state.f_y, st.session_state.f_m)
    h_html = "".join([f'<div style="font-weight: bold; color: #5c8d89;">{d}</div>' for d in ['M', 'T', 'W', 'T', 'F', 'S', 'S']])
    b_html = ""
    for week in cal_data:
        for day in week:
            if day == 0: b_html += '<div></div>'
            else:
                d_str = f"{st.session_state.f_y}-{st.session_state.f_m:02d}-{day:02d}"
                b_html += f'<div class="calendar-day {"day-active" if d_str in activity else ""}">{day}</div>'
    st.markdown(f'<div class="calendar-container"><div class="calendar-header">{calendar.month_name[st.session_state.f_m]} {st.session_state.f_y}</div><div class="calendar-grid">{h_html}{b_html}</div></div>', unsafe_allow_html=True)

    featured = get_recommended_quote(user_data["_id"])
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
    if st.button("Refresh Feed 🔄"): st.rerun()
    db = get_db()
    pipeline = [{"$match": {"_id": {"$ne": featured_id}}}, {"$sample": {"size": 10}}]
    for q in list(db.quotes.aggregate(pipeline)): render_quote_card(q, user_data["_id"], key_suffix="feed")

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
        st.write(f"**Impact:** ⬆️ {user_data.get('total_upvotes_received', 0)} | ⬇️ {user_data.get('total_downvotes_received', 0)}")
    st.write("---"); st.write("### My Highlights")
    for q in get_user_quotes(user_data["_id"]): render_quote_card(q, user_data["_id"], key_suffix="prof")

if st.session_state.page == "Feed": render_feed()
else: render_profile()
