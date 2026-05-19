import streamlit as st

st.set_page_config(page_title="OAuth Minimal Test")

st.title("Minimal Google Login Test")
st.write("This is a clean, isolated environment to test Streamlit's native Google OAuth.")

# Simple dictionary check to see if user is logged in
if not st.user:
    st.warning("You are currently logged out.")
    if st.button("Log in with Google"):
        st.login("google")
else:
    st.success("You are successfully logged in!")
    
    st.subheader("Your Google Profile Data:")
    st.write(st.user)
    
    if st.button("Log out"):
        st.logout()
