import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("nyc_neighborhoods")

class WikipediaParser:
    def parse(self, html_content: str, neighborhood_name: str) -> Dict[str, Any]:
        """
        Parses Wikipedia HTML content to extract the full, cleaned page text.
        This parser is designed to be as simple and robust as possible.
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find the main content area of the page
        parser_output = soup.find('div', class_='mw-parser-output')
        if not parser_output:
            logger.warning(f"[{neighborhood_name}] Could not find main content area ('mw-parser-output').")
            return {"page_text": "", "summary": "", "warnings": ["Could not find main content area."]}

        # Create a deep copy of the parser_output before modifying it
        # This ensures that decompose calls don't affect subsequent text extraction if BeautifulSoup has weird caching
        cleaned_parser_output = BeautifulSoup(str(parser_output), 'html.parser')

        # Pre-clean the HTML by removing noisy elements that are NOT content (e.g., edit links, references)
        for element_class in ["mw-editsection", "reference", "reflist", "portal", "navbox", "thumb", "gallery", "IPA", "sidebar"]:
            for element in cleaned_parser_output.find_all(class_=element_class):
                element.decompose()

        # Extract Summary from the first meaningful paragraph from the CLEANED content
        summary = ""
        first_p = cleaned_parser_output.find('p', recursive=False)
        if first_p:
            # Check if it's the coordinates paragraph (very common first p on Wikipedia)
            if 'coordinates' in first_p.get_text(strip=True).lower() and not first_p.find_next_sibling('p'):
                # If only coordinates paragraph, summary is empty
                summary = ""
            elif 'coordinates' in first_p.get_text(strip=True).lower():
                # If coords paragraph but there's a next one, use the next one as summary
                next_p = first_p.find_next_sibling('p')
                if next_p:
                    summary = next_p.get_text(strip=True)
                else:
                    summary = "" # Fallback if no next paragraph
            else:
                # First paragraph is not coordinates, use it as summary
                summary = first_p.get_text(strip=True)
        
        if not summary:
            logger.warning(f"[{neighborhood_name}] Could not extract short summary.")

        # Extract all remaining text from the cleaned content area
        # Iterate over direct children of cleaned_parser_output to capture all relevant text
        page_text_parts = []
        for child in cleaned_parser_output.children:
            if isinstance(child, Tag): # Ensure it's a tag, not a NavigableString (e.g., whitespace)
                # Only include text from common content-bearing tags, explicitly skipping the first coord p if present
                if child.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'div', 'table', 'li']:
                    text = child.get_text(separator=" ", strip=True)
                    if text:
                        page_text_parts.append(text)
        
        page_text = " ".join(page_text_parts)

        return {
            "summary": summary,
            "page_text": page_text,
            # Empty placeholders to maintain data structure
            "key_details": {}, "around_the_block": "", "neighborhood_facts": {}, 
            "transit_accessibility": {}, "warnings": []
        }
