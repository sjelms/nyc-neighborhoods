import pytest
from datetime import date, datetime
from pathlib import Path
from src.lib.template_renderer import TemplateRenderer
from src.models.neighborhood_profile import (
    KeyDetails, Boundaries, NeighborhoodFacts, TransitAccessibility, CommuteTime, NeighborhoodProfile
)

@pytest.fixture
def dummy_template_path(tmp_path: Path):
    """Fixture to create a dummy Markdown template file."""
    content = """
**Version**: [VERSION] | **Ratified**: [RATIFIED_DATE] | **Last Amended**: [LAST_AMENDED_DATE]

## [Neighborhood Name]

[Short Summary Paragraph]

---

### Key Details
- **WHAT TO EXPECT:**  
- **UNEXPECTED APPEAL:**  
- **THE MARKET:**  

---

### Around the Block

[A 1–2 paragraph narrative]

---

### Neighborhood Facts
- **Population:**   
- **Population Density:**   
- **Area:** 
- **Boundaries:**  
  - **East to West:** 
  - **North to South:** 
  - **Adjacent Neighborhoods:**   
- **ZIP Codes:** 

---

### Transit & Accessibility
#### Nearest Subways:
…  
#### Major Stations:
…  
#### Bus Routes:
…  
#### Rail / Freight / Other Transit (if applicable):
…  
#### Highways & Major Roads:
…  

---

### Commute Times (optional — if data available)
| Destination | Subway | Drive |
|-------------|--------|-------|
| … | … | … |
"""
    file_path = tmp_path / "output-template.md"
    file_path.write_text(content)
    return file_path

@pytest.fixture
def sample_profile_data():
    """Fixture to provide sample NeighborhoodProfile data."""
    key_details = KeyDetails(
        what_to_expect="Vibrant community with diverse dining.",
        unexpected_appeal="Hidden street art.",
        the_market="Mix of brownstones and condos."
    )
    boundaries = Boundaries(
        east_to_west="Main St to River Rd",
        north_to_south="Park Ave to Beachfront",
        adjacent_neighborhoods=["Suburbia", "Downtown"]
    )
    neighborhood_facts = NeighborhoodFacts(
        population="50,000",
        population_density="10,000/sq mi",
        area="5 sq mi",
        boundaries=boundaries,
        zip_codes=["10001"]
    )
    transit_accessibility = TransitAccessibility(
        nearest_subways=["1", "2", "3"],
        major_stations=["Grand Central"],
        bus_routes=["M15", "M42"],
        rail_freight_other=["LIRR"],
        highways_major_roads=["I-95"]
    )
    commute_times = [
        CommuteTime(destination="Office", subway="30 min", drive="45 min")
    ]

    return NeighborhoodProfile(
        version="1.0",
        ratified_date=date(2023, 1, 1),
        last_amended_date=date(2023, 1, 15),
        neighborhood_name="Exampleville",
        borough="Example Borough",
        summary="A bustling neighborhood.",
        key_details=key_details,
        around_the_block="Lots of cafes and parks.",
        neighborhood_facts=neighborhood_facts,
        transit_accessibility=transit_accessibility,
        commute_times=commute_times,
        sources=["http://example.com/source"],
        generation_date=datetime(2023, 1, 15, 10, 0, 0),
        warnings=["Some data missing from source X"]
    )

class TestTemplateRenderer:
    def test_renderer_initialization_success(self, dummy_template_path):
        renderer = TemplateRenderer(dummy_template_path)
        assert renderer.template_path == dummy_template_path
        assert "[VERSION]" in renderer.template_content

    def test_renderer_initialization_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="Template file not found"):
            TemplateRenderer(Path("non_existent_template.md"))

    def test_render_all_fields_populated(self, dummy_template_path, sample_profile_data):
        renderer = TemplateRenderer(dummy_template_path)
        rendered_output = renderer.render(sample_profile_data)

        # Check for replaced placeholders
        assert "Version: 1.0" in rendered_output
        assert "Ratified: 2023-01-01" in rendered_output
        assert "Last Amended: 2023-01-15" in rendered_output
        assert "## Exampleville" in rendered_output
        assert "A bustling neighborhood." in rendered_output
        assert "Vibrant community with diverse dining." in rendered_output
        assert "Main St to River Rd" in rendered_output
        assert "- 10001" in rendered_output # ZIP Codes
        assert "- 1" in rendered_output # Subways
        assert "- M15" in rendered_output # Bus Routes
        assert "Office | 30 min | 45 min" in rendered_output # Commute Times
        
        # Ensure no original placeholders remain
        assert "[VERSION]" not in rendered_output
        assert "[Neighborhood Name]" not in rendered_output
        assert "[Short Summary Paragraph]" not in rendered_output
        assert "…  " not in rendered_output # Check for empty bullet points

    def test_render_no_commute_times(self, dummy_template_path, sample_profile_data):
        profile_no_commute = sample_profile_data.copy(update={"commute_times": None})
        renderer = TemplateRenderer(dummy_template_path)
        rendered_output = renderer.render(profile_no_commute)

        # Ensure commute times section is removed
        assert "### Commute Times" not in rendered_output
        assert "| Destination | Subway | Drive |" not in rendered_output
        assert "|-------------|--------|-------|" not in rendered_output
        assert "Office | 30 min | 45 min" not in rendered_output
        assert "… | … | …" not in rendered_output # Old template placeholder
    
    def test_render_empty_list_fields(self, dummy_template_path, sample_profile_data):
        profile_empty_lists = sample_profile_data.copy(update={
            "transit_accessibility": TransitAccessibility(
                nearest_subways=[],
                major_stations=[],
                bus_routes=[],
                rail_freight_other=[],
                highways_major_roads=[]
            ),
            "neighborhood_facts": NeighborhoodFacts(
                population="50,000",
                population_density="10,000/sq mi",
                area="5 sq mi",
                boundaries=Boundaries(east_to_west="", north_to_south="", adjacent_neighborhoods=[]),
                zip_codes=[]
            )
        })
        renderer = TemplateRenderer(dummy_template_path)
        rendered_output = renderer.render(profile_empty_lists)

        # Ensure empty lists don't create " - " or other artifacts
        assert "- \n" not in rendered_output
        assert "Adjacent Neighborhoods: " in rendered_output # Should be just the label, no items
        assert "ZIP Codes: " in rendered_output # Should be just the label, no items

        # Check transit section for empty lists
        assert "#### Nearest Subways:" in rendered_output
        assert "#### Major Stations:" in rendered_output
        assert "#### Bus Routes:" in rendered_output
        assert "#### Rail / Freight / Other Transit (if applicable):" in rendered_output
        assert "#### Highways & Major Roads:" in rendered_output
        
        # Verify no list items were rendered for these empty lists.
        # This is tricky without parsing markdown, but we can check for common list prefixes.
        # This assumes _format_list returns empty string for empty list.
        assert "- " not in rendered_output[rendered_output.find("#### Nearest Subways:"):]
