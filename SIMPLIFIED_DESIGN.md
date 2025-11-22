# Simplified TLF YAML Design - Plan-Focused

## Core Principle: Plan-Only Approach

Focus entirely on the plan YAML file following the metalite pattern. Eliminate complex inheritance and mock systems.

## Single File Structure: `plan_xyz123.yaml`

```yaml
# Study XYZ123 - Analysis Plan
study:
  name: "XYZ123"
  title: "Phase III Study of Drug X vs Placebo"

# Data sources (simplified)
data:
  subject: "data/adam_validate/adsl.parquet"
  observation: "data/adam_validate/adae.parquet"

# Analysis Plans - Direct metalite mapping
plans:
  # Demographics
  - analysis: "demographics"
    population: ["itt"]

  # AE Summary tables
  - analysis: "ae_summary"
    population: ["apat"]
    observation: ["wk12", "wk24"]
    parameter: "any;rel;ser"

  # AE Specific analysis
  - analysis: "ae_specific"
    population: ["apat"]
    observation: ["wk12", "wk24"]
    parameter: ["any", "rel", "ser"]

  # AE Listings
  - analysis: "ae_listing"
    population: ["apat"]
    observation: ["wk12"]
    parameter: ["any", "rel", "ser"]
```

## Key Simplifications

### ✅ **What's Included**
- **Single plan file per study**
- **Direct metalite pattern mapping**
- **Cartesian product generation**
- **Minimal configuration overhead**

### ❌ **What's Eliminated**
- Complex inheritance (org → ta → study)
- Separate mock template files
- YAML anchors and references
- Multiple configuration layers
- Therapeutic area abstractions

## Benefits

1. **Simplicity**: One file contains everything needed for a study
2. **Clarity**: Direct correspondence to metalite R syntax
3. **Maintainability**: Easy to understand and modify
4. **Focus**: Purely on analysis planning, not framework complexity
5. **Efficiency**: 4 plan specs → 22 individual analyses

## Implementation Focus

- **Plan expansion logic**: Convert condensed plans to individual analyses
- **Cartesian product generation**: Handle lists and semicolon syntax
- **Direct execution**: From plan to TLF generation
- **No inheritance resolution**: Just parse and expand plans

This approach prioritizes practical clinical analysis needs over architectural complexity.