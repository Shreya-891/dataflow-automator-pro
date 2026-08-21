"""
DataFlow Automator Pro - Workflow Orchestration Engine
Chains scraping, data cleaning, Excel synthesis, PDF generation, and email dispatch into automated pipelines.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional

from core.logger import logger
from core.exceptions import WorkflowExecutionError
from core.file_manager import organize_directory, find_duplicates, clean_stale_files
from core.excel_processor import load_dataset, clean_dataset, get_dataset_summary, generate_pivot_table, export_styled_excel
from core.pdf_engine import generate_executive_report, generate_invoice_pdf
from core.email_automator import EmailDispatcher
from core.web_scraper import WebScraper

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)


class WorkflowOrchestrator:
    """
    Executes automated end-to-end multi-step pipelines.
    """
    def __init__(self, email_dispatcher: Optional[EmailDispatcher] = None):
        self.email_dispatcher = email_dispatcher or EmailDispatcher(mock_mode=True)
        self.scraper = WebScraper()

    def run_ecommerce_intelligence_pipeline(
        self,
        recipient_email: str = "stakeholder@company.com",
        pages: int = 2
    ) -> Dict[str, Any]:
        """
        End-to-End Pipeline:
        1. Scrape catalog data
        2. Clean and structure in Pandas
        3. Export styled Excel workbook
        4. Generate Executive PDF report with chart & KPIs
        5. Email attachments to stakeholder
        """
        logger.info(">>> Starting E-Commerce Intelligence Pipeline")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {"steps": []}

        try:
            # Step 1: Scrape
            logger.info("Step 1: Scraping e-commerce catalog...")
            df = self.scraper.scrape_books_catalog(max_pages=pages)
            results["steps"].append({"step": "Scrape", "status": "success", "records": len(df)})

            # Step 2: Clean
            logger.info("Step 2: Cleaning scraped data...")
            clean_res = clean_dataset(df)
            clean_df = clean_res["df"]
            results["steps"].append({"step": "Data Cleaning", "status": "success", "cleaned_records": len(clean_df)})

            # Step 3: Excel Export
            logger.info("Step 3: Generating styled Excel report...")
            excel_path = os.path.join(EXPORT_DIR, f"Ecommerce_Catalog_{timestamp}.xlsx")
            export_styled_excel(
                {"All Products": clean_df, "In Stock": clean_df[clean_df["in_stock"] == True]},
                excel_path,
                title="E-Commerce Catalog & Pricing Digest"
            )
            results["steps"].append({"step": "Excel Generation", "status": "success", "file": excel_path})

            # Step 4: PDF Generation
            logger.info("Step 4: Synthesizing Executive PDF report with visualization...")
            pdf_path = os.path.join(EXPORT_DIR, f"Ecommerce_Report_{timestamp}.pdf")
            avg_price = float(clean_df["price_gbp"].mean()) if not clean_df.empty else 0.0
            in_stock_count = int(clean_df["in_stock"].sum()) if not clean_df.empty else 0

            # Rating distribution for chart
            rating_counts = clean_df["rating_stars"].value_counts().sort_index().to_dict()
            chart_data = {f"{k} Stars": int(v) for k, v in rating_counts.items()}

            kpis = [
                {"label": "Total Products", "value": f"{len(clean_df)}"},
                {"label": "Average Price", "value": f"£{avg_price:.2f}"},
                {"label": "In-Stock Items", "value": f"{in_stock_count}"},
                {"label": "Top Rated (5★)", "value": f"{rating_counts.get(5, 0)}"}
            ]

            table_rows = [
                [row["title"][:35], f"£{row['price_gbp']:.2f}", f"{row['rating_stars']}★", "Yes" if row["in_stock"] else "No"]
                for _, row in clean_df.head(20).iterrows()
            ]

            generate_executive_report(
                output_path=pdf_path,
                report_title="E-Commerce Catalog Intelligence Report",
                subtitle="Automated Web Scraping & Pricing Audit",
                kpis=kpis,
                table_headers=["Title", "Price (GBP)", "Rating", "Availability"],
                table_rows=table_rows,
                chart_config={
                    "type": "bar",
                    "title": "Product Rating Distribution",
                    "data": chart_data
                },
                summary_text=(
                    f"This automated market digest analyzed {len(clean_df)} live inventory items. "
                    f"The average product price is £{avg_price:.2f}, with {in_stock_count} units available in stock. "
                    "Complete dataset and visual breakdown are encapsulated in the attached reports."
                )
            )
            results["steps"].append({"step": "PDF Generation", "status": "success", "file": pdf_path})

            # Step 5: Email Dispatch
            logger.info("Step 5: Dispatching automated email digest...")
            mail_res = self.email_dispatcher.send_email(
                to_addresses=[recipient_email],
                subject=f"📊 E-Commerce Catalog Digest - {datetime.now().strftime('%b %d, %Y')}",
                template_name="executive_report",
                context={
                    "title": "E-Commerce Market Intelligence Digest",
                    "recipient_name": recipient_email.split("@")[0].title(),
                    "message": "Automated data harvesting and pricing synthesis finished successfully.",
                    "metrics": {
                        "Items Scraped": f"{len(clean_df)}",
                        "Avg Price": f"£{avg_price:.2f}",
                        "In Stock": f"{in_stock_count}"
                    }
                },
                attachments=[excel_path, pdf_path]
            )
            results["steps"].append({"step": "Email Dispatch", "status": "success", "email_id": mail_res.get("id")})
            results["status"] = "completed"
            results["artifacts"] = {"excel": excel_path, "pdf": pdf_path}
            logger.info(">>> E-Commerce Intelligence Pipeline completed successfully!")
            return results

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            raise WorkflowExecutionError(f"Pipeline failed at execution: {e}", {"details": str(e)})

    def run_sales_processing_pipeline(
        self,
        dataset_path: str,
        recipient_email: str = "management@company.com"
    ) -> Dict[str, Any]:
        """
        End-to-End Sales Processing: Ingest CSV/Excel -> Clean -> Pivot -> Excel + PDF Report -> Email.
        """
        logger.info(f">>> Starting Sales Processing Pipeline for '{dataset_path}'")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {"steps": []}

        try:
            # 1. Ingest & Clean
            raw_df = load_dataset(dataset_path)
            clean_res = clean_dataset(raw_df)
            df = clean_res["df"]
            results["steps"].append({"step": "Ingest & Clean", "records": len(df)})

            # 2. Identify numeric and categorical columns
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

            val_col = num_cols[0] if num_cols else df.columns[-1]
            idx_col = cat_cols[0] if cat_cols else df.columns[0]

            pivot_df = generate_pivot_table(df, index_col=idx_col, values_col=val_col, agg_func="sum")

            # 3. Export Styled Excel
            excel_path = os.path.join(EXPORT_DIR, f"Sales_Summary_{timestamp}.xlsx")
            export_styled_excel(
                {"Cleaned Data": df, "Pivot Summary": pivot_df},
                excel_path,
                title="Commercial Revenue Analysis"
            )
            results["steps"].append({"step": "Excel Generation", "file": excel_path})

            # 4. Generate PDF Report
            pdf_path = os.path.join(EXPORT_DIR, f"Sales_Executive_Report_{timestamp}.pdf")
            total_val = float(df[val_col].sum()) if pd.api.types.is_numeric_dtype(df[val_col]) else len(df)
            avg_val = float(df[val_col].mean()) if pd.api.types.is_numeric_dtype(df[val_col]) else 0

            # Build chart from pivot
            chart_dict = {}
            for _, row in pivot_df.head(6).iterrows():
                chart_dict[str(row[idx_col])[:12]] = float(row[val_col])

            kpis = [
                {"label": "Total Records", "value": f"{len(df):,}"},
                {"label": f"Total {val_col.title()}", "value": f"${total_val:,.2f}" if "price" in val_col or "amount" in val_col or "revenue" in val_col or "sales" in val_col else f"{total_val:,.0f}"},
                {"label": f"Avg {val_col.title()}", "value": f"${avg_val:,.2f}" if "price" in val_col or "amount" in val_col or "revenue" in val_col or "sales" in val_col else f"{avg_val:,.1f}"}
            ]

            table_rows = [
                [str(row[c]) for c in df.columns[:5]]
                for _, row in df.head(25).iterrows()
            ]

            generate_executive_report(
                output_path=pdf_path,
                report_title="Commercial Performance & Revenue Digest",
                subtitle="Financial Audit & Automated Synthesis",
                kpis=kpis,
                table_headers=[str(c).replace("_", " ").title() for c in df.columns[:5]],
                table_rows=table_rows,
                chart_config={
                    "type": "bar",
                    "title": f"{val_col.title()} by {idx_col.title()}",
                    "data": chart_dict
                },
                summary_text=f"This comprehensive sales audit summarized {len(df)} transactions across key operating segments."
            )
            results["steps"].append({"step": "PDF Generation", "file": pdf_path})

            # 5. Email
            mail_res = self.email_dispatcher.send_email(
                to_addresses=[recipient_email],
                subject=f"📈 Financial & Sales Performance Digest - {datetime.now().strftime('%b %d, %Y')}",
                template_name="executive_report",
                context={
                    "title": "Revenue Performance Digest",
                    "recipient_name": recipient_email.split("@")[0].title(),
                    "message": "The automated financial processing pipeline has parsed your data.",
                    "metrics": {
                        "Rows": f"{len(df)}",
                        "Metric Total": f"{total_val:,.2f}",
                        "Status": "Verified"
                    }
                },
                attachments=[excel_path, pdf_path]
            )
            results["steps"].append({"step": "Email Dispatch", "email_id": mail_res.get("id")})
            results["status"] = "completed"
            results["artifacts"] = {"excel": excel_path, "pdf": pdf_path}
            return results
        except Exception as e:
            logger.error(f"Sales pipeline failure: {e}")
            raise WorkflowExecutionError(f"Sales processing failed: {e}", {"details": str(e)})
