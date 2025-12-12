# Technical Summary — Automated Neighborhood Profile Generator

## 1. Overview & Objectives

- Develop a tool that, given a list of New York City neighborhoods, **automatically retrieves** public information (demographics, boundaries, transit, commercial context, etc.) from trusted online sources and  
  **outputs** a standardized markdown file per neighborhood following a fixed template.  
- Ensure outputs include a header with metadata:  
  **Version**, **Ratified Date**, and **Last Amended Date**.  
- Prioritize data accuracy and source traceability: prefer high‑authority sources (Wikipedia or official NYC Open Data datasets).  
- Design the system to be maintainable, extensible, and easy to review / update.

---

## 2. Data Sources & Source Selection Strategy

| Source | Purpose / Use Cases |
|--------|--------------------|
| **Wikipedia** (neighborhood pages) | Demographics, historical context, boundaries, ZIP codes, transit summary, notable features — often compiled with citations and used as primary scrape source. |
| **LLM (GPT series)** | Synthesizing narrative content ("Around the Block", "Key Details") and filling gaps in parsed data by structuring unstructured text. |
| **NYC Open Data** portal ([data.cityofnewyork.us](https://data.cityofnewyork.us)) | For more granular / official data — e.g. zoning, community district boundaries, land use, infrastructure, sanitation, or other public‑agency datasets. (Integration currently parked). |

**Source Strategy:**

- For each neighborhood, first attempt to retrieve a dedicated Wikipedia page. If found, use as primary source for narrative, demographics, transit overview.
- Use an LLM to enrich the parsed data, generate descriptive narratives, and fill in missing fields in a structured format.
- Supplement with NYC Open Data when available — especially for numeric data (zoning, land use, infrastructure), or to cross‑validate key facts.
- Where conflicting data exists (e.g. boundaries, ZIP codes), prefer official data (Open Data). If only Wikipedia exists, include a note and flag for manual review.

---

## 3. Input Specification

- Provide a **list of neighborhood names** as input.
  - Best stored in a **CSV file** with two columns: `Neighborhood`, `Borough`
  - CSV is simple to manage, editable in Excel or a text editor, and easy to parse.
- Optionally include metadata columns in CSV (e.g. `preferred_version`, `manual_override`) for future flexibility.

---

## 4. Output Specification

For each neighborhood, produce a standalone Markdown (`.md`) file using the following structure (see `reference/output-template.md`).

**File Location & Naming:**
- **Path:** `output/profiles/<Borough>/<Neighborhood>_<Borough>.md` (e.g., `output/profiles/Queens/Maspeth_Queens.md`)
- **Format:** Spaces in borough and neighborhood names are replaced with underscores.

**Content Structure:**
```markdown
**Version**: [VERSION] | **Ratified**: [RATIFIED_DATE] | **Last Amended**: [LAST_AMENDED_DATE]

## [Neighborhood Name]

[Short Summary Paragraph]

---

### Key Details
- **WHAT TO EXPECT:**  
- **UNEXPECTED APPEAL:**  
- **THE MARKET:**  

---

### Around the Block

[A 1–2 paragraph narrative]

---

### Neighborhood Facts
- **Population:**   
- **Population Density:**   
- **Area:** 
- **Boundaries:**  
...

---

### Transit & Accessibility
...

---

### Commute Times (optional — if data available)
...

### Online Resources
- **Official Website:** [Neighborhood Website URL]
- **Wikipedia:** [Wikipedia URL]

> **Disclaimer:** This content was generated in part by an artificial intelligence system...
```

- **Generation Log:** A companion log (`logs/generation_log.json`) tracks each generated file, its version, and key metadata to manage regeneration workflows (`--force-regenerate`, `--update-since`).

---

## 5. Technical Architecture & Tools

### Preferred Stack:
- Language: **Python 3.11**
- Libraries:
  - `requests` — for fetching web content
  - `beautifulsoup4` — for HTML parsing
  - `pandas` — for CSV parsing
  - `pydantic` — for data modeling
  - `typer` — for the command-line interface
  - `openai` — for interacting with the LLM API

### Components:
- **CLI (`main.py`)**: The entry point, defining commands (`generate-profiles`, `organize-profiles`) and options.
- **CSV Parser**: Reads the input CSV file.
- **Web Fetcher**: Fetches content from Wikipedia, with caching support.
- **Wikipedia Parser**: Extracts structured data (infoboxes, sections) from HTML.
- **LLM Helper**: A dedicated service that constructs prompts, interacts with the OpenAI API, and validates/parses the JSON response.
- **Data Normalizer**: Converts raw parsed data into the `NeighborhoodProfile` Pydantic model; orchestrates the LLM gap-fill.
- **Template Renderer**: Injects the structured data from the profile model into the Markdown template.
- **Profile Generator**: Orchestrates the entire process from fetching to file writing, including the final content cleanup.
- **Cache Manager**: A file-based caching utility. It's used by `WebFetcher` and `LLMHelper` to store downloaded HTML and LLM responses in `cache/html/` and `cache/llm/` respectively, reducing redundant API calls.
- **Generation Log**: A JSON-backed log to track generated profiles and their metadata.

---

## 6. Implementation Steps

1. **Project setup**: `input`, `output`, `logs`, and `cache` directories were created. Dependencies installed via `pip`.
2. **CSV Importer**: A `CSVParser` class was implemented to load `Neighborhood` and `Borough` data.
3. **Page Fetcher**: `WebFetcher` handles retrieving Wikipedia pages with caching.
4. **HTML Parser**: `WikipediaParser` uses BeautifulSoup to scrape key data points.
5. **Data Schema**: `NeighborhoodProfile` Pydantic model defines the data structure.
6. **Template Renderer**: `TemplateRenderer` populates the `.md` template.
7. **File Output**: `ProfileGenerator` saves files to `output/profiles/<Borough>/<File>.md` and records the action in `logs/generation_log.json`.
8. **CLI Interface**: A robust CLI was built with `Typer`, supporting various options for caching, regeneration, and LLM usage.
    ```bash
    # Example of a full command
    python3 -m src.cli.main generate-profiles \
      --input-csv reference/neighborhood-borough.csv \
      --output-dir output/profiles \
      --force-regenerate \
      --use-llm
    ```
9. **Testing**: Unit and integration tests were developed to validate parsing, data modeling, and generation logic.
10. **Refinement**: Logic was added for borough-based file organization and automated content cleanup (e.g., punctuation, adding disclaimer).

---

## 7. Source Tracking & Manual Overrides

- Each profile includes a link to its Wikipedia source.
- The generation log tracks the file path, version, and generation dates.
- No manual override system is currently implemented, but it is a potential future enhancement.

---

## 8. Versioning & Maintenance

- Version metadata is included at the top of each profile (`Version`, `Ratified`, `Last Amended`).
- **Automated Content Cleanup**: A post-processing step integrated into the generation pipeline automatically corrects common formatting errors (e.g., spacing and punctuation) and appends an AI-generated content disclaimer.
- **Refresh Process**: To refresh profiles, re-run the generator with `--force-regenerate`. The `Last Amended` date should be updated accordingly.
- **LLM Cache Refresh**: The system is designed to re-request LLM responses if a cached response is found to be empty or malformed, ensuring data richness.

---

## 9. Limitations & Risks

| Issue | Mitigation |
|-------|------------|
| Wikipedia content varies per neighborhood | Write flexible parsing logic; use LLM to fill gaps; log missing data. |
| Missing/incomplete data | Flag with `#to-validate` (manual process), supplement manually. |
| API/Source Changes (Wikipedia/OpenAI) | Keep code modular, use caching, pin dependencies, and maintain tests. |
| Long-run maintenance | Keep code modular, log parsing issues, automate tests. |
| Licensing of scraped data | Use public domain or Creative Commons sources only; add disclaimers. |

---

## 10. Future Enhancements

- Add YAML front matter to each `.md` file for integration into static site generators (e.g. Jekyll, Hugo).
- Integrate vector search or semantic indexing to make files searchable.
- Build a web interface for previewing profiles.
- Auto-generate visual maps or boundary diagrams via NYC Open Data shapefiles.
- Implement a manual override system for specific data fields.
