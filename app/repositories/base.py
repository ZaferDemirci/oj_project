import json
import os
import tempfile
from typing import Any, Optional

class BaseRepository:
    def __init__(self, file_path: str):
        self.file_path = file_path
        dir_name = os.path.dirname(file_path) # Ensure dir exists
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def _load_data(self) -> Optional[Any]:
        """
        Load raw JSON data from the file.
        Returns None if the file does not exist.
        Raises RuntimeError if the file is corrupted (cannot be parsed).
        """

        if not os.path.exists(self.file_path):
            return None

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # Raise an error instead of returning empty list/dict so the API returns HTTP 500 and data is preserved
            raise RuntimeError(f"Data file {self.file_path} is corrupted: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to read {self.file_path}: {e}")

    def _save_data(self, data: Any) -> None:
        temp_path = self.file_path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(temp_path, self.file_path)
        except Exception as e:
            # Clean up temp file if an error occurred
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass # best effort
            raise RuntimeError(f"Failed to save data to {self.file_path}: {e}")