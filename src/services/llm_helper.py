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
        self._enabled = False
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
                "page_text": raw_data.get("page_text", ""),
            }

            system = (
                "You are a careful data normalizer for NYC neighborhood profiles. "
                "Given noisy scraped fields and raw page text, return a STRICT JSON object with the following keys only: "
                "key_details, around_the_block, neighborhood_facts, transit_accessibility. "
                "- key_details must include what_to_expect, unexpected_appeal, the_market (short, factual, neutral). "
                "- around_the_block: a concise 1–2 sentence narrative capturing the essence; if empty in input, write one from summary and page_text. "
                "- neighborhood_facts must include population, population_density, area, boundaries, zip_codes. "
                "  Convert numbers to plain numbers when possible (no commas or units). If unknown, keep existing value. "
                "  boundaries has east_to_west, north_to_south, adjacent_neighborhoods (list). "
                "- transit_accessibility has nearest_subways, major_stations, bus_routes, rail_freight_other, highways_major_roads (lists). "
                "- Use page_text to recover transit/boundary facts when the structured fields are empty. "
                "Keep it grounded in the provided input; do not invent facts."
            )

            user = (
                "Input fields (JSON):\n" + json.dumps(llm_input, ensure_ascii=False)
            )

            base_params = {
                "model": self.model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},  # enforce JSON when supported
            }

            # Try token parameter variants in order (modern -> legacy), skipping ones the API rejects.
            # Try token parameter variants in order (most likely to be supported for GPT-4.1/5 style models)
            token_param_options = [
                ("max_completion_tokens", 1600),  # new SDK/models
                ("max_tokens", 1600),             # legacy
                (None, None),                     # last resort: rely on model default limits
            ]
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
                    # If the error is clearly about an unsupported parameter, try the next option
                    if hasattr(e, "response") and getattr(e, "response", None) is not None:
                        try:
                            err_json = e.response.json()  # type: ignore[attr-defined]
                            message = err_json.get("error", {}).get("message", "").lower()
                            if param_name and param_name.replace("_", " ") in message:
                                continue
                        except Exception:
                            pass
                    # Otherwise bail out
                    break

            if response is None:
                if last_error:
                    raise last_error
                raise RuntimeError("LLM request failed with no response and no exception.")

            content = ""
            # Guard against unexpected shapes from the SDK
            if hasattr(response, "choices") and response.choices:
                message = response.choices[0].message  # type: ignore[attr-defined]
                if message and hasattr(message, "content"):
                    raw_content = message.content  # type: ignore[attr-defined]
                    if isinstance(raw_content, list):
                        # Newer SDKs may return structured content parts
                        content = "".join(
                            part.get("text", "") if isinstance(part, dict) else str(part) for part in raw_content
                        )
                    elif isinstance(raw_content, str):
                        content = raw_content

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
            # Disable further attempts for the remainder of the run to avoid noisy retries
            self._enabled = False
            logger.warning(
                "LLMHelper request failed; disabling LLM for this run. "
                f"Reason: {e}. Run with --no-llm or check OPENAI_API_KEY."
            )
            return {}
