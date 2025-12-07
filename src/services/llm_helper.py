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

        def _is_effectively_empty(payload: Dict[str, Any]) -> bool:
            kd = payload.get("key_details", {})
            nf = payload.get("neighborhood_facts", {})
            ta = payload.get("transit_accessibility", {})
            if any(kd.get(k) for k in ["what_to_expect", "unexpected_appeal", "the_market"]):
                return False
            if payload.get("around_the_block"):
                return False
            if any(nf.get(k) for k in ["population", "population_density", "area"]):
                return False
            b = nf.get("boundaries", {})
            if any(b.get(k) for k in ["east_to_west", "north_to_south"]):
                return False
            if nf.get("zip_codes"):
                return False
            if any(ta.get(k) for k in ["nearest_subways", "major_stations", "bus_routes", "rail_freight_other", "highways_major_roads"]):
                return False
            return True

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
                            if _is_effectively_empty(parsed):
                                logger.info(f"Cached LLM response for {neighborhood_name} is effectively empty; refreshing.")
                                try:
                                    self.cache_manager.delete(cache_filename, cache_subdirectory)
                                except Exception:
                                    pass
                            else:
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
                "You are an expert data extractor for NYC neighborhood profiles with a commercial/CRE emphasis. "
                "Your task is to parse the provided 'page_text' and populate a STRICT JSON object with the schema below. "
                "Ground all answers in the provided text. Do not invent facts. If truly absent, return empty strings or empty lists.\n"
                "SCHEMA:\n"
                "{\n"
                "  \"key_details\": {\n"
                "    \"what_to_expect\": \"...\",\n"
                "    \"unexpected_appeal\": \"...\",\n"
                "    \"the_market\": \"...\"\n"
                "  },\n"
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
                "INSTRUCTIONS (commercial focus):\n"
                "1) key_details: Write concise, neutral, CRE-aware sentences. Mention retail corridors, industrial/warehouse presence, manufacturing legacy, parking availability, zoning/land-use hints, and commercial vibrancy when present. Avoid residential language.\n"
                "2) around_the_block: 1-2 sentences summarizing the commercial vibe (retail streets, mixed-use density, industrial edges) from the intro/overview.\n"
                "3) neighborhood_facts:\n"
                "   - population/density/area: prefer values from infobox/demographics; keep units as seen (plain text ok).\n"
                "   - boundaries: summarize E-W and N-S if text mentions 'bounded by' or similar; list adjacent neighborhoods if explicit.\n"
                "   - zip_codes: list all 5-digit ZIPs.\n"
                "4) transit_accessibility: from transportation/public transit sections.\n"
                "   - nearest_subways: subway lines (single letters/numbers).\n"
                "   - bus_routes: bus IDs (Q, B, M, Bx + number).\n"
                "   - major_stations: named stations/terminals.\n"
                "   - highways_major_roads: named highways/major arterials.\n"
                "Return ONLY the JSON object."
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
