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
    def __init__(self, cache_dir: Path, expiry_days: int = 7):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.expiry_time = timedelta(days=expiry_days)
        logger.info(f"CacheManager initialized. Cache directory: {os.path.relpath(self.cache_dir)}, Expiry: {self.expiry_time}")

    def _get_cache_path(self, url: str) -> Path:
        """Generates a unique file path for a URL in the cache."""
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{url_hash}.json"

    def get(self, url: str) -> Optional[str]:
        """
        Retrieves cached content for a given URL.
        Returns the content as a string if found and not expired, otherwise None.
        """
        cache_file = self._get_cache_path(url)
        if not cache_file.exists():
            logger.debug(f"Cache miss: {url} (file not found)")
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_entry = json.load(f)
            
            cached_timestamp = datetime.fromisoformat(cache_entry['timestamp'])
            if datetime.now() - cached_timestamp > self.expiry_time:
                logger.debug(f"Cache miss: {url} (expired)")
                cache_file.unlink() # Delete expired entry
                return None
            
            logger.debug(f"Cache hit: {url}")
            return cache_entry['content']
        except json.JSONDecodeError:
            logger.warning(f"Corrupted cache file for {url} at {os.path.relpath(cache_file)}. Deleting.")
            cache_file.unlink(missing_ok=True)
            return None
        except Exception as e:
            logger.error(f"Error reading cache for {url} at {os.path.relpath(cache_file)}: {e}")
            return None

    def set(self, url: str, content: str):
        """
        Stores content for a given URL in the cache.
        """
        cache_file = self._get_cache_path(url)
        try:
            cache_entry = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'content': content
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, ensure_ascii=False, indent=2)
            logger.debug(f"Content for {url} cached to {cache_file}")
        except Exception as e:
            logger.error(f"Error writing cache for {url} to {os.path.relpath(cache_file)}: {e}")

    def clear_expired(self):
        """Clears all expired cache entries from the cache directory."""
        logger.info("Clearing expired cache entries.")
        for cache_file in self.cache_dir.iterdir():
            if cache_file.is_file() and cache_file.suffix == ".json":
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_entry = json.load(f)
                    cached_timestamp = datetime.fromisoformat(cache_entry['timestamp'])
                    if datetime.now() - cached_timestamp > self.expiry_time:
                        cache_file.unlink()
                        logger.debug(f"Removed expired cache entry: {cache_file.name}")
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"Corrupted or invalid cache file {cache_file}. Deleting. Error: {e}")
                    cache_file.unlink(missing_ok=True)
                except Exception as e:
                    logger.error(f"Unexpected error during cache cleanup for {cache_file}: {e}")
    
    def clear_all(self):
        """Clears all cache entries from the cache directory."""
        logger.info(f"Clearing all cache entries in {os.path.relpath(self.cache_dir)}.")
        for cache_file in self.cache_dir.iterdir():
            if cache_file.is_file():
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.error(f"Error deleting cache file {os.path.relpath(cache_file)}: {e}")


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
