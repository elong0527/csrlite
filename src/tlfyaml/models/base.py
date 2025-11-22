"""
Base data models for TLF YAML framework.
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


class Variable(BaseModel):
    """Represents a clinical data variable."""
    name: str = Field(..., description="Variable name (e.g., USUBJID)")
    label: str = Field(..., description="Variable label for display")
    type: Literal["string", "numeric", "date", "datetime"] = Field(..., description="Variable data type")
    required: bool = Field(default=False, description="Whether variable is required")


class Population(BaseModel):
    """Defines a clinical analysis population."""
    name: str = Field(..., description="Population identifier (e.g., SAFFL)")
    label: str = Field(..., description="Population description for display")
    filter: str = Field(..., description="SQL-like filter expression")


class Parameter(BaseModel):
    """Defines an analysis parameter."""
    name: str = Field(..., description="Parameter identifier")
    label: str = Field(..., description="Parameter description for display")
    filter: Optional[str] = Field(default=None, description="SQL-like filter expression")


class DataSource(BaseModel):
    """Defines a data source (ADaM dataset)."""
    path: str = Field(..., description="File path to dataset")
    source: str = Field(..., description="ADaM domain name (e.g., ADSL, ADAE)")


class DataSources(BaseModel):
    """Defines the two standard data sources for TLF generation."""
    subject: DataSource = Field(..., description="Subject-level dataset (e.g., ADSL)")
    observation: DataSource = Field(..., description="Observation-level dataset (e.g., ADAE, ADVS)")


class Treatment(BaseModel):
    """Defines a treatment group."""
    name: str = Field(..., description="Treatment name for display")
    variable: str = Field(..., description="Treatment variable name")
    filter: str = Field(..., description="SQL-like filter to identify treatment")


class Column(BaseModel):
    """Defines a column for listings."""
    name: str = Field(..., description="Column header name")
    variable: str = Field(..., description="Variable name")
    format: Optional[str] = Field(default=None, description="Display format")
    width: Optional[int] = Field(default=None, description="Column width")


class OutputFormat(BaseModel):
    """Defines output formatting options."""
    filename: str = Field(..., description="Output filename")
    title_page: bool = Field(default=True, description="Include title page")
    orientation: Literal["portrait", "landscape"] = Field(default="landscape", description="Page orientation")
    font_size: int = Field(default=9, description="Font size")
    engine: Literal["rtflite"] = Field(default="rtflite", description="Output generation engine")