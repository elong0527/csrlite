"""
Configuration models for different hierarchy levels.
"""

from typing import List, Dict, Optional, Union, Any
from pydantic import BaseModel, Field
from .base import Variable, Population, Parameter, DataSources, Treatment
from .tlf import Table, Listing, Figure
from .mock import MockUnion, Plan, Observation


class OrganizationConfig(BaseModel):
    """Organization-level configuration."""
    organization: Dict[str, str] = Field(..., description="Organization metadata")
    common_variables: Optional[Dict[str, Variable]] = Field(default=None, description="Common variables")
    common_populations: Optional[Dict[str, Population]] = Field(default=None, description="Common populations")
    output_formats: Optional[Dict[str, Dict[str, Any]]] = Field(default=None, description="Output format defaults")


class TherapeuticAreaConfig(BaseModel):
    """Therapeutic Area-level configuration."""
    therapeutic_area: Dict[str, str] = Field(..., description="TA metadata")
    populations: Optional[Dict[str, Population]] = Field(default=None, description="TA-specific populations")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="TA-specific parameters")
    tlf_templates: Optional[Dict[str, Any]] = Field(default=None, description="TLF templates")

    # Inherited fields from organization level
    organization: Optional[Dict[str, str]] = Field(default=None, description="Organization metadata")
    common_variables: Optional[Dict[str, Variable]] = Field(default=None, description="Common variables")
    common_populations: Optional[Dict[str, Population]] = Field(default=None, description="Common populations")
    output_formats: Optional[Dict[str, Dict[str, Any]]] = Field(default=None, description="Output format defaults")


class StudyConfig(BaseModel):
    """Study-level configuration with full inheritance resolution."""
    study: Dict[str, str] = Field(..., description="Study metadata")
    data: DataSources = Field(..., description="Study data sources (subject and observation)")
    treatments: Optional[Dict[str, Treatment]] = Field(default=None, description="Study treatments")
    populations: Optional[Dict[str, Population]] = Field(default=None, description="Study populations")
    observations: Optional[Dict[str, Observation]] = Field(default=None, description="Study observation periods")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Study parameters")

    # New mock/plan structure
    mocks: Optional[Dict[str, MockUnion]] = Field(default=None, description="Mock templates")
    plans: Optional[List[Plan]] = Field(default=None, description="Plan specifications")

    # Legacy TLF structure (for backward compatibility)
    tlfs: Optional[Dict[str, Union[Table, Listing, Figure]]] = Field(default=None, description="Legacy TLF specifications")

    # Inherited fields from organization and TA levels
    organization: Optional[Dict[str, str]] = Field(default=None, description="Organization metadata")
    therapeutic_area: Optional[Dict[str, str]] = Field(default=None, description="TA metadata")
    common_variables: Optional[Dict[str, Variable]] = Field(default=None, description="Common variables")
    common_populations: Optional[Dict[str, Population]] = Field(default=None, description="Common populations")
    output_formats: Optional[Dict[str, Dict[str, Any]]] = Field(default=None, description="Output formats")
    tlf_templates: Optional[Dict[str, Any]] = Field(default=None, description="TLF templates")

    model_config = {"validate_assignment": True}