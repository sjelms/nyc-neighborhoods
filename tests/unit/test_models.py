import pytest
from datetime import date, datetime
from typing import List, Optional
from src.models.neighborhood_profile import (
    KeyDetails, Boundaries, NeighborhoodFacts, TransitAccessibility, CommuteTime, NeighborhoodProfile
)

@pytest.fixture
def valid_key_details_data():
    return {
        "what_to_expect": "Vibrant community.",
        "unexpected_appeal": "Hidden gems.",
        "the_market": "Competitive pricing."
    }

@pytest.fixture
def valid_boundaries_data():
    return {
        "east_to_west": "East to West street.",
        "north_to_south": "North to South street.",
        "adjacent_neighborhoods": ["Neighbor A", "Neighbor B"]
    }

@pytest.fixture
def valid_neighborhood_facts_data(valid_boundaries_data):
    return {
        "population": "100,000",
        "population_density": "10,000/sq mi",
        "area": "10 sq mi",
        "boundaries": valid_boundaries_data,
        "zip_codes": ["10001", "10002"]
    }

@pytest.fixture
def valid_transit_accessibility_data():
    return {
        "nearest_subways": ["A", "C", "E"],
        "major_stations": ["Station A"],
        "bus_routes": ["M1", "M2"],
        "rail_freight_other": [],
        "highways_major_roads": ["Highway 1"]
    }

@pytest.fixture
def valid_commute_time_data():
    return {
        "destination": "Downtown",
        "subway": "20 min",
        "drive": "30 min"
    }

@pytest.fixture
def valid_neighborhood_profile_data(
    valid_key_details_data,
    valid_neighborhood_facts_data,
    valid_transit_accessibility_data,
    valid_commute_time_data
):
    return {
        "version": "1.0",
        "ratified_date": date(2025, 1, 1),
        "last_amended_date": date(2025, 1, 10),
        "neighborhood_name": "Testville",
        "summary": "A test summary.",
        "key_details": valid_key_details_data,
        "around_the_block": "A narrative.",
        "neighborhood_facts": valid_neighborhood_facts_data,
        "transit_accessibility": valid_transit_accessibility_data,
        "commute_times": [valid_commute_time_data],
        "sources": ["http://source1.com"],
        "generation_date": datetime(2025, 1, 10, 10, 0, 0),
        "warnings": []
    }

class TestPydanticModels:
    def test_key_details_creation(self, valid_key_details_data):
        key_details = KeyDetails(**valid_key_details_data)
        assert key_details.what_to_expect == "Vibrant community."

    def test_boundaries_creation(self, valid_boundaries_data):
        boundaries = Boundaries(**valid_boundaries_data)
        assert "Neighbor A" in boundaries.adjacent_neighborhoods

    def test_neighborhood_facts_creation(self, valid_neighborhood_facts_data):
        facts = NeighborhoodFacts(**valid_neighborhood_facts_data)
        assert facts.population == "100,000"
        assert isinstance(facts.boundaries, Boundaries)

    def test_transit_accessibility_creation(self, valid_transit_accessibility_data):
        transit = TransitAccessibility(**valid_transit_accessibility_data)
        assert "A" in transit.nearest_subways

    def test_commute_time_creation(self, valid_commute_time_data):
        commute = CommuteTime(**valid_commute_time_data)
        assert commute.destination == "Downtown"

    def test_neighborhood_profile_creation(self, valid_neighborhood_profile_data):
        profile = NeighborhoodProfile(**valid_neighborhood_profile_data)
        assert profile.neighborhood_name == "Testville"
        assert isinstance(profile.key_details, KeyDetails)
        assert profile.ratified_date == date(2025, 1, 1)

    def test_neighborhood_profile_optional_commute_times(self, valid_neighborhood_profile_data):
        data_no_commute = valid_neighborhood_profile_data.copy()
        data_no_commute["commute_times"] = None
        profile = NeighborhoodProfile(**data_no_commute)
        assert profile.commute_times is None

    def test_neighborhood_profile_missing_required_field(self, valid_neighborhood_profile_data):
        invalid_data = valid_neighborhood_profile_data.copy()
        del invalid_data["neighborhood_name"]
        with pytest.raises(Exception): # Pydantic ValidationError is a subclass of Exception
            NeighborhoodProfile(**invalid_data)

    def test_neighborhood_profile_incorrect_date_type(self, valid_neighborhood_profile_data):
        invalid_data = valid_neighborhood_profile_data.copy()
        invalid_data["ratified_date"] = "not-a-date"
        with pytest.raises(Exception):
            NeighborhoodProfile(**invalid_data)

    def test_list_fields_empty(self, valid_neighborhood_profile_data):
        data_empty_lists = valid_neighborhood_profile_data.copy()
        data_empty_lists["sources"] = []
        data_empty_lists["warnings"] = []
        profile = NeighborhoodProfile(**data_empty_lists)
        assert profile.sources == []
        assert profile.warnings == []
