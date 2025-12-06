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
    """

    def __init__(
        self,
        model: str = "gpt-5.1-2025-11-13",
        api_key: Optional[str] = None,
        enabled: bool = True,
        cache_manager: Optional['CacheManager'] = None,
        expiry_days: int = 7,
    ) -> None:
        self._openai = None
        self._client = None
        self.model = model
        self._enabled = False
        self._enabled_requested = enabled
        self.cache_manager = cache_manager
        self.expiry_time = timedelta(days=expiry_days) if expiry_days > 0 else None

        try:
            from dotenv import load_dotenv
            load_dotenv()
        except Exception:
            pass

        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            self._enabled = False
            logger.info("LLMHelper disabled: OPENAI_API_KEY not found.")
            return
        if isinstance(key, str) and key.strip().startswith("op://"):
            self._enabled = False
            logger.info("LLMHelper disabled: OPENAI_API_KEY appears to be an unresolved 1Password secret reference.")
            return
        if not enabled:
            self._enabled = False
            logger.info("LLMHelper disabled by configuration flag.")
            return

        try:
            from openai import OpenAI
            self._openai = OpenAI
            self._client = OpenAI(api_key=key)
            self._enabled = True
        except Exception as e:
            logger.warning(f"LLMHelper could not initialize OpenAI client, running disabled. Reason: {e}")
            self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return bool(self._enabled and self._client is not None)

    def _get_llm_cache_filename(self, neighborhood_name: str, borough: str) -> str:
        """Generates a descriptive, deterministic filename for LLM cache entries."""
        neighborhood_slug = re.sub(r'[^\w\-_.]', '', neighborhood_name.replace(' ', '_'))
        borough_slug = re.sub(r'[^\w\-_.]', '', borough.replace(' ', '_'))
        return f"{neighborhood_slug}_{borough_slug}.json"

    def refine_profile_inputs(
        self,
        raw_data: Dict[str, Any],
        neighborhood_name: str,
        borough: str
    ) -> Dict[str, Any]:
        """
        Processes raw text using an LLM to extract a structured JSON object.
        """
        if not self.is_enabled:
            return {}

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
                            parsed = json.loads(cached_content)
                            parsed['llm_cache_path'] = str(cached_file_path.resolve())
                            return parsed
                        except json.JSONDecodeError:
                            logger.warning(f"Could not parse cached LLM response. Fetching live.")
        
        try:
            llm_input = {
                "neighborhood_name": neighborhood_name,
                "borough": borough,
                "page_text": raw_data.get("page_text", "")
            }
            
            system_prompt = (
                "You are an expert data extractor for NYC neighborhood profiles. Your task is to parse the provided 'page_text' "
                "and populate a STRICT JSON object with the following schema. Ground all answers in the provided text. Do not invent facts.\n"
                "SCHEMA:\n"
                "{\n"
                "  \"key_details\": {\"what_to_expect\": \"...\", \"unexpected_appeal\": \"...\", \"the_market\": \"...\"},\n"
                "  \"around_the_block\": \"...\",\n"
                "  \"neighborhood_facts\": {\n"
                "    \"population\": \"...\",\n"
                "    \"population_density\": \"...\",\n"
                "    \"area\": \"...\",\n"
                "    \"boundaries\": {\"east_to_west\": \"...\", \"north_to_south\": \"...\", \"adjacent_neighborhoods\": []},\n"
                "    \"zip_codes\": []\n"
                "  },\n"
                "  \"transit_accessibility\": {\n"
                "    \"nearest_subways\": [],\n"
                "    \"major_stations\": [],\n"
                "    \"bus_routes\": [],\n"
                "    \"rail_freight_other\": [],\n"
                "    \"highways_major_roads\": []\n"
                "  }\n"
                "}\n"
                "INSTRUCTIONS:\n"
                "1.  **key_details**: Synthesize short, neutral, one-sentence descriptions for each key from the entire text.\n"
                "2.  **around_the_block**: Write a 1-2 sentence narrative capturing the neighborhood's essence from the summary and introduction.\n"
                "3.  **neighborhood_facts**:\n"
                "    - Find Population, Area, and Density from an infobox or 'Demographics' section. Convert numbers to plain integers where possible. If a value is given in multiple units, prefer the imperial unit (e.g., sq mi over km2).\n"
                "    - For 'boundaries', find descriptions of what borders the neighborhood (e.g., 'bounded by...'). Synthesize the E-W and N-S descriptions. List all unique adjacent neighborhoods.\n"
                "    - For 'zip_codes', find all 5-digit postal codes mentioned in the 'ZIP Codes' section or infobox.\n"
                "4.  **transit_accessibility**: Scour the 'Transportation' or 'Public transportation' section of the 'page_text'.\n"
                "    - `nearest_subways`: Find all subway lines. They are often single letters or numbers (e.g., N, W, R, 4, 5, 6).\n"
                "    - `bus_routes`: Find all bus routes. They usually start with a letter (Q, B, M, Bx) followed by a number (e.g., Q101, M60).\n"
                "    - `major_stations`: List any prominent train or subway station names.\n"
                "    - `highways_major_roads`: List all named highways, parkways, or major boulevards."
            )

            user_prompt = "Input text to parse:\n" + json.dumps(llm_input, ensure_ascii=False)

            base_params = {
                "model": self.model,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "response_format": {"type": "json_object"},
            }

            response = self._client.chat.completions.create(**base_params)
            content = response.choices[0].message.content if response.choices else ""
            
            logger.debug(f"LLM raw response content: {content}")
            if not content: return {}

            parsed = json.loads(content)
            
            allowed_top = {"key_details", "around_the_block", "neighborhood_facts", "transit_accessibility"}
            refined = {k: v for k, v in parsed.items() if k in allowed_top}

            if self.cache_manager and refined:
                cache_filename = self._get_llm_cache_filename(neighborhood_name, borough)
                cache_subdirectory = "llm"
                self.cache_manager.set(cache_filename, json.dumps(refined, indent=2), cache_subdirectory)
                refined['llm_cache_path'] = str((self.cache_manager.cache_dir / cache_subdirectory / cache_filename).resolve())

            return refined
        except Exception as e:
            logger.warning(f"LLMHelper request failed for {neighborhood_name}. Reason: {e}")
            # Do not disable the helper for the entire run for a single failure
            return {}