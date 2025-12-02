import pytest
import pandas as pd
from pathlib import Path
from src.lib.csv_parser import CSVParser

@pytest.fixture
def temp_csv_file(tmp_path: Path):
    """Fixture to create a temporary CSV file for testing."""
    def _create_csv(content: str, filename: str = "test.csv"):
        file_path = tmp_path / filename
        file_path.write_text(content)
        return file_path
    return _create_csv

class TestCSVParser:
    def test_parse_valid_csv(self, temp_csv_file):
        content = """Neighborhood,Borough
Maspeth,Queens
Williamsburg,Brooklyn
"""
        file_path = temp_csv_file(content)
        parser = CSVParser(file_path)
        result = parser.parse()
        assert len(result) == 2
        assert result[0] == {"Neighborhood": "Maspeth", "Borough": "Queens"}
        assert result[1] == {"Neighborhood": "Williamsburg", "Borough": "Brooklyn"}

    def test_parse_csv_with_duplicates(self, temp_csv_file, capsys):
        content = """Neighborhood,Borough
Maspeth,Queens
Williamsburg,Brooklyn
Maspeth,Queens
"""
        file_path = temp_csv_file(content)
        parser = CSVParser(file_path)
        result = parser.parse()
        assert len(result) == 2 # Duplicates should be dropped
        captured = capsys.readouterr()
        assert "Warning: Removed 1 duplicate neighborhood-borough entries" in captured.out

    def test_parse_csv_with_empty_rows_or_values(self, temp_csv_file):
        content = """Neighborhood,Borough
Maspeth,Queens

Williamsburg,Brooklyn
Invalid,,
 ,
Empty,
"""
        file_path = temp_csv_file(content)
        parser = CSVParser(file_path)
        result = parser.parse()
        assert len(result) == 2 # Only Maspeth and Williamsburg should remain
        assert result[0] == {"Neighborhood": "Maspeth", "Borough": "Queens"}
        assert result[1] == {"Neighborhood": "Williamsburg", "Borough": "Brooklyn"}
    
    def test_parse_csv_with_whitespace(self, temp_csv_file):
        content = """Neighborhood , Borough
 Maspeth , Queens 
Williamsburg , Brooklyn
"""
        file_path = temp_csv_file(content)
        parser = CSVParser(file_path)
        result = parser.parse()
        assert len(result) == 2
        assert result[0] == {"Neighborhood": "Maspeth", "Borough": "Queens"}
        assert result[1] == {"Neighborhood": "Williamsburg", "Borough": "Brooklyn"}

    def test_parse_file_not_found(self):
        parser = CSVParser(Path("non_existent_file.csv"))
        with pytest.raises(ValueError, match="CSV file not found"):
            parser.parse()

    def test_parse_missing_required_columns(self, temp_csv_file):
        content = """Name,City
Maspeth,Queens
"""
        file_path = temp_csv_file(content)
        parser = CSVParser(file_path)
        with pytest.raises(ValueError, match="CSV file must contain 'Neighborhood' and 'Borough' columns"):
            parser.parse()

    def test_parse_empty_csv_after_cleaning(self, temp_csv_file):
        content = """Neighborhood,Borough
,,
 ,
"""
        file_path = temp_csv_file(content)
        parser = CSVParser(file_path)
        with pytest.raises(ValueError, match="No valid neighborhood-borough pairs found after cleaning."):
            parser.parse()

    def test_parse_empty_csv_file(self, temp_csv_file):
        content = ""
        file_path = temp_csv_file(content)
        parser = CSVParser(file_path)
        with pytest.raises(ValueError, match="Error reading CSV file"): # pandas will raise EmptyDataError
            parser.parse()
