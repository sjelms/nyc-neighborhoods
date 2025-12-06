import requests
import logging
import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path
import re # Added re import
from src.lib.cache_manager import CacheManager

logger = logging.getLogger("nyc_neighborhoods")

class WebFetcher:
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; nyc-neighborhoods/1.0; +https://example.com)",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, cache_manager: Optional[CacheManager] = None, headers: Optional[dict] = None, expiry_days: int = 7):
        self.cache_manager = cache_manager
        self.headers = headers or self.DEFAULT_HEADERS
        self.expiry_time = timedelta(days=expiry_days) if expiry_days > 0 else None

    def _get_cache_filename_and_subdir(self, url: str, item_name: Optional[str] = None, item_type: str = "html") -> Tuple[str, str]:
        # Clean up item_name for use in filename
        cleaned_item_name = re.sub(r'[^\w\-_\.]', '', item_name.replace(' ', '_')) if item_name else None

        if cleaned_item_name:
            # Use descriptive filename if available
            filename = f"{cleaned_item_name}.{item_type}"
        else:
            # Fallback to hash if no descriptive name is provided
            url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
            filename = f"{url_hash}.{item_type}" # Using .type as extension now

        # Determine subdirectory based on item_type
        subdirectory = "html" if item_type == "html" else "json" # Default to html, or json for rest api responses
        
        return filename, subdirectory

    def fetch_json(self, url: str, item_name: Optional[str] = None) -> Optional[dict]:
        """
        Fetches JSON content from a given URL, utilizing a cache if provided,
        and manages cache expiry.
        """
        item_type = "json"
        if not self.cache_manager or not self.expiry_time:
            # Bypass cache if not configured
            return self._fetch_json_from_network(url, item_name, item_type)

        # Generate cache filename and subdirectory
        filename, subdirectory = self._get_cache_filename_and_subdir(url, item_name, item_type)

        # Attempt to retrieve from cache
        cached_raw_entry = self.cache_manager.get(filename, subdirectory)
        if cached_raw_entry:
            try:
                cache_entry = json.loads(cached_raw_entry)
                cached_timestamp = datetime.fromisoformat(cache_entry['timestamp'])
                
                if datetime.now() - cached_timestamp < self.expiry_time:
                    logger.info(f"Retrieved JSON for {url} from cache ({os.path.join(subdirectory, filename)}).")
                    return cache_entry['content']
                else:
                    logger.debug(f"Cache miss: {url} (expired). Deleting {filename}.")
                    self.cache_manager.delete(filename, subdirectory) # Delete expired entry
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Corrupted cache file for {url} at {os.path.join(subdirectory, filename)}. Deleting. Error: {e}")
                self.cache_manager.delete(filename, subdirectory)
            except Exception as e:
                logger.error(f"Error processing cached entry for {url} at {os.path.join(subdirectory, filename)}: {e}")
        
        # If not in cache or expired/corrupted, fetch from network
        return self._fetch_json_from_network(url, item_name, item_type, filename, subdirectory)

    def _fetch_json_from_network(self, url: str, item_name: Optional[str], item_type: str, cache_filename: Optional[str] = None, cache_subdirectory: Optional[str] = None) -> Optional[dict]:
        """Internal helper to fetch JSON content from the network and optionally cache it."""
        logger.info(f"Attempting to fetch JSON from network: {url}")
        content = None
        try:
            response = requests.get(url, timeout=10, headers={**self.headers, "Accept": "application/json"})
            response.raise_for_status()
            content = response.json()
            logger.info(f"Successfully fetched JSON from network: {url}")
            
            if self.cache_manager and self.expiry_time:
                # Prepare filename and subdirectory for caching
                filename, subdirectory = self._get_cache_filename_and_subdir(url, item_name, item_type)
                if cache_filename: filename = cache_filename # Use provided filename if in retry
                if cache_subdirectory: subdirectory = cache_subdirectory # Use provided subdirectory if in retry

                cache_entry = {
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'content': content
                }
                self.cache_manager.set(filename, json.dumps(cache_entry), subdirectory)
                logger.info(f"Content for {url} saved to cache ({os.path.join(subdirectory, filename)}).")
            
            return content
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching JSON {url}: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error fetching JSON {url}: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error fetching JSON {url}: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"An unexpected request error occurred while fetching JSON {url}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing JSON: {e}")
        return None

    def fetch(self, url: str, item_name: Optional[str] = None, item_type: str = "html") -> Optional[str]:
        """
        Fetches content from a given URL, utilizing a cache if provided,
        and manages cache expiry.

        Args:
            url: The URL to fetch.
            item_name: A descriptive name for the item, used in the cache filename.
            item_type: The type of item, used for the cache subdirectory and file extension.

        Returns:
            The content of the URL as a string, or None if an error occurred.
        """
        if not self.cache_manager or not self.expiry_time:
            # Bypass cache if not configured (expiry_days <= 0)
            return self._fetch_from_network(url, item_name, item_type)

        # Generate cache filename and subdirectory
        filename, subdirectory = self._get_cache_filename_and_subdir(url, item_name, item_type)

        # Attempt to retrieve from cache
        cached_raw_entry = self.cache_manager.get(filename, subdirectory)
        if cached_raw_entry:
            try:
                cache_entry = json.loads(cached_raw_entry)
                cached_timestamp = datetime.fromisoformat(cache_entry['timestamp'])
                
                if datetime.now() - cached_timestamp < self.expiry_time:
                    logger.info(f"Retrieved content for {url} from cache ({os.path.join(subdirectory, filename)}).")
                    return cache_entry['content']
                else:
                    logger.debug(f"Cache miss: {url} (expired). Deleting {filename}.")
                    self.cache_manager.delete(filename, subdirectory) # Delete expired entry
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Corrupted cache file for {url} at {os.path.join(subdirectory, filename)}. Deleting. Error: {e}")
                self.cache_manager.delete(filename, subdirectory)
            except Exception as e:
                logger.error(f"Error processing cached entry for {url} at {os.path.join(subdirectory, filename)}: {e}")
        
        # If not in cache or expired/corrupted, fetch from network
        return self._fetch_from_network(url, item_name, item_type, filename, subdirectory)

    def _fetch_from_network(self, url: str, item_name: Optional[str], item_type: str, cache_filename: Optional[str] = None, cache_subdirectory: Optional[str] = None) -> Optional[str]:
        """Internal helper to fetch content from the network and optionally cache it."""
        logger.info(f"Attempting to fetch content from network: {url}")
        content = None
        try:
            response = requests.get(url, timeout=10, headers=self.headers)
            response.raise_for_status()
            content = response.text
            logger.info(f"Successfully fetched content from network: {url}")
            
            if self.cache_manager and self.expiry_time:
                # Prepare filename and subdirectory for caching
                filename, subdirectory = self._get_cache_filename_and_subdir(url, item_name, item_type)
                if cache_filename: filename = cache_filename # Use provided filename if in retry
                if cache_subdirectory: subdirectory = cache_subdirectory # Use provided subdirectory if in retry

                cache_entry = {
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'content': content
                }
                self.cache_manager.set(filename, json.dumps(cache_entry), subdirectory)
                logger.info(f"Content for {url} saved to cache ({os.path.join(subdirectory, filename)}).")
            
            return content
        except requests.exceptions.HTTPError as e:
            # If forbidden from Wikipedia, try mobile site as a fallback
            if getattr(response, "status_code", None) == 403 and "wikipedia.org" in url:
                mobile_url = url.replace("https://en.wikipedia.org", "https://en.m.wikipedia.org")
                logger.warning(f"HTTP 403 for {url}; retrying via mobile Wikipedia at {mobile_url}")
                try:
                    response_mobile = requests.get(mobile_url, timeout=10, headers=self.headers)
                    response_mobile.raise_for_status()
                    content = response_mobile.text
                    if self.cache_manager and self.expiry_time:
                        # Re-use filename/subdirectory from original attempt
                        filename, subdirectory = self._get_cache_filename_and_subdir(url, item_name, item_type)
                        if cache_filename: filename = cache_filename
                        if cache_subdirectory: subdirectory = cache_subdirectory

                        cache_entry = {
                            'url': url,
                            'timestamp': datetime.now().isoformat(),
                            'content': content
                        }
                        self.cache_manager.set(filename, json.dumps(cache_entry), subdirectory)
                    return content
                except Exception as mobile_error:
                    logger.error(f"Fallback mobile fetch failed for {mobile_url}: {mobile_error}")
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
