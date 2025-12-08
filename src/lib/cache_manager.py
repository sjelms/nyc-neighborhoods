import hashlib
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger("nyc_neighborhoods")

class CacheManager:
    """
    Manages a file-based cache for web content.
    Each URL's content is stored in a separate file within the cache directory.
    """
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CacheManager initialized. Cache directory: {os.path.relpath(self.cache_dir)}")

    def _get_cache_path(self, filename: str, subdirectory: str) -> Path:
        """Generates a file path within a specific subdirectory of the cache."""
        sub_cache_dir = self.cache_dir / subdirectory
        sub_cache_dir.mkdir(parents=True, exist_ok=True) # Ensure subdirectory exists
        return sub_cache_dir / filename

    def get_file_path(self, filename: str, subdirectory: str) -> Optional[Path]:
        """
        Returns the Path object for a cached file if it exists, otherwise None.
        """
        cache_file = self._get_cache_path(filename, subdirectory)
        if cache_file.exists():
            return cache_file
        return None

    def get(self, filename: str, subdirectory: str) -> Optional[str]:
        """
        Retrieves content from a cached file.
        Returns the content as a string if found, otherwise None.
        """
        cache_file = self._get_cache_path(filename, subdirectory)
        if not cache_file.exists():
            logger.debug(f"Cache miss: {os.path.join(subdirectory, filename)}")
            return None
        
        try:
            content = cache_file.read_text(encoding='utf-8')
            logger.debug(f"Cache hit: {os.path.join(subdirectory, filename)}")
            return content
        except Exception as e:
            logger.error(f"Error reading cache file {os.path.relpath(cache_file)}: {e}")
            return None

    def set(self, filename: str, content: str, subdirectory: str):
        """
        Stores content in a specific cached file.
        """
        cache_file = self._get_cache_path(filename, subdirectory)
        try:
            cache_file.write_text(content, encoding='utf-8')
            logger.debug(f"Content cached to {os.path.join(subdirectory, filename)}")
        except Exception as e:
            logger.error(f"Error writing cache file {os.path.relpath(cache_file)}: {e}")


    
    def delete(self, filename: str, subdirectory: str):
        """
        Deletes a specific cached file.
        """
        cache_file = self._get_cache_path(filename, subdirectory)
        if cache_file.exists():
            try:
                cache_file.unlink()
                logger.debug(f"Deleted cache file: {os.path.join(subdirectory, filename)}")
            except Exception as e:
                logger.error(f"Error deleting cache file {os.path.relpath(cache_file)}: {e}")

    def clear_all(self):
        """Clears all cache entries from the cache directory."""
        logger.info(f"Clearing all cache entries in {os.path.relpath(self.cache_dir)}.")
        # Iterate through subdirectories too
        for item in self.cache_dir.iterdir():
            if item.is_dir():
                for cache_file in item.iterdir():
                    if cache_file.is_file():
                        try:
                            cache_file.unlink()
                        except Exception as e:
                            logger.error(f"Error deleting cache file {os.path.relpath(cache_file)}: {e}")
                try:
                    item.rmdir() # Remove empty subdirectory
                except Exception as e:
                    logger.error(f"Error removing cache subdirectory {os.path.relpath(item)}: {e}")
            elif item.is_file(): # For any files directly in cache_dir
                try:
                    item.unlink()
                except Exception as e:
                    logger.error(f"Error deleting cache file {os.path.relpath(item)}: {e}")


if __name__ == '__main__':
    from src.lib.logger import setup_logging
    setup_logging(level=logging.INFO)

    demo_cache_dir = Path("temp_cache")
    
    # Clean up previous demo run
    if demo_cache_dir.exists():
        for item in demo_cache_dir.iterdir():
            item.unlink()
        demo_cache_dir.rmdir()

    cache_manager = CacheManager(demo_cache_dir, expiry_days=0.001) # Very short expiry for testing

    test_url_1 = "http://example.com/page1"
    test_content_1 = "<html><body>Page 1 Content</body></html>"

    test_url_2 = "http://example.com/page2"
    test_content_2 = "<html><body>Page 2 Content</body></html>"

    # Test set and get
    cache_manager.set(test_url_1, test_content_1)
    retrieved_content_1 = cache_manager.get(test_url_1)
    print(f"\nRetrieved content 1: {retrieved_content_1 == test_content_1}")

    # Test cache miss (different URL)
    retrieved_content_2 = cache_manager.get(test_url_2)
    print(f"Retrieved content 2 (expected None): {retrieved_content_2 is None}")

    # Test expiry
    cache_manager.set(test_url_2, test_content_2)
    print("Waiting for cache to expire...")
    import time
    time.sleep(1) # Wait for expiry (0.001 days is ~1.44 minutes, so 1 second should be enough for this test)
    retrieved_content_2_expired = cache_manager.get(test_url_2)
    print(f"Retrieved content 2 after expiry (expected None): {retrieved_content_2_expired is None}")
    
    # Test clearing all
    cache_manager.set(test_url_1, test_content_1 + "updated")
    cache_manager.set(test_url_2, test_content_2 + "updated")
    print(f"Cache dir content before clear_all: {list(demo_cache_dir.iterdir())}")
    cache_manager.clear_all()
    print(f"Cache dir content after clear_all: {list(demo_cache_dir.iterdir())}")
    assert not list(demo_cache_dir.iterdir())

    # Clean up
    if demo_cache_dir.exists():
        demo_cache_dir.rmdir()
