# Power BI Dashboard — Build and Fix Checklist

Report name: **Rail Ops Analytics**. Three pages, canvas **1280 × 720** (16:9). The warehouse is the source of truth for the numbers. This file is the source of truth for how the report is built. Paste measures from [`measures.dax`](measures.dax). Definitions: [`../docs/kpi_definitions.md`](../docs/kpi_definitions.md).

The published report is edited in Power BI Desktop. Do not rebuild the model from scratch if the tables below are already imported. Refresh after the warehouse job has run at least once on this version so the new columns exist.

## Why the published report looks the way it does

**Punctuality 75.01% vs 0.68.** Same rule, two non-additive totals.

- The card is the unweighted mean of the daily rates (`AVERAGE` of `v_kpi_ops_daily[punctuality_6min]`). The line is that measure by date, left on a 0–1 format, so the card can read 75.01% while the axis reads 0.75.
- The station matrix is not that measure. `v_kpi_ops_daily` has no station, so a station breakdown is the station-grain rate (`v_kpi_station[punctuality_6min]` or an implicit average of the flag). Its total weights each station equally and was shown as a raw decimal: 0.68, not 68%.
- Both are the share of **arrival** events with `delay_minutes < 6`. There is no train-level punctuality. `fact_train_runs` has no delay columns. Cancelled arrivals stay in the base. That predicate was not changed.

After this checklist the card, the line, and the matrix total all use `Punctuality % (6 min)`. They match under the same slicers. The card will not stay 75.01% unless every day in the filter has the same number of arrivals. That is the fix.

**The line only spans a few dates (8–11 Aug on the published report).** Data coverage, not a visual filter.

- One ingest asks for 4 hours of `/plan` plus one `/fchg` snapshot, in the near future. Departed trains fall out of `/fchg`. The API will not backfill August.
- Each load replaced `stop_events`, so the next run deleted the previous dates. The line hides dates with no rows. Commercial data is regenerated for 90 days, so revenue still has a long axis.
- History is now appended. The axis grows as the every-3-hours job lands. Do not add a filter that pins the chart to those four dates. Until a few refreshes have run, a short axis is the remaining coverage, and the chart subtitle says so.

**"Sum of distance_km".** Route length is repeated once per route-day. Sum multiplies kilometres by the number of days. The scatter uses `Route Distance (km)`.

## 0. Warehouse refresh

- [ ] Run `python -m pipeline.run_pipeline` (or wait for the scheduled job) before refreshing Power BI. The first run copies the current snapshot into `stop_events_history`, then appends the new window.
- [ ] Leave `--hours` at 4. A longer window stores trains that have not departed as on time.
- [ ] Confirm `dim_route` has `route_label` and `v_kpi_route_daily` has `seats_total` and `seat_km`. If those columns are missing, the model was refreshed too early.

## 1. Connect

- [ ] Get data → **Google BigQuery** → **Import**.
- [ ] Project → `rail_ops_marts`. Select: `dim_date`, `dim_station`, `dim_route`, `dim_train`, `fact_stop_events`, `fact_train_runs`, `v_kpi_ops_daily`, `v_kpi_route_daily`, `v_kpi_exec_daily`.
- [ ] Do **not** import `v_kpi_station`. It has no date, so a date slicer cannot filter it.

## 2. Model

Star schema, single direction, one-to-many from the dimension:

- [ ] `dim_date[date_key]` → `fact_stop_events[date_key]`, `fact_train_runs[date_key]`, `v_kpi_ops_daily[date_key]`, `v_kpi_route_daily[date_key]`, `v_kpi_exec_daily[date_key]`
- [ ] `dim_station[station_key]` → `fact_stop_events[station_key]`
- [ ] `dim_route[route_key]` → `fact_train_runs[route_key]`, `v_kpi_route_daily[route_key]`
- [ ] `dim_train[train_key]` → `fact_stop_events[train_key]`
- [ ] Mark `dim_date` as a date table on `date_key`.
- [ ] Home → Enter data → name the table `_Measures` (one dummy column). Paste [`measures.dax`](measures.dax). Delete the dummy column. Delete any older copies of these measures (`Total Revenue EUR`, `Revenue per Seat-km`, `Revenue MTD`) so a visual cannot keep the old field.

What each slicer actually filters (do not turn relationships bidirectional to "make it filter everything"):

| Slicer | Filters punctuality, delay, cancellations | Filters passengers, load factor, revenue |
|---|---|---|
| Service date | Yes | Yes |
| Station | Yes | No. Commercial facts have no station. |
| Train category | Yes | No. Synthetic train numbers are not DB train numbers. |
| Route, origin, destination | No. Real stops are not joined to synthetic runs. | Yes |

### Formats

Set the format on the **measure** (select it → Measure tools → Format → Custom). A format set only on the card is why the card showed a percent and the line stayed on 0–1. Display folder is the comment above each block in `measures.dax`.

| Measure | Custom format |
|---|---|
| `Punctuality % (6 min)` | `0.0%` |
| `Punctuality % (15 min)` | `0.0%` |
| `Punctuality Target (6 min)` | `0.0%` |
| `Avg Arrival Delay (min)` | `0.00` |
| `Cancellation Rate` | `0.0%` |
| `Platform Change Rate` | `0.0%` |
| `Punctuality vs Prev Period` | `+0.0%;-0.0%;0.0%` |
| `Total Revenue (EUR)` | `€#,0` |
| `Total Passengers` | `#,0` |
| `Avg Load Factor` | `0.0%` |
| `Revenue per Seat-km (EUR)` | `€0.000` |
| `Route Distance (km)` | `#,0` |
| `Revenue MTD (EUR)` | `€#,0` |
| `Load Factor 7d Avg` | `0.0%` |
| `Active Date Range`, `Slicer Route Label`, `Slicer Station Label`, `Slicer Category Label`, `Filter Summary` | Text (`@`) |

### Hide in Report view

So they cannot be dropped on a visual by accident:

- [ ] `fact_stop_events[is_punctual_6]`, `fact_stop_events[is_punctual_15]`
- [ ] On `v_kpi_ops_daily`: `punctuality_6min`, `punctuality_15min`, `avg_arrival_delay_min`, `cancellation_rate`, `platform_change_rate`
- [ ] On `v_kpi_route_daily`: `avg_load_factor`, `distance_km`, `revenue_per_seat_km`

The additive columns (`arrival_events`, `punctual_arrivals_6`, `seats_total`, `seat_km`, …) stay visible for audit. Do not put them on a visual. The measures already divide them.

## 3. Report chrome

Apply on every page.

- [ ] Canvas: **1280 × 720**. Page background white. Margin used below is 16 px. Card gutter is 12 px. Slicer gutter is 8 px.
- [ ] Rename pages: **Executive Overview**, **Operations**, **Commercial**.
- [ ] Header text box, x=16 y=8 w=360 h=32, Segoe UI 20 pt bold: `Rail Ops Analytics`
- [ ] Page-name text box, x=16 y=40 w=360 h=20, Segoe UI 12 pt:
  - Executive Overview
  - Operations
  - Commercial
- [ ] Card, x=400 y=8 w=864 h=52. Measure: `Filter Summary`. Title **off**. Category label **off**. Callout 12 pt, display units None, word wrap on. This is the report header's filter line (`Dates: … | Routes: … | Stations: … | Categories: …`).

### Slicers

Dropdowns unless noted. Style the header of each slicer to the title below (not the raw column name). View → **Sync slicers**: sync a field across the pages where it appears, and keep it visible on those pages.

| Title | Field | Style | Pages |
|---|---|---|---|
| Service date | `dim_date[date_key]` (the column, not the auto date hierarchy) | Between | All three |
| Station | `dim_station[station_name]` | Dropdown | Executive Overview, Operations |
| Train category | `dim_train[train_category]` | Dropdown | Executive Overview, Operations |
| Route | `dim_route[route_label]` | Dropdown | Executive Overview, Commercial |
| Origin | `dim_route[origin]` | Dropdown | Executive Overview, Commercial |
| Destination | `dim_route[destination]` | Dropdown | Executive Overview, Commercial |

- [ ] Service date: because `dim_date` runs from 1 Jan 2026 through 31 Dec 2027, set the slicer's filter to **Relative date → is in the last → 90 → days** (calendar). That opens on the commercial window. Do not filter the slicer, or any chart, to 8–11 Aug. If the punctuality line is empty, the captured service dates sit outside that 90-day window: clear the relative filter and widen Between.
- [ ] Executive Overview slicer row, y=68 h=60. Six slicers, w=201, x = 16, 225, 434, 643, 852, 1061 (last w=203).
- [ ] Operations slicer row, y=68 h=60. Three slicers (date, station, category), w=410, x = 16, 434, 852 (last w=412).
- [ ] Commercial slicer row, y=68 h=60. Four slicers (date, route, origin, destination), w=306, x = 16, 330, 644, 958.

For every visual below: Format → General → Title → **Title text** is the title given. Do not leave the generated title (`Punctuality % (6 min) by date_key`, `Sum of distance_km`). Turn the axis title on and set the text. Display units None unless a row says otherwise.

## 4. Executive Overview

KPI row, y=140 h=100. Four cards, w=303, x = 16, 331, 646, 961. Equal widths, 12 px gutters. Title on, category label off, display units **None** (so revenue shows `€24,670,000` from the measure format, not `24.67M`).

| x | Title | Measure |
|---|---|---|
| 16 | Punctuality (6 min) | `Punctuality % (6 min)` |
| 331 | Avg arrival delay (min) | `Avg Arrival Delay (min)` |
| 646 | Avg load factor | `Avg Load Factor` |
| 961 | Total revenue (EUR) | `Total Revenue (EUR)` |

- [ ] Line chart, x=16 y=252 w=618 h=400.
  - Title: `Punctuality (6 min) by service date`
  - Subtitle: `Service dates captured so far. The axis lengthens after each pipeline refresh. The Timetables API does not backfill departed trains.`
  - X axis: `dim_date[date_key]`, continuous, title `Service date`
  - Y axis: `Punctuality % (6 min)`, title `Punctuality (6 min)`, minimum 0, maximum 1
  - Analytics → Constant line → value `Punctuality Target (6 min)`, name `90% target`
  - Markers on, data labels off, legend off
- [ ] Line and clustered column chart, x=646 y=252 w=618 h=400.
  - Title: `Revenue and load factor by service date`
  - X axis: `dim_date[date_key]`, title `Service date`
  - Columns: `Total Revenue (EUR)`. Column axis title `Revenue (EUR)`. Start at 0.
  - Line: `Avg Load Factor`, on the secondary axis. Line axis title `Load factor`.
  - Rename the series `Revenue` and `Load factor`.
- [ ] Footer text box, x=16 y=664 w=1248 h=40, 11 pt italic: `Occupancy and revenue are a synthetic demand model (see the repo docs). Routes, delays, and cancellations are real.`

`Platform Change Rate`, `Punctuality % (15 min)`, `Punctuality vs Prev Period`, and `Revenue MTD (EUR)` are in the model and not placed on a page.

## 5. Operations

These three cards use the same measures as page 1. With the synced date, station, and category slicers, they show the same values as the executive ops cards.

KPI row, y=140 h=100. Three cards, w=408, x = 16, 436, 856. Title on, category label off, display units None.

| x | Title | Measure |
|---|---|---|
| 16 | Punctuality (6 min) | `Punctuality % (6 min)` |
| 436 | Avg arrival delay (min) | `Avg Arrival Delay (min)` |
| 856 | Cancellation rate | `Cancellation Rate` |

- [ ] Matrix, x=16 y=252 w=760 h=210.
  - Title: `Punctuality and delay by station`
  - Rows: `dim_station[station_name]`
  - Values, in order: `Punctuality % (6 min)`, `Avg Arrival Delay (min)`, `Cancellation Rate`
  - Row subtotals **on**. The total is the measure with no station filter. It equals the punctuality card. It is not the average of the station rows.
  - Sort by `Avg Arrival Delay (min)` descending.
  - Conditional formatting on `Avg Arrival Delay (min)` only: Rules → if value **is greater than 10** → font `#B03A2E`. Else no colour.
  - Do not add `punctuality_6min`, `is_punctual_6`, or any column from `v_kpi_station`.
- [ ] Clustered bar, x=788 y=252 w=476 h=210.
  - Title: `Average arrival delay by station`
  - Y axis: `dim_station[station_name]` (category, do not summarize)
  - X axis: `Avg Arrival Delay (min)`, title `Average arrival delay (min)`
  - Data labels on. Sort the axis by `Avg Arrival Delay (min)` descending. Legend off.
- [ ] Clustered column, x=16 y=474 w=618 h=230.
  - Title: `Average arrival delay by planned hour`
  - X axis: `fact_stop_events[planned_hour]`. Do not summarize. Sort the axis by `planned_hour` ascending. Title `Planned hour`.
  - Y axis: `Avg Arrival Delay (min)`, title `Average arrival delay (min)`
- [ ] Decomposition tree, x=646 y=474 w=618 h=230.
  - Title: `Arrival delay breakdown`
  - Analyze: `Avg Arrival Delay (min)`
  - Explain by, in this order: `dim_station[station_name]`, `fact_stop_events[planned_hour]`, `dim_train[train_category]`

If a station name is cut off, switch that one visual's category to `dim_station[station_name_short]` (`Frankfurt (Main) Hbf` → `Frankfurt Hbf`). The matrix and bar use the full name by default.

## 6. Commercial

- [ ] Banner text box, x=16 y=136 w=1248 h=36, 12 pt bold: `Routes are FlixTrain's real network (GTFS). Occupancy and revenue are a synthetic demand model, not real bookings.`
- [ ] Table, x=16 y=180 w=1248 h=200.
  - Title: `Routes`
  - Columns, in order, with these titles:
    - `dim_route[origin]` → `Origin`
    - `dim_route[destination]` → `Destination`
    - `Total Passengers` → `Passengers`
    - `Avg Load Factor` → `Load factor`
    - `Total Revenue (EUR)` → `Revenue (EUR)`
    - `Revenue per Seat-km (EUR)` → `Revenue per seat-km (EUR)`
  - Values come from the measures, so passengers show thousands separators and the rates show as percents. Sort by `Total Revenue (EUR)` descending. Total row on.
- [ ] Line chart, x=16 y=392 w=618 h=312.
  - Title: `Load factor, 7-day average, by route`
  - X axis: `dim_date[date_key]`, title `Service date`
  - Y axis: `Load Factor 7d Avg`, title `Load factor`
  - Legend: `dim_route[route_label]`. Series names are short city pairs (`Karlsruhe – Freiburg`), not `Freiburg (Breisg…`.
- [ ] Scatter chart, x=646 y=392 w=618 h=312.
  - Title: `Load factor vs route distance`
  - Subtitle: `Each point is one route. Distance is route length, not a sum across days.`
  - X axis: `Route Distance (km)`, title `Route distance (km)`
  - Y axis: `Avg Load Factor`, title `Load factor`
  - Details: `dim_route[route_label]`
  - Size: `Total Passengers`
  - Do not put `distance_km` on this visual. Do not plot delay here: synthetic train numbers (`1200`–`1209`) and real DB train numbers are different ID spaces, so there is no join.

## 7. Check before publishing

- [ ] With only the date slicer restricting the page, Executive Overview and Operations show the same punctuality, the same average arrival delay, and (on Operations) a matrix total equal to the punctuality card.
- [ ] No visual title contains `date_key`, `Sum of`, or a truncated city (`Freiburg (Breisg`).
- [ ] The punctuality axis is labelled in percent and runs from 0% to 100%, with the 90% target line.
- [ ] The four executive cards are the same width and the same gap.
- [ ] Passengers in the route table use a thousands separator. Revenue uses `€` and a thousands separator.
- [ ] Station, train category, route, origin, and destination slicers are on the pages in the table above, and the date slicer is on all three.
- [ ] The header `Rail Ops Analytics` and `Filter Summary` are on all three pages.
- [ ] Publish to the Power BI service and keep the existing public link. Replace the screenshots in `powerbi/screenshots/` (`page1_executive.jpg`, `page2_operations.jpg`, `page3_commercial.jpg`) after the pages match this checklist. Do not change those filenames.
