"""
DataFlow Automator Pro - Command Line Interface (CLI)
Provides interactive and non-interactive terminal commands for all file automation,
Excel processing, PDF generation, email dispatching, web scraping, and pipeline orchestration.
"""

import os
import sys
import argparse
import json
from core.logger import logger
from core.file_manager import organize_directory, find_duplicates, batch_rename, clean_stale_files, get_directory_stats, create_archive
from core.excel_processor import load_dataset, clean_dataset, get_dataset_summary, export_styled_excel, generate_pivot_table
from core.pdf_engine import generate_executive_report, generate_invoice_pdf
from core.email_automator import EmailDispatcher
from core.web_scraper import WebScraper
from core.orchestrator import WorkflowOrchestrator


def print_banner():
    banner = """\033[36m
  ╔═════════════════════════════════════════════════════════════════════════╗
  ║    ⚡ DataFlow Automator Pro - Advanced Automation & Intelligence Suite ║
  ╚═════════════════════════════════════════════════════════════════════════╝\033[0m"""
    print(banner)


def handle_organize(args):
    print(f"\n📁 Organizing Directory: {args.path}")
    print(f"   Strategy: {args.rule} | Dry Run: {args.dry_run}")
    res = organize_directory(args.path, target_dir=args.target, rule_type=args.rule, dry_run=args.dry_run)
    print(f"\n✓ Completed: {res['moved_count']} files processed.")
    for action in res["actions"][:10]:
        print(f"  → [{action['status'].upper()}] {action['file']} => {action['destination_folder']}")
    if len(res["actions"]) > 10:
        print(f"  ... and {len(res['actions']) - 10} more files.")


def handle_duplicates(args):
    print(f"\n🔍 Scanning for Duplicate Files in: {args.path}")
    res = find_duplicates(args.path, algo=args.algo, delete_duplicates=args.delete)
    print(f"\nFound {res['duplicate_groups_count']} duplicate groups ({res['total_duplicates_found']} duplicate files).")
    print(f"Total Wasted Space: {res['total_wasted_space']}")
    for g in res["groups"][:5]:
        print(f"\n  • Original: {g['original']}")
        for d in g["duplicates"]:
            print(f"    - Dup: {d} ({g['file_size']})")
    if args.delete:
        print(f"\n✓ Deleted {res['deleted_count']} duplicate copies.")


def handle_rename(args):
    print(f"\n✏️ Batch Renaming in: {args.path}")
    res = batch_rename(
        args.path,
        pattern=args.pattern or "",
        replacement=args.replace or "",
        prefix=args.prefix or "",
        suffix=args.suffix or "",
        numbering=args.numbering,
        case_style=args.case,
        dry_run=args.dry_run
    )
    print(f"\n✓ Processed {res['total_files']} files. Renamed: {res['renamed_count']}")
    for item in res["items"][:10]:
        print(f"  {item['old_name']}  ───►  {item['new_name']}")


def handle_excel(args):
    print(f"\n📊 Ingesting & Cleaning Dataset: {args.input}")
    df = load_dataset(args.input)
    clean_res = clean_dataset(df)
    cleaned_df = clean_res["df"]
    print(f"Cleaned Shape: {cleaned_df.shape} (Removed {clean_res['report']['duplicates_removed']} duplicates)")

    if args.output:
        export_styled_excel({"Cleaned_Data": cleaned_df}, args.output, title="DataFlow Processed Dataset")
        print(f"✓ Exported styled Excel to: {args.output}")


def handle_scrape(args):
    print(f"\n🌐 Web Scraping: Source={args.source}")
    scraper = WebScraper()
    if args.source == "books":
        df = scraper.scrape_books_catalog(max_pages=args.pages)
    elif args.source == "quotes":
        df = scraper.scrape_quotes_feed(max_pages=args.pages)
    elif args.source == "news":
        df = scraper.scrape_hacker_news(limit=args.pages * 10)
    else:
        print("Unknown source preset.")
        return

    print(f"\n✓ Successfully scraped {len(df)} records.")
    print(df.head(5).to_string())

    if args.output:
        if args.output.endswith(".xlsx"):
            export_styled_excel({"Scraped_Data": df}, args.output, title=f"Scraped {args.source.title()} Data")
        else:
            df.to_csv(args.output, index=False)
        print(f"✓ Saved records to {args.output}")


def handle_pipeline(args):
    print(f"\n⚡ Running Workflow Pipeline: {args.name}")
    orch = WorkflowOrchestrator()
    if args.name == "ecommerce":
        res = orch.run_ecommerce_intelligence_pipeline(recipient_email=args.email, pages=args.pages)
    elif args.name == "sales" and args.input:
        res = orch.run_sales_processing_pipeline(dataset_path=args.input, recipient_email=args.email)
    else:
        print("Please specify a valid pipeline and required arguments.")
        return
    print(f"\n✓ Pipeline finished successfully! Status: {res['status']}")
    print(f"  Artifacts: {res.get('artifacts', {})}")


def handle_server(args):
    print_banner()
    print(f"\n🚀 Starting DataFlow Automator Pro Web Server on http://{args.host}:{args.port}")
    import app
    app.app.run(host=args.host, port=args.port, debug=args.debug)


def main():
    parser = argparse.ArgumentParser(
        description="DataFlow Automator Pro - Advanced File & Data Processing Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. organize
    p_org = subparsers.add_parser("organize", help="Organize files by category, extension, date, or size")
    p_org.add_argument("path", help="Source directory path")
    p_org.add_argument("--target", help="Destination directory path (default: source)")
    p_org.add_argument("--rule", choices=["category", "extension", "date", "size"], default="category", help="Sorting rule")
    p_org.add_argument("--dry-run", action="store_true", help="Simulate without moving files")

    # 2. duplicates
    p_dup = subparsers.add_parser("duplicates", help="Find and clean duplicate files by hash")
    p_dup.add_argument("path", help="Directory path to scan")
    p_dup.add_argument("--algo", choices=["sha256", "md5"], default="sha256", help="Hash algorithm")
    p_dup.add_argument("--delete", action="store_true", help="Delete duplicate copies")

    # 3. rename
    p_ren = subparsers.add_parser("rename", help="Batch rename files")
    p_ren.add_argument("path", help="Directory path")
    p_ren.add_argument("--pattern", help="Regex or text pattern to find")
    p_ren.add_argument("--replace", help="Replacement text")
    p_ren.add_argument("--prefix", help="Add prefix")
    p_ren.add_argument("--suffix", help="Add suffix")
    p_ren.add_argument("--numbering", action="store_true", help="Append sequential numbering")
    p_ren.add_argument("--case", choices=["lower", "upper", "title", "slug"], help="Convert case style")
    p_ren.add_argument("--dry-run", action="store_true", help="Preview renames without executing")

    # 4. excel
    p_exc = subparsers.add_parser("excel", help="Clean dataset and export styled Excel")
    p_exc.add_argument("input", help="Path to CSV/XLSX/JSON")
    p_exc.add_argument("--output", help="Path to save styled XLSX")

    # 5. scrape
    p_scr = subparsers.add_parser("scrape", help="Scrape live web feeds")
    p_scr.add_argument("source", choices=["books", "quotes", "news"], help="Preset scraper source")
    p_scr.add_argument("--pages", type=int, default=2, help="Number of pages/batches")
    p_scr.add_argument("--output", help="Save output to CSV or XLSX")

    # 6. pipeline
    p_pip = subparsers.add_parser("pipeline", help="Run end-to-end automated multi-step pipeline")
    p_pip.add_argument("name", choices=["ecommerce", "sales"], help="Pipeline name")
    p_pip.add_argument("--email", default="stakeholder@company.com", help="Recipient email")
    p_pip.add_argument("--pages", type=int, default=2, help="Pages to scrape (for ecommerce)")
    p_pip.add_argument("--input", help="Dataset path (for sales pipeline)")

    # 7. server
    p_srv = subparsers.add_parser("server", help="Launch interactive Web Dashboard")
    p_srv.add_argument("--host", default="127.0.0.1", help="Host address")
    p_srv.add_argument("--port", type=int, default=5000, help="Port number")
    p_srv.add_argument("--debug", action="store_true", help="Enable Flask debug mode")

    if len(sys.argv) == 1:
        print_banner()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.command == "organize":
        handle_organize(args)
    elif args.command == "duplicates":
        handle_duplicates(args)
    elif args.command == "rename":
        handle_rename(args)
    elif args.command == "excel":
        handle_excel(args)
    elif args.command == "scrape":
        handle_scrape(args)
    elif args.command == "pipeline":
        handle_pipeline(args)
    elif args.command == "server":
        handle_server(args)


if __name__ == "__main__":
    main()
