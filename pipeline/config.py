"""Central configuration. All secrets come from .env (never committed)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FIXTURES_DIR = ROOT / "tests" / "fixtures"

# Deutsche Bahn API Marketplace
DB_API_BASE = "https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1"
DB_CLIENT_ID = os.getenv("DB_CLIENT_ID", "")
DB_API_KEY = os.getenv("DB_API_KEY", "")

# Stations tracked (EVA numbers = DB station IDs). Long-distance network core.
STATIONS = {
    8011160: "Berlin Hbf",
    8002549: "Hamburg Hbf",
    8000207: "Köln Hbf",
    8000105: "Frankfurt (Main) Hbf",
    8000261: "München Hbf",
    8000096: "Stuttgart Hbf",
    8010205: "Leipzig Hbf",
    8000152: "Hannover Hbf",
    8000080: "Dortmund Hbf",
    8000085: "Düsseldorf Hbf",
}

# Google BigQuery (free sandbox tier works; auth via ADC or service-account key)
GCP = {
    "project": os.getenv("GCP_PROJECT_ID", ""),
    "location": os.getenv("BQ_LOCATION", "EU"),
}

# Dataset layout (BigQuery has no schemas-inside-database; one dataset per layer)
BQ_DATASETS = {
    "raw": "rail_ops_raw",
    "staging": "rail_ops_staging",
    "marts": "rail_ops_marts",
}
