import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    load_data, inject_css, render_metric_card, render_section,
    get_date_range, filter_by_date, get_previous_period, calc_delta_pct,
    format_number, calc_lead_age,
    COLORS, STATUS_ORDER, STATUS_LABELS, STATUS_COLORS, FUNNEL_STAGES
)

# ─── Page Config ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Executive Lead Management System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css(st)

# ─── Load Data ───────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_data():
    return load_data()

data = get_data()
prospects = data["prospects"]
progress = data["progress"]
users = data["users"]

import streamlit as st
import base64

def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

logo_base64 = get_base64_image("qonex_logo.png")  # ganti sesuai nama file logo kamu

# ─── Sidebar ─────────────────────────────────────────────────────────
with st.sidebar:

    st.markdown(f"""
    <div style="padding: 20px 0 10px 0;">
        <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
        ">
            <img src="data:image/png;base64,{logo_base64}" 
                 style="width: 42px; height: 42px; object-fit: contain;">
            
            <div style="text-align: left;">
                <div style="
                    font-size: 28px;
                    font-weight: 800;
                    letter-spacing: -1px;
                    font-family: 'DM Sans', sans-serif;
                    color: white;
                    line-height: 1.1;
                ">
                    Qonex City
                </div>

                <div style="
                    font-size: 12px;
                    color: rgba(255,255,255,0.5);
                    margin-top: 4px;
                ">
                    Lead Management System
                </div>
            </div>
        </div>

        <hr style="border-color: rgba(255,255,255,0.1); margin: 16px 0 20px 0;">
    </div>
    """, unsafe_allow_html=True)

    time_filter = st.selectbox(
        "📅 PERIODE",
        ["Minggu Ini", "Minggu Lalu", "Bulan Ini", "Bulan Lalu", "Tahun Ini", "Lifetime"],
        index=4
    )

    start_date, end_date = get_date_range(time_filter)
    prev_start, prev_end = get_previous_period(start_date, end_date)

    st.caption(f"📆 {start_date.strftime('%d %b %Y')} — {end_date.strftime('%d %b %Y')}")
    st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    # Sales filter
    all_sales = sorted(prospects["sales_name"].dropna().unique())
    selected_sales = st.multiselect("👤 FILTER SALES", all_sales, default=[])

    st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-size: 11px; color: rgba(255,255,255,0.4); text-align: center; padding-top: 10px;">
        Data Snapshot: 10 Apr 2026<br>
        Dashboard v1.0
    </div>
    """, unsafe_allow_html=True)

# ─── Filter Data ─────────────────────────────────────────────────────
df = filter_by_date(prospects, "created_at", start_date, end_date)
df_prev = filter_by_date(prospects, "created_at", prev_start, prev_end)

prog = filter_by_date(progress, "created_at", start_date, end_date)
prog_prev = filter_by_date(progress, "created_at", prev_start, prev_end)

if selected_sales:
    df = df[df["sales_name"].isin(selected_sales)]
    df_prev = df_prev[df_prev["sales_name"].isin(selected_sales)]
    prog = prog[prog["sales_name"].isin(selected_sales)]

# ─── Header ──────────────────────────────────────────────────────────
st.markdown(f"""
<div class="dashboard-header">
    <h1>Executive Lead Management System</h1>
    <p>Qonex City — {time_filter} &nbsp;|&nbsp; Last updated: 10 Apr 2026, 09:25 AM</p>
</div>
""", unsafe_allow_html=True)

# ─── KPI Cards Row ──────────────────────────────────────────────────
total_leads = len(df)
total_leads_prev = len(df_prev)
delta_leads = calc_delta_pct(total_leads, total_leads_prev)

# Cold rate
cold_count = len(df[df["progress_status"] == "cold_leads"])
cold_rate = round(cold_count / total_leads * 100, 1) if total_leads > 0 else 0

# Hot rate
hot_count = len(df[df["progress_status"].isin(["hot_leads"])])
hot_rate = round(hot_count / total_leads * 100, 1) if total_leads > 0 else 0

# Deal count (from progress, status = deal)
deal_prospects = df[df["progress_status"] == "deal"]
deal_count = len(deal_prospects)

# Handover count
handover_prospects = df[df["progress_status"] == "handover"]
handover_count = len(handover_prospects)

# Handover prev
handover_prev = len(df_prev[df_prev["progress_status"] == "handover"])
delta_handover = calc_delta_pct(handover_count, handover_prev)

# Contact rate (has first_contact)
contacted = df[df["first_contact"].notna()]
contact_rate = round(len(contacted) / total_leads * 100, 1) if total_leads > 0 else 0
contacted_prev = df_prev[df_prev["first_contact"].notna()]
contact_rate_prev = round(len(contacted_prev) / total_leads_prev * 100, 1) if total_leads_prev > 0 else 0

# Deal rate
deal_rate = round(deal_count / total_leads * 100, 1) if total_leads > 0 else 0
handover_rate = round(handover_count / total_leads * 100, 1) if total_leads > 0 else 0

cols = st.columns(6)
with cols[0]:
    st.markdown(render_metric_card("Total Leads", format_number(total_leads), delta_leads, "vs prev period"), unsafe_allow_html=True)
with cols[1]:
    st.markdown(render_metric_card("Cold", f"{cold_count}", None, "", prefix=""), unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center; font-size:12px; color:#95A5A6; margin-top:-8px;'>Rate: {cold_rate}%</div>", unsafe_allow_html=True)
with cols[2]:
    st.markdown(render_metric_card("Hot", f"{hot_count}", None, "", prefix=""), unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center; font-size:12px; color:#E67E22; margin-top:-8px;'>Rate: {hot_rate}%</div>", unsafe_allow_html=True)
with cols[3]:
    st.markdown(render_metric_card("Deal", f"{deal_count}", None, "", prefix=""), unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center; font-size:12px; color:#27AE60; margin-top:-8px;'>Rate: {deal_rate}%</div>", unsafe_allow_html=True)
with cols[4]:
    st.markdown(render_metric_card("Handover", f"{handover_count}", delta_handover, "vs prev"), unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center; font-size:12px; color:#2ECC71; margin-top:-8px;'>Rate: {handover_rate}%</div>", unsafe_allow_html=True)
with cols[5]:
    st.markdown(render_metric_card("Contact Rate", f"{contact_rate}%", round(contact_rate - contact_rate_prev, 1), "pp vs prev"), unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# ROW 2: Lead Response Time (moved up) + Lead Funnel
# ═══════════════════════════════════════════════════════════════════════
col_resp, col_funnel = st.columns([4, 5])

with col_resp:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Lead Response Time", "⏱️"), unsafe_allow_html=True)

    resp_toggle = st.radio("Mode", ["Overall", "Per Sales"], horizontal=True, key="resp_mode", label_visibility="collapsed")

    valid_resp = df[df["response_time_min"].notna() & (df["response_time_min"] >= 0)]

    if resp_toggle == "Overall":
        # Bucket response times
        def bucket_resp(minutes):
            if minutes <= 5:
                return "0-5 min"
            elif minutes <= 30:
                return "5-30 min"
            elif minutes <= 60:
                return "30-60 min"
            else:
                return "> 1 hour"

        if len(valid_resp) > 0:
            valid_resp = valid_resp.copy()
            valid_resp["resp_bucket"] = valid_resp["response_time_min"].apply(bucket_resp)
            bucket_order = ["0-5 min", "5-30 min", "30-60 min", "> 1 hour"]
            bucket_counts = valid_resp["resp_bucket"].value_counts()
            bucket_pcts = (bucket_counts / len(valid_resp) * 100).reindex(bucket_order, fill_value=0)

            fig_resp = go.Figure()
            bar_colors = ["#27AE60", "#2E86DE", "#F39C12", "#E74C3C"]
            for i, (bucket, pct) in enumerate(bucket_pcts.items()):
                fig_resp.add_trace(go.Bar(
                    y=[bucket], x=[pct], orientation="h",
                    marker_color=bar_colors[i],
                    text=f"{pct:.0f}%", textposition="auto",
                    name=bucket, showlegend=False,
                    hovertemplate=f"{bucket}: {pct:.1f}% ({int(bucket_counts.get(bucket, 0))} leads)<extra></extra>"
                ))
            fig_resp.update_layout(
                height=220, margin=dict(l=0, r=20, t=10, b=10),
                xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]),
                yaxis=dict(autorange="reversed", tickfont=dict(size=12, family="DM Sans")),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                barmode="stack",
            )
            st.plotly_chart(fig_resp, use_container_width=True, key="resp_chart")

            avg_resp = valid_resp["response_time_min"].median()
            st.markdown(f"""
            <div style="text-align:center; padding: 8px; background: #F0F7FF; border-radius: 10px;
                        font-family: 'DM Sans'; font-size: 13px; color: #1B2A4A;">
                ⚡ Median Response: <b>{avg_resp:.0f} menit</b> &nbsp;|&nbsp;
                📊 Total Responded: <b>{len(valid_resp)}</b> / {len(df)} leads
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Tidak ada data response time untuk periode ini.")
    else:
        # Per Sales
        if len(valid_resp) > 0:
            sales_resp = valid_resp.groupby("sales_name")["response_time_min"].agg(["median", "count"]).reset_index()
            sales_resp.columns = ["Sales", "Median (min)", "Total"]
            sales_resp = sales_resp.sort_values("Median (min)")

            fig_sr = go.Figure()
            fig_sr.add_trace(go.Bar(
                y=sales_resp["Sales"], x=sales_resp["Median (min)"],
                orientation="h",
                marker_color=COLORS["secondary"],
                text=sales_resp["Median (min)"].apply(lambda x: f"{x:.0f} min"),
                textposition="auto",
                hovertemplate="%{y}: %{x:.0f} min<extra></extra>"
            ))
            fig_sr.update_layout(
                height=max(200, len(sales_resp) * 35),
                margin=dict(l=0, r=20, t=10, b=10),
                xaxis=dict(title="Median Response (menit)", showgrid=True, gridcolor="#F0F0F0"),
                yaxis=dict(tickfont=dict(size=11, family="DM Sans")),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_sr, use_container_width=True, key="resp_sales")
        else:
            st.info("Tidak ada data response time.")

    st.markdown('</div>', unsafe_allow_html=True)


with col_funnel:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Lead Funnel", "🔽"), unsafe_allow_html=True)

    # Calculate funnel counts based on progress data
    # A lead passes through stages, so we count all progress entries
    funnel_data = []
    for status in FUNNEL_STAGES:
        if status == "leads":
            count = total_leads  # All leads start as leads
        else:
            # Count prospects that have ever reached this status
            prospect_ids_at_status = prog[prog["status"] == status]["prospect_id"].nunique()
            count = prospect_ids_at_status
        funnel_data.append({"stage": STATUS_LABELS.get(status, status), "count": count})

    funnel_df = pd.DataFrame(funnel_data)

    # Avg response and avg closing time
    avg_response = valid_resp["response_time_min"].median() if len(valid_resp) > 0 else 0

    # Avg closing time: created_at -> handover progress created_at
    ho_prog = progress[progress["status"] == "handover"].copy()
    if len(ho_prog) > 0:
        ho_merged = ho_prog.merge(prospects[["id", "created_at"]], left_on="prospect_id", right_on="id", suffixes=("_prog", "_prospect"))
        ho_merged["closing_days"] = (ho_merged["created_at_prog"] - ho_merged["created_at_prospect"]).dt.days
        avg_closing = ho_merged["closing_days"].median()
    else:
        avg_closing = 0

    # Stats row
    st.markdown(f"""
    <div style="display: flex; gap: 20px; margin-bottom: 16px;">
        <div style="flex:1; text-align:center; padding: 10px; background: #F0F7FF; border-radius: 10px;">
            <div style="font-size: 11px; color: #6C757D; font-family: 'DM Sans'; text-transform: uppercase;">Avg Response</div>
            <div style="font-size: 20px; font-weight: 700; color: #2E86DE; font-family: 'DM Sans';">{avg_response:.0f} min</div>
        </div>
        <div style="flex:1; text-align:center; padding: 10px; background: #F0FFF0; border-radius: 10px;">
            <div style="font-size: 11px; color: #6C757D; font-family: 'DM Sans'; text-transform: uppercase;">Avg Closing Time</div>
            <div style="font-size: 20px; font-weight: 700; color: #27AE60; font-family: 'DM Sans';">{avg_closing:.0f} days</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Funnel chart
    funnel_colors = ["#3498DB", "#95A5A6", "#E67E22", "#27AE60", "#2ECC71"]
    fig_funnel = go.Figure(go.Funnel(
        y=funnel_df["stage"],
        x=funnel_df["count"],
        textinfo="value+percent initial",
        marker=dict(color=funnel_colors),
        connector=dict(line=dict(color="#E8ECF1", width=1)),
        textfont=dict(family="DM Sans", size=13),
    ))
    fig_funnel.update_layout(
        height=280, margin=dict(l=0, r=0, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_funnel, use_container_width=True, key="funnel")
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# ROW 3: Lead Sources + Quick Business Health
# ═══════════════════════════════════════════════════════════════════════
col_source, col_health = st.columns([5, 4])

with col_source:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Lead Sources", "📡"), unsafe_allow_html=True)

    source_stats = df.groupby("source_label").agg(
        leads=("id", "count"),
    ).reset_index()

    # Count deals and handovers per source
    deal_ho = df[df["progress_status"].isin(["deal", "handover"])]
    deal_by_source = deal_ho.groupby("source_label")["id"].count().reset_index()
    deal_by_source.columns = ["source_label", "deals"]

    source_stats = source_stats.merge(deal_by_source, on="source_label", how="left")
    source_stats["deals"] = source_stats["deals"].fillna(0).astype(int)
    source_stats["conversion"] = np.where(
        source_stats["leads"] > 0,
        (source_stats["deals"] / source_stats["leads"] * 100).round(1),
        0
    )
    source_stats = source_stats.sort_values("leads", ascending=False)

    # Pie chart + table side by side
    top_sources = source_stats.head(8)

    pie_col, tbl_col = st.columns([2, 3])
    with pie_col:
        fig_pie = go.Figure(go.Pie(
            labels=top_sources["source_label"],
            values=top_sources["leads"],
            hole=0.55,
            marker=dict(colors=COLORS["chart"]),
            textinfo="percent",
            textfont=dict(size=11, family="DM Sans"),
            hovertemplate="%{label}<br>Leads: %{value}<br>Share: %{percent}<extra></extra>"
        ))
        fig_pie.update_layout(
            height=260, margin=dict(l=0, r=0, t=10, b=10),
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(
                text=f"<b>{len(df)}</b><br><span style='font-size:10px'>Total</span>",
                x=0.5, y=0.5, font=dict(size=18, family="DM Sans", color="#1B2A4A"),
                showarrow=False
            )]
        )
        st.plotly_chart(fig_pie, use_container_width=True, key="pie_source")

    with tbl_col:
        # Render as styled HTML table
        rows_html = ""
        for _, r in top_sources.iterrows():
            rows_html += f"""
            <tr>
                <td style="font-weight:600; font-size:12px;">{r['source_label']}</td>
                <td style="text-align:right;">{r['leads']}</td>
                <td style="text-align:right;">{r['deals']}</td>
                <td style="text-align:right; color: {'#27AE60' if r['conversion'] >= 5 else '#E74C3C'};">{r['conversion']}%</td>
            </tr>"""

        st.markdown(f"""
        <table class="lb-table">
            <thead><tr>
                <th>Source</th><th style="text-align:right;">Leads</th>
                <th style="text-align:right;">Deals</th><th style="text-align:right;">Conv.</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


with col_health:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Quick Business Health Overview", "💡"), unsafe_allow_html=True)

    # Lead-to-Hot Conversion Rate (this period)
    hot_from_leads = len(df[df["progress_status"].isin(["hot_leads", "deal", "handover"])])
    lead_to_hot = round(hot_from_leads / total_leads * 100, 1) if total_leads > 0 else 0

    hot_prev = len(df_prev[df_prev["progress_status"].isin(["hot_leads", "deal", "handover"])])
    lead_to_hot_prev = round(hot_prev / total_leads_prev * 100, 1) if total_leads_prev > 0 else 0
    delta_hot_conv = round(lead_to_hot - lead_to_hot_prev, 1)

    # Lead-to-Deal Conversion
    deal_from_leads = len(df[df["progress_status"].isin(["deal", "handover"])])
    lead_to_deal = round(deal_from_leads / total_leads * 100, 1) if total_leads > 0 else 0

    deal_prev_count = len(df_prev[df_prev["progress_status"].isin(["deal", "handover"])])
    lead_to_deal_prev = round(deal_prev_count / total_leads_prev * 100, 1) if total_leads_prev > 0 else 0
    delta_deal_conv = round(lead_to_deal - lead_to_deal_prev, 1)

    # MoM Growth (leads)
    df_this_month = df[df["created_at"].dt.month == end_date.month]
    df_last_month_m = df[df["created_at"].dt.month == (end_date.month - 1 if end_date.month > 1 else 12)]
    mom_growth = calc_delta_pct(len(df_this_month), len(df_last_month_m)) if len(df_last_month_m) > 0 else 0

    kpi_col1, kpi_col2 = st.columns(2)
    with kpi_col1:
        delta_color = "delta-up" if delta_hot_conv >= 0 else "delta-down"
        delta_arrow = "▲" if delta_hot_conv >= 0 else "▼"
        st.markdown(f"""
        <div style="padding: 16px; background: #FFF8F0; border-radius: 12px; text-align: center; margin-bottom: 12px;">
            <div style="font-size: 11px; color: #6C757D; text-transform: uppercase; letter-spacing: 0.5px; font-family: 'DM Sans';">Lead-to-Hot Rate</div>
            <div style="font-size: 28px; font-weight: 700; color: #E67E22; font-family: 'DM Sans';">{lead_to_hot}%</div>
            <div class="metric-delta {delta_color}" style="font-size: 12px;">{delta_arrow} {abs(delta_hot_conv)}pp</div>
        </div>
        """, unsafe_allow_html=True)

        delta2_color = "delta-up" if delta_deal_conv >= 0 else "delta-down"
        delta2_arrow = "▲" if delta_deal_conv >= 0 else "▼"
        st.markdown(f"""
        <div style="padding: 16px; background: #F0FFF4; border-radius: 12px; text-align: center;">
            <div style="font-size: 11px; color: #6C757D; text-transform: uppercase; letter-spacing: 0.5px; font-family: 'DM Sans';">Lead-to-Deal Rate</div>
            <div style="font-size: 28px; font-weight: 700; color: #27AE60; font-family: 'DM Sans';">{lead_to_deal}%</div>
            <div class="metric-delta {delta2_color}" style="font-size: 12px;">{delta2_arrow} {abs(delta_deal_conv)}pp</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col2:
        # Monthly Leads vs Conversion chart
        monthly = df.groupby(df["created_at"].dt.to_period("M")).agg(
            leads=("id", "count"),
        ).reset_index()
        monthly["month"] = monthly["created_at"].astype(str)

        # Handover per month
        ho_monthly = df[df["progress_status"] == "handover"].groupby(
            df[df["progress_status"] == "handover"]["created_at"].dt.to_period("M")
        )["id"].count().reset_index()
        ho_monthly.columns = ["created_at", "handover"]
        ho_monthly["month"] = ho_monthly["created_at"].astype(str)

        monthly = monthly.merge(ho_monthly[["month", "handover"]], on="month", how="left")
        monthly["handover"] = monthly["handover"].fillna(0)
        monthly["conv_pct"] = np.where(monthly["leads"] > 0, (monthly["handover"] / monthly["leads"] * 100).round(1), 0)

        fig_mlc = make_subplots(specs=[[{"secondary_y": True}]])
        fig_mlc.add_trace(go.Bar(
            x=monthly["month"], y=monthly["leads"], name="Leads",
            marker_color=COLORS["secondary"], opacity=0.7,
            hovertemplate="%{x}: %{y} leads<extra></extra>"
        ), secondary_y=False)
        fig_mlc.add_trace(go.Scatter(
            x=monthly["month"], y=monthly["conv_pct"], name="Conv %",
            line=dict(color=COLORS["accent"], width=2.5),
            mode="lines+markers", marker=dict(size=6),
            hovertemplate="%{x}: %{y}%<extra></extra>"
        ), secondary_y=True)

        fig_mlc.update_layout(
            height=240, margin=dict(l=0, r=0, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.15, font=dict(size=10, family="DM Sans")),
            font=dict(family="DM Sans"),
        )
        fig_mlc.update_xaxes(tickfont=dict(size=9), tickangle=-45)
        fig_mlc.update_yaxes(title_text="Leads", secondary_y=False, showgrid=True, gridcolor="#F0F0F0")
        fig_mlc.update_yaxes(title_text="Conv %", secondary_y=True, showgrid=False)

        st.plotly_chart(fig_mlc, use_container_width=True, key="monthly_conv")

    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# ROW 4: Sales Leaderboard + Hot Leads + Daily Lead Trend
# ═══════════════════════════════════════════════════════════════════════
col_lb, col_hot, col_trend = st.columns([3, 3, 4])

with col_lb:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Sales Leaderboard", "🏆"), unsafe_allow_html=True)

    lb = df.groupby("sales_name").agg(
        leads=("id", "count"),
    ).reset_index()

    # Handover per sales
    ho_sales = df[df["progress_status"] == "handover"].groupby("sales_name")["id"].count().reset_index()
    ho_sales.columns = ["sales_name", "handover"]

    lb = lb.merge(ho_sales, on="sales_name", how="left")
    lb["handover"] = lb["handover"].fillna(0).astype(int)
    lb["conv_pct"] = np.where(lb["leads"] > 0, (lb["handover"] / lb["leads"] * 100).round(1), 0)
    lb = lb.sort_values("leads", ascending=False)

    rows_html = ""
    for rank, (_, r) in enumerate(lb.head(10).iterrows(), 1):
        badge = ""
        if rank == 1:
            badge = '<span class="lb-badge badge-gold">🥇</span>'
        elif rank == 2:
            badge = '<span class="lb-badge badge-silver">🥈</span>'
        elif rank == 3:
            badge = '<span class="lb-badge badge-bronze">🥉</span>'
        else:
            badge = f'<span class="lb-rank">{rank}</span>'

        rows_html += f"""
        <tr>
            <td>{badge}</td>
            <td class="lb-name">{r['sales_name']}</td>
            <td style="text-align:right; font-weight:600;">{r['leads']}</td>
            <td style="text-align:right;">{r['handover']}</td>
            <td style="text-align:right; color: {'#27AE60' if r['conv_pct'] >= 5 else '#E74C3C'};">
                {r['conv_pct']}%
            </td>
        </tr>"""

    st.markdown(f"""
    <table class="lb-table">
        <thead><tr>
            <th>#</th><th>Sales</th>
            <th style="text-align:right;">Leads</th>
            <th style="text-align:right;">HO</th>
            <th style="text-align:right;">Conv</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


with col_hot:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Hot Leads by Sales", "🔥"), unsafe_allow_html=True)

    # Hot leads per sales (MR with total hot leads)
    hot_by_sales = df[df["progress_status"] == "hot_leads"].groupby("sales_name")["id"].count().reset_index()
    hot_by_sales.columns = ["sales_name", "hot_count"]
    hot_by_sales = hot_by_sales.sort_values("hot_count", ascending=False)

    # Also get prospect names for hot leads
    hot_prospects = df[df["progress_status"] == "hot_leads"].copy()

    if len(hot_by_sales) > 0:
        for _, r in hot_by_sales.head(8).iterrows():
            # Calculate a "score" — total_progress as proxy
            sales_hot = hot_prospects[hot_prospects["sales_name"] == r["sales_name"]]
            avg_prog = sales_hot["total_progress"].mean() if "total_progress" in sales_hot.columns else 0

            st.markdown(f"""
            <div class="hot-lead-item">
                <div>
                    <div class="hot-lead-name">{r['sales_name']}</div>
                    <div style="font-size: 11px; color: #6C757D;">{len(sales_hot)} hot leads</div>
                </div>
                <div class="hot-lead-score">{r['hot_count']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Tidak ada hot leads untuk periode ini.")

    st.markdown('</div>', unsafe_allow_html=True)


with col_trend:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Daily Lead Trend", "📈"), unsafe_allow_html=True)

    # Daily lead trend — last 14 days of the period
    daily = df.groupby("created_date")["id"].count().reset_index()
    daily.columns = ["date", "leads"]
    daily = daily.sort_values("date").tail(30)

    if len(daily) > 0:
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=daily["date"], y=daily["leads"],
            mode="lines+markers",
            line=dict(color=COLORS["secondary"], width=2.5, shape="spline"),
            marker=dict(size=5, color=COLORS["secondary"]),
            fill="tozeroy",
            fillcolor="rgba(46,134,222,0.08)",
            hovertemplate="%{x|%d %b}: %{y} leads<extra></extra>"
        ))

        # Add peak annotation
        peak_idx = daily["leads"].idxmax()
        peak_row = daily.loc[peak_idx]
        fig_trend.add_annotation(
            x=peak_row["date"], y=peak_row["leads"],
            text=f"Peak: {peak_row['leads']}",
            showarrow=True, arrowhead=2,
            font=dict(size=10, color=COLORS["accent"], family="DM Sans"),
            bgcolor="white", bordercolor=COLORS["accent"], borderwidth=1,
        )

        fig_trend.update_layout(
            height=280, margin=dict(l=0, r=10, t=10, b=10),
            xaxis=dict(tickfont=dict(size=10), showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#F0F0F0", title="Leads"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_trend, use_container_width=True, key="daily_trend")
    else:
        st.info("Tidak ada data untuk trend harian.")

    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# ROW 5: Lead Aging + Lost Lead Analysis + Monthly Sales Growth
# ═══════════════════════════════════════════════════════════════════════
col_age, col_lost, col_growth = st.columns([3, 3, 4])

with col_age:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Lead Aging", "⏳"), unsafe_allow_html=True)

    # Lead aging — only for leads, cold, hot, deal (not handover/cancel)
    active_leads = df[df["progress_status"].isin(["leads", "cold_leads", "hot_leads", "deal"])].copy()

    if len(active_leads) > 0:
        # Calculate age from last followup (updated_at) to snapshot date
        snapshot = datetime(2026, 4, 10)
        # Use the last progress entry per prospect for last followup
        last_prog = progress.groupby("prospect_id")["created_at"].max().reset_index()
        last_prog.columns = ["id", "last_followup"]

        active_aged = active_leads.merge(last_prog, on="id", how="left")
        active_aged["age_days"] = (snapshot - active_aged["last_followup"]).dt.days
        active_aged.loc[active_aged["age_days"].isna(), "age_days"] = (
            snapshot - active_aged.loc[active_aged["age_days"].isna(), "created_at"]
        ).dt.days

        def age_bucket(days):
            if days <= 1:
                return "0-1 day"
            elif days <= 3:
                return "1-3 days"
            elif days <= 7:
                return "3-7 days"
            else:
                return ">7 days"

        active_aged["age_bucket"] = active_aged["age_days"].apply(age_bucket)
        bucket_order = ["0-1 day", "1-3 days", "3-7 days", ">7 days"]
        age_counts = active_aged["age_bucket"].value_counts().reindex(bucket_order, fill_value=0)
        age_pcts = (age_counts / len(active_aged) * 100).round(1)

        age_colors = ["#27AE60", "#2E86DE", "#F39C12", "#E74C3C"]

        fig_age = go.Figure()
        for i, (bucket, pct) in enumerate(age_pcts.items()):
            fig_age.add_trace(go.Bar(
                y=[bucket], x=[pct], orientation="h",
                marker_color=age_colors[i],
                text=f"{pct:.1f}%", textposition="auto",
                showlegend=False,
                hovertemplate=f"{bucket}: {age_counts[bucket]} leads ({pct}%)<extra></extra>"
            ))

        fig_age.update_layout(
            height=200, margin=dict(l=0, r=20, t=10, b=10),
            xaxis=dict(showgrid=False, showticklabels=False, range=[0, 100]),
            yaxis=dict(autorange="reversed", tickfont=dict(size=12, family="DM Sans")),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_age, use_container_width=True, key="aging")
    else:
        st.info("Tidak ada active leads.")

    st.markdown('</div>', unsafe_allow_html=True)


with col_lost:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Lost Lead Analysis", "❌"), unsafe_allow_html=True)

    # Drop/Cancel reasons
    cancelled = df[df["progress_status"] == "cancelreject"].copy()
    if len(cancelled) > 0:
        reason_counts = cancelled["reason_label"].value_counts().head(6)
        reason_pcts = (reason_counts / len(cancelled) * 100).round(1)

        fig_lost = go.Figure()
        fig_lost.add_trace(go.Bar(
            y=reason_counts.index[::-1],
            x=reason_pcts.values[::-1],
            orientation="h",
            marker_color=COLORS["danger"],
            marker_opacity=0.8,
            text=[f"{p}%" for p in reason_pcts.values[::-1]],
            textposition="auto",
            hovertemplate="%{y}: %{x:.1f}% (%{customdata} leads)<extra></extra>",
            customdata=reason_counts.values[::-1],
            showlegend=False,
        ))
        fig_lost.update_layout(
            height=220, margin=dict(l=0, r=20, t=10, b=10),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(tickfont=dict(size=10, family="DM Sans")),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_lost, use_container_width=True, key="lost_analysis")
    else:
        st.info("Tidak ada data cancel/reject.")

    st.markdown('</div>', unsafe_allow_html=True)


with col_growth:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Monthly Handover & Growth", "📊"), unsafe_allow_html=True)

    # Monthly handover trend
    ho_df = df[df["progress_status"] == "handover"].copy()
    if len(ho_df) > 0:
        ho_monthly_trend = ho_df.groupby(ho_df["created_at"].dt.to_period("M"))["id"].count().reset_index()
        ho_monthly_trend.columns = ["month", "handovers"]
        ho_monthly_trend["month_str"] = ho_monthly_trend["month"].astype(str)
        ho_monthly_trend["growth"] = ho_monthly_trend["handovers"].pct_change() * 100

        fig_growth = make_subplots(specs=[[{"secondary_y": True}]])
        fig_growth.add_trace(go.Bar(
            x=ho_monthly_trend["month_str"],
            y=ho_monthly_trend["handovers"],
            name="Handovers",
            marker_color=COLORS["success"],
            opacity=0.8,
            hovertemplate="%{x}: %{y} units<extra></extra>"
        ), secondary_y=False)

        fig_growth.add_trace(go.Scatter(
            x=ho_monthly_trend["month_str"],
            y=ho_monthly_trend["growth"],
            name="Growth %",
            line=dict(color=COLORS["accent"], width=2.5),
            mode="lines+markers",
            marker=dict(size=6),
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>"
        ), secondary_y=True)

        fig_growth.update_layout(
            height=260, margin=dict(l=0, r=0, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.15, font=dict(size=10, family="DM Sans")),
            font=dict(family="DM Sans"),
        )
        fig_growth.update_xaxes(tickfont=dict(size=9), tickangle=-45)
        fig_growth.update_yaxes(title_text="Handovers", secondary_y=False, showgrid=True, gridcolor="#F0F0F0")
        fig_growth.update_yaxes(title_text="Growth %", secondary_y=True, showgrid=False)

        # Summary stats
        total_ho = ho_monthly_trend["handovers"].sum()
        avg_monthly = ho_monthly_trend["handovers"].mean()

        st.plotly_chart(fig_growth, use_container_width=True, key="growth_chart")

        st.markdown(f"""
        <div style="display:flex; gap:12px; margin-top: -8px;">
            <div style="flex:1; text-align:center; padding: 8px; background:#F0FFF4; border-radius:8px;">
                <div style="font-size:10px; color:#6C757D; text-transform:uppercase;">Total</div>
                <div style="font-size:18px; font-weight:700; color:#27AE60;">{total_ho}</div>
            </div>
            <div style="flex:1; text-align:center; padding: 8px; background:#FFF8F0; border-radius:8px;">
                <div style="font-size:10px; color:#6C757D; text-transform:uppercase;">Avg/Month</div>
                <div style="font-size:18px; font-weight:700; color:#E67E22;">{avg_monthly:.0f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Tidak ada data handover.")

    st.markdown('</div>', unsafe_allow_html=True)
