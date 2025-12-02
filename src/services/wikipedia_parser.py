import logging
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup, Tag
import re

logger = logging.getLogger("nyc_neighborhoods")

class WikipediaParser:
    def parse(self, html_content: str, neighborhood_name: str) -> Dict[str, Any]:
        """
        Parses Wikipedia HTML content to extract neighborhood information.

        Args:
            html_content: The HTML content of the Wikipedia page.
            neighborhood_name: The name of the neighborhood (for context in logging).

        Returns:
            A dictionary containing extracted data.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        data: Dict[str, Any] = {
            "summary": "",
            "key_details": { # Placeholder for now, Wikipedia doesn't have these directly
                "what_to_expect": "",
                "unexpected_appeal": "",
                "the_market": ""
            },
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
            "commute_times": None, # Not typically found on Wikipedia infoboxes
            "sources": [], # To be filled by WebFetcher or external tracking
            "warnings": []
        }

        # Extract Short Summary Paragraph
        # Look for the first few paragraphs after the main title
        summary_paragraphs = []
        # Find the main content div, typically 'mw-parser-output'
        parser_output = soup.find('div', class_='mw-parser-output')
        if parser_output:
            for p in parser_output.find_all('p', recursive=False): # Only direct children of content
                if not p.get_text(strip=True).startswith('Coordinates:') and not p.find('span', class_='coordinates'):
                    summary_paragraphs.append(p.get_text(strip=True))
                    if len(" ".join(summary_paragraphs).split()) >= 50: # Roughly 2-3 sentences
                        break
        data["summary"] = " ".join(summary_paragraphs[:3]) # Take up to first 3 paragraphs

        if not data["summary"]:
            logger.warning(f"[{neighborhood_name}] Could not extract short summary.")
            data["warnings"].append("Could not extract short summary from Wikipedia.")

        # Extract Infobox data
        infobox = soup.find('table', class_='infobox geography vcard')
        if infobox:
            infobox_data = self._parse_infobox(infobox)
            
            # Population
            data["neighborhood_facts"]["population"] = infobox_data.get("Population", "")
            if not data["neighborhood_facts"]["population"]:
                logger.warning(f"[{neighborhood_name}] Could not extract population from infobox.")
                data["warnings"].append("Could not extract population from Wikipedia infobox.")

            # Area
            area_data = infobox_data.get("Area", {})
            if isinstance(area_data, dict):
                area_raw = area_data.get("Total", "")
            else:
                area_raw = area_data
            if isinstance(area_raw, list):
                area_raw = area_raw[0] if area_raw else ""
            data["neighborhood_facts"]["area"] = area_raw
            if not data["neighborhood_facts"]["area"]:
                logger.warning(f"[{neighborhood_name}] Could not extract area from infobox.")
                data["warnings"].append("Could not extract area from Wikipedia infobox.")
            
            # Population Density (often calculated or missing)
            data["neighborhood_facts"]["population_density"] = infobox_data.get("Density", "")
            if not data["neighborhood_facts"]["population_density"]:
                logger.warning(f"[{neighborhood_name}] Could not extract population density from infobox.")
                data["warnings"].append("Could not extract population density from Wikipedia infobox.")

            # ZIP Codes (often under 'Postal code' or similar)
            zip_codes_raw = infobox_data.get("Postal code", infobox_data.get("ZIP Code", infobox_data.get("ZIP codes", [])))
            if isinstance(zip_codes_raw, str):
                data["neighborhood_facts"]["zip_codes"] = [zc.strip() for zc in zip_codes_raw.split(',') if zc.strip()]
            elif isinstance(zip_codes_raw, list):
                data["neighborhood_facts"]["zip_codes"] = [zc.strip() for zc in zip_codes_raw if zc.strip()]
            
            if not data["neighborhood_facts"]["zip_codes"]:
                logger.warning(f"[{neighborhood_name}] Could not extract ZIP codes from infobox.")
                data["warnings"].append("Could not extract ZIP codes from Wikipedia infobox.")
            
            # Highways might be in infobox
            highways_raw = infobox_data.get("Highways", infobox_data.get("Major roads", []))
            if isinstance(highways_raw, str):
                data["transit_accessibility"]["highways_major_roads"].extend([h.strip() for h in highways_raw.split(',') if h.strip()])
            elif isinstance(highways_raw, list):
                data["transit_accessibility"]["highways_major_roads"].extend([h.strip() for h in highways_raw if h.strip()])


        else:
            logger.warning(f"[{neighborhood_name}] Infobox not found.")
            data["warnings"].append("Could not find infobox on Wikipedia page.")

        # Placeholder for "Around the Block" - often needs more sophisticated extraction
        # For now, we'll try to get content from a "History" or "Culture" section if available
        around_the_block_content = []
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if any(text in heading.get_text(strip=True).lower() for text in ['history', 'culture', 'description']):
                for sibling in heading.find_next_siblings(['p']):
                    text = sibling.get_text(strip=True)
                    if text and not text.startswith('Coordinates:') and not text.startswith('This article is about'):
                        around_the_block_content.append(text)
                        if len(" ".join(around_the_block_content).split()) >= 100: # Roughly 2 paragraphs
                            break
            if around_the_block_content:
                break
        data["around_the_block"] = " ".join(around_the_block_content[:2]) # Take up to first 2 paragraphs

        if not data["around_the_block"]:
            logger.warning(f"[{neighborhood_name}] Could not extract 'Around the Block' narrative.")
            data["warnings"].append("Could not extract 'Around the Block' narrative from Wikipedia.")

        # Extract Transit information (highly variable, best effort)
        # Look for sections like "Transportation", "Transit", "Infrastructure"
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if 'transportation' in heading.get_text(strip=True).lower() or 'transit' in heading.get_text(strip=True).lower():
                section_content = []
                for sibling in heading.find_next_siblings():
                    if sibling.name and sibling.name.startswith('h') and sibling.name <= heading.name:
                        break # Stop at next major heading
                    if sibling.name == 'p':
                        section_content.append(sibling.get_text(strip=True))
                    elif sibling.name == 'ul' or sibling.name == 'ol':
                        for li in sibling.find_all('li'):
                            section_content.append(li.get_text(strip=True))

                transit_text = " ".join(section_content).lower()

                # Simple keyword matching for transit types
                # These helpers will now look for lists and general mentions in the section
                data["transit_accessibility"]["nearest_subways"].extend(self._extract_transit_items(soup, 'Subway', heading))
                data["transit_accessibility"]["major_stations"].extend(self._extract_transit_items(soup, 'Station', heading))
                data["transit_accessibility"]["bus_routes"].extend(self._extract_transit_items(soup, 'Bus', heading))
                data["transit_accessibility"]["rail_freight_other"].extend(self._extract_transit_items(soup, 'Rail', heading))
                # Highways are handled by infobox first, then secondary text scan if not found
                if not data["transit_accessibility"]["highways_major_roads"]:
                    data["transit_accessibility"]["highways_major_roads"].extend(self._extract_transit_items(soup, 'Highway', heading))

                # Deduplicate and clean
                for key in ["nearest_subways", "major_stations", "bus_routes", "rail_freight_other", "highways_major_roads"]:
                    data["transit_accessibility"][key] = list(set([item.strip() for item in data["transit_accessibility"].get(key, []) if item.strip()]))
                
                if not any(data["transit_accessibility"].values()):
                    logger.warning(f"[{neighborhood_name}] Could not extract detailed transit info, but found transportation section.")
                    data["warnings"].append("Could not extract detailed transit info from Wikipedia.")
                break # Stop after first transportation section

        if not any(data["transit_accessibility"].values()):
            logger.warning(f"[{neighborhood_name}] Could not find transit information section.")
            data["warnings"].append("Could not find transit information section on Wikipedia page.")


        # Boundaries are very hard to parse generally from text. Will leave as placeholders or try to extract from infobox
        # For now, leave these empty as direct text parsing is too ambiguous without specific patterns.
        # Infobox might have "Area" and "Coordinates" but not "East to West" etc.
        data["neighborhood_facts"]["boundaries"]["east_to_west"] = "" # NEEDS MANUAL REVIEW/SOPHISTICATION
        data["neighborhood_facts"]["boundaries"]["north_to_south"] = "" # NEEDS MANUAL REVIEW/SOPHISTICATION
        
        # Adjacent neighborhoods are also hard to parse reliably.
        data["neighborhood_facts"]["boundaries"]["adjacent_neighborhoods"] = self._extract_adjacent_neighborhoods(soup)
        if not data["neighborhood_facts"]["boundaries"]["adjacent_neighborhoods"]:
            logger.warning(f"[{neighborhood_name}] Could not extract adjacent neighborhoods.")
            data["warnings"].append("Could not extract adjacent neighborhoods from Wikipedia.")


        # Key Details fields are abstract and won't be directly found on Wikipedia
        # These would likely need to be generated or summarized from other data after parsing.
        data["key_details"]["what_to_expect"] = "" # NEEDS POST-PROCESSING
        data["key_details"]["unexpected_appeal"] = "" # NEEDS POST-PROCESSING
        data["key_details"]["the_market"] = "" # NEEDS POST-PROCESSING

        return data

    def _parse_infobox(self, infobox: Tag) -> Dict[str, Any]:
        """Helper to parse a Wikipedia infobox table."""
        infobox_data: Dict[str, Any] = {}
        for row in infobox.find_all('tr'):
            header = row.find('th')
            value_cell = row.find('td')
            if header and value_cell:
                key = header.get_text(strip=True).replace('\n', ' ')
                value = self._clean_infobox_value(value_cell)
                infobox_data[key] = value
        return infobox_data

    def _clean_infobox_value(self, cell: Tag) -> Any:
        """Cleans and extracts text from an infobox cell, handling lists and nested tags."""
        # Remove sup tags (citations)
        for sup in cell.find_all('sup'):
            sup.decompose()
        
        # Handle lists within cells
        list_items = [li.get_text(strip=True) for li in cell.find_all(['li', 'div'], recursive=False) if li.get_text(strip=True)]
        if list_items:
            return list_items
        
        # Try to get text from links if relevant (e.g., for 'Area' which might link to units)
        links = [a.get_text(strip=True) for a in cell.find_all('a') if a.get_text(strip=True)]
        if links and len(" ".join(links)) > len(cell.get_text(strip=True)) / 2: # Heuristic: if links cover most of the text
            return links # Return all linked items as a list
        
        # Fallback to direct text
        text = cell.get_text(separator=' ', strip=True)
        # Clean up common infobox patterns like " • " list separators or multiple values separated by newlines
        text = text.replace(' • ', ', ').replace('\n', ', ').replace(' , ', ', ')
        return text.strip()

    def _extract_transit_items(self, soup: BeautifulSoup, keyword: str, section_heading: Optional[Tag] = None) -> List[str]:
        """
        Extracts transit items (e.g., subway lines, bus routes) based on keywords within a given section.
        """
        items = []
        search_scope = section_heading.find_next_siblings() if section_heading else soup.find_all(['p', 'ul', 'ol'])
        
        for sibling in search_scope:
            if sibling.name and sibling.name.startswith('h') and section_heading and sibling.name <= section_heading.name:
                break # Stop at next major heading
            
            if sibling.name == 'p':
                # Look for patterns like "served by the 1, 2, 3 subway lines"
                matches = re.findall(rf'\b(?:{keyword}|line|route)[s]?\s(?:[A-Z0-9&/-]+(?:,\s*)?)+\b', sibling.get_text(), re.IGNORECASE)
                for match in matches:
                    # Extract just the codes/names
                    codes = re.findall(r'[A-Z0-9&/-]+', match)
                    items.extend(codes)
            elif sibling.name in ['ul', 'ol']:
                for li in sibling.find_all('li'):
                    text = li.get_text(strip=True)
                    if keyword.lower() in text.lower() or any(k in text.lower() for k in ['train', 'station', 'bus', 'highway', 'road']):
                        # Heuristic: try to get the most relevant part, or the whole item
                        match = re.search(r'(\b[A-Z0-9&/-]+\b(?:.*?line)?(?:.*?route)?)', text, re.IGNORECASE)
                        if match:
                            items.append(match.group(1).replace('line', '').replace('route', '').strip())
                        else:
                            items.append(text)
            
        return list(set([item.replace('•','').strip() for item in items if item.strip() and len(item) > 1])) # Deduplicate and clean


    def _extract_adjacent_neighborhoods(self, soup: BeautifulSoup) -> List[str]:
        """
        A highly experimental and basic method to extract adjacent neighborhoods,
        as this is very inconsistent on Wikipedia pages.
        """
        adjacent = []
        # Common patterns: "Bordered by X, Y, and Z" or lists under a "Geography" section
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            if 'geography' in heading.get_text(strip=True).lower() or 'borders' in heading.get_text(strip=True).lower():
                for sibling in heading.find_next_siblings(['p', 'ul', 'ol']):
                    if sibling.name and sibling.name.startswith('h') and sibling.name <= heading.name:
                        break # Stop at next major heading
                    text = sibling.get_text(strip=True)
                    # Look for "bordered by" pattern
                    match = re.search(r'bordered by (.*?)(?:\.|;|,$|$)', text, re.IGNORECASE)
                    if match:
                        parts = re.split(r', and |,? and |,|;', match.group(1))
                        adjacent.extend([p.strip() for p in parts if p.strip()])
                    # Look for lists of places (might be too broad)
                    if sibling.name in ['ul', 'ol']:
                        for li in sibling.find_all('li'):
                            # Heuristic: if list item looks like a place name (e.g., capitalized words)
                            if len(li.get_text().split()) <= 3 and li.get_text().istitle():
                                adjacent.append(li.get_text(strip=True))

        # Filter out self-reference or very short words that are not neighborhoods
        return list(set([n for n in adjacent if len(n.split()) > 1 or (len(n) > 2 and n.istitle())]))


if __name__ == '__main__':
    from src.lib.logger import setup_logging
    setup_logging(level=logging.INFO)

    # Example HTML (simplified structure for demonstration)
    # A real Wikipedia page would be much more complex.
    html_content = """
    <div class="mw-parser-output">
        <p><b>Coordinates:</b> 40°45′14″N 73°54′54″W</p>
        <p>This is the first paragraph of the summary. It talks about the neighborhood's general characteristics and location.</p>
        <p>This is the second paragraph of the summary, providing more details about its history and culture. It is quite a long paragraph to test summary extraction.</p>
        <p>This is a third paragraph. It might contain additional information.</p>
        <table class="infobox geography vcard">
            <tbody>
                <tr><th scope="row">Population</th><td>100,000 (2020)</td></tr>
                <tr><th scope="row">Density</th><td>10,000/sq mi</td></tr>
                <tr><th scope="row">Area</th><td><div><a href="/wiki/Square_mile" title="Square mile">5 sq mi</a></div></td></tr>
                <tr><th scope="row">ZIP Code</th><td><ul><li>10001</li><li>10002</li></ul></td></tr>
                <tr><th scope="row">Adjacent</th><td><div class="plainlist"><ul><li>Neighbor A</li><li>Neighbor B</li></ul></div></td></tr>
                <tr><th scope="row">Highways</th><td>I-95</td></tr>
            </tbody>
        </table>
        <h2>History</h2>
        <p>The neighborhood has a rich history, dating back to colonial times. It was settled by Dutch immigrants.</p>
        <p>Later, it became an industrial hub and attracted various immigrant groups.</p>
        <h2>Transportation</h2>
        <p>The area is well-served by public transit, including several subway lines.</p>
        <ul>
            <li><a href="/wiki/B_train_(New_York_City_Subway)" title="B train (New York City Subway)">B</a>, <a href="/wiki/D_train_(New_York_City_Subway)" title="D train (New York City Subway)">D</a> trains</li>
            <li><a href="/wiki/4_train_(New_York_City_Subway)" title="4 train (New York City Subway)">4</a>, <a href="/wiki/5_train_(New_York_City_Subway)" title="5 train (New York City Subway)">5</a> trains</li>
            <li>M15, M42 bus routes</li>
        </ul>
        <h3>Major Stations</h3>
        <p>Grand Central Station, Penn Station</p>
        <h4>Bus Routes</h4>
        <p>Several MTA local and express bus routes serve the neighborhood, including the Bx1, Bx2, and Bx3.</p>
        <h4>Rail and Freight</h4>
        <p>LIRR has a station here. Freight rail also passes through.</p>
        <h2>Geography</h2>
        <p>The neighborhood is bordered by Neighbor C to the North, and Neighbor D to the South.</p>
    </div>
    """
    parser = WikipediaParser()
    extracted_data = parser.parse(html_content, "Test Neighborhood")
    
    print("\n--- Extracted Data ---")
    for key, value in extracted_data.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for sub_key, sub_value in value.items():
                print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")

    # Test case for no infobox
    html_no_infobox = """
    <div class="mw-parser-output">
        <p>This is a summary without an infobox.</p>
    </div>
    """
    extracted_no_infobox = parser.parse(html_no_infobox, "No Infobox Test")
    print("\n--- Extracted Data (No Infobox) ---")
    print(extracted_no_infobox["summary"])
    print(extracted_no_infobox["warnings"])

    # Test case for no summary
    html_no_summary = """
    <div class="mw-parser-output">
        <table class="infobox geography vcard"></table>
        <h2>Transportation</h2>
        <p>Bus routes only</p>
    </div>
    """
    extracted_no_summary = parser.parse(html_no_summary, "No Summary Test")
    print("\n--- Extracted Data (No Summary) ---")
    print(extracted_no_summary["summary"])
    print(extracted_no_summary["warnings"])
