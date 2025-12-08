import logging
import re
from typing import Dict, Any, List, Optional
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

        parser_outputs = soup.find_all("div", class_="mw-parser-output")
        text_po = None
        infobox_po = None
        if parser_outputs:
            parser_outputs_sorted = sorted(parser_outputs, key=lambda po: len(po.get_text(" ", strip=True)), reverse=True)
            text_po = parser_outputs_sorted[0]
            with_infobox = [po for po in parser_outputs if po.find("table", class_=re.compile("infobox"))]
            infobox_po = with_infobox[0] if with_infobox else text_po

        if not text_po:
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

        cleaned_parser_output = BeautifulSoup(str(text_po), "html.parser")
        for element_class in [
            "mw-editsection", "reference", "reflist", "portal",
            "thumb", "gallery", "IPA", "sidebar"
        ]:
            for element in cleaned_parser_output.find_all(class_=element_class):
                element.decompose()

        summary, secondary_para = self._extract_summary(cleaned_parser_output, neighborhood_name)
        page_text = self._extract_page_text(cleaned_parser_output)

        infobox_data = self._parse_infobox(infobox_po)  # use original to avoid any accidental table removal
        section_texts = self._collect_section_text(cleaned_parser_output)
        transit_data = self._extract_transit(section_texts, fallback_text=page_text)
        boundary_texts = self._extract_boundaries(section_texts, fallback_text=page_text)

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
            "around_the_block": around_text or secondary_para or summary,
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

        current_field: Optional[str] = None

        def set_population(text: str):
            if data.get("population"):
                return
            number_match = re.search(r"([\d,]{3,})", text)
            data["population"] = number_match.group(1) if number_match else text

        def set_density(text: str):
            if data.get("population_density"):
                return
            density_match = re.search(r"([\d,\.]+)\s*[/\\s]*(?:sq|km)", text)
            data["population_density"] = density_match.group(1) if density_match else text

        def set_area(text: str):
            if data.get("area"):
                return
            area_match = re.search(r"([\d,\.]+)\s*(sq mi|sqmi|square mile|mi2|mi²)", text, re.IGNORECASE)
            km_match = re.search(r"([\d,\.]+)\s*(km2|km²|square kilometre|square kilometer)", text, re.IGNORECASE)
            if area_match:
                data["area"] = f"{area_match.group(1)} sq mi"
            elif km_match:
                data["area"] = f"{km_match.group(1)} km²"
            else:
                data["area"] = text

        for row in infobox.find_all("tr"):
            header = row.find("th")
            value = row.find("td")
            header_text = header.get_text(" ", strip=True).lower() if header else ""
            value_text = self._clean_cell_text(value) if value else ""

            # Skip obvious non-targets
            if "area code" in header_text:
                continue

            if "population density" in header_text:
                set_density(value_text)
                current_field = None
                continue

            if "population" in header_text:
                current_field = "population"
                if value_text:
                    set_population(value_text)
                    current_field = None
                continue

            if "area" in header_text:
                current_field = "area"
                if value_text:
                    set_area(value_text)
                    current_field = None
                continue

            if "zip" in header_text or "postal" in header_text:
                zips = self.ZIP_PATTERN.findall(value_text)
                data["zip_codes"] = sorted(set(zips))
                continue

            # Handle sub-rows (e.g., "• Total" under Population)
            if current_field and value_text:
                if current_field == "population":
                    set_population(value_text)
                elif current_field == "area":
                    set_area(value_text)
                current_field = None

        # Secondary ZIP scan from entire infobox text if none found
        if not data["zip_codes"]:
            zips = self.ZIP_PATTERN.findall(infobox.get_text(" ", strip=True))
            data["zip_codes"] = sorted(set(zips))
        return data

    def _extract_summary(self, cleaned_parser_output: BeautifulSoup, neighborhood_name: str) -> (str, str):
        """
        Returns a tuple: (summary, secondary_paragraph_candidate)
        """
        summary = ""
        secondary = ""
        meaningful_paras = []

        for p in cleaned_parser_output.find_all("p"):
            text = p.get_text(" ", strip=True)
            if not text:
                continue
            if "coordinates" in text.lower() and len(text) < 120:
                # Likely the coordinates-only lead paragraph
                continue
            meaningful_paras.append(text)
            if len(meaningful_paras) >= 2:
                break

        if meaningful_paras and len(meaningful_paras) < 2:
            # keep scanning for the next distinct paragraph after the first
            seen_first = meaningful_paras[0]
            for p in cleaned_parser_output.find_all("p"):
                text = p.get_text(" ", strip=True)
                if not text or text == seen_first:
                    continue
                if "coordinates" in text.lower() and len(text) < 120:
                    continue
                meaningful_paras.append(text)
                break

        if meaningful_paras:
            summary = meaningful_paras[0]
            if len(meaningful_paras) > 1:
                secondary = meaningful_paras[1]

        if not summary:
            logger.warning(f"[{neighborhood_name}] Could not extract short summary.")
        return summary, secondary

    def _extract_page_text(self, cleaned_parser_output: BeautifulSoup) -> str:
        page_text_parts = []
        for child in cleaned_parser_output.children:
            if isinstance(child, Tag) and child.name in [
                "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "div", "table", "li"
            ]:
                text = child.get_text(" ", strip=True)
                if text and not (text.lower().startswith("coordinates") and len(text) < 120):
                    page_text_parts.append(text)
        return " ".join(page_text_parts)

    def _collect_section_text(self, cleaned_parser_output: BeautifulSoup) -> Dict[str, str]:
        """
        Collects text for key sections we care about (transportation, geography/boundaries).
        """
        sections: Dict[str, str] = {"transport": "", "geography": ""}
        full_text = cleaned_parser_output.get_text("\n", strip=True)
        full_lower = full_text.lower()

        headings = cleaned_parser_output.find_all("h2")
        heading_positions = []
        for h in headings:
            title = h.get_text(" ", strip=True)
            if not title:
                continue
            pos = full_lower.find(title.lower())
            if pos >= 0:
                heading_positions.append((pos, title))
        heading_positions.sort()

        def slice_section(match_keys: List[str]) -> str:
            start = None
            end = len(full_text)
            for idx, (pos, title) in enumerate(heading_positions):
                if any(k in title.lower() for k in match_keys):
                    start = pos
                    # end at next heading if exists
                    if idx + 1 < len(heading_positions):
                        end = heading_positions[idx + 1][0]
                    break
            if start is None:
                return ""
            return full_text[start:end]

        sections["transport"] = slice_section(["transport", "transit", "public transportation"])
        sections["geography"] = slice_section(["geography", "boundar", "location"])
        return sections

    def _extract_transit(self, section_texts: Dict[str, str], fallback_text: str) -> Dict[str, List[str]]:
        text = section_texts.get("transport", "") or fallback_text
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^A-Za-z0-9\s/,-]", " ", text)  # remove odd zero-width or icon characters
        text = re.sub(r"\s+", " ", text)
        nearest_subways: List[str] = []
        bus_routes: List[str] = []
        major_stations: List[str] = []
        highways: List[str] = []

        if text:
            line_tokens = set()

            # 1) Capture tokens inside parentheses that mention trains/lines
            for m in re.finditer(r"\(([^)]*?)\)", text):
                content = m.group(1)
                if any(k in content.lower() for k in ["train", "line"]):
                    for tok in re.findall(r"\b([A-Z0-9])\b", content):
                        if tok in self.SUBWAY_LINES:
                            line_tokens.add(tok)

            # 2) Capture tokens in snippets near train/subway keywords
            for m in re.finditer(r"(?:train|trains|subway|line|lines)[^.]{0,80}", text, flags=re.IGNORECASE):
                snippet = m.group(0)
                for tok in re.findall(r"\b([A-Z0-9])\b", snippet):
                    if tok in self.SUBWAY_LINES:
                        line_tokens.add(tok)

            # 3) Fallback: any standalone tokens in the transport text that match known lines
            if not line_tokens:
                for tok in re.findall(r"\b([A-Z0-9])\b", text):
                    if tok in self.SUBWAY_LINES:
                        line_tokens.add(tok)

            nearest_subways = sorted(line_tokens)

            # Bus routes
            bus_routes = sorted(set(self.BUS_PATTERN.findall(text)))

            # Major stations / terminals
            station_matches = re.findall(
                r"\b([A-Za-z0-9][\w'&.-]*(?:\s+[A-Za-z0-9][\w'&.-]*){0,5}\s+(?:Station|Terminal))\b",
                text,
                flags=re.IGNORECASE
            )
            cleaned_stations: List[str] = []
            for s in station_matches:
                words = s.split()
                idx = next((i for i, w in enumerate(words) if w.lower().startswith("station") or w.lower().startswith("terminal")), None)
                if idx is None:
                    cleaned_stations.append(s.strip())
                else:
                    start = max(0, idx - 2)
                    cleaned_stations.append(" ".join(words[start:idx + 1]))
            major_stations = sorted(set(cleaned_stations))

            # Highways / major roads
            highway_matches = re.findall(
                r"\b(?:I-[0-9]{1,3}|Interstate [0-9]{1,3}|U\.S\. Route [0-9]{1,3}|"
                r"(?:[A-Z][\w'&.-]*\s+){0,2}[A-Z][\w'&.-]*\s+(?:Expressway|Parkway|Highway|Boulevard|Avenue|Drive|Road|Street))\b",
                text
            )
            highways = []
            for h in highway_matches:
                cleaned = h.strip()
                if "train" in cleaned.lower():
                    continue
                highways.append(cleaned)
            highways = sorted(set(highways))

        return {
            "nearest_subways": nearest_subways,
            "major_stations": major_stations,
            "bus_routes": bus_routes,
            "rail_freight_other": [],
            "highways_major_roads": highways,
        }

    def _extract_boundaries(self, section_texts: Dict[str, str], fallback_text: str) -> Dict[str, Any]:
        """
        Simple heuristic: grab sentences mentioning 'bounded by' or 'bordered by'.
        """
        geography_text = section_texts.get("geography", "") or fallback_text
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
