"""Main CLI entrypoint to execute the CENACE LMP Data Extraction Pipeline."""

import argparse
import logging
import sys
from pathlib import Path

# Ensure code directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import END_DATE, PROCESSES, START_DATE
from extractor import run_extraction
from parser import build_dataframe_for_process, export_curated_datasets
from validator import print_validation_report, validate_dataframe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PipelineRunner")


def main():
    parser = argparse.ArgumentParser(description="Extract and process CENACE PML data.")
    parser.add_argument(
        "--processes",
        nargs="+",
        default=PROCESSES,
        help="Market processes to extract (e.g. MDA MTR). Default: MDA MTR",
    )
    parser.add_argument(
        "--start-date",
        default=START_DATE,
        help=f"Start date in YYYY-MM-DD format (default: {START_DATE})",
    )
    parser.add_argument(
        "--end-date",
        default=END_DATE,
        help=f"End date in YYYY-MM-DD format (default: {END_DATE})",
    )
    parser.add_argument(
        "--force-reload",
        action="store_true",
        help="Ignore cached raw JSON files and re-download from CENACE API.",
    )
    args = parser.parse_args()

    logger.info("=== STEP 1: DOWNLOADING RAW CHUNKS FROM CENACE ===")
    run_extraction(
        processes=args.processes,
        start_date=args.start_date,
        end_date=args.end_date,
        force_reload=args.force_reload,
    )

    logger.info("=== STEP 2: PARSING, NORMALIZING, AND EXPORTING DATASETS ===")
    exported = export_curated_datasets()
    for name, path in exported.items():
        logger.info(f"Exported {name} -> {path}")

    logger.info("=== STEP 3: RUNNING DATA QUALITY AND INTEGRITY VALIDATIONS ===")
    for proc in args.processes:
        try:
            df = build_dataframe_for_process(proc)
            report = validate_dataframe(df, process_name=proc)
            print_validation_report(report)
        except Exception as e:
            logger.error(f"Failed to validate process {proc}: {e}")

    logger.info("=== PIPELINE EXECUTION COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()

