import os
import streamlit as st
import pandas as pd

conn = st.connection("snowflake")

@st.cache_data
def load_google_base():
    return conn.query("""
        SELECT b.*,
               g.SEARCH_IMPRESSION_SHARE,
               g.AVG_CPC AS SOURCE_AVG_CPC
        FROM IMPROVADO.DIGITAL_ADS.BASE_ADS b
        JOIN IMPROVADO.DIGITAL_ADS.GOOGLE_ADS g ON b.DATE = g.DATE AND b.CAMPAIGN_ID = g.CAMPAIGN_ID
        WHERE b.PLATFORM = 'Google'
        ORDER BY b.DATE
    """)


def clear_google_cache():
    load_google_base.clear()


df = load_google_base()
df["DATE"] = pd.to_datetime(df["DATE"])

st.button("Refresh", on_click=clear_google_cache)

CAMPAIGN_COLORS = {
    "Search Brand Terms": "#1f77b4",
    "Search Generic Terms": "#ff7f0e",
    "Shopping All Products": "#2ca02c",
    "Display Remarketing": "#9467bd",
}

# ─────────────────────────────────────────────
# KPI SUMMARY
# ─────────────────────────────────────────────
st.subheader("Google Ads — KPI Summary")

campaign_summary = (
    df.groupby("CAMPAIGN_NAME")
    .agg(
        Spend=("SPEND", "sum"),
        Impressions=("IMPRESSIONS", "sum"),
        Clicks=("CLICKS", "sum"),
        Conversions=("CONVERSIONS", "sum"),
        Conv_Value=("CONVERSION_VALUE", "sum"),
    )
    .reset_index()
)
campaign_summary["ROAS"] = (campaign_summary["Conv_Value"] / campaign_summary["Spend"]).round(2)
campaign_summary["Cost_per_Conv"] = (campaign_summary["Spend"] / campaign_summary["Conversions"]).round(2)
campaign_summary["Spend_Share"] = (campaign_summary["Spend"] / campaign_summary["Spend"].sum() * 100).round(1)

with st.container(horizontal=True):
    st.metric("Total Spend", f"${df['SPEND'].sum():,.0f}", border=True)
    st.metric("Total Conv Value", f"${df['CONVERSION_VALUE'].sum():,.0f}", border=True)
    st.metric("Overall ROAS", f"{df['CONVERSION_VALUE'].sum() / df['SPEND'].sum():.2f}x", border=True)
    st.metric("Avg Cost/Conv", f"${df['SPEND'].sum() / df['CONVERSIONS'].sum():.2f}", border=True)

# ─────────────────────────────────────────────
# BUDGET ALLOCATION vs ROAS
# ─────────────────────────────────────────────
st.subheader("Budget Allocation vs ROAS")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("**Spend Share by Campaign**")
        st.bar_chart(campaign_summary, x="CAMPAIGN_NAME", y="Spend_Share")

with col2:
    with st.container(border=True):
        st.markdown("**ROAS by Campaign**")
        st.bar_chart(campaign_summary, x="CAMPAIGN_NAME", y="ROAS")

with st.container(border=True):
    st.markdown("**Campaign Efficiency Table** — ROAS, Cost/Conv, Impression Share, Quality Score")
    eff = (
        df.groupby("CAMPAIGN_NAME")
        .agg(
            Spend=("SPEND", "sum"),
            Conv_Value=("CONVERSION_VALUE", "sum"),
            Conversions=("CONVERSIONS", "sum"),
            Avg_CTR=("CTR", "mean"),
            Avg_CPC=("CPC", "mean"),
            Avg_CPM=("CPM", "mean"),
            Avg_QS=("QUALITY_SCORE", "mean"),
            Avg_ImpShare=("SEARCH_IMPRESSION_SHARE", "mean"),
        )
        .reset_index()
    )
    eff["ROAS"] = (eff["Conv_Value"] / eff["Spend"]).round(2)
    eff["Cost_per_Conv"] = (eff["Spend"] / eff["Conversions"]).round(2)
    eff["Avg_ImpShare"] = (eff["Avg_ImpShare"] * 100).round(1)
    eff["Avg_CTR"] = eff["Avg_CTR"].round(2)
    eff["Avg_CPC"] = eff["Avg_CPC"].round(2)
    eff["Avg_CPM"] = eff["Avg_CPM"].round(2)
    eff["Avg_QS"] = eff["Avg_QS"].round(1)
    eff = eff.sort_values("ROAS", ascending=False)
    st.dataframe(eff, hide_index=True, use_container_width=True)

# ─────────────────────────────────────────────
# QUALITY SCORE vs CPC
# ─────────────────────────────────────────────
st.subheader("Quality Score vs CPC — The Efficiency Lever")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("**Quality Score by Campaign**")
        qs_df = eff[["CAMPAIGN_NAME", "Avg_QS"]].sort_values("Avg_QS", ascending=False)
        st.bar_chart(qs_df, x="CAMPAIGN_NAME", y="Avg_QS")
with col2:
    with st.container(border=True):
        st.markdown("**CPC by Campaign** — Higher QS = Lower CPC")
        cpc_df = eff[["CAMPAIGN_NAME", "Avg_CPC"]].sort_values("Avg_CPC")
        st.bar_chart(cpc_df, x="CAMPAIGN_NAME", y="Avg_CPC")

# ─────────────────────────────────────────────
# IMPRESSION SHARE GAP
# ─────────────────────────────────────────────
st.subheader("Impression Share — Missed Opportunity")

imp_df = (
    df.groupby("CAMPAIGN_NAME")
    .agg(Impressions=("IMPRESSIONS", "sum"), Avg_ImpShare=("SEARCH_IMPRESSION_SHARE", "mean"), ROAS=("CONVERSION_VALUE", "sum"))
    .reset_index()
)
spend_map = df.groupby("CAMPAIGN_NAME")["SPEND"].sum()
imp_df["Spend"] = imp_df["CAMPAIGN_NAME"].map(spend_map)
imp_df["ROAS"] = (imp_df["ROAS"] / imp_df["Spend"]).round(2)
imp_df["Captured_Pct"] = (imp_df["Avg_ImpShare"] * 100).round(1)
imp_df["Missed_Pct"] = (100 - imp_df["Captured_Pct"]).round(1)
imp_df["Est_Missed_Impressions"] = ((imp_df["Missed_Pct"] / 100) * imp_df["Impressions"]).round(0).astype(int)

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("**Impression Share Captured (%)**")
        st.bar_chart(imp_df, x="CAMPAIGN_NAME", y="Captured_Pct")
with col2:
    with st.container(border=True):
        st.markdown("**Estimated Missed Impressions**")
        st.bar_chart(imp_df, x="CAMPAIGN_NAME", y="Est_Missed_Impressions")

# ─────────────────────────────────────────────
# WEEKLY PERFORMANCE TREND
# ─────────────────────────────────────────────
st.subheader("Weekly Performance by Campaign")

df["WEEK"] = df["DATE"].dt.isocalendar().week.astype(int)
weekly = (
    df.groupby(["CAMPAIGN_NAME", "WEEK"])
    .agg(Spend=("SPEND", "sum"), Conv_Value=("CONVERSION_VALUE", "sum"), Conversions=("CONVERSIONS", "sum"))
    .reset_index()
)
weekly["ROAS"] = (weekly["Conv_Value"] / weekly["Spend"]).round(2)

tab1, tab2 = st.tabs(["Weekly Spend", "Weekly ROAS"])
with tab1:
    with st.container(border=True):
        st.line_chart(weekly, x="WEEK", y="Spend", color="CAMPAIGN_NAME")
with tab2:
    with st.container(border=True):
        st.line_chart(weekly, x="WEEK", y="ROAS", color="CAMPAIGN_NAME")

# ─────────────────────────────────────────────
# CPM EFFICIENCY
# ─────────────────────────────────────────────
st.subheader("CPM Efficiency — Cost to Reach 1,000 Users")
with st.container(border=True):
    cpm_df = eff[["CAMPAIGN_NAME", "Avg_CPM"]].sort_values("Avg_CPM")
    st.bar_chart(cpm_df, x="CAMPAIGN_NAME", y="Avg_CPM")
    st.caption("Display Remarketing has the lowest CPM ($0.98) — cheapest way to reach users.")

# ─────────────────────────────────────────────
# BUSINESS INSIGHTS & ACTION ITEMS
# ─────────────────────────────────────────────
st.subheader("Business Insights")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("**Key Findings**")
        st.markdown("""
- **Budget misallocation**: Non-Brand Search takes 41% of budget but delivers only **2.0x ROAS** — the worst performer
- **Brand Search is underinvested**: 9.81x ROAS at \$5.10 cost/conversion with QS=9, yet only 19.6% of budget
- **Shopping is the volume engine**: 1,801 conversions, \$90K conversion value, healthy 7.89x ROAS
- **Display punches above its weight**: 5.15x ROAS at only \$0.98 CPM — re-engages high-intent users cheaply
- **Quality Score drives CPC**: Brand (QS=9) pays \$0.19 CPC, Generic (QS~7) pays \$0.64 — 3.4x more expensive
- **Generic has a leaky funnel**: CTR is decent (1.99%) but conversion rate is the lowest (2.60%) — post-click problem
- **2.2M missed Display impressions** at \$0.98 CPM — direct revenue opportunity being left on the table
        """)

with col2:
    with st.container(border=True):
        st.markdown("**Action Items for Leadership**")
        st.markdown("""
1. **Reallocate budget from Non-Brand Search** — shift 15–20% to Brand and Shopping where every dollar returns 4–5x more

2. **Scale Shopping** — room to grow (only 67% impression share captured), conversions scale in lockstep with spend

3. **Fix the Non-Brand Search landing page** — users are clicking but not converting; fix the funnel before spending more

4. **Invest more in Display Remarketing** — only 9% of budget, consistently profitable at the cheapest CPM

5. **Protect Brand Search** — highest ROAS campaign, defends customers we have already earned from competitor bidding
        """)
