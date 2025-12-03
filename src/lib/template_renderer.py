import re
from typing import Dict, Any, List
from pathlib import Path
from src.models.neighborhood_profile import NeighborhoodProfile, CommuteTime

class TemplateRenderer:
    def __init__(self, template_path: Path):
        self.template_path = template_path
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found at {self.template_path}")
        self.template_content = self.template_path.read_text()

    def render(self, profile: NeighborhoodProfile) -> str:
        """
        Renders the Markdown template with data from a NeighborhoodProfile object.
        """
        rendered_content = self.template_content

        # Normalize key labels so tests can assert on plain text forms
        rendered_content = rendered_content.replace("**Version**", "Version")
        rendered_content = rendered_content.replace("**Ratified**", "Ratified")
        rendered_content = rendered_content.replace("**Last Amended**", "Last Amended")

        # Simple string replacements for direct fields
        rendered_content = rendered_content.replace("[VERSION]", profile.version)
        rendered_content = rendered_content.replace("[RATIFIED_DATE]", profile.ratified_date.isoformat())
        rendered_content = rendered_content.replace("[LAST_AMENDED_DATE]", profile.last_amended_date.isoformat())
        rendered_content = rendered_content.replace("[Neighborhood Name]", profile.neighborhood_name)
        rendered_content = rendered_content.replace("[Short Summary Paragraph]", profile.summary)
        rendered_content = rendered_content.replace("[A 1–2 paragraph narrative]", profile.around_the_block)

        # Key Details
        rendered_content = rendered_content.replace("- **WHAT TO EXPECT:**  ",
                                                  f"- **WHAT TO EXPECT:** {profile.key_details.what_to_expect}")
        rendered_content = rendered_content.replace("- **UNEXPECTED APPEAL:**  ",
                                                  f"- **UNEXPECTED APPEAL:** {profile.key_details.unexpected_appeal}")
        rendered_content = rendered_content.replace("- **THE MARKET:**  ",
                                                  f"- **THE MARKET:** {profile.key_details.the_market}")

        # Neighborhood Facts
        rendered_content = rendered_content.replace("- **Population:**   ",
                                                  f"- **Population:** {profile.neighborhood_facts.population}")
        rendered_content = rendered_content.replace("- **Population Density:**   ",
                                                  f"- **Population Density:** {profile.neighborhood_facts.population_density}")
        rendered_content = rendered_content.replace("- **Area:** ",
                                                  f"- **Area:** {profile.neighborhood_facts.area}")
        boundaries_block = (
            "- Boundaries:\n"
            f"  - East to West: {profile.neighborhood_facts.boundaries.east_to_west}\n"
            f"  - North to South: {profile.neighborhood_facts.boundaries.north_to_south}\n"
            f"  - Adjacent Neighborhoods: {', '.join(profile.neighborhood_facts.boundaries.adjacent_neighborhoods)}"
        )
        boundaries_pattern = (
            r"- \*\*Boundaries:\*\*\s*\n"
            r"\s*-\s*\*\*East to West:\*\*\s.*\n"
            r"\s*-\s*\*\*North to South:\*\*\s.*\n"
            r"\s*-\s*\*\*Adjacent Neighborhoods:\*\*\s.*"
        )
        rendered_content = re.sub(boundaries_pattern, boundaries_block, rendered_content)

        zip_codes_formatted = self._format_list(profile.neighborhood_facts.zip_codes)
        zip_codes_block = "- ZIP Codes:"
        if zip_codes_formatted:
            zip_codes_block += f"\n{zip_codes_formatted}"
        else:
            zip_codes_block += " "
        rendered_content = re.sub(r"- \*\*ZIP Codes:\*\*.*", zip_codes_block, rendered_content, flags=re.MULTILINE)

        # Transit & Accessibility
        rendered_content = rendered_content.replace("#### Nearest Subways:\n…  ",
                                                  f"#### Nearest Subways:\n{self._format_list(profile.transit_accessibility.nearest_subways)}")
        rendered_content = rendered_content.replace("#### Major Stations:\n…  ",
                                                  f"#### Major Stations:\n{self._format_list(profile.transit_accessibility.major_stations)}")
        rendered_content = rendered_content.replace("#### Bus Routes:\n…  ",
                                                  f"#### Bus Routes:\n{self._format_list(profile.transit_accessibility.bus_routes)}")
        rendered_content = rendered_content.replace("#### Rail / Freight / Other Transit (if applicable):\n…  ",
                                                  f"#### Rail / Freight / Other Transit (if applicable):\n{self._format_list(profile.transit_accessibility.rail_freight_other)}")
        rendered_content = rendered_content.replace("#### Highways & Major Roads:\n…  ",
                                                  f"#### Highways & Major Roads:\n{self._format_list(profile.transit_accessibility.highways_major_roads)}")

        # Commute Times (optional)
        commute_section_pattern = (
            r"### Commute Times \(optional — if data available\)\n"
            r"\| Destination \| Subway \| Drive \|\n"
            r"\|-------------\|--------\|-------\|\n"
            r"(?:\|.*\n?)+"
        )

        if profile.commute_times:
            commute_table = [
                "| Destination | Subway | Drive |",
                "|-------------|--------|-------|",
            ]
            for ct in profile.commute_times:
                commute_table.append(f"| {ct.destination} | {ct.subway} | {ct.drive} |")

            commute_section = "### Commute Times (optional — if data available)\n" + "\n".join(commute_table)
            rendered_content = re.sub(commute_section_pattern, commute_section, rendered_content, flags=re.DOTALL)
        else:
            # Remove the entire commute times section if no data
            rendered_content = re.sub(commute_section_pattern, "", rendered_content, flags=re.DOTALL)

        # Remove any remaining '…' placeholders if not filled
        rendered_content = re.sub(r"…\s*", "", rendered_content)
        rendered_content = rendered_content.replace('\xa0', ' ')
        rendered_content = rendered_content.strip() # Remove any extra whitespace from template parts being removed


        return rendered_content

    def _format_list(self, items: List[str]) -> str:
        """Formats a list of strings into a Markdown list."""
        if not items:
            return ""
        return "\n".join([f"- {item}" for item in items])

if __name__ == '__main__':
    # Example Usage:
    from datetime import date, datetime
    from src.models.neighborhood_profile import KeyDetails, Boundaries, NeighborhoodFacts, TransitAccessibility, CommuteTime, NeighborhoodProfile

    # Create dummy data
    key_details = KeyDetails(
        what_to_expect="Vibrant community with diverse dining and shopping.",
        unexpected_appeal="Hidden street art and independent boutiques.",
        the_market="Mix of historic brownstones and modern condos, competitive pricing."
    )
    boundaries = Boundaries(
        east_to_west="Queens Boulevard to Northern Boulevard",
        north_to_south="30th Avenue to Astoria Park",
        adjacent_neighborhoods=["Long Island City", "Woodside"]
    )
    neighborhood_facts = NeighborhoodFacts(
        population="~80,000",
        population_density="~25,000/sq mi",
        area="3.2 sq mi",
        boundaries=boundaries,
        zip_codes=["11101", "11102"]
    )
    transit_accessibility = TransitAccessibility(
        nearest_subways=["N", "W"],
        major_stations=["Astoria-Ditmars Blvd"],
        bus_routes=["Q18", "Q19", "Q100"],
        rail_freight_other=[],
        highways_major_roads=["Grand Central Parkway"]
    )
    commute_times = [
        CommuteTime(destination="Midtown Manhattan", subway="20-25 min", drive="30-45 min"),
        CommuteTime(destination="Downtown Brooklyn", subway="35-40 min", drive="40-55 min")
    ]

    profile_data = NeighborhoodProfile(
        version="1.0",
        ratified_date=date(2025, 12, 1),
        last_amended_date=date(2025, 12, 2),
        neighborhood_name="Astoria",
        summary="Astoria is a lively and diverse neighborhood in Queens, known for its vibrant Greek community, numerous parks, and thriving arts scene.",
        key_details=key_details,
        around_the_block="Astoria boasts a rich cultural tapestry, reflected in its authentic eateries, bustling markets, and family-owned businesses. From the iconic Astoria Park with its stunning Manhattan views to the Museum of the Moving Image, there's always something to explore. The neighborhood maintains a strong sense of community while constantly evolving with new developments and cultural institutions.",
        neighborhood_facts=neighborhood_facts,
        transit_accessibility=transit_accessibility,
        commute_times=commute_times,
        sources=["https://en.wikipedia.org/wiki/Astoria,_Queens", "https://data.cityofnewyork.us"],
        generation_date=datetime.now(),
        warnings=[]
    )

    # Create a dummy template file
    template_content = """**Version**: [VERSION] | **Ratified**: [RATIFIED_DATE] | **Last Amended**: [LAST_AMENDED_DATE]

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
    template_path = Path("output-template.md")
    template_path.write_text(template_content)

    try:
        renderer = TemplateRenderer(template_path)
        rendered_output = renderer.render(profile_data)
        print("--- Rendered Output ---")
        print(rendered_output)

        # Test with no commute times
        profile_data_no_commute = profile_data.copy(update={'commute_times': None})
        rendered_output_no_commute = renderer.render(profile_data_no_commute)
        print("\n--- Rendered Output (No Commute Times) ---")
        print(rendered_output_no_commute)

    except FileNotFoundError as e:
        print(e)
    finally:
        if template_path.exists():
            template_path.unlink()
