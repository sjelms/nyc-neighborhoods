import pandas as pd
from typing import List, Tuple, Dict

class CSVParser:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> List[Dict[str, str]]:
        """
        Parses the CSV file, expecting 'Neighborhood' and 'Borough' columns.
        Returns a list of dictionaries, each representing a valid neighborhood-borough pair.
        Raises ValueError for missing file or invalid columns.
        """
        try:
            df = pd.read_csv(self.file_path)
        except FileNotFoundError:
            raise ValueError(f"CSV file not found at {self.file_path}")
        except Exception as e:
            raise ValueError(f"Error reading CSV file: {e}")

        required_columns = ["Neighborhood", "Borough"]
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"CSV file must contain 'Neighborhood' and 'Borough' columns. Found: {df.columns.tolist()}")

        # Drop rows with any missing values in required columns
        df.dropna(subset=required_columns, inplace=True)

        # Ensure values are strings and not empty after stripping whitespace
        for col in required_columns:
            df[col] = df[col].astype(str).str.strip()
            df = df[df[col] != '']

        if df.empty:
            raise ValueError("No valid neighborhood-borough pairs found after cleaning.")

        # Identify and handle duplicates (e.g., log a warning or drop)
        # For now, let's keep unique combinations and log a warning if duplicates were present
        initial_rows = len(df)
        df.drop_duplicates(subset=required_columns, inplace=True)
        if len(df) < initial_rows:
            print(f"Warning: Removed {initial_rows - len(df)} duplicate neighborhood-borough entries from {self.file_path}")

        return df[required_columns].to_dict(orient='records')

if __name__ == '__main__':
    # Example usage (for testing purposes, assumes a test.csv exists)
    # Create a dummy CSV for testing
    dummy_csv_content = """Neighborhood,Borough
    Maspeth,Queens
    Williamsburg,Brooklyn
    Maspeth,Queens
    Invalid,,
    Greenpoint,Brooklyn
    """
    with open("test.csv", "w") as f:
        f.write(dummy_csv_content)

    try:
        parser = CSVParser("test.csv")
        neighborhoods = parser.parse()
        print("Parsed neighborhoods:", neighborhoods)
    except ValueError as e:
        print("Error:", e)
    finally:
        import os
        if os.path.exists("test.csv"):
            os.remove("test.csv")

    # Test with missing columns
    dummy_csv_content_missing = """Name,City
    Maspeth,Queens
    """
    with open("test_missing.csv", "w") as f:
        f.write(dummy_csv_content_missing)

    try:
        parser = CSVParser("test_missing.csv")
        neighborhoods = parser.parse()
    except ValueError as e:
        print("Error for missing columns:", e)
    finally:
        import os
        if os.path.exists("test_missing.csv"):
            os.remove("test_missing.csv")
