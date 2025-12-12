# NYC Neighborhood Profiles
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![ChatGPT](https://img.shields.io/badge/chatGPT-74aa9c?style=for-the-badge&logo=openai&logoColor=white)

A CLI tool that turns a CSV of NYC neighborhoods into polished, standardized Markdown profiles. It fetches and parses Wikipedia by default, normalizes demographics/boundaries/transit, then uses an LLM (on by default) to synthesize the commercial narrative and fill gaps so the output is publication-ready. If no OpenAI key is available, it falls back to parser-only output, which will be much sparser.

## How it works (at a glance)
- Read a CSV with `Neighborhood` and `Borough`.
- Fetch each neighborhood’s Wikipedia page (cached for repeatable runs).
- Parse infobox + transport/geography sections for hard facts.
- Run the LLM to produce “Key Details” and “Around the Block” narratives and to backfill missing facts.
- Render the profile into a Markdown template, apply automated content corrections (e.g., fixing punctuation, adding a disclaimer), and log the generation for skip/force/update workflows.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/nyc-neighborhoods.git
    cd nyc-neighborhoods
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    python3 -m pip install -r requirements.txt
    ```

## Usage

The primary way to use this tool is via its command-line interface (CLI).

```bash
python3 -m src.cli.main generate-profiles [OPTIONS]
# Underscore alias is also accepted: generate_profiles
```

### Options:

*   `-i, --input-csv <PATH>`: **Required.** Path to the input CSV file containing `Neighborhood` and `Borough` columns.
*   `-o, --output-dir <PATH>`: **Required.** Path to the directory where generated Markdown files will be saved.
*   `-t, --template-path <PATH>`: Path to the Markdown template file for output. Defaults to `output-template.md`.
*   `-v, --version <TEXT>`: Version of the generated profiles. Defaults to `1.0`.
*   `-r, --ratified-date <YYYY-MM-DD>`: Date when the profile format was ratified. Defaults to today's date.
*   `-a, --last-amended-date <YYYY-MM-DD>`: Date when the profile was last amended. Defaults to today's date.
*   `-l, --log-level <TEXT>`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Defaults to `INFO`.
*   `-c, --cache-dir <PATH>`: Path to the directory for caching web content. Defaults to `cache`.
*   `-e, --cache-expiry-days <INT>`: Number of days before cached web content expires. Set to `0` to disable caching. Defaults to `7`.
*   `--odid, --nyc-open-data-dataset-id <TEXT>`: **Temporarily parked.** Option is accepted but ignored while the NYC Open Data integration is disabled pending API documentation review.
*   `-f, --force-regenerate`: A boolean flag that, when present, forces the re-generation of all profiles, even if they already exist in the log.
    - If a force-regenerate attempt fails, a marker file named `Neighborhood_Borough_regenerate-fail-<timestamp>.md` is written with the version suffixed by `-fail`, leaving any existing profile untouched.
*   `-u, --update-since <YYYY-MM-DD>`: A date string that instructs the tool to only re-generate profiles that were last amended *on or after* this date.
*   `--log-file, --generation-log-file, --glf <PATH>`: Path to the JSON log file for tracking generated profiles. Defaults to `logs/generation_log.json`.
*   `--use-llm/--no-llm`: Enable or disable the LLM-assisted structuring layer (enabled by default; auto-disables when `OPENAI_API_KEY` is missing, which will reduce richness).
*   `--llm-model <TEXT>`: LLM model name to use when the helper is enabled. Defaults to `gpt-5.1-2025-11-13`.

### Example:

```bash
python3 -m src.cli.main generate-profiles \
  --input-csv /path/to/your/neighborhoods.csv \
  --output-dir ./generated_profiles \
  --template-path ./output-template.md \
  --version "1.0" \
  --ratified-date "2025-12-01" \
  --last-amended-date "2025-12-02" \
  --log-level "INFO" \
  --cache-dir "./my_cache" \
  --cache-expiry-days 30 \
  --nyc-open-data-dataset-id "ntacode_dataset_placeholder" \
  --force-regenerate \
  --update-since "2025-01-01" \
  --log-file "./logs/my_custom_log.json" \
  --no-llm
```

### Organize existing profiles by borough

Newly generated profiles are written directly into `<output-dir>/<borough>/` (spaces become underscores). Regenerate-fail marker files stay in `<output-dir>` so they are easy to spot. If you have older flat files, you can move them into borough subfolders without regenerating:

```bash
python3 -m src.cli.main organize-profiles \
  --profiles-dir output/profiles \
  --dry-run
```

Remove `--dry-run` to perform the moves. Regenerate-fail marker files are skipped unless you pass `--include-failure-artifacts`.

## Input CSV Format

Your input CSV file should have at least two columns: `Neighborhood` and `Borough`.

Example `neighborhoods.csv`:

```csv
Neighborhood,Borough
Maspeth,Queens
Williamsburg,Brooklyn
Astoria,Queens
```

## Output Markdown Template

The tool generates Markdown files based on a template. An example template (`reference/output-template.md`) is provided in the repository. You can customize this template to control the structure and content of the generated neighborhood profiles. The default template includes:

- Metadata header (Version, Ratified, Last Amended)
- Key Details (three short bullets, enriched by the LLM when enabled)
- Around the Block (LLM-generated multi-paragraph commercial/industrial narrative when enabled, otherwise derived from page text)
- Neighborhood Facts (population, density, area, boundaries, ZIPs)
- Transit & Accessibility (subways, stations, buses, other transit, highways/major roads)
- Commute Times (optional)
- Online Resources (Wikipedia link auto-populated; official link if available)
- An AI-generated content disclaimer appended at the end of the file.

## Development

Refer to the `tasks.md` and other documentation in the `specs/` directory for development details, design decisions, and task tracking.

### Key recent changes:
- **Integrated Content Cleanup:** The generation process now includes an automated cleanup step that fixes common formatting issues, such as removing extra spaces before punctuation and standardizing subway line formatting.
- **AI Disclaimer:** A disclaimer is now automatically appended to each generated profile to note the use of AI.
- **Borough-Based File Organization:** Newly generated profiles are now saved in borough-specific subdirectories (`output/profiles/Bronx`, `output/profiles/Brooklyn`, etc.) for better organization. An `organize-profiles` CLI command was added to help migrate older, unsorted profiles.
- **Robust Caching:** The caching mechanism has been enhanced, with separate directories for fetched HTML (`cache/html/`) and LLM responses (`cache/llm/`). This improves debugging and allows for more granular cache management.
- **LLM API Fixes:** Resolved issues with LLM API parameters (`max_tokens`, `temperature`) and upgraded the default model to ensure reliable and high-quality JSON output for data enrichment.
- **Generation Log Enhancements:** The generation log is now more robust, enabling more reliable skipping of existing profiles and targeted regeneration with `--force-regenerate` and `--update-since`.

### Example Generation Command

```bash
python3 -m src.cli.main generate-profiles \
--input-csv reference/neighborhood-borough.csv \
--output-dir output/profiles \
--template-path reference/output-template.md \
--log-level INFO \
--cache-dir cache \
--cache-expiry-days 7 \
--use-llm \
--force-regenerate
```
