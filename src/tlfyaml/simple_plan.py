"""
Simplified plan-only approach for TLF generation.

This module focuses purely on plan YAML files without complex inheritance
or mock systems, following the metalite pattern directly.
"""

import yaml
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import itertools
from pydantic import BaseModel, Field, validator


class SimplePlan(BaseModel):
    """Simple plan specification following metalite pattern."""
    analysis: str = Field(..., description="Analysis type")
    population: List[str] = Field(..., description="Population identifiers")
    observation: Optional[List[str]] = Field(default=None, description="Observation periods")
    parameter: Optional[Union[str, List[str]]] = Field(default=None, description="Parameters")

    @validator('parameter')
    def parse_parameter(cls, v):
        """Parse parameter - handle semicolon-separated strings and lists."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(';')]
        return v or []

    def expand(self) -> List[Dict[str, Any]]:
        """Expand this plan into individual analysis specifications."""
        expanded = []

        populations = self.population
        observations = self.observation or [None]
        parameters = self.parameter or [None]

        for pop, obs, param in itertools.product(populations, observations, parameters):
            spec = {
                'analysis': self.analysis,
                'population': pop,
            }
            if obs:
                spec['observation'] = obs
            if param:
                spec['parameter'] = param

            # Generate unique ID
            parts = [self.analysis, pop]
            if obs:
                parts.append(obs)
            if param:
                parts.append(param)
            spec['id'] = '_'.join(parts)

            expanded.append(spec)

        return expanded


class StudyPlan(BaseModel):
    """Complete study plan - simplified."""
    study: Dict[str, str] = Field(..., description="Study metadata")
    data: Optional[Dict[str, str]] = Field(default=None, description="Data sources")
    plans: List[SimplePlan] = Field(..., description="Analysis plans")

    def expand_all(self) -> List[Dict[str, Any]]:
        """Expand all plans into individual specifications."""
        all_expanded = []
        for plan in self.plans:
            expanded = plan.expand()
            all_expanded.extend(expanded)
        return all_expanded

    def summary(self) -> Dict[str, Any]:
        """Generate summary of plan expansion."""
        expanded = self.expand_all()
        return {
            'study': self.study,
            'data_sources': self.data,
            'condensed_plans': len(self.plans),
            'individual_analyses': len(expanded),
            'analyses': expanded
        }


class SimplePlanLoader:
    """Simple loader for plan YAML files."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)

    def load(self, plan_file: str) -> StudyPlan:
        """Load and validate a plan YAML file."""
        file_path = self.base_path / plan_file

        if not file_path.exists():
            raise FileNotFoundError(f"Plan file not found: {file_path}")

        with open(file_path, 'r') as f:
            content = yaml.safe_load(f)

        return StudyPlan(**content)

    def expand(self, plan_file: str) -> Dict[str, Any]:
        """Load plan file and return expansion summary."""
        study_plan = self.load(plan_file)
        return study_plan.summary()


def demonstrate_simplicity():
    """Demonstrate the simplified approach."""
    print("Simplified TLF Plan Approach")
    print("=" * 50)

    # Example usage
    loader = SimplePlanLoader('examples/yaml')

    try:
        summary = loader.expand('plan_xyz123.yaml')

        print(f"Study: {summary['study']['name']}")
        print(f"Plans: {summary['condensed_plans']} → {summary['individual_analyses']} analyses")
        print()

        print("Individual analyses:")
        for i, analysis in enumerate(summary['analyses'][:8], 1):  # Show first 8
            print(f"  {i:2d}. {analysis['id']}")

        if len(summary['analyses']) > 8:
            print(f"  ... and {len(summary['analyses']) - 8} more")

        print()
        print("✅ Simplified Design Benefits:")
        print("  • Single file per study")
        print("  • Direct metalite mapping")
        print("  • No inheritance complexity")
        print("  • Focus on analysis planning")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    demonstrate_simplicity()