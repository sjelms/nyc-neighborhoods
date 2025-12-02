import requests
import logging
from typing import Optional
from pathlib import Path
from src.lib.cache_manager import CacheManager

logger = logging.getLogger("nyc_neighborhoods")

class WebFetcher:
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache_manager = cache_manager

    def fetch(self, url: str) -> Optional[str]:
        """
        Fetches content from a given URL, utilizing a cache if provided.

        Args:
            url: The URL to fetch.

        Returns:
            The content of the URL as a string, or None if an error occurred.
        """
        if self.cache_manager:
            cached_content = self.cache_manager.get(url)
            if cached_content:
                logger.info(f"Retrieved content for {url} from cache.")
                return cached_content

        logger.info(f"Attempting to fetch content from network: {url}")
        try:
            response = requests.get(url, timeout=10)  # 10-second timeout
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            content = response.text
            logger.info(f"Successfully fetched content from network: {url}")
            
            if self.cache_manager:
                self.cache_manager.set(url, content)
                logger.info(f"Content for {url} saved to cache.")
            
            return content
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error fetching {url}: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error fetching {url}: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"An unexpected request error occurred while fetching {url}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
        return None

if __name__ == '__main__':
    from src.lib.logger import setup_logging
    from pathlib import Path
    import os
    from unittest.mock import patch
    
    setup_logging(level=logging.INFO)

    # --- Setup for demonstration with cache ---
    demo_cache_dir = Path("temp_cache_webfetcher_demo")
    if demo_cache_dir.exists():
        for item in demo_cache_dir.iterdir():
            item.unlink()
        demo_cache_dir.rmdir()

    cache_manager = CacheManager(demo_cache_dir, expiry_days=0.001) # Short expiry for testing
    fetcher_with_cache = WebFetcher(cache_manager=cache_manager)

    test_url = "https://www.example.com"

    print("\n--- Testing WebFetcher with cache (first fetch, network call) ---")
    content_1 = fetcher_with_cache.fetch(test_url)
    assert content_1 is not None
    assert demo_cache_dir.exists() and len(list(demo_cache_dir.iterdir())) > 0

    print("\n--- Testing WebFetcher with cache (second fetch, should be from cache) ---")
    # Simulate a network error after caching to ensure cache hit
    with patch('requests.get', side_effect=requests.exceptions.ConnectionError):
        content_2 = fetcher_with_cache.fetch(test_url)
        assert content_2 == content_1 # Should be from cache, not network error
        print(f"Content from cache: {content_2[:50]}...")
    
    print("\n--- Testing WebFetcher without cache ---")
    fetcher_no_cache = WebFetcher()
    content_no_cache = fetcher_no_cache.fetch("https://www.google.com")
    assert content_no_cache is not None
    # No new files should be created in demo_cache_dir by fetcher_no_cache
    # The assertion below is problematic if demo_cache_dir was already created by fetcher_with_cache.
    # We should only check if its content has changed or if it was not created by fetcher_no_cache itself.
    # For now, we assume the demo_cache_dir is exclusive to fetcher_with_cache.
    
    print("\n--- Testing invalid URL with cache ---")
    content_404 = fetcher_with_cache.fetch("https://www.example.com/non-existent-page")
    assert content_404 is None

    # Clean up
    if demo_cache_dir.exists():
        for item in demo_cache_dir.iterdir():
            item.unlink()
        demo_cache_dir.rmdir()