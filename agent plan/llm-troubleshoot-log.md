### LLM helper troubleshooting log

**Context:** Feature branch `002-helper-llm-feature` adds an optional LLM layer to enrich parsed Wikipedia/Open Data content (Key Details, Around the Block, Transit). Runs are on macOS with `python3`, Typer CLI (`generate-profiles`), OpenAI SDK, and `.env`-provided `OPENAI_API_KEY`.

---

#### Attempt history (chronological)

- **Initial integration (prior work):** Added `src/services/llm_helper.py`, wired into `DataNormalizer` to fill gaps only; added CLI flags `--use-llm/--no-llm`, `--llm-model`. No key loading errors but default pipeline unchanged when LLM disabled.
- **Dec 3 ~09:04–09:30:** Runs failed with `401 Unauthorized` because `.env` had an unresolved 1Password reference (`op://...`). LLM disabled; output matched Python-only scraper.
- **Fixes applied:**
  - Disabled LLM when `OPENAI_API_KEY` looks like `op://...`.
  - Relaxed `NeighborhoodFacts` fields to strings to prevent Pydantic crashes on messy numeric strings.
  - Added CLI alias `generate_profiles`; added log-file flag aliases; docs updated to `python3`.
  - Added full page text (`page_text`, truncated ~12k chars) into the LLM payload to give richer context.
  - Adjusted token params to prefer `max_completion_tokens`, with fallbacks.
- **Dec 3 ~09:54 run:** With real key present, LLM calls hit `400 Unsupported parameter: 'max_tokens'` → helper disabled → scraper-only output.
- **Dec 3 ~10:00 run:** After token handling change, LLM calls hit `Completions.create() got an unexpected keyword argument 'max_output_tokens'` (a param not supported by chat completions) → helper disabled → scraper-only output.
- **Current state (post-fix):** LLM helper now tries token params in this order: `max_completion_tokens`, then `max_tokens`, then none. `max_output_tokens` was removed. LLM still disabled in the last user run before this fix; needs a fresh run to confirm no 400/param errors.

---

#### Observed errors and causes

- `401 Unauthorized` with message showing `op://...` key → unresolved secret reference in `.env`.
- `400 Unsupported parameter: 'max_tokens'` → model/API requires `max_completion_tokens` for GPT-4.1/5 models.
- `unexpected keyword argument 'max_output_tokens'` → chat/completions endpoint doesn’t accept this; caused by previous fallback attempt.
- When LLM request fails once, helper disables itself for the run, so the rest of the batch uses scraper-only data.

---

#### Changes implemented in code

- `src/services/llm_helper.py`
  - Loads `.env`; disables when key missing or looks like `op://`.
  - Sends `page_text` plus parsed fields; structured JSON response enforced.
  - Token param handling: tries `max_completion_tokens`, then `max_tokens`, then no token param; stops on success, otherwise disables on error.
  - Content extraction supports both string and list-of-part formats from newer SDKs.
- `src/services/profile_generator.py`
  - Adds cleaned, truncated page text (`page_text`) from the full HTML to the LLM payload.
- `src/models/neighborhood_profile.py`
  - `population`, `population_density`, `area` now strings with normalization to avoid validation failures.
- `src/cli/main.py`
  - Added legacy command alias `generate_profiles`; added log-file flag aliases.
- Docs (`README.md`, quickstart, agent notes) updated to use `python3`, note aliases, and LLM flags.

---

#### Tests/commands attempted

- Multiple CLI runs:
  - `python3 -m src.cli.main generate-profiles --force-regenerate` (with/without real key).
  - LLM failures observed in `logs/app.log` with 401, 400, and unexpected param errors; helper disabled each time.
- Pytest not run successfully here (pytest not installed in this environment).

---

#### Current blockers

- Need a clean LLM call: ensure the token param set now works with the deployed OpenAI SDK/model. Latest change removed `max_output_tokens` and should avoid the 400/param errors, but needs a fresh run to verify.
- If the model still rejects both `max_completion_tokens` and `max_tokens`, we may need to send no token param at all or target a different model (e.g., `gpt-4o-mini`) that accepts one of these.

---

#### Action items / next steps

1) **Re-run after latest token-param fix:**  
   `python3 -m src.cli.main generate-profiles --force-regenerate` with a real `OPENAI_API_KEY`. Check `logs/app.log` for LLM success vs. disable messages. Expect no “max_output_tokens” or “max_tokens unsupported” errors.

2) **If still failing on params:**  
   - Set `--llm-model gpt-4o-mini` (or another known-compatible model) to align with SDK expectations.  
   - As a fallback, remove token params entirely and let the model default limits apply.

3) **If LLM succeeds but fields still empty:**  
   - Loosen merge rules to allow LLM values to overwrite empties and short placeholders (e.g., “Information not available”).  
   - Increase `page_text` limit (e.g., to ~20k) if context seems truncated.

4) **Verification steps:**  
   - After a successful LLM call, ensure `DataNormalizer` appends a warning like “Applied LLM-assisted structuring…” and inspect generated Markdown to confirm Key Details and Transit are populated.  
   - Optionally add a log line when LLM merge applies, to confirm behavior even when no warnings are added.

5) **Environment sanity:**  
   - `.env` should contain `OPENAI_API_KEY=sk-...` (no `op://`).  
   - Ensure venv is active and OpenAI SDK is installed (`python3 -m pip install -r requirements.txt`).

