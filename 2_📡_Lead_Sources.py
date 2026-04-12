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
    format_number, COLORS, STATUS_LABELS
)

st.set_page_config(page_title="Lead Sources", page_icon="📡", layout="wide")
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
            📡 Lead Sources
        </div>
    </div>
    <hr style="border-color: rgba(255,255,255,0.1);">
    """, unsafe_allow_html=True)

    time_filter = st.selectbox(
        "📅 PERIODE",
        ["Minggu Ini", "Minggu Lalu", "Bulan Ini", "Bulan Lalu", "Tahun Ini", "Lifetime"],
        index=4, key="ls_time"
    )
    start_date, end_date = get_date_range(time_filter)
    prev_start, prev_end = get_previous_period(start_date, end_date)
    st.caption(f"📆 {start_date.strftime('%d %b %Y')} — {end_date.strftime('%d %b %Y')}")

df = filter_by_date(prospects, "created_at", start_date, end_date)
df_prev = filter_by_date(prospects, "created_at", prev_start, prev_end)

# ─── Header ──────────────────────────────────────────────────────────
st.markdown(f"""
<div class="dashboard-header">
    <h1>📡 Lead Sources & Conversion Analysis</h1>
    <p>Analisis efektivitas sumber lead dan conversion rate per channel &nbsp;|&nbsp; {time_filter}</p>
</div>
""", unsafe_allow_html=True)

# ─── Source KPIs ─────────────────────────────────────────────────────
source_stats = df.groupby("source_label").agg(
    leads=("id", "count"),
).reset_index()

# Deal+Handover per source
deal_ho = df[df["progress_status"].isin(["deal", "handover"])]
deals_per_source = deal_ho.groupby("source_label")["id"].count().reset_index()
deals_per_source.columns = ["source_label", "deals"]
source_stats = source_stats.merge(deals_per_source, on="source_label", how="left")
source_stats["deals"] = source_stats["deals"].fillna(0).astype(int)
source_stats["conversion"] = np.where(
    source_stats["leads"] > 0,
    (source_stats["deals"] / source_stats["leads"] * 100).round(1), 0
)
source_stats = source_stats.sort_values("leads", ascending=False)

# Top source
top_source = source_stats.iloc[0] if len(source_stats) > 0 else None
total_sources = source_stats["source_label"].nunique()
best_conv_source = source_stats[source_stats["leads"] >= 10].sort_values("conversion", ascending=False)
best_conv = best_conv_source.iloc[0] if len(best_conv_source) > 0 else None

cols = st.columns(4)
with cols[0]:
    st.markdown(render_metric_card("Total Sources", str(total_sources)), unsafe_allow_html=True)
with cols[1]:
    st.markdown(render_metric_card("Top Source", top_source["source_label"][:25] if top_source is not None else "-"), unsafe_allow_html=True)
    if top_source is not None:
        st.markdown(f"<div style='text-align:center; font-size:12px; color:#2E86DE; margin-top:-8px;'>{int(top_source['leads'])} leads</div>", unsafe_allow_html=True)
with cols[2]:
    st.markdown(render_metric_card("Best Conversion", best_conv["source_label"][:25] if best_conv is not None else "-"), unsafe_allow_html=True)
    if best_conv is not None:
        st.markdown(f"<div style='text-align:center; font-size:12px; color:#27AE60; margin-top:-8px;'>{best_conv['conversion']}%</div>", unsafe_allow_html=True)
with cols[3]:
    avg_conv = source_stats[source_stats["leads"] >= 10]["conversion"].mean() if len(source_stats[source_stats["leads"] >= 10]) > 0 else 0
    st.markdown(render_metric_card("Avg Conversion", f"{avg_conv:.1f}%"), unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# ─── Charts ──────────────────────────────────────────────────────────
col_tree, col_conv = st.columns([5, 5])

with col_tree:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Lead Distribution by Source", "🗺️"), unsafe_allow_html=True)

    # Determine OL vs OF category from options
    options = data["options"]
    source_category = options[options["kind"] == "referrer_source_prospect"][["key", "category"]].drop_duplicates()
    source_cat_map = dict(zip(source_category["key"], source_category["category"]))

    df_with_cat = df.copy()
    df_with_cat["source_category"] = df_with_cat["referrer_source"].map(source_cat_map).fillna("other")
    df_with_cat["source_category"] = df_with_cat["source_category"].map({"online": "Online", "offline": "Offline"}).fillna("Other")

    cat_source = df_with_cat.groupby(["source_category", "source_label"])["id"].count().reset_index()
    cat_source.columns = ["category", "source", "leads"]
    cat_source = cat_source.sort_values("leads", ascending=False)

    if len(cat_source) > 0:
        fig_tree = px.treemap(
            cat_source, path=["category", "source"], values="leads",
            color="leads",
            color_continuous_scale=["#E8F4FD", "#2E86DE", "#1B2A4A"],
        )
        fig_tree.update_layout(
            height=400, margin=dict(l=0, r=0, t=10, b=10),
            font=dict(family="DM Sans"),
            coloraxis_showscale=False,
        )
        fig_tree.update_traces(
            textfont=dict(size=12, family="DM Sans"),
            hovertemplate="<b>%{label}</b><br>Leads: %{value}<extra></extra>"
        )
        st.plotly_chart(fig_tree, use_container_width=True, key="treemap")

    st.markdown('</div>', unsafe_allow_html=True)

with col_conv:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Conversion Rate by Source", "🎯"), unsafe_allow_html=True)

    # Only sources with >= 10 leads
    sig_sources = source_stats[source_stats["leads"] >= 10].sort_values("conversion", ascending=True)

    if len(sig_sources) > 0:
        colors = [COLORS["success"] if c >= 5 else COLORS["warning"] if c >= 2 else COLORS["danger"] for c in sig_sources["conversion"]]

        fig_conv = go.Figure()
        fig_conv.add_trace(go.Bar(
            y=sig_sources["source_label"],
            x=sig_sources["conversion"],
            orientation="h",
            marker_color=colors,
            text=[f"{c}% ({d})" for c, d in zip(sig_sources["conversion"], sig_sources["deals"])],
            textposition="auto",
            hovertemplate="%{y}: %{x:.1f}% conversion<extra></extra>",
            showlegend=False,
        ))
        fig_conv.update_layout(
            height=400, margin=dict(l=0, r=20, t=10, b=10),
            xaxis=dict(title="Conversion Rate %", showgrid=True, gridcolor="#F0F0F0"),
            yaxis=dict(tickfont=dict(size=10, family="DM Sans")),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_conv, use_container_width=True, key="conv_source")
    else:
        st.info("Tidak cukup data untuk analisis conversion.")

    st.markdown('</div>', unsafe_allow_html=True)


# ─── Monthly Source Trend ────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown(render_section("Monthly Leads by Source", "📅"), unsafe_allow_html=True)

top_5_sources = source_stats.head(5)["source_label"].tolist()
df_top = df[df["source_label"].isin(top_5_sources)].copy()

monthly_src = df_top.groupby([df_top["created_at"].dt.to_period("M").astype(str), "source_label"])["id"].count().reset_index()
monthly_src.columns = ["month", "source", "leads"]

fig_area = px.area(
    monthly_src, x="month", y="leads", color="source",
    color_discrete_sequence=COLORS["chart"],
    labels={"leads": "Leads", "month": "Month", "source": "Source"},
)
fig_area.update_layout(
    height=350, margin=dict(l=0, r=0, t=10, b=10),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", y=-0.2, font=dict(size=10, family="DM Sans")),
    xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
    yaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
    font=dict(family="DM Sans"),
)
st.plotly_chart(fig_area, use_container_width=True, key="monthly_source")
st.markdown('</div>', unsafe_allow_html=True)

# ─── Online vs Offline Comparison ────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown(render_section("Online vs Offline Performance", "🌐"), unsafe_allow_html=True)

col_ol, col_of = st.columns(2)

ol_leads = len(df_with_cat[df_with_cat["source_category"] == "Online"])
of_leads = len(df_with_cat[df_with_cat["source_category"] == "Offline"])
total = ol_leads + of_leads

with col_ol:
    ol_pct = round(ol_leads / total * 100, 1) if total > 0 else 0
    ol_deals = len(df_with_cat[(df_with_cat["source_category"] == "Online") & (df_with_cat["progress_status"].isin(["deal", "handover"]))])
    ol_conv = round(ol_deals / ol_leads * 100, 1) if ol_leads > 0 else 0

    st.markdown(f"""
    <div style="padding: 20px; background: linear-gradient(135deg, #EBF5FB, #D6EAF8); border-radius: 16px; text-align: center;">
        <div style="font-size: 14px; font-weight: 600; color: #2E86DE; font-family: 'DM Sans'; text-transform: uppercase;">🌐 Online</div>
        <div style="font-size: 36px; font-weight: 800; color: #1B2A4A; font-family: 'DM Sans';">{format_number(ol_leads)}</div>
        <div style="font-size: 13px; color: #6C757D;">({ol_pct}% of total)</div>
        <div style="margin-top: 10px; font-size: 13px; color: #27AE60; font-weight: 600;">Conv: {ol_conv}% ({ol_deals} deals)</div>
    </div>
    """, unsafe_allow_html=True)

with col_of:
    of_pct = round(of_leads / total * 100, 1) if total > 0 else 0
    of_deals = len(df_with_cat[(df_with_cat["source_category"] == "Offline") & (df_with_cat["progress_status"].isin(["deal", "handover"]))])
    of_conv = round(of_deals / of_leads * 100, 1) if of_leads > 0 else 0

    st.markdown(f"""
    <div style="padding: 20px; background: linear-gradient(135deg, #FEF9E7, #FCF3CF); border-radius: 16px; text-align: center;">
        <div style="font-size: 14px; font-weight: 600; color: #F39C12; font-family: 'DM Sans'; text-transform: uppercase;">🏪 Offline</div>
        <div style="font-size: 36px; font-weight: 800; color: #1B2A4A; font-family: 'DM Sans';">{format_number(of_leads)}</div>
        <div style="font-size: 13px; color: #6C757D;">({of_pct}% of total)</div>
        <div style="margin-top: 10px; font-size: 13px; color: #27AE60; font-weight: 600;">Conv: {of_conv}% ({of_deals} deals)</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
