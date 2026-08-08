# Power BI Dashboard — Build Guide

Target: a 3-page report connected to BigQuery `rail_ops_marts`. Budget ~1–2 hours in Power BI Desktop.

## 1. Connect

1. Power BI Desktop → **Get Data → Google BigQuery**.
2. Sign in with the Google account that owns the GCP project.
3. **Import** mode (sandbox-friendly; DirectQuery optional talking point).
4. Expand your project → `rail_ops_marts` → select: `dim_date`, `dim_station`, `dim_route`, `fact_stop_events`, `fact_train_runs`, `v_kpi_ops_daily`, `v_kpi_route_daily`, `v_kpi_exec_daily`.

## 2. Model view

Star schema relationships (single direction, 1:many from dim to fact):

- `dim_date[date_key]` → `fact_stop_events[date_key]`, `fact_train_runs[date_key]`, `v_kpi_ops_daily[date_key]`, `v_kpi_route_daily[date_key]`
- `dim_station[station_key]` → `fact_stop_events[station_key]`
- `dim_route[route_key]` → `fact_train_runs[route_key]`, `v_kpi_route_daily[route_key]`

Mark `dim_date` as the date table. Paste measures from `measures.dax` into a dedicated `_Measures` table.

## 3. Pages

### Page 1 — Executive Overview
- 4 KPI cards: `Punctuality % (6 min)`, `Avg Arrival Delay (min)`, `Avg Load Factor`, `Total Revenue EUR`
- Line chart: Punctuality % (6 min) by `dim_date[date_key]`, with 90% target constant line
- Combo chart: Revenue (columns) + Load Factor (line) by date
- Slicer: date range. Footer text box: *"Commercial figures are synthetic (see repo docs); operational figures are real DB open data."*

### Page 2 — Operations Deep-Dive
- Matrix: `dim_station[station_name]` rows × Punctuality % / Avg Delay / Cancellation Rate, conditional formatting (red > 10 min)
- Bar chart: Avg Arrival Delay by station, sorted desc
- Column chart: delay by `fact_stop_events[planned_hour]` (peak-hour pattern)
- Decomposition tree: Avg Arrival Delay by station → hour → train category

### Page 3 — Commercial (Synthetic)
- Header banner: **"SYNTHETIC DATA — demand model, not real bookings"**
- Table: routes × passengers, load factor, revenue, revenue/seat-km
- Line: `Load Factor 7d Avg` by date, split by route
- Scatter: Load Factor vs Avg Max Arrival Delay by route (does unreliability depress demand?)

## 4. Publish

Publish to Power BI Service (free tier) → share the public "Publish to web" link in the README, plus 2–3 screenshots in `powerbi/screenshots/`.
