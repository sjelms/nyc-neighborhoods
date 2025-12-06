import json
import os
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import re
from src.lib.cache_manager import CacheManager

logger = logging.getLogger("nyc_neighborhoods")


class LLMHelper:
    """
    Optional helper that uses an LLM to refine and structure scraped data
    into a shape that aligns with our NeighborhoodProfile/template fields.

    Safe by default: if no API key or SDK is available, it remains disabled
    and returns the input unmodified.
    """

    def __init__(
        self,
        model: str = "gpt-5.1-2025-11-13",
        api_key: Optional[str] = None,
        enabled: bool = True,
        cache_manager: Optional['CacheManager'] = None, # Added
        expiry_days: int = 7, # Added
    ) -> None:
        # Lazy imports and .env loading to keep tests and offline runs happy
        self._openai = None
        self._client = None
        self.model = model
        self._enabled = False
        self._enabled_requested = enabled
        self.cache_manager = cache_manager # Added
        self.expiry_time = timedelta(days=expiry_days) if expiry_days > 0 else None # Added

        # Load .env if python-dotenv is available
        try:
            from dotenv import load_dotenv  # type: ignore

            load_dotenv()
        except Exception:
            # It's fine if dotenv isn't installed
            pass

        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            self._enabled = False
            logger.info("LLMHelper disabled: OPENAI_API_KEY not found.")
            return
        if isinstance(key, str) and key.strip().startswith("op://"):
            # Likely a 1Password reference that hasn't been resolved into a real key
            self._enabled = False
            logger.info("LLMHelper disabled: OPENAI_API_KEY appears to be an unresolved 1Password secret reference.")
            return

        if not enabled:
            self._enabled = False
            logger.info("LLMHelper disabled by configuration flag.")
            return

        try:
            # Prefer the modern OpenAI client if available
            from openai import OpenAI  # type: ignore

            self._openai = OpenAI
            self._client = OpenAI(api_key=key)
            self._enabled = True
        except Exception as e:
            logger.warning(f"LLMHelper could not initialize OpenAI client, running disabled. Reason: {e}")
            self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return bool(self._enabled and self._client is not None)

    @property
    def is_enabled(self) -> bool:
        return bool(self._enabled and self._client is not None)

    def _get_llm_cache_filename(self, neighborhood_name: str, borough: str) -> str:
        """Generates a descriptive, deterministic filename for LLM cache entries."""
        neighborhood_slug = re.sub(r'[^\w\-_\.]', '', neighborhood_name.replace(' ', '_'))
        borough_slug = re.sub(r'[^\w\-_\.]', '', borough.replace(' ', '_'))
        return f"{neighborhood_slug}_{borough_slug}.json"

    def refine_profile_inputs(
        self,
        raw_data: Dict[str, Any],
        neighborhood_name: str,
        borough: str
    ) -> Dict[str, Any]:
        """
        Send collected fields to the LLM and ask for a tightened, schema-aligned
        structure. Returns a dict with only the fields we intend to merge back
        into the pipeline. If disabled or any error occurs, returns an empty dict.
        """
        if not self.is_enabled:
            return {}

        # --- Caching Logic: READ ---
        if self.cache_manager:
            cache_filename = self._get_llm_cache_filename(neighborhood_name, borough)
            cache_subdirectory = "llm"
            
            cached_file_path = self.cache_manager.get_file_path(cache_filename, cache_subdirectory)

            if cached_file_path:
                is_expired = False
                if self.expiry_time:
                    file_mod_time = datetime.fromtimestamp(cached_file_path.stat().st_mtime)
                    if datetime.now() - file_mod_time > self.expiry_time:
                        is_expired = True
                        logger.info(f"LLM cache for {neighborhood_name} is expired. Fetching live.")

                if not is_expired:
                    logger.info(f"Using cached LLM response for {neighborhood_name} from {os.path.relpath(cached_file_path)}")
                    cached_content = self.cache_manager.get(cache_filename, cache_subdirectory)
                    if cached_content:
                        try:
                            # The cached content should already be the refined JSON
                            parsed = json.loads(cached_content)
                            # Return the cache path so the caller can log it.
                            parsed['llm_cache_path'] = str(cached_file_path.resolve())
                            return parsed
                        except json.JSONDecodeError:
                            logger.warning(f"Could not parse cached LLM response from {os.path.relpath(cached_file_path)}. Fetching live.")
        
        try:
            # Compose a compact input payload for the model
            llm_input = {
                "neighborhood_name": neighborhood_name,
                "borough": borough,
                "summary": raw_data.get("summary", ""),
                "around_the_block": raw_data.get("around_the_block", ""),
                "neighborhood_facts": raw_data.get("neighborhood_facts", {}),
                "page_text": raw_data.get("page_text", ""),
                "transportation_text": raw_data.get("transportation_text", "") # New focused text
            }
            logger.debug(f"LLM input payload: {json.dumps(llm_input, ensure_ascii=False, indent=2)}")

            system = (
                "You are a careful data normalizer for NYC neighborhood profiles. "
                "Given noisy scraped fields and various text inputs, return a STRICT JSON object with the following keys only: "
                "key_details, around_the_block, neighborhood_facts, transit_accessibility. "
                "- key_details must include what_to_expect, unexpected_appeal, the_market (short, factual, neutral). "
                "- around_the_block: a concise 1–2 sentence narrative capturing the essence; if empty in input, write one from summary. "
                "- neighborhood_facts must include population, population_density, area, boundaries, zip_codes. "
                "  Convert numbers to plain numbers when possible (no commas or units). "
                "  boundaries has east_to_west, north_to_south, adjacent_neighborhoods (list). "
                "- transit_accessibility: Use the 'transportation_text' field exclusively for this. "
                "  - From 'transportation_text', find all subway lines (e.g., N, W, R). Put them in 'nearest_subways'. "
                "  - From 'transportation_text', find all bus routes (e.g., Q18, Q69, M60). Put them in 'bus_routes'. "
                "  - From 'transportation_text', find all major station names (e.g., 'Astoria–Ditmars Boulevard'). Put them in 'major_stations'. "
                "  - From 'transportation_text', find all highways and major roads. Put them in 'highways_major_roads'. "
                "Keep it grounded in the provided input; do not invent facts."
            )

            user = (
                "Input fields (JSON):\n" + json.dumps(llm_input, ensure_ascii=False)
            )

            base_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},  # enforce JSON when supported
            }

            # Try token parameter variants
            token_param_options = [("max_completion_tokens", 1600), ("max_tokens", 1600), (None, None)]
            response = None
            last_error: Optional[Exception] = None
            for param_name, param_value in token_param_options:
                try:
                    request_kwargs = dict(base_params)
                    if param_name:
                        request_kwargs[param_name] = param_value
                    response = self._client.chat.completions.create(**request_kwargs)
                    break
                except Exception as e:
                    last_error = e
                    error_message = str(e).lower()
                    if param_name and (f"unsupported parameter: '{param_name}'" in error_message or f"got an unexpected keyword argument '{param_name}'" in error_message):
                        logger.debug(f"LLM param '{param_name}' not supported, trying next option.")
                        continue
                    break

            if response is None:
                if last_error:
                    raise last_error
                raise RuntimeError("LLM request failed with no response and no exception.")

            content = ""
            if hasattr(response, "choices") and response.choices:
                message = response.choices[0].message
                if message and hasattr(message, "content"):
                    raw_content = message.content
                    if isinstance(raw_content, list):
                        content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in raw_content)
                    elif isinstance(raw_content, str):
                        content = raw_content
            
            logger.debug(f"LLM raw response content: {content}")

            if not content:
                return {}

            try:
                parsed = json.loads(content)
            except Exception:
                # Attempt to recover JSON block
                start = content.find("{")
                end = content.rfind("}")
                if start >= 0 and end > start:
                    parsed = json.loads(content[start : end + 1])
                else:
                    return {}

            # Filter to only the keys we accept
            allowed_top = {"key_details", "around_the_block", "neighborhood_facts", "transit_accessibility"}
            refined: Dict[str, Any] = {k: v for k, v in parsed.items() if k in allowed_top}

            # --- Caching Logic: WRITE ---
            if self.cache_manager and refined:
                cache_filename = self._get_llm_cache_filename(neighborhood_name, borough)
                cache_subdirectory = "llm"
                # We store the successfully parsed and refined JSON
                self.cache_manager.set(cache_filename, json.dumps(refined, indent=2), cache_subdirectory)
                # Return the cache path so the caller can log it.
                refined['llm_cache_path'] = str((self.cache_manager.cache_dir / cache_subdirectory / cache_filename).resolve())

            return refined
        except Exception as e:
            self._enabled = False
            logger.warning(f"LLMHelper request failed; disabling LLM for this run. Reason: {e}")
            return {}
