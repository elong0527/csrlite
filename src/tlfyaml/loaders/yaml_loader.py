"""
YAML inheritance loader for TLF framework.

Handles loading YAML configurations with hierarchical inheritance:
Organization → Therapeutic Area → Study
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from copy import deepcopy

from ..models.config import OrganizationConfig, TherapeuticAreaConfig, StudyConfig


class YAMLInheritanceLoader:
    """
    Loads and resolves YAML configurations with inheritance.

    Supports hierarchical inheritance where child configurations
    inherit from parent configurations and can override specific values.
    """

    def __init__(self, config_base_path: Optional[str] = None):
        """
        Initialize the YAML loader.

        Args:
            config_base_path: Base directory for YAML configuration files.
                             If None, uses the current directory.
        """
        self.config_base_path = Path(config_base_path) if config_base_path else Path.cwd()
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load_study_config(self, study_yaml_path: str) -> StudyConfig:
        """
        Load a study configuration with full inheritance resolution.

        Args:
            study_yaml_path: Path to the study YAML file

        Returns:
            StudyConfig: Fully resolved study configuration

        Raises:
            FileNotFoundError: If YAML file is not found
            yaml.YAMLError: If YAML parsing fails
            ValueError: If inheritance chain is invalid
        """
        # Load the study YAML
        study_config = self._load_yaml_file(study_yaml_path)

        # Resolve inheritance chain
        resolved_config = self._resolve_inheritance(study_config, study_yaml_path)

        # Validate and return as StudyConfig
        return StudyConfig(**resolved_config)

    def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load a YAML file with caching.

        Args:
            file_path: Path to YAML file

        Returns:
            Dict: Parsed YAML content
        """
        abs_path = self._resolve_path(file_path)

        # Check cache first
        if str(abs_path) in self._cache:
            return deepcopy(self._cache[str(abs_path)])

        # Load file
        if not abs_path.exists():
            raise FileNotFoundError(f"YAML file not found: {abs_path}")

        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML file {abs_path}: {e}")

        # Cache the content
        self._cache[str(abs_path)] = deepcopy(content)

        return content

    def _resolve_inheritance(self, config: Dict[str, Any], config_path: str) -> Dict[str, Any]:
        """
        Recursively resolve inheritance chain.

        Args:
            config: Configuration dictionary
            config_path: Path to current config file (for relative path resolution)

        Returns:
            Dict: Fully resolved configuration
        """
        # Base case: no inheritance
        if 'inherits_from' not in config:
            return config

        parent_name = config['inherits_from']

        # Load parent configuration
        parent_path = self._find_parent_config(parent_name, config_path)
        parent_config = self._load_yaml_file(parent_path)

        # Recursively resolve parent's inheritance
        resolved_parent = self._resolve_inheritance(parent_config, parent_path)

        # Merge parent and child configurations
        merged_config = self._merge_configs(resolved_parent, config)

        return merged_config

    def _find_parent_config(self, parent_name: str, current_config_path: str) -> str:
        """
        Find the parent configuration file.

        Args:
            parent_name: Name of parent configuration
            current_config_path: Path to current config file

        Returns:
            str: Path to parent configuration file
        """
        # Try different patterns to find the parent config
        search_patterns = [
            f"{parent_name}.yaml",
            f"{parent_name}.yml",
            f"configs/{parent_name}.yaml",
            f"../configs/{parent_name}.yaml",
        ]

        current_dir = Path(current_config_path).parent

        for pattern in search_patterns:
            potential_path = current_dir / pattern
            if potential_path.exists():
                return str(potential_path)

        # Also try from base config path
        for pattern in search_patterns:
            potential_path = self.config_base_path / pattern
            if potential_path.exists():
                return str(potential_path)

        raise FileNotFoundError(f"Parent configuration '{parent_name}' not found")

    def _merge_configs(self, parent: Dict[str, Any], child: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge parent and child configurations with child taking precedence.

        Args:
            parent: Parent configuration
            child: Child configuration

        Returns:
            Dict: Merged configuration
        """
        merged = deepcopy(parent)

        # Merge each top-level key
        for key, value in child.items():
            if key == 'inherits_from':
                # Remove inherits_from from final config
                continue
            elif key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                merged[key] = self._deep_merge_dict(merged[key], value)
            else:
                # Child overrides parent
                merged[key] = deepcopy(value)

        return merged

    def _deep_merge_dict(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.

        Args:
            dict1: Base dictionary
            dict2: Override dictionary

        Returns:
            Dict: Merged dictionary
        """
        result = deepcopy(dict1)

        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_dict(result[key], value)
            else:
                result[key] = deepcopy(value)

        return result

    def _resolve_path(self, file_path: str) -> Path:
        """
        Resolve file path relative to base config path.

        Args:
            file_path: Input file path

        Returns:
            Path: Resolved absolute path
        """
        path = Path(file_path)
        if path.is_absolute():
            return path
        else:
            return self.config_base_path / path

    def clear_cache(self):
        """Clear the configuration cache."""
        self._cache.clear()

    def load_organization_config(self, org_yaml_path: str) -> OrganizationConfig:
        """
        Load organization-level configuration.

        Args:
            org_yaml_path: Path to organization YAML file

        Returns:
            OrganizationConfig: Organization configuration
        """
        config = self._load_yaml_file(org_yaml_path)
        return OrganizationConfig(**config)

    def load_therapeutic_area_config(self, ta_yaml_path: str) -> TherapeuticAreaConfig:
        """
        Load therapeutic area configuration with inheritance.

        Args:
            ta_yaml_path: Path to therapeutic area YAML file

        Returns:
            TherapeuticAreaConfig: TA configuration with inheritance resolved
        """
        config = self._load_yaml_file(ta_yaml_path)
        resolved_config = self._resolve_inheritance(config, ta_yaml_path)
        return TherapeuticAreaConfig(**resolved_config)