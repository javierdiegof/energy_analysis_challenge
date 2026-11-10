"""Configuration for CENACE PML Data Extraction Pipeline."""

from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SOURCE_DIR = PROJECT_ROOT / "source"

# CENACE API Settings
API_BASE_URL = "https://ws01.cenace.gob.mx:8082/SWPML/SIM"
SISTEMA = "SIN"
PROCESSES = ["MDA", "MTR"]

# Monclova Load-Zone Nodes (from official CENACE NodosP Catalog)
MONCLOVA_NODES = [
    "06AEO-115",  # Acero (115 kV)
    "06AHM-400",  # Ahmsa (400 kV)
    "06FRO-115",  # Frontera (115 kV)
    "06GRA-115",  # Granjas (115 kV)
    "06MON-115",  # Monclova (115 kV)
    "06MON-230",  # Monclova (230 kV)
    "06RGS-115",  # Regidores (115 kV)
    "06TKS-115",  # Teksid (115 kV)
    "06XOC-115",  # Xochitilli (115 kV)
]

NODE_METADATA = {
    "06AEO-115": {"name": "Acero", "voltage_kv": 115.0, "substation": "Acero"},
    "06AHM-400": {"name": "Ahmsa", "voltage_kv": 400.0, "substation": "Ahmsa"},
    "06FRO-115": {"name": "Frontera", "voltage_kv": 115.0, "substation": "Frontera"},
    "06GRA-115": {"name": "Granjas", "voltage_kv": 115.0, "substation": "Granjas"},
    "06MON-115": {"name": "Monclova", "voltage_kv": 115.0, "substation": "Monclova"},
    "06MON-230": {"name": "Monclova", "voltage_kv": 230.0, "substation": "Monclova"},
    "06RGS-115": {"name": "Regidores", "voltage_kv": 115.0, "substation": "Regidores"},
    "06TKS-115": {"name": "Teksid", "voltage_kv": 115.0, "substation": "Teksid"},
    "06XOC-115": {"name": "Xochitilli", "voltage_kv": 115.0, "substation": "Xochitilli"},
}

# Extraction Date Range
START_DATE = "2024-01-01"
END_DATE = "2025-06-30"

# Technical constraints from CENACE API manual
MAX_DAYS_PER_REQUEST = 7
MAX_NODES_PER_REQUEST = 20
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 5
DEFAULT_REQUEST_DELAY = 0.35  # Politeness delay between queries (seconds)

