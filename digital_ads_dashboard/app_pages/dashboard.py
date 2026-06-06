import os
import streamlit as st
import pandas as pd
from datetime import timedelta

conn = st.connection("snowflake")

@st.cache_data
def load_data():
    df = conn.query("SELECT * FROM IMPROVADO.DIGITAL_ADS.BASE_ADS ORDER BY DATE")
    df["DATE"] = pd.to_datetime(df["DATE"])
    return df


def clear_cache():
    load_data.clear()


df = load_data()

st.button("Refresh Data", on_click=clear_cache)

with st.container(horizontal=True):
    platform_filter = st.selectbox(
        "Platform", options=["All"] + sorted(df["PLATFORM"].unique().tolist()), index=0
    )
    date_range = st.date_input(
        "Date Range",
        value=(df["DATE"].min().date(), df["DATE"].max().date()),
        min_value=df["DATE"].min().date(),
        max_value=df["DATE"].max().date(),
    )

filtered = df[df["PLATFORM"] == platform_filter].copy() if platform_filter != "All" else df.copy()
filtered = filtered[
    (filtered["DATE"].dt.date >= date_range[0])
    & (filtered["DATE"].dt.date <= date_range[1])
]

date_span = (date_range[1] - date_range[0]).days
prev_start = date_range[0] - timedelta(days=date_span + 1)
prev_end = date_range[0] - timedelta(days=1)
prev_period = df[df["PLATFORM"] == platform_filter].copy() if platform_filter != "All" else df.copy()
prev_period = prev_period[
    (prev_period["DATE"].dt.date >= prev_start)
    & (prev_period["DATE"].dt.date <= prev_end)
]


def pct_delta(current, previous):
    if previous == 0:
        return None
    return f"{((current - previous) / previous * 100):+.0f}%"


def format_number(val):
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    elif val >= 1_000:
        return f"{val / 1_000:.0f}K"
    return f"{val:,.0f}"


curr_cost = filtered["SPEND"].sum()
curr_impressions = filtered["IMPRESSIONS"].sum()
curr_cpm = curr_cost / curr_impressions * 1000 if curr_impressions > 0 else 0
curr_clicks = filtered["CLICKS"].sum()
curr_ctr = curr_clicks / curr_impressions * 100 if curr_impressions > 0 else 0
curr_cpc = curr_cost / curr_clicks if curr_clicks > 0 else 0
curr_conversions = filtered["CONVERSIONS"].sum()
curr_conv_rate = curr_conversions / curr_clicks * 100 if curr_clicks > 0 else 0
curr_cost_conv = curr_cost / curr_conversions if curr_conversions > 0 else 0

prev_cost = prev_period["SPEND"].sum()
prev_impressions = prev_period["IMPRESSIONS"].sum()
prev_cpm = prev_cost / prev_impressions * 1000 if prev_impressions > 0 else 0
prev_clicks = prev_period["CLICKS"].sum()
prev_ctr = prev_clicks / prev_impressions * 100 if prev_impressions > 0 else 0
prev_cpc = prev_cost / prev_clicks if prev_clicks > 0 else 0
prev_conversions = prev_period["CONVERSIONS"].sum()
prev_conv_rate = prev_conversions / prev_clicks * 100 if prev_conversions > 0 else 0
prev_cost_conv = prev_cost / prev_conversions if prev_conversions > 0 else 0

daily_spend = filtered.groupby("DATE")["SPEND"].sum().tolist()
daily_impressions = filtered.groupby("DATE")["IMPRESSIONS"].sum().tolist()
daily_clicks = filtered.groupby("DATE")["CLICKS"].sum().tolist()
daily_conversions = filtered.groupby("DATE")["CONVERSIONS"].sum().tolist()

kpi1, kpi2, kpi3 = st.columns(3)

with kpi1:
    with st.container(border=True):
        st.caption("COST & IMPRESSIONS")
        with st.container(horizontal=True):
            st.metric("Cost", f"${curr_cost:,.0f}", pct_delta(curr_cost, prev_cost), border=True)
            st.metric("CPM", f"${curr_cpm:.2f}", pct_delta(curr_cpm, prev_cpm), border=True)
            st.metric("Impressions", format_number(curr_impressions), pct_delta(curr_impressions, prev_impressions), border=True)

with kpi2:
    with st.container(border=True):
        st.caption("CLICKS")
        with st.container(horizontal=True):
            st.metric("Clicks", format_number(curr_clicks), pct_delta(curr_clicks, prev_clicks), border=True)
            st.metric("CTR", f"{curr_ctr:.2f}%", pct_delta(curr_ctr, prev_ctr), border=True)
            st.metric("CPC", f"${curr_cpc:.2f}", pct_delta(curr_cpc, prev_cpc), border=True)

with kpi3:
    with st.container(border=True):
        st.caption("CONVERSIONS")
        with st.container(horizontal=True):
            st.metric("Conversions", format_number(curr_conversions), pct_delta(curr_conversions, prev_conversions), border=True)
            st.metric("Conv Rate", f"{curr_conv_rate:.2f}%", pct_delta(curr_conv_rate, prev_conv_rate), border=True)
            st.metric("Cost/Conv", f"${curr_cost_conv:.2f}", pct_delta(curr_cost_conv, prev_cost_conv), border=True)

left_col, right_col = st.columns(2)

with left_col:
    with st.container(border=True):
        st.subheader("Top Campaigns")
        campaign_table = (
            filtered.groupby(["PLATFORM", "CAMPAIGN_NAME"])
            .agg(Cost=("SPEND", "sum"), CPM=("CPM", "mean"), CTR=("CTR", "mean"), Conversions=("CONVERSIONS", "sum"), Cost_Conv=("COST_PER_CONVERSION", "mean"))
            .reset_index().sort_values("Cost", ascending=False)
        )
        campaign_table = campaign_table.rename(columns={"CAMPAIGN_NAME": "Campaign", "PLATFORM": "Platform", "Cost_Conv": "Cost/Conv"})

        def color_scale(series, reverse=False):
            if series.max() == series.min():
                return [""] * len(series)
            norm = (series - series.min()) / (series.max() - series.min())
            if reverse:
                norm = 1 - norm
            colors = []
            for v in norm:
                if v < 0.5:
                    r, g = int(255), int(255 * v * 2)
                else:
                    r, g = int(255 * (1 - v) * 2), int(255)
                colors.append(f"background-color: rgb({r},{g},80); color: black")
            return colors

        styled = (
            campaign_table.style
            .apply(lambda s: color_scale(s, reverse=False), subset=["CTR"])
            .apply(lambda s: color_scale(s, reverse=False), subset=["Conversions"])
            .apply(lambda s: color_scale(s, reverse=True), subset=["CPM"])
            .apply(lambda s: color_scale(s, reverse=True), subset=["Cost/Conv"])
            .format({"Cost": "${:,.0f}", "CPM": "${:.2f}", "CTR": "{:.2f}%", "Cost/Conv": "${:.2f}", "Conversions": "{:,.0f}"})
        )
        st.dataframe(styled, hide_index=True, use_container_width=True)

with right_col:
    with st.container(border=True):
        st.subheader("Daily Performance")
        daily_perf = filtered.groupby("DATE").agg(Cost=("SPEND", "sum"), Conversions=("CONVERSIONS", "sum")).reset_index()
        daily_perf["Cost/Conv"] = (daily_perf["Cost"] / daily_perf["Conversions"].replace(0, pd.NA)).round(2)
        tab1, tab2 = st.tabs(["Cost & Cost/Conv", "Conversions"])
        with tab1:
            st.bar_chart(daily_perf, x="DATE", y="Cost")
            st.line_chart(daily_perf, x="DATE", y="Cost/Conv")
        with tab2:
            st.bar_chart(daily_perf, x="DATE", y="Conversions")

with st.container(border=True):
    st.subheader("Business Insights Summary")
    platform_agg = (
        filtered.groupby("PLATFORM")
        .agg(Spend=("SPEND", "sum"), Impressions=("IMPRESSIONS", "sum"), Clicks=("CLICKS", "sum"), Conversions=("CONVERSIONS", "sum"))
        .reset_index()
    )
    platform_agg["CTR"] = (platform_agg["Clicks"] / platform_agg["Impressions"] * 100).round(2)
    platform_agg["CPC"] = (platform_agg["Spend"] / platform_agg["Clicks"]).round(2)
    platform_agg["Cost_per_Conv"] = (platform_agg["Spend"] / platform_agg["Conversions"].replace(0, pd.NA)).round(2)
    platform_agg["Conv_Rate"] = (platform_agg["Conversions"] / platform_agg["Clicks"] * 100).round(2)
    campaign_agg = (
        filtered.groupby(["PLATFORM", "CAMPAIGN_NAME"])
        .agg(Spend=("SPEND", "sum"), Conversions=("CONVERSIONS", "sum"), Clicks=("CLICKS", "sum"))
        .reset_index()
    )
    campaign_agg["Cost_per_Conv"] = (campaign_agg["Spend"] / campaign_agg["Conversions"].replace(0, pd.NA)).round(2)
    best_campaign = campaign_agg.loc[campaign_agg["Cost_per_Conv"].idxmin()]
    worst_campaign = campaign_agg.loc[campaign_agg["Cost_per_Conv"].idxmax()]
    total_spend = filtered["SPEND"].sum()
    total_conversions = filtered["CONVERSIONS"].sum()
    overall_cost_conv = total_spend / total_conversions if total_conversions > 0 else 0
    insights = [
        f"Overall Performance: Total spend of {total_spend:,.0f} generated {total_conversions:,.0f} conversions at an average cost of {overall_cost_conv:.2f} per conversion.",
        f"Best Performing Campaign: {best_campaign['CAMPAIGN_NAME']} ({best_campaign['PLATFORM']}) — lowest cost per conversion at {best_campaign['Cost_per_Conv']:.2f}.",
        f"Needs Optimization: {worst_campaign['CAMPAIGN_NAME']} ({worst_campaign['PLATFORM']}) — highest cost per conversion at {worst_campaign['Cost_per_Conv']:.2f}.",
    ]
    if prev_cost > 0:
        spend_change = (curr_cost - prev_cost) / prev_cost * 100
        conv_change = (curr_conversions - prev_conversions) / prev_conversions * 100 if prev_conversions > 0 else 0
        if spend_change > 0 and conv_change < spend_change:
            insights.append(f"Efficiency Alert: Spend increased {spend_change:+.0f}% vs prior period but conversions only grew {conv_change:+.0f}% — review budget scaling strategy.")
    for insight in insights:
        st.write(f"• {insight}")