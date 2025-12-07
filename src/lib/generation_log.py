import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("nyc_neighborhoods")

class GenerationLog:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_data: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """Loads the JSON log file from disk if it exists."""
        if self.log_path.exists():
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    self.log_data = json.load(f)
                logger.info(f"Loaded generation log from {os.path.relpath(self.log_path)} with {len(self.log_data)} entries.")
            except json.JSONDecodeError:
                logger.warning(f"Could not decode existing generation log at {os.path.relpath(self.log_path)}. Starting fresh.")
                self.log_data = []
        else:
            logger.info(f"Generation log not found at {os.path.relpath(self.log_path)}. A new one will be created.")

    def _save(self):
        """Saves the current log data to the JSON file."""
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(self.log_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Generation log saved to {os.path.relpath(self.log_path)}")
        except Exception as e:
            logger.error(f"Failed to save generation log to {os.path.relpath(self.log_path)}: {e}")

    def add_entry(self, entry: Dict[str, Any]):
        """
        Adds a new entry to the log. If an entry with the same unique identifier
        (neighborhood_name, borough) already exists, it updates it.
        """
        neighborhood_name = entry.get("neighborhood_name")
        borough = entry.get("borough")
        
        # Check for existing entry and update it
        found_and_updated = False
        for i, existing_entry in enumerate(self.log_data):
            if (existing_entry.get("neighborhood_name") == neighborhood_name and
                existing_entry.get("borough") == borough):
                self.log_data[i] = entry
                found_and_updated = True
                logger.debug(f"Updated log entry for {neighborhood_name}, {borough}.")
                break
        
        if not found_and_updated:
            self.log_data.append(entry)
            logger.debug(f"Added new log entry for {neighborhood_name}, {borough}.")

        self._save()

    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Returns all entries in the log."""
        return self.log_data

    def remove_entry(self, neighborhood_name: str, borough: str) -> bool:
        """
        Removes a log entry by neighborhood name and borough.

        Returns:
            True if an entry was removed, False otherwise.
        """
        initial_len = len(self.log_data)
        self.log_data = [
            entry for entry in self.log_data
            if not (entry.get("neighborhood_name") == neighborhood_name and entry.get("borough") == borough)
        ]
        if len(self.log_data) < initial_len:
            self._save()
            logger.debug(f"Removed log entry for {neighborhood_name}, {borough}.")
            return True
        return False

    def find_entry(self, neighborhood_name: str, borough: str) -> Optional[Dict[str, Any]]:
        """
        Finds a log entry by neighborhood name and borough.

        Returns:
            The entry if found, otherwise None.
        """
        for entry in self.log_data:
            if (entry.get("neighborhood_name") == neighborhood_name and
                entry.get("borough") == borough):
                return entry
        return None

if __name__ == '__main__':
    from src.lib.logger import setup_logging
    setup_logging(level=logging.INFO)

    demo_log_path = Path("temp_logs/generation_log.json")
    
    # Clean up previous demo run
    if demo_log_path.exists():
        demo_log_path.unlink()
    if demo_log_path.parent.exists():
        demo_log_path.parent.rmdir()

    # --- Test 1: Initialization and adding new entries ---
    print("\n--- Test 1: Initialization and adding entries ---")
    log = GenerationLog(demo_log_path)
    entry1 = {
        "neighborhood_name": "Maspeth", "borough": "Queens",
        "generation_date": "2025-12-03T10:00:00", "output_file_path": "output/Maspeth_Queens.md"
    }
    log.add_entry(entry1)
    
    entry2 = {
        "neighborhood_name": "Williamsburg", "borough": "Brooklyn",
        "generation_date": "2025-12-03T11:00:00", "output_file_path": "output/Williamsburg_Brooklyn.md"
    }
    log.add_entry(entry2)
    
    all_entries = log.get_all_entries()
    print("All entries:", json.dumps(all_entries, indent=2))
    assert len(all_entries) == 2

    # --- Test 2: Finding an entry ---
    print("\n--- Test 2: Finding an entry ---")
    found_entry = log.find_entry("Maspeth", "Queens")
    print("Found Maspeth:", found_entry)
    assert found_entry is not None
    assert found_entry["generation_date"] == "2025-12-03T10:00:00"

    # --- Test 3: Updating an entry ---
    print("\n--- Test 3: Updating an entry ---")
    updated_entry1 = {
        "neighborhood_name": "Maspeth", "borough": "Queens",
        "generation_date": "2025-12-04T12:00:00", "output_file_path": "output/Maspeth_Queens.md"
    }
    log.add_entry(updated_entry1)
    all_entries_updated = log.get_all_entries()
    print("All entries after update:", json.dumps(all_entries_updated, indent=2))
    assert len(all_entries_updated) == 2
    found_entry_updated = log.find_entry("Maspeth", "Queens")
    assert found_entry_updated["generation_date"] == "2025-12-04T12:00:00"

    # --- Test 4: Loading from existing file ---
    print("\n--- Test 4: Loading from existing file ---")
    del log # Delete instance to ensure it reloads from file
    log_reloaded = GenerationLog(demo_log_path)
    all_entries_reloaded = log_reloaded.get_all_entries()
    print("Reloaded entries:", json.dumps(all_entries_reloaded, indent=2))
    assert len(all_entries_reloaded) == 2

    # Clean up
    if demo_log_path.exists():
        demo_log_path.unlink()
    if demo_log_path.parent.exists():
        demo_log_path.parent.rmdir()
