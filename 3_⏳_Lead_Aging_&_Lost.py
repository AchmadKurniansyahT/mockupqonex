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

st.set_page_config(page_title="Lead Aging & Lost Analysis", page_icon="⏳", layout="wide")
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
            ⏳ Aging & Lost
        </div>
    </div>
    <hr style="border-color: rgba(255,255,255,0.1);">
    """, unsafe_allow_html=True)

    time_filter = st.selectbox(
        "📅 PERIODE",
        ["Minggu Ini", "Minggu Lalu", "Bulan Ini", "Bulan Lalu", "Tahun Ini", "Lifetime"],
        index=4, key="la_time"
    )
    start_date, end_date = get_date_range(time_filter)
    prev_start, prev_end = get_previous_period(start_date, end_date)
    st.caption(f"📆 {start_date.strftime('%d %b %Y')} — {end_date.strftime('%d %b %Y')}")

    all_sales = sorted(prospects["sales_name"].dropna().unique())
    selected_sales = st.multiselect("👤 FILTER SALES", all_sales, default=[], key="la_sales")

df = filter_by_date(prospects, "created_at", start_date, end_date)
if selected_sales:
    df = df[df["sales_name"].isin(selected_sales)]

snapshot = datetime(2026, 4, 10)

# ─── Header ──────────────────────────────────────────────────────────
st.markdown(f"""
<div class="dashboard-header">
    <h1>⏳ Lead Aging & Lost Lead Analysis</h1>
    <p>Monitoring umur lead aktif dan analisis alasan lost &nbsp;|&nbsp; {time_filter}</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# LEAD AGING SECTION
# ═══════════════════════════════════════════════════════════════════════

# Active leads only: leads, cold, hot, deal
active = df[df["progress_status"].isin(["leads", "cold_leads", "hot_leads", "deal"])].copy()

# Calculate last followup from progress
last_prog = progress.groupby("prospect_id")["created_at"].max().reset_index()
last_prog.columns = ["id", "last_followup"]

active = active.merge(last_prog, on="id", how="left")
active["days_since_followup"] = (snapshot - active["last_followup"]).dt.days
active.loc[active["days_since_followup"].isna(), "days_since_followup"] = (
    snapshot - active.loc[active["days_since_followup"].isna(), "created_at"]
).dt.days

def age_bucket(days):
    if days <= 1: return "0-1 day"
    elif days <= 3: return "1-3 days"
    elif days <= 7: return "3-7 days"
    elif days <= 14: return "7-14 days"
    elif days <= 30: return "14-30 days"
    else: return ">30 days"

active["age_bucket"] = active["days_since_followup"].apply(age_bucket)

# ─── KPIs ────────────────────────────────────────────────────────────
total_active = len(active)
avg_age = active["days_since_followup"].mean() if total_active > 0 else 0
stale_7 = len(active[active["days_since_followup"] > 7])
stale_pct = round(stale_7 / total_active * 100, 1) if total_active > 0 else 0

cols = st.columns(4)
with cols[0]:
    st.markdown(render_metric_card("Active Leads", str(total_active)), unsafe_allow_html=True)
with cols[1]:
    st.markdown(render_metric_card("Avg Age (days)", f"{avg_age:.1f}"), unsafe_allow_html=True)
with cols[2]:
    st.markdown(render_metric_card("Stale (>7d)", str(stale_7)), unsafe_allow_html=True)
with cols[3]:
    st.markdown(render_metric_card("Stale %", f"{stale_pct}%"), unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

# ─── Aging Distribution + By Status ─────────────────────────────────
col_dist, col_status = st.columns([5, 5])

with col_dist:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Aging Distribution", "📊"), unsafe_allow_html=True)

    bucket_order = ["0-1 day", "1-3 days", "3-7 days", "7-14 days", "14-30 days", ">30 days"]
    age_counts = active["age_bucket"].value_counts().reindex(bucket_order, fill_value=0)
    age_pcts = (age_counts / len(active) * 100).round(1) if len(active) > 0 else pd.Series([0]*6, index=bucket_order)

    age_colors = ["#27AE60", "#2ECC71", "#F1C40F", "#F39C12", "#E67E22", "#E74C3C"]

    fig_age = go.Figure()
    fig_age.add_trace(go.Bar(
        x=bucket_order, y=age_counts.values,
        marker_color=age_colors,
        text=[f"{p}%" for p in age_pcts.values],
        textposition="outside",
        hovertemplate="%{x}: %{y} leads (%{text})<extra></extra>",
        showlegend=False,
    ))
    fig_age.update_layout(
        height=320, margin=dict(l=0, r=0, t=30, b=10),
        xaxis=dict(tickfont=dict(size=11, family="DM Sans")),
        yaxis=dict(showgrid=True, gridcolor="#F0F0F0", title="Leads"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_age, use_container_width=True, key="age_dist")
    st.markdown('</div>', unsafe_allow_html=True)

with col_status:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Aging by Status", "🏷️"), unsafe_allow_html=True)

    if len(active) > 0:
        status_age = active.groupby("progress_status")["days_since_followup"].agg(["mean", "median", "count"]).reset_index()
        status_age.columns = ["Status", "Avg Days", "Median Days", "Count"]
        status_age["Status"] = status_age["Status"].map(STATUS_LABELS).fillna(status_age["Status"])
        status_age = status_age.sort_values("Avg Days", ascending=False)

        status_colors_map = {"Leads": "#3498DB", "Cold": "#95A5A6", "Hot": "#E67E22", "Deal": "#27AE60"}

        fig_status = go.Figure()
        for _, r in status_age.iterrows():
            fig_status.add_trace(go.Bar(
                x=[r["Status"]], y=[r["Avg Days"]],
                marker_color=status_colors_map.get(r["Status"], "#6C757D"),
                text=f"{r['Avg Days']:.0f}d",
                textposition="outside",
                showlegend=False,
                hovertemplate=f"{r['Status']}: Avg {r['Avg Days']:.1f}d, Median {r['Median Days']:.1f}d ({r['Count']} leads)<extra></extra>"
            ))
        fig_status.update_layout(
            height=320, margin=dict(l=0, r=0, t=30, b=10),
            xaxis=dict(tickfont=dict(size=12, family="DM Sans")),
            yaxis=dict(showgrid=True, gridcolor="#F0F0F0", title="Avg Days"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_status, use_container_width=True, key="age_status")

    st.markdown('</div>', unsafe_allow_html=True)


# ─── Aging by Sales ──────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown(render_section("Lead Aging per Sales — Heatmap", "🔥"), unsafe_allow_html=True)

if len(active) > 0:
    pivot = active.groupby(["sales_name", "age_bucket"])["id"].count().reset_index()
    pivot.columns = ["Sales", "Bucket", "Count"]
    pivot_wide = pivot.pivot(index="Sales", columns="Bucket", values="Count").fillna(0)
    pivot_wide = pivot_wide.reindex(columns=bucket_order, fill_value=0)

    fig_heat = px.imshow(
        pivot_wide.values,
        labels=dict(x="Age Bucket", y="Sales", color="Leads"),
        x=bucket_order,
        y=pivot_wide.index.tolist(),
        color_continuous_scale=["#FFFFFF", "#FDEBD0", "#F39C12", "#E74C3C", "#922B21"],
        text_auto=True,
        aspect="auto",
    )
    fig_heat.update_layout(
        height=max(300, len(pivot_wide) * 40),
        margin=dict(l=0, r=0, t=10, b=10),
        font=dict(family="DM Sans", size=11),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_heat, use_container_width=True, key="age_heatmap")
else:
    st.info("Tidak ada active leads.")

st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# LOST LEAD ANALYSIS SECTION
# ═══════════════════════════════════════════════════════════════════════
st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
st.markdown(f"""
<div style="background: linear-gradient(135deg, #FDEDEC, #F9EBEA); border-radius: 16px; padding: 20px 28px; margin-bottom: 20px;">
    <div style="font-size: 20px; font-weight: 700; color: #E74C3C; font-family: 'DM Sans';">
        ❌ Lost Lead Analysis
    </div>
    <div style="font-size: 13px; color: #6C757D; font-family: 'DM Sans';">
        Analisis alasan lead cancel/reject untuk improvement strategi
    </div>
</div>
""", unsafe_allow_html=True)

cancelled = df[df["progress_status"] == "cancelreject"].copy()
total_cancel = len(cancelled)
cancel_rate = round(total_cancel / len(df) * 100, 1) if len(df) > 0 else 0

col_reason, col_trend = st.columns([5, 5])

with col_reason:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Cancel/Reject Reasons", "📋"), unsafe_allow_html=True)

    if total_cancel > 0:
        reason_counts = cancelled["reason_label"].value_counts().head(10)
        reason_pcts = (reason_counts / total_cancel * 100).round(1)

        fig_reasons = go.Figure()
        fig_reasons.add_trace(go.Bar(
            y=reason_counts.index[::-1],
            x=reason_pcts.values[::-1],
            orientation="h",
            marker=dict(
                color=reason_pcts.values[::-1],
                colorscale=[[0, "#FADBD8"], [1, "#E74C3C"]],
            ),
            text=[f"{p}% ({c})" for p, c in zip(reason_pcts.values[::-1], reason_counts.values[::-1])],
            textposition="auto",
            showlegend=False,
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>"
        ))
        fig_reasons.update_layout(
            height=350, margin=dict(l=0, r=30, t=10, b=10),
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(tickfont=dict(size=10, family="DM Sans")),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_reasons, use_container_width=True, key="reasons")

        st.markdown(f"""
        <div style="text-align:center; padding: 10px; background: #FDEDEC; border-radius: 10px; font-family: 'DM Sans'; font-size: 13px;">
            Total Cancel/Reject: <b>{total_cancel}</b> &nbsp;|&nbsp; Rate: <b>{cancel_rate}%</b> dari total leads
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Tidak ada data cancel/reject.")

    st.markdown('</div>', unsafe_allow_html=True)

with col_trend:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(render_section("Monthly Cancel Trend", "📉"), unsafe_allow_html=True)

    if total_cancel > 0:
        cancel_monthly = cancelled.groupby(cancelled["created_at"].dt.to_period("M").astype(str))["id"].count().reset_index()
        cancel_monthly.columns = ["month", "cancels"]

        # Also total leads per month for rate
        total_monthly = df.groupby(df["created_at"].dt.to_period("M").astype(str))["id"].count().reset_index()
        total_monthly.columns = ["month", "total"]

        cancel_monthly = cancel_monthly.merge(total_monthly, on="month", how="left")
        cancel_monthly["rate"] = (cancel_monthly["cancels"] / cancel_monthly["total"] * 100).round(1)

        fig_cancel = make_subplots(specs=[[{"secondary_y": True}]])
        fig_cancel.add_trace(go.Bar(
            x=cancel_monthly["month"], y=cancel_monthly["cancels"],
            name="Cancels", marker_color="#E74C3C", opacity=0.7,
        ), secondary_y=False)
        fig_cancel.add_trace(go.Scatter(
            x=cancel_monthly["month"], y=cancel_monthly["rate"],
            name="Rate %", line=dict(color="#F39C12", width=2.5),
            mode="lines+markers", marker=dict(size=6),
        ), secondary_y=True)

        fig_cancel.update_layout(
            height=350, margin=dict(l=0, r=0, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.12, font=dict(size=10, family="DM Sans")),
            xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
            font=dict(family="DM Sans"),
        )
        fig_cancel.update_yaxes(title_text="Cancels", secondary_y=False, showgrid=True, gridcolor="#F0F0F0")
        fig_cancel.update_yaxes(title_text="Rate %", secondary_y=True, showgrid=False)
        st.plotly_chart(fig_cancel, use_container_width=True, key="cancel_trend")
    else:
        st.info("Tidak ada data.")

    st.markdown('</div>', unsafe_allow_html=True)


# ─── Cancel by Sales ─────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown(render_section("Cancel Rate per Sales", "👥"), unsafe_allow_html=True)

if total_cancel > 0:
    cancel_by_sales = df.groupby("sales_name").agg(
        total=("id", "count"),
    ).reset_index()
    cancel_count = cancelled.groupby("sales_name")["id"].count().reset_index()
    cancel_count.columns = ["sales_name", "cancels"]
    cancel_by_sales = cancel_by_sales.merge(cancel_count, on="sales_name", how="left")
    cancel_by_sales["cancels"] = cancel_by_sales["cancels"].fillna(0).astype(int)
    cancel_by_sales["cancel_rate"] = (cancel_by_sales["cancels"] / cancel_by_sales["total"] * 100).round(1)
    cancel_by_sales = cancel_by_sales.sort_values("cancel_rate", ascending=False)

    fig_cs = go.Figure()
    fig_cs.add_trace(go.Bar(
        x=cancel_by_sales["sales_name"],
        y=cancel_by_sales["cancel_rate"],
        marker_color=[COLORS["danger"] if r > 90 else COLORS["warning"] if r > 80 else COLORS["success"] for r in cancel_by_sales["cancel_rate"]],
        text=[f"{r}%" for r in cancel_by_sales["cancel_rate"]],
        textposition="outside",
        showlegend=False,
        hovertemplate="%{x}: %{y:.1f}% (%{customdata} of %{meta})<extra></extra>",
        customdata=cancel_by_sales["cancels"],
        meta=cancel_by_sales["total"],
    ))
    fig_cs.update_layout(
        height=300, margin=dict(l=0, r=0, t=30, b=10),
        xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#F0F0F0", title="Cancel Rate %", range=[0, 105]),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_cs, use_container_width=True, key="cancel_sales")

st.markdown('</div>', unsafe_allow_html=True)
