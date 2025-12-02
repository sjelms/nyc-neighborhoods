import logging
from datetime import date
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from src.services.web_fetcher import WebFetcher
from src.services.wikipedia_parser import WikipediaParser
from src.services.data_normalizer import DataNormalizer
from src.lib.template_renderer import TemplateRenderer
from src.models.neighborhood_profile import NeighborhoodProfile

logger = logging.getLogger("nyc_neighborhoods")

class ProfileGenerator:
    WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki/"

    def __init__(self,
                 web_fetcher: WebFetcher,
                 wikipedia_parser: WikipediaParser,
                 data_normalizer: DataNormalizer,
                 template_renderer: TemplateRenderer,
                 output_dir: Path):
        self.web_fetcher = web_fetcher
        self.wikipedia_parser = wikipedia_parser
        self.data_normalizer = data_normalizer
        self.template_renderer = template_renderer
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True) # Ensure output directory exists

    def _construct_wikipedia_url(self, neighborhood_name: str, borough: str) -> str:
        """
        Constructs a Wikipedia URL for the given neighborhood and borough.
        """
        # Wikipedia uses underscores for spaces and often includes the borough for disambiguation
        search_name = f"{neighborhood_name}, {borough}".replace(" ", "_")
        return f"{self.WIKIPEDIA_BASE_URL}{search_name}"

    def generate_profile(
                         self,
                         neighborhood_name: str,
                         borough: str) -> Tuple[bool, Optional[Path]]:
        """
        Generates a Markdown profile for a single neighborhood.

        Args:
            neighborhood_name: The name of the neighborhood.
            borough: The borough the neighborhood belongs to.

        Returns:
            A tuple: (success_status, path_to_generated_file if successful else None).
        """
        logger.info(f"Starting profile generation for {neighborhood_name}, {borough}")
        
        # 1. Construct Wikipedia URL
        wikipedia_url = self._construct_wikipedia_url(neighborhood_name, borough)
        logger.debug(f"Constructed Wikipedia URL: {wikipedia_url}")

        # 2. Fetch content
        html_content = self.web_fetcher.fetch(wikipedia_url)
        if not html_content:
            logger.error(f"Failed to fetch Wikipedia content for {neighborhood_name}, {borough}. Skipping.")
            return False, None

        # 3. Parse content
        raw_data = self.wikipedia_parser.parse(html_content, neighborhood_name)
        
        # Add source URL to raw data for tracking
        if "sources" not in raw_data:
            raw_data["sources"] = []
        raw_data["sources"].append(wikipedia_url)

        # 4. Normalize data
        profile = self.data_normalizer.normalize(raw_data, neighborhood_name)
        if not profile:
            logger.error(f"Failed to normalize data for {neighborhood_name}, {borough}. Skipping.")
            return False, None

        # 5. Render Markdown
        try:
            markdown_content = self.template_renderer.render(profile)
        except Exception as e:
            logger.error(f"Error rendering Markdown for {neighborhood_name}, {borough}: {e}. Skipping.")
            return False, None

        # 6. Save Markdown to file
        file_name = f"{neighborhood_name.replace(' ', '_')}_{borough.replace(' ', '_')}.md"
        output_file_path = self.output_dir / file_name
        try:
            output_file_path.write_text(markdown_content)
            logger.info(f"Successfully generated profile for {neighborhood_name}, {borough} at {output_file_path}")
            return True, output_file_path
        except Exception as e:
            logger.error(f"Error saving profile for {neighborhood_name}, {borough} to {output_file_path}: {e}")
            return False, None
    
    def generate_profiles_from_list(self,
                                    neighborhood_list: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Generates Markdown profiles for a list of neighborhoods.

        Args:
            neighborhood_list: A list of dictionaries, each with 'Neighborhood' and 'Borough' keys.

        Returns:
            A dictionary containing success/failure counts and a list of results.
        """
        logger.info(f"Starting batch profile generation for {len(neighborhood_list)} neighborhoods.")
        results = {
            "total": len(neighborhood_list),
            "success": 0,
            "failed": 0,
            "details": []
        }

        for entry in neighborhood_list:
            neighborhood = entry.get("Neighborhood")
            borough = entry.get("Borough")

            if not neighborhood or not borough:
                logger.warning(f"Skipping entry due to missing Neighborhood or Borough: {entry}")
                results["failed"] += 1
                results["details"].append({
                    "neighborhood": neighborhood,
                    "borough": borough,
                    "status": "failed",
                    "reason": "Missing neighborhood or borough name in input."
                })
                continue

            success, file_path = self.generate_profile(neighborhood, borough)
            if success:
                results["success"] += 1
                results["details"].append({
                    "neighborhood": neighborhood,
                    "borough": borough,
                    "status": "success",
                    "file_path": str(file_path)
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "neighborhood": neighborhood,
                    "borough": borough,
                    "status": "failed",
                    "reason": f"Failed to generate profile. Check logs for details."
                })
        
        logger.info(f"Batch profile generation completed. Successful: {results['success']}, Failed: {results['failed']}.")
        return results

if __name__ == '__main__':
    from src.lib.logger import setup_logging
    from pathlib import Path
    import os

    setup_logging(level=logging.INFO)

    # --- Setup for demonstration ---
    # Create dummy output-template.md if it doesn't exist
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
    dummy_template_path = Path("output-template.md")
    if not dummy_template_path.exists():
        dummy_template_path.write_text(template_content)

    # Instantiate dependencies (using MagicMock for WebFetcher to prevent real external calls)
    from unittest.mock import MagicMock
    mock_fetcher = MagicMock(spec=WebFetcher)
    mock_fetcher.fetch.side_effect = [
        # Mock HTML for Maspeth (success)
        "<div class=\"mw-parser-output\"><p>Summary Maspeth.</p><table class=\"infobox\"><tr><th>Population</th><td>50000</td></tr></table></div>",
        # Mock HTML for Williamsburg (will cause normalization failure by parser returning minimal data)
        "<div class=\"mw-parser-output\"><p>Summary Williamsburg.</p></div>",
        # Mock HTML for NonExistent (fetch failure)
        None
    ]

    parser = WikipediaParser()
    normalizer = DataNormalizer(version="1.0", ratified_date=date(2025, 12, 2), last_amended_date=date(2025, 12, 2))
    renderer = TemplateRenderer(dummy_template_path)
    
    # Use a temporary output directory for demonstration
    demo_output_dir = Path("demo_output")
    
    generator = ProfileGenerator(
        web_fetcher=mock_fetcher,
        wikipedia_parser=parser,
        data_normalizer=normalizer,
        template_renderer=renderer,
        output_dir=demo_output_dir
    )

    # --- Generate profiles from a list ---
    neighborhood_list_to_process = [
        {"Neighborhood": "Maspeth", "Borough": "Queens"},
        {"Neighborhood": "Williamsburg", "Borough": "Brooklyn"},
        {"Neighborhood": "NonExistent", "Borough": "Someplace"},
        {"Neighborhood": "MissingBorough"} # Invalid entry
    ]
    print("\n--- Generating profiles from list ---")
    batch_results = generator.generate_profiles_from_list(neighborhood_list_to_process)
    
    print("\nBatch Results:")
    print(f"Total: {batch_results['total']}")
    print(f"Successful: {batch_results['success']}")
    print(f"Failed: {batch_results['failed']}")
    for detail in batch_results['details']:
        print(f"  - {detail['neighborhood']}, {detail.get('borough', 'N/A')}: {detail['status']} ({detail.get('reason', '')})")

    # Clean up dummy template and demo_output_dir
    if dummy_template_path.exists():
        dummy_template_path.unlink()
    if demo_output_dir.exists():
        for item in demo_output_dir.iterdir():
            if item.is_file():
                item.unlink()
        demo_output_dir.rmdir()