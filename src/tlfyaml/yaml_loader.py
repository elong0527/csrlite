from pathlib import Path
from typing import Any, Dict
import yaml
from copy import deepcopy

class YamlInheritanceLoader:
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path('.')

    def load(self, file_name: str) -> Dict[str, Any]:
        """
        Load a YAML file by name relative to base_path and resolve inheritance.
        """
        file_path = self.base_path / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"YAML file not found: {file_path}")

        with open(file_path, 'r') as f:
            data = yaml.safe_load(f) or {}

        return self._resolve_inheritance(data)

    def _resolve_inheritance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        templates = data.get('study', {}).get('template', [])
        if isinstance(templates, str):
            templates = [templates]

        if not templates:
            return data

        merged_template_data = {}
        for template_file in templates:
            template_data = self.load(template_file)
            merged_template_data = self._deep_merge(merged_template_data, template_data)

        return self._deep_merge(merged_template_data, data)

    def _deep_merge(self, dict1: Dict, dict2: Dict) -> Dict:
        merged = deepcopy(dict1)
        for key, value in dict2.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._deep_merge(merged[key], value)
            elif key in merged and isinstance(merged[key], list) and isinstance(value, list):
                merged[key].extend([item for item in value if item not in merged[key]])
            else:
                merged[key] = value
        return merged
