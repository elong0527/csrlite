"""
Mock and Plan models for metalite-style TLF generation.

This module defines the mock/plan pattern where:
- Mocks define reusable TLF templates
- Plans specify which combinations to generate from each mock
"""

from typing import List, Dict, Optional, Literal, Union
from pydantic import BaseModel, Field
from .base import Column, Treatment


class MockBase(BaseModel):
    """Base class for TLF mocks (templates)."""
    type: Literal["table", "listing", "figure"] = Field(..., description="TLF type")
    title_template: str = Field(..., description="Title template with placeholders like {parameter_label}")
    subtitle_template: Optional[str] = Field(default=None, description="Subtitle template")
    data: Literal["subject", "observation"] = Field(..., description="Data source type")


class TableMock(MockBase):
    """Mock template for summary tables."""
    type: Literal["table"] = Field(default="table")
    group_by: List[str] = Field(..., description="Grouping variables")
    summary_vars: Optional[List[str]] = Field(default=None, description="Variables to summarize (if not parameter-specific)")
    treatments: Optional[List[Treatment]] = Field(default=None, description="Treatment groups")
    columns: Optional[List[Column]] = Field(default=None, description="Table columns")
    output: Dict[str, Union[str, int]] = Field(..., description="Output formatting with templates")


class ListingMock(MockBase):
    """Mock template for patient listings."""
    type: Literal["listing"] = Field(default="listing")
    sort_by: List[str] = Field(..., description="Sort variables")
    columns: List[Column] = Field(..., description="Listing columns")
    output: Dict[str, Union[str, int]] = Field(..., description="Output formatting with templates")


class FigureMock(MockBase):
    """Mock template for figures."""
    type: Literal["figure"] = Field(default="figure")
    plot_type: Literal["forest", "kaplan_meier", "histogram", "box", "scatter"] = Field(..., description="Plot type")
    x_axis: Optional[str] = Field(default=None, description="X-axis variable")
    y_axis: Optional[str] = Field(default=None, description="Y-axis variable")
    group_var: Optional[str] = Field(default=None, description="Grouping variable")
    output: Dict[str, Union[str, int]] = Field(..., description="Output formatting with templates")


class Observation(BaseModel):
    """Defines an observation period/window."""
    name: str = Field(..., description="Observation identifier")
    label: str = Field(..., description="Observation description")
    filter: str = Field(..., description="SQL-like filter for observation period")


class Plan(BaseModel):
    """Plan specification for generating a specific TLF from a mock."""
    mock: str = Field(..., description="Mock template identifier")
    population: str = Field(..., description="Population identifier")
    observation: Optional[str] = Field(default=None, description="Observation period (optional)")
    parameter: str = Field(..., description="Parameter identifier")
    filter: Optional[str] = Field(default=None, description="Additional filter specific to this plan")
    footnotes: Optional[List[str]] = Field(default=None, description="Plan-specific footnotes")

    def generate_id(self) -> str:
        """Generate a unique identifier for this plan."""
        parts = [self.mock, self.population]
        if self.observation:
            parts.append(self.observation)
        parts.append(self.parameter)
        return "_".join(parts)


# Union type for all mock types
MockUnion = Union[TableMock, ListingMock, FigureMock]