"""
TLF-specific data models for Tables, Listings, and Figures.
"""

from typing import List, Dict, Optional, Literal, Union
from pydantic import BaseModel, Field
from .base import Column, OutputFormat, Treatment


class TLFBase(BaseModel):
    """Base class for all TLF types."""
    type: Literal["table", "listing", "figure"] = Field(..., description="TLF type")
    title: str = Field(..., description="TLF title")
    subtitle: Optional[str] = Field(default=None, description="TLF subtitle")
    data_source: str = Field(..., description="Data source identifier")
    population: str = Field(..., description="Population identifier")
    output: OutputFormat = Field(..., description="Output formatting")


class Table(TLFBase):
    """Model for summary tables."""
    type: Literal["table"] = Field(default="table")
    group_by: Optional[List[str]] = Field(default=None, description="Grouping variables")
    summary_vars: List[str] = Field(..., description="Variables to summarize")
    footnotes: Optional[List[str]] = Field(default=None, description="Table footnotes")
    treatments: Optional[List[Treatment]] = Field(default=None, description="Treatment groups")
    columns: Optional[List[Column]] = Field(default=None, description="Table columns")


class Listing(TLFBase):
    """Model for patient listings."""
    type: Literal["listing"] = Field(default="listing")
    filter: Optional[str] = Field(default=None, description="Additional filter for listing")
    sort_by: List[str] = Field(..., description="Sort variables")
    columns: List[Column] = Field(..., description="Listing columns")


class Figure(TLFBase):
    """Model for figures/plots."""
    type: Literal["figure"] = Field(default="figure")
    plot_type: Literal["forest", "kaplan_meier", "histogram", "box", "scatter"] = Field(
        ..., description="Type of plot"
    )
    x_axis: Optional[str] = Field(default=None, description="X-axis variable")
    y_axis: Optional[str] = Field(default=None, description="Y-axis variable")
    group_var: Optional[str] = Field(default=None, description="Grouping variable")
    figure_width: float = Field(default=8.0, description="Figure width in inches")
    figure_height: float = Field(default=6.0, description="Figure height in inches")