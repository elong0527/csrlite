# Claude Integration Guide for TLF YAML Framework

## Project Overview

This is a **simplified plan-focused YAML framework** for generating clinical trial Tables, Listings, and Figures (TLFs). The framework directly follows the metalite R package pattern and is designed for biostatisticians and statistical programmers working on regulatory submissions.

### Key Features (Simplified Design)
- ✅ **Plan-focused approach**: Single YAML file per study
- ✅ **Direct metalite mapping**: 1:1 correspondence with metalite R syntax
- ✅ **Cartesian product expansion**: Condensed plans → multiple analyses
- ✅ **Clean YAML structure**: Uses consistent list format with `-`
- ✅ **No inheritance complexity**: Focused on practical analysis planning

## Quick Start for Claude

### Understanding the Repository
```bash
# Simplified project structure
demo-tlf-yaml/
├── src/tlfyaml/
│   └── simple_plan.py        # Core plan expansion logic
├── examples/yaml/
│   └── plan_xyz123.yaml      # Study analysis plan
└── SIMPLIFIED_DESIGN.md      # Design documentation
```

### Running the Demo
```bash
# Initialize environment
uv add pydantic pyyaml polars

# Test simplified approach
uv run python src/tlfyaml/simple_plan.py
```

## Core Concepts for Claude

### 1. Single Plan File Approach
The framework uses one YAML file per study that directly maps to metalite R patterns:

```yaml
# plan_xyz123.yaml - Complete study analysis plan
study:
  name: "XYZ123"
  title: "Phase III Study of Drug X vs Placebo"

data:
  subject: "data/adam_validate/adsl.parquet"
  observation: "data/adam_validate/adae.parquet"

plans:
  - analysis: "ae_summary"
    population: ["apat"]
    observation: ["wk12", "wk24"]
    parameter: "any;rel;ser"

  - analysis: "ae_specific"
    population: ["apat"]
    observation: ["wk12", "wk24"]
    parameter: ["any", "rel", "ser"]
```

### 2. Direct Metalite R Mapping
Perfect 1:1 correspondence between R and YAML:

```r
# Metalite R code
plan(analysis="ae_summary", population="apat",
     observation=c("wk12", "wk24"), parameter="any;rel;ser")
```

```yaml
# Equivalent YAML
- analysis: "ae_summary"
  population: ["apat"]
  observation: ["wk12", "wk24"]
  parameter: "any;rel;ser"
```

### 3. Cartesian Product Expansion
Both generate identical analysis combinations automatically:

```
ae_summary_apat_wk12_any
ae_summary_apat_wk12_rel
ae_summary_apat_wk12_ser
ae_summary_apat_wk24_any
ae_summary_apat_wk24_rel
ae_summary_apat_wk24_ser
```

## Clinical Context for Claude

### Understanding Clinical Data
- **ADaM datasets**: Analysis Data Model (CDISC standard)
  - `ADSL`: Subject-level data (demographics, treatments)
  - `ADAE`: Adverse events data
  - `ADVS`: Vital signs data
  - `ADTTE`: Time-to-event data

### Common Clinical Variables
```yaml
# Standard clinical variables Claude should recognize
USUBJID: "Unique Subject Identifier"
TRTA: "Actual Treatment Received"
TRTP: "Planned Treatment"
SAFFL: "Safety Population Flag"
ITTFL: "Intent-to-Treat Population Flag"
AESOC: "System Organ Class" (AE grouping)
AEDECOD: "Preferred Term" (specific AE)
AESER: "Serious Adverse Event Flag"
AEREL: "AE Relationship to Treatment"
```

### Regulatory Context
- **Safety tables**: Primary focus, following metalite.ae patterns
- **RTF output**: Standard for regulatory submissions
- **Population definitions**: Must be consistent across all analyses
- **Traceability**: Changes must propagate through inheritance

## Working with Claude

### When to Use This Framework
- Clinical trial TLF generation following metalite patterns
- Regulatory submission preparation
- Cartesian product analysis planning
- Safety/efficacy analysis automation
- Study-specific analysis specification

### Common Claude Tasks

#### 1. Adding New Analysis Plans
```yaml
# Add new plan to existing file
- analysis: "efficacy_primary"
  population: ["itt", "pp"]
  observation: ["week24", "eot"]
  parameter: ["endpoint1", "endpoint2"]
```

#### 2. Creating Study-Specific Plans
```yaml
# New study plan file
study:
  name: "ABC456"
  title: "Phase II Oncology Study"

plans:
  - analysis: "tumor_response"
    population: ["evaluable"]
    parameter: ["complete", "partial", "stable"]
```

#### 3. Expanding Analysis Coverage
```yaml
# Add new timepoints or parameters
- analysis: "ae_summary"
  population: ["apat"]
  observation: ["wk4", "wk8", "wk12", "wk16"]  # Expanded timepoints
  parameter: "any;rel;ser;sev"  # Added severity
```

### Claude Best Practices

#### 1. Configuration Validation
- Always test inheritance resolution after changes
- Verify filter syntax is valid SQL
- Check that referenced anchors exist
- Ensure required fields are present

#### 2. Clinical Accuracy
- Understand population definitions before modifying
- Validate filter logic with clinical team
- Follow CDISC ADaM conventions
- Maintain regulatory traceability

#### 3. Framework Extensions
- Use existing patterns when adding new features
- Maintain backward compatibility
- Document new anchor patterns
- Test with example data

## Advanced Patterns for Claude

### 1. Complex Template Inheritance
```yaml
# Base template
base_ae_template: &base_ae
  type: "table"
  data_source: "adae"
  population: "safety"
  group_by: ["TRTA"]

# Specialized templates
serious_ae_template: &serious_ae
  <<: *base_ae
  title: "Serious Adverse Events"
  filter: "AESER == 'Y'"

related_ae_template: &related_ae
  <<: *base_ae
  title: "Treatment-Related Adverse Events"
  filter: "AEREL IN ('POSSIBLE', 'PROBABLE', 'DEFINITE')"
```

### 2. Multi-Study Standardization
```yaml
# Organization-level standard
standard_safety_suite: &safety_suite
  ae_summary: *ae_summary_template
  ae_serious: *serious_ae_template
  ae_related: *related_ae_template

# Studies inherit complete suite
study_abc123:
  inherits_from: "ta_safety"
  tlfs: *safety_suite

study_def456:
  inherits_from: "ta_safety"
  tlfs: *safety_suite  # Same suite, guaranteed consistency
```

### 3. Dynamic Column Configurations
```yaml
# Reusable column sets
standard_ae_columns: &ae_cols
  - {name: "Subject", variable: "USUBJID", width: 12}
  - {name: "Treatment", variable: "TRTA", width: 20}
  - {name: "System Organ Class", variable: "AESOC", width: 25}

# Apply to multiple listings
serious_ae_listing:
  columns: *ae_cols

related_ae_listing:
  columns: *ae_cols
```

## Framework Status

### Phase 1 Complete ✅
- [x] Project structure and Pydantic models
- [x] YAML inheritance system
- [x] Example configurations
- [x] Basic TLF generation (placeholder RTF)
- [x] End-to-end demonstration

### Upcoming Phases
- **Phase 2**: SQL filter parsing and polars integration
- **Phase 3**: rtflite RTF generation
- **Phase 4**: Complete metalite.ae-style safety tables

## Resources for Claude

### Key Files to Reference
- `TLF_YAML_Framework_Design.md`: Complete technical specification
- `examples/yaml/`: Working configuration examples
- `src/tlfyaml/models/`: Pydantic model definitions
- `examples/demo.py`: End-to-end usage example

### Understanding the User's Goals
This framework is being developed for:
1. **Clinical biostatisticians**: Need efficient, standardized TLF generation
2. **Regulatory submissions**: Require consistent, traceable analysis
3. **Enterprise scale**: Multiple studies, therapeutic areas, organizations
4. **Platform flexibility**: Python now, potential R integration later

The design prioritizes **correctness**, **consistency**, and **regulatory compliance** over rapid development, reflecting the critical nature of clinical trial reporting.

### Working with the User
The user (elong0527) is an experienced biostatistician who:
- Understands CDISC standards and regulatory requirements
- Values well-architected, maintainable code
- Prefers design-first approach before implementation
- Wants production-ready frameworks, not quick demos

When helping with this project, focus on:
- Clinical accuracy and regulatory compliance
- Following established patterns and conventions
- Maintaining the hierarchical inheritance design
- Ensuring changes work across the entire framework