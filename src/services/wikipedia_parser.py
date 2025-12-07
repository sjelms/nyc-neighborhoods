import logging
import re
from typing import Dict, Any, List
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("nyc_neighborhoods")

class WikipediaParser:
    SUBWAY_LINES = {
        "A", "C", "E", "B", "D", "F", "M", "G", "L", "J", "Z",
        "N", "Q", "R", "W", "1", "2", "3", "4", "5", "6", "7", "S"
    }

    BUS_PATTERN = re.compile(r"\b(?:M|Q|B|Bx|S)\d{1,3}[A-Z]?\b")
    ZIP_PATTERN = re.compile(r"\b\d{5}(?:-\d{4})?\b")

    def parse(self, html_content: str, neighborhood_name: str) -> Dict[str, Any]:
        """
        Parses Wikipedia HTML content to extract structured fields plus a cleaned
        fallback page_text for LLM use.
        """
        soup = BeautifulSoup(html_content, "html.parser")

        parser_output = soup.find("div", class_="mw-parser-output")
        if not parser_output:
            logger.warning(f"[{neighborhood_name}] Could not find main content area ('mw-parser-output').")
            return {
                "summary": "",
                "page_text": "",
                "key_details": {},
                "around_the_block": "",
                "neighborhood_facts": {
                    "population": "",
                    "population_density": "",
                    "area": "",
                    "boundaries": {
                        "east_to_west": "",
                        "north_to_south": "",
                        "adjacent_neighborhoods": []
                    },
                    "zip_codes": []
                },
                "transit_accessibility": {
                    "nearest_subways": [],
                    "major_stations": [],
                    "bus_routes": [],
                    "rail_freight_other": [],
                    "highways_major_roads": []
                },
                "warnings": ["Could not find main content area."],
            }

        cleaned_parser_output = BeautifulSoup(str(parser_output), "html.parser")
        for element_class in [
            "mw-editsection", "reference", "reflist", "portal", "navbox",
            "thumb", "gallery", "IPA", "sidebar"
        ]:
            for element in cleaned_parser_output.find_all(class_=element_class):
                element.decompose()

        summary = self._extract_summary(cleaned_parser_output, neighborhood_name)
        page_text = self._extract_page_text(cleaned_parser_output)

        infobox_data = self._parse_infobox(cleaned_parser_output)
        section_texts = self._collect_section_text(cleaned_parser_output)
        transit_data = self._extract_transit(section_texts)
        boundary_texts = self._extract_boundaries(section_texts)

        neighborhood_facts = {
            "population": infobox_data.get("population", ""),
            "population_density": infobox_data.get("population_density", ""),
            "area": infobox_data.get("area", ""),
            "boundaries": {
                "east_to_west": boundary_texts.get("east_to_west", ""),
                "north_to_south": boundary_texts.get("north_to_south", ""),
                "adjacent_neighborhoods": boundary_texts.get("adjacent_neighborhoods", []),
            },
            "zip_codes": infobox_data.get("zip_codes", []),
        }

        warnings: List[str] = []
        if not neighborhood_facts["population"]:
            warnings.append("Population not found in Wikipedia infobox.")
        if not neighborhood_facts["area"]:
            warnings.append("Area not found in Wikipedia infobox.")
        if not neighborhood_facts["zip_codes"]:
            warnings.append("ZIP codes not found; will rely on LLM inference.")

        around_text = summary
        if not around_text:
            first_two = " ".join(page_text.split(". ")[:2]).strip()
            around_text = first_two

        return {
            "summary": summary,
            "page_text": page_text,
            "key_details": {},
            "around_the_block": around_text,
            "neighborhood_facts": neighborhood_facts,
            "transit_accessibility": transit_data,
            "warnings": warnings,
        }

    def _clean_cell_text(self, node: Tag) -> str:
        return node.get_text(" ", strip=True) if node else ""

    def _parse_infobox(self, soup: BeautifulSoup) -> Dict[str, Any]:
        data: Dict[str, Any] = {"zip_codes": []}
        infobox = soup.find("table", class_=re.compile("infobox"))
        if not infobox:
            return data

        for row in infobox.find_all("tr"):
            header = row.find("th")
            value = row.find("td")
            if not header or not value:
                continue

            header_text = header.get_text(" ", strip=True).lower()
            value_text = self._clean_cell_text(value)

            if "population" in header_text and "density" not in header_text and not data.get("population"):
                number_match = re.search(r"([\d,]{3,})", value_text)
                data["population"] = number_match.group(1) if number_match else value_text
            elif "density" in header_text and not data.get("population_density"):
                density_match = re.search(r"([\d,\.]+)\s*[/\s]*(?:sq|km)", value_text)
                data["population_density"] = density_match.group(1) + " per unit" if density_match else value_text
            elif "area" in header_text and not data.get("area"):
                area_match = re.search(r"([\d,\.]+)\s*(sq mi|sqmi|square mile|mi2|mi²)", value_text, re.IGNORECASE)
                km_match = re.search(r"([\d,\.]+)\s*(km2|km²|square kilometre|square kilometer)", value_text, re.IGNORECASE)
                if area_match:
                    data["area"] = f"{area_match.group(1)} sq mi"
                elif km_match:
                    data["area"] = f"{km_match.group(1)} km²"
                else:
                    data["area"] = value_text
            elif "zip" in header_text or "postal" in header_text:
                zips = self.ZIP_PATTERN.findall(value_text)
                data["zip_codes"] = sorted(set(zips))
        # Secondary ZIP scan from entire infobox text if none found
        if not data["zip_codes"]:
            zips = self.ZIP_PATTERN.findall(infobox.get_text(" ", strip=True))
            data["zip_codes"] = sorted(set(zips))
        return data

    def _extract_summary(self, cleaned_parser_output: BeautifulSoup, neighborhood_name: str) -> str:
        summary = ""
        first_p = cleaned_parser_output.find("p", recursive=False)
        if first_p:
            text = first_p.get_text(strip=True)
            if "coordinates" in text.lower():
                next_p = first_p.find_next_sibling("p")
                summary = next_p.get_text(strip=True) if next_p else ""
            else:
                summary = text

        if not summary:
            logger.warning(f"[{neighborhood_name}] Could not extract short summary.")
        return summary

    def _extract_page_text(self, cleaned_parser_output: BeautifulSoup) -> str:
        page_text_parts = []
        for child in cleaned_parser_output.children:
            if isinstance(child, Tag) and child.name in [
                "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "div", "table", "li"
            ]:
                text = child.get_text(" ", strip=True)
                if text:
                    page_text_parts.append(text)
        return " ".join(page_text_parts)

    def _collect_section_text(self, cleaned_parser_output: BeautifulSoup) -> Dict[str, str]:
        """
        Collects text for key sections we care about (transportation, geography/boundaries).
        """
        sections: Dict[str, str] = {"transport": "", "geography": ""}
        for header in cleaned_parser_output.find_all(["h2", "h3"]):
            title_text = header.get_text(" ", strip=True).lower()
            content_text = []
            for sibling in header.find_next_siblings():
                if sibling.name in ["h2", "h3"]:
                    break
                if isinstance(sibling, Tag):
                    text = sibling.get_text(" ", strip=True)
                    if text:
                        content_text.append(text)
            combined = " ".join(content_text)
            if any(key in title_text for key in ["transport", "transit", "public transportation"]):
                sections["transport"] += " " + combined
            if any(key in title_text for key in ["geography", "boundar", "location"]):
                sections["geography"] += " " + combined
        # Fallback: if no dedicated section, use entire page text in caller
        return sections

    def _extract_transit(self, section_texts: Dict[str, str]) -> Dict[str, List[str]]:
        text = section_texts.get("transport", "")
        nearest_subways: List[str] = []
        bus_routes: List[str] = []
        major_stations: List[str] = []
        highways: List[str] = []

        if text:
            # Subway lines: look for known tokens
            candidates = set(re.findall(r"\b([A-Z0-9]{1,2})\b", text))
            nearest_subways = sorted([c for c in candidates if c in self.SUBWAY_LINES])

            # Bus routes
            bus_routes = sorted(set(self.BUS_PATTERN.findall(text)))

            # Major stations / terminals
            station_matches = re.findall(r"([A-Z][\w\s.-]*(?:Station|Terminal|station|terminal))", text)
            major_stations = sorted(set(s.strip() for s in station_matches))

            # Highways / major roads
            highway_matches = re.findall(
                r"\b(?:I-[0-9]{1,3}|Interstate [0-9]{1,3}|U\.S\. Route [0-9]{1,3}|[A-Z][\w\s-]*(?:Expressway|Parkway|Highway|Boulevard|Avenue|Drive|Road|Street))",
                text
            )
            highways = sorted(set(h.strip() for h in highway_matches))

        return {
            "nearest_subways": nearest_subways,
            "major_stations": major_stations,
            "bus_routes": bus_routes,
            "rail_freight_other": [],
            "highways_major_roads": highways,
        }

    def _extract_boundaries(self, section_texts: Dict[str, str]) -> Dict[str, Any]:
        """
        Simple heuristic: grab sentences mentioning 'bounded by' or 'bordered by'.
        """
        geography_text = section_texts.get("geography", "")
        if not geography_text:
            return {"east_to_west": "", "north_to_south": "", "adjacent_neighborhoods": []}

        sentences = re.split(r"(?<=[.!?])\s+", geography_text)
        bound_sentences = [s for s in sentences if "bounded by" in s.lower() or "bordered by" in s.lower()]

        east_to_west = bound_sentences[0] if bound_sentences else ""
        north_to_south = bound_sentences[1] if len(bound_sentences) > 1 else east_to_west

        neighbors: List[str] = []
        for s in bound_sentences:
            # crude extraction of capitalized words following "by"
            for match in re.findall(r"by\s+([A-Z][\w\s&-]+)", s):
                neighbors.append(match.strip())

        return {
            "east_to_west": east_to_west,
            "north_to_south": north_to_south,
            "adjacent_neighborhoods": sorted(set([n for n in neighbors if n])),
        }
