import logging
from datetime import date
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from src.services.web_fetcher import WebFetcher
from src.services.wikipedia_parser import WikipediaParser
from src.services.data_normalizer import DataNormalizer
from src.lib.template_renderer import TemplateRenderer
from src.models.neighborhood_profile import NeighborhoodProfile
from src.services.nyc_open_data_fetcher import NYCOpenDataFetcher
from src.services.nyc_open_data_parser import NYCOpenDataParser
from src.lib.generation_log import GenerationLog # Import GenerationLog


logger = logging.getLogger("nyc_neighborhoods")

class ProfileGenerator:
    WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki/"

    def __init__(self, 
                 web_fetcher: WebFetcher,
                 wikipedia_parser: WikipediaParser,
                 data_normalizer: DataNormalizer,
                 template_renderer: TemplateRenderer,
                 output_dir: Path,
                 nyc_open_data_fetcher: Optional[NYCOpenDataFetcher] = None,
                 nyc_open_data_parser: Optional[NYCOpenDataParser] = None,
                 generation_log: Optional[GenerationLog] = None): # New
        self.web_fetcher = web_fetcher
        self.wikipedia_parser = wikipedia_parser
        self.data_normalizer = data_normalizer
        self.template_renderer = template_renderer
        self.output_dir = output_dir
        self.nyc_open_data_fetcher = nyc_open_data_fetcher
        self.nyc_open_data_parser = nyc_open_data_parser
        self.generation_log = generation_log # Store
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

        # 3a. Fetch REST summary (more stable than HTML)
        summary_api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{neighborhood_name.replace(' ', '_')},_{borough.replace(' ', '_')}"
        summary_data = self.web_fetcher.fetch_json(summary_api_url)
        summary_text = ""
        if summary_data:
            summary_text = summary_data.get("extract", "") or summary_data.get("description", "")

        # 3b. Parse content
        raw_data = self.wikipedia_parser.parse(html_content, neighborhood_name, summary_override=summary_text)
        
        # Add source URL to raw data for tracking
        if "sources" not in raw_data:
            raw_data["sources"] = []
        raw_data["sources"].append(wikipedia_url)

        # 4. Normalize data (now passing Open Data fetcher/parser)
        profile = self.data_normalizer.normalize(raw_data, neighborhood_name, borough)
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
        file_name = f"{profile.neighborhood_name.replace(' ', '_')}_{profile.borough.replace(' ', '_')}.md"
        output_file_path = self.output_dir / file_name
        try:
            output_file_path.write_text(markdown_content)
            logger.info(f"Successfully generated profile for {neighborhood_name}, {borough} at {output_file_path}")
            
            # 7. Log the generation
            if self.generation_log:
                log_entry = {
                    "neighborhood_name": profile.neighborhood_name,
                    "borough": profile.borough,
                    "unique_id": profile.unique_id, # Use the new unique_id
                    "version": profile.version,
                    "generation_date": profile.generation_date.isoformat(),
                    "last_amended_date": profile.last_amended_date.isoformat(),
                    "output_file_path": str(output_file_path)
                }
                self.generation_log.add_entry(log_entry)
            
            return True, output_file_path
        except Exception as e:
            logger.error(f"Error saving profile for {neighborhood_name}, {borough} to {output_file_path}: {e}")
            return False, None
    
    def generate_profiles_from_list(
                                    self,
                                    neighborhood_list: List[Dict[str, str]],
                                    force_regenerate: bool = False, # New
                                    update_since: Optional[date] = None # New
                                    ) -> Dict[str, Any]:
        """
        Generates Markdown profiles for a list of neighborhoods.

        Args:
            neighborhood_list: A list of dictionaries, each with 'Neighborhood' and 'Borough' keys.
            force_regenerate: If True, regenerate all profiles regardless of log status.
            update_since: If provided, regenerate profiles amended on or after this date.

        Returns:
            A dictionary containing success/failure counts and a list of results.
        """
        logger.info(f"Starting batch profile generation for {len(neighborhood_list)} neighborhoods.")
        results = {
            "total": len(neighborhood_list),
            "skipped": 0,
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
            
            # Determine if this profile should be processed based on log and flags
            process_profile = True
            if self.generation_log and not force_regenerate:
                existing_log_entry = self.generation_log.find_entry(neighborhood, borough)
                if existing_log_entry:
                    if update_since:
                        # Convert log's last_amended_date string to date object for comparison
                        log_amended_date_str = existing_log_entry.get("last_amended_date")
                        if log_amended_date_str:
                            try:
                                log_amended_date = date.fromisoformat(log_amended_date_str)
                                if log_amended_date < update_since:
                                    process_profile = False
                                    logger.info(f"Skipping {neighborhood}, {borough} (last amended {log_amended_date} is before update_since {update_since}).")
                            except ValueError:
                                logger.warning(f"Log entry for {neighborhood}, {borough} has invalid 'last_amended_date': '{log_amended_date_str}'. Processing.")
                        else:
                            # If no last_amended_date in log, treat as old and don't skip if update_since is present
                            # Or decide to always process if amended date is missing. For now, process if missing.
                            logger.warning(f"Log entry for {neighborhood}, {borough} is missing 'last_amended_date'. Processing.")

                    if process_profile and not update_since: # Skip if no update_since and not force_regenerate
                        process_profile = False
                        results["skipped"] += 1
                        results["details"].append({
                            "neighborhood": neighborhood,
                            "borough": borough,
                            "status": "skipped",
                            "reason": "Profile already exists in log (use --force-regenerate or --update-since to reprocess)."
                        })
                        logger.info(f"Skipping {neighborhood}, {borough}. Already in log.")
            
            if not process_profile:
                continue

            # Process the profile
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
        
        logger.info(f"Batch profile generation completed. Successful: {results['success']}, Failed: {results['failed']}, Skipped: {results['skipped']}.")
        return results

if __name__ == '__main__':
    from src.lib.logger import setup_logging
    from pathlib import Path
    import os
    from unittest.mock import MagicMock
    from src.services.web_fetcher import WebFetcher as RealWebFetcher
    from src.services.nyc_open_data_fetcher import NYCOpenDataFetcher as RealNYCOpenDataFetcher
    from src.services.nyc_open_data_parser import NYCOpenDataParser as RealNYCOpenDataParser
    from src.lib.generation_log import GenerationLog as RealGenerationLog

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
    mock_web_fetcher = MagicMock(spec=RealWebFetcher)
    mock_web_fetcher.fetch.side_effect = [
        # Mock HTML for Maspeth (success)
        "<div class=\"mw-parser-output\"><p>Summary Maspeth.</p><table class=\"infobox\"><tr><th>Population</th><td>50000</td></tr></table></div>",
        # Mock HTML for Williamsburg (will cause normalization failure by parser returning minimal data)
        "<div class=\"mw-parser-output\"><p>Summary Williamsburg.</p></div>",
        # Mock HTML for NonExistent (fetch failure)
        None,
        # Mock HTML for Ambiguous (success)
        "<div class=\"mw-parser-output\"><p>Summary Ambiguous.</p><table class=\"infobox\"><tr><th>Population</th><td>10000</td></tr></table></div>",
        # Mock HTML for OldNeighborhood (success)
        "<div class=\"mw-parser-output\"><p>Summary OldNeighborhood.</p><table class=\"infobox\"><tr><th>Population</th><td>20000</td></tr></table></div>",
        # Mock HTML for RecentNeighborhood (success)
        "<div class=\"mw-parser-output\"><p>Summary RecentNeighborhood.</p><table class=\"infobox\"><tr><th>Population</th><td>30000</td></tr></table></div>",
        # Mock HTML for AlwaysProcess (success)
        "<div class=\"mw-parser-output\"><p>Summary AlwaysProcess.</p><table class=\"infobox\"><tr><th>Population</th><td>40000</td></tr></table></div>",
    ]

    mock_web_fetcher_for_open_data = MagicMock(spec=RealWebFetcher)
    mock_web_fetcher_for_open_data.fetch.return_value = json.dumps([
        {"ntacode": "QN27", "ntaname": "Maspeth-Ridgewood", "boroughname": "Queens", "shape_area": "123456.78", "shape_len": "9876.54"}
    ])

    # Real dependencies used for demonstration of types
    wikipedia_parser = WikipediaParser()
    nyc_open_data_fetcher = RealNYCOpenDataFetcher(web_fetcher=mock_web_fetcher_for_open_data)
    nyc_open_data_parser = RealNYCOpenDataParser()

    normalizer = DataNormalizer(
        version="1.0",
        ratified_date=date(2025, 12, 2),
        last_amended_date=date(2025, 12, 2),
        nyc_open_data_fetcher=nyc_open_data_fetcher, # Pass here
        nyc_open_data_parser=nyc_open_data_parser   # Pass here
    )
    renderer = TemplateRenderer(dummy_template_path)
    
    # Use a temporary output directory for demonstration
    demo_output_dir = Path("demo_output")
    
    # Setup GenerationLog for testing
    demo_log_path = Path("temp_logs/generation_log.json")
    if demo_log_path.exists():
        demo_log_path.unlink()
    if demo_log_path.parent.exists():
        demo_log_path.parent.rmdir()
    generation_log = RealGenerationLog(demo_log_path)
    
    # Add a couple of existing entries to the log for testing skipping logic
    generation_log.add_entry({
        "neighborhood_name": "OldNeighborhood", "borough": "Manhattan",
        "unique_id": "oldneighborhood-manhattan",
        "version": "1.0", "generation_date": "2024-01-01T10:00:00", "last_amended_date": "2024-01-01",
        "output_file_path": str(demo_output_dir / "OldNeighborhood_Manhattan.md")
    })
    generation_log.add_entry({
        "neighborhood_name": "RecentNeighborhood", "borough": "Bronx",
        "unique_id": "recentneighborhood-bronx",
        "version": "1.0", "generation_date": "2025-11-20T10:00:00", "last_amended_date": "2025-11-20",
        "output_file_path": str(demo_output_dir / "RecentNeighborhood_Bronx.md")
    })

    generator = ProfileGenerator(
        web_fetcher=mock_web_fetcher,
        wikipedia_parser=wikipedia_parser,
        data_normalizer=normalizer,
        template_renderer=renderer,
        output_dir=demo_output_dir,
        nyc_open_data_fetcher=nyc_open_data_fetcher, # Pass here
        nyc_open_data_parser=nyc_open_data_parser,   # Pass here
        generation_log=generation_log # Pass generation log
    )

    # --- Generate profiles from a list ---
    neighborhood_list_to_process = [
        {"Neighborhood": "Maspeth", "Borough": "Queens"}, # New entry
        {"Neighborhood": "Williamsburg", "Borough": "Brooklyn"}, # New entry, will fail normalization
        {"Neighborhood": "NonExistent", "Borough": "Someplace"}, # New entry, will fail fetch
        {"Neighborhood": "Ambiguous", "Borough": "Manhattan"}, # New entry
        {"Neighborhood": "OldNeighborhood", "Borough": "Manhattan"}, # Existing, will be skipped by default
        {"Neighborhood": "RecentNeighborhood", "Borough": "Bronx"}, # Existing, will be skipped by default
        {"Neighborhood": "MissingBorough"} # Invalid entry for parser itself
    ]
    print("\n--- Generating profiles from list (default behavior) ---")
    batch_results = generator.generate_profiles_from_list(neighborhood_list_to_process)
    
    print("\nBatch Results (default):")
    print(f"Total: {batch_results['total']}")
    print(f"Successful: {batch_results['success']}")
    print(f"Failed: {batch_results['failed']}")
    print(f"Skipped: {batch_results['skipped']}")
    for detail in batch_results['details']:
        print(f"  - {detail['neighborhood']}, {detail.get('borough', 'N/A')}: {detail['status']} ({detail.get('reason', '')})")

    # Test with force_regenerate
    mock_web_fetcher.fetch.reset_mock() # Reset mocks for new test run
    mock_web_fetcher.fetch.side_effect = [
        "<div class=\"mw-parser-output\"><p>Summary OldNeighborhood.</p><table class=\"infobox\"><tr><th>Population</th><td>20000</td></tr></table></div>",
        "<div class=\"mw-parser-output\"><p>Summary RecentNeighborhood.</p><table class=\"infobox\"><tr><th>Population</th><td>30000</td></tr></table></div>",
    ]
    print("\n--- Generating profiles from list (force_regenerate=True) ---")
    batch_results_force = generator.generate_profiles_from_list(
        [{"Neighborhood": "OldNeighborhood", "Borough": "Manhattan"}, {"Neighborhood": "RecentNeighborhood", "Borough": "Bronx"}],
        force_regenerate=True
    )
    print("\nBatch Results (force_regenerate):")
    print(f"Total: {batch_results_force['total']}")
    print(f"Successful: {batch_results_force['success']}")
    print(f"Failed: {batch_results_force['failed']}")
    print(f"Skipped: {batch_results_force['skipped']}")
    assert batch_results_force["success"] == 2
    assert generation_log.find_entry("OldNeighborhood", "Manhattan")["generation_date"] > "2024-01-01"


    # Test with update_since
    mock_web_fetcher.fetch.reset_mock()
    mock_web_fetcher.fetch.side_effect = [
        "<div class=\"mw-parser-output\"><p>Summary OldNeighborhood.</p><table class=\"infobox\"><tr><th>Population</th><td>20000</td></tr></table></div>",
    ]
    print("\n--- Generating profiles from list (update_since=2025-01-01) ---")
    batch_results_update = generator.generate_profiles_from_list(
        [{"Neighborhood": "OldNeighborhood", "Borough": "Manhattan"}, {"Neighborhood": "RecentNeighborhood", "Borough": "Bronx"}],
        update_since=date(2025, 1, 1)
    )
    print("\nBatch Results (update_since):")
    print(f"Total: {batch_results_update['total']}")
    print(f"Successful: {batch_results_update['success']}")
    print(f"Failed: {batch_results_update['failed']}")
    print(f"Skipped: {batch_results_update['skipped']}")
    assert batch_results_update["success"] == 1
    assert batch_results_update["skipped"] == 1 # RecentNeighborhood should be skipped

    # Clean up dummy template and demo_output_dir
    if dummy_template_path.exists():
        dummy_template_path.unlink()
    if demo_output_dir.exists():
        for item in demo_output_dir.iterdir():
            if item.is_file():
                item.unlink()
        demo_output_dir.rmdir()
    if demo_log_path.exists():
        demo_log_path.unlink()
    if demo_log_path.parent.exists():
        demo_log_path.parent.rmdir()
