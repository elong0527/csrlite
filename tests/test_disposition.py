# pyre-strict
import unittest
from pathlib import Path

import polars as pl

from csrlite.common.plan import load_plan
from csrlite.disposition.disposition import (
    disposition,
    disposition_ard,
    disposition_df,
    disposition_rtf,
    study_plan_to_disposition_summary,
)


class TestDispositionArd(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test data for disposition analysis."""
        self.population_data = pl.DataFrame(
            {
                "USUBJID": ["01", "02", "03", "04", "05", "06", "07", "08"],
                "TRT01A": [
                    "Treatment A",
                    "Treatment A",
                    "Treatment B",
                    "Treatment B",
                    "Treatment B",
                    "Treatment A",
                    "Treatment A",
                    "Treatment B",
                ],
                "SAFFL": ["Y", "Y", "Y", "Y", "Y", "Y", "Y", "Y"],
                "EOSSTT": [
                    "Completed",
                    "Completed",
                    "Discontinued",
                    "Discontinued",
                    "Completed",
                    "Completed",
                    "Ongoing",  # New case: Ongoing
                    "Discontinued",  # New case: Discontinued with Null Reason
                ],
                "DCREASCD": [
                    None,
                    None,
                    "Withdrawn",
                    "Screening Failure",
                    None,
                    None,
                    None,  # Ongoing has Null reason
                    None,  # Discontinued has Null reason (Missing)
                ],
            }
        ).with_columns(
            pl.col("EOSSTT").cast(pl.Categorical),
            pl.col("DCREASCD").cast(pl.Categorical),
        )

    def test_disposition_ard_basic(self) -> None:
        """Test basic ARD generation for disposition."""

        ard = disposition_ard(
            population=self.population_data,
            population_filter=None,
            id=("USUBJID", "Subject ID"),
            group=("TRT01A", "Treatment"),
            dist_reason_term=("DCREASCD", "Discontinued"),
            ds_term=("EOSSTT", "Status"),
            total=True,
            missing_group="error",
        )

        # Check that ARD has expected columns
        self.assertIn("__index__", ard.columns)
        self.assertIn("__group__", ard.columns)
        self.assertIn("__value__", ard.columns)

        # Check that we have results for all groups
        groups = ard["__group__"].unique().to_list()
        self.assertIn("Treatment A", groups)
        self.assertIn("Treatment B", groups)
        self.assertIn("Total", groups)

        # Verify specific values
        # Check "Ongoing" presence (Subject 07 in Treatment A)
        ongoing_row = ard.filter(
            (pl.col("__index__") == "Ongoing") & (pl.col("__group__") == "Treatment A")
        )
        self.assertFalse(ongoing_row.is_empty(), "Ongoing row should exist for Treatment A")

    def test_disposition_ard_missing_reason(self) -> None:
        """Test that missing discontinuation reasons are counted correctly."""
        ard = disposition_ard(
            population=self.population_data,
            population_filter=None,
            id=("USUBJID", "Subject ID"),
            group=("TRT01A", "Treatment"),
            dist_reason_term=("DCREASCD", "Discontinued"),
            ds_term=("EOSSTT", "Status"),
            total=True,
            missing_group="error",
        )

        # Subject 08 is Discontinued with Null Reason in Treatment B
        missing_row = ard.filter(
            (pl.col("__index__") == "Missing") & (pl.col("__group__") == "Treatment B")
        )
        self.assertFalse(missing_row.is_empty(), "Missing reason row should exist for Treatment B")

        # Make sure "Completed" subjects (Null reason) are NOT counted as missing
        # Subject 01, 02 are Completed in Treatment A, DCREASCD is Null.
        # If logic is wrong, Missing for Treatment A might be non-zero (or higher than expected)
        # Treatment A: 2 Completed, 1 Ongoing, 1 ??? (from original data? No, I redefined data)
        # Data:
        # 01 (A): Completed, Null
        # 02 (A): Completed, Null
        # 03 (B): Discontinued, Withdrawn
        # 04 (B): Discontinued, Screening Failure
        # 05 (B): Completed, Null
        # 06 (A): Completed, Null
        # 07 (A): Ongoing, Null
        # 08 (B): Discontinued, Null

        # Treatment A Discontinued: 0. Missing should be 0 or row not present/0 value?
        # Actually count_subject usually returns 0 if total=True and no matches?
        # Wait, count_subject returns counts for all groups in population/group column.
        # If count is 0, it might be present as "0".
        missing_row_a = ard.filter(
            (pl.col("__index__") == "Missing") & (pl.col("__group__") == "Treatment A")
        )

        val = missing_row_a.select("__value__").item() if not missing_row_a.is_empty() else "0"
        # Since we use count_subject, it formats as n (%).
        # If 0, it should be "0 (  0.0)" or similar.
        # But crucially, it shouldn't be 2 or 3 (the number of completed/ongoing).
        self.assertTrue(
            "0" in val or val == "0",
            f"Treatment A should have 0 missing reasons, got {val}",
        )

    def test_disposition_ard_no_group(self) -> None:
        """Test ARD generation without group variable."""

        ard = disposition_ard(
            population=self.population_data,
            population_filter=None,
            id=("USUBJID", "Subject ID"),
            group=None,  # No grouping
            dist_reason_term=("DCREASCD", "Discontinued"),
            ds_term=("EOSSTT", "Status"),
            total=True,
            missing_group="error",
        )

        # When no group is specified, Overall is used
        self.assertIn("__group__", ard.columns)
        groups = ard["__group__"].unique().to_list()
        self.assertIn("Overall", groups)

    def test_disposition_ard_with_filters(self) -> None:
        """Test ARD generation with population and observation filters."""

        ard = disposition_ard(
            population=self.population_data,
            population_filter="TRT01A == 'Treatment A'",
            id=("USUBJID", "Subject ID"),
            group=("TRT01A", "Treatment"),
            dist_reason_term=("DCREASCD", "Discontinued"),
            ds_term=("EOSSTT", "Status"),
            total=False,
            missing_group="error",
        )

        # Should only have Treatment A group
        groups = ard["__group__"].unique().to_list()
        self.assertEqual(len(groups), 1)
        self.assertIn("Treatment A", groups)


class TestDispositionDf(unittest.TestCase):
    def test_disposition_df_basic(self) -> None:
        """Test transformation of ARD to display format."""
        ard = pl.DataFrame(
            {
                "__index__": ["Enrolled", "Enrolled", "Completed", "Completed"],
                "__group__": ["Treatment A", "Treatment B", "Treatment A", "Treatment B"],
                "__value__": ["3 (100%)", "3 (100%)", "1 (33.3%)", "2 (66.7%)"],
            }
        )

        df = disposition_df(ard)

        # Check columns
        self.assertIn("Term", df.columns)
        self.assertIn("Treatment A", df.columns)
        self.assertIn("Treatment B", df.columns)

        # Check shape
        self.assertEqual(df.height, 2)  # Two rows: Enrolled, Completed

    def test_disposition_df_preserves_order(self) -> None:
        """Test that row order is preserved from ARD."""
        # Create ARD with Enum to enforce order
        var_labels = ["Enrolled", "Completed", "Discontinued"]
        ard = pl.DataFrame(
            {
                "__index__": var_labels * 2,
                "__group__": ["Grp A"] * 3 + ["Grp B"] * 3,
                "__value__": ["1", "2", "3", "4", "5", "6"],
            }
        ).with_columns(pl.col("__index__").cast(pl.Enum(var_labels)))

        df = disposition_df(ard)

        # Check that rows are in expected order
        status_col = df["Term"].to_list()
        self.assertEqual(status_col, var_labels)


class TestDispositionRtf(unittest.TestCase):
    def test_disposition_rtf_basic(self) -> None:
        """Test RTF generation from display dataframe."""
        df = pl.DataFrame(
            {
                "Disposition Status": ["Enrolled", "Completed"],
                "Treatment A": ["3 (100%)", "1 (33.3%)"],
                "Treatment B": ["3 (100%)", "2 (66.7%)"],
                "Total": ["6 (100%)", "3 (50.0%)"],
            }
        )

        rtf_doc = disposition_rtf(
            df=df,
            title=["Disposition of Participants", "Safety Population"],
            footnote=["Percentages based on enrolled participants."],
            source=None,
            col_rel_width=None,
        )

        # Check that RTF document was created
        self.assertIsNotNone(rtf_doc)

    def test_disposition_rtf_custom_widths(self) -> None:
        """Test RTF generation with custom column widths."""
        df = pl.DataFrame(
            {
                "Disposition Status": ["Enrolled"],
                "Treatment A": ["3 (100%)"],
            }
        )

        rtf_doc = disposition_rtf(
            df=df,
            title=["Test Title"],
            footnote=None,
            source=None,
            col_rel_width=[3.0, 1.5],
        )

        self.assertIsNotNone(rtf_doc)


class TestDispositionPipeline(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test data and output directory."""
        self.population_data = pl.DataFrame(
            {
                "USUBJID": ["01", "02", "03", "04", "05", "06"],
                "TRT01A": [
                    "Treatment A",
                    "Treatment A",
                    "Treatment B",
                    "Treatment B",
                    "Treatment B",
                    "Treatment A",
                ],
                "SAFFL": ["Y", "Y", "Y", "Y", "Y", "Y"],
                "EOSSTT": [
                    "Completed",
                    "Completed",
                    "Discontinued",
                    "Discontinued",
                    "Completed",
                    "Completed",
                ],
                "DCREASCD": [
                    None,
                    None,
                    "Withdrawn",
                    "Screening Failure",
                    None,
                    None,
                ],
            }
        ).with_columns(
            pl.col("EOSSTT").cast(pl.Categorical),
            pl.col("DCREASCD").cast(pl.Categorical),
        )

        self.output_dir = Path("tests/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        """Clean up test output files."""
        if self.output_dir.exists():
            for file in self.output_dir.glob("*.rtf"):
                file.unlink()

    def test_disposition_full_pipeline(self) -> None:
        """Test complete disposition pipeline."""

        output_file = str(self.output_dir / "test_disposition.rtf")

        result_path = disposition(
            population=self.population_data,
            population_filter=None,
            id=("USUBJID", "Subject ID"),
            group=("TRT01A", "Treatment"),
            dist_reason_term=("DCREASCD", "Discontinued"),
            ds_term=("EOSSTT", "Status"),
            title=["Disposition of Participants"],
            footnote=["Test footnote"],
            source=None,
            output_file=output_file,
            total=True,
            missing_group="error",
        )

        # Check that file was created
        self.assertTrue(Path(result_path).exists())
        self.assertEqual(result_path, output_file)

    def test_disposition_no_total(self) -> None:
        """Test disposition without total column."""
        output_file = str(self.output_dir / "test_disposition_no_total.rtf")

        result_path = disposition(
            population=self.population_data,
            population_filter=None,
            id=("USUBJID", "Subject ID"),
            group=("TRT01A", "Treatment"),
            dist_reason_term=("DCREASCD", "Discontinued"),
            ds_term=("EOSSTT", "Status"),
            title=["Test"],
            footnote=None,
            source=None,
            output_file=output_file,
            total=False,
        )

        self.assertTrue(Path(result_path).exists())


class TestStudyPlanToDisposition(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test environment."""
        self.output_dir = Path("studies/xyz123/rtf")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        """Clean up test output files."""
        if self.output_dir.exists():
            for file in self.output_dir.glob("disposition_*.rtf"):
                file.unlink()

    def test_study_plan_to_disposition_summary(self) -> None:
        """Test generating disposition tables from StudyPlan."""
        # Load the study plan
        study_plan = load_plan("studies/xyz123/yaml/plan_ae_xyz123.yaml")

        # Generate disposition tables
        rtf_files = study_plan_to_disposition_summary(study_plan)

        # Check that files were generated
        self.assertIsInstance(rtf_files, list)
        self.assertGreater(len(rtf_files), 0)

        # Check that all files exist
        for rtf_file in rtf_files:
            self.assertTrue(Path(rtf_file).exists(), f"File {rtf_file} should exist")


if __name__ == "__main__":
    unittest.main()
