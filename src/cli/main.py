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
from src.lib.cache_manager import CacheManager # Import CacheManager

app = typer.Typer()
logger = typer.echo  # Use typer.echo for CLI output, logging for internal messages

@app.command()
def generate_profiles(
    input_csv: Path = typer.Option(..., "--input-csv", "-i", exists=True, file_okay=True, dir_okay=False,
                                   writable=False, readable=True, resolve_path=True,
                                   help="Path to the input CSV file containing neighborhood and borough."),
    output_dir: Path = typer.Option(..., "--output-dir", "-o", exists=False, file_okay=False, dir_okay=True,
                                    writable=True, readable=True, resolve_path=True,
                                    help="Path to the directory where generated Markdown files will be saved."),
    template_path: Path = typer.Option("output-template.md", "--template-path", "-t", exists=True, file_okay=True, dir_okay=False,
                                    readable=True, resolve_path=True,
                                    help="Path to the Markdown template file for output."),
    version: str = typer.Option("1.0", "--version", "-v", help="Version of the generated profiles."),
    ratified_date: date = typer.Option(date.today(), "--ratified-date", "-r", help="Date when the profile format was ratified (YYYY-MM-DD)."),
    last_amended_date: date = typer.Option(date.today(), "--last-amended-date", "-a", help="Date when the profile was last amended (YYYY-MM-DD)."),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."),
    cache_dir: Path = typer.Option("cache", "--cache-dir", "-c", exists=False, file_okay=False, dir_okay=True,
                                   writable=True, readable=True, resolve_path=True,
                                   help="Path to the directory for caching web content."),
    cache_expiry_days: int = typer.Option(7, "--cache-expiry-days", "-e", min=0,
                                         help="Number of days before cached web content expires. Set to 0 to disable caching.")
):
    """
    Generates standardized Markdown profile files for New York City neighborhoods.
    """
    setup_logging(level=getattr(logging, log_level.upper(), logging.INFO))
    internal_logger = logging.getLogger("nyc_neighborhoods")
    
    internal_logger.info("CLI command started.")

    # Initialize CacheManager if caching is enabled
    cache_manager: Optional[CacheManager] = None
    if cache_expiry_days > 0:
        cache_manager = CacheManager(cache_dir=cache_dir, expiry_days=cache_expiry_days)
        internal_logger.info(f"Caching enabled with expiry of {cache_expiry_days} days in {cache_dir}")
    else:
        internal_logger.info("Caching disabled.")

    # Initialize core components
    csv_parser = CSVParser(input_csv)
    web_fetcher = WebFetcher(cache_manager=cache_manager) # Pass cache_manager here
    wikipedia_parser = WikipediaParser()
    data_normalizer = DataNormalizer(version, ratified_date, last_amended_date)
    
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
        output_dir=output_dir
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
    results = profile_generator.generate_profiles_from_list(neighborhoods_to_process)
    
    # Report summary
    typer.echo("\n--- Profile Generation Summary ---")
    typer.echo(f"Total neighborhoods processed: {results['total']}")
    typer.echo(f"Successfully generated: {results['success']}")
    typer.echo(f"Failed to generate: {results['failed']}")

    if results['failed'] > 0:
        typer.echo("\n--- Details for Failed Profiles ---")
        for detail in results['details']:
            if detail['status'] == 'failed':
                typer.echo(f"  - {detail['neighborhood']}, {detail.get('borough', 'N/A')}: {detail['reason']}")
        raise typer.Exit(code=1) # Exit with error code if any profiles failed
    else:
        typer.echo("\nAll profiles generated successfully!")

    internal_logger.info("CLI command finished.")

if __name__ == "__main__":
    app()
