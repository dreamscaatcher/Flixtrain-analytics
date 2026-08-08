"""Synthetic generator tests: determinism + business-rule invariants."""
import csv

from pipeline.ingest import synthetic


def _generate(tmp_path, **kwargs):
    out = synthetic.generate(out_path=tmp_path / "runs.csv", days=30, **kwargs)
    with out.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_expected_row_count(tmp_path):
    rows = _generate(tmp_path)
    assert len(rows) == 30 * len(synthetic.ROUTES) * synthetic.DEPARTURES_PER_ROUTE_DAY


def test_deterministic_with_seed(tmp_path):
    a = _generate(tmp_path, seed=42)
    b = _generate(tmp_path, seed=42)
    assert a == b


def test_business_invariants(tmp_path):
    for r in _generate(tmp_path):
        sold, total = int(r["seats_sold"]), int(r["seats_total"])
        assert 0 <= sold <= total
        expected_rev = round(sold * float(r["avg_ticket_price_eur"]), 2)
        assert abs(float(r["revenue_eur"]) - expected_rev) < 0.01
        assert r["is_synthetic"] == "True"  # honesty flag always set


def test_friday_demand_uplift(tmp_path):
    """Fridays should on average outsell Tuesdays (demand model sanity)."""
    from datetime import date
    rows = _generate(tmp_path)
    by_weekday = {1: [], 4: []}  # Tue=1, Fri=4
    for r in rows:
        wd = date.fromisoformat(r["service_date"]).weekday()
        if wd in by_weekday:
            by_weekday[wd].append(int(r["seats_sold"]))
    avg = {wd: sum(v) / len(v) for wd, v in by_weekday.items()}
    assert avg[4] > avg[1]
