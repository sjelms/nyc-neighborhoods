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
def mock_web_fetcher():
    """Mocks WebFetcher to return predefined HTML content."""
    mock = MagicMock(spec=WebFetcher)
    # Default behavior: return some HTML
    mock.fetch.return_value = """
    <div class="mw-parser-output">
        <p>This is a summary of Maspeth.</p>
        <table class="infobox geography vcard">
            <tbody>
                <tr><th scope="row">Population</th><td>50,000</td></tr>
                <tr><th scope="row">Area</th><td>2 sq mi</td></tr>
                <tr><th scope="row">ZIP Code</th><td>11378</td></tr>
            </tbody>
        </table>
        <h2>Transportation</h2>
        <ul><li><a href="#">M Bus</a></li></ul>
    </div>
    """
    return mock

@pytest.fixture
def mock_wikipedia_parser():
    """Mocks WikipediaParser to return predefined parsed data."""
    mock = MagicMock(spec=WikipediaParser)
    # Default behavior: return data structure expected by DataNormalizer
    mock.parse.return_value = {
        "summary": "This is a summary of Maspeth.",
        "key_details": {}, # Populated by normalizer with defaults
        "around_the_block": "Maspeth has a quiet, suburban feel.",
        "neighborhood_facts": {
            "population": "50,000",
            "population_density": "", # Not in mock HTML
            "area": "2 sq mi",
            "boundaries": {
                "east_to_west": "", # Not in mock HTML
                "north_to_south": "", # Not in mock HTML
                "adjacent_neighborhoods": []
            },
            "zip_codes": ["11378"]
        },
        "transit_accessibility": {
            "nearest_subways": [],
            "major_stations": [],
            "bus_routes": ["M Bus"],
            "rail_freight_other": [],
            "highways_major_roads": []
        },
        "commute_times": None,
        "sources": [],
        "warnings": []
    }
    return mock

@pytest.fixture
def mock_data_normalizer():
    """Mocks DataNormalizer to return a valid NeighborhoodProfile."""
    mock = MagicMock(spec=DataNormalizer)
    mock.normalize.return_value = NeighborhoodProfile(
        version="1.0",
        ratified_date=date(2025, 1, 1),
        last_amended_date=date(2025, 1, 15),
        neighborhood_name="Maspeth",
        summary="This is a summary of Maspeth.",
        key_details=KeyDetails(
            what_to_expect="Quiet streets.",
            unexpected_appeal="Strong community.",
            the_market="Stable housing."
        ),
        around_the_block="Maspeth has a quiet, suburban feel.",
        neighborhood_facts=NeighborhoodFacts(
            population="50,000",
            population_density="N/A",
            area="2 sq mi",
            boundaries=Boundaries(
                east_to_west="N/A", north_to_south="N/A", adjacent_neighborhoods=[]
            ),
            zip_codes=["11378"]
        ),
        transit_accessibility=TransitAccessibility(
            nearest_subways=[], major_stations=[], bus_routes=["M Bus"],
            rail_freight_other=[], highways_major_roads=[]
        ),
        commute_times=None,
        sources=["https://en.wikipedia.org/wiki/Maspeth,_Queens"],
        generation_date=datetime(2025, 1, 15, 10, 0, 0),
        warnings=["Population density data missing for Maspeth."]
    )
    return mock

@pytest.fixture
def mock_template_renderer(tmp_path: Path):
    """Mocks TemplateRenderer, also sets up a dummy template file."""
    # Create a dummy template as TemplateRenderer requires a path
    template_content = """**Version**: [VERSION] | **Neighborhood**: [Neighborhood Name] | Bus: {BUS_ROUTES}"""
    (tmp_path / "output-template.md").write_text(template_content)
    
    mock = MagicMock(spec=TemplateRenderer)
    mock.template_path = tmp_path / "output-template.md" # Assign dummy path
    mock.render.return_value = "**Version**: 1.0 | **Neighborhood**: Maspeth | Bus: M Bus"
    return mock

@pytest.fixture
def integration_setup(tmp_path: Path, mock_web_fetcher, mock_wikipedia_parser, mock_data_normalizer, mock_template_renderer):
    """Provides a fully configured ProfileGenerator for integration tests."""
    output_dir = tmp_path / "output"
    # Ensure the actual TemplateRenderer can find its mocked template
    mock_template_renderer.template_path = tmp_path / "output-template.md"
    
    generator = ProfileGenerator(
        web_fetcher=mock_web_fetcher,
        wikipedia_parser=mock_wikipedia_parser,
        data_normalizer=mock_data_normalizer,
        template_renderer=mock_template_renderer,
        output_dir=output_dir
    )
    return generator, output_dir

class TestSingleProfileGeneration:
    @patch('src.lib.logger.logger') # Mock the logger to prevent actual log output during tests
    def test_generate_single_profile_success(self, mock_logger, integration_setup):
        generator, output_dir = integration_setup
        
        success, file_path = generator.generate_profile("Maspeth", "Queens")
        
        assert success is True
        assert file_path is not None
        assert file_path.exists()
        assert file_path.name == "Maspeth_Queens.md"
        assert file_path.read_text() == "**Version**: 1.0 | **Neighborhood**: Maspeth | Bus: M Bus"

        generator.web_fetcher.fetch.assert_called_once_with("https://en.wikipedia.org/wiki/Maspeth,_Queens")
        generator.wikipedia_parser.parse.assert_called_once()
        generator.data_normalizer.normalize.assert_called_once()
        generator.template_renderer.render.assert_called_once()
        
        mock_logger.info.assert_any_call("Starting profile generation for Maspeth, Queens")
        mock_logger.info.assert_any_call(f"Successfully generated profile for Maspeth, Queens at {file_path}")

    @patch('src.lib.logger.logger')
    def test_generate_single_profile_web_fetch_failure(self, mock_logger, integration_setup):
        generator, output_dir = integration_setup
        generator.web_fetcher.fetch.return_value = None # Simulate fetch failure

        success, file_path = generator.generate_profile("Maspeth", "Queens")

        assert success is False
        assert file_path is None
        assert not (output_dir / "Maspeth_Queens.md").exists()
        generator.web_fetcher.fetch.assert_called_once()
        generator.wikipedia_parser.parse.assert_not_called() # Should not proceed if fetch fails
        mock_logger.error.assert_called_once_with("Failed to fetch Wikipedia content for Maspeth, Queens. Skipping.")

    @patch('src.lib.logger.logger')
    def test_generate_single_profile_normalization_failure(self, mock_logger, integration_setup):
        generator, output_dir = integration_setup
        generator.data_normalizer.normalize.return_value = None # Simulate normalization failure

        success, file_path = generator.generate_profile("Maspeth", "Queens")

        assert success is False
        assert file_path is None
        assert not (output_dir / "Maspeth_Queens.md").exists()
        generator.web_fetcher.fetch.assert_called_once()
        generator.wikipedia_parser.parse.assert_called_once()
        generator.data_normalizer.normalize.assert_called_once()
        generator.template_renderer.render.assert_not_called() # Should not proceed if normalize fails
        mock_logger.error.assert_called_once_with("Failed to normalize data for Maspeth, Queens. Skipping.")

    @patch('src.lib.logger.logger')
    def test_generate_single_profile_rendering_failure(self, mock_logger, integration_setup):
        generator, output_dir = integration_setup
        generator.template_renderer.render.side_effect = Exception("Rendering error") # Simulate rendering error

        success, file_path = generator.generate_profile("Maspeth", "Queens")

        assert success is False
        assert file_path is None
        assert not (output_dir / "Maspeth_Queens.md").exists()
        generator.web_fetcher.fetch.assert_called_once()
        generator.wikipedia_parser.parse.assert_called_once()
        generator.data_normalizer.normalize.assert_called_once()
        generator.template_renderer.render.assert_called_once()
        mock_logger.error.assert_called_once_with("Error rendering Markdown for Maspeth, Queens: Rendering error. Skipping.")
