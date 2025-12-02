# Quickstart: Automated Neighborhood Profile Generator

**Date**: 2025-12-02

This guide provides a quick overview to get started with the Automated Neighborhood Profile Generator.

## 1. Prerequisites

*   Python 3.8+
*   `pip` (Python package installer)

## 2. Setup

### 2.1. Clone the repository

```bash
git clone https://github.com/your-username/nyc-neighborhoods.git
cd nyc-neighborhoods
```

### 2.2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2.3. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Usage

The primary way to use this tool is via its command-line interface (CLI).

```bash
python -m src.cli.main generate-profiles [OPTIONS]
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
*   `--odid, --nyc-open-data-dataset-id <TEXT>`: ID of the NYC Open Data Socrata dataset to use for supplementary data (e.g., `ntacode_dataset_placeholder`). If not provided, Open Data will not be used.

### Example:

```bash
python -m src.cli.main generate-profiles \
  --input-csv /path/to/your/neighborhoods.csv \
  --output-dir ./generated_profiles \
  --template-path ./output-template.md \
  --version "1.0" \
  --ratified-date "2025-12-01" \
  --last-amended-date "2025-12-02" \
  --log-level "INFO" \
  --cache-dir "./my_cache" \
  --cache-expiry-days 30 \
  --nyc-open-data-dataset-id "ntacode_dataset_placeholder"
```

## 4. Expected Output

The tool will generate Markdown files for each neighborhood in the specified output directory (e.g., `./output/Maspeth_Queens.md`).

## 5. Development

For development and testing, refer to the `README.md` and the `tasks.md` and other documentation in this directory (`specs/001-automated-neighborhood-profile-generator/`).
