"""
TLF YAML Framework - A hierarchical YAML-based framework for generating
Tables, Listings, and Figures in clinical trials.

Inspired by the metalite R package ecosystem.
"""

__version__ = "0.1.0"
__author__ = "Clinical Biostatistics Team"

from .loaders import YAMLInheritanceLoader
from .generators import TLFGenerator

__all__ = [
    "YAMLInheritanceLoader",
    "TLFGenerator",
]