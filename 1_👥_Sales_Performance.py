import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils import (
    load_data, inject_css, render_metric_card, render_section,
    get_date_range, filter_by_date, get_previous_period, calc_delta_pct,
    format_number, COLORS, STATUS_LABELS, STATUS_COLORS
)

st.set_page_config(page_title="Sales Performance", page_icon="👥", layout="wide")
inject_css(st)

@st.cache_data(ttl=300)
def get_data():
    return load_data()

data = get_data()
prospects = data["prospects"]
progress = data["progress"]

# ─── Sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 20px 0 10px 0;">
        <div style="font-size: 24px; font-weight: 800; font-family: 'DM Sans'; color: white;">
            👥 Sales Performance
        </div>
    </div>
    <hr style="border-color: rgba(255,255,255,0.1);">
    """, unsafe_allow_html=True)

    time_filter = st.selectbox(
        "📅 PERIODE",
        ["Minggu Ini", "Minggu Lalu", "Bulan Ini", "Bulan Lalu", "Tahun Ini", "Lifetime"],
        index=4, key="sp_time"
    )
    start_date, end_date = get_date_range(time_filter)
    prev_start, prev_end = get_previous_period(start_date, end_date)
    st.caption(f"📆 {start_date.strftime('%d %b %Y')} — {end_date.strftime('%d %b %Y')}")

    all_sales = sorted(prospects["sales_name"].dropna().unique())
    selected_sales = st.multiselect("👤 FILTER SALES", all_sales, default=[], key="sp_sales")

df = filter_by_date(prospects, "created_at", start_date, end_date)
df_prev = filter_by_date(prospects, "created_at", prev_start, prev_end)
if selected_sales:
    df = df[df["sales_name"].isin(selected_sales)]
    df_prev = df_prev[df_prev["sales_name"].isin(selected_sales)]

# ─── Header ──────────────────────────────────────────────────────────
st.markdown(f"""
<div class="dashboard-header">
    <h1>👥 Sales Performance Analysis</h1>
    <p>Deep-dive performa sales berdasarkan leads, conversion, dan response time &nbsp;|&nbsp; {time_filter}</p>
</div>
""", unsafe_allow_html=True)

# ─── Sales Summary Table ────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown(render_section("Sales Performance Matrix", "📋"), unsafe_allow_html=True)

sales_stats = df.groupby("sales_name").agg(
    total_leads=("id", "count"),
).reset_index()

# Add status breakdowns
for status_key, status_label in [("cold_leads", "Cold"), ("hot_leads", "Hot"), ("deal", "Deal"), ("handover", "Handover"), ("cancelreject", "Cancel")]:
    status_count = df[df["progress_status"] == status_key].groupby("sales_name")["id"].count().reset_index()
    status_count.columns = ["sales_name", status_label.lower()]
    sales_stats = sales_stats.merge(status_count, on="sales_name", how="left")
    sales_stats[status_label.lower()] = sales_stats[status_label.lower()].fillna(0).astype(int)

# Response time per sales
resp_stats = df[df["response_time_min"].notna() & (df["response_time_min"] >= 0)].groupby("sales_name")["response_time_min"].median().reset_index()
resp_stats.columns = ["sales_name", "median_resp_min"]
sales_stats = sales_stats.merge(resp_stats, on="sales_name", how="left")

# Conversion rate
sales_stats["conv_rate"] = np.where(
    sales_stats["total_leads"] > 0,
    ((sales_stats["handover"]) / sales_stats["total_leads"] * 100).round(1),
    0
)

sales_stats = sales_stats.sort_values("total_leads", ascending=False)

# Display as a styled dataframe
display_df = sales_stats.rename(columns={
    "sales_name": "Sales",
    "total_leads": "Total Leads",
    "cold": "Cold",
    "hot": "Hot",
    "deal": "Deal",
    "handover": "Handover",
    "cancel": "Cancel",
    "median_resp_min": "Resp (min)",
    "conv_rate": "Conv %"
})

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Conv %": st.column_config.ProgressColumn(
            "Conv %", format="%.1f%%", min_value=0, max_value=20
        ),
        "Resp (min)": st.column_config.NumberColumn("Resp (min)", format="%.0f"),
    },
    height=400
)
st.markdown('</div>', unsafe_allow_html=True)

# ─── Charts Row ──────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Leads Distribution by Sales", "📊"), unsafe_allow_html=True)

    top_sales = sales_stats.head(10)
    fig_bar = go.Figure()

    for status, color in [("cold", "#95A5A6"), ("hot", "#E67E22"), ("deal", "#27AE60"), ("handover", "#2ECC71"), ("cancel", "#E74C3C")]:
        if status in top_sales.columns:
            fig_bar.add_trace(go.Bar(
                x=top_sales["sales_name"],
                y=top_sales[status],
                name=status.capitalize(),
                marker_color=color,
                hovertemplate="%{x}: %{y}<extra></extra>"
            ))

    fig_bar.update_layout(
        barmode="stack",
        height=380, margin=dict(l=0, r=0, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1, font=dict(size=10, family="DM Sans")),
        xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#F0F0F0", title="Count"),
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_bar, use_container_width=True, key="sales_dist")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Response Time Comparison", "⏱️"), unsafe_allow_html=True)

    valid_resp = df[df["response_time_min"].notna() & (df["response_time_min"] >= 0) & (df["response_time_min"] <= 1440)]

    if len(valid_resp) > 0:
        fig_box = px.box(
            valid_resp, x="sales_name", y="response_time_min",
            color_discrete_sequence=[COLORS["secondary"]],
            labels={"response_time_min": "Response Time (min)", "sales_name": "Sales"},
        )
        fig_box.update_layout(
            height=380, margin=dict(l=0, r=0, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
            yaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
            font=dict(family="DM Sans"),
            showlegend=False,
        )
        st.plotly_chart(fig_box, use_container_width=True, key="resp_box")
    else:
        st.info("Tidak ada data response time.")

    st.markdown('</div>', unsafe_allow_html=True)

# ─── Monthly Performance per Sales ───────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown(render_section("Monthly Leads Trend per Sales", "📈"), unsafe_allow_html=True)

monthly_sales = df.groupby([df["created_at"].dt.to_period("M").astype(str), "sales_name"])["id"].count().reset_index()
monthly_sales.columns = ["month", "sales_name", "leads"]

fig_lines = px.line(
    monthly_sales, x="month", y="leads", color="sales_name",
    markers=True,
    color_discrete_sequence=COLORS["chart"],
    labels={"leads": "Leads", "month": "Month", "sales_name": "Sales"},
)
fig_lines.update_layout(
    height=350, margin=dict(l=0, r=0, t=10, b=10),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", y=-0.2, font=dict(size=10, family="DM Sans")),
    xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
    yaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
    font=dict(family="DM Sans"),
)
st.plotly_chart(fig_lines, use_container_width=True, key="monthly_sales_trend")
st.markdown('</div>', unsafe_allow_html=True)
