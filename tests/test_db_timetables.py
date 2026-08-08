"""Parser + offline ingestion tests against realistic API fixtures."""
import csv

from pipeline import config
from pipeline.ingest import db_timetables


def _berlin_rows():
    xml = (config.FIXTURES_DIR / "timetable_8011160_plan.xml").read_text(encoding="utf-8")
    return list(db_timetables.parse_timetable_xml(xml, 8011160))


def test_parses_all_events():
    rows = _berlin_rows()
    # 5 trains: 4 with ar+dp, 1 dp-only -> 9 events
    assert len(rows) == 9
    assert {r["event_type"] for r in rows} == {"ARRIVAL", "DEPARTURE"}


def test_delay_information_preserved():
    rows = _berlin_rows()
    ice = [r for r in rows if r["train_number"] == "857" and r["event_type"] == "ARRIVAL"][0]
    assert ice["planned_time"] == "2026-08-08T12:10:00"
    assert ice["changed_time"] == "2026-08-08T12:26:00"  # 16 min late
    on_time = [r for r in rows if r["train_number"] == "1204" and r["event_type"] == "ARRIVAL"][0]
    assert on_time["changed_time"] is None  # no change = on time


def test_cancellation_flag():
    rows = _berlin_rows()
    cancelled = [r for r in rows if r["cancelled"]]
    assert len(cancelled) == 1
    assert cancelled[0]["train_number"] == "2434"


def test_platform_change_captured():
    rows = _berlin_rows()
    flx = [r for r in rows if r["train_number"] == "1208" and r["event_type"] == "DEPARTURE"][0]
    assert flx["planned_platform"] == "14"
    assert flx["changed_platform"] == "14"


def test_offline_ingest_writes_csv(tmp_path):
    out = db_timetables.ingest(out_path=tmp_path / "stop_events.csv")
    with out.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) > 0
    assert set(rows[0].keys()) == set(db_timetables.CSV_COLUMNS)
    # both fixture stations present
    assert {r["station_eva"] for r in rows} == {"8011160", "8002549"}
