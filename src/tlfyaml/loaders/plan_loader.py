"""
Plan loader for handling separate plan YAML files.

This module loads study plans that are defined separately from the main
study configuration, following the metalite pattern of condensed plan specifications.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List

from ..models.plan import StudyPlan, CondensedPlan, IndividualPlan


class PlanLoader:
    """
    Loader for study analysis plans defined in separate YAML files.

    Supports the metalite-style condensed plan format where multiple
    combinations are generated from lists of values.
    """

    def __init__(self, config_base_path: str = "."):
        """
        Initialize the plan loader.

        Args:
            config_base_path: Base directory for plan files
        """
        self.config_base_path = Path(config_base_path)

    def load_study_plan(self, plan_file: str) -> StudyPlan:
        """
        Load a study plan from a YAML file.

        Args:
            plan_file: Path to the plan YAML file

        Returns:
            StudyPlan: Loaded and validated study plan

        Raises:
            FileNotFoundError: If plan file is not found
            yaml.YAMLError: If YAML parsing fails
        """
        plan_path = self._resolve_path(plan_file)

        if not plan_path.exists():
            raise FileNotFoundError(f"Plan file not found: {plan_path}")

        try:
            with open(plan_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing plan file {plan_path}: {e}")

        return StudyPlan(**content)

    def expand_study_plan(self, plan_file: str) -> List[IndividualPlan]:
        """
        Load a study plan and expand all condensed plans into individual plans.

        Args:
            plan_file: Path to the plan YAML file

        Returns:
            List[IndividualPlan]: All individual plans generated from condensed plans
        """
        study_plan = self.load_study_plan(plan_file)
        return study_plan.expand_all_plans()

    def generate_plan_summary(self, plan_file: str) -> Dict[str, Any]:
        """
        Generate a summary of how many individual plans each condensed plan creates.

        Args:
            plan_file: Path to the plan YAML file

        Returns:
            Dict: Summary with plan counts and details
        """
        study_plan = self.load_study_plan(plan_file)
        individual_plans = study_plan.expand_all_plans()
        plan_summary = study_plan.get_plan_summary()

        return {
            "study": study_plan.study,
            "condensed_plans": len(study_plan.plans),
            "individual_plans": len(individual_plans),
            "plan_breakdown": plan_summary,
            "plan_details": [
                {
                    "id": plan.generate_id(),
                    "analysis": plan.analysis,
                    "population": plan.population,
                    "observation": plan.observation,
                    "parameter": plan.parameter
                }
                for plan in individual_plans
            ]
        }

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

    def validate_plan_references(self, study_plan: StudyPlan,
                                available_mocks: List[str],
                                available_populations: List[str],
                                available_observations: List[str],
                                available_parameters: List[str]) -> Dict[str, List[str]]:
        """
        Validate that all plan references exist in the study configuration.

        Args:
            study_plan: Study plan to validate
            available_mocks: List of available mock identifiers
            available_populations: List of available population identifiers
            available_observations: List of available observation identifiers
            available_parameters: List of available parameter identifiers

        Returns:
            Dict: Validation results with any missing references
        """
        missing = {
            "mocks": [],
            "populations": [],
            "observations": [],
            "parameters": []
        }

        for plan_name, plan in study_plan.plans.items():
            # Check analysis/mock
            if plan.analysis not in available_mocks:
                missing["mocks"].append(f"{plan_name}: {plan.analysis}")

            # Check populations
            for pop in plan.population:
                if pop not in available_populations:
                    missing["populations"].append(f"{plan_name}: {pop}")

            # Check observations
            if plan.observation:
                for obs in plan.observation:
                    if obs not in available_observations:
                        missing["observations"].append(f"{plan_name}: {obs}")

            # Check parameters
            parameters = plan.parameter if isinstance(plan.parameter, list) else plan.parameter.split(';')
            for param in parameters:
                param = param.strip()
                if param not in available_parameters:
                    missing["parameters"].append(f"{plan_name}: {param}")

        return missing