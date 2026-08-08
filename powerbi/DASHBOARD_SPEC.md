# Power BI Dashboard — Build Guide

Target: a 3-page report connected live to Snowflake `RAIL_OPS.MARTS`. Budget ~1–2 hours in Power BI Desktop.

## 1. Connect

1. Power BI Desktop → **Get Data → Snowflake**.
2. Server: `<account>.snowflakecomputing.com`, Warehouse: `RAIL_OPS_WH`.
3. **Import** mode (trial account; DirectQuery optional talking point).
4. Select from `RAIL_OPS.MARTS`: `DIM_DATE`, `DIM_STATION`, `DIM_ROUTE`, `FACT_STOP_EVENTS`, `FACT_TRAIN_RUNS`, `V_KPI_OPS_DAILY`, `V_KPI_ROUTE_DAILY`, `V_KPI_EXEC_DAILY`.

## 2. Model view

Star schema relationships (single direction, 1:many from dim to fact):

- `DIM_DATE[DATE_KEY]` → `FACT_STOP_EVENTS[DATE_KEY]`, `FACT_TRAIN_RUNS[DATE_KEY]`, `V_KPI_OPS_DAILY[DATE_KEY]`, `V_KPI_ROUTE_DAILY[DATE_KEY]`
- `DIM_STATION[STATION_KEY]` → `FACT_STOP_EVENTS[STATION_KEY]`
- `DIM_ROUTE[ROUTE_KEY]` → `FACT_TRAIN_RUNS[ROUTE_KEY]`, `V_KPI_ROUTE_DAILY[ROUTE_KEY]`

Mark `DIM_DATE` as the date table. Paste measures from `measures.dax` into a dedicated `_Measures` table.

## 3. Pages

### Page 1 — Executive Overview
- 4 KPI cards: `Punctuality % (6 min)`, `Avg Arrival Delay (min)`, `Avg Load Factor`, `Total Revenue EUR`
- Line chart: Punctuality % (6 min) by `DIM_DATE[DATE_KEY]`, with 90% target constant line
- Combo chart: Revenue (columns) + Load Factor (line) by date
- Slicer: date range. Footer text box: *"Commercial figures are synthetic (see repo docs); operational figures are real DB open data."*

### Page 2 — Operations Deep-Dive
- Matrix: `DIM_STATION[STATION_NAME]` rows × Punctuality % / Avg Delay / Cancellation Rate, conditional formatting (red > 10 min)
- Bar chart: Avg Arrival Delay by station, sorted desc
- Column chart: delay by `FACT_STOP_EVENTS[PLANNED_HOUR]` (peak-hour pattern)
- Decomposition tree: Avg Arrival Delay by station → hour → train category

### Page 3 — Commercial (Synthetic)
- Header banner: **"SYNTHETIC DATA — demand model, not real bookings"**
- Table: routes × passengers, load factor, revenue, revenue/seat-km
- Line: `Load Factor 7d Avg` by date, split by route
- Scatter: Load Factor vs Avg Max Arrival Delay by route (does unreliability depress demand?)

## 4. Publish

Publish to Power BI Service (free tier) → share the public "Publish to web" link in the README, plus 2–3 screenshots in `powerbi/screenshots/`.
