# pyre-strict
"""
Inclusion/Exclusion (IE) Listing Functions

This module provides functions for generating IE listings.

"""

from pathlib import Path
from typing import Any

import polars as pl
from rtflite import RTFBody, RTFColumnHeader, RTFDocument, RTFFootnote, RTFPage, RTFSource, RTFTitle

from ..common.parse import StudyPlanParser
from ..common.plan import StudyPlan
from ..common.utils import apply_common_filters


def ie_listing_ard(
    population: pl.DataFrame,
    observation: pl.DataFrame,
    population_filter: str | None,
    id: tuple[str, str],
    population_columns: list[tuple[str, str]] | None = None,
    observation_columns: list[tuple[str, str]] | None = None,
    sort_columns: list[str] | None = None,
) -> pl.DataFrame:
    """
    Generate Analysis Results Data (ARD) for IE listing.
    """
    id_var_name, id_var_label = id

    # Apply common filters
    # Note: ITT typically uses population filter (ittfl)
    # observation filter might be None or specific to disposition
    population_filtered, observation_to_filter = apply_common_filters(
        population=population,
        observation=observation,
        population_filter=population_filter,
        observation_filter=None,
    )

    assert observation_to_filter is not None

    # Filter observation to include only subjects in filtered population
    observation_filtered = observation_to_filter.filter(
        pl.col(id_var_name).is_in(population_filtered[id_var_name].to_list())
    )

    # Determine columns to select
    if observation_columns is None:
        obs_cols = [id_var_name]
    else:
        obs_col_names = [var_name for var_name, _ in observation_columns]
        obs_cols = [id_var_name] + [col for col in obs_col_names if col != id_var_name]

    # Select available observation columns
    obs_cols_available = [col for col in obs_cols if col in observation_filtered.columns]
    result = observation_filtered.select(obs_cols_available)

    # Join with population
    if population_columns is not None:
        pop_col_names = [var_name for var_name, _ in population_columns]
        pop_cols = [id_var_name] + [col for col in pop_col_names if col != id_var_name]
        pop_cols_available = [col for col in pop_cols if col in population_filtered.columns]
        population_subset = population_filtered.select(pop_cols_available)

        # Left join to preserve observation records
        result = result.join(population_subset, on=id_var_name, how="left")

    # Sort
    if sort_columns is None:
        if id_var_name in result.columns:
            result = result.sort(id_var_name)
    else:
        cols_to_sort = [col for col in sort_columns if col in result.columns]
        if cols_to_sort:
            result = result.sort(cols_to_sort)

    return result


def ie_listing_rtf(
    df: pl.DataFrame,
    column_labels: dict[str, str],
    title: list[str],
    footnote: list[str] | None,
    source: list[str] | None,
    col_rel_width: list[float] | None = None,
    orientation: str = "landscape",
) -> RTFDocument:
    """
    Generate RTF table from IE listing display DataFrame.
    """
    n_cols = len(df.columns)
    col_header = [column_labels.get(col, col) for col in df.columns]

    if col_rel_width is None:
        col_widths = [1.0] * n_cols
    else:
        col_widths = col_rel_width

    title_list = title
    footnote_list: list[str] = footnote or []
    source_list: list[str] = source or []

    rtf_components: dict[str, Any] = {
        "df": df,
        "rtf_page": RTFPage(orientation=orientation),
        "rtf_title": RTFTitle(text=title_list),
        "rtf_column_header": [
            RTFColumnHeader(
                text=col_header,
                col_rel_width=col_widths,
                text_justification=["l"] * n_cols,
            ),
        ],
        "rtf_body": RTFBody(
            col_rel_width=col_widths,
            text_justification=["l"] * n_cols,
            border_left=["single"],
            border_top=["single"],
            border_bottom=["single"],
        ),
    }

    if footnote_list:
        rtf_components["rtf_footnote"] = RTFFootnote(text=footnote_list)

    if source_list:
        rtf_components["rtf_source"] = RTFSource(text=source_list)

    return RTFDocument(**rtf_components)


def ie_listing(
    population: pl.DataFrame,
    observation: pl.DataFrame,
    population_filter: str | None,
    id: tuple[str, str],
    title: list[str],
    footnote: list[str] | None,
    source: list[str] | None,
    output_file: str,
    population_columns: list[tuple[str, str]] | None = None,
    observation_columns: list[tuple[str, str]] | None = None,
    sort_columns: list[str] | None = None,
    col_rel_width: list[float] | None = None,
    orientation: str = "landscape",
) -> str:
    """
    Complete IE listing pipeline wrapper.
    """
    # Step 1: Generate ARD
    df = ie_listing_ard(
        population=population,
        observation=observation,
        population_filter=population_filter,
        id=id,
        population_columns=population_columns,
        observation_columns=observation_columns,
        sort_columns=sort_columns,
    )

    # Build column labels
    id_var_name, id_var_label = id
    column_labels = {id_var_name: id_var_label}

    if observation_columns:
        for var_name, var_label in observation_columns:
            column_labels[var_name] = var_label

    if population_columns:
        for var_name, var_label in population_columns:
            column_labels[var_name] = var_label

    # Step 2: Generate RTF
    rtf_doc = ie_listing_rtf(
        df=df,
        column_labels=column_labels,
        title=title,
        footnote=footnote,
        source=source,
        col_rel_width=col_rel_width,
        orientation=orientation,
    )

    rtf_doc.write_rtf(output_file)
    return output_file


def study_plan_to_ie_listing(
    study_plan: StudyPlan,
) -> list[str]:
    """
    Generate IE listing RTF outputs.
    """
    analysis = "ie_listing"
    output_dir = study_plan.output_dir
    # Adjust widths: Subject ID, Parameter
    col_rel_width = [1.0, 4.0]

    population_df_name = "adsl"
    observation_df_name = "adie"

    id = ("USUBJID", "Subject ID")

    # Defaults - User requested only USUBJID and I/E Reason
    population_columns_base: list[tuple[str, str]] = []

    # Based on adie.parquet
    observation_columns_base = [
        ("PARAM", "Inclusion/Exclusion Reason"),
    ]

    sort_columns = ["USUBJID"]

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    parser = StudyPlanParser(study_plan)
    plan_df = study_plan.get_plan_df()

    ie_plans = plan_df.filter(pl.col("analysis") == analysis)

    rtf_files: list[str] = []

    for row in ie_plans.iter_rows(named=True):
        population: str = row["population"]
        # observation = row.get("observation")
        group: str | None = row.get("group")  # Optional

        # Get datasets
        population_df, observation_df = parser.get_datasets(population_df_name, observation_df_name)

        # Get filters
        population_filter = parser.get_population_filter(population)

        # Handle group if present
        population_columns = list(population_columns_base)
        if group:
            group_var_name, group_labels = parser.get_group_info(group)
            group_var_label = group_labels[0] if group_labels else "Treatment"
            population_columns.append((group_var_name, group_var_label))

        # Build title
        title_parts = ["Inclusion/Exclusion Listing"]
        pop_kw = study_plan.keywords.populations.get(population)
        if pop_kw and pop_kw.label:
            title_parts.append(pop_kw.label)

        filename = f"{analysis}_{population}.rtf"
        output_file = str(Path(output_dir) / filename)

        rtf_path = ie_listing(
            population=population_df,
            observation=observation_df,
            population_filter=population_filter,
            id=id,
            title=title_parts,
            footnote=None,
            source=None,
            output_file=output_file,
            population_columns=population_columns,
            observation_columns=observation_columns_base,
            sort_columns=sort_columns,
            col_rel_width=col_rel_width,  # Using fixed width for now, could be dynamic
        )
        rtf_files.append(rtf_path)

    return rtf_files
