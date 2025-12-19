# pyre-strict
"""
Concomitant Medications (CM) Listing Functions
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import polars as pl
from rtflite import RTFBody, RTFColumnHeader, RTFDocument, RTFFootnote, RTFPage, RTFSource, RTFTitle

from ..common.parse import StudyPlanParser
from ..common.plan import StudyPlan
from ..common.utils import apply_common_filters
from ..pd.pd_listing import pd_listing_ard, pd_listing_rtf # Reuse generic listing logic if possible?
# Actually pd_listing_* are generic enough, but specific names might be better for clarity.
# For now, I will re-implement wrapper but reuse logic or verify if I can import.
# pd_listing_ard is quite generic. Let's see if we can adapt or copy-paste with minor changes.
# pd_listing_ard asserts observation_to_filter is not None.
# It selects columns.
# It joins population.
# It adds index.
# It's actually generic "listing_ard".
# But for now to avoid refactoring `pd` into `common`, I will duplicate the logic or keep it specific if CM needs special handling.
# CM usually needs sorting by date.

def cm_listing_ard(
    population: pl.DataFrame,
    observation: pl.DataFrame,
    population_filter: Optional[str],
    observation_filter: Optional[str],
    id: Tuple[str, str],
    population_columns: Optional[List[Tuple[str, str]]] = None,
    observation_columns: Optional[List[Tuple[str, str]]] = None,
    sort_columns: Optional[List[str]] = None,
    page_by: Optional[List[str]] = None,
) -> pl.DataFrame:
    """
    Generate ARD for CM listing.
    """
    # Reuse the logic logic from PD listing pattern (copy-paste for independence/stability)
    id_var_name, id_var_label = id

    population_filtered, observation_to_filter = apply_common_filters(
        population=population,
        observation=observation,
        population_filter=population_filter,
        observation_filter=observation_filter,
        parameter_filter=None,
    )
    assert observation_to_filter is not None

    observation_filtered = observation_to_filter.filter(
        pl.col(id_var_name).is_in(population_filtered[id_var_name].to_list())
    )

    if observation_columns is None:
        obs_cols = [id_var_name]
    else:
        obs_col_names = [var_name for var_name, _ in observation_columns]
        obs_cols = [id_var_name] + [col for col in obs_col_names if col != id_var_name]

    obs_cols_available = [col for col in obs_cols if col in observation_filtered.columns]
    result = observation_filtered.select(obs_cols_available)

    if population_columns is not None:
        pop_col_names = [var_name for var_name, _ in population_columns]
        pop_cols = [id_var_name] + [col for col in pop_col_names if col != id_var_name]
        pop_cols_available = [col for col in pop_cols if col in population_filtered.columns]
        population_subset = population_filtered.select(pop_cols_available)
        result = result.join(population_subset, on=id_var_name, how="left")

    if id_var_name in result.columns:
        result = result.with_columns(
            (pl.lit(f"{id_var_label} = ") + pl.col(id_var_name).cast(pl.Utf8)).alias("__index__")
        )

    existing_page_by_cols = [col for col in page_by if col in result.columns] if page_by else []

    if existing_page_by_cols:
        column_labels = {id_var_name: id_var_label}
        if population_columns:
            for var_name, var_label in population_columns:
                column_labels[var_name] = var_label

        index_expressions = []
        for col_name in existing_page_by_cols:
            label = column_labels.get(col_name, col_name)
            index_expressions.append(pl.lit(f"{label} = ") + pl.col(col_name).cast(pl.Utf8))

        result = result.with_columns(
            pl.concat_str(index_expressions, separator=", ").alias("__index__")
        )
        page_by_remove = [col for col in (page_by or []) if col != id_var_name]
        result = result.drop(page_by_remove)

    if "__index__" in result.columns:
        other_columns = [col for col in result.columns if col != "__index__"]
        result = result.select(["__index__"] + other_columns)

    if sort_columns is None:
        if id_var_name in result.columns:
            result = result.sort(id_var_name)
    else:
        cols_to_sort = [col for col in sort_columns if col in result.columns]
        if cols_to_sort:
            result = result.sort(cols_to_sort)

    return result

def cm_listing_rtf(
    df: pl.DataFrame,
    column_labels: Dict[str, str],
    title: List[str],
    footnote: Optional[List[str]],
    source: Optional[List[str]],
    col_rel_width: Optional[List[float]] = None,
    group_by: Optional[List[str]] = None,
    page_by: Optional[List[str]] = None,
    orientation: str = "landscape",
) -> RTFDocument:
    n_cols = len(df.columns)
    col_header = [column_labels.get(col, col) for col in df.columns]

    if col_rel_width is None:
        col_widths = [1.0] * n_cols
    else:
        col_widths = col_rel_width

    title_list = title
    footnote_list: List[str] = footnote or []
    source_list: List[str] = source or []

    rtf_components: Dict[str, Any] = {
        "df": df,
        "rtf_page": RTFPage(orientation=orientation),
        "rtf_title": RTFTitle(text=title_list),
        "rtf_column_header": [
            RTFColumnHeader(
                text=col_header[1:],
                col_rel_width=col_widths[1:],
                text_justification=["l"] + ["l"] * (n_cols - 1),
            ),
        ],
        "rtf_body": RTFBody(
            col_rel_width=col_widths,
            text_justification=["l"] * n_cols,
            border_left=["single"],
            border_top=["single"] + [""] * (n_cols - 1),
            border_bottom=["single"] + [""] * (n_cols - 1),
            group_by=group_by,
            page_by=page_by,
        ),
    }

    if footnote_list:
        rtf_components["rtf_footnote"] = RTFFootnote(text=footnote_list)
    if source_list:
        rtf_components["rtf_source"] = RTFSource(text=source_list)

    return RTFDocument(**rtf_components)

def cm_listing(
    population: pl.DataFrame,
    observation: pl.DataFrame,
    population_filter: Optional[str],
    observation_filter: Optional[str],
    id: Tuple[str, str],
    title: List[str],
    footnote: Optional[List[str]],
    source: Optional[List[str]],
    output_file: str,
    population_columns: Optional[List[Tuple[str, str]]] = None,
    observation_columns: Optional[List[Tuple[str, str]]] = None,
    sort_columns: Optional[List[str]] = None,
    group_by: Optional[List[str]] = None,
    page_by: Optional[List[str]] = None,
    col_rel_width: Optional[List[float]] = None,
    orientation: str = "landscape",
) -> str:
    df = cm_listing_ard(
        population=population,
        observation=observation,
        population_filter=population_filter,
        observation_filter=observation_filter,
        id=id,
        population_columns=population_columns,
        observation_columns=observation_columns,
        sort_columns=sort_columns,
        page_by=page_by,
    )

    id_var_name, id_var_label = id
    column_labels = {id_var_name: id_var_label}

    if observation_columns is not None:
        for var_name, var_label in observation_columns:
            column_labels[var_name] = var_label

    if population_columns is not None:
        for var_name, var_label in population_columns:
            column_labels[var_name] = var_label

    column_labels["__index__"] = ""

    rtf_doc = cm_listing_rtf(
        df=df,
        column_labels=column_labels,
        title=title,
        footnote=footnote,
        source=source,
        col_rel_width=col_rel_width,
        group_by=group_by,
        page_by=["__index__"],
        orientation=orientation,
    )
    rtf_doc.write_rtf(output_file)

    return output_file

def study_plan_to_cm_listing(study_plan: StudyPlan) -> List[str]:
    output_dir = study_plan.output_dir
    analysis = "cm_listing"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Default Columns for CM Listing
    # Use: CMTRT, CMDECOD, ASTDT, AENDT, ONTRTFL
    
    observation_columns_base = [
        ("CMTRT", "Reported Term"),
        ("CMDECOD", "Standardized Term"),
        ("ASTDT", "Start Date"),
        ("AENDT", "End Date"),
        ("ONTRTFL", "On Treatment"),
    ]
    
    sort_columns = ["TRT01A", "USUBJID", "ASTDT", "CMTRT"]
    page_by = ["USUBJID", "TRT01A"]
    group_by = ["USUBJID"]
    col_rel_width = [1.0, 1.0, 2.0, 2.0, 1.0, 1.0, 0.5] # Adjust based on 7 cols? ID + 5 obs + 1 pop
    
    parser = StudyPlanParser(study_plan)
    plan_df = study_plan.get_plan_df().filter(pl.col("analysis") == analysis)
    
    files = []
    
    for row in plan_df.iter_rows(named=True):
        population = row["population"]
        observation = row.get("observation")
        group = row.get("group")
        
        if not group:
            raise ValueError("Group required for CM listing")
            
        pop_df, obs_df = parser.get_datasets("adsl", "adcm")
        pop_filter = parser.get_population_filter(population)
        obs_filter = parser.get_observation_filter(observation)
        
        group_var, group_labels = parser.get_group_info(group)
        group_label = group_labels[0] if group_labels else "Treatment"
        
        population_columns = [(group_var, group_label)]
        observation_columns = observation_columns_base
        
        title = ["Listing of Concomitant Medications"]
        pop_kw = study_plan.keywords.populations.get(population)
        if pop_kw and pop_kw.label:
            title.append(pop_kw.label)
            
        filename = f"{analysis}_{population}"
        if observation:
             filename += f"_{observation}"
        filename += ".rtf"
        output_file = str(Path(output_dir) / filename)
        
        cm_listing(
            population=pop_df,
            observation=obs_df,
            population_filter=pop_filter,
            observation_filter=obs_filter,
            id=("USUBJID", "Subject ID"),
            title=title,
            footnote=None,
            source=None,
            output_file=output_file,
            population_columns=population_columns,
            observation_columns=observation_columns,
            sort_columns=sort_columns,
            col_rel_width=None, # auto
            group_by=group_by,
            page_by=page_by
        )
        files.append(output_file)
        
    return files
