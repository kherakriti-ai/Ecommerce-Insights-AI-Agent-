import os
import streamlit as st

st.set_page_config(page_title="Digital Ads Dashboard", layout="wide")

page = st.navigation(
    {
        "Overview": [
            st.Page("app_pages/dashboard.py", title="Ads Performance", icon=":material/dashboard:"),
        ],
        "Deep Dive Insights": [
            st.Page("app_pages/google_insights.py", title="Google Insights", icon=":material/insights:"),
            st.Page("app_pages/facebook_insights.py", title="Facebook Insights", icon=":material/insights:"),
            st.Page("app_pages/tiktok_insights.py", title="TikTok Insights", icon=":material/insights:"),
        ],
    },
    position="sidebar",
)

st.title(f"{page.title}")
page.run()
