import logging
import json
from datetime import date, datetime
from typing import Dict, Any, List, Optional
from src.models.neighborhood_profile import (
    NeighborhoodProfile, KeyDetails, NeighborhoodFacts, Boundaries,
    TransitAccessibility, CommuteTime
)
from src.services.nyc_open_data_fetcher import NYCOpenDataFetcher # Import Fetcher
from src.services.nyc_open_data_parser import NYCOpenDataParser   # Import Parser

logger = logging.getLogger("nyc_neighborhoods")

class DataNormalizer:
    def __init__(self,
                 version: str,
                 ratified_date: date,
                 last_amended_date: date,
                 nyc_open_data_fetcher: Optional[NYCOpenDataFetcher] = None,
                 nyc_open_data_parser: Optional[NYCOpenDataParser] = None,
                 nyc_open_data_dataset_id: Optional[str] = None):
        self.version = version
        self.ratified_date = ratified_date
        self.last_amended_date = last_amended_date
        self.nyc_open_data_fetcher = nyc_open_data_fetcher
        self.nyc_open_data_parser = nyc_open_data_parser
        self.nyc_open_data_dataset_id = nyc_open_data_dataset_id

    def normalize(self, raw_data: Dict[str, Any], neighborhood_name: str, borough: str) -> Optional[NeighborhoodProfile]:
        """
        Normalizes raw data extracted from Wikipedia (and potentially other sources)
        into a NeighborhoodProfile Pydantic model.
        """
        current_warnings = raw_data.get("warnings", [])
        
        # --- Supplement with NYC Open Data if available ---
        if self.nyc_open_data_fetcher and self.nyc_open_data_parser and self.nyc_open_data_dataset_id:
            logger.info(f"Attempting to supplement data for {neighborhood_name} with NYC Open Data.")
            # Construct a query to find the neighborhood by exact name.
            query_params = {
                "$where": f"ntaname = '{neighborhood_name}'"
            }
            
            open_data_raw_json = self.nyc_open_data_fetcher.fetch_data(self.nyc_open_data_dataset_id, query_params)

            if open_data_raw_json:
                open_data_parsed = self.nyc_open_data_parser.parse_nta_data(open_data_raw_json, neighborhood_name)
                
                # Update existing data with Open Data if it's more specific or fills gaps
                if open_data_parsed.get("area_from_open_data") and (not raw_data["neighborhood_facts"].get("area") or raw_data["neighborhood_facts"].get("area") == "N/A"):
                    raw_data["neighborhood_facts"]["area"] = open_data_parsed["area_from_open_data"]
                    current_warnings.append(f"Area supplemented by NYC Open Data for {neighborhood_name}.")
                
                # Add Open Data sources
                raw_data["sources"].extend(open_data_parsed.get("open_data_sources", []))
            else:
                current_warnings.append(f"Failed to fetch or parse NYC Open Data for {neighborhood_name}.")
        else:
            logger.debug("NYC Open Data fetcher/parser not provided to DataNormalizer.")


        # --- Handle KeyDetails ---
        # These are not directly from Wikipedia infobox, so we can set defaults or process later
        key_details_data = raw_data.get("key_details", {})
        key_details = KeyDetails(
            what_to_expect=key_details_data.get("what_to_expect", "Information not available."),
            unexpected_appeal=key_details_data.get("unexpected_appeal", "Information not available."),
            the_market=key_details_data.get("the_market", "Information not available.")
        )

        # --- Handle Boundaries ---
        boundaries_data = raw_data.get("neighborhood_facts", {}).get("boundaries", {})
        boundaries = Boundaries(
            east_to_west=boundaries_data.get("east_to_west", "Information not available."),
            north_to_south=boundaries_data.get("north_to_south", "Information not available."),
            adjacent_neighborhoods=boundaries_data.get("adjacent_neighborhoods", [])
        )

        # --- Handle NeighborhoodFacts ---
        neighborhood_facts_data = raw_data.get("neighborhood_facts", {})
        neighborhood_facts = NeighborhoodFacts(
            population=neighborhood_facts_data.get("population", "N/A"),
            population_density=neighborhood_facts_data.get("population_density", "N/A"),
            area=neighborhood_facts_data.get("area", "N/A"),
            boundaries=boundaries,
            zip_codes=neighborhood_facts_data.get("zip_codes", [])
        )
        if not neighborhood_facts.population or neighborhood_facts.population == "N/A":
            current_warnings.append(f"Population data missing for {neighborhood_name}.")
        if not neighborhood_facts.area or neighborhood_facts.area == "N/A":
            current_warnings.append(f"Area data missing for {neighborhood_name}.")

        # --- Handle TransitAccessibility ---
        transit_data = raw_data.get("transit_accessibility", {})
        transit_accessibility = TransitAccessibility(
            nearest_subways=transit_data.get("nearest_subways", []),
            major_stations=transit_data.get("major_stations", []),
            bus_routes=transit_data.get("bus_routes", []),
            rail_freight_other=transit_data.get("rail_freight_other", []),
            highways_major_roads=transit_data.get("highways_major_roads", [])
        )

        # --- Handle CommuteTimes (Optional) ---
        commute_times: Optional[List[CommuteTime]] = None
        # Wikipedia parser doesn't typically provide this, so it will be None by default

        # --- Construct NeighborhoodProfile ---
        try:
            profile = NeighborhoodProfile(
                version=self.version,
                ratified_date=self.ratified_date,
                last_amended_date=self.last_amended_date,
                neighborhood_name=neighborhood_name,
                borough=borough,
                summary=raw_data.get("summary", ""),
                key_details=key_details,
                around_the_block=raw_data.get("around_the_block", ""),
                neighborhood_facts=neighborhood_facts,
                transit_accessibility=transit_accessibility,
                commute_times=commute_times,
                sources=raw_data.get("sources", []),
                generation_date=datetime.now(),
                warnings=current_warnings
            )
            return profile
        except Exception as e:
            logger.error(f"Error normalizing data for {neighborhood_name} into NeighborhoodProfile: {e}")
            current_warnings.append(f"Failed to normalize data: {e}")
            return None # Return None if normalization fails

if __name__ == '__main__':
    from src.lib.logger import setup_logging
    from unittest.mock import MagicMock
    from src.services.web_fetcher import WebFetcher as RealWebFetcher # Use real WebFetcher
    from src.services.nyc_open_data_fetcher import NYCOpenDataFetcher as RealNYCOpenDataFetcher # Use real fetcher
    from src.services.nyc_open_data_parser import NYCOpenDataParser as RealNYCOpenDataParser # Use real parser

    setup_logging(level=logging.INFO)

    # --- Setup for demo ---
    dummy_wikipedia_raw_data = {
        "summary": "A sample summary from Wikipedia.",
        "key_details": {},
        "around_the_block": "A narrative about the area from Wikipedia.",
        "neighborhood_facts": {
            "population": "50,000",
            "population_density": "N/A", # Wikipedia might not have this, expect Open Data to supplement
            "area": "N/A", # Wikipedia might not have this, expect Open Data to supplement
            "boundaries": {
                "east_to_west": "Wikipedia East",
                "north_to_south": "Wikipedia North",
                "adjacent_neighborhoods": ["Wiki Neighbor A"]
            },
            "zip_codes": ["10001"]
        },
        "transit_accessibility": {
            "nearest_subways": ["A"],
            "major_stations": [],
            "bus_routes": [],
            "rail_freight_other": [],
            "highways_major_roads": []
        },
        "sources": ["https://en.wikipedia.org/wiki/Test_Neighborhood"],
        "warnings": ["Wikipedia did not have full boundary info."]
    }

    # Mock NYCOpenDataFetcher and Parser responses
    mock_web_fetcher_for_open_data = MagicMock(spec=RealWebFetcher)
    mock_web_fetcher_for_open_data.fetch.return_value = json.dumps([
        {"ntacode": "QN27", "ntaname": "Maspeth-Ridgewood", "boroughname": "Queens", "shape_area": "123456.78", "shape_len": "9876.54"}
    ])
    mock_nyc_open_data_fetcher = RealNYCOpenDataFetcher(web_fetcher=mock_web_fetcher_for_open_data)
    mock_nyc_open_data_parser = RealNYCOpenDataParser()

    # --- Test case: Supplementing data ---
    normalizer_with_open_data = DataNormalizer(
        version="1.0",
        ratified_date=date(2025, 1, 1),
        last_amended_date=date(2025, 1, 10),
        nyc_open_data_fetcher=mock_nyc_open_data_fetcher,
        nyc_open_data_parser=mock_nyc_open_data_parser,
        nyc_open_data_dataset_id="ntacode_dataset_placeholder"
    )
    profile_supplemented = normalizer_with_open_data.normalize(dummy_wikipedia_raw_data, "Maspeth", "Queens")

    if profile_supplemented:
        print("\n--- Normalized Profile (Supplemented with Open Data) ---")
        print(profile_supplemented.json(indent=2))
        assert profile_supplemented.neighborhood_facts.area == "123456.78" # Should be supplemented
        assert "Area supplemented by NYC Open Data for Maspeth." in profile_supplemented.warnings
        assert "NYC NTA Data (ntacode: QN27)" in profile_supplemented.sources # Should have open data source
    else:
        print("Normalization failed for Maspeth (supplemented).")
    
    # --- Test case: No Open Data provided ---
    normalizer_no_open_data = DataNormalizer(
        version="1.0",
        ratified_date=date(2025, 1, 1),
        last_amended_date=date(2025, 1, 10)
    )
    profile_no_open_data = normalizer_no_open_data.normalize(dummy_wikipedia_raw_data, "Testville", "Brooklyn")
    if profile_no_open_data:
        print("\n--- Normalized Profile (No Open Data) ---")
        print(profile_no_open_data.json(indent=2))
        assert "Area supplemented by NYC Open Data" not in profile_no_open_data.warnings
    else:
        print("Normalization failed for Testville (no Open Data).")
