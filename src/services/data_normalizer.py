import logging
from datetime import date, datetime
from typing import Dict, Any, List, Optional
from src.models.neighborhood_profile import (
    NeighborhoodProfile, KeyDetails, NeighborhoodFacts, Boundaries,
    TransitAccessibility, CommuteTime
)

logger = logging.getLogger("nyc_neighborhoods")

class DataNormalizer:
    def __init__(self, version: str, ratified_date: date, last_amended_date: date):
        self.version = version
        self.ratified_date = ratified_date
        self.last_amended_date = last_amended_date

    def normalize(self, raw_data: Dict[str, Any], neighborhood_name: str) -> Optional[NeighborhoodProfile]:
        """
        Normalizes raw data extracted from Wikipedia (and potentially other sources)
        into a NeighborhoodProfile Pydantic model.
        """
        current_warnings = raw_data.get("warnings", [])
        
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
    setup_logging(level=logging.INFO)

    # Dummy raw data from WikipediaParser
    dummy_raw_data = {
        "summary": "A sample summary.",
        "key_details": {},
        "around_the_block": "A narrative about the area.",
        "neighborhood_facts": {
            "population": "100,000",
            "population_density": "10,000/sq mi",
            "area": "5 sq mi",
            "boundaries": {
                "east_to_west": "East St.",
                "north_to_south": "North Ave.",
                "adjacent_neighborhoods": ["Town A", "Town B"]
            },
            "zip_codes": ["10001", "10002"]
        },
        "transit_accessibility": {
            "nearest_subways": ["A", "C"],
            "major_stations": ["Station X"],
            "bus_routes": ["M15"],
            "rail_freight_other": [],
            "highways_major_roads": ["I-95"]
        },
        "commute_times": None,
        "sources": ["https://en.wikipedia.org/wiki/Sample_Neighborhood"],
        "warnings": ["Infobox data missing for some fields."]
    }

    # Test with valid data
    normalizer = DataNormalizer(
        version="1.0",
        ratified_date=date(2025, 1, 1),
        last_amended_date=date(2025, 1, 10)
    )
    profile = normalizer.normalize(dummy_raw_data, "Sampleville")
    
    if profile:
        print("\n--- Normalized Profile (Sampleville) ---")
        print(profile.json(indent=2))
        assert profile.neighborhood_name == "Sampleville"
        assert "Population data missing" not in profile.warnings
        assert profile.neighborhood_facts.boundaries.east_to_west == "East St."
    else:
        print("Normalization failed for Sampleville.")

    # Test with missing critical data (e.g., population)
    dummy_raw_data_missing_pop = dummy_raw_data.copy()
    dummy_raw_data_missing_pop["neighborhood_facts"]["population"] = ""
    profile_missing_pop = normalizer.normalize(dummy_raw_data_missing_pop, "MissingPopville")
    
    if profile_missing_pop:
        print("\n--- Normalized Profile (MissingPopville) ---")
        print(profile_missing_pop.json(indent=2))
        assert "Population data missing for MissingPopville." in profile_missing_pop.warnings
    else:
        print("Normalization failed for MissingPopville.")

    # Test with entirely empty raw data
    empty_raw_data = {}
    profile_empty = normalizer.normalize(empty_raw_data, "Emptyville")
    if profile_empty:
        print("\n--- Normalized Profile (Emptyville) ---")
        print(profile_empty.json(indent=2))
        assert "Population data missing for Emptyville." in profile_empty.warnings
    else:
        print("Normalization failed for Emptyville (expected to fail gracefully).")
