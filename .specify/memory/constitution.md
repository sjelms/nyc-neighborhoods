<!--
<div id="sync-impact-report">
Version change: None (initial creation)
Modified principles: All (initial creation)
Added sections: Project Scope & Limitations, Development Workflow (initial creation)
Removed sections: None
Templates requiring updates:
  - .specify/templates/plan-template.md: ⚠ pending (Constitution Check section needs to reference new principles)
  - .specify/templates/spec-template.md: ⚠ pending (Requirements and Acceptance Scenarios should implicitly align with principles like Data Accuracy, Standardized Output)
  - .specify/templates/tasks-template.md: ⚠ pending (Task categorization and testing tasks should reflect new principles like Verification & Robustness, Data Accuracy)
  - .gemini/commands/*.toml: ✅ updated (No direct textual changes needed, but their generated output/guidance should align)
  - README.md: ✅ updated (No direct textual changes needed, content aligns with project scope)
Follow-up TODOs: None
</div>
-->
# Automated Neighborhood Profile Generator Constitution

## Core Principles

### I. Data Accuracy & Traceability
Prioritize data accuracy and source traceability by preferring high-authority sources (Wikipedia, official NYC Open Data). Cross-validate facts, and for conflicting data, prefer official sources. Flag inconsistencies for manual review.

### II. Standardized Output
Produce standalone Markdown files per neighborhood with a fixed template, including metadata (Version, Ratified Date, Last Amended Date). Follow `Neighborhood_Borough.md` naming convention. Maintain a companion log for generation details and warnings.

### III. Python-First Development
All core development must utilize Python 3.x. Adhere to the preferred stack: `requests`, `BeautifulSoup`, `pandas`, `pydantic` (or `dataclasses`), `typer` or `argparse`. Maintain a modular component architecture.

### IV. Verification & Robustness
Implement comprehensive testing and debugging for all components. Start with a subset of neighborhoods for verification. Verify formatting, structure, and data accuracy. Handle missing/malformed sections with warnings and flag any missing or ambiguous values.

### V. Extensibility & Maintainability
Design the system to be maintainable, extensible, and easy to review/update. Implement flexible parsing logic and fallback rules for varying data sources. Add inline flags (e.g., `#reference-required`, `#to-validate`) for missing or unverified data.

## Project Scope & Limitations

### Limitations & Risks
- **Wikipedia content varies per neighborhood**: Write flexible parsing logic and fallback rules.
- **Missing/incomplete data**: Flag with `#to-validate`, supplement manually.
- **Open Data APIs may change structure or be incomplete**: Use caching, stable endpoints, or file downloads.
- **Long-run maintenance**: Keep code modular, log parsing issues, automate tests.
- **Licensing of scraped data**: Use public domain or Creative Commons sources only.

### Future Enhancements
- Add YAML front matter to each `.md` file for integration into static site generators (e.g., Jekyll, Hugo).
- Integrate vector search or semantic indexing to make files searchable.
- Build a web interface for previewing profiles.
- Auto-generate visual maps or boundary diagrams via NYC Open Data shapefiles.

## Development Workflow

1.  **Project setup**: Create folders: `/input`, `/output`, `/logs`, `/cache`. Install dependencies via `pip`.
2.  **CSV Importer**: Load `neighborhood_name` and `borough` columns. Handle duplicates or missing values.
3.  **Page Fetcher**: Build Wikipedia URL from name. Fallback: Open Data API (if available).
4.  **HTML Parser**: Extract infobox items (population, ZIPs, area, etc.). Scrape transit, boundary, and zoning info. Handle missing/malformed sections with warnings.
5.  **Data Schema**: Define `NeighborhoodProfile` model (Pydantic or plain class). Populate fields with parsed data.
6.  **Template Renderer**: Inject values into Markdown template with correct formatting. Add version metadata at top.
7.  **File Output**: Save as `Neighborhood_Borough.md` in `/output`. Append a log entry for each record (CSV or JSON).
8.  **CLI Interface (optional)**: Allow version, ratified, amended dates to be passed as flags.
9.  **Testing / Debugging**: Start with ~3 neighborhoods (e.g., Williamsburg, Maspeth, Sunset Park). Verify: formatting, structure, key data filled in. Log any missing or ambiguous values.
10. **Refinement**: Add fallback options for unreliable sources. Add inline flags for `#reference-required` or `#to-validate` for missing data.

## Governance
This Constitution supersedes all other project practices. Amendments require a documented rationale, approval from project leads, and a migration plan if applicable. All code reviews must verify compliance with these principles. Versioning of outputs and the Constitution itself must adhere to semantic versioning guidelines outlined below.

**Version**: 1.0.0 | **Ratified**: 2025-12-02 | **Last Amended**: 2025-12-02