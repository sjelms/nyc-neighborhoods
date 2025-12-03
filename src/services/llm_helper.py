import json
import os
import logging
from typing import Any, Dict, Optional

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
        model: str = "gpt-5-mini",
        api_key: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        # Lazy imports and .env loading to keep tests and offline runs happy
        self._openai = None
        self._client = None
        self.model = model
        self._enabled_requested = enabled

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

    def refine_profile_inputs(
        self,
        raw_data: Dict[str, Any],
        neighborhood_name: str,
        borough: str,
    ) -> Dict[str, Any]:
        """
        Send collected fields to the LLM and ask for a tightened, schema-aligned
        structure. Returns a dict with only the fields we intend to merge back
        into the pipeline. If disabled or any error occurs, returns an empty dict.
        """
        if not self.is_enabled:
            return {}

        try:
            # Compose a compact input payload for the model
            llm_input = {
                "neighborhood_name": neighborhood_name,
                "borough": borough,
                "summary": raw_data.get("summary", ""),
                "around_the_block": raw_data.get("around_the_block", ""),
                "neighborhood_facts": raw_data.get("neighborhood_facts", {}),
                "transit_accessibility": raw_data.get("transit_accessibility", {}),
                "sources": raw_data.get("sources", []),
            }

            system = (
                "You are a careful data normalizer for NYC neighborhood profiles. "
                "Given noisy scraped fields, return a STRICT JSON object with the following keys only: "
                "key_details, around_the_block, neighborhood_facts, transit_accessibility. "
                "- key_details must include what_to_expect, unexpected_appeal, the_market (short, factual, neutral). "
                "- around_the_block: a concise 1–2 sentence narrative capturing the essence; if empty in input, write one from summary. "
                "- neighborhood_facts must include population, population_density, area, boundaries, zip_codes. "
                "  Convert numbers to plain numbers when possible (no commas or units). If unknown, keep existing value. "
                "  boundaries has east_to_west, north_to_south, adjacent_neighborhoods (list). "
                "- transit_accessibility has nearest_subways, major_stations, bus_routes, rail_freight_other, highways_major_roads (lists). "
                "Keep it grounded in the provided input; do not invent facts."
            )

            user = (
                "Input fields (JSON):\n" + json.dumps(llm_input, ensure_ascii=False)
            )

            # Use chat.completions with JSON output if available
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},  # enforce JSON when supported
                    max_tokens=1200,
                )
                content = response.choices[0].message.content  # type: ignore[attr-defined]
            except Exception:
                # Fallback to responses API (in case the environment uses newer SDK)
                try:
                    content = (
                        self._client.responses.create(  # type: ignore
                            model=self.model,
                            temperature=0.2,
                            input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                            response_format={"type": "json_object"},
                            max_output_tokens=1200,
                        )
                        .output_text()
                    )
                except Exception as e2:
                    logger.warning(f"LLMHelper request failed, skipping LLM refinement. Reason: {e2}")
                    return {}

            if not content:
                return {}

            try:
                parsed = json.loads(content)
            except Exception:
                # If not strict JSON, attempt to find a JSON block
                try:
                    start = content.find("{")
                    end = content.rfind("}")
                    if start >= 0 and end > start:
                        parsed = json.loads(content[start : end + 1])
                    else:
                        return {}
                except Exception:
                    return {}

            # Filter to only the keys we accept
            allowed_top = {"key_details", "around_the_block", "neighborhood_facts", "transit_accessibility"}
            refined: Dict[str, Any] = {k: v for k, v in parsed.items() if k in allowed_top}
            return refined
        except Exception as e:
            logger.warning(f"LLMHelper encountered an error: {e}")
            return {}
