"""
Adverse Event (AE) Analysis Functions

This module provides three core functions for AE analysis following metalite.ae patterns:
- ae_summary: Summary tables with counts/percentages by treatment group
- ae_specific: Specific AE analysis with SOC/PT hierarchical breakdown
- ae_listing: Patient-level AE listings with detailed information

Uses Polars native SQL capabilities for data manipulation.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import polars as pl

from .plan import StudyPlan


def parse_filter_to_sql(filter_str: str) -> str:
    """
    Parse custom filter syntax to SQL WHERE clause.

    Converts:
    - "adsl:saffl == 'Y'" -> "SAFFL = 'Y'"
    - "adae:trtemfl == 'Y' and adae:aeser == 'Y'" -> "TRTEMFL = 'Y' AND AESER = 'Y'"
    - "adae:aerel in ['A', 'B']" -> "AEREL IN ('A', 'B')"

    Args:
        filter_str: Custom filter string with dataset:column format

    Returns:
        SQL WHERE clause string
    """
    if not filter_str or filter_str.strip() == "":
        return "1=1"  # Always true

    # Remove dataset prefixes (adsl:, adae:)
    sql = re.sub(r"\w+:", "", filter_str)

    # Convert Python syntax to SQL
    sql = sql.replace("==", "=")  # Python equality to SQL
    sql = sql.replace(" and ", " AND ")  # Python to SQL
    sql = sql.replace(" or ", " OR ")  # Python to SQL

    # Convert Python list syntax to SQL IN: ['A', 'B'] -> ('A', 'B')
    sql = sql.replace("[", "(").replace("]", ")")

    # Uppercase column names (assuming ADaM standard)
    # Match word boundaries before operators
    sql = re.sub(
        r"\b([a-z]\w*)\b(?=\s*[=<>!]|\s+IN)", lambda m: m.group(1).upper(), sql, flags=re.IGNORECASE
    )

    return sql


def apply_filter_sql(df: pl.DataFrame, filter_str: str, table_name: str = "t") -> pl.DataFrame:
    """
    Apply filter using pl.sql_expr() - simpler and faster than SQLContext.

    Args:
        df: DataFrame to filter
        filter_str: Custom filter string
        table_name: Table alias (unused, kept for backward compatibility)

    Returns:
        Filtered DataFrame
    """
    if not filter_str or filter_str.strip() == "":
        return df

    where_clause = parse_filter_to_sql(filter_str)

    try:
        # Use pl.sql_expr() - much simpler and faster!
        return df.filter(pl.sql_expr(where_clause))
    except Exception as e:
        # Fallback to manual parsing if SQL fails
        print(f"Warning: SQL filter failed ({e}), using fallback method")
        return df.filter(_parse_filter_expr(filter_str))


def _parse_filter_expr(filter_str: str) -> Any:
    """
    Fallback filter parser using Polars expressions.
    Used if SQL parsing fails.

    Args:
        filter_str: Filter string

    Returns:
        Polars expression
    """
    if not filter_str or filter_str.strip() == "":
        return pl.lit(True)

    # Remove dataset prefixes
    filter_str = re.sub(r"\w+:", "", filter_str)

    # Handle 'in' operator: column in ['A', 'B'] -> pl.col(column).is_in(['A', 'B'])
    in_pattern = r"(\w+)\s+in\s+\[([^\]]+)\]"

    def replace_in(match: re.Match) -> str:
        col = match.group(1).upper()
        values = match.group(2)
        return f"(pl.col('{col}').is_in([{values}]))"

    filter_str = re.sub(in_pattern, replace_in, filter_str)

    # Handle equality/inequality
    eq_pattern = r"(\w+)\s*(==|!=|>|<|>=|<=)\s*'([^']+)'"

    def replace_eq(match: re.Match) -> str:
        col = match.group(1).upper()
        op = match.group(2)
        val = match.group(3)
        return f"(pl.col('{col}') {op} '{val}')"

    filter_str = re.sub(eq_pattern, replace_eq, filter_str)

    # Replace 'and'/'or'
    filter_str = filter_str.replace(" and ", " & ")
    filter_str = filter_str.replace(" or ", " | ")

    return eval(filter_str)


def parse_parameter(parameter_str: str) -> List[str]:
    """
    Parse semicolon-separated parameter string.

    Args:
        parameter_str: Single parameter or semicolon-separated (e.g., "any;rel;ser")

    Returns:
        List of parameter names
    """
    if not parameter_str:
        return []
    if ";" in parameter_str:
        return [p.strip() for p in parameter_str.split(";")]
    return [parameter_str]


def get_population_data(
    study_plan: StudyPlan, population: str, group: str
) -> Tuple[pl.DataFrame, pl.DataFrame]:
    """
    Get population dataset and denominator counts by group using pl.sql_expr().

    Args:
        study_plan: StudyPlan object with loaded datasets
        population: Population keyword name
        group: Group keyword name

    Returns:
        Tuple of (population dataframe, denominator dataframe)
    """
    # Get ADSL dataset
    adsl = study_plan.datasets.get("adsl")
    if adsl is None:
        raise ValueError("ADSL dataset not found in study plan")

    # Get population filter
    pop = study_plan.keywords.get_population(population)
    if pop is None:
        raise ValueError(f"Population '{population}' not found")

    # Apply population filter using pl.sql_expr()
    adsl_pop = apply_filter_sql(adsl, pop.filter)

    # Get group variable
    grp = study_plan.keywords.get_group(group)
    if grp is None:
        raise ValueError(f"Group '{group}' not found")

    group_var = grp.variable.split(":")[-1].upper()

    # Calculate denominators using simple group_by
    n_pop = adsl_pop.group_by(group_var).agg(pl.count().alias("n")).sort(group_var)

    return adsl_pop, n_pop


def ae_summary_core(
    adsl: pl.DataFrame,
    adae: pl.DataFrame,
    population_filter: str,
    parameter_filters: List[str],
    observation_filter: Optional[str] = None,
    group_var: str = "TRT01A",
    parameter_labels: Optional[List[str]] = None,
    group_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Core AE summary function - decoupled from StudyPlan.

    Generates summary statistics showing the number and percentage
    of subjects experiencing adverse events, organized hierarchically by
    System Organ Class (SOC) and Preferred Term (PT).

    Args:
        adsl: ADSL DataFrame (subject-level data)
        adae: ADAE DataFrame (adverse event data)
        population_filter: SQL WHERE clause for population (e.g., "SAFFL = 'Y'")
        parameter_filters: List of SQL WHERE clauses for parameters
        observation_filter: Optional SQL WHERE clause for observation
        group_var: Treatment group variable name (default: "TRT01A")
        parameter_labels: Optional labels for parameters
        group_labels: Optional labels for treatment groups

    Returns:
        Dictionary containing:
        - meta: Analysis metadata
        - n_pop: Population denominators by group
        - summary: Summary statistics with SOC/PT hierarchy
        - group_labels: Treatment group labels

    Example:
        >>> result = ae_summary_core(
        ...     adsl=adsl_df,
        ...     adae=adae_df,
        ...     population_filter="SAFFL = 'Y'",
        ...     parameter_filters=["TRTEMFL = 'Y'"],
        ...     group_var="TRT01A"
        ... )
    """
    # Apply population filter using pl.sql_expr()
    # Apply population filter using pl.sql_expr()
    adsl_pop = adsl.filter(pl.sql_expr(population_filter))

    # Calculate denominators using simple group_by (no SQL needed!)
    n_pop = adsl_pop.group_by(group_var).agg(pl.len().alias("n")).sort(group_var)

    # Build combined filter expression
    filter_expr = pl.lit(True)

    # Add parameter filters with OR logic
    if parameter_filters:
        param_conditions = [f"({pf})" for pf in parameter_filters]
        param_sql = f"({' OR '.join(param_conditions)})"
        filter_expr = filter_expr & pl.sql_expr(param_sql)

    # Add observation filter with AND logic
    if observation_filter:
        filter_expr = filter_expr & pl.sql_expr(observation_filter)

    # Apply all filters at once
    ae_filtered = adae.filter(filter_expr)

    # Filter to population subjects
    pop_subjects = adsl_pop.select("USUBJID")
    ae_filtered = ae_filtered.join(pop_subjects, on="USUBJID", how="inner")

    # Merge treatment group from ADSL
    ae_with_trt = ae_filtered.join(
        adsl_pop.select(["USUBJID", group_var]), on="USUBJID", how="left"
    )

    # Calculate SOC-level counts
    soc_summary = (
        ae_with_trt.filter(pl.col("AOCCSFL") == "Y")
        .group_by([group_var, "AESOC"])
        .agg(pl.n_unique("USUBJID").alias("n_subj"))
        .join(n_pop, on=group_var)
        .with_columns(
            [
                (pl.col("n_subj") / pl.col("n") * 100).round(1).alias("pct"),
                pl.lit("SOC").alias("level"),
                pl.lit("").alias("AEDECOD"),
            ]
        )
        .rename({"AESOC": "term"})
        .select([group_var, "level", "term", "AEDECOD", "n_subj", "n", "pct"])
    )

    # Calculate PT-level counts
    pt_summary = (
        ae_with_trt.filter(pl.col("AOCCPFL") == "Y")
        .group_by([group_var, "AESOC", "AEDECOD"])
        .agg(pl.n_unique("USUBJID").alias("n_subj"))
        .join(n_pop, on=group_var)
        .with_columns(
            [
                (pl.col("n_subj") / pl.col("n") * 100).round(1).alias("pct"),
                pl.lit("PT").alias("level"),
            ]
        )
        .rename({"AESOC": "term", "AEDECOD": "AEDECOD"})
        .select([group_var, "level", "term", "AEDECOD", "n_subj", "n", "pct"])
    )

    # Combine and sort
    summary = pl.concat([soc_summary, pt_summary])
    summary = (
        summary.with_columns(
            [
                pl.col("n_subj").sum().over(["term", group_var]).alias("soc_total"),
                pl.col("n_subj").sum().over(["AEDECOD", group_var]).alias("pt_total"),
            ]
        )
        .sort(
            [
                pl.col("soc_total").max().over("term"),
                "term",
                "level",
                pl.col("pt_total").max().over("AEDECOD"),
            ],
            descending=[True, False, False, True],
        )
        .drop(["soc_total", "pt_total"])
    )

    return {
        "meta": {
            "analysis": "ae_summary",
            "parameter_filters": parameter_filters,
            "parameter_labels": parameter_labels or [],
            "observation_filter": observation_filter,
            "group_var": group_var,
        },
        "n_pop": n_pop,
        "summary": summary,
        "group_labels": group_labels or [],
    }


def ae_summary(
    study_plan: StudyPlan,
    population: str,
    observation: Optional[str] = None,
    parameter: str = "any",
    group: str = "trt01a",
) -> Dict[str, Any]:
    """
    Wrapper function for ae_summary_core with StudyPlan integration.

    This function extracts configuration from StudyPlan and calls ae_summary_core.
    Use ae_summary_core() directly if you don't have a StudyPlan object.

    Args:
        study_plan: StudyPlan object with loaded datasets and keywords
        population: Population keyword name (e.g., "apat", "itt")
        observation: Optional observation keyword for timepoint filtering
        parameter: Parameter keyword, can be semicolon-separated (e.g., "any;rel;ser")
        group: Group keyword name for treatment grouping

    Returns:
        Dictionary containing:
        - meta: Analysis metadata
        - n_pop: Population denominators by group
        - summary: Summary statistics with SOC/PT hierarchy
        - group_labels: Treatment group labels
    """
    # Get datasets
    adsl = study_plan.datasets.get("adsl")
    adae = study_plan.datasets.get("adae")
    if adsl is None or adae is None:
        raise ValueError("ADSL and ADAE datasets required")

    # Get population filter
    pop = study_plan.keywords.get_population(population)
    if pop is None:
        raise ValueError(f"Population '{population}' not found")
    population_filter = parse_filter_to_sql(pop.filter)

    # Get group variable
    grp = study_plan.keywords.get_group(group)
    if grp is None:
        raise ValueError(f"Group '{group}' not found")
    group_var = grp.variable.split(":")[-1].upper()
    group_labels = grp.group_label

    # Parse parameters and get filters
    param_names = parse_parameter(parameter)
    param_labels = []
    param_filters = []
    for param_name in param_names:
        param = study_plan.keywords.get_parameter(param_name)
        if param is None:
            raise ValueError(f"Parameter '{param_name}' not found")
        param_filters.append(parse_filter_to_sql(param.filter))
        param_labels.append(param.label or param_name)

    # Get observation filter
    obs_filter = None
    if observation:
        obs = study_plan.keywords.get_observation(observation)
        if obs:
            obs_filter = parse_filter_to_sql(obs.filter)

    # Call core function
    result = ae_summary_core(
        adsl=adsl,
        adae=adae,
        population_filter=population_filter,
        parameter_filters=param_filters,
        observation_filter=obs_filter,
        group_var=group_var,
        parameter_labels=param_labels,
        group_labels=group_labels,
    )

    # Add StudyPlan-specific metadata
    result["meta"].update(
        {
            "population": population,
            "observation": observation,
            "parameter": param_names,
            "group": group,
        }
    )

    return result


def ae_specific_core(
    adsl: pl.DataFrame,
    adae: pl.DataFrame,
    population_filter: str,
    parameter_filter: str,
    observation_filter: Optional[str] = None,
    group_var: str = "TRT01A",
    parameter_label: Optional[str] = None,
    components: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Core AE specific analysis function - decoupled from StudyPlan.

    Generates specific AE analysis with SOC/PT hierarchical breakdown
    and optional severity stratification.

    Args:
        adsl: ADSL DataFrame
        adae: ADAE DataFrame
        population_filter: SQL WHERE clause for population
        parameter_filter: SQL WHERE clause for parameter (single, NOT list)
        observation_filter: Optional SQL WHERE clause for observation
        group_var: Treatment group variable name
        parameter_label: Optional label for parameter
        group_labels: Optional labels for treatment groups
        components: Analysis components, default ["soc", "pt"]

    Returns:
        Dictionary with analysis results

    Example:
        >>> result = ae_specific_core(
        ...     adsl=adsl_df,
        ...     adae=adae_df,
        ...     population_filter="SAFFL = 'Y'",
        ...     parameter_filter="TRTEMFL = 'Y'",
        ...     group_var="TRT01A"
        ... )
    """
    if components is None:
        components = ["soc", "pt"]

    # Apply population filter
    adsl_pop = adsl.filter(pl.sql_expr(population_filter))

    # Calculate denominators
    n_pop = adsl_pop.group_by(group_var).agg(pl.len().alias("n")).sort(group_var)

    # Build filter expression
    filter_expr = pl.sql_expr(parameter_filter)
    if observation_filter:
        filter_expr = filter_expr & pl.sql_expr(observation_filter)

    # Apply filters
    ae_filtered = adae.filter(filter_expr)

    # Filter to population subjects and merge treatment
    pop_subjects = adsl_pop.select("USUBJID")
    ae_filtered = ae_filtered.join(pop_subjects, on="USUBJID", how="inner")

    ae_with_trt = ae_filtered.join(
        adsl_pop.select(["USUBJID", group_var]), on="USUBJID", how="left"
    )

    # Calculate SOC-level counts
    soc_summary = (
        ae_with_trt.filter(pl.col("AOCCSFL") == "Y")
        .group_by([group_var, "AESOC"])
        .agg(pl.n_unique("USUBJID").alias("n_subj"))
        .join(n_pop, on=group_var)
        .with_columns(
            [
                (pl.col("n_subj") / pl.col("n") * 100).round(1).alias("pct"),
                pl.lit("SOC").alias("level"),
                pl.lit("").alias("AEDECOD"),
            ]
        )
        .rename({"AESOC": "term"})
        .select([group_var, "level", "term", "AEDECOD", "n_subj", "n", "pct"])
    )

    # Calculate PT-level counts
    pt_summary = (
        ae_with_trt.filter(pl.col("AOCCPFL") == "Y")
        .group_by([group_var, "AESOC", "AEDECOD"])
        .agg(pl.n_unique("USUBJID").alias("n_subj"))
        .join(n_pop, on=group_var)
        .with_columns(
            [
                (pl.col("n_subj") / pl.col("n") * 100).round(1).alias("pct"),
                pl.lit("PT").alias("level"),
            ]
        )
        .rename({"AESOC": "term", "AEDECOD": "AEDECOD"})
        .select([group_var, "level", "term", "AEDECOD", "n_subj", "n", "pct"])
    )

    # Combine and sort
    summary = pl.concat([soc_summary, pt_summary])
    summary = (
        summary.with_columns(
            [
                pl.col("n_subj").sum().over(["term", group_var]).alias("soc_total"),
                pl.col("n_subj").sum().over(["AEDECOD", group_var]).alias("pt_total"),
            ]
        )
        .sort(
            [
                pl.col("soc_total").max().over("term"),
                "term",
                "level",
                pl.col("pt_total").max().over("AEDECOD"),
            ],
            descending=[True, False, False, True],
        )
        .drop(["soc_total", "pt_total"])
    )

    # Add severity breakdown
    severity_breakdown = None
    if "AESEV" in ae_with_trt.columns:
        severity_breakdown = (
            ae_with_trt.group_by([group_var, "AEDECOD", "AESEV"])
            .agg(pl.n_unique("USUBJID").alias("n_subj"))
            .pivot(index=[group_var, "AEDECOD"], on="AESEV", values="n_subj")
        )

    return {
        "meta": {
            "analysis": "ae_specific",
            "parameter_filter": parameter_filter,
            "parameter_label": parameter_label,
            "observation_filter": observation_filter,
            "group_var": group_var,
            "components": components,
        },
        "n_pop": n_pop,
        "summary": summary,
        "severity": severity_breakdown,
    }


def ae_specific(
    study_plan: StudyPlan,
    population: str,
    observation: Optional[str] = None,
    parameter: str = "any",
    group: str = "trt01a",
    components: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Prepare specific AE analysis with SOC/PT hierarchical breakdown.

    Similar to ae_summary but includes additional clinical context like
    severity and relationship to treatment.

    Args:
        study_plan: StudyPlan object with loaded datasets and keywords
        population: Population keyword name
        observation: Optional observation keyword
        parameter: Single parameter keyword (NOT semicolon-separated)
        group: Group keyword name
        components: Analysis components, default ["soc", "pt"]

    Returns:
        Dictionary containing:
        - meta: Analysis metadata
        - n_pop: Population denominators
        - summary: Detailed SOC/PT breakdown with clinical context
        - severity: Optional severity breakdown
        - group_labels: Treatment group labels
    """
    if components is None:
        components = ["soc", "pt"]

    # Get DataFrames from StudyPlan
    adsl = study_plan.datasets.get("adsl")
    if adsl is None:
        raise ValueError("ADSL dataset not found")

    adae = study_plan.datasets.get("adae")
    if adae is None:
        raise ValueError("ADAE dataset not found")

    # Get group configuration
    grp = study_plan.keywords.get_group(group)
    if grp is None:
        raise ValueError(f"Group '{group}' not found")
    group_var = grp.variable.split(":")[-1].upper()

    # Get population filter
    pop = study_plan.keywords.get_population(population)
    if pop is None:
        raise ValueError(f"Population '{population}' not found")
    population_filter = parse_filter_to_sql(pop.filter)

    # Get parameter filter (single, not semicolon-separated)
    param = study_plan.keywords.get_parameter(parameter)
    if param is None:
        raise ValueError(f"Parameter '{parameter}' not found")
    parameter_filter = parse_filter_to_sql(param.filter)

    # Get observation filter if specified
    observation_filter = None
    if observation:
        obs = study_plan.keywords.get_observation(observation)
        if obs:
            observation_filter = parse_filter_to_sql(obs.filter)

    # Call core function
    result = ae_specific_core(
        adsl=adsl,
        adae=adae,
        population_filter=population_filter,
        parameter_filter=parameter_filter,
        observation_filter=observation_filter,
        group_var=group_var,
        parameter_label=param.label,
        components=components,
    )

    # Add StudyPlan-specific metadata
    result["meta"].update(
        {
            "population": population,
            "observation": observation,
            "parameter": parameter,
            "group": group,
        }
    )

    return result


def ae_listing_core(
    adsl: pl.DataFrame,
    adae: pl.DataFrame,
    population_filter: str,
    parameter_filter: str,
    observation_filter: Optional[str] = None,
    sort_by: Optional[List[str]] = None,
    columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Core AE listing function - decoupled from StudyPlan.

    Generates patient-level AE listings with demographics and clinical details.

    Args:
        adsl: ADSL DataFrame
        adae: ADAE DataFrame
        population_filter: SQL WHERE clause for population
        parameter_filter: SQL WHERE clause for parameter
        observation_filter: Optional SQL WHERE clause for observation
        sort_by: Sort columns, default ["TRTA", "USUBJID", "ASTDY", "AESEQ"]
        columns: Optional list of columns to include in listing

    Returns:
        Dictionary with listing results

    Example:
        >>> result = ae_listing_core(
        ...     adsl=adsl_df,
        ...     adae=adae_df,
        ...     population_filter="SAFFL = 'Y'",
        ...     parameter_filter="AESER = 'Y'",
        ...     sort_by=["TRTA", "USUBJID", "ASTDY"]
        ... )
    """
    if sort_by is None:
        sort_by = ["TRTA", "USUBJID", "ASTDY", "AESEQ"]

    # Apply population filter
    adsl_pop = adsl.filter(pl.sql_expr(population_filter))

    # Build filter expression for AE
    filter_expr = pl.sql_expr(parameter_filter)
    if observation_filter:
        filter_expr = filter_expr & pl.sql_expr(observation_filter)

    # Apply filters
    ae_filtered = adae.filter(filter_expr)

    # Filter to population subjects
    pop_subjects = adsl_pop.select("USUBJID")
    ae_filtered = ae_filtered.join(pop_subjects, on="USUBJID", how="inner")

    # Merge demographics from ADSL
    demo_cols = ["USUBJID", "AGE", "SEX", "RACE", "TRTA"]
    adsl_demo = adsl_pop.select([c for c in demo_cols if c in adsl_pop.columns])

    listing = ae_filtered.join(adsl_demo, on="USUBJID", how="left")

    # Select columns
    if columns is None:
        listing_cols = [
            "USUBJID",
            "AGE",
            "SEX",
            "RACE",
            "TRTA",
            "AETERM",
            "AEDECOD",
            "AESOC",
            "ASTDY",
            "AENDY",
            "ADURN",
            "AESEV",
            "AESER",
            "AEREL",
            "AEACN",
            "AEOUT",
        ]
    else:
        listing_cols = columns

    # Keep only columns that exist
    listing_cols = [c for c in listing_cols if c in listing.columns]
    listing = listing.select(listing_cols)

    # Sort
    sort_cols = [c for c in sort_by if c in listing.columns]
    if sort_cols:
        listing = listing.sort(sort_cols)

    return {
        "meta": {
            "analysis": "ae_listing",
            "population_filter": population_filter,
            "parameter_filter": parameter_filter,
            "observation_filter": observation_filter,
        },
        "listing": listing,
    }


def ae_listing(
    study_plan: StudyPlan,
    population: str,
    observation: Optional[str] = None,
    parameter: str = "any",
    sort_by: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Prepare patient-level AE listing with detailed information.

    Merges ADSL demographics with ADAE adverse event data to provide
    comprehensive patient-level listings for clinical review.

    Args:
        study_plan: StudyPlan object with loaded datasets and keywords
        population: Population keyword name
        observation: Optional observation keyword
        parameter: Parameter keyword
        sort_by: Sort columns, default ["TRTA", "USUBJID", "ASTDY", "AESEQ"]

    Returns:
        Dictionary containing:
        - meta: Analysis metadata
        - listing: Patient-level AE dataframe
        - column_labels: Readable column labels
    """
    # Get datasets
    adsl = study_plan.datasets.get("adsl")
    adae = study_plan.datasets.get("adae")
    if adsl is None or adae is None:
        raise ValueError("ADSL and ADAE datasets must be loaded")

    # Get population filter
    pop = study_plan.keywords.get_population(population)
    if pop is None:
        raise ValueError(f"Population '{population}' not found")
    population_filter = parse_filter_to_sql(pop.filter)

    # Get parameter filter
    param = study_plan.keywords.get_parameter(parameter)
    if param is None:
        raise ValueError(f"Parameter '{parameter}' not found")
    parameter_filter = parse_filter_to_sql(param.filter)

    # Get observation filter
    observation_filter = None
    if observation:
        obs = study_plan.keywords.get_observation(observation)
        if obs:
            observation_filter = parse_filter_to_sql(obs.filter)

    # Call core function
    result = ae_listing_core(
        adsl=adsl,
        adae=adae,
        population_filter=population_filter,
        parameter_filter=parameter_filter,
        observation_filter=observation_filter,
        sort_by=sort_by,
    )

    # Column labels for display
    column_labels = {
        "USUBJID": "Subject ID",
        "AGE": "Age",
        "SEX": "Sex",
        "RACE": "Race",
        "TRTA": "Treatment",
        "AETERM": "Reported Term",
        "AEDECOD": "Preferred Term",
        "AESOC": "System Organ Class",
        "ASTDY": "Start Day",
        "AENDY": "End Day",
        "ADURN": "Duration (days)",
        "AESEV": "Severity",
        "AESER": "Serious",
        "AEREL": "Relationship",
        "AEACN": "Action Taken",
        "AEOUT": "Outcome",
    }

    # Add StudyPlan-specific metadata
    result["meta"].update(
        {"population": population, "observation": observation, "parameter": parameter}
    )
    result["column_labels"] = column_labels

    return result
