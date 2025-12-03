import typer
import logging
from typing import Optional
from pathlib import Path
from datetime import date

from src.lib.logger import setup_logging
from src.lib.csv_parser import CSVParser
from src.lib.template_renderer import TemplateRenderer
from src.services.web_fetcher import WebFetcher
from src.services.wikipedia_parser import WikipediaParser
from src.services.data_normalizer import DataNormalizer
from src.services.profile_generator import ProfileGenerator
from src.lib.cache_manager import CacheManager
from src.services.nyc_open_data_fetcher import NYCOpenDataFetcher
from src.services.nyc_open_data_parser import NYCOpenDataParser
from src.lib.generation_log import GenerationLog # Import GenerationLog

app = typer.Typer()


def _parse_date(value: Optional[str], option_name: str) -> date:
    """Parse ISO date strings supplied via CLI options."""
    if value is None:
        return date.today()
    try:
        return date.fromisoformat(value)
    except ValueError:
        typer.echo(f"Error: Invalid date for --{option_name}: '{value}'. Use YYYY-MM-DD.", err=True)
        raise typer.Exit(code=1)


@app.command()
def generate_profiles(
    input_csv: Path = typer.Option(Path("reference/neighborhood-borough.csv"), "--input-csv", "-i", exists=True, file_okay=True, dir_okay=False,
                                   writable=False, readable=True, resolve_path=True,
                                   help="Path to the input CSV file containing neighborhood and borough."),
    output_dir: Path = typer.Option(Path("output/profiles"), "--output-dir", "-o", exists=False, file_okay=False, dir_okay=True,
                                    writable=True, readable=True, resolve_path=True,
                                    help="Path to the directory where generated Markdown files will be saved."),
    template_path: Path = typer.Option(Path("reference/output-template.md"), "--template-path", "-t", exists=True, file_okay=True, dir_okay=False,
                                    readable=True, resolve_path=True,
                                    help="Path to the Markdown template file for output."),
    version: str = typer.Option("1.0", "--version", "-v", help="Version of the generated profiles."),
    ratified_date: Optional[str] = typer.Option(None, "--ratified-date", "-r", help="Date when the profile format was ratified (YYYY-MM-DD). Defaults to today."),
    last_amended_date: Optional[str] = typer.Option(None, "--last-amended-date", "-a", help="Date when the profile was last amended (YYYY-MM-DD). Defaults to today."),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."),
    cache_dir: Path = typer.Option("cache", "--cache-dir", "-c", exists=False, file_okay=False, dir_okay=True,
                                   writable=True, readable=True, resolve_path=True,
                                   help="Path to the directory for caching web content."),
    cache_expiry_days: int = typer.Option(7, "--cache-expiry-days", "-e", min=0,
                                         help="Number of days before cached web content expires. Set to 0 to disable caching."),
    nyc_open_data_dataset_id: Optional[str] = typer.Option(None, "--nyc-open-data-dataset-id", "--odid",
                                                          help="ID of the NYC Open Data Socrata dataset to use for supplementary data. e.g. 'ntacode_dataset_placeholder'. If not provided, Open Data will not be used."),
    force_regenerate: bool = typer.Option(False, "--force-regenerate", "-f",
                                         help="Force regeneration of all profiles, even if they exist in the log."),
    update_since: Optional[str] = typer.Option(None, "--update-since", "-u",
                                              help="Regenerate profiles last amended on or after this date (YYYY-MM-DD)."),
    generation_log_file: Path = typer.Option("logs/generation_log.json", "--log-file", "--glf",
                                           file_okay=True, dir_okay=False, writable=True, readable=True, resolve_path=True,
                                           help="Path to the JSON log file for tracking generated profiles.")
):
    """
    Generates standardized Markdown profile files for New York City neighborhoods.
    """
    setup_logging(level=getattr(logging, log_level.upper(), logging.INFO))
    internal_logger = logging.getLogger("nyc_neighborhoods")
    
    internal_logger.info("CLI command started.")

    parsed_ratified_date = _parse_date(ratified_date, "ratified-date")
    parsed_last_amended_date = _parse_date(last_amended_date, "last-amended-date")
    parsed_update_since = None
    if update_since is not None:
        parsed_update_since = _parse_date(update_since, "update-since")

    # Initialize CacheManager if caching is enabled
    cache_manager: Optional[CacheManager] = None
    if cache_expiry_days > 0:
        cache_manager = CacheManager(cache_dir=cache_dir, expiry_days=cache_expiry_days)
        internal_logger.info(f"Caching enabled with expiry of {cache_expiry_days} days in {cache_dir}")
    else:
        internal_logger.info("Caching disabled.")

    # Initialize WebFetcher
    web_fetcher = WebFetcher(cache_manager=cache_manager)

    # Initialize NYC Open Data components if ID is provided
    nyc_open_data_fetcher: Optional[NYCOpenDataFetcher] = None
    nyc_open_data_parser: Optional[NYCOpenDataParser] = None
    if nyc_open_data_dataset_id:
        nyc_open_data_fetcher = NYCOpenDataFetcher(web_fetcher=web_fetcher)
        nyc_open_data_parser = NYCOpenDataParser()
        internal_logger.info(f"NYC Open Data integration enabled for dataset: {nyc_open_data_dataset_id}")
    else:
        internal_logger.info("NYC Open Data integration disabled.")

    # Initialize GenerationLog
    generation_log = GenerationLog(generation_log_file)
    internal_logger.info(f"Generation log initialized at {generation_log_file}")

    # Initialize core components
    csv_parser = CSVParser(input_csv)
    wikipedia_parser = WikipediaParser()
    
    data_normalizer = DataNormalizer(
        version, parsed_ratified_date, parsed_last_amended_date,
        nyc_open_data_fetcher=nyc_open_data_fetcher,
        nyc_open_data_parser=nyc_open_data_parser,
        nyc_open_data_dataset_id=nyc_open_data_dataset_id
    )
    
    try:
        template_renderer = TemplateRenderer(template_path)
    except FileNotFoundError as e:
        internal_logger.critical(f"Template file error: {e}")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    profile_generator = ProfileGenerator(
        web_fetcher=web_fetcher,
        wikipedia_parser=wikipedia_parser,
        data_normalizer=data_normalizer,
        template_renderer=template_renderer,
        output_dir=output_dir,
        nyc_open_data_fetcher=nyc_open_data_fetcher,
        nyc_open_data_parser=nyc_open_data_parser,
        generation_log=generation_log # Pass generation log here
    )

    # Parse CSV for neighborhoods
    try:
        neighborhoods_to_process = csv_parser.parse()
        if not neighborhoods_to_process:
            typer.echo("No neighborhoods found in the input CSV. Exiting.")
            internal_logger.info("No neighborhoods found in the input CSV. Exiting.")
            raise typer.Exit(code=0)
    except ValueError as e:
        internal_logger.critical(f"CSV parsing error: {e}")
        typer.echo(f"Error parsing CSV: {e}", err=True)
        raise typer.Exit(code=1)
    
    # Process all neighborhoods (batch mode)
    typer.echo(f"Starting to generate profiles for {len(neighborhoods_to_process)} neighborhoods...")
    results = profile_generator.generate_profiles_from_list(
        neighborhoods_to_process,
        force_regenerate=force_regenerate,
        update_since=parsed_update_since
    )
    
    # Report summary
    typer.echo("\n--- Profile Generation Summary ---")
    typer.echo(f"Total neighborhoods processed: {results['total']}")
    typer.echo(f"Successfully generated: {results['success']}")
    typer.echo(f"Failed to generate: {results['failed']}")
    typer.echo(f"Skipped: {results['skipped']}") # Display skipped count

    if results['failed'] > 0:
        typer.echo("\n--- Details for Failed Profiles ---")
        for detail in results['details']:
            if detail['status'] == 'failed':
                typer.echo(f"  - {detail['neighborhood']}, {detail.get('borough', 'N/A')}: {detail['reason']}")
        raise typer.Exit(code=1) # Exit with error code if any profiles failed
    elif results['skipped'] > 0 and not force_regenerate and not update_since:
        typer.echo("\nSome profiles were skipped because they already exist in the log.")
        typer.echo("Use --force-regenerate to reprocess all, or --update-since to refresh specific records.")
    else:
        typer.echo("\nAll eligible profiles generated successfully!")

    internal_logger.info("CLI command finished.")

if __name__ == "__main__":
    app()
