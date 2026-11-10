"""Parser module to parse raw JSON responses into clean, validated DataFrames and Parquet datasets."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd

from config import NODE_METADATA, PROCESSED_DATA_DIR, RAW_DATA_DIR

logger = logging.getLogger(__name__)


def parse_chunk_file(file_path: Path) -> List[Dict]:
    """Parse a single raw CENACE JSON chunk file into a list of flattened record dicts."""
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sistema = data.get("sistema", "SIN")
    proceso = data.get("proceso", "UNKNOWN")

    for node_result in data.get("Resultados", []):
        clv_nodo = node_result.get("clv_nodo")
        node_meta = NODE_METADATA.get(clv_nodo, {})
        node_name = node_meta.get("name", clv_nodo)
        voltage_kv = node_meta.get("voltage_kv", None)

        for val in node_result.get("Valores", []):
            try:
                fecha_str = val.get("fecha")
                hora_int = int(val.get("hora"))
                pml = float(val.get("pml")) if val.get("pml") is not None else None
                pml_ene = float(val.get("pml_ene")) if val.get("pml_ene") is not None else None
                pml_per = float(val.get("pml_per")) if val.get("pml_per") is not None else None
                pml_cng = float(val.get("pml_cng")) if val.get("pml_cng") is not None else None

                records.append({
                    "sistema": sistema,
                    "proceso": proceso,
                    "clv_nodo": clv_nodo,
                    "nombre_nodo": node_name,
                    "tension_kv": voltage_kv,
                    "fecha": fecha_str,
                    "hora": hora_int,
                    "pml": pml,
                    "pml_ene": pml_ene,
                    "pml_per": pml_per,
                    "pml_cng": pml_cng,
                })
            except Exception as e:
                logger.warning(f"Error parsing value record {val} in {file_path}: {e}")

    return records


def build_dataframe_for_process(
    process: str,
    raw_dir: Path = RAW_DATA_DIR,
) -> pd.DataFrame:
    """Read all raw JSON chunks for a process, flatten, clean, sort, and construct timestamps."""
    process_dir = Path(raw_dir) / process
    if not process_dir.exists():
        raise FileNotFoundError(f"Raw directory for process {process} not found at {process_dir}")

    json_files = sorted(process_dir.glob("chunk_*.json"))
    if not json_files:
        raise FileNotFoundError(f"No raw chunk JSON files found in {process_dir}")

    all_records = []
    for jf in json_files:
        records = parse_chunk_file(jf)
        all_records.extend(records)

    df = pd.DataFrame(all_records)
    if df.empty:
        raise ValueError(f"No records parsed from {len(json_files)} files in {process_dir}")

    # Remove any potential duplicates (by node, date, and hour)
    initial_len = len(df)
    df = df.drop_duplicates(subset=["clv_nodo", "fecha", "hora"])
    if len(df) < initial_len:
        logger.info(f"Dropped {initial_len - len(df)} duplicate records for {process}.")

    # Build continuous datetime timestamps
    # Hour 1 corresponds to [00:00, 01:00) interval start
    df["timestamp"] = pd.to_datetime(df["fecha"]) + pd.to_timedelta(df["hora"] - 1, unit="h")

    # CENACE arithmetic validation check: PML = PML_ENE + PML_PER + PML_CNG
    df["pml_component_sum"] = df["pml_ene"] + df["pml_per"] + df["pml_cng"]
    df["pml_diff"] = (df["pml"] - df["pml_component_sum"]).round(4)

    # Sort deterministically
    df = df.sort_values(by=["clv_nodo", "timestamp"]).reset_index(drop=True)

    # Reorder columns
    ordered_cols = [
        "timestamp",
        "fecha",
        "hora",
        "clv_nodo",
        "nombre_nodo",
        "tension_kv",
        "sistema",
        "proceso",
        "pml",
        "pml_ene",
        "pml_per",
        "pml_cng",
        "pml_component_sum",
        "pml_diff",
    ]
    return df[ordered_cols]


def export_curated_datasets(
    raw_dir: Path = RAW_DATA_DIR,
    output_dir: Path = PROCESSED_DATA_DIR,
) -> Dict[str, Path]:
    """Parse both MDA and MTR, save individual Parquets and a combined wide dataset."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    exported_files = {}

    mda_df = None
    mtr_df = None

    # Process MDA
    try:
        mda_df = build_dataframe_for_process("MDA", raw_dir=raw_dir)
        mda_path = output_dir / "mda_monclova_lmp.parquet"
        mda_df.to_parquet(mda_path, index=False, engine="pyarrow")
        exported_files["MDA"] = mda_path
        logger.info(f"Saved MDA curated dataset to {mda_path} ({len(mda_df):,} rows)")
    except Exception as e:
        logger.error(f"Error processing MDA dataset: {e}")

    # Process MTR
    try:
        mtr_df = build_dataframe_for_process("MTR", raw_dir=raw_dir)
        mtr_path = output_dir / "mtr_monclova_lmp.parquet"
        mtr_df.to_parquet(mtr_path, index=False, engine="pyarrow")
        exported_files["MTR"] = mtr_path
        logger.info(f"Saved MTR curated dataset to {mtr_path} ({len(mtr_df):,} rows)")
    except Exception as e:
        logger.error(f"Error processing MTR dataset: {e}")

    # If both are present, create a merged dataset with price spread (MTR - MDA)
    if mda_df is not None and mtr_df is not None:
        merged = pd.merge(
            mda_df[["timestamp", "fecha", "hora", "clv_nodo", "nombre_nodo", "tension_kv", "pml", "pml_ene", "pml_per", "pml_cng"]],
            mtr_df[["timestamp", "clv_nodo", "pml", "pml_ene", "pml_per", "pml_cng"]],
            on=["timestamp", "clv_nodo"],
            suffixes=("_mda", "_mtr"),
            how="outer",
        )
        merged["pml_spread_mtr_minus_mda"] = (merged["pml_mtr"] - merged["pml_mda"]).round(4)
        merged = merged.sort_values(by=["clv_nodo", "timestamp"]).reset_index(drop=True)

        combined_path = output_dir / "combined_monclova_lmp.parquet"
        merged.to_parquet(combined_path, index=False, engine="pyarrow")
        exported_files["COMBINED"] = combined_path
        logger.info(f"Saved combined MDA/MTR dataset to {combined_path} ({len(merged):,} rows)")

    return exported_files

