# AI Agents Guide for TLF YAML Framework

## Overview

This guide provides comprehensive instructions for AI agents working with the TLF (Tables, Listings, Figures) YAML Framework for clinical trial reporting. The framework generates regulatory submission documents using YAML configurations with keyword-driven templates and metalite R package patterns.

## Framework Architecture

### Design Philosophy
- **Proof of Concept**: Focus on demonstrating capabilities rather than production robustness
- **Self-Contained YAML**: Templates should be platform-agnostic (Python/R compatible)
- **SQL-Like Filtering**: Use SQL syntax for data filtering (translatable to polars/tidyverse)
- **Metalite Pattern**: Follow metalite.ae R package conventions directly
- **Template Inheritance**: Support organization → TA → study hierarchy


## Key Concepts for Agents

### 1. Clinical Trial Context

**Common Analysis Types:**
- **Demographics**: Baseline characteristics (`demographics`)
- **AE Summary**: Adverse event summary tables (`ae_summary`)
- **AE Specific**: Detailed AE analysis (`ae_specific`)
- **AE Listings**: Patient-level AE listings (`ae_listing`)

**Standard Parameters:**
- **any**: Any adverse event
- **rel**: Treatment-related adverse events
- **ser**: Serious adverse events

## Agent Guidelines

### 1. When Creating/Modifying Plans

**DO:**
- Use consistent list format with `-` for all plan items
- Include required `parameter` field (except for demographics)
- Follow metalite R syntax patterns exactly
- Use SQL-compatible filter expressions
- Add meaningful labels and descriptions for keywords
- Test plan expansion to verify expected analysis count
- Use semicolon format `"any;rel;ser"` for single parameter combinations
- Use list format `["any", "rel", "ser"]` for Cartesian product expansion

**DON'T:**
- Hard-code dataset names or variable names
- Create overly complex nested structures
- Mix different parameter combination formats
- Forget template references in study metadata
- Use non-SQL compatible filter syntax

### 2. Template Inheritance Patterns

**Organization Level** (Base templates):
```yaml
# Standard populations across all studies
population:
  - name: itt
    label: "Intention-to-Treat"
    filter: "adsl:ittfl == 'Y'"

# Common parameters
parameter:
  - name: any
    label: "Any Adverse Event"
    filter: "adae:trtemfl == 'Y'"
```

**Study Level** (References templates):
```yaml
study:
  template:
    - organization.yaml    # Base definitions
    - ta_oncology.yaml    # TA-specific (future)

# Study-specific overrides/additions
population:
  - name: biomarker_high
    label: "Biomarker High Expression"
    filter: "adsl:biomarker >= 50"
```

### 3. Plan Expansion Logic

**Understanding Cartesian Products:**
```yaml
# This plan:
- analysis: "ae_specific"
  population: ["apat"]           # 1 population
  observation: ["week12", "week24"]  # 2 observations
  parameter: ["any", "rel", "ser"]   # 3 parameters

# Generates: 1 × 2 × 3 = 6 individual analyses:
# ae_specific_apat_week12_any
# ae_specific_apat_week12_rel
# ae_specific_apat_week12_ser
# ae_specific_apat_week24_any
# ae_specific_apat_week24_rel
# ae_specific_apat_week24_ser
```

### 4. Output Requirements

**RTF Generation Focus:**
- Use rtflite for table generation (like metalite.ae)
- Support both summary tables and patient listings
- Generate regulatory-compliant formatting
- Extensible to other formats (HTML, PDF)

**Required Components:**
- **Tables**: Summary statistics with groupings
- **Listings**: Patient-level detailed data
- **Figures**: Plots and visualizations (future scope)

### 5. Error Handling & Validation

**Common Issues to Check:**
- Missing `parameter` field in plans (required except demographics)
- Invalid YAML syntax (especially list formatting)
- Circular template references
- SQL filter syntax errors
- Missing keyword definitions referenced in plans

**Validation Steps:**
1. Load plan file successfully
2. Resolve all template references
3. Validate all keyword references exist
4. Check SQL filter syntax
5. Verify plan expansion produces expected count

### 6. Code Management
**DO NOT:**
- Automatically stage modified files. Always confirm explicit instructions or run `git status` first.
- Automatically commit changes. Always await explicit instructions to commit, and propose a draft commit message for user review.

## Working with the Framework

### Loading and Testing Plans
```python
from src.tlfyaml.enhanced_plan import EnhancedPlanLoader

# Load plan with template inheritance
loader = EnhancedPlanLoader('examples/yaml')
summary = loader.expand('plan_xyz123.yaml')

# Check expansion results
print(f"Plans: {summary['condensed_plans']} → {summary['individual_analyses']} analyses")

# Examine keyword resolution
for analysis in summary['analyses'][:3]:
    print(f"Analysis: {analysis['id']}")
    print(f"Title: {analysis['title']}")
    print(f"Population Filter: {analysis['population']['filter']}")
```

### Creating New Analysis Types
```yaml
# Add new analysis type to plans
- analysis: "conmed_summary"
  population: "safety"
  observation: "baseline"
  group: "trt01a"
  parameter: "any_conmed"

# Define corresponding parameter
parameter:
  - name: any_conmed
    label: "Any Concomitant Medication"
    filter: "adcm:cmoccur == 'Y'"
```

## Best Practices for Agents

### 1. Clinical Accuracy
- Understand regulatory requirements for TLF content
- Use appropriate population definitions for analysis type
- Ensure treatment-emergent logic for safety analyses
- Follow standard adverse event classification

### 2. Template Design
- Create reusable organization-wide keyword definitions
- Use descriptive labels for all keywords
- Document complex filter logic clearly
- Maintain consistency across similar analyses

### 3. Plan Optimization
- Group related analyses efficiently
- Use appropriate parameter combination formats
- Minimize duplication through smart keyword reuse
- Test with realistic data scenarios

### 4. Documentation Standards
- Include clear descriptions for all custom keywords
- Document any non-standard filter logic
- Explain study-specific population definitions
- Provide examples for complex analysis patterns

## Advanced Patterns

### Biomarker Subgroup Analysis
```yaml
# Biomarker-stratified efficacy
- analysis: "efficacy_by_biomarker"
  population: ["biomarker_high", "biomarker_low"]
  observation: "week12"
  group: "trt01a"
  parameter: "response"
```

### Time-to-Event Analysis
```yaml
# Survival analysis
- analysis: "survival_analysis"
  population: "itt"
  observation: "final"
  group: "trt01a"
  parameter: ["os", "pfs"]
```

### Safety Monitoring
```yaml
# Comprehensive safety package
- analysis: "ae_summary"
  population: "safety"
  observation: ["week12", "week24", "eot"]
  group: "trt01a"
  parameter: "any;rel;ser;grade3;grade4"
```

## Framework Evolution

The framework is designed to evolve from this proof-of-concept to support:
- Multiple therapeutic areas with TA-specific templates
- Extended output formats beyond RTF
- Custom analysis type definitions
- Integration with clinical data pipelines
- R language compatibility through shared YAML specifications

This guide provides the foundation for agents to work effectively with the TLF YAML Framework while maintaining clinical accuracy and regulatory compliance.