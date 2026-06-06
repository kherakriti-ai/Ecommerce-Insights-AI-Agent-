import os
import streamlit as st
import pandas as pd

conn = st.connection("snowflake")

@st.cache_data
def load_tiktok():
    df = conn.query("""
        SELECT b.DATE, b.CAMPAIGN_NAME, b.AD_GROUP_NAME,
               b.IMPRESSIONS, b.CLICKS, b.SPEND, b.CONVERSIONS,
               b.VIDEO_VIEWS, b.CTR, b.CPC, b.CPM,
               b.CONVERSION_RATE, b.COST_PER_CONVERSION,
               b.LIKES, b.SHARES, b.COMMENTS, b.ENGAGEMENT_RATE,
               t.VIDEO_WATCH_25, t.VIDEO_WATCH_50,
               t.VIDEO_WATCH_75, t.VIDEO_WATCH_100
        FROM IMPROVADO.DIGITAL_ADS.BASE_ADS b
        JOIN IMPROVADO.DIGITAL_ADS.TIKTOK_ADS t
            ON b.DATE = t.DATE AND b.CAMPAIGN_ID = t.CAMPAIGN_ID
        WHERE b.PLATFORM = 'TikTok'
        ORDER BY b.DATE
    """)
    df["DATE"] = pd.to_datetime(df["DATE"])
    return df


df = load_tiktok()

campaign_list = sorted(df["CAMPAIGN_NAME"].unique().tolist())
selected = st.multiselect("Filter Campaigns", options=campaign_list, default=campaign_list)
filtered = df[df["CAMPAIGN_NAME"].isin(selected)]

# ── KPIs ──
total_spend = filtered["SPEND"].sum()
total_conversions = filtered["CONVERSIONS"].sum()
total_video_views = filtered["VIDEO_VIEWS"].sum()
total_completions = filtered["VIDEO_WATCH_100"].sum()
total_likes = filtered["LIKES"].sum()
total_shares = filtered["SHARES"].sum()
avg_cpm = filtered["CPM"].mean()
avg_ctr = filtered["CTR"].mean()
avg_conv_rate = filtered["CONVERSION_RATE"].mean()
avg_cost_conv = filtered["COST_PER_CONVERSION"].mean()

with st.container(horizontal=True):
    st.metric("Total Spend", f"${total_spend:,.0f}", border=True)
    st.metric("Total Conversions", f"{total_conversions:,.0f}", border=True)
    st.metric("Video Views", f"{total_video_views:,.0f}", border=True)
    st.metric("Completions (100%)", f"{total_completions:,.0f}", border=True)
    st.metric("Total Shares", f"{total_shares:,.0f}", border=True)
    st.metric("Avg CPM", f"${avg_cpm:.2f}", border=True)

# ── Campaign Efficiency Table ──
with st.container(border=True):
    st.subheader("Campaign Efficiency")
    camp_agg = (
        filtered.groupby(["CAMPAIGN_NAME", "AD_GROUP_NAME"])
        .agg(
            Spend=("SPEND", "sum"),
            Impressions=("IMPRESSIONS", "sum"),
            Video_Views=("VIDEO_VIEWS", "sum"),
            Watch_25=("VIDEO_WATCH_25", "sum"),
            Watch_50=("VIDEO_WATCH_50", "sum"),
            Watch_75=("VIDEO_WATCH_75", "sum"),
            Watch_100=("VIDEO_WATCH_100", "sum"),
            Likes=("LIKES", "sum"),
            Shares=("SHARES", "sum"),
            Comments=("COMMENTS", "sum"),
            Conversions=("CONVERSIONS", "sum"),
            Avg_CTR=("CTR", "mean"),
            Avg_CPM=("CPM", "mean"),
            Avg_CPC=("CPC", "mean"),
            Avg_Conv_Rate=("CONVERSION_RATE", "mean"),
            Avg_Cost_Conv=("COST_PER_CONVERSION", "mean"),
            Avg_Engagement=("ENGAGEMENT_RATE", "mean"),
        )
        .reset_index()
        .sort_values("Spend", ascending=False)
    )
    camp_agg["VV_Rate"] = (camp_agg["Video_Views"] / camp_agg["Impressions"] * 100).round(1)
    camp_agg["Completion_Rate"] = (camp_agg["Watch_100"] / camp_agg["Video_Views"] * 100).round(1)
    camp_agg["Cost_per_1k_Completions"] = (camp_agg["Spend"] / camp_agg["Watch_100"] * 1000).round(2)
    display = camp_agg[["CAMPAIGN_NAME", "AD_GROUP_NAME", "Spend", "Conversions",
                         "Avg_CTR", "Avg_CPM", "Avg_Conv_Rate", "Avg_Cost_Conv",
                         "VV_Rate", "Completion_Rate", "Cost_per_1k_Completions",
                         "Avg_Engagement", "Likes", "Shares", "Comments"]].copy()
    display["Spend"] = display["Spend"].apply(lambda x: f"${x:,.0f}")
    display["Avg_CPM"] = display["Avg_CPM"].apply(lambda x: f"${x:.2f}")
    display["Avg_CTR"] = display["Avg_CTR"].apply(lambda x: f"{x:.2f}%")
    display["Avg_Conv_Rate"] = display["Avg_Conv_Rate"].apply(lambda x: f"{x:.2f}%")
    display["Avg_Cost_Conv"] = display["Avg_Cost_Conv"].apply(lambda x: f"${x:.2f}")
    display["VV_Rate"] = display["VV_Rate"].apply(lambda x: f"{x:.1f}%")
    display["Completion_Rate"] = display["Completion_Rate"].apply(lambda x: f"{x:.1f}%")
    display["Cost_per_1k_Completions"] = display["Cost_per_1k_Completions"].apply(lambda x: f"${x:.2f}")
    st.dataframe(display.rename(columns={
        "CAMPAIGN_NAME": "Campaign", "AD_GROUP_NAME": "Ad Group",
        "Avg_CTR": "CTR", "Avg_CPM": "CPM", "Avg_Conv_Rate": "Conv Rate",
        "Avg_Cost_Conv": "Cost/Conv", "VV_Rate": "VV Rate",
        "Completion_Rate": "Completion", "Cost_per_1k_Completions": "Cost/1K Complete",
        "Avg_Engagement": "Engagement Rate"
    }), hide_index=True, use_container_width=True)

# ── Video Watch Funnel ──
with st.container(border=True):
    st.subheader("Video Watch Funnel by Campaign")
    funnel = camp_agg[["CAMPAIGN_NAME", "Video_Views", "Watch_25", "Watch_50", "Watch_75", "Watch_100"]].copy()
    funnel_pct = pd.DataFrame({
        "Campaign": funnel["CAMPAIGN_NAME"],
        "25%": (funnel["Watch_25"] / funnel["Video_Views"] * 100).round(1),
        "50%": (funnel["Watch_50"] / funnel["Video_Views"] * 100).round(1),
        "75%": (funnel["Watch_75"] / funnel["Video_Views"] * 100).round(1),
        "100%": (funnel["Watch_100"] / funnel["Video_Views"] * 100).round(1),
    })
    st.dataframe(funnel_pct, hide_index=True, use_container_width=True)
    funnel_melted = funnel_pct.melt(id_vars="Campaign", var_name="Watch %", value_name="Viewers %")
    st.bar_chart(funnel_melted, x="Watch %", y="Viewers %", color="Campaign")

# ── Social & Charts ──
col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.subheader("Social Engagement")
        social = camp_agg[["CAMPAIGN_NAME", "Likes", "Shares", "Comments"]].copy()
        social_melted = social.melt(id_vars="CAMPAIGN_NAME", var_name="Type", value_name="Count")
        st.bar_chart(social_melted, x="CAMPAIGN_NAME", y="Count", color="Type")

with col2:
    with st.container(border=True):
        st.subheader("Weekly Spend vs Conversions")
        weekly = filtered.copy()
        weekly["WEEK"] = weekly["DATE"].dt.isocalendar().week.astype(int)
        w_agg = weekly.groupby(["CAMPAIGN_NAME", "WEEK"]).agg(Spend=("SPEND", "sum"), Conversions=("CONVERSIONS", "sum")).reset_index()
        st.line_chart(w_agg, x="WEEK", y="Conversions", color="CAMPAIGN_NAME")

# ── Key Insights ──
with st.container(border=True):
    st.subheader("Key Insights")
    st.markdown("""
- **Influencer Collab is the engagement powerhouse** — Creator Partnership achieves the highest engagement rate (7.67%), best video retention (80.8% reach 25%, 30.4% completion), and highest share rate (1.28%) generating 134K organic shares. At only \$0.04 per interaction, creator content drives unmatched organic amplification.
- **Conversion Focus is the revenue driver** — Product Demo has the highest conversion rate (2.72%) and \$10.00 cost per conversion despite 27% less spend than Influencer Collab. Its CTA fires before the video mid-point where most viewers drop off.
- **Awareness GenZ has a critical mid-video drop** — Dance Challenge loses 29% of viewers between the 25% and 50% mark. Strong hook, weak second act. A shorter, re-edited version would recover completions.
- **Traffic Campaign is the most cost-efficient scaler** — Cheapest CPM (\$1.90) and the only campaign where conversion growth (+35%) outpaced spend growth (+32%). Best used as a top-of-funnel feeder, not a standalone conversion tool.
- **TikTok Shares are an organic amplifier** — 134K shares from Influencer Collab and 78K from Awareness GenZ represent earned distribution at zero extra cost. True ROI is significantly understated by paid metrics alone.
- **Video completion ≠ conversion** — Influencer Collab completes most (30.4%) but converts worst (1.55%). Conversion Focus completes less (25.3%) but converts best (2.72%). CTA placement and post-click experience matter more than watch time.
- **All campaigns scale linearly** — Every TikTok campaign shows spend-to-conversion parity under 3% gap week-over-week. The algorithm is stable — scaling budgets will return proportional results.
""")

# ── Action Items ──
with st.container(border=True):
    st.subheader("Action Items for Leadership")
    st.markdown("""
1. **Scale Conversion Focus** — Best conversion rate (2.72%), predictable returns, and scales efficiently. Our most reliable TikTok revenue driver deserves more budget.
2. **Double down on Influencer Collab** — Generated 134K organic shares this month. Every share is free distribution. The true ROI is larger than paid metrics show.
3. **Fix the mid-video drop on Awareness GenZ** — The second quarter of the video is losing viewers. A shorter re-edit could recover completions and improve downstream conversions.
4. **Reposition Traffic Campaign as a funnel feeder** — Cheapest reach but lowest conversion intent. Measure it on audience building and reach, not direct revenue.
5. **Increase overall TikTok investment** — Unlike Google where more spend didn't return more results, every TikTok campaign scales linearly. Low-risk channel to grow total budget allocation.
""")
