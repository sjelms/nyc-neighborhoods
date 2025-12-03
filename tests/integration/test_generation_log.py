import pytest
import json
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import date, datetime

from src.lib.generation_log import GenerationLog
from src.services.web_fetcher import WebFetcher
from src.services.wikipedia_parser import WikipediaParser
from src.services.data_normalizer import DataNormalizer
from src.lib.template_renderer import TemplateRenderer
from src.services.profile_generator import ProfileGenerator
from src.models.neighborhood_profile import (
    KeyDetails, Boundaries, NeighborhoodFacts, TransitAccessibility, NeighborhoodProfile
)

# --- Fixtures for mocked dependencies and setup ---

@pytest.fixture
def mock_web_fetcher_for_log_test():
    """Mocks WebFetcher to return minimal successful HTML."""
    mock = MagicMock(spec=WebFetcher)
    mock.fetch.return_value = """<div class="mw-parser-output"><p>Summary.</p></div>"""
    return mock

@pytest.fixture
def mock_parser_for_log_test():
    """Mocks WikipediaParser for log tests."""
    mock = MagicMock(spec=WikipediaParser)
    mock.parse.return_value = {
        "summary": "Summary text.",
        "key_details": {}, "around_the_block": "",
        "neighborhood_facts": {"population": "1", "area": "1", "zip_codes": [], "boundaries": {"adjacent_neighborhoods": []}},
        "transit_accessibility": {}, "sources": [], "warnings": []
    }
    return mock

@pytest.fixture
def mock_normalizer_for_log_test():
    """Mocks DataNormalizer to return a basic profile based on input name."""
    def normalize_side_effect(raw_data, neighborhood_name, borough, **kwargs):
        return NeighborhoodProfile(
            version="1.0", ratified_date=date(2025, 12, 1), last_amended_date=date(2025, 12, 1),
            neighborhood_name=neighborhood_name, borough=borough, summary="Summary.",
            key_details=KeyDetails(what_to_expect="", unexpected_appeal="", the_market=""),
            around_the_block="",
            neighborhood_facts=NeighborhoodFacts(
                population="1", area="1", zip_codes=[],
                boundaries=Boundaries(east_to_west="", north_to_south="", adjacent_neighborhoods=[])
            ),
            transit_accessibility=TransitAccessibility(nearest_subways=[], major_stations=[], bus_routes=[], rail_freight_other=[], highways_major_roads=[]),
            sources=[], generation_date=datetime.now(), warnings=[]
        )
    mock = MagicMock(spec=DataNormalizer)
    mock.normalize.side_effect = normalize_side_effect
    return mock

@pytest.fixture
def mock_renderer_for_log_test():
    """Mocks TemplateRenderer."""
    mock = MagicMock(spec=TemplateRenderer)
    mock.render.side_effect = lambda profile: f"Profile for {profile.neighborhood_name}"
    return mock

@pytest.fixture
def log_test_setup(tmp_path, mock_web_fetcher_for_log_test, mock_parser_for_log_test, mock_normalizer_for_log_test, mock_renderer_for_log_test):
    """Provides a fully configured ProfileGenerator and paths for log tests."""
    output_dir = tmp_path / "output"
    log_file_path = tmp_path / "logs" / "generation_log.json"
    
    generation_log = GenerationLog(log_file_path)
    
    generator = ProfileGenerator(
        web_fetcher=mock_web_fetcher_for_log_test,
        wikipedia_parser=mock_parser_for_log_test,
        data_normalizer=mock_normalizer_for_log_test,
        template_renderer=mock_renderer_for_log_test,
        output_dir=output_dir,
        generation_log=generation_log
    )
    
    return generator, output_dir, log_file_path

class TestGenerationLogFunctionality:

    def test_default_behavior_skips_existing(self, log_test_setup):
        generator, output_dir, log_file_path = log_test_setup

        # Pre-populate log with Maspeth
        generator.generation_log.add_entry({
            "neighborhood_name": "Maspeth", "borough": "Queens",
            "unique_id": "maspeth-queens",
            "generation_date": "2024-01-01T00:00:00"
        })

        neighborhood_list = [
            {"Neighborhood": "Maspeth", "Borough": "Queens"},
            {"Neighborhood": "Williamsburg", "Borough": "Brooklyn"}
        ]
        
        results = generator.generate_profiles_from_list(neighborhood_list)

        assert results["total"] == 2
        assert results["success"] == 1
        assert results["skipped"] == 1
        assert results["failed"] == 0
        assert (output_dir / "Williamsburg_Brooklyn.md").exists()
        assert not (output_dir / "Maspeth_Queens.md").exists() # Should not be re-created

    def test_force_regenerate_processes_all(self, log_test_setup):
        generator, output_dir, log_file_path = log_test_setup

        # Pre-populate log with Maspeth
        generator.generation_log.add_entry({
            "neighborhood_name": "Maspeth", "borough": "Queens",
            "unique_id": "maspeth-queens",
            "generation_date": "2024-01-01T00:00:00"
        })

        neighborhood_list = [
            {"Neighborhood": "Maspeth", "Borough": "Queens"},
            {"Neighborhood": "Williamsburg", "Borough": "Brooklyn"}
        ]
        
        results = generator.generate_profiles_from_list(neighborhood_list, force_regenerate=True)

        assert results["total"] == 2
        assert results["success"] == 2
        assert results["skipped"] == 0
        assert results["failed"] == 0
        assert (output_dir / "Maspeth_Queens.md").exists()
        assert (output_dir / "Williamsburg_Brooklyn.md").exists()

        log_data = json.loads(log_file_path.read_text())
        maspeth_log_entry = next(e for e in log_data if e["unique_id"] == "maspeth-queens")
        assert maspeth_log_entry["generation_date"] > "2024-01-01" # Check for updated timestamp

    def test_update_since_processes_correctly(self, log_test_setup):
        generator, output_dir, log_file_path = log_test_setup

        # Pre-populate log with one old and one recent entry
        generator.generation_log.add_entry({
            "neighborhood_name": "Maspeth", "borough": "Queens",
            "unique_id": "maspeth-queens",
            "last_amended_date": "2024-01-01"
        })
        generator.generation_log.add_entry({
            "neighborhood_name": "Williamsburg", "borough": "Brooklyn",
            "unique_id": "williamsburg-brooklyn",
            "last_amended_date": "2025-11-20"
        })

        neighborhood_list = [
            {"Neighborhood": "Maspeth", "Borough": "Queens"},
            {"Neighborhood": "Williamsburg", "Borough": "Brooklyn"}
        ]
        
        # Only Williamsburg should be updated
        results = generator.generate_profiles_from_list(neighborhood_list, update_since=date(2025, 1, 1))

        assert results["total"] == 2
        assert results["success"] == 1
        assert results["skipped"] == 1
        assert results["failed"] == 0
        assert not (output_dir / "Maspeth_Queens.md").exists() # Skipped
        assert (output_dir / "Williamsburg_Brooklyn.md").exists() # Processed
