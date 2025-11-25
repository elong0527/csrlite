"""
Adverse Event (AE) Analysis Functions

This module provides core function for AE summary analysis following metalite.ae patterns:
- ae_summary: Summary tables with counts/percentages by treatment group

Uses Polars native SQL capabilities for data manipulation, count.py utilities for subject counting,
and parse.py utilities for StudyPlan parsing.
"""

from pathlib import Path
from typing import Any

import polars as pl

from rtflite import RTFBody, RTFColumnHeader, RTFDocument, RTFFootnote, RTFSource, RTFTitle
from .plan import StudyPlan
from .count import count_subject, count_subject_with_observation
from .parse import StudyPlanParser


def ae_summary_ard(
    population: pl.DataFrame,
    observation: pl.DataFrame,
    population_filter: str | None,
    observation_filter: str | None,
    id: tuple[str, str],
    group: tuple[str, str],
    variables: list[tuple[str, str]],
    total: bool,
    missing_group: str,
) -> dict[str, Any]:
    """
    Core AE summary function for generating Analysis Results Data (ARD) - decoupled from StudyPlan.

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
        id: Tuple of ID column name(s) for counting (default: ("USUBJID",))
        total: Whether to include total column in counts (default: False)
        missing_group: How to handle missing group values: "error", "ignore", or "fill" (default: "error")

    Returns:
        Dictionary containing:
        - meta: Analysis metadata
        - n_pop: Population denominators by group
        - summary: Summary statistics with SOC/PT hierarchy
    """
    # Extract group variable name (label is in tuple but not needed separately)
    pop_var_name = "Participants in Population"
    id_var_name, id_var_label = id
    group_var_name, group_var_label = group

    # Apply population filter using pl.sql_expr()
    if population_filter:
        population_filtered = population.filter(pl.sql_expr(population_filter))
    else:
        population_filtered = population

    # Apply observation filter once if provided
    observation_to_filter = observation
    if observation_filter:
        observation_to_filter = observation_to_filter.filter(pl.sql_expr(observation_filter))

    # Filter observation data to include only subjects in the filtered population
    # Process all variables in the list
    observation_filtered_list = []
    for variable_filter, variable_label in variables:
        obs_filtered = (
            observation_to_filter
            .filter(pl.col(id_var_name).is_in(population_filtered[id_var_name].to_list()))
            .filter(pl.sql_expr(variable_filter))
            .with_columns(pl.lit(variable_label).alias("__index__"))
        )

        observation_filtered_list.append(obs_filtered)

    # Concatenate all filtered observations
    observation_filtered = pl.concat(observation_filtered_list) 

    # Population
    n_pop = count_subject(
        population=population_filtered,
        id=id_var_name,
        group=group_var_name,
        total=total,
        missing_group=missing_group
    )

    n_pop = n_pop.select(
        pl.lit(pop_var_name).alias("__index__"),
        pl.col(group_var_name).alias("__group__"),
        pl.col("n_subj_pop").cast(pl.String).alias("__value__")
    )

    # Empty row with same structure as n_pop but with empty strings
    n_empty = n_pop.select(
        pl.lit("").alias("__index__"),
        pl.col("__group__"),
        pl.lit("").alias("__value__")
    )

    # Observation
    n_obs = count_subject_with_observation(
        population=population_filtered,
        observation = observation_filtered,
        id=id_var_name,
        group=group_var_name,
        total=total,
        variable = "__index__",
        missing_group=missing_group
    )

    n_obs = n_obs.select(
        pl.col("__index__"),
        pl.col(group_var_name).alias("__group__"),
        pl.col("n_pct_subj_fmt").alias("__value__")
    )

    res = pl.concat([n_pop, n_empty, n_obs])

    # Convert __index__ to ordered Enum based on appearance
    # Build the ordered categories list: population name, empty string, then variable labels
    variable_labels = [label for _, label in variables]
    ordered_categories = [pop_var_name, ""] + variable_labels

    res = res.with_columns(
        pl.col("__index__").cast(pl.Enum(ordered_categories))
    ).sort("__index__", "__group__")

    return res

def study_plan_to_ae_summary(
    study_plan: StudyPlan,
) -> list[str]:
    """
    Generate AE summary RTF outputs for all analyses defined in StudyPlan.

    This function reads the expanded plan from StudyPlan and generates
    an RTF table for each analysis specification automatically.

    Args:
        study_plan: StudyPlan object with loaded datasets and analysis specifications

    Returns:
        list[str]: List of paths to generated RTF files
    """

    # Meta data
    analysis = "ae_summary"
    analysis_label = "Analysis of Adverse Event Summary"
    output_dir = "examples/tlf"
    footnote = ["Every participant is counted a single time for each applicable row and column."]
    source = None

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Get expanded plan DataFrame
    plan_df = study_plan.get_plan_df()

    # Filter for AE summary analyses
    ae_plans = plan_df.filter(pl.col("analysis") == analysis)

    rtf_files = []

    # Generate RTF for each analysis
    for row in ae_plans.iter_rows(named=True):
        population = row["population"]
        observation = row.get("observation")
        parameter = row["parameter"]

        # Get group - must be specified in YAML
        group = row.get("group")
        if group is None:
            raise ValueError(f"Group not specified in YAML for analysis: population={population}, observation={observation}, parameter={parameter}. Please add group to your YAML plan.")

        # Build title with population and observation context
        title_parts = [analysis_label]
        if observation:
            obs_kw = study_plan.keywords.observations.get(observation)
            if obs_kw and obs_kw.label:
                title_parts.append(f"({obs_kw.label})")

        pop_kw = study_plan.keywords.populations.get(population)
        if pop_kw and pop_kw.label:
            title_parts.append(f"({pop_kw.label})")

        # Build output filename
        filename = f"{analysis}_{population}"
        if observation:
            filename += f"_{observation}"
        filename += f"_{parameter.replace(';', '_')}.rtf"
        output_file = str(Path(output_dir) / filename)

        # Generate RTF
        rtf_path = ae_summary(
            study_plan=study_plan,
            population=population,
            title=title_parts,
            footnote=footnote,
            source=source,
            output_file=output_file,
            observation=observation,
            parameter=parameter,
            group=group,
        )

        rtf_files.append(rtf_path)

    return rtf_files


def ae_summary(
    population: pl.DataFrame,
    observation: pl.DataFrame,
    population_filter: str | None,
    observation_filter: str | None,
    id: tuple[str, str],
    group: tuple[str, str],
    variables: list[tuple[str, str]],
    title: list[str],
    footnote: list[str] | None,
    source: list[str] | None,
    output_file: str,
    total: bool = True,
    col_rel_width: list[float] | None = None,
    missing_group: str = "error",
) -> str:
    """
    Complete AE summary pipeline wrapper.

    This function orchestrates the three-step pipeline:
    1. ae_summary_ard: Generate Analysis Results Data
    2. ae_summary_df: Transform to display format
    3. ae_summary_rtf: Generate RTF output and write to file

    Args:
        population: Population DataFrame (subject-level data, e.g., ADSL)
        observation: Observation DataFrame (event data, e.g., ADAE)
        population_filter: SQL WHERE clause for population (can be None)
        observation_filter: SQL WHERE clause for observation (can be None)
        id: Tuple (variable_name, label) for ID column
        group: Tuple (variable_name, label) for grouping variable
        variables: List of tuples [(filter, label)] for analysis variables
        title: Title for RTF output as list of strings
        footnote: Optional footnote for RTF output as list of strings
        source: Optional source for RTF output as list of strings
        output_file: File path to write RTF output
        total: Whether to include total column (default: False)
        missing_group: How to handle missing group values (default: "error")
        col_rel_width: Optional column widths for RTF output

    Returns:
        str: Path to the generated RTF file
    """
    # Step 1: Generate ARD
    ard = ae_summary_ard(
        population=population,
        observation=observation,
        population_filter=population_filter,
        observation_filter=observation_filter,
        id=id,
        group=group,
        variables=variables,
        total=total,
        missing_group=missing_group,
    )

    # Step 2: Transform to display format
    df = ae_summary_df(ard)

    # Step 3: Generate RTF and write to file
    rtf_doc = ae_summary_rtf(
        df=df,
        title=title,
        footnote=footnote,
        source=source,
        col_rel_width=col_rel_width,
    )
    rtf_doc.write_rtf(output_file)

    return output_file


def ae_summary_df(ard: pl.DataFrame) -> pl.DataFrame:
    """
    Transform AE summary ARD (Analysis Results Data) into display-ready DataFrame.

    Converts the long-format ARD with __index__, __group__, and __value__ columns
    into a wide-format display table where groups become columns.

    Args:
        ard: Analysis Results Data DataFrame with __index__, __group__, __value__ columns
        split_n_pct: If True, split "n (%)" into separate "n" and "(%)" columns for each group.
                     Useful for RTF tables with multi-level headers. Defaults to False.

    Returns:
        pl.DataFrame: Wide-format display table with groups as columns
    """
    # Pivot from long to wide format: __group__ values become columns
    df_wide = ard.pivot(
        index="__index__",
        on="__group__",
        values="__value__"
    )

    return df_wide


def ae_summary_rtf(
    df: pl.DataFrame,
    title: list[str],
    footnote: list[str] | None,
    source: list[str] | None,
    col_rel_width: list[float] | None = None,
) -> str:
    """
    Generate RTF table from AE summary display DataFrame.

    Creates a formatted RTF table with two-level column headers showing
    treatment groups with "n (%)" values.

    Args:
        df: Display DataFrame from ae_summary_df (wide format with __index__ column)
        title: Title(s) for the table as list of strings.
        footnote: Optional footnote(s) as list of strings.
        source: Optional source note(s) as list of strings.
        col_rel_width: Optional list of relative column widths. If None, auto-calculated
                       as [n_cols-1, 1, 1, 1, ...] where n_cols is total column count.

    Returns:
        RTF document as string

    Example:
        >>> ard = ae_summary_ard(population, observation, ...)
        >>> df = ae_summary_df(ard)
        >>> rtf = ae_summary_rtf(
        ...     df,
        ...     title=["Analysis of Adverse Event Summary", "(Safety Analysis Population)"],
        ...     footnote=["Every participant is counted a single time for each applicable row and column."],
        ...     source=["Source: ADSL and ADAE datasets"]
        ... )
    """

    # Rename __index__ to empty string for display
    df_rtf = df.rename({"__index__": ""})

    # Calculate number of columns
    n_cols = len(df_rtf.columns)

    # Build first-level column headers (use actual column names)
    col_header_1 = df_rtf.columns

    # Build second-level column headers (empty for first, "n (%)" for groups)
    col_header_2 = [""] + ["n (%)"] * (n_cols - 1)

    # Calculate column widths - auto-calculate if not provided
    if col_rel_width is None:
        col_widths = [n_cols - 1] + [1] * (n_cols - 1)
    else:
        col_widths = col_rel_width

    # Normalize title, footnote, source to lists
    title_list = [title] if isinstance(title, str) else title
    footnote_list = [footnote] if isinstance(footnote, str) else (footnote or [])
    source_list = [source] if isinstance(source, str) else (source or [])

    # Build RTF document
    rtf_components = {
        "df": df_rtf,
        "rtf_title": RTFTitle(text=title_list),
        "rtf_column_header": [
            RTFColumnHeader(
                text=col_header_1,
                col_rel_width=col_widths,
                text_justification=["l"] + ["c"] * (n_cols - 1),
            ),
            RTFColumnHeader(
                text=col_header_2,
                col_rel_width=col_widths,
                text_justification=["l"] + ["c"] * (n_cols - 1),
                border_left=["single"],
                border_top=[""],
            ),
        ],
        "rtf_body": RTFBody(
            col_rel_width=col_widths,
            text_justification=["l"] + ["c"] * (n_cols - 1),
            border_left=["single"] * n_cols,
        ),
    }

    # Add optional footnote
    if footnote_list:
        rtf_components["rtf_footnote"] = RTFFootnote(text=footnote_list)

    # Add optional source
    if source_list:
        rtf_components["rtf_source"] = RTFSource(text=source_list)

    # Create RTF document
    doc = RTFDocument(**rtf_components)

    # Return RTF string
    return doc
