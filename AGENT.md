# TLF YAML Framework Agent Documentation

## Overview

This document provides guidance for AI agents working with the TLF YAML Framework for clinical trial reporting. The framework uses a simplified plan-focused approach with single YAML files per study, directly mapping to metalite R package patterns for generating Tables, Listings, and Figures (TLFs) for regulatory submissions.

## Simplified Architecture

### Core Components

```
src/tlfyaml/
├── simple_plan.py   # Main simplified plan implementation
└── models/
    └── plan.py      # Plan data models (CondensedPlan, IndividualPlan)
```

### Single Plan File Approach

Each study has a single plan YAML file that contains everything needed:
- Study metadata
- Data source references (subject/observation level)
- Condensed analysis plans that expand to individual analyses

Example: `examples/yaml/plan_xyz123.yaml`

## Key Design Principles

### 1. Metalite R Pattern Mapping
Direct correspondence between metalite R syntax and YAML structure:

**Metalite R:**
```r
plan(analysis = "ae_summary",
     population = "apat",
     observation = c("wk12", "wk24"),
     parameter = "any;rel;ser")
```

**YAML Equivalent:**
```yaml
- analysis: "ae_summary"
  population: ["apat"]
  observation: ["wk12", "wk24"]
  parameter: "any;rel;ser"
```

### 2. Cartesian Product Expansion
One condensed plan generates multiple individual analyses through Cartesian product:
- 1 analysis × 1 population × 2 observations × 3 parameters = 6 individual analyses

### 3. Two Data Source Pattern
Assumes at most two data sources:
- **Subject level**: e.g., ADSL (demographics)
- **Observation level**: e.g., ADAE (adverse events)

```yaml
data:
  subject: "data/adam_validate/adsl.parquet"
  observation: "data/adam_validate/adae.parquet"
```

## Working with the Framework

### Loading and Expanding Plans
```python
from tlfyaml.simple_plan import SimplePlanLoader

# Load plan and expand to individual analyses
loader = SimplePlanLoader('examples/yaml')
summary = loader.expand('plan_xyz123.yaml')

# Access expanded analyses
print(f"Study: {summary['study']['name']}")
print(f"Plans: {summary['condensed_plans']} → {summary['individual_analyses']} analyses")
```

### Understanding Plan Models

#### Core Concepts
- **SimplePlan**: Condensed plan specification with lists for Cartesian expansion
- **StudyPlan**: Complete study plan containing metadata and multiple SimplePlans
- **Plan Expansion**: Converting condensed plans to individual analysis specifications

#### Plan Structure
```yaml
plans:
  - analysis: "demographics"      # Single analysis type
    population: ["itt"]          # List of populations
    observation: ["wk12"]        # Optional observation periods
    parameter: ["age", "sex"]    # List or semicolon-separated parameters
```

### Common Patterns

#### 1. Single Analysis Plan
```yaml
- analysis: "demographics"
  population: ["itt"]
  # No observation or parameter needed for demographics
```

#### 2. Multiple Populations
```yaml
- analysis: "ae_summary"
  population: ["apat", "itt", "safety"]
  observation: ["wk12"]
  parameter: ["any"]
```

#### 3. Cartesian Product Expansion
```yaml
- analysis: "ae_specific"
  population: ["apat"]
  observation: ["wk12", "wk24"]
  parameter: ["any", "rel", "ser"]
# Generates 6 individual analyses (1×2×3)

## Agent Guidelines

### 1. When Creating Plan Configurations

**DO:**
- Use consistent list format with `-` for all plan items
- Include required `parameter` field for all analyses except demographics
- Follow metalite R syntax patterns directly
- Test plan expansion to verify expected number of analyses
- Use semicolon format `"any;rel;ser"` for single parameter combinations
- Use list format `["any", "rel", "ser"]` for Cartesian product expansion

**DON'T:**
- Mix plan naming conventions (avoid named plan sections)
- Forget required `parameter` field
- Create overly complex nested structures
- Duplicate analysis specifications

### 2. Understanding Clinical Context

**Key Clinical Populations:**
- **ITT**: Intention-to-Treat population (all randomized)
- **APAT**: All Patients as Treated (safety population)
- **Safety**: Subjects who received study treatment

**Common Analysis Types:**
- **demographics**: Subject baseline characteristics
- **ae_summary**: Adverse event summary tables
- **ae_specific**: Specific adverse event analysis
- **ae_listing**: Detailed adverse event listings

**Parameter Examples:**
- **any**: Any adverse event
- **rel**: Related adverse events
- **ser**: Serious adverse events

### 3. Error Handling

**Common Issues:**
- Missing `parameter` field in plans
- Invalid YAML list syntax
- File path errors in data sources
- Pydantic validation failures

**Debugging:**
- Use `SimplePlanLoader` to test plan loading
- Check plan expansion results
- Verify YAML syntax with proper `-` list format
- Test with example files first

## Extension Points

### Adding New Analysis Types
1. Add new analysis identifier to plan YAML
2. Implement corresponding generation logic
3. Define required parameters for the analysis type

### Custom Parameters
1. Add new parameter values to plan specifications
2. Document parameter meaning and usage
3. Ensure parameter combinations make clinical sense

### Data Source Extensions
1. Modify data source references in plan YAML
2. Update loader to handle new data sources
3. Maintain subject/observation level distinction

## Best Practices for Agents

### 1. Plan Design
- Focus on simplicity over complexity
- Use single plan file per study approach
- Follow metalite R patterns directly
- Validate plan expansion results

### 2. Clinical Accuracy
- Understand analysis population definitions
- Use appropriate parameter combinations
- Ensure clinically meaningful groupings
- Follow regulatory TLF standards

### 3. Maintainability
- Use descriptive analysis identifiers
- Document parameter meanings clearly
- Keep plan specifications minimal
- Test with realistic data scenarios

## Resources

- **Simplified Design Document**: `SIMPLIFIED_DESIGN.md`
- **Example Plan**: `examples/yaml/plan_xyz123.yaml`
- **Main Implementation**: `src/tlfyaml/simple_plan.py`
- **Plan Models**: `src/tlfyaml/models/plan.py`

## Quick Reference

### Plan File Structure
```yaml
# Single plan file per study
study:
  name: "XYZ123"
  title: "Phase III Study"

data:
  subject: "data/adsl.parquet"      # Subject-level data
  observation: "data/adae.parquet"  # Observation-level data

plans:
  - analysis: "demographics"
    population: ["itt"]
  - analysis: "ae_summary"
    population: ["apat"]
    observation: ["wk12", "wk24"]
    parameter: "any;rel;ser"
```

### Key Commands
```bash
# Run simplified demo
uv run python -c "from tlfyaml.simple_plan import demonstrate_simplicity; demonstrate_simplicity()"

# Load and expand plan
from tlfyaml.simple_plan import SimplePlanLoader
loader = SimplePlanLoader('examples/yaml')
summary = loader.expand('plan_xyz123.yaml')
```

This simplified framework prioritizes practical clinical analysis needs over architectural complexity, following the metalite R package pattern directly.