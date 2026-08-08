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

# Snowflake
SNOWFLAKE = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT", ""),
    "user": os.getenv("SNOWFLAKE_USER", ""),
    "password": os.getenv("SNOWFLAKE_PASSWORD", ""),
    "role": os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "RAIL_OPS_WH"),
    "database": os.getenv("SNOWFLAKE_DATABASE", "RAIL_OPS"),
}
