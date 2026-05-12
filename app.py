import streamlit as st
from database import get_highlights, get_activity_dates, get_local_now
import datetime
import calendar
import subprocess
import os
import sys

st.set_page_config(
    page_title="Readvibe 🌿",
    page_icon="🌿",
    layout="centered"
)

# Launch Bot in background if not already running (Deployment Hack)
@st.cache_resource
def start_bot():
    try:
        # Use sys.executable to ensure we use the same python version
        subprocess.Popen([sys.executable, "bot.py"])
        return True
    except Exception as e:
        return f"Error starting bot: {e}"

bot_status = start_bot()
if bot_status is not True:
    st.error(f"Bot failed to start: {bot_status}")

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

st.title("Readvibe 🌿")
st.write("Your calm space for highlights and thoughts.")

# --- Habit Calendar Section ---
activity = get_activity_dates()
local_now = get_local_now()
today = local_now.date()

# Initialize session state for calendar navigation
if 'cal_month' not in st.session_state:
    st.session_state.cal_month = today.month
if 'cal_year' not in st.session_state:
    st.session_state.cal_year = today.year

# Calendar Navigation Buttons
col1, col2, col3 = st.columns([1, 3, 1])

if col1.button("←", use_container_width=True):
    st.session_state.cal_month -= 1
    if st.session_state.cal_month == 0:
        st.session_state.cal_month = 12
        st.session_state.cal_year -= 1
    st.rerun()

if col2.button("Today 🌿", use_container_width=True):
    st.session_state.cal_month = today.month
    st.session_state.cal_year = today.year
    st.rerun()

if col3.button("→", use_container_width=True):
    st.session_state.cal_month += 1
    if st.session_state.cal_month == 13:
        st.session_state.cal_month = 1
        st.session_state.cal_year += 1
    st.rerun()

view_month = st.session_state.cal_month
view_year = st.session_state.cal_year

# Generate Calendar HTML
cal = calendar.monthcalendar(view_year, view_month)
days_header = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

header_html = "".join([f'<div style="font-weight: bold; color: #5c8d89;">{d}</div>' for d in days_header])

body_html = ""
for week in cal:
    for day in week:
        if day == 0:
            body_html += '<div></div>'
        else:
            date_str = f"{view_year}-{view_month:02d}-{day:02d}"
            is_active = date_str in activity
            class_name = "calendar-day day-active" if is_active else "calendar-day"
            body_html += f'<div class="{class_name}">{day}</div>'

st.markdown(f"""
    <div class="calendar-container">
        <div class="calendar-header">{calendar.month_name[view_month]} {view_year}</div>
        <div class="calendar-grid">
            {header_html}
            {body_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Quote of the Day Section ---
from database import get_random_highlight
featured = get_random_highlight()
if featured:
    st.markdown(f"""
    <div class="featured-card">
        <div class="featured-badge">Featured Reflection</div>
        <div class="featured-content">"{featured['content']}"</div>
        <div style="margin-top: 15px; font-style: italic; color: #8c8c8c;">
            — {featured['title']} by {featured['author']}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.write("Your calm space for highlights and thoughts.")

# --- Search & Filter Section ---
search_query = st.text_input("🔍 Search your highlights...", placeholder="Search by content, author, or #tag")

with st.expander("Add a new highlight manually ✍️"):
    with st.form("manual_entry"):
        new_content = st.text_area("Content")
        col1, col2 = st.columns(2)
        new_title = col1.text_input("Title", placeholder="e.g. Deep Work")
        new_author = col2.text_input("Author", placeholder="e.g. Cal Newport")
        new_tags = st.text_input("Tags (comma separated)", placeholder="e.g. focus, productivity")
        submit = st.form_submit_button("Save Highlight")
        
        if submit:
            if new_content:
                from database import save_highlight
                tags_list = [t.strip() for t in new_tags.split(',')] if new_tags else []
                save_highlight(new_content, new_title, new_author, tags_list)
                st.success("Saved! ✨")
                st.rerun()
            else:
                st.warning("Please enter some content.")

if st.button("Refresh 🔄"):
    st.rerun()

try:
    highlights = get_highlights(search_query)
    
    if not highlights:
        if search_query:
            st.info(f"No matches found for '{search_query}'.")
        else:
            st.info("No highlights saved yet. Send some to your Telegram bot!")
    else:
        for h in highlights:
            # Prepare tags HTML
            tags_html = ""
            if h.get('tags'):
                tags_html = '<div class="tag-container">' + \
                            ''.join([f'<span class="tag">#{t}</span>' for t in h['tags']]) + \
                            '</div>'
            
            with st.container():
                st.markdown(f"""
                <div class="highlight-card">
                    <div class="highlight-content">"{h['content']}"</div>
                    <div class="highlight-meta">
                        <span class="highlight-title">{h['title']}</span> by {h['author']} 
                        • {h['created_at'].strftime('%Y-%m-%d %H:%M')}
                    </div>
                    {tags_html}
                </div>
                """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Could not connect to database: {e}")
    st.info("Make sure MONGODB_URI is correctly set in your .env file.")
