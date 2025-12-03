import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("nyc_neighborhoods")

class NYCOpenDataParser:
    """
    Parses JSON data fetched from NYC Open Data (e.g., Socrata NTA datasets).
    """
    def parse_nta_data(self, json_data: List[Dict[str, Any]], neighborhood_name: str) -> Dict[str, Any]:
        """
        Parses NTA (Neighborhood Tabulation Area) data from NYC Open Data.
        Looks for data matching the given neighborhood name.

        Args:
            json_data: A list of dictionaries, typically from a Socrata API response.
            neighborhood_name: The neighborhood name to search for.

        Returns:
            A dictionary with extracted data (e.g., area, related boundaries info),
            or an empty dictionary if no matching data is found.
        """
        extracted_info: Dict[str, Any] = {
            "area_from_open_data": "",
            "shape_length": "",
            "open_data_sources": []
        }

        if not json_data:
            logger.warning(f"No JSON data provided for {neighborhood_name} from NYC Open Data.")
            return extracted_info

        # Normalize neighborhood name for matching (e.g., "Maspeth" vs "Maspeth-Ridgewood")
        normalized_search_name = neighborhood_name.lower().replace(" ", "-")

        for record in json_data:
            nta_name = record.get("ntaname", "").lower()
            borough_name = record.get("boroughname", "").lower()

            # Attempt to match neighborhood name. This can be complex for NTAs.
            # Simple match: NTA name contains neighborhood name
            if normalized_search_name in nta_name or neighborhood_name.lower() == nta_name:
                extracted_info["area_from_open_data"] = record.get("shape_area", "")
                extracted_info["shape_length"] = record.get("shape_len", "")
                # We need a proper URL to cite as a source
                # For now, just add a generic source identifier
                extracted_info["open_data_sources"].append(f"NYC NTA Data (ntacode: {record.get('ntacode')})")
                
                # For simplicity, we'll take the first match.
                # A more robust parser might aggregate or find the best match.
                logger.info(f"Matched NTA data for {neighborhood_name} from NYC Open Data.")
                break
        
        if not extracted_info["area_from_open_data"]:
            logger.warning(f"Could not find specific NTA data for {neighborhood_name} in NYC Open Data response.")
        
        return extracted_info

if __name__ == '__main__':
    from src.lib.logger import setup_logging
    setup_logging(level=logging.INFO)

    parser = NYCOpenDataParser()

    # Sample JSON data mimicking Socrata NTA response
    sample_json_data = [
        {"ntacode": "QN27", "ntaname": "Maspeth-Ridgewood", "boroughname": "Queens", "shape_area": "123456.78", "shape_len": "9876.54"},
        {"ntacode": "BK64", "ntaname": "Williamsburg", "boroughname": "Brooklyn", "shape_area": "789012.34", "shape_len": "5432.10"},
        {"ntacode": "MN01", "ntaname": "Marble Hill-Inwood", "boroughname": "Manhattan", "shape_area": "30496870.00", "shape_len": "100000.00"}
    ]

    # Test case 1: Matching neighborhood
    print("\n--- Test Case 1: Matching neighborhood ---")
    extracted_maspeth = parser.parse_nta_data(sample_json_data, "Maspeth")
    print("Maspeth Data:", extracted_maspeth)
    assert extracted_maspeth["area_from_open_data"] == "123456.78"
    assert "NYC NTA Data" in extracted_maspeth["open_data_sources"][0]

    # Test case 2: No matching neighborhood
    print("\n--- Test Case 2: No matching neighborhood ---")
    extracted_bronx = parser.parse_nta_data(sample_json_data, "Bronx Park")
    print("Bronx Park Data:", extracted_bronx)
    assert extracted_bronx["area_from_open_data"] == ""
    assert not extracted_bronx["open_data_sources"]

    # Test case 3: Empty JSON data
    print("\n--- Test Case 3: Empty JSON data ---")
    extracted_empty = parser.parse_nta_data([], "Someplace")
    print("Empty Data:", extracted_empty)
    assert extracted_empty["area_from_open_data"] == ""
