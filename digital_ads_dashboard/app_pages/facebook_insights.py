import os
import streamlit as st
import pandas as pd

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))


@st.cache_data
def load_facebook():
    df = conn.query("""
        SELECT b.DATE, b.CAMPAIGN_NAME, b.AD_GROUP_NAME,
               b.IMPRESSIONS, b.CLICKS, b.SPEND, b.CONVERSIONS,
               b.VIDEO_VIEWS, b.CTR, b.CPC, b.CPM,
               b.CONVERSION_RATE, b.COST_PER_CONVERSION,
               f.REACH, f.FREQUENCY, f.ENGAGEMENT_RATE
        FROM IMPROVADO.DIGITAL_ADS.BASE_ADS b
        JOIN IMPROVADO.DIGITAL_ADS.FACEBOOK_ADS f
            ON b.DATE = f.DATE AND b.CAMPAIGN_ID = f.CAMPAIGN_ID
        WHERE b.PLATFORM = 'Facebook'
        ORDER BY b.DATE
    """)
    df["DATE"] = pd.to_datetime(df["DATE"])
    return df


df = load_facebook()

campaign_list = sorted(df["CAMPAIGN_NAME"].unique().tolist())
selected = st.multiselect("Filter Campaigns", options=campaign_list, default=campaign_list)
filtered = df[df["CAMPAIGN_NAME"].isin(selected)]

# ── KPIs ──
total_spend = filtered["SPEND"].sum()
total_conversions = filtered["CONVERSIONS"].sum()
total_reach = filtered["REACH"].sum()
total_video_views = filtered["VIDEO_VIEWS"].sum()
avg_cpm = filtered["CPM"].mean()
avg_cpc = filtered["CPC"].mean()
avg_ctr = filtered["CTR"].mean()
avg_freq = filtered["FREQUENCY"].mean()
avg_conv_rate = filtered["CONVERSION_RATE"].mean()
avg_cost_conv = filtered["COST_PER_CONVERSION"].mean()

with st.container(horizontal=True):
    st.metric("Total Spend", f"${total_spend:,.0f}", border=True)
    st.metric("Total Conversions", f"{total_conversions:,.0f}", border=True)
    st.metric("Avg CPM", f"${avg_cpm:.2f}", border=True)
    st.metric("Avg CPC", f"${avg_cpc:.2f}", border=True)
    st.metric("Avg CTR", f"{avg_ctr:.2f}%", border=True)
    st.metric("Avg Frequency", f"{avg_freq:.2f}", border=True)

# ── Campaign Efficiency Table ──
with st.container(border=True):
    st.subheader("Campaign Efficiency")
    camp_agg = (
        filtered.groupby(["CAMPAIGN_NAME", "AD_GROUP_NAME"])
        .agg(
            Spend=("SPEND", "sum"),
            Impressions=("IMPRESSIONS", "sum"),
            Reach=("REACH", "sum"),
            Avg_Frequency=("FREQUENCY", "mean"),
            Video_Views=("VIDEO_VIEWS", "sum"),
            Conversions=("CONVERSIONS", "sum"),
            Avg_CTR=("CTR", "mean"),
            Avg_CPM=("CPM", "mean"),
            Avg_CPC=("CPC", "mean"),
            Avg_Conv_Rate=("CONVERSION_RATE", "mean"),
            Avg_Cost_Conv=("COST_PER_CONVERSION", "mean"),
        )
        .reset_index()
        .sort_values("Spend", ascending=False)
    )
    camp_agg["Video_View_Rate"] = (camp_agg["Video_Views"] / camp_agg["Impressions"] * 100).round(1)
    camp_agg["Conv_per_1K_Reached"] = (camp_agg["Conversions"] / camp_agg["Reach"] * 1000).round(2)
    display = camp_agg.copy()
    display["Spend"] = display["Spend"].apply(lambda x: f"${x:,.0f}")
    display["Avg_CPM"] = display["Avg_CPM"].apply(lambda x: f"${x:.2f}")
    display["Avg_CPC"] = display["Avg_CPC"].apply(lambda x: f"${x:.2f}")
    display["Avg_CTR"] = display["Avg_CTR"].apply(lambda x: f"{x:.2f}%")
    display["Avg_Conv_Rate"] = display["Avg_Conv_Rate"].apply(lambda x: f"{x:.2f}%")
    display["Avg_Cost_Conv"] = display["Avg_Cost_Conv"].apply(lambda x: f"${x:.2f}")
    display["Avg_Frequency"] = display["Avg_Frequency"].apply(lambda x: f"{x:.2f}")
    display["Video_View_Rate"] = display["Video_View_Rate"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(display.rename(columns={
        "CAMPAIGN_NAME": "Campaign", "AD_GROUP_NAME": "Ad Set",
        "Avg_CTR": "CTR", "Avg_CPM": "CPM", "Avg_CPC": "CPC",
        "Avg_Conv_Rate": "Conv Rate", "Avg_Cost_Conv": "Cost/Conv",
        "Avg_Frequency": "Frequency", "Video_View_Rate": "VV Rate",
        "Conv_per_1K_Reached": "Conv/1K Reached"
    }), hide_index=True, use_container_width=True)

# ── Charts ──
col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.subheader("Reach & Frequency by Campaign")
        reach_data = camp_agg[["CAMPAIGN_NAME", "Reach", "Avg_Frequency"]].copy()
        st.bar_chart(reach_data, x="CAMPAIGN_NAME", y="Reach")
        st.caption("Avg Frequency: " + " | ".join([f"{r['CAMPAIGN_NAME']}: {r['Avg_Frequency']:.2f}" for _, r in reach_data.iterrows()]))

with col2:
    with st.container(border=True):
        st.subheader("Video View Rate by Campaign")
        vv_data = camp_agg[["CAMPAIGN_NAME", "Video_View_Rate"]].copy()
        st.bar_chart(vv_data, x="CAMPAIGN_NAME", y="Video_View_Rate")

col3, col4 = st.columns(2)
with col3:
    with st.container(border=True):
        st.subheader("Spend vs Conversions")
        st.scatter_chart(camp_agg, x="Spend", y="Conversions", color="CAMPAIGN_NAME")

with col4:
    with st.container(border=True):
        st.subheader("Daily Spend & Video Views")
        daily = filtered.groupby("DATE").agg(Spend=("SPEND", "sum"), Video_Views=("VIDEO_VIEWS", "sum")).reset_index()
        st.bar_chart(daily, x="DATE", y="Spend")

# ── Key Insights ──
with st.container(border=True):
    st.subheader("Key Insights")
    st.markdown("""
- **Conversions Retargeting is the most efficient campaign** — Cart Abandoners delivers the lowest cost per conversion (\$5.97), highest CTR (4.62%), highest conversion rate (6.26%), and 3.68 conversions per 1,000 people reached. Deserves a larger budget share.
- **Video Views Campaign is an untapped awareness asset** — Achieves 67.4% video view rate at only \$1.29 CPM, reaching 1.44M unique users on just 12% of budget. It feeds the retargeting pool at minimal cost.
- **Brand Awareness CPM inefficiency** — Broad Audience 18-35 pays \$15.62 per 1K video views — 8x more expensive than Video Views Campaign. Budget could work harder if reallocated.
- **Traffic Drive Jan scales efficiently** — Spend grew +20% week-over-week while conversions grew +24%, meaning returns improve as the campaign scales.
- **No ad fatigue detected** — All campaigns hold frequency 1.19–1.27, well below the ~2.0 fatigue threshold. There is headroom to increase reach.
- **Engagement Rate data quality flag** — Facebook's ENGAGEMENT_RATE mirrors CTR exactly across all campaigns. It is not measuring true social engagement (likes, reactions, shares) and should not be used as such.
- **Video Views Campaign super-scales** — In Week 2, spend doubled (+100%) but conversions grew +131%, suggesting video builds downstream intent that converts later.
- **Reach-to-conversion gap** — Retargeting converts 3.68 users per 1K reached vs Brand Awareness (0.36) and Video Views (0.11). Audience intent drives conversions far more than volume.
""")

# ── Action Items ──
with st.container(border=True):
    st.subheader("Action Items for Leadership")
    st.markdown("""
1. **Invest more in Conversions Retargeting** — Converting at 6x the rate of awareness campaigns at the lowest cost per conversion. Fastest way to grow Facebook revenue without new risk.
2. **Grow the Video Views Campaign** — Cheapest top-of-funnel builder (\$1.57 per 1K reached). A bigger video audience today means more retargeting opportunities tomorrow.
3. **Challenge the Brand Awareness budget** — Paying 8x more per video view than the Video Views Campaign. Evaluate whether this budget performs better elsewhere.
4. **Investigate Facebook Engagement Rate data** — The metric reflects only clicks, not true social engagement. Fix before using in any reporting or benchmarking.
5. **Maintain frequency discipline** — Audience frequency is healthy (1.19–1.27). Continue to set frequency caps as budgets scale to protect campaign longevity.
""")
