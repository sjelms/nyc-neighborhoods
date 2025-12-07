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
        content = self.template_content

        # Simple string replacements for direct fields
        content = content.replace("[VERSION]", profile.version or "N/A")
        content = content.replace("[RATIFIED_DATE]", profile.ratified_date.isoformat())
        content = content.replace("[LAST_AMENDED_DATE]", profile.last_amended_date.isoformat())
        content = content.replace("[Neighborhood Name]", profile.neighborhood_name or "N/A")
        content = content.replace("[Short Summary Paragraph]", profile.summary or "Not available.")
        content = content.replace("[A 1–2 paragraph narrative]", profile.around_the_block or "")

        # Key-Value replacements using regex for robustness
        def replace_kv(text, key, value):
            # Matches "- **KEY:**" followed by optional whitespace up to the end of the line.
            pattern = re.compile(f"(- \\*\\*{re.escape(key)}:\\*\\*).*$", re.IGNORECASE | re.MULTILINE)
            replacement = f"\\g<1> {value or 'N/A'}"
            return pattern.sub(replacement, text)

        content = replace_kv(content, "WHAT TO EXPECT", profile.key_details.what_to_expect)
        content = replace_kv(content, "UNEXPECTED APPEAL", profile.key_details.unexpected_appeal)
        content = replace_kv(content, "THE MARKET", profile.key_details.the_market)
        
        content = replace_kv(content, "Population", str(profile.neighborhood_facts.population or 'N/A'))
        content = replace_kv(content, "Population Density", str(profile.neighborhood_facts.population_density or 'N/A'))
        content = replace_kv(content, "Area", str(profile.neighborhood_facts.area or 'N/A'))

        # Boundaries
        content = replace_kv(content, "East to West", profile.neighborhood_facts.boundaries.east_to_west or 'N/A')
        content = replace_kv(content, "North to South", profile.neighborhood_facts.boundaries.north_to_south or 'N/A')
        adj_neighborhoods_str = ', '.join(profile.neighborhood_facts.boundaries.adjacent_neighborhoods or [])
        content = replace_kv(content, "Adjacent Neighborhoods", adj_neighborhoods_str or 'N/A')

        # List-based sections (ZIPs and Transit)
        zip_list_str = self._format_list(profile.neighborhood_facts.zip_codes)
        content = re.sub(r"(- \*\*ZIP Codes:\*\*).*", f"\\g<1>\n{zip_list_str or 'N/A'}", content, flags=re.IGNORECASE)

        content = content.replace("#### Nearest Subways:\n…  ", f"#### Nearest Subways:\n{self._format_list(profile.transit_accessibility.nearest_subways) or 'N/A'}")
        content = content.replace("#### Major Stations:\n…  ", f"#### Major Stations:\n{self._format_list(profile.transit_accessibility.major_stations) or 'N/A'}")
        content = content.replace("#### Bus Routes:\n…  ", f"#### Bus Routes:\n{self._format_list(profile.transit_accessibility.bus_routes) or 'N/A'}")
        content = content.replace("#### Rail / Freight / Other Transit (if applicable):\n…  ", f"#### Rail / Freight / Other Transit (if applicable):\n{self._format_list(profile.transit_accessibility.rail_freight_other) or 'N/A'}")
        content = content.replace("#### Highways & Major Roads:\n…  ", f"#### Highways & Major Roads:\n{self._format_list(profile.transit_accessibility.highways_major_roads) or 'N/A'}")

        # Safely remove Commute Times section if no data is available
        commute_section_pattern = re.compile(r"\n---\s*\n\n### Commute Times.*?(?=\n\n---|$)", re.DOTALL)
        if profile.commute_times:
            table = ["| Destination | Subway | Drive |", "|-------------|--------|-------|"]
            table.extend([f"| {ct.destination} | {ct.subway} | {ct.drive} |" for ct in profile.commute_times])
            commute_section = "\n---\n\n### Commute Times (optional — if data available)\n" + "\n".join(table)
            content = commute_section_pattern.sub(commute_section, content)
        else:
            content = commute_section_pattern.sub("", content)

        # Online Resources links
        if profile.sources:
            wiki_link = next((src for src in profile.sources if "wikipedia.org" in src), "")
            official_link = next((src for src in profile.sources if "nyc.gov" in src or "official" in src.lower()), "")
            content = content.replace("[Neighborhood Website URL]", official_link or "N/A")
            content = content.replace("[Wikipedia URL]", wiki_link or "N/A")
        else:
            content = content.replace("[Neighborhood Website URL]", "N/A")
            content = content.replace("[Wikipedia URL]", "N/A")

        # Final cleanup
        content = content.replace('…', '')
        return content.strip()

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
