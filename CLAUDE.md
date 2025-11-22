# Claude Integration Guide for TLF YAML Framework

## Project Overview

This is a proof-of-concept **hierarchical YAML-based framework** for generating clinical trial Tables, Listings, and Figures (TLFs). The framework is designed for biostatisticians and statistical programmers working on regulatory submissions.

### Key Features
- ✅ **Hierarchical inheritance**: Organization → Therapeutic Area → Study
- ✅ **Metadata-driven**: No hard-coded assumptions
- ✅ **Self-contained YAML**: Platform-agnostic SQL-like filters
- ✅ **Anchor-based reusability**: DRY principle implementation
- ✅ **Production-ready structure**: Follows metalite R package principles

## Quick Start for Claude

### Understanding the Repository
```bash
# Project structure
demo-tlf-yaml/
├── src/tlfyaml/              # Core framework
├── examples/yaml/            # Configuration examples
├── examples/demo.py          # Working demonstration
└── TLF_YAML_Framework_Design.md  # Complete design document
```

### Running the Demo
```bash
# Initialize environment
uv add pydantic pyyaml polars pytest

# Run demonstration
uv run python examples/demo.py
```

## Core Concepts for Claude

### 1. Inheritance Hierarchy
The framework uses a three-level inheritance system inspired by enterprise clinical operations:

```yaml
# org_common.yaml (Organization level)
common_populations: &common_populations
  safety:
    name: "SAFFL"
    label: "Safety Population Flag"
    filter: "SAFFL == 'Y'"

# ta_safety.yaml (Therapeutic Area level)
inherits_from: "org_common"
populations:
  safety_evaluable:
    name: "SAFEVAL"
    label: "Safety Evaluable Population"
    filter: "SAFFL == 'Y' AND DTHFL != 'Y'"

# study_xyz123.yaml (Study level)
inherits_from: "ta_safety"
data_sources:
  adae:
    name: "adae"
    path: "data/adam_validate/adae.parquet"
    source: "ADAE"
```

### 2. YAML Anchors for Clinical Templates
Anchors (`&`) and references (`*`) eliminate duplication and ensure consistency:

```yaml
# Define once
control: &control
  name: "Placebo"
  variable: "TRTA"
  filter: "TRTA == 'Placebo'"

# Use everywhere
ae_summary:
  treatments: [*control, *active]

demographics:
  treatments: [*control, *active]  # Same definition guaranteed
```

### 3. SQL-like Filtering for Platform Agnosticism
Filter expressions work with Python (polars), R (dplyr), and SQL:

```yaml
population:
  safety:
    filter: "SAFFL == 'Y' AND TRTEMFL == 'Y'"
    # Python/polars: df.filter((pl.col("SAFFL") == "Y") & (pl.col("TRTEMFL") == "Y"))
    # R/dplyr: filter(SAFFL == "Y" & TRTEMFL == "Y")
    # SQL: WHERE SAFFL = 'Y' AND TRTEMFL = 'Y'
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
- Clinical trial TLF generation
- Regulatory submission preparation
- Cross-study standardization
- Safety analysis automation
- Efficacy endpoint reporting

### Common Claude Tasks

#### 1. Adding New TLF Specifications
```yaml
# Add to study YAML
new_efficacy_table:
  type: "table"
  title: "Primary Efficacy Analysis"
  data_source: "adeff"
  population: "itt"
  group_by: ["TRTA"]
  summary_vars: ["PRIMARY_ENDPOINT"]
  output:
    filename: "t_efficacy_primary.rtf"
```

#### 2. Creating Therapeutic Area Templates
```yaml
# In ta_oncology.yaml
oncology_parameters:
  tumor_response: &tumor_resp
    name: "TUMOR_RESP"
    label: "Tumor Response"
    filter: "EVALFL == 'Y'"

efficacy_template: &eff_template
  type: "table"
  data_source: "adrs"
  population: *tumor_resp
```

#### 3. Study-Specific Customizations
```yaml
# Override inherited definitions
populations:
  modified_safety:
    name: "MSAFFL"
    label: "Modified Safety Population"
    filter: "SAFFL == 'Y' AND TRTSDT IS NOT NULL AND AGE >= 18"
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