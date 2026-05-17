import streamlit as st
from database import (
    get_secret, TZ_OFFSET, get_user_by_google_id, create_user, 
    get_user_by_username, save_quote, quote_exists, init_db,
    get_quotes, get_user_activity_dates, log_interaction, 
    get_user_quotes, get_user_vote, update_user_profile_pic, get_recommended_quote
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

# Default Avatar List with Labels
DEFAULT_AVATARS = {
    "Panda": "https://api.dicebear.com/7.x/bottts/svg?seed=Panda",
    "Cat": "https://api.dicebear.com/7.x/bottts/svg?seed=Felix",
    "Dog": "https://api.dicebear.com/7.x/bottts/svg?seed=Buster",
    "Bear": "https://api.dicebear.com/7.x/bottts/svg?seed=Bear",
    "Fox": "https://api.dicebear.com/7.x/bottts/svg?seed=Fox",
    "Owl": "https://api.dicebear.com/7.x/bottts/svg?seed=Owl"
}

# Helper to format content
def format_quote(text):
    if not text: return ""
    text = text.strip()
    return text[0].upper() + text[1:]

# Custom CSS for Modern "Calm" Look
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #fdfaf6;
    }
    
    /* Elegant Modern Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f0f4f0 !important;
        border-right: 1px solid #e0eee0;
    }
    
    /* Card Styling */
    .highlight-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 20px;
        border: 1px solid #f0f0f0;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .highlight-content {
        font-family: 'Georgia', serif;
        font-size: 1.2rem;
        color: #333333;
        line-height: 1.7;
        margin-bottom: 12px;
    }
    .highlight-meta {
        font-size: 0.85rem;
        color: #888888;
    }
    .highlight-title {
        font-weight: bold;
        color: #5c8d89;
    }
    
    /* Voting Buttons Styling */
    .vote-btn-active-up {
        background-color: #d4e2d4 !important;
        color: #2e7d32 !important;
        border: 1px solid #2e7d32 !important;
    }
    .vote-btn-active-down {
        background-color: #ffebee !important;
        color: #c62828 !important;
        border: 1px solid #c62828 !important;
    }

    /* Calendar Fix */
    .calendar-container {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 20px;
        border: 1px solid #e0eee0;
        max-width: 400px;
        margin: 0 auto 30px auto;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Authentication Logic ---
if 'user' not in st.session_state:
    st.session_state.user = None

def login():
    st.title("Welcome to Readvibe 🌿")
    st.write("Please sign in to continue to the community.")
    if st.button("Sign in with Google"):
        mock_user_info = {
            "google_id": "mock_google_123",
            "email": "user@example.com",
            "profile_pic": DEFAULT_AVATARS["Panda"]
        }
        user = get_user_by_google_id(mock_user_info["google_id"])
        st.session_state.user = user if user else mock_user_info
        st.rerun()

def onboarding():
    st.title("Join the Community 🌿")
    st.write("Almost there! Choose your unique username and contribute your first quote.")
    with st.form("onboarding_form"):
        username = st.text_input("Choose a Username")
        st.divider()
        st.write("### Contribute your first unique quote")
        content = st.text_area("The Quote", max_chars=300)
        col1, col2 = st.columns(2)
        title = col1.text_input("Source Title")
        author = col2.text_input("Author")
        submit = st.form_submit_button("Complete Registration")
        if submit:
            content = format_quote(content)
            if not username: st.error("Username is required.")
            elif get_user_by_username(username): st.error("Username taken.")
            elif not content: st.error("Quote required.")
            elif quote_exists(content): st.error("Quote already exists!")
            else:
                with st.spinner("AI verifying..."):
                    ai_result = verify_quote_with_ai(content, title, author)
                if ai_result["verified"]:
                    user_res = create_user(st.session_state.user["google_id"], username, st.session_state.user["email"], st.session_state.user["profile_pic"])
                    save_quote(content, ai_result["title"], ai_result["author"], user_res.inserted_id)
                    st.session_state.user = get_user_by_google_id(st.session_state.user["google_id"])
                    st.success("Welcome! 🎉")
                    st.rerun()
                else:
                    st.error(f"Rejection: {ai_result['reason']}")

if st.session_state.user is None:
    login()
    st.stop()
if "_id" not in st.session_state.user:
    onboarding()
    st.stop()

user_data = st.session_state.user

# --- Sidebar ---
with st.sidebar:
    st.markdown(f'<h2 style="color: #5c8d89; margin-left: 20px;">Readvibe 🌿</h2>', unsafe_allow_html=True)
    
    with st.expander("🛠️ Switch Account (Debug)"):
        if st.button("User: Taiman", use_container_width=True):
            st.session_state.user = get_user_by_google_id("mock_google_123")
            st.rerun()
        if st.button("User: Sarah", use_container_width=True):
            sarah = get_user_by_google_id("mock_google_sarah")
            if not sarah:
                st.session_state.user = {"google_id": "mock_google_sarah", "email": "sarah@test.com", "profile_pic": DEFAULT_AVATARS["Cat"]}
            else:
                st.session_state.user = sarah
            st.rerun()
            
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Feed"
    if st.button("Explore Feed", use_container_width=True, type="primary" if st.session_state.current_page == "Feed" else "secondary"):
        st.session_state.current_page = "Feed"
        st.rerun()
    if st.button("My Profile", use_container_width=True, type="primary" if st.session_state.current_page == "My Profile" else "secondary"):
        st.session_state.current_page = "My Profile"
        st.rerun()
    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# --- Page Rendering ---
def render_feed():
    st.title("Community Feed 🌿")
    with st.expander("✨ Share a New Quote"):
        with st.form("new_quote_form"):
            content = st.text_area("The Quote", max_chars=300)
            col1, col2 = st.columns(2)
            title = col1.text_input("Source")
            author = col2.text_input("Author")
            submit = st.form_submit_button("Submit")
            if submit:
                content = format_quote(content)
                if content and not quote_exists(content):
                    with st.spinner("AI verifying..."):
                        ai_result = verify_quote_with_ai(content, title, author)
                    if ai_result["verified"]:
                        save_quote(content, ai_result["title"], ai_result["author"], user_data["_id"])
                        st.success("Added! ✨")
                        st.rerun()
                    else: st.error(ai_result["reason"])

    st.write("### Consistency Tracker")
    activity = get_user_activity_dates(user_data["_id"])
    if 'feed_month' not in st.session_state:
        st.session_state.feed_month = datetime.datetime.now(timezone.utc).month
        st.session_state.feed_year = datetime.datetime.now(timezone.utc).year
    nav_cols = st.columns([1, 1, 3, 1, 1])
    if nav_cols[0].button("←", key="p"):
        st.session_state.feed_month -= 1
        if st.session_state.feed_month == 0:
            st.session_state.feed_month = 12
            st.session_state.feed_year -= 1
        st.rerun()
    if nav_cols[2].button("Today 🌿", use_container_width=True):
        st.session_state.feed_month = datetime.datetime.now(timezone.utc).month
        st.session_state.feed_year = datetime.datetime.now(timezone.utc).year
        st.rerun()
    if nav_cols[4].button("→", key="n"):
        st.session_state.feed_month += 1
        if st.session_state.feed_month == 13:
            st.session_state.feed_month = 1
            st.session_state.feed_year += 1
        st.rerun()

    view_month = st.session_state.feed_month
    view_year = st.session_state.feed_year
    cal_data = calendar.monthcalendar(view_year, view_month)
    header_html = "".join([f'<div style="font-weight: bold; color: #5c8d89;">{d}</div>' for d in ['M', 'T', 'W', 'T', 'F', 'S', 'S']])
    body_html = ""
    for week in cal_data:
        for day in week:
            if day == 0: body_html += '<div></div>'
            else:
                date_str = f"{view_year}-{view_month:02d}-{day:02d}"
                is_active = date_str in activity
                body_html += f'<div class="calendar-day {"day-active" if is_active else ""}">{day}</div>'
    st.markdown(f'<div class="calendar-container"><div class="calendar-header">{calendar.month_name[view_month]} {view_year}</div><div class="calendar-grid">{header_html}{body_html}</div></div>', unsafe_allow_html=True)

    st.write("---")
    featured = get_recommended_quote(user_data["_id"])
    if featured:
        st.markdown(f'<div class="featured-card"><div class="featured-badge">Recommended for You</div><div class="featured-content">"{featured["content"]}"</div><div style="margin-top: 15px; font-style: italic; color: #8c8c8c;">— {featured["title"]} by {featured["author"]}</div></div>', unsafe_allow_html=True)

    st.write("### Community Feed")
    quotes = get_quotes(limit=20)
    for q in quotes:
        st.markdown(f'<div class="highlight-card"><div class="highlight-content">"{q["content"]}"</div><div class="highlight-meta"><span class="highlight-title">{q["title"]}</span> by {q["author"]}</div></div>', unsafe_allow_html=True)
        if q["added_by"] != user_data["_id"]:
            user_vote = get_user_vote(user_data["_id"], q["_id"])
            v1, v2, v3 = st.columns([1, 1, 4])
            if v1.button(f"⬆️ {q.get('upvotes', 0)}", key=f"u_{q['_id']}", type="primary" if user_vote == "upvote" else "secondary"):
                log_interaction(user_data["_id"], q["_id"], "upvote")
                st.rerun()
            if v2.button(f"⬇️ {q.get('downvotes', 0)}", key=f"d_{q['_id']}", type="primary" if user_vote == "downvote" else "secondary"):
                log_interaction(user_data["_id"], q["_id"], "downvote")
                st.rerun()
        else:
            st.caption(f"✨ Your contribution • ⬆️ {q.get('upvotes', 0)} ⬇️ {q.get('downvotes', 0)}")

def render_profile():
    st.title(f"@{user_data['username']} 🌿")
    p1, p2 = st.columns([1, 3])
    with p1:
        st.image(user_data["profile_pic"], width=120)
        with st.expander("Change Avatar 🐾"):
            for name, url in DEFAULT_AVATARS.items():
                if st.button(f"Choose {name}", key=f"av_{name}", use_container_width=True):
                    update_user_profile_pic(user_data["_id"], url)
                    st.session_state.user["profile_pic"] = url
                    st.rerun()
    with p2:
        st.write(f"**Verified Highlights:** {len(get_user_quotes(user_data['_id']))}")
        st.write(f"**Community Impact:** ⬆️ {user_data.get('total_upvotes_received', 0)} | ⬇️ {user_data.get('total_downvotes_received', 0)}")
    st.write("---")
    st.write("### My Highlights")
    for q in get_user_quotes(user_data["_id"]):
        st.markdown(f'<div class="highlight-card"><div class="highlight-content">"{q["content"]}"</div><div class="highlight-meta"><span class="highlight-title">{q["title"]}</span> by {q["author"]} • ⬆️ {q.get("upvotes", 0)} ⬇️ {q.get("downvotes", 0)}</div></div>', unsafe_allow_html=True)

if st.session_state.current_page == "Feed": render_feed()
else: render_profile()
