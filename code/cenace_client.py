"""HTTP Client for CENACE SW-PML REST Web Service."""

import logging
import random
import time
from datetime import date
from typing import Any, Dict, List, Optional, Union
import httpx

from config import (
    API_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_TIMEOUT_SECONDS,
    SISTEMA,
)

logger = logging.getLogger(__name__)


class CenaceAPIError(Exception):
    """Custom exception raised when CENACE API responds with an error or unparseable payload."""
    pass


class CenaceClient:
    """Production-ready client for querying CENACE's SW-PML Web Service."""

    def __init__(
        self,
        base_url: str = API_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        request_delay: float = DEFAULT_REQUEST_DELAY,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.request_delay = request_delay
        # CENACE uses an internal self-signed certificate in chain; verify=False is required
        self.client = httpx.Client(
            verify=False,
            timeout=httpx.Timeout(self.timeout),
            headers={
                "User-Agent": "Arkham-LMP-DataPipeline/1.0",
                "Accept": "application/json",
            },
        )

    def close(self):
        """Close the underlying HTTP client session."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @staticmethod
    def format_date(dt: Union[date, str]) -> tuple[str, str, str]:
        """Convert a date or YYYY-MM-DD string into (YYYY, MM, DD)."""
        if isinstance(dt, str):
            parts = dt.split("-")
            return parts[0], parts[1].zfill(2), parts[2].zfill(2)
        return f"{dt.year:04d}", f"{dt.month:02d}", f"{dt.day:02d}"

    def build_url(
        self,
        process: str,
        nodes: Union[str, List[str]],
        start_date: Union[date, str],
        end_date: Union[date, str],
        sistema: str = SISTEMA,
        output_format: str = "JSON",
    ) -> str:
        """Construct the REST URL adhering to CENACE SW-PML specification."""
        if isinstance(nodes, list):
            node_str = ",".join(nodes)
        else:
            node_str = nodes

        y_ini, m_ini, d_ini = self.format_date(start_date)
        y_fin, m_fin, d_fin = self.format_date(end_date)

        # URL format: {base}/{sistema}/{proceso}/{lista_nodos}/{y_ini}/{m_ini}/{d_ini}/{y_fin}/{m_fin}/{d_fin}/{formato}
        return (
            f"{self.base_url}/{sistema}/{process}/{node_str}/"
            f"{y_ini}/{m_ini}/{d_ini}/{y_fin}/{m_fin}/{d_fin}/{output_format}"
        )

    def fetch_chunk(
        self,
        process: str,
        nodes: Union[str, List[str]],
        start_date: Union[date, str],
        end_date: Union[date, str],
        sistema: str = SISTEMA,
    ) -> Dict[str, Any]:
        """Fetch LMP data for a date chunk (<= 7 days) with exponential backoff and retries."""
        url = self.build_url(process, nodes, start_date, end_date, sistema=sistema)

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Attempt {attempt}/{self.max_retries} GET {url}")
                response = self.client.get(url)

                # CENACE returns 200 on success
                if response.status_code == 200:
                    payload = response.json()
                    status_text = payload.get("status")
                    if status_text == "OK":
                        if self.request_delay > 0:
                            time.sleep(self.request_delay)
                        return payload
                    elif status_text == "No Content":
                        logger.warning(f"CENACE reported 'No Content' for {url}")
                        return payload
                    else:
                        raise CenaceAPIError(
                            f"Unexpected API status: '{status_text}'. Full response: {payload}"
                        )

                # Retry on rate limit (429) or transient server errors (500, 502, 503, 504)
                if response.status_code in [429, 500, 502, 503, 504]:
                    backoff = (2 ** attempt) + random.uniform(0.5, 1.5)
                    logger.warning(
                        f"HTTP {response.status_code} received. Retrying in {backoff:.2f}s..."
                    )
                    time.sleep(backoff)
                    continue

                # Client errors (400, 401, 404)
                raise CenaceAPIError(
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )

            except (httpx.TimeoutException, httpx.NetworkError) as err:
                last_exception = err
                backoff = (2 ** attempt) + random.uniform(0.5, 1.5)
                logger.warning(
                    f"Network/timeout error ({err.__class__.__name__}): {err}. Retrying in {backoff:.2f}s..."
                )
                time.sleep(backoff)
            except Exception as e:
                # Catch JSON decode or other unexpected parsing issues
                last_exception = e
                backoff = (2 ** attempt) + random.uniform(0.5, 1.0)
                logger.warning(f"Error ({e.__class__.__name__}): {e}. Retrying in {backoff:.2f}s...")
                time.sleep(backoff)

        raise CenaceAPIError(
            f"Failed to fetch {url} after {self.max_retries} attempts. Last error: {last_exception}"
        )

