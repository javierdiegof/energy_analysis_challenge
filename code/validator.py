"""Validation module for checking data integrity, completeness, and quality."""

import logging
from typing import Dict, List
import numpy as np
import pandas as pd

from config import MONCLOVA_NODES

logger = logging.getLogger(__name__)


def validate_dataframe(df: pd.DataFrame, process_name: str = "MDA") -> Dict:
    """Run comprehensive quality assurance checks on a parsed LMP dataframe."""
    report = {
        "process": process_name,
        "total_rows": len(df),
        "unique_nodes": df["clv_nodo"].nunique(),
        "nodes_found": sorted(df["clv_nodo"].unique().tolist()),
        "date_min": str(df["timestamp"].min()),
        "date_max": str(df["timestamp"].max()),
        "passed": True,
        "checks": {},
    }

    # 1. Check all expected nodes are present
    missing_nodes = set(MONCLOVA_NODES) - set(report["nodes_found"])
    report["checks"]["nodes_completeness"] = {
        "status": "PASS" if not missing_nodes else "FAIL",
        "missing_nodes": list(missing_nodes),
        "expected_count": len(MONCLOVA_NODES),
        "actual_count": len(report["nodes_found"]),
    }
    if missing_nodes:
        report["passed"] = False

    # 2. Check completeness per node (expected 13,128 hourly timestamps)
    expected_hours_per_node = 547 * 24  # 13,128 hours between 2024-01-01 and 2025-06-30
    node_counts = df.groupby("clv_nodo")["timestamp"].count().to_dict()
    missing_timestamps_per_node = {}

    for node, count in node_counts.items():
        if count != expected_hours_per_node:
            missing_timestamps_per_node[node] = {
                "actual": int(count),
                "expected": expected_hours_per_node,
                "diff": int(expected_hours_per_node - count),
            }

    report["checks"]["hourly_completeness"] = {
        "status": "PASS" if not missing_timestamps_per_node else "FAIL",
        "expected_per_node": expected_hours_per_node,
        "anomalous_nodes": missing_timestamps_per_node,
    }
    if missing_timestamps_per_node:
        report["passed"] = False

    # 3. Check for Nulls / NaNs
    null_counts = df.isnull().sum().to_dict()
    has_nulls = any(c > 0 for c in null_counts.values())
    report["checks"]["null_values"] = {
        "status": "PASS" if not has_nulls else "FAIL",
        "null_counts": {k: int(v) for k, v in null_counts.items() if v > 0},
    }
    if has_nulls:
        report["passed"] = False

    # 4. Check for Duplicate Timestamps per Node
    duplicates = df.duplicated(subset=["clv_nodo", "timestamp"]).sum()
    report["checks"]["duplicates"] = {
        "status": "PASS" if duplicates == 0 else "FAIL",
        "duplicate_count": int(duplicates),
    }
    if duplicates > 0:
        report["passed"] = False

    # 5. Check Mathematical Consistency: PML == PML_ENE + PML_PER + PML_CNG
    tolerance = 0.05
    arithmetic_violations = (df["pml_diff"].abs() > tolerance).sum()
    report["checks"]["component_additivity"] = {
        "status": "PASS" if arithmetic_violations == 0 else "WARNING",
        "violations_count": int(arithmetic_violations),
        "max_discrepancy": float(df["pml_diff"].abs().max()),
    }

    # 6. Negative price frequency & summary stats
    negative_prices = (df["pml"] < 0).sum()
    report["checks"]["price_distribution"] = {
        "negative_price_count": int(negative_prices),
        "negative_price_pct": float(round((negative_prices / len(df)) * 100, 2)),
        "min_pml": float(df["pml"].min()),
        "max_pml": float(df["pml"].max()),
        "mean_pml": float(round(df["pml"].mean(), 2)),
        "std_pml": float(round(df["pml"].std(), 2)),
    }

    return report


def print_validation_report(report: Dict) -> None:
    """Print an executive console-friendly summary of the validation report."""
    print("=" * 60)
    print(f" DATA VALIDATION REPORT: {report['process']}")
    print("=" * 60)
    print(f"Overall Status:    {'PASSED' if report['passed'] else 'ATTENTION NEEDED'}")
    print(f"Total Rows:        {report['total_rows']:,}")
    print(f"Date Range:        {report['date_min']} to {report['date_max']}")
    print(f"Nodes Evaluated:   {len(report['nodes_found'])} nodes")
    print("-" * 60)

    for check_name, details in report["checks"].items():
        status = details.get("status", "INFO")
        print(f"[{status}] {check_name}: {details}")

    print("=" * 60)

