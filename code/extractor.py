"""Extractor module to iterate through date chunks, query CENACE, and cache raw JSON."""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple, Union
from tqdm import tqdm

from cenace_client import CenaceClient
from config import (
    END_DATE,
    MAX_DAYS_PER_REQUEST,
    MONCLOVA_NODES,
    PROCESSES,
    RAW_DATA_DIR,
    SISTEMA,
    START_DATE,
)

logger = logging.getLogger(__name__)


def generate_date_chunks(
    start: Union[date, str],
    end: Union[date, str],
    chunk_size_days: int = MAX_DAYS_PER_REQUEST,
) -> Generator[Tuple[date, date], None, None]:
    """Generate (chunk_start, chunk_end) date pairs where each chunk is at most chunk_size_days long."""
    if isinstance(start, str):
        cur_date = datetime.strptime(start, "%Y-%m-%d").date()
    else:
        cur_date = start

    if isinstance(end, str):
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    else:
        end_date = end

    while cur_date <= end_date:
        next_date = min(cur_date + timedelta(days=chunk_size_days - 1), end_date)
        yield cur_date, next_date
        cur_date = next_date + timedelta(days=1)


class CenaceExtractor:
    """Manages chunked extraction and local raw caching for CENACE PML series."""

    def __init__(
        self,
        nodes: Optional[List[str]] = None,
        raw_dir: Path = RAW_DATA_DIR,
        client: Optional[CenaceClient] = None,
    ):
        self.nodes = nodes or MONCLOVA_NODES
        self.raw_dir = Path(raw_dir)
        self.client = client or CenaceClient()
        self._owns_client = client is None

    def close(self):
        if self._owns_client and self.client:
            self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _get_cache_path(self, process: str, start: date, end: date) -> Path:
        process_dir = self.raw_dir / process
        process_dir.mkdir(parents=True, exist_ok=True)
        return process_dir / f"chunk_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.json"

    def _load_cached_chunk(self, path: Path) -> Optional[Dict]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("status") == "OK" and data.get("Resultados"):
                    return data
            except Exception as e:
                logger.warning(f"Corrupt cache file {path}: {e}. Re-downloading.")
        return None

    def extract_process(
        self,
        process: str,
        start_date: Union[date, str] = START_DATE,
        end_date: Union[date, str] = END_DATE,
        force_reload: bool = False,
    ) -> List[Path]:
        """Extract all chunks for a given market process (MDA or MTR). Returns list of raw JSON filepaths."""
        chunks = list(generate_date_chunks(start_date, end_date, MAX_DAYS_PER_REQUEST))
        saved_files = []

        logger.info(
            f"Starting extraction for process={process}, {len(chunks)} chunks, "
            f"range [{start_date} to {end_date}], {len(self.nodes)} nodes."
        )

        pbar = tqdm(chunks, desc=f"Extracting {process}")
        for chunk_start, chunk_end in pbar:
            cache_file = self._get_cache_path(process, chunk_start, chunk_end)

            if not force_reload:
                cached_data = self._load_cached_chunk(cache_file)
                if cached_data is not None:
                    saved_files.append(cache_file)
                    pbar.set_postfix_str(f"Cached {chunk_start} to {chunk_end}")
                    continue

            # Fetch fresh chunk
            pbar.set_postfix_str(f"Fetching {chunk_start} to {chunk_end}")
            try:
                data = self.client.fetch_chunk(
                    process=process,
                    nodes=self.nodes,
                    start_date=chunk_start,
                    end_date=chunk_end,
                    sistema=SISTEMA,
                )
            except Exception as e:
                logger.error(f"Error fetching chunk {chunk_start} to {chunk_end}: {e}")
                # Try fallback: fetch node-by-node if multi-node failed
                data = self._fetch_nodes_individually(process, chunk_start, chunk_end)

            # Persist raw response
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            saved_files.append(cache_file)

        logger.info(f"Completed extraction for process={process}. {len(saved_files)} chunks ready.")
        return saved_files

    def _fetch_nodes_individually(self, process: str, chunk_start: date, chunk_end: date) -> Dict:
        """Fallback method to fetch each node individually and merge Resultados."""
        logger.info(f"Falling back to node-by-node fetch for {chunk_start} to {chunk_end}...")
        merged_resultados = []
        base_meta = None

        for node in self.nodes:
            node_data = self.client.fetch_chunk(
                process=process,
                nodes=[node],
                start_date=chunk_start,
                end_date=chunk_end,
                sistema=SISTEMA,
            )
            if not base_meta:
                base_meta = {
                    "nombre": node_data.get("nombre", "PML"),
                    "proceso": process,
                    "sistema": SISTEMA,
                    "area": node_data.get("area", "PÚBLICA"),
                    "status": "OK",
                }
            merged_resultados.extend(node_data.get("Resultados", []))

        base_meta["Resultados"] = merged_resultados
        return base_meta


def run_extraction(
    processes: Optional[List[str]] = None,
    start_date: str = START_DATE,
    end_date: str = END_DATE,
    force_reload: bool = False,
) -> Dict[str, List[Path]]:
    """Convenience runner for extracting both MDA and MTR."""
    proc_list = processes or PROCESSES
    results = {}
    with CenaceExtractor() as extractor:
        for proc in proc_list:
            results[proc] = extractor.extract_process(
                process=proc,
                start_date=start_date,
                end_date=end_date,
                force_reload=force_reload,
            )
    return results

