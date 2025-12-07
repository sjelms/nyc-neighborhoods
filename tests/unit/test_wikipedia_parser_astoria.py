import json
from pathlib import Path

from src.services.wikipedia_parser import WikipediaParser


def _load_cached_astoria_html() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    cache_path = repo_root / "cache/html/9bbcb6b6c18e86476af39c9f34bd6830.html"
    cache_entry = json.loads(cache_path.read_text())
    return cache_entry["content"]


def test_parser_extracts_infobox_and_transit_from_astoria_cache():
    html = _load_cached_astoria_html()
    parser = WikipediaParser()

    parsed = parser.parse(html, "Astoria")

    nf = parsed["neighborhood_facts"]
    transit = parsed["transit_accessibility"]

    assert parsed["summary"], "Summary should be populated from the lead paragraph."
    assert parsed["around_the_block"], "Around the Block should fall back to summary or lead text."
    assert nf["population"], "Population should be extracted from the infobox."
    assert nf["area"], "Area should be extracted from the infobox."
    assert nf["zip_codes"], "ZIP codes should be extracted from the infobox."
    assert transit["nearest_subways"], "Subway lines should be extracted from transport text."
    assert transit["bus_routes"], "Bus routes should be extracted from transport text."
