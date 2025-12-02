# Quickstart: Automated Neighborhood Profile Generator

**Date**: 2025-12-02

This guide provides a quick overview to get started with the Automated Neighborhood Profile Generator.

## 1. Prerequisites

*   Python 3.8+
*   `pip` (Python package installer)

## 2. Setup

### 2.1. Clone the repository

```bash
git clone <repository_url>
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

### 3.1. Prepare Input Data

Ensure you have a CSV file (e.g., `neighborhood-borough.csv`) with `Neighborhood` and `Borough` columns, specifying the neighborhoods you want to generate profiles for.

### 3.2. Run the Generator

Once the tool is implemented, you will be able to run it from the command line, likely with an interface similar to:

```bash
python -m src.main generate-profiles --input-csv neighborhood-borough.csv --output-dir ./output --version 1.0 --ratified 2025-12-02 --last-amended 2025-12-02
```

*(Note: The exact command and arguments may vary as development progresses.)*

## 4. Expected Output

The tool will generate Markdown files for each neighborhood in the specified output directory (e.g., `./output/Maspeth_Queens.md`).

## 5. Development

For development and testing, refer to `CONTRIBUTING.md` (if available) and the project's `README.md`.
