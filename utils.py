import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# ─── Color Palette ───────────────────────────────────────────────────
COLORS = {
    "primary": "#1B2A4A",
    "secondary": "#2E86DE",
    "accent": "#F39C12",
    "success": "#27AE60",
    "danger": "#E74C3C",
    "warning": "#F1C40F",
    "info": "#3498DB",
    "dark": "#0D1B2A",
    "light": "#F8F9FA",
    "muted": "#6C757D",
    "bg_card": "#FFFFFF",
    "bg_page": "#F0F2F5",
    "gradient_start": "#1B2A4A",
    "gradient_end": "#2E86DE",
    # Status colors
    "leads": "#3498DB",
    "cold": "#95A5A6",
    "hot": "#E67E22",
    "deal": "#27AE60",
    "handover": "#2ECC71",
    "cancel": "#E74C3C",
    # Chart palette
    "chart": ["#2E86DE", "#E67E22", "#27AE60", "#E74C3C", "#9B59B6",
              "#1ABC9C", "#F39C12", "#3498DB", "#2C3E50", "#D35400"],
}

STATUS_ORDER = ["leads", "cold_leads", "hot_leads", "deal", "handover", "cancelreject"]
STATUS_LABELS = {
    "leads": "Leads",
    "cold_leads": "Cold",
    "hot_leads": "Hot",
    "deal": "Deal",
    "handover": "Handover",
    "cancelreject": "Cancel/Reject",
}
STATUS_COLORS = {
    "leads": "#3498DB",
    "cold_leads": "#95A5A6",
    "hot_leads": "#E67E22",
    "deal": "#27AE60",
    "handover": "#2ECC71",
    "cancelreject": "#E74C3C",
}

FUNNEL_STAGES = ["leads", "cold_leads", "hot_leads", "deal", "handover"]

# ─── Data Loading ────────────────────────────────────────────────────

def find_data_path():
    """Find data files - check uploads first, then local."""
    paths = ["/data", "./data", "."]
    for p in paths:
        if os.path.exists(os.path.join(p, "Prospect__-_10042026.csv")):
            return p
    return "."


def load_data(data_path=None):
    """Load and prepare all dataframes."""
    if data_path is None:
        data_path = find_data_path()

    # Load CSVs
    prospects = pd.read_csv(
        os.path.join(data_path, "Prospect__-_10042026.csv"),
        sep=";", quotechar='"', on_bad_lines="skip"
    )
    progress = pd.read_csv(
        os.path.join(data_path, "Progress_-_10042026.csv"),
        sep=";", quotechar='"', on_bad_lines="skip"
    )
    users = pd.read_csv(
        os.path.join(data_path, "Project-User_-_10042026.csv"),
        sep=";", quotechar='"', on_bad_lines="skip"
    )
    options = pd.read_csv(
        os.path.join(data_path, "Option_-_10042026.csv"),
        sep=";", quotechar='"', on_bad_lines="skip"
    )

    # Parse dates
    prospects["created_at"] = pd.to_datetime(prospects["created_at"], errors="coerce")
    prospects["updated_at"] = pd.to_datetime(prospects["updated_at"], errors="coerce")
    prospects["first_contact"] = pd.to_datetime(prospects["first_contact"], errors="coerce")

    progress["created_at"] = pd.to_datetime(progress["created_at"], errors="coerce")

    # Clean progress status — only keep valid statuses
    valid_statuses = {"leads", "cold_leads", "hot_leads", "deal", "handover", "cancelreject"}
    progress = progress[progress["status"].isin(valid_statuses)].copy()

    # Build user lookup (email -> display name)
    users["display_name"] = users.apply(
        lambda r: r["name"].strip() if pd.notna(r["name"]) and r["name"].strip()
        else r["username"].split("@")[0].replace(".", " ").title(),
        axis=1
    )
    user_lookup = dict(zip(users["id"], users["display_name"]))
    user_email_lookup = dict(zip(users["id"], users["username"]))

    # Build source lookup
    source_options = options[options["kind"] == "referrer_source_prospect"]
    source_lookup = dict(zip(source_options["key"], source_options["value"]))

    # Build reason lookup
    reason_options = options[options["kind"] == "reason_cancel"]
    reason_lookup = dict(zip(reason_options["key"], reason_options["value"]))

    # Enrich prospects
    prospects["sales_name"] = prospects["assignee_id"].map(user_lookup).fillna("Unassigned")
    prospects["source_label"] = prospects["referrer_source"].map(source_lookup).fillna(prospects["referrer_source"])
    prospects["reason_label"] = prospects["reason_cancel"].map(reason_lookup).fillna(prospects["reason_cancel"])

    # Month columns
    prospects["created_month"] = prospects["created_at"].dt.to_period("M")
    prospects["created_year_month"] = prospects["created_at"].dt.strftime("%Y-%m")
    prospects["created_date"] = prospects["created_at"].dt.date

    # Calculate response time in minutes (created_at -> first_contact)
    mask_fc = prospects["first_contact"].notna()
    prospects.loc[mask_fc, "response_time_min"] = (
        (prospects.loc[mask_fc, "first_contact"] - prospects.loc[mask_fc, "created_at"])
        .dt.total_seconds() / 60
    )
    # Only positive values (first_contact after created_at)
    prospects.loc[prospects["response_time_min"] < 0, "response_time_min"] = np.nan

    # Enrich progress
    progress["sales_name"] = progress["creator_id"].map(user_lookup).fillna("Unknown")

    return {
        "prospects": prospects,
        "progress": progress,
        "users": users,
        "options": options,
        "user_lookup": user_lookup,
        "source_lookup": source_lookup,
        "reason_lookup": reason_lookup,
    }


# ─── Date Filters ────────────────────────────────────────────────────

def get_date_range(filter_key: str, ref_date=None):
    """Return (start_date, end_date) based on filter selection."""
    if ref_date is None:
        ref_date = datetime(2026, 4, 10)  # data snapshot date

    today = ref_date.date() if isinstance(ref_date, datetime) else ref_date

    if filter_key == "Minggu Ini":
        start = today - timedelta(days=today.weekday())  # Monday
        return start, today
    elif filter_key == "Minggu Lalu":
        this_monday = today - timedelta(days=today.weekday())
        start = this_monday - timedelta(days=7)
        end = this_monday - timedelta(days=1)
        return start, end
    elif filter_key == "Bulan Ini":
        start = today.replace(day=1)
        return start, today
    elif filter_key == "Bulan Lalu":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        start = last_prev.replace(day=1)
        return start, last_prev
    elif filter_key == "Tahun Ini":
        start = today.replace(month=1, day=1)
        return start, today
    elif filter_key == "Lifetime":
        return datetime(2020, 1, 1).date(), today
    else:
        return today.replace(month=1, day=1), today


def filter_by_date(df, date_col, start, end):
    """Filter dataframe by date range."""
    s = pd.Timestamp(start)
    e = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    return df[(df[date_col] >= s) & (df[date_col] <= e)]


def get_previous_period(start, end):
    """Get equivalent previous period for comparison."""
    delta = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=delta - 1)
    return prev_start, prev_end


# ─── Metric helpers ──────────────────────────────────────────────────

def calc_delta_pct(current, previous):
    """Calculate percentage change."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def format_number(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(int(n))


# ─── Lead Age Calculation ────────────────────────────────────────────

def calc_lead_age(prospects_df, progress_df):
    """
    Calculate lead aging.
    - Jika sudah handover: age = created_at prospect -> handover progress created_at
    - Jika belum: age = created_at prospect -> hari ini (snapshot)
    Only for status: leads, cold_leads, hot_leads, deal
    """
    snapshot = datetime(2026, 4, 10)

    # Get handover dates per prospect
    handover_progress = progress_df[progress_df["status"] == "handover"].copy()
    handover_dates = handover_progress.groupby("prospect_id")["created_at"].min().reset_index()
    handover_dates.columns = ["id", "handover_date"]

    merged = prospects_df.merge(handover_dates, on="id", how="left")

    # Age in days
    mask_ho = merged["handover_date"].notna()
    merged.loc[mask_ho, "age_days"] = (merged.loc[mask_ho, "handover_date"] - merged.loc[mask_ho, "created_at"]).dt.days
    merged.loc[~mask_ho, "age_days"] = (snapshot - merged.loc[~mask_ho, "created_at"]).dt.days

    # Only relevant statuses
    relevant = merged[merged["progress_status"].isin(["leads", "cold_leads", "hot_leads", "deal"])].copy()
    return relevant


# ─── CSS Injection ───────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --primary: #1B2A4A;
    --secondary: #2E86DE;
    --accent: #F39C12;
    --bg-page: #F0F2F5;
}

.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 1rem;
    max-width: 1400px;
}

/* Metric cards */
.metric-card {
    background: #FFFFFF;
    border-radius: 16px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    border: 1px solid #E8ECF1;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    position: relative;
    overflow: hidden;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.08);
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--secondary), var(--accent));
}
.metric-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 12px;
    font-weight: 500;
    color: #6C757D;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
}
.metric-value {
    font-family: 'DM Sans', sans-serif;
    font-size: 28px;
    font-weight: 700;
    color: #1B2A4A;
    line-height: 1.1;
}
.metric-delta {
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    font-weight: 600;
    margin-top: 6px;
}
.delta-up { color: #27AE60; }
.delta-down { color: #E74C3C; }
.delta-neutral { color: #6C757D; }

/* Section cards */
.section-card {
    background: #FFFFFF;
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    border: 1px solid #E8ECF1;
    margin-bottom: 16px;
}
.section-title {
    font-family: 'DM Sans', sans-serif;
    font-size: 16px;
    font-weight: 700;
    color: #1B2A4A;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-title .icon {
    font-size: 18px;
}

/* Header */
.dashboard-header {
    background: linear-gradient(135deg, #1B2A4A 0%, #2E4A7A 50%, #2E86DE 100%);
    border-radius: 20px;
    padding: 28px 36px;
    margin-bottom: 24px;
    color: white;
    position: relative;
    overflow: hidden;
}
.dashboard-header::after {
    content: '';
    position: absolute;
    top: -50%; right: -10%;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
    border-radius: 50%;
}
.dashboard-header h1 {
    font-family: 'DM Sans', sans-serif;
    font-size: 26px;
    font-weight: 700;
    margin: 0;
    color: white;
}
.dashboard-header p {
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    color: rgba(255,255,255,0.75);
    margin: 4px 0 0 0;
}

/* Leaderboard table */
.lb-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 4px;
}
.lb-table th {
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: #6C757D;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 8px 12px;
    text-align: left;
    border-bottom: 2px solid #E8ECF1;
}
.lb-table td {
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    padding: 10px 12px;
    color: #1B2A4A;
}
.lb-table tr:nth-child(even) td {
    background: #F8F9FB;
}
.lb-table tr:hover td {
    background: #EDF2FA;
}
.lb-rank {
    font-weight: 700;
    color: #2E86DE;
    font-size: 14px;
}
.lb-name {
    font-weight: 600;
}
.lb-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
}
.badge-gold { background: #FFF3CD; color: #856404; }
.badge-silver { background: #E8ECF1; color: #495057; }
.badge-bronze { background: #FCE4D6; color: #C0392B; }

/* Hot lead item */
.hot-lead-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    border-radius: 10px;
    margin-bottom: 6px;
    background: #FFF8F0;
    border-left: 3px solid #E67E22;
}
.hot-lead-name {
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    font-size: 13px;
    color: #1B2A4A;
}
.hot-lead-score {
    font-family: 'DM Sans', sans-serif;
    font-weight: 700;
    font-size: 14px;
    color: #E67E22;
    background: #FFF0DB;
    padding: 3px 10px;
    border-radius: 8px;
}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    font-weight: 500;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B2A4A 0%, #162240 100%);
}
[data-testid="stSidebar"] * {
    color: rgba(255,255,255,0.9) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label {
    color: rgba(255,255,255,0.7) !important;
    font-size: 12px !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
</style>
"""


def inject_css(st):
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_metric_card(label, value, delta=None, delta_suffix="vs prev", prefix="", color_override=None):
    """Render a styled metric card as HTML."""
    delta_html = ""
    if delta is not None:
        if delta > 0:
            delta_html = f'<div class="metric-delta delta-up">▲ +{delta}% {delta_suffix}</div>'
        elif delta < 0:
            delta_html = f'<div class="metric-delta delta-down">▼ {delta}% {delta_suffix}</div>'
        else:
            delta_html = f'<div class="metric-delta delta-neutral">● 0% {delta_suffix}</div>'

    top_bar = ""
    if color_override:
        top_bar = f"<style>.metric-card-{label.replace(' ','_')}::before {{ background: {color_override} !important; }}</style>"

    return f"""
    {top_bar}
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{prefix}{value}</div>
        {delta_html}
    </div>
    """


def render_section(title, icon="📊"):
    return f'<div class="section-title"><span class="icon">{icon}</span> {title}</div>'
