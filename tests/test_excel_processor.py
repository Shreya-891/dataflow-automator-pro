"""
Unit tests for Excel & Data Processing Module.
"""

import os
import tempfile
import unittest
import pandas as pd
from core.excel_processor import (
    load_dataset, clean_dataset, clean_column_names, get_dataset_summary,
    generate_pivot_table, export_styled_excel
)


class TestExcelProcessor(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.sample_csv = os.path.join(self.test_dir, "sample_sales.csv")

        # Create raw sample data with messy headers, duplicates, missing values, currency strings
        data = {
            "Product Name ": ["Laptop Pro", "Wireless Mouse", "Laptop Pro", "USB-C Hub", "4K Monitor", "Keyboard RGB"],
            "Category ": ["Hardware", "Accessories", "Hardware", "Accessories", "Hardware", "Accessories"],
            "Price USD": ["$1,200.00", "$25.50", "$1,200.00", "$45.00", "$350.00", "$80.00"],
            "Units Sold": [5, 40, 5, 25, 8, None],
            "Region": ["North", "South", "North", "West", "East", "North"]
        }
        pd.DataFrame(data).to_csv(self.sample_csv, index=False)

    def test_load_and_clean_dataset(self):
        df = load_dataset(self.sample_csv)
        self.assertEqual(len(df), 6)

        clean_res = clean_dataset(df, drop_duplicates=True, standardize_names=True)
        cleaned_df = clean_res["df"]

        # Duplicate row removed
        self.assertEqual(len(cleaned_df), 5)
        self.assertIn("product_name", cleaned_df.columns)
        self.assertIn("price_usd", cleaned_df.columns)
        self.assertTrue(pd.api.types.is_numeric_dtype(cleaned_df["price_usd"]))
        # Missing units_sold filled
        self.assertFalse(cleaned_df["units_sold"].isna().any())

    def test_summary_and_pivot(self):
        df = load_dataset(self.sample_csv)
        cleaned = clean_dataset(df)["df"]
        summary = get_dataset_summary(cleaned)
        self.assertIn("numeric_summary", summary)
        self.assertIn("price_usd", summary["numeric_summary"])

        pivot = generate_pivot_table(cleaned, index_col="category", values_col="price_usd", agg_func="sum")
        self.assertGreater(len(pivot), 0)

    def test_export_styled_excel(self):
        df = load_dataset(self.sample_csv)
        cleaned = clean_dataset(df)["df"]
        out_excel = os.path.join(self.test_dir, "styled_output.xlsx")
        export_styled_excel({"Clean Data": cleaned}, out_excel, title="Sales Performance")
        self.assertTrue(os.path.exists(out_excel))
        self.assertGreater(os.path.getsize(out_excel), 0)


if __name__ == "__main__":
    unittest.main()
