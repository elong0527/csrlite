"""
Plan models for metalite-style condensed analysis plans.

This module supports the metalite approach where plans can be specified
using lists of values to create Cartesian products, similar to:
plan(analysis="ae_summary", population="apat", observation=c("wk12", "wk24"), parameter="any;rel;ser")
"""

from typing import List, Dict, Optional, Union, Any
from pydantic import BaseModel, Field, validator
import itertools


class CondensedPlan(BaseModel):
    """
    Condensed plan specification that generates multiple analysis combinations.

    Similar to metalite's plan() function, this creates a Cartesian product
    of all specified values.
    """
    analysis: str = Field(..., description="Analysis type (mock identifier)")
    population: List[str] = Field(..., description="Population identifiers")
    observation: Optional[List[str]] = Field(default=None, description="Observation period identifiers")
    parameter: Union[str, List[str]] = Field(..., description="Parameter identifiers (string with ; or list)")

    @validator('parameter')
    def parse_parameter(cls, v):
        """Parse parameter field - handle both semicolon-separated strings and lists."""
        if isinstance(v, str):
            # Handle semicolon-separated format like "any;rel;ser"
            return [p.strip() for p in v.split(';')]
        return v

    def generate_individual_plans(self) -> List['IndividualPlan']:
        """
        Generate all individual plan combinations from the condensed specification.

        Returns:
            List[IndividualPlan]: All possible combinations
        """
        plans = []

        # Create Cartesian product of all combinations
        populations = self.population
        observations = self.observation or [None]
        parameters = self.parameter if isinstance(self.parameter, list) else [self.parameter]

        for pop, obs, param in itertools.product(populations, observations, parameters):
            plan = IndividualPlan(
                analysis=self.analysis,
                population=pop,
                observation=obs,
                parameter=param
            )
            plans.append(plan)

        return plans

    def count_combinations(self) -> int:
        """Count how many individual plans this condensed plan will generate."""
        pop_count = len(self.population)
        obs_count = len(self.observation) if self.observation else 1
        param_count = len(self.parameter) if isinstance(self.parameter, list) else len(self.parameter.split(';'))

        return pop_count * obs_count * param_count


class IndividualPlan(BaseModel):
    """Individual plan specification - one specific combination."""
    analysis: str = Field(..., description="Analysis type (mock identifier)")
    population: str = Field(..., description="Population identifier")
    observation: Optional[str] = Field(default=None, description="Observation period identifier")
    parameter: str = Field(..., description="Parameter identifier")

    def generate_id(self) -> str:
        """Generate a unique identifier for this plan."""
        parts = [self.analysis, self.population]
        if self.observation:
            parts.append(self.observation)
        parts.append(self.parameter)
        return "_".join(parts)

    def generate_title(self, mock_title_template: str,
                      population_label: str,
                      observation_label: Optional[str] = None,
                      parameter_label: str = "") -> str:
        """Generate title from template and labels."""
        title = mock_title_template.format(
            parameter_label=parameter_label,
            population_label=population_label,
            observation_label=observation_label or ""
        )
        return title

    def generate_filename(self, filename_template: str) -> str:
        """Generate filename from template."""
        filename = filename_template.format(
            analysis=self.analysis,
            mock=self.analysis,  # alias for analysis
            population=self.population,
            observation=self.observation or "",
            parameter=self.parameter
        )
        # Clean up double underscores from empty observations
        filename = filename.replace("__", "_").strip("_")
        return filename


class StudyPlan(BaseModel):
    """Study-level analysis plan with condensed specifications."""
    study: Dict[str, str] = Field(..., description="Study metadata")
    plans: List[CondensedPlan] = Field(..., description="Condensed plan specifications")

    def expand_all_plans(self) -> List[IndividualPlan]:
        """
        Expand all condensed plans into individual plan specifications.

        Returns:
            List[IndividualPlan]: All individual plans from all condensed plans
        """
        all_plans = []
        for i, condensed_plan in enumerate(self.plans):
            individual_plans = condensed_plan.generate_individual_plans()
            all_plans.extend(individual_plans)

        return all_plans

    def get_plan_summary(self) -> Dict[str, int]:
        """Get summary of how many plans each condensed plan generates."""
        summary = {}
        for i, condensed_plan in enumerate(self.plans):
            plan_key = f"plan_{i+1}_{condensed_plan.analysis}"
            summary[plan_key] = condensed_plan.count_combinations()

        return summary