import logging
import json
from typing import Dict, Any, Optional
from src.services.web_fetcher import WebFetcher

logger = logging.getLogger("nyc_neighborhoods")

class NYCOpenDataFetcher:
    """
    Fetches data from NYC Open Data (Socrata API) endpoints.
    Uses WebFetcher for actual HTTP requests.
    """
    # This is a placeholder base URL. A real implementation would need
    # to derive this from the dataset ID or have specific endpoints.
    # For demonstration, we'll use a hypothetical structure.
    # A real dataset might be: https://data.cityofnewyork.us/resource/9a8g-qc86.json (for example)
    SOCRATA_BASE_URL = "https://data.cityofnewyork.us/resource/"

    def __init__(self, web_fetcher: WebFetcher):
        self.web_fetcher = web_fetcher

    def fetch_data(self, dataset_id: str, query_params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Fetches JSON data from a specified NYC Open Data (Socrata) dataset.

        Args:
            dataset_id: The ID of the Socrata dataset (e.g., "9a8g-qc86").
            query_params: Optional dictionary of query parameters for the API.

        Returns:
            Parsed JSON data as a dictionary, or None if fetching fails.
        """
        full_url = f"{self.SOCRATA_BASE_URL}{dataset_id}.json"
        
        # Add query parameters
        if query_params:
            from urllib.parse import urlencode
            full_url += f"?{urlencode(query_params)}"

        logger.info(f"Attempting to fetch data from NYC Open Data: {full_url}")
        
        json_string = self.web_fetcher.fetch(full_url)
        if json_string:
            try:
                data = json.loads(json_string)
                logger.info(f"Successfully fetched and parsed data from {full_url}")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from NYC Open Data ({full_url}): {e}")
                return None
        return None

if __name__ == '__main__':
    from src.lib.logger import setup_logging
    from unittest.mock import MagicMock
    from src.services.web_fetcher import WebFetcher as RealWebFetcher # Use the real WebFetcher for demo

    setup_logging(level=logging.INFO)

    # --- Demo with mocked WebFetcher (no actual network calls) ---
    print("\n--- Demo with Mocked WebFetcher ---")
    mock_web_fetcher = MagicMock(spec=RealWebFetcher)
    mock_web_fetcher.fetch.return_value = json.dumps([
        {"ntacode": "QN27", "ntaname": "Maspeth", "boroughname": "Queens", "shape_area": "123456"},
        {"ntacode": "BK64", "ntaname": "Williamsburg", "boroughname": "Brooklyn", "shape_area": "789012"}
    ])
    
    fetcher = NYCOpenDataFetcher(web_fetcher=mock_web_fetcher)
    data = fetcher.fetch_data("dummy_dataset_id", {"$where": "ntaname='Maspeth'"})
    if data:
        print(f"Mocked Data Fetched: {json.dumps(data, indent=2)}")
    else:
        print("Mocked data fetch failed.")

    mock_web_fetcher.fetch.assert_called_once_with(
        "https://data.cityofnewyork.us/resource/dummy_dataset_id.json?$where=ntaname%3D%27Maspeth%27"
    )

    # --- Demo with real WebFetcher (requires network access) ---
    # WARNING: This will make a real network request.
    # It might fail if the dummy_dataset_id is not real or the query is invalid.
    # For a real integration, identify a specific, small, and stable public dataset.
    print("\n--- Demo with Real WebFetcher (Skipped to avoid unnecessary network calls in automated run) ---")
    # real_web_fetcher = RealWebFetcher()
    # real_fetcher = NYCOpenDataFetcher(web_fetcher=real_web_fetcher)
    # real_data = real_fetcher.fetch_data("n2rz-nfzh", {"$limit": 1})
    # if real_data:
    #     print(f"Real Data Fetched (first item): {json.dumps(real_data[0], indent=2)}")
    # else:
    #     print("Real data fetch failed.")
