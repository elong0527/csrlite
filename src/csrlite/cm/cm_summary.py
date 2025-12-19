# pyre-strict
"""
Concomitant Medications (CM) Summary Functions
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import polars as pl
from rtflite import RTFBody, RTFColumnHeader, RTFDocument, RTFFootnote, RTFPage, RTFSource, RTFTitle

from ..common.count import count_subject_with_observation
from ..common.parse import StudyPlanParser
from ..common.plan import StudyPlan
from ..common.utils import apply_common_filters
from ..common.rtf import create_rtf_table_n_pct

def cm_summary_ard(
    population: pl.DataFrame,
    observation: pl.DataFrame,
    population_filter: Optional[str],
    observation_filter: Optional[str],
    group_var: str,
    term_var: str = "CMDECOD",
    id_var: str = "USUBJID",
    total: bool = True,
) -> pl.DataFrame:
    """
    Generate ARD for CM summary (counts by medication term).
    Adds 'With one or more medications' and 'With no medications' rows.
    """
    pop_var_name = "Participants in population"
    
    # Apply filters first
    pop_filtered, obs_filtered = apply_common_filters(
        population=population,
        observation=observation,
        population_filter=population_filter,
        observation_filter=observation_filter,
        parameter_filter=None,
    )
    
    # Ensure obs_filtered is not None
    assert obs_filtered is not None
    
    # 1. Population Row
    from ..common.count import count_subject
    n_pop = count_subject(
        population=pop_filtered,
        id=id_var,
        group=group_var,
        total=total,
    )
    n_pop = n_pop.select(
        pl.lit(pop_var_name).alias("__index__"),
        pl.col(group_var).cast(pl.String).alias("__group__"),
        pl.col("n_subj_pop").cast(pl.String).alias("__value__"),
    )

    # 2. Empty Row
    n_empty = n_pop.select(
        pl.lit("").alias("__index__"), pl.col("__group__"), pl.lit("").alias("__value__")
    )

    # 3. Overall Summary Rows (With / Without)
    # Identify subjects with ANY event in the filtered observation
    subjects_with_events = obs_filtered.select(id_var).unique()
    
    pop_with_indicator = pop_filtered.with_columns(
        pl.col(id_var)
        .is_in(subjects_with_events[id_var].to_list())
        .alias("__has_cm__")
    )
    
    event_counts = count_subject_with_observation(
        population=pop_filtered,
        observation=pop_with_indicator,
        id=id_var,
        group=group_var,
        variable="__has_cm__",
        total=total,
    )
    
    n_with = event_counts.filter(pl.col("__has_cm__") == "true").select(
        pl.lit("    with one or more medications").alias("__index__"),
        pl.col(group_var).cast(pl.String).alias("__group__"),
        pl.col("n_pct_subj_fmt").alias("__value__"),
    )

    n_without = event_counts.filter(pl.col("__has_cm__") == "false").select(
        pl.lit("    with no medications").alias("__index__"),
        pl.col(group_var).cast(pl.String).alias("__group__"),
        pl.col("n_pct_subj_fmt").alias("__value__"),
    )

    # 4. Term Counts
    # We use term_var as the index
    # We rename it to __index__ before counting
    obs_for_terms = obs_filtered.with_columns(pl.col(term_var).alias("__index__"))
    
    n_terms = count_subject_with_observation(
        population=pop_filtered,
        observation=obs_for_terms,
        id=id_var,
        group=group_var,
        variable="__index__",
        total=total,
    )
    
    n_terms = n_terms.select(
        pl.col("__index__"),
        pl.col(group_var).cast(pl.String).alias("__group__"),
        pl.col("n_pct_subj_fmt").alias("__value__"),
    )

    # Concat all
    parts = [n_pop, n_with, n_without, n_empty, n_terms]
    # Debug types
    # for i, p in enumerate(parts):
    #     print(f"Part {i} schemas: {p.schema}")
    
    res = pl.concat(parts)
    
    # Sort order: Pop, With, Without, Empty, Terms (A-Z)
    terms = n_terms.select("__index__").unique().sort("__index__").to_series().to_list()
    ordered_cats = [pop_var_name, "    with one or more medications", "    with no medications", ""] + terms
    
    # Ensure __index__ is String before casting to Enum to avoid "expected String type, got: enum" if it was already Enum somehow
    res = res.with_columns(pl.col("__index__").cast(pl.String))
    
    res = res.with_columns(pl.col("__index__").cast(pl.Enum(ordered_cats))).sort("__index__", "__group__")
    
    return res

def cm_summary_df(ard: pl.DataFrame) -> pl.DataFrame:
    """
    Transform long ARD to wide display DF.
    """
    df_wide = ard.pivot(index="__index__", on="__group__", values="__value__")
    # Rename __index__ to Medication or similar
    df_wide = df_wide.rename({"__index__": "Medication"})
    return df_wide

def cm_summary_rtf(
    df: pl.DataFrame,
    title: List[str],
    footnote: Optional[List[str]],
    source: Optional[List[str]],
    col_rel_width: Optional[List[float]] = None,
    orientation: str = "landscape",
) -> RTFDocument:
    """
    Generate RTF table from CM summary display DF.
    """
    # Rename Medication column to empty string for clean display if desired, 
    # OR keep "Medication" header. 
    # For AE it renames to "". But here "Medication" roughly effectively is the header.
    # Let's use create_rtf_table_n_pct logic for consistency.
    
    # Assuming df has 'Medication' and then group columns.
    n_cols = len(df.columns)
    col_header_1 = list(df.columns)
    
    # Second header line
    col_header_2 = [""] + ["n (%)"] * (n_cols - 1)
    
    if col_rel_width is None:
        col_widths = [3.0] + [1.0] * (n_cols - 1)
    else:
        col_widths = col_rel_width

    return create_rtf_table_n_pct(
        df=df,
        col_header_1=col_header_1,
        col_header_2=col_header_2,
        col_widths=col_widths,
        title=title,
        footnote=footnote,
        source=source,
    )


def cm_summary(
    population: pl.DataFrame,
    observation: pl.DataFrame,
    population_filter: Optional[str],
    observation_filter: Optional[str],
    group_var: str,
    title: List[str],
    output_file: str,
    footnote: Optional[List[str]] = None,
    source: Optional[List[str]] = None,
    term_var: str = "CMDECOD",
) -> str:
    """
    Pipeline for CM summary.
    """
    ard = cm_summary_ard(
        population=population,
        observation=observation,
        population_filter=population_filter,
        observation_filter=observation_filter,
        group_var=group_var,
        term_var=term_var,
    )
    
    df = cm_summary_df(ard)

    doc = cm_summary_rtf(
        df=df,
        title=title,
        footnote=footnote,
        source=source,
    )
    doc.write_rtf(output_file)
    return output_file


def study_plan_to_cm_summary(study_plan: StudyPlan) -> List[str]:
    """
    Generate CM summaries from StudyPlan.
    """
    output_dir = study_plan.output_dir
    analysis = "cm_summary"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    parser = StudyPlanParser(study_plan)
    plan_df = study_plan.get_plan_df().filter(pl.col("analysis") == analysis)

    files = []

    for row in plan_df.iter_rows(named=True):
        population = row["population"]
        observation = row.get("observation")
        group = row.get("group")
        
        if not group:
             raise ValueError(f"Group required for {analysis}")

        pop_df, obs_df = parser.get_datasets("adsl", "adcm")
        pop_filter = parser.get_population_filter(population)
        obs_filter = parser.get_observation_filter(observation)
        group_var, group_labels = parser.get_group_info(group)

        # Build title
        title = ["Summary of Concomitant Medications"]
        pop_kw = study_plan.keywords.populations.get(population)
        if pop_kw and pop_kw.label:
            title.append(f"Population: {pop_kw.label}")
        if observation:
             obs_kw = study_plan.keywords.get_observation(observation)
             if obs_kw and obs_kw.label:
                 title.append(f"Subset: {obs_kw.label}")

        filename = f"{analysis}_{population}"
        if observation:
            filename += f"_{observation}"
        filename += ".rtf"
        
        output_file = str(Path(output_dir) / filename)

        cm_summary(
            population=pop_df,
            observation=obs_df,
            population_filter=pop_filter,
            observation_filter=obs_filter,
            group_var=group_var,
            title=title,
            output_file=output_file,
            footnote=None, # customize?
            source=None,
        )
        files.append(output_file)
        
    return files
