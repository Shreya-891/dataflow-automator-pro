"""
DataFlow Automator Pro - Excel & Data Processing Module
Provides automated ingestion, comprehensive data cleaning, statistical analysis,
pivot aggregation, and styled multi-sheet Excel report generation.
"""

import os
import re
import json
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from core.logger import logger
from core.exceptions import DataProcessingError


def load_dataset(file_path: str, sheet_name: Optional[Union[str, int]] = 0) -> pd.DataFrame:
    """
    Ingest tabular dataset from CSV, TSV, XLSX, XLS, or JSON.
    """
    if not os.path.exists(file_path):
        raise DataProcessingError(f"Data file not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext == ".tsv":
            df = pd.read_csv(file_path, sep="\t")
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        elif ext == ".json":
            df = pd.read_json(file_path)
        else:
            raise DataProcessingError(f"Unsupported file format: {ext}")

        logger.info(f"Loaded dataset '{os.path.basename(file_path)}' with shape {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Error loading dataset {file_path}: {e}")
        raise DataProcessingError(f"Failed to load dataset: {file_path}", {"error": str(e)})


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names to clean snake_case."""
    df = df.copy()
    cleaned = []
    for col in df.columns:
        c = str(col).strip()
        c = re.sub(r'[^\w\s-]', '', c)
        c = re.sub(r'[-\s]+', '_', c).lower()
        cleaned.append(c)
    df.columns = cleaned
    return df


def clean_dataset(
    df: pd.DataFrame,
    drop_duplicates: bool = True,
    standardize_names: bool = True,
    fill_missing: Optional[Dict[str, Any]] = None,
    default_fill_strategy: str = "auto",
    convert_currencies: bool = True
) -> Dict[str, Any]:
    """
    Automated dataset cleaning pipeline.
    Strategies for missing values: 'auto', 'mean', 'median', 'mode', 'drop', 'none'
    """
    df = df.copy()
    initial_rows = len(df)
    report = {
        "initial_rows": initial_rows,
        "initial_columns": len(df.columns),
        "duplicates_removed": 0,
        "missing_values_handled": 0,
        "conversions": []
    }

    try:
        if standardize_names:
            df = clean_column_names(df)

        if drop_duplicates:
            dups = df.duplicated().sum()
            df = df.drop_duplicates().reset_index(drop=True)
            report["duplicates_removed"] = int(dups)

        # Convert currency or formatted strings to numeric where applicable
        if convert_currencies:
            for col in df.columns:
                if df[col].dtype == object:
                    # check if sample values look like currency: $1,234.50 or €500 or 45%
                    sample_series = df[col].dropna().astype(str)
                    if sample_series.empty:
                        continue
                    if sample_series.str.match(r'^\s*[\$€£₹]?\s*-?[\d,]+(\.\d+)?%?\s*$').mean() > 0.7:
                        clean_series = sample_series.str.replace(r'[\$€£₹,\s%]', '', regex=True)
                        try:
                            df[col] = pd.to_numeric(clean_series)
                            report["conversions"].append(f"Converted '{col}' to numeric")
                        except Exception:
                            pass

        # Handle missing values
        missing_count = int(df.isna().sum().sum())
        report["missing_values_before"] = missing_count

        if fill_missing:
            for col, val in fill_missing.items():
                if col in df.columns:
                    df[col] = df[col].fillna(val)

        if default_fill_strategy == "drop":
            df = df.dropna().reset_index(drop=True)
        elif default_fill_strategy == "auto":
            for col in df.columns:
                if df[col].isna().sum() > 0:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = df[col].fillna(df[col].median())
                    elif pd.api.types.is_datetime64_any_dtype(df[col]):
                        df[col] = df[col].bfill().ffill()
                    else:
                        mode_val = df[col].mode()
                        fill_val = mode_val.iloc[0] if not mode_val.empty else "Unknown"
                        df[col] = df[col].fillna(fill_val)

        report["final_rows"] = len(df)
        report["final_columns"] = len(df.columns)
        report["missing_values_after"] = int(df.isna().sum().sum())
        logger.info(f"Dataset cleaning completed. Rows: {initial_rows} -> {len(df)}")

        return {
            "df": df,
            "report": report
        }
    except Exception as e:
        logger.error(f"Error during dataset cleaning: {e}")
        raise DataProcessingError("Dataset cleaning failed", {"error": str(e)})


def get_dataset_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate comprehensive summary statistics, column types, and sample records."""
    try:
        stats = {
            "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "missing_counts": {col: int(count) for col, count in df.isna().sum().items()},
            "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB"
        }

        # Numeric column summaries
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        numeric_summary = {}
        for col in numeric_cols:
            series = df[col].dropna()
            if not series.empty:
                numeric_summary[col] = {
                    "mean": round(float(series.mean()), 2),
                    "median": round(float(series.median()), 2),
                    "std": round(float(series.std()), 2) if len(series) > 1 else 0.0,
                    "min": round(float(series.min()), 2),
                    "max": round(float(series.max()), 2),
                    "sum": round(float(series.sum()), 2)
                }
        stats["numeric_summary"] = numeric_summary

        # Categorical column top values
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        cat_summary = {}
        for col in cat_cols:
            val_counts = df[col].value_counts().head(5).to_dict()
            cat_summary[col] = {str(k): int(v) for k, v in val_counts.items()}
        stats["categorical_summary"] = cat_summary

        # Preview rows
        stats["preview"] = json.loads(df.head(10).to_json(orient="records", date_format="iso"))

        return stats
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise DataProcessingError("Summary generation failed", {"error": str(e)})


def generate_pivot_table(
    df: pd.DataFrame,
    index_col: str,
    values_col: str,
    agg_func: str = "sum",
    columns_col: Optional[str] = None
) -> pd.DataFrame:
    """Generate a pivot table aggregated by specified function."""
    try:
        valid_funcs = {"sum": "sum", "mean": "mean", "count": "count", "min": "min", "max": "max"}
        func = valid_funcs.get(agg_func.lower(), "sum")

        pivot = pd.pivot_table(
            df,
            index=index_col,
            columns=columns_col if columns_col and columns_col in df.columns else None,
            values=values_col,
            aggfunc=func,
            fill_value=0
        )
        if isinstance(pivot, pd.DataFrame):
            pivot = pivot.reset_index()
        return pivot
    except Exception as e:
        logger.error(f"Pivot table generation failed: {e}")
        raise DataProcessingError(f"Pivot calculation failed: {e}")


def export_styled_excel(
    sheets_dict: Dict[str, pd.DataFrame],
    output_path: str,
    title: str = "Executive Data Report"
) -> str:
    """
    Export one or more DataFrames into a beautifully styled Excel workbook with:
    - Corporate Navy/Cyan header theme
    - Zebra striped rows
    - Automatic column sizing
    - Thin borders & formatted numbers
    - Auto-filter
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb = openpyxl.Workbook()
        # remove default sheet
        wb.remove(wb.active)

        # Style Definitions
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid") # Dark Navy Slate
        title_font = Font(name="Segoe UI", size=15, bold=True, color="0F172A")
        sub_font = Font(name="Segoe UI", size=9, italic=True, color="64748B")

        row_fill_even = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        row_fill_odd = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        total_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        total_font = Font(name="Segoe UI", size=10, bold=True, color="0F172A")

        thin_side = Side(style="thin", color="E2E8F0")
        border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        for sheet_name, df in sheets_dict.items():
            clean_sheet_name = sheet_name[:30].replace("/", "-").replace("\\", "-")
            ws = wb.create_sheet(title=clean_sheet_name)
            ws.views.sheetView[0].showGridLines = True

            # Write Title Block
            ws.merge_cells("A1:F1")
            ws["A1"] = f"{title} - {clean_sheet_name}"
            ws["A1"].font = title_font

            ws.merge_cells("A2:F2")
            ws["A2"] = f"Generated by DataFlow Automator Pro | Total Records: {len(df)}"
            ws["A2"].font = sub_font

            # Start table at row 4
            start_row = 4

            # Write Headers
            for col_idx, col_name in enumerate(df.columns, start=1):
                cell = ws.cell(row=start_row, column=col_idx, value=str(col_name).replace("_", " ").title())
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = border
                ws.row_dimensions[start_row].height = 26

            # Write Data Rows
            numeric_col_indices = [
                idx for idx, col in enumerate(df.columns, start=1)
                if pd.api.types.is_numeric_dtype(df[col])
            ]

            for row_idx, row_data in enumerate(df.values, start=start_row + 1):
                fill = row_fill_even if row_idx % 2 == 0 else row_fill_odd
                ws.row_dimensions[row_idx].height = 20

                for col_idx, val in enumerate(row_data, start=1):
                    # Handle NaN / None
                    if pd.isna(val):
                        val = ""
                    cell = ws.cell(row=row_idx, column=col_idx, value=val)
                    cell.fill = fill
                    cell.border = border
                    cell.font = Font(name="Segoe UI", size=10)

                    # Number formatting
                    if isinstance(val, (int, float)):
                        cell.alignment = Alignment(horizontal="right", vertical="center")
                        if isinstance(val, float):
                            cell.number_format = "#,##0.00"
                        else:
                            cell.number_format = "#,##0"
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="center")

            # Add Total Row for numeric columns if there are rows
            if len(df) > 0 and numeric_col_indices:
                total_row_idx = start_row + len(df) + 1
                ws.row_dimensions[total_row_idx].height = 22
                first_cell = ws.cell(row=total_row_idx, column=1, value="TOTAL / SUMMARY")
                first_cell.font = total_font
                first_cell.fill = total_fill
                first_cell.border = border

                for col_idx in range(1, len(df.columns) + 1):
                    cell = ws.cell(row=total_row_idx, column=col_idx)
                    cell.fill = total_fill
                    cell.border = border
                    cell.font = total_font
                    if col_idx in numeric_col_indices:
                        col_letter = get_column_letter(col_idx)
                        formula = f"=SUM({col_letter}{start_row + 1}:{col_letter}{total_row_idx - 1})"
                        cell.value = formula
                        cell.number_format = "#,##0.00"
                        cell.alignment = Alignment(horizontal="right", vertical="center")

            # Auto-fit column widths
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.row < start_row:
                        continue
                    val_str = str(cell.value or "")
                    max_len = max(max_len, len(val_str))
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        wb.save(output_path)
        logger.info(f"Exported styled Excel report to '{output_path}'")
        return output_path
    except Exception as e:
        logger.error(f"Failed to export styled Excel to {output_path}: {e}")
        raise DataProcessingError(f"Excel export failed: {e}")
