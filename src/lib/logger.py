import logging
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "app.log"

def setup_logging(level=logging.INFO, log_file: Path = LOG_FILE):
    """
    Sets up basic logging configuration.
    Logs to console and a file.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True) # Ensure log directory exists

    # Clear existing handlers to prevent duplicate logs in repeated calls
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)

    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Output to console
        ]
    )

    # Set up specific logger for the application
    app_logger = logging.getLogger("nyc_neighborhoods")
    app_logger.setLevel(level)

    # Example usage:
    # from src.lib.logger import setup_logging
    # setup_logging(level=logging.INFO)
    # logger = logging.getLogger("nyc_neighborhoods")
    # logger.info("This is an info message.")
    # logger.error("This is an error message.")
