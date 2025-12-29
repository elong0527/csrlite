# pyre-strict
from typing import Any
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from csrlite.common.plan import StudyPlan
from csrlite.mh.mh_listing import (
    mh_listing,
    mh_listing_df,
    mh_listing_rtf,
    study_plan_to_mh_listing,
)


@pytest.fixture
def adsl_data() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "USUBJID": ["01-001", "01-002", "01-003"],
            "TRT01A": ["Drug A", "Placebo", "Drug A"],
            "AGE": [45, 52, 38],
            "SEX": ["M", "F", "M"],
            "SAFFL": ["Y", "Y", "Y"],
        }
    )


@pytest.fixture
def admh_data() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "USUBJID": ["01-001", "01-001", "01-002"],
            "MHSEQ": [1, 2, 1],
            "MHBODSYS": ["Infections", "Cardiac", "Nervous"],
            "MHDECOD": ["Flu", "Hypertension", "Headache"],
            "MHSTDTC": ["2023-01-01", "2020-05-15", "2022-11-20"],
            "MHENRTPT": ["RESOLVED", "ONGOING", "RESOLVED"],
            "MHOCCUR": ["Y", "Y", "Y"],
        }
    )


def test_mh_listing_df(adsl_data: pl.DataFrame, admh_data: pl.DataFrame) -> None:
    """Test dataframe creation for listing."""
    df = mh_listing_df(
        population=adsl_data,
        observation=admh_data,
        population_filter=None,
        observation_filter=None,
        id_col="USUBJID",
        pop_cols=None,
        obs_cols=None,
        sort_cols=None,
    )
    assert df.height == 3
    row1 = df.filter((pl.col("USUBJID") == "01-001") & (pl.col("MHSEQ") == 1)).row(0, named=True)
    assert row1["MHDECOD"] == "Flu"


def test_mh_listing_df_explicit_cols(adsl_data: pl.DataFrame, admh_data: pl.DataFrame) -> None:
    """Test explicit columns."""
    df = mh_listing_df(
        population=adsl_data,
        observation=admh_data,
        population_filter=None,
        observation_filter=None,
        id_col="USUBJID",
        pop_cols=[("SEX", "Gender")],  # Explicit pop cols
        obs_cols=[("MHDECOD", "Term")],  # Explicit obs cols
        sort_cols=None,
    )
    assert "SEX" in df.columns
    assert "MHDECOD" in df.columns
    assert "TRT01A" not in df.columns  # Should not be there
    # USUBJID should affectively be added if missing from pop_cols (logic check)
    assert "USUBJID" in df.columns


def test_mh_listing_df_sorting(adsl_data: pl.DataFrame, admh_data: pl.DataFrame) -> None:
    """Test sorting in listing."""
    df = mh_listing_df(
        population=adsl_data,
        observation=admh_data,
        population_filter=None,
        observation_filter=None,
        id_col="USUBJID",
        pop_cols=None,
        obs_cols=None,
        sort_cols=["USUBJID", "MHSTDTC"],
    )
    dates = df.filter(pl.col("USUBJID") == "01-001")["MHSTDTC"].to_list()
    assert dates == ["2020-05-15", "2023-01-01"]


def test_mh_listing_df_invalid_sorts(adsl_data: pl.DataFrame, admh_data: pl.DataFrame) -> None:
    """Test sort with invalid columns (should be ignored)."""
    df = mh_listing_df(
        population=adsl_data,
        observation=admh_data,
        population_filter=None,
        observation_filter=None,
        id_col="USUBJID",
        pop_cols=None,
        obs_cols=None,
        sort_cols=["NON_EXISTENT_COL"],
    )
    assert df.height == 3


def test_mh_listing_rtf(adsl_data: pl.DataFrame, admh_data: pl.DataFrame, tmp_path: Any) -> None:
    """Test RTF generation."""
    output_path = tmp_path / "test_mh_listing.rtf"
    mh_listing(
        population=adsl_data,
        observation=admh_data,
        output_file=str(output_path),
        title=None,  # Trigger default title branching
    )
    assert output_path.exists()


def test_mh_listing_rtf_empty(tmp_path: Any) -> None:
    """Test RTF generation with empty DF."""
    output_path = tmp_path / "test_mh_listing_empty.rtf"
    result = mh_listing_rtf(
        df=pl.DataFrame(), output_path=str(output_path), title="Title", footnote=None, source=None
    )
    assert result is None
    assert not output_path.exists()


def test_mh_listing_missing_obs_data(adsl_data: pl.DataFrame) -> None:
    """Test error when obs data is missing (None passed)."""
    with pytest.raises(ValueError, match="Observation data is missing"):
        mh_listing_df(
            population=adsl_data,
            observation=None,  # pyre-ignore
            population_filter=None,
            observation_filter=None,
            id_col="USUBJID",
            pop_cols=None,
            obs_cols=None,
            sort_cols=None,
        )


@patch("csrlite.mh.mh_listing.mh_listing")
def test_study_plan_to_mh_listing(mock_mh_listing: MagicMock, tmp_path: Any) -> None:
    """Test study plan integration using mocks."""

    mock_plan = MagicMock(spec=StudyPlan)
    mock_plan.output_dir = str(tmp_path)
    mock_plan.study_data = {"plans": [{"analysis": "mh_listing", "population": "saffl"}]}

    mock_expander = MagicMock()
    mock_expander.expand_plan.return_value = [{"analysis": "mh_listing", "population": "saffl"}]
    mock_expander.create_analysis_spec.return_value = {
        "analysis": "mh_listing",
        "population": "saffl",
    }
    mock_plan.expander = mock_expander

    with patch("csrlite.mh.mh_listing.StudyPlanParser") as MockParser:
        parser_instance = MockParser.return_value

        adsl_mock = pl.DataFrame({"USUBJID": ["001"], "TRT01A": ["A"], "SAFFL": ["Y"]})
        admh_mock = pl.DataFrame({"USUBJID": ["001"], "MHDECOD": ["Flu"], "MHOCCUR": ["Y"]})

        parser_instance.get_population_data.return_value = (adsl_mock, "TRT01A")
        parser_instance.get_datasets.return_value = (admh_mock,)

        generated = study_plan_to_mh_listing(mock_plan)

        assert len(generated) == 1
        assert "mh_listing_saffl.rtf" in generated[0]

        mock_mh_listing.assert_called_once()


def test_study_plan_to_mh_listing_defaults(tmp_path: Any) -> None:
    """Test default generation (no explicit plan defaults to nothing if none found)."""
    mock_plan = MagicMock(spec=StudyPlan)
    mock_plan.study_data = {"plans": []}
    mock_expander = MagicMock()
    mock_expander.expand_plan.return_value = []
    mock_plan.expander = mock_expander

    with patch("csrlite.mh.mh_listing.StudyPlanParser"):
        generated = study_plan_to_mh_listing(mock_plan)
        assert len(generated) == 0


def test_study_plan_to_mh_listing_exception(tmp_path: Any) -> None:
    """Test study plan integration exception handling."""
    mock_plan = MagicMock(spec=StudyPlan)
    mock_plan.output_dir = str(tmp_path)
    mock_plan.study_data = {"plans": [{"analysis": "mh_listing", "population": "saffl"}]}

    mock_expander = MagicMock()
    mock_expander.expand_plan.return_value = [{"analysis": "mh_listing", "population": "saffl"}]
    mock_expander.create_analysis_spec.return_value = {
        "analysis": "mh_listing",
        "population": "saffl",
    }
    mock_plan.expander = mock_expander

    with patch("csrlite.mh.mh_listing.StudyPlanParser") as MockParser:
        parser_instance = MockParser.return_value
        # Raise exception
        parser_instance.get_population_data.side_effect = Exception("Test Error")

        generated = study_plan_to_mh_listing(mock_plan)

        assert len(generated) == 0
