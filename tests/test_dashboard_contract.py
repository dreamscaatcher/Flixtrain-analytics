"""Guards for the dashboard source of truth: history, labels, measure shape."""
import re

from google.cloud import bigquery

from pipeline import config
from pipeline.load.bigquery_loader import write_disposition_for

_PAREN = re.compile(r"\s*\([^)]*\)")
_SUFFIX = re.compile(r"\s+(Hbf|Sued|Bad Bf|Bf)$")


def _city(name: str) -> str:
    """Same two replacements as dim_route.route_label in 10_dimensions.sql."""
    return _SUFFIX.sub("", _PAREN.sub("", name))


def test_history_appends_and_snapshots_truncate():
    assert (
        write_disposition_for("rail_ops_raw.stop_events_history")
        == bigquery.WriteDisposition.WRITE_APPEND
    )
    assert (
        write_disposition_for("rail_ops_raw.stop_events")
        == bigquery.WriteDisposition.WRITE_TRUNCATE
    )
    assert (
        write_disposition_for("rail_ops_raw.train_runs")
        == bigquery.WriteDisposition.WRITE_TRUNCATE
    )


def test_staging_unions_history_and_prefers_observed_changes():
    sql = (config.ROOT / "sql/20_staging/staging.sql").read_text(encoding="utf-8")
    assert "rail_ops_raw.stop_events_history" in sql
    assert "UNION ALL" in sql
    assert "changed_time IS NOT NULL" in sql
    assert "loaded_at DESC" in sql


def test_short_labels_exist_and_match_the_legend_examples():
    sql = (config.ROOT / "sql/30_marts/10_dimensions.sql").read_text(encoding="utf-8")
    assert "station_name_short" in sql
    assert "route_label" in sql
    assert "Hbf|Sued|Bad Bf|Bf" in sql
    assert _city("Freiburg (Breisgau) Hbf") == "Freiburg"
    assert _city("Frankfurt (Main) Sued") == "Frankfurt"
    assert _city("Basel Bad Bf") == "Basel"
    assert f"{_city('Karlsruhe Hbf')} – {_city('Freiburg (Breisgau) Hbf')}" == "Karlsruhe – Freiburg"


def test_measures_are_ratios_with_format_strings():
    dax = (config.ROOT / "powerbi/measures.dax").read_text(encoding="utf-8")
    assert "v_kpi_ops_daily[punctuality_6min]" not in dax
    assert "v_kpi_station" not in dax
    assert 'fact_stop_events[event_type] = "ARRIVAL"' in dax
    assert "fact_stop_events[is_punctual_6]" in dax
    assert "SUM ( v_kpi_route_daily[seat_km] )" in dax
    assert "HASONEVALUE ( dim_route[route_key] )" in dax
    assert "Filter Summary" in dax
    for fmt in ("0.0%", "#,0", "€#,0", "€0.000", "0.00"):
        assert f"// Format: {fmt}" in dax


def test_spec_names_every_slicer_and_the_header():
    spec = (config.ROOT / "powerbi/DASHBOARD_SPEC.md").read_text(encoding="utf-8")
    for needle in (
        "Rail Ops Analytics",
        "dim_date[date_key]",
        "dim_station[station_name]",
        "dim_train[train_category]",
        "dim_route[route_label]",
        "dim_route[origin]",
        "dim_route[destination]",
        "Route Distance (km)",
        "Filter Summary",
        "Service date",
    ):
        assert needle in spec
