import streamlit as st

st.set_page_config(page_title="OAuth Minimal Test")

st.title("Minimal Google Login Test")
st.write("This is a clean, isolated environment to test Streamlit's native Google OAuth.")

# Use get to safely check if they are logged in.
# Streamlit injects "is_logged_in" into the dictionary when secrets are properly configured.
if not st.user.get("is_logged_in", False):
    st.warning("You are currently logged out.")
    if st.button("Log in with Google"):
        st.login("google")
else:
    st.success("You are successfully logged in!")
    
    st.subheader("Your Google Profile Data:")
    st.write(st.user)
    
    if st.button("Log out"):
        st.logout()
