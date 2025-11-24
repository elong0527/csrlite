"""
Adverse Event (AE) Analysis Functions

This module provides core function for AE summary analysis following metalite.ae patterns:
- ae_summary: Summary tables with counts/percentages by treatment group

Uses Polars native SQL capabilities for data manipulation, count.py utilities for subject counting,
and parse.py utilities for StudyPlan parsing.
"""

from typing import Any

import polars as pl

try:
    from rtflite import RTFBody, RTFColumnHeader, RTFDocument, RTFSource, RTFTitle
    RTFLITE_AVAILABLE = True
except ImportError:
    RTFLITE_AVAILABLE = False

from .plan import StudyPlan
from .count import count_subject
from .parse import StudyPlanParser


def ae_summary_core(
    population: pl.DataFrame,
    observation: pl.DataFrame,
    population_filter: str | None,
    observation_filter: str | None,
    group: tuple[str, str],
    variables: list[tuple[str, str]],
) -> dict[str, Any]:
    """
    Core AE summary function - decoupled from StudyPlan.

    Generates summary statistics showing the number and percentage
    of subjects experiencing adverse events, organized hierarchically by
    System Organ Class (SOC) and Preferred Term (PT).

    Args:
        population: Population DataFrame (subject-level data, e.g., ADSL)
        observation: Observation DataFrame (event data, e.g., ADAE)
        population_filter: SQL WHERE clause for population (can be None)
        observation_filter: SQL WHERE clause for observation (can be None)
        group: Tuple (variable_name, label) for grouping variable
        variables: List of tuples [(filter, label)] for analysis variables

    Returns:
        Dictionary containing:
        - meta: Analysis metadata
        - n_pop: Population denominators by group
        - summary: Summary statistics with SOC/PT hierarchy

    Example:
        >>> result = ae_summary_core(
        ...     population=adsl_df,
        ...     observation=adae_df,
        ...     population_filter="SAFFL = 'Y'",
        ...     observation_filter=None,
        ...     group=("TRT01A", "Treatment Group"),
        ...     variables=[("TRTEMFL = 'Y'", "Any AE")]
        ... )
    """
    # Extract group variable name (label is in tuple but not needed separately)
    group_var_name, _ = group

    # Extract variable filters and labels
    variable_filters = [f for f, _ in variables]
    variable_labels = [l for _, l in variables]

    # Apply population filter using pl.sql_expr()
    if population_filter:
        population_filtered = population.filter(pl.sql_expr(population_filter))
    else:
        population_filtered = population

    # Calculate denominators using count_subject() from count.py
    n_pop = count_subject(
        population=population_filtered,
        id="USUBJID",
        group=group_var_name,
        total=False,
        missing_group="error"
    ).rename({"n_subj_pop": "n"})

    # Build combined filter expression
    filter_expr = pl.lit(True)

    # Add variable filters with OR logic
    if variable_filters:
        var_conditions = [f"({vf})" for vf in variable_filters]
        var_sql = f"({' OR '.join(var_conditions)})"
        filter_expr = filter_expr & pl.sql_expr(var_sql)

    # Add observation filter with AND logic
    if observation_filter:
        filter_expr = filter_expr & pl.sql_expr(observation_filter)

    # Apply all filters at once
    observation_filtered = observation.filter(filter_expr)

    # Filter to population subjects
    pop_subjects = population_filtered.select("USUBJID")
    observation_filtered = observation_filtered.join(pop_subjects, on="USUBJID", how="inner")

    # Merge treatment group from population
    observation_with_group = observation_filtered.join(
        population_filtered.select(["USUBJID", group_var_name]), on="USUBJID", how="left"
    )

    # Calculate SOC-level counts
    soc_summary = (
        observation_with_group.filter(pl.col("AOCCSFL") == "Y")
        .group_by([group_var_name, "AESOC"])
        .agg(pl.n_unique("USUBJID").alias("n_subj"))
        .join(n_pop, on=group_var_name)
        .with_columns(
            [
                (pl.col("n_subj") / pl.col("n") * 100).round(1).alias("pct"),
                pl.lit("SOC").alias("level"),
                pl.lit("").alias("AEDECOD"),
            ]
        )
        .rename({"AESOC": "term"})
        .select([group_var_name, "level", "term", "AEDECOD", "n_subj", "n", "pct"])
    )

    # Calculate PT-level counts
    pt_summary = (
        observation_with_group.filter(pl.col("AOCCPFL") == "Y")
        .group_by([group_var_name, "AESOC", "AEDECOD"])
        .agg(pl.n_unique("USUBJID").alias("n_subj"))
        .join(n_pop, on=group_var_name)
        .with_columns(
            [
                (pl.col("n_subj") / pl.col("n") * 100).round(1).alias("pct"),
                pl.lit("PT").alias("level"),
            ]
        )
        .rename({"AESOC": "term", "AEDECOD": "AEDECOD"})
        .select([group_var_name, "level", "term", "AEDECOD", "n_subj", "n", "pct"])
    )

    # Combine and sort
    summary = pl.concat([soc_summary, pt_summary])
    summary = (
        summary.with_columns(
            [
                pl.col("n_subj").sum().over(["term", group_var_name]).alias("soc_total"),
                pl.col("n_subj").sum().over(["AEDECOD", group_var_name]).alias("pt_total"),
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
            "variable_filters": variable_filters,
            "variable_labels": variable_labels,
            "observation_filter": observation_filter,
            "group": group,
        },
        "n_pop": n_pop,
        "summary": summary,
    }


def ae_summary(
    study_plan: StudyPlan,
    population: str,
    observation: str | None = None,
    parameter: str = "any",
    group: str = "trt01a",
) -> dict[str, Any]:
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
    # Initialize parser
    parser = StudyPlanParser(study_plan)

    # Get datasets (adsl for population, adae for observation)
    population_df, observation_df = parser.get_datasets("adsl", "adae")

    # Get filters and configuration using parser
    population_filter = parser.get_population_filter(population)
    param_names, param_filters, param_labels = parser.get_parameter_info(parameter)
    obs_filter = parser.get_observation_filter(observation)
    group_var_name, group_labels = parser.get_group_info(group)

    # Build variables as list of tuples [(filter, label)]
    variables_list = list(zip(param_filters, param_labels))

    # Build group tuple (variable_name, label)
    # Use first group label or variable name as label
    group_var_label = group_labels[0] if group_labels else group_var_name
    group_tuple = (group_var_name, group_var_label)

    # Call core function
    result = ae_summary_core(
        population=population_df,
        observation=observation_df,
        population_filter=population_filter,
        observation_filter=obs_filter,
        group=group_tuple,
        variables=variables_list,
    )

    # Add StudyPlan-specific metadata and group labels
    result["meta"].update(
        {
            "population": population,
            "observation": observation,
            "parameter": param_names,
            "group": group,
        }
    )
    result["group_labels"] = group_labels

    return result


def calculate_parameter_summary(
    study_plan: StudyPlan,
    population: str,
    observation: str | None = None,
    parameters: list[str] = None,
    group: str = "trt01a",
) -> dict[str, Any]:
    """
    Calculate summary counts for multiple parameters separately.

    This generates the high-level summary table format showing counts by parameter category.

    Args:
        study_plan: StudyPlan object with loaded datasets
        population: Population keyword name
        observation: Optional observation keyword
        parameters: List of parameter names to calculate separately
        group: Group keyword name

    Returns:
        Dictionary with n_pop and parameter_counts per group
    """
    # Initialize parser
    parser = StudyPlanParser(study_plan)

    # Get datasets (adsl for population, adae for observation)
    population_df, observation_df = parser.get_datasets("adsl", "adae")

    # Get filters and configuration using parser
    population_filter = parser.get_population_filter(population)
    obs_filter = parser.get_observation_filter(observation)
    group_var, group_labels = parser.get_group_info(group)

    # Apply population filter
    population_filtered = population_df.filter(pl.sql_expr(population_filter))

    # Calculate denominators using count_subject() from count.py
    n_pop = count_subject(
        population=population_filtered,
        id="USUBJID",
        group=group_var,
        total=False,
        missing_group="error"
    ).rename({"n_subj_pop": "n"})

    # Calculate counts for each parameter separately
    param_results = []
    for param_name in parameters:
        # Get parameter filter and label using parser
        param_filter, param_label = parser.get_single_parameter_info(param_name)

        # Build filter expression
        filter_expr = pl.sql_expr(param_filter)
        if obs_filter:
            filter_expr = filter_expr & pl.sql_expr(obs_filter)

        # Filter observation data
        observation_filtered = observation_df.filter(filter_expr)

        # Filter to population subjects
        pop_subjects = population_filtered.select("USUBJID")
        observation_filtered = observation_filtered.join(pop_subjects, on="USUBJID", how="inner")

        # Merge treatment group
        observation_with_group = observation_filtered.join(
            population_filtered.select(["USUBJID", group_var]), on="USUBJID", how="left"
        )

        # Count unique subjects per group
        param_counts = (
            observation_with_group.group_by(group_var)
            .agg(pl.n_unique("USUBJID").alias("n_subj"))
            .join(n_pop, on=group_var, how="right")
            .with_columns(pl.col("n_subj").fill_null(0))
            .sort(group_var)
        )

        param_results.append({
            "parameter": param_name,
            "label": param_label,
            "counts": param_counts,
        })

    return {
        "n_pop": n_pop,
        "parameters": param_results,
        "group_var": group_var,
        "group_labels": group_labels,
    }


def ae_summary_to_rtf(
    result: dict[str, Any],
    study_plan: StudyPlan | None = None,
    title: str | None = None,
    subtitle: list[str] | None = None,
    output_file: str | None = None,
    col_widths: list[float] | None = None,
) -> str:
    """
    Convert ae_summary result to RTF summary table format using rtflite.

    Generates a high-level summary table showing counts and percentages of subjects
    with adverse events by parameter category (any AE, drug-related AE, serious AE, etc.).
    This matches the format of metalite.ae's prepare_ae_summary() output.

    Args:
        result: Dictionary from ae_summary() - used to extract metadata
        study_plan: StudyPlan object (required for accurate per-parameter counts)
        title: Main title for the table (default: "Summary of Adverse Events")
        subtitle: Optional list of subtitle lines (e.g., ["Weeks 0 to 12", "All Participants as Treated"])
        output_file: Optional file path to write RTF output (if None, returns RTF string only)
        col_widths: Optional list of relative column widths (default: auto-calculated)

    Returns:
        RTF document as string

    Raises:
        ImportError: If rtflite is not installed
        ValueError: If study_plan is not provided or result is invalid

    Example:
        >>> result = ae_summary(study_plan, "apat", parameter="any;rel;ser")
        >>> rtf_string = ae_summary_to_rtf(
        ...     result,
        ...     study_plan=study_plan,
        ...     subtitle=["Weeks 0 to 12", "All Participants as Treated"],
        ...     output_file="ae_summary.rtf"
        ... )
    """
    if not RTFLITE_AVAILABLE:
        raise ImportError(
            "rtflite is required for RTF output. Install it with: pip install rtflite"
        )

    if study_plan is None:
        raise ValueError("study_plan is required for accurate parameter-level counts")

    # Extract metadata from result
    meta = result.get("meta", {})
    population = meta.get("population")
    observation = meta.get("observation")
    parameters = meta.get("parameter", [])
    group = meta.get("group")

    if not population or not group:
        raise ValueError("Result must contain population and group in metadata")

    # Calculate per-parameter summary
    summary_data = calculate_parameter_summary(
        study_plan=study_plan,
        population=population,
        observation=observation,
        parameters=parameters,
        group=group,
    )

    n_pop_df = summary_data["n_pop"]
    param_results = summary_data["parameters"]
    group_var = summary_data["group_var"]
    group_labels = summary_data.get("group_labels", [])

    # Get treatment groups
    groups = n_pop_df[group_var].to_list()
    n_values = n_pop_df["n"].to_list()

    # Use actual group values as labels if group_labels is empty
    if not group_labels or len(group_labels) == 0:
        group_labels = groups

    # Build display data
    display_data = []

    # First row: Population denominators (n only, no percentage)
    pop_row = {"Category": "Participants in population"}
    for i, label in enumerate(group_labels):
        pop_row[label] = str(n_values[i])
    total_n = sum(n_values)
    pop_row["Total"] = str(total_n)
    display_data.append(pop_row)

    # Subsequent rows: One row per parameter with n (%)
    for param_result in param_results:
        param_label = param_result["label"]
        param_counts_df = param_result["counts"]

        # Extract counts
        param_row = {"Category": f"  {param_label.lower()}"}
        total_subj = 0

        for i, (grp, label) in enumerate(zip(groups, group_labels)):
            # Get count for this group
            grp_row = param_counts_df.filter(pl.col(group_var) == grp)
            if len(grp_row) > 0:
                n_subj = int(grp_row["n_subj"][0])
            else:
                n_subj = 0

            n_pop = n_values[i]
            pct = (n_subj / n_pop * 100) if n_pop > 0 else 0
            param_row[label] = f"{n_subj} ({pct:.1f})"
            total_subj += n_subj

        total_pct = (total_subj / total_n * 100) if total_n > 0 else 0
        param_row["Total"] = f"{total_subj} ({total_pct:.1f})"
        display_data.append(param_row)

    # Convert to DataFrame
    display_df = pl.DataFrame(display_data)

    # Create title text
    if title is None:
        title_text = "Summary of Adverse Events"
    else:
        title_text = title

    # Add subtitles if provided
    if subtitle:
        title_lines = [title_text] + subtitle
        title_text = "\n".join(title_lines)

    # Create column headers
    col_headers = [""]  # First column is category
    for label in group_labels:
        col_headers.append(f"{label}")
    col_headers.append("Total")

    # Add second header row with n and (%)
    col_headers_2 = [""]
    for _ in group_labels:
        col_headers_2.append("n\n(%)")
    col_headers_2.append("n\n(%)")

    # Determine column widths
    n_cols = len(display_df.columns)
    if col_widths is None:
        # Auto-calculate: first column wider, rest equal
        first_col_width = 3.5
        other_col_width = 1.0
        col_widths = [first_col_width] + [other_col_width] * (n_cols - 1)

    # Create RTF document
    doc = RTFDocument(
        df=display_df,
        rtf_title=RTFTitle(text=title_text, text_font_size=11, text_format="b"),
        rtf_column_header=[
            RTFColumnHeader(
                text=col_headers,
                text_font_size=9,
                text_justification=["l"] + ["c"] * (n_cols - 1),
            ),
            RTFColumnHeader(
                text=col_headers_2,
                text_font_size=9,
                text_justification=["l"] + ["c"] * (n_cols - 1),
            ),
        ],
        rtf_body=RTFBody(
            col_rel_width=col_widths,
            text_justification=["l"] + ["c"] * (n_cols - 1),
            text_font_size=9,
        ),
        rtf_source=RTFSource(text="Source: [CDISCpilot: adam-adsl; adae]", text_font_size=8),
    )

    # Generate RTF string
    rtf_string = doc.rtf_encode()

    # Write to file if specified
    if output_file:
        doc.write_rtf(output_file)

    return rtf_string


