import streamlit as st
from database import (
    get_secret, TZ_OFFSET, get_user_by_google_id, create_user, 
    get_user_by_username, save_quote, quote_exists, init_db,
    get_quotes, get_user_activity_dates, log_interaction, get_user_quotes
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
    layout="centered"
)

# --- Authentication Logic (Google OAuth Placeholder) ---
# Note: In a real deployment, you would use streamlit-google-auth or similar.
# For now, we will use a session state mock to develop the flow.

if 'user' not in st.session_state:
    st.session_state.user = None

def login():
    st.title("Welcome to Readvibe 🌿")
    st.write("Please sign in to continue to the community.")
    
    # Mock Google Login for development
    # In production, this would be the OAuth flow
    if st.button("Sign in with Google"):
        # This info would come from the Google ID Token
        mock_user_info = {
            "google_id": "mock_google_123",
            "email": "user@example.com",
            "profile_pic": "https://via.placeholder.com/150"
        }
        
        user = get_user_by_google_id(mock_user_info["google_id"])
        if user:
            st.session_state.user = user
        else:
            st.session_state.user = mock_user_info # Temp storage for onboarding
        st.rerun()

def onboarding():
    st.title("Join the Community 🌿")
    st.write("Almost there! Choose your unique username and contribute your first quote.")
    
    with st.form("onboarding_form"):
        username = st.text_input("Choose a Username", help="This must be unique and will be used on your profile.")
        st.divider()
        st.write("### Contribute your first unique quote")
        content = st.text_area("The Quote", max_chars=300)
        col1, col2 = st.columns(2)
        title = col1.text_input("Source Title (Book/Movie/Show)")
        author = col2.text_input("Author/Person")
        tags = st.text_input("Tags (comma separated)")
        
        submit = st.form_submit_button("Complete Registration")
        
        if submit:
            if not username:
                st.error("Username is required.")
            elif get_user_by_username(username):
                st.error("This username is already taken. Please choose another.")
            elif not content:
                st.error("You must contribute a quote to join.")
            elif quote_exists(content):
                st.error("This quote already exists in our community! Please share a novel one.")
            else:
                with st.spinner("Verifying quote with AI..."):
                    ai_result = verify_quote_with_ai(content, title, author)
                
                if not ai_result["verified"]:
                    st.error(f"Verification Failed: {ai_result['reason']}")
                else:
                    # 1. Create User
                    user_res = create_user(
                        st.session_state.user["google_id"],
                        username,
                        st.session_state.user["email"],
                        st.session_state.user["profile_pic"]
                    )
                    user_id = user_res.inserted_id
                    
                    # 2. Save First Quote (using AI corrected data)
                    save_quote(
                        content, 
                        ai_result["title"], 
                        ai_result["author"], 
                        user_id, 
                        [t.strip() for t in tags.split(',')] if tags else []
                    )
                    
                    # 3. Finalize Login
                    st.session_state.user = get_user_by_google_id(st.session_state.user["google_id"])
                    st.success("Welcome aboard! 🎉")
                    st.rerun()

if st.session_state.user is None:
    login()
    st.stop()

if "_id" not in st.session_state.user:
    onboarding()
    st.stop()

# --- Authenticated App UI ---
user_data = st.session_state.user

# Sidebar Navigation
page = st.sidebar.radio("Navigation", ["Feed", "My Profile"])

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# Helper to get current local time
def get_local_now():
    return datetime.datetime.now(timezone.utc) + timedelta(hours=TZ_OFFSET)

# Launch Bot in background if not already running (Deployment Hack)
@st.cache_resource
def start_bot():
    try:
        # We pass secrets as env vars to the bot process
        env = os.environ.copy()
        env["MONGODB_URI"] = get_secret("MONGODB_URI")
        env["TELEGRAM_BOT_TOKEN"] = get_secret("TELEGRAM_BOT_TOKEN")
        env["TIMEZONE_OFFSET"] = str(TZ_OFFSET)
        
        subprocess.Popen([sys.executable, "bot.py"], env=env)
        return True
    except Exception as e:
        return f"Error starting bot: {e}"

start_bot()

# Custom CSS for "calm-tone" cards and Habit Calendar
st.markdown("""
    <style>
    .highlight-card {
        background-color: #fdfaf6;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #d4e2d4;
        margin-bottom: 20px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .highlight-content {
        font-family: 'Georgia', serif;
        font-size: 1.1rem;
        color: #4a4a4a;
        line-height: 1.6;
        margin-bottom: 10px;
    }
    .highlight-meta {
        font-size: 0.9rem;
        color: #8c8c8c;
        font-style: italic;
    }
    .highlight-title {
        font-weight: bold;
        color: #5c8d89;
    }
    .tag-container {
        margin-top: 10px;
    }
    .tag {
        background-color: #e8f0e8;
        color: #5c8d89;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.75rem;
        margin-right: 5px;
        display: inline-block;
    }
    
    /* Featured Quote Styling */
    .featured-card {
        background: linear-gradient(135deg, #fdfaf6 0%, #f0f4f0 100%);
        padding: 30px;
        border-radius: 20px;
        border: 1px solid #d4e2d4;
        margin-bottom: 30px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .featured-badge {
        background-color: #5c8d89;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 15px;
        display: inline-block;
    }
    .featured-content {
        font-family: 'Georgia', serif;
        font-size: 1.4rem;
        color: #2c3e50;
        font-style: italic;
        line-height: 1.5;
    }

    /* Calendar Styling */
    .calendar-container {
        background-color: #f8fbf8;
        padding: 20px;
        border-radius: 15px;
        margin: 0 auto 30px auto;
        border: 1px solid #e0eee0;
        max-width: 400px;
        width: 100%;
    }
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 10px;
        text-align: center;
        align-items: center;
    }
    .calendar-day {
        width: 100%;
        aspect-ratio: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.85rem;
        border-radius: 8px;
        background-color: #ffffff;
        color: #d1d1d1;
        border: 1px solid #f0f0f0;
    }
    .day-active {
        background-color: #d4e2d4;
        color: #5c8d89;
        font-weight: bold;
        box-shadow: 0 0 10px rgba(212, 226, 212, 0.6);
        border: 2px solid #5c8d89;
    }
    .calendar-header {
        font-weight: bold;
        color: #5c8d89;
        font-size: 1.5rem;
        margin-bottom: 20px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Page Rendering ---

def render_feed():
    st.title("Community Feed 🌿")
    
    # --- 1. Submission Section ---
    with st.expander("✨ Share a New Quote with the Community"):
        with st.form("new_quote_form"):
            content = st.text_area("The Quote (Max 300 characters)", max_chars=300)
            col1, col2 = st.columns(2)
            title = col1.text_input("Source Title")
            author = col2.text_input("Author")
            tags = st.text_input("Tags (comma separated)")
            submit = st.form_submit_button("Submit to Readvibe")
            
            if submit:
                if not content:
                    st.error("Quote content is required.")
                elif quote_exists(content):
                    st.error("This quote already exists in our community!")
                else:
                    with st.spinner("AI is verifying your quote..."):
                        ai_result = verify_quote_with_ai(content, title, author)
                    
                    if ai_result["verified"]:
                        save_quote(
                            content, 
                            ai_result["title"], 
                            ai_result["author"], 
                            user_data["_id"],
                            [t.strip() for t in tags.split(',')] if tags else []
                        )
                        st.success("Verified and added! ✨")
                        st.rerun()
                    else:
                        st.error(f"Rejection: {ai_result['reason']}")

    st.write("---")

    # --- 2. Habit Calendar (Personal) ---
    st.write("### Your Consistency")
    activity = get_user_activity_dates(user_data["_id"])
    
    # Navigation Buttons for Calendar
    if 'feed_month' not in st.session_state:
        st.session_state.feed_month = datetime.datetime.now(timezone.utc).month
        st.session_state.feed_year = datetime.datetime.now(timezone.utc).year

    c1, c2, c3 = st.columns([1, 3, 1])
    if c1.button("←", key="prev"):
        st.session_state.feed_month -= 1
        if st.session_state.feed_month == 0:
            st.session_state.feed_month = 12
            st.session_state.feed_year -= 1
        st.rerun()
    if c2.button("Today 🌿", key="today"):
        st.session_state.feed_month = datetime.datetime.now(timezone.utc).month
        st.session_state.feed_year = datetime.datetime.now(timezone.utc).year
        st.rerun()
    if c3.button("→", key="next"):
        st.session_state.feed_month += 1
        if st.session_state.feed_month == 13:
            st.session_state.feed_month = 1
            st.session_state.feed_year += 1
        st.rerun()

    view_month = st.session_state.feed_month
    view_year = st.session_state.feed_year
    cal = calendar.monthcalendar(view_year, view_month)
    
    st.markdown(f'<div class="calendar-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="calendar-header">{calendar.month_name[view_month]} {view_year}</div>', unsafe_allow_html=True)
    
    header_html = "".join([f'<div style="font-weight: bold; color: #5c8d89;">{d}</div>' for d in ['M', 'T', 'W', 'T', 'F', 'S', 'S']])
    body_html = ""
    for week in cal:
        for day in week:
            if day == 0: body_html += '<div></div>'
            else:
                date_str = f"{view_year}-{view_month:02d}-{day:02d}"
                is_active = date_str in activity
                class_name = "calendar-day day-active" if is_active else "calendar-day"
                body_html += f'<div class="{class_name}">{day}</div>'
    
    st.markdown(f'<div class="calendar-grid">{header_html}{body_html}</div></div>', unsafe_allow_html=True)

    # --- 3. Semantic Featured Quote ---
    st.write("---")
    from database import get_recommended_quote
    featured = get_recommended_quote(user_data["_id"])
    
    if featured:
        st.markdown(f"""
        <div class="featured-card">
            <div class="featured-badge">Recommended for You</div>
            <div class="featured-content">"{featured['content']}"</div>
            <div style="margin-top: 15px; font-style: italic; color: #8c8c8c;">
                — {featured['title']} by {featured['author']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- 4. Anonymous Feed ---
    st.write("### Explore Community")
    quotes = get_quotes(limit=10) # Random/Recent feed
    
    for q in quotes:
        with st.container():
            st.markdown(f"""
            <div class="highlight-card">
                <div class="highlight-content">"{q['content']}"</div>
                <div class="highlight-meta">
                    <span class="highlight-title">{q['title']}</span> by {q['author']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action Buttons (Up/Down)
            col1, col2, col3 = st.columns([1, 1, 4])
            if col1.button("⬆️", key=f"up_{q['_id']}"):
                log_interaction(user_data["_id"], q["_id"], "upvote")
                st.rerun()
            if col2.button("⬇️", key=f"down_{q['_id']}"):
                log_interaction(user_data["_id"], q["_id"], "downvote")
                st.rerun()

def render_profile():
    st.title(f"Profile: @{user_data['username']} 🌿")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image(user_data["profile_pic"], width=150)
    with col2:
        st.write(f"**Verified Contributions:** {len(get_user_quotes(user_data['_id']))}")
        st.write(f"**Total Reputation:** ⬆️ {user_data.get('total_upvotes_received', 0)} | ⬇️ {user_data.get('total_downvotes_received', 0)}")

    st.write("---")
    st.write("### Your Contributions")
    my_quotes = get_user_quotes(user_data["_id"])
    for q in my_quotes:
        st.markdown(f"""
        <div class="highlight-card">
            <div class="highlight-content">"{q['content']}"</div>
            <div class="highlight-meta">
                <span class="highlight-title">{q['title']}</span> by {q['author']}
                • {q['created_at'].strftime('%Y-%m-%d')} 
                • ⬆️ {q.get('upvotes', 0)} ⬇️ {q.get('downvotes', 0)}
            </div>
        </div>
        """, unsafe_allow_html=True)

# Main Router
if page == "Feed":
    render_feed()
else:
    render_profile()
