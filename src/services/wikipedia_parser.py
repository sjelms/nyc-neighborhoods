import logging
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup, Tag
import re

logger = logging.getLogger("nyc_neighborhoods")

class WikipediaParser:
    def parse(self, html_content: str, neighborhood_name: str, summary_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Parses Wikipedia HTML content to extract neighborhood information.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for edit_section in soup.find_all("span", class_="mw-editsection"):
            edit_section.decompose()

        data: Dict[str, Any] = {
            "summary": "",
            "key_details": {},
            "around_the_block": "",
            "neighborhood_facts": {
                "population": "", "population_density": "", "area": "",
                "boundaries": {"east_to_west": "", "north_to_south": "", "adjacent_neighborhoods": []},
                "zip_codes": []
            },
            "transit_accessibility": {
                "nearest_subways": [], "major_stations": [], "bus_routes": [],
                "rail_freight_other": [], "highways_major_roads": []
            },
            "commute_times": None, "sources": [], "warnings": []
        }

        # Summary
        parser_output = soup.find('div', class_='mw-parser-output')
        if parser_output:
            summary_paragraphs = []
            for p in parser_output.find_all('p', recursive=False)[:5]:
                text = p.get_text(strip=True)
                if not text or text.startswith('Coordinates:'): continue
                summary_paragraphs.append(text)
                if len(summary_paragraphs) >= 2: break
            data["summary"] = " ".join(summary_paragraphs)
        
        if summary_override and not data["summary"]:
            data["summary"] = summary_override.strip()
        if not data["summary"]:
            logger.warning(f"[{neighborhood_name}] Could not extract short summary.")
            data["warnings"].append("Could not extract short summary.")

        # Infobox
        infobox = soup.find('table', class_=lambda c: c and 'infobox' in c)
        if infobox:
            infobox_data = self._parse_infobox(infobox)
            def _first_value(prefix: str):
                for k, v in infobox_data.items():
                    if k.lower().startswith(prefix.lower()): return v
                return ""
            data["neighborhood_facts"]["population"] = _first_value("Population")
            area_raw = _first_value("Area")
            data["neighborhood_facts"]["area"] = area_raw[0] if isinstance(area_raw, list) else area_raw
            data["neighborhood_facts"]["population_density"] = _first_value("Density")
            zip_codes_raw = ""
            for k, v in infobox_data.items():
                if any(lbl in k.lower() for lbl in ["zip", "postal"]):
                    zip_codes_raw = v
                    break
            if isinstance(zip_codes_raw, str):
                data["neighborhood_facts"]["zip_codes"] = [zc.strip() for zc in re.split(r'[,\s]+', zip_codes_raw) if zc.strip()]
            elif isinstance(zip_codes_raw, list):
                data["neighborhood_facts"]["zip_codes"] = [zc.strip() for zc in zip_codes_raw if zc.strip()]
        else:
            logger.warning(f"[{neighborhood_name}] Infobox not found.")
            data["warnings"].append("Could not find infobox.")

        # Adjacent Neighborhoods
        data["neighborhood_facts"]["boundaries"]["adjacent_neighborhoods"] = self._extract_adjacent_neighborhoods(soup, infobox)
        if not data["neighborhood_facts"]["boundaries"]["adjacent_neighborhoods"]:
            logger.warning(f"[{neighborhood_name}] Could not extract adjacent neighborhoods.")
            data["warnings"].append("Could not extract adjacent neighborhoods.")

        # Transportation Text for LLM
        transportation_keywords = ['transportation', 'transit', 'transport', 'infrastructure', 'public transport']
        data["transportation_text"] = self._get_section_text(soup, transportation_keywords)
        if not data["transportation_text"]:
            logger.warning(f"[{neighborhood_name}] Could not find 'Transportation' section text.")
            data["warnings"].append("Could not find 'Transportation' section text.")

        return data

    def _get_section_text(self, soup: BeautifulSoup, section_keywords: List[str]) -> str:
        section_heading = None
        # Search for the heading in h2, h3, h4 tags
        for heading_level in ['h2', 'h3', 'h4']:
            for heading in soup.find_all(heading_level):
                heading_text = heading.get_text(strip=True).lower()
                if any(keyword in heading_text for keyword in section_keywords):
                    section_heading = heading
                    break
            if section_heading:
                break
        
        if not section_heading:
            return ""

        content = []
        for sibling in section_heading.find_next_siblings():
            # Stop if we hit the next heading of the same or higher level
            if sibling.name and sibling.name.startswith('h') and sibling.name <= section_heading.name:
                break
            content.append(sibling.get_text(separator=" ", strip=True))
        
        return " ".join(content)

    def _parse_infobox(self, infobox: Tag) -> Dict[str, Any]:
        infobox_data: Dict[str, Any] = {}
        for row in infobox.find_all('tr'):
            header = row.find('th')
            value_cell = row.find('td')
            if header and value_cell:
                infobox_data[header.get_text(strip=True)] = self._clean_infobox_value(value_cell)
        return infobox_data

    def _clean_infobox_value(self, cell: Tag) -> Any:
        for sup in cell.find_all('sup'): sup.decompose()
        list_items = [li.get_text(strip=True) for li in cell.find_all('li')]
        if list_items: return [item.replace('\xa0', ' ') for item in list_items]
        return cell.get_text(separator=' ', strip=True).replace('\xa0', ' ')

    def _extract_adjacent_neighborhoods(self, soup: BeautifulSoup, infobox: Optional[Tag]) -> List[str]:
        adjacent = []
        if infobox:
            for row in infobox.find_all('tr'):
                header = row.find('th')
                if header and 'adjacent' in header.get_text(strip=True).lower():
                    value_cell = row.find('td')
                    if value_cell:
                        neighbors = self._clean_infobox_value(value_cell)
                        if isinstance(neighbors, list):
                            adjacent.extend(neighbors)
                        elif isinstance(neighbors, str):
                            adjacent.extend(re.split(r', | and ', neighbors))
                        break
        
        if not adjacent:
            parser_output = soup.find('div', class_='mw-parser-output')
            if parser_output:
                first_p = parser_output.find('p', recursive=False)
                if first_p:
                    match = re.search(r'(?:bounded by|adjacent to) (.*?)(?:\.|;|$)', first_p.get_text(strip=True), re.IGNORECASE)
                    if match:
                        parts = re.split(r', and |,? and |,|;', match.group(1))
                        adjacent.extend([p.strip() for p in parts if p.strip() and len(p.split()) < 4])

        cleaned = []
        for item in adjacent:
            item_cleaned = re.sub(r'\s*\([^)]*\)', '', item).strip()
            if item_cleaned:
                cleaned.extend(re.split(r', | and ', item_cleaned))
        
        return sorted(list(set([n.strip() for n in cleaned if n.strip() and len(n.split()) < 4 and n.lower() != 'new york city'])))