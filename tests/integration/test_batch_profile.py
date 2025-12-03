import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import date, datetime

from src.lib.csv_parser import CSVParser
from src.lib.template_renderer import TemplateRenderer
from src.services.web_fetcher import WebFetcher
from src.services.wikipedia_parser import WikipediaParser
from src.services.data_normalizer import DataNormalizer
from src.services.profile_generator import ProfileGenerator
from src.models.neighborhood_profile import (
    KeyDetails, Boundaries, NeighborhoodFacts, TransitAccessibility, CommuteTime, NeighborhoodProfile
)

# --- Fixtures for mocked dependencies and setup ---

@pytest.fixture
def mock_batch_web_fetcher():
    """Mocks WebFetcher for batch scenarios."""
    mock = MagicMock(spec=WebFetcher)
    mock.fetch.side_effect = [
        # For "Maspeth, Queens" - Success
        """<div class="mw-parser-output"><p>Summary Maspeth.</p><table class="infobox"><tr><th>Population</th><td>50000</td></tr></table></div>""",
        # For "Williamsburg, Brooklyn" - Simulate parsing failure (minimal HTML)
        """<div class="mw-parser-output"><p>Summary Williamsburg.</p></div>""",
        # For "NonExistent, Borough" - Simulate fetch failure
        None,
        # For "Ambiguous, Manhattan" - Success
        """<div class="mw-parser-output"><p>Summary Ambiguous.</p><table class="infobox"><tr><th>Population</th><td>10000</td></tr></table></div>""",
    ]
    return mock

@pytest.fixture
def mock_batch_wikipedia_parser():
    """Mocks WikipediaParser for batch scenarios."""
    mock = MagicMock(spec=WikipediaParser)
    mock.parse.side_effect = [
        # For "Maspeth" - Success
        {
            "summary": "This is a summary of Maspeth.",
            "key_details": {},
            "around_the_block": "Maspeth has a quiet, suburban feel.",
            "neighborhood_facts": {
                "population": "50,000", "area": "2 sq mi", "zip_codes": ["11378"],
                "boundaries": {"adjacent_neighborhoods": []}
            },
            "transit_accessibility": {"bus_routes": ["M Bus"]},
            "sources": [], "warnings": []
        },
        # For "Williamsburg" - Simulate raw data that causes normalization to fail (e.g., critical data missing)
        {
            "summary": "This is a summary of Williamsburg.",
            "key_details": {},
            "around_the_block": "Williamsburg is trendy.",
            "neighborhood_facts": {}, # Missing population/area
            "transit_accessibility": {},
            "sources": [], "warnings": ["Missing critical infobox data."]
        },
        # NonExistent would not reach here
        # For "Ambiguous" - Success
        {
            "summary": "This is a summary of Ambiguous.",
            "key_details": {},
            "around_the_block": "Ambiguous is diverse.",
            "neighborhood_facts": {
                "population": "10,000", "area": "1 sq mi", "zip_codes": ["10010"],
                "boundaries": {"adjacent_neighborhoods": []}
            },
            "transit_accessibility": {"nearest_subways": ["L"]},
            "sources": [], "warnings": []
        }
    ]
    return mock

@pytest.fixture
def mock_batch_data_normalizer():
    """Mocks DataNormalizer for batch scenarios."""
    mock = MagicMock(spec=DataNormalizer)
    
    # Simulate a successful normalization for Maspeth
    maspeth_profile = NeighborhoodProfile(
        version="1.0", ratified_date=date(2025, 1, 1), last_amended_date=date(2025, 1, 15),
        neighborhood_name="Maspeth", summary="Summary Maspeth.",
        key_details=KeyDetails(what_to_expect="", unexpected_appeal="", the_market=""),
        around_the_block="Around Maspeth.",
        neighborhood_facts=NeighborhoodFacts(population="50000", population_density="", area="2 sq mi",
                                             boundaries=Boundaries(east_to_west="", north_to_south="", adjacent_neighborhoods=[]),
                                             zip_codes=["11378"]),
        transit_accessibility=TransitAccessibility(nearest_subways=[], major_stations=[], bus_routes=["M Bus"], rail_freight_other=[], highways_major_roads=[]),
        sources=["https://en.wikipedia.org/wiki/Maspeth,_Queens"], generation_date=datetime.now(), warnings=[]
    )
    # Simulate normalization failure for Williamsburg (due to parser returning missing critical data)
    williamsburg_profile = None # Simulate normalization returning None

    # Simulate a successful normalization for Ambiguous
    ambiguous_profile = NeighborhoodProfile(
        version="1.0", ratified_date=date(2025, 1, 1), last_amended_date=date(2025, 1, 15),
        neighborhood_name="Ambiguous", summary="Summary Ambiguous.",
        key_details=KeyDetails(what_to_expect="", unexpected_appeal="", the_market=""),
        around_the_block="Around Ambiguous.",
        neighborhood_facts=NeighborhoodFacts(population="10000", population_density="", area="1 sq mi",
                                             boundaries=Boundaries(east_to_west="", north_to_south="", adjacent_neighborhoods=[]),
                                             zip_codes=["10010"]),
        transit_accessibility=TransitAccessibility(nearest_subways=["L"], major_stations=[], bus_routes=[], rail_freight_other=[], highways_major_roads=[]),
        sources=["https://en.wikipedia.org/wiki/Ambiguous,_Manhattan"], generation_date=datetime.now(), warnings=[]
    )


    mock.normalize.side_effect = [
        maspeth_profile,
        williamsburg_profile,
        # NonExistent would not reach here
        ambiguous_profile
    ]
    return mock

@pytest.fixture
def mock_batch_template_renderer(tmp_path: Path):
    """Mocks TemplateRenderer, sets up dummy template, for batch scenarios."""
    template_content = """**Version**: [VERSION] | **Neighborhood**: [Neighborhood Name]"""
    (tmp_path / "output-template.md").write_text(template_content)
    
    mock = MagicMock(spec=TemplateRenderer)
    mock.template_path = tmp_path / "output-template.md"
    mock.render.side_effect = [
        "**Version**: 1.0 | **Neighborhood**: Maspeth", # For Maspeth
        # Williamsburg fails normalization, so no render call
        "**Version**: 1.0 | **Neighborhood**: Ambiguous", # For Ambiguous
    ]
    return mock

@pytest.fixture
def batch_integration_setup(
    tmp_path: Path,
    mock_batch_web_fetcher,
    mock_batch_wikipedia_parser,
    mock_batch_data_normalizer,
    mock_batch_template_renderer
):
    """Provides a fully configured ProfileGenerator for batch integration tests."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Ensure the actual TemplateRenderer can find its mocked template
    # This is a bit redundant with the mock_batch_template_renderer.template_path assignment
    # but ensures if a real TemplateRenderer was used, it would find the file
    (tmp_path / "output-template.md").write_text("""**Version**: [VERSION]""") 
    
    generator = ProfileGenerator(
        web_fetcher=mock_batch_web_fetcher,
        wikipedia_parser=mock_batch_wikipedia_parser,
        data_normalizer=mock_batch_data_normalizer,
        template_renderer=mock_batch_template_renderer,
        output_dir=output_dir
    )
    return generator, output_dir, tmp_path

class TestBatchProfileGeneration:
    @patch('src.lib.logger.logger') # Mock the logger
    def test_generate_profiles_from_list_mixed_results(self, mock_logger, batch_integration_setup):
        generator, output_dir, tmp_path = batch_integration_setup
        
        neighborhood_list = [
            {"Neighborhood": "Maspeth", "Borough": "Queens"},
            {"Neighborhood": "Williamsburg", "Borough": "Brooklyn"},
            {"Neighborhood": "NonExistent", "Borough": "Borough"},
            {"Neighborhood": "Ambiguous", "Borough": "Manhattan"},
            {"Neighborhood": "MissingBorough"} # Invalid entry for parser itself
        ]

        results = generator.generate_profiles_from_list(neighborhood_list)
        
        # Assert overall summary
        assert results["total"] == 5
        assert results["success"] == 2
        assert results["failed"] == 3

        # Assert details for each outcome
        # Maspeth: Success
        maspeth_result = next(d for d in results["details"] if d["neighborhood"] == "Maspeth")
        assert maspeth_result["status"] == "success"
        assert Path(maspeth_result["file_path"]).exists()
        assert Path(maspeth_result["file_path"]).read_text() == "**Version**: 1.0 | **Neighborhood**: Maspeth"

        # Williamsburg: Failed (Normalization failure)
        williamsburg_result = next(d for d in results["details"] if d["neighborhood"] == "Williamsburg")
        assert williamsburg_result["status"] == "failed"
        assert "Failed to normalize data" in williamsburg_result["reason"]
        assert not (output_dir / "Williamsburg_Brooklyn.md").exists()

        # NonExistent: Failed (Web Fetcher failure)
        nonexistent_result = next(d for d in results["details"] if d["neighborhood"] == "NonExistent")
        assert nonexistent_result["status"] == "failed"
        assert "Failed to fetch Wikipedia content" in nonexistent_result["reason"] # Generic, details in log
        assert not (output_dir / "NonExistent_Borough.md").exists()

        # Ambiguous: Success
        ambiguous_result = next(d for d in results["details"] if d["neighborhood"] == "Ambiguous")
        assert ambiguous_result["status"] == "success"
        assert Path(ambiguous_result["file_path"]).exists()
        assert Path(ambiguous_result["file_path"]).read_text() == "**Version**: 1.0 | **Neighborhood**: Ambiguous"

        # MissingBorough: Failed (Input validation failure)
        missing_borough_result = next(d for d in results["details"] if d["neighborhood"] == "MissingBorough")
        assert missing_borough_result["status"] == "failed"
        assert "Missing neighborhood or borough name in input." in missing_borough_result["reason"]
        # File should not be created for invalid input that's caught before generator.generate_profile is called
        assert not (output_dir / "MissingBorough_.md").exists() 
        
        # Verify calls to dependencies
        assert generator.web_fetcher.fetch.call_count == 3 # Maspeth, Williamsburg, NonExistent, Ambiguous (MissingBorough skipped before fetch)
        assert generator.wikipedia_parser.parse.call_count == 2 # Maspeth, Williamsburg, Ambiguous
        assert generator.data_normalizer.normalize.call_count == 2 # Maspeth, Williamsburg, Ambiguous
        assert generator.template_renderer.render.call_count == 2 # Maspeth, Ambiguous

        # Verify logger messages
        mock_logger.info.assert_any_call("Starting batch profile generation for 5 neighborhoods.")
        mock_logger.error.assert_any_call("Failed to fetch Wikipedia content for NonExistent, Borough. Skipping.")
        mock_logger.error.assert_any_call("Failed to normalize data for Williamsburg, Brooklyn. Skipping.")
        mock_logger.warning.assert_any_call("Skipping entry due to missing Neighborhood or Borough: {'Neighborhood': 'MissingBorough'}")
        mock_logger.info.assert_any_call("Batch profile generation completed. Successful: 2, Failed: 3.")
