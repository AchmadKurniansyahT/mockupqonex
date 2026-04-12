# 🚗 DSS Motor — Executive Lead Management Dashboard

Dashboard Streamlit untuk monitoring dan analisis lead management system DSS Motor.

## Struktur Dashboard

### 🏠 Executive Dashboard (Main Page)
Halaman utama dengan overview menyeluruh:
- **KPI Cards**: Total Leads, Cold/Hot/Deal/Handover count & rate, Contact Rate
- **Lead Response Time**: Overall distribution + Per Sales breakdown (toggle)
- **Lead Funnel**: Visualisasi funnel dari Leads → Cold → Hot → Deal → Handover
- **Lead Sources**: Pie chart + tabel dengan conversion per source
- **Quick Business Health**: Lead-to-Hot rate, Lead-to-Deal rate, Monthly Leads vs Conversion chart
- **Sales Leaderboard**: Ranking sales by leads, handover, conversion
- **Hot Leads by Sales**: List sales dengan jumlah hot leads
- **Daily Lead Trend**: Trend harian lead masuk (30 hari terakhir)
- **Lead Aging**: Distribusi umur lead aktif (0-1d, 1-3d, 3-7d, >7d)
- **Lost Lead Analysis**: Breakdown alasan cancel/reject
- **Monthly Handover & Growth**: Trend handover bulanan dengan growth %

### 👥 Sales Performance (Page 2)
Deep-dive performa per sales:
- Performance matrix (tabel lengkap semua metrik per sales)
- Stacked bar chart distribusi leads by status per sales
- Box plot response time comparison
- Monthly leads trend per sales

### 📡 Lead Sources (Page 3)
Analisis efektivitas channel:
- Source KPIs (top source, best conversion)
- Treemap distribusi leads by Online/Offline → Source
- Conversion rate bar chart per source
- Monthly area chart trend per top 5 source
- Online vs Offline performance comparison

### ⏳ Lead Aging & Lost (Page 4)
Monitoring lead health:
- Active leads aging KPIs
- Age distribution histogram
- Aging by status breakdown
- Sales × Age bucket heatmap
- Cancel/Reject reason analysis
- Monthly cancel trend
- Cancel rate per sales

## Filter Global (Sidebar)
- **Periode**: Minggu Ini, Minggu Lalu, Bulan Ini, Bulan Lalu, Tahun Ini, Lifetime
- **Filter Sales**: Multi-select per sales person

## Setup & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Taruh CSV files di folder yang sama atau di /mnt/user-data/uploads/
# Files yang dibutuhkan:
#   - Prospect__-_10042026.csv
#   - Progress_-_10042026.csv
#   - Project-User_-_10042026.csv
#   - Option_-_10042026.csv

# Run dashboard
streamlit run 🏠_Executive_Dashboard.py
```

## Data Schema

| File | Deskripsi |
|------|-----------|
| `Prospect__-_10042026.csv` | Data prospect/lead utama |
| `Progress_-_10042026.csv` | History perubahan status per prospect |
| `Project-User_-_10042026.csv` | Data sales/user |
| `Option_-_10042026.csv` | Master data (status, source, reason) |
| `Project_-_10042026.csv` | Data project/dealer |

## Kalkulasi Penting

- **Response Time**: `first_contact - created_at` (dalam menit)
- **Lead Age**: `last_followup - hari_ini` (hanya untuk status leads/cold/hot/deal)
- **Handover Age**: `handover_progress.created_at - prospect.created_at`
- **Conversion Rate**: `handover_count / total_leads * 100`
- **Contact Rate**: `leads_with_first_contact / total_leads * 100`
- **Filter waktu** berdasarkan `created_at` prospect (kapan lead masuk)
