"""
DataFlow Automator Pro - Flask Web Application & REST API
Powers the interactive cyber-modern web dashboard with live endpoints for all automation modules.
"""

import os
import io
import json
import traceback
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pandas as pd

from core.logger import logger, get_ui_logs, clear_ui_logs
from core.exceptions import DataFlowException
from core.file_manager import (
    organize_directory, find_duplicates, batch_rename, clean_stale_files,
    scan_directory, get_directory_stats, create_archive
)
from core.excel_processor import (
    load_dataset, clean_dataset, get_dataset_summary, generate_pivot_table, export_styled_excel
)
from core.pdf_engine import generate_executive_report, generate_invoice_pdf
from core.email_automator import EmailDispatcher, get_sent_emails
from core.web_scraper import WebScraper
from core.orchestrator import WorkflowOrchestrator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
SAMPLE_DIR = os.path.join(BASE_DIR, "data", "sample_files")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64 MB max upload

# In-memory active dataset cache for interactive web studio
_ACTIVE_DATASETS = {}


@app.route("/")
def index():
    return render_template("index.html")


# ----------------- SYSTEM & LOGS API -----------------

@app.route("/api/logs", methods=["GET"])
def get_logs():
    limit = request.args.get("limit", 50, type=int)
    logs = get_ui_logs(limit)
    return jsonify({"success": True, "logs": logs})


@app.route("/api/logs/clear", methods=["POST"])
def clear_logs():
    clear_ui_logs()
    return jsonify({"success": True, "message": "Logs cleared"})


@app.route("/api/stats", methods=["GET"])
def get_system_stats():
    import psutil
    stats = {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage(BASE_DIR).percent,
        "active_datasets": len(_ACTIVE_DATASETS),
        "sent_emails": len(get_sent_emails(100)),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return jsonify({"success": True, "stats": stats})


# ----------------- FILE AUTOMATION API -----------------

@app.route("/api/files/scan", methods=["POST"])
def api_scan_files():
    data = request.json or {}
    directory = data.get("directory", SAMPLE_DIR)
    try:
        items = scan_directory(directory)
        stats = get_directory_stats(directory)
        return jsonify({"success": True, "directory": directory, "items": items, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/files/organize", methods=["POST"])
def api_organize_files():
    data = request.json or {}
    source_dir = data.get("source_dir", SAMPLE_DIR)
    rule_type = data.get("rule_type", "category")
    dry_run = data.get("dry_run", False)

    try:
        res = organize_directory(source_dir, rule_type=rule_type, dry_run=dry_run)
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/files/duplicates", methods=["POST"])
def api_find_duplicates():
    data = request.json or {}
    directory = data.get("directory", SAMPLE_DIR)
    delete = data.get("delete", False)
    algo = data.get("algo", "sha256")

    try:
        res = find_duplicates(directory, algo=algo, delete_duplicates=delete)
        return jsonify({"success": True, "data": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/files/rename", methods=["POST"])
def api_batch_rename():
    data = request.json or {}
    directory = data.get("directory", SAMPLE_DIR)
    try:
        res = batch_rename(
            directory,
            pattern=data.get("pattern", ""),
            replacement=data.get("replacement", ""),
            prefix=data.get("prefix", ""),
            suffix=data.get("suffix", ""),
            numbering=data.get("numbering", False),
            case_style=data.get("case_style"),
            dry_run=data.get("dry_run", False)
        )
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ----------------- EXCEL & DATA STUDIO API -----------------

@app.route("/api/data/upload", methods=["POST"])
def api_upload_data():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    try:
        df = load_dataset(save_path)
        _ACTIVE_DATASETS["current"] = df
        summary = get_dataset_summary(df)
        return jsonify({"success": True, "filename": filename, "path": save_path, "summary": summary})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/data/clean", methods=["POST"])
def api_clean_data():
    df = _ACTIVE_DATASETS.get("current")
    if df is None:
        return jsonify({"success": False, "error": "No active dataset loaded"}), 400

    data = request.json or {}
    try:
        res = clean_dataset(
            df,
            drop_duplicates=data.get("drop_duplicates", True),
            standardize_names=data.get("standardize_names", True),
            default_fill_strategy=data.get("fill_strategy", "auto")
        )
        _ACTIVE_DATASETS["current"] = res["df"]
        summary = get_dataset_summary(res["df"])
        return jsonify({"success": True, "report": res["report"], "summary": summary})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/data/export", methods=["POST"])
def api_export_excel():
    df = _ACTIVE_DATASETS.get("current")
    if df is None:
        return jsonify({"success": False, "error": "No active dataset"}), 400

    data = request.json or {}
    title = data.get("title", "DataFlow Export")
    filename = f"Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    export_path = os.path.join(EXPORT_DIR, filename)

    try:
        export_styled_excel({"Report Data": df}, export_path, title=title)
        return jsonify({"success": True, "filename": filename, "download_url": f"/api/download/exports/{filename}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ----------------- PDF STUDIO API -----------------

@app.route("/api/pdf/generate-report", methods=["POST"])
def api_generate_pdf_report():
    data = request.json or {}
    title = data.get("title", "Executive Automated Summary")
    subtitle = data.get("subtitle", "DataFlow Automator Pro Intelligence Digest")
    summary = data.get("summary", "Automated system digest covering active operational metrics.")
    kpis = data.get("kpis", [{"label": "Total Tasks", "value": "128"}, {"label": "Success Rate", "value": "99.4%"}])
    table_headers = data.get("headers", ["Metric", "Value", "Status"])
    table_rows = data.get("rows", [["Files Processed", "1,240", "Passed"], ["Duplicates Cleaned", "45", "Cleaned"], ["Emails Dispatched", "88", "Delivered"]])

    filename = f"Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(EXPORT_DIR, filename)

    try:
        generate_executive_report(
            output_path=pdf_path,
            report_title=title,
            subtitle=subtitle,
            kpis=kpis,
            table_headers=table_headers,
            table_rows=table_rows,
            summary_text=summary
        )
        return jsonify({"success": True, "filename": filename, "download_url": f"/api/download/exports/{filename}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/pdf/generate-invoice", methods=["POST"])
def api_generate_invoice():
    data = request.json or {}
    client_name = data.get("client_name", "Acme Corporation")
    client_email = data.get("client_email", "billing@acme.com")
    items = data.get("items", [
        {"description": "Workflow Automation Implementation", "qty": 1, "rate": 1800.0},
        {"description": "Custom Scraping Pipeline Integration", "qty": 2, "rate": 450.0}
    ])
    inv_num = f"INV-{datetime.now().strftime('%Y%m%d-%H%M')}"
    filename = f"Invoice_{inv_num}.pdf"
    pdf_path = os.path.join(EXPORT_DIR, filename)

    try:
        generate_invoice_pdf(pdf_path, inv_num, client_name, client_email, items)
        return jsonify({"success": True, "filename": filename, "download_url": f"/api/download/exports/{filename}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ----------------- WEB SCRAPER API -----------------

@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    data = request.json or {}
    source = data.get("source", "books")
    pages = data.get("pages", 1)
    url = data.get("url", "")

    scraper = WebScraper()
    try:
        if source == "books":
            df = scraper.scrape_books_catalog(max_pages=pages)
            _ACTIVE_DATASETS["current"] = df
            summary = get_dataset_summary(df)
            return jsonify({"success": True, "records_count": len(df), "summary": summary})
        elif source == "quotes":
            df = scraper.scrape_quotes_feed(max_pages=pages)
            _ACTIVE_DATASETS["current"] = df
            summary = get_dataset_summary(df)
            return jsonify({"success": True, "records_count": len(df), "summary": summary})
        elif source == "news":
            df = scraper.scrape_hacker_news(limit=pages * 15)
            _ACTIVE_DATASETS["current"] = df
            summary = get_dataset_summary(df)
            return jsonify({"success": True, "records_count": len(df), "summary": summary})
        elif source == "custom" and url:
            res = scraper.scrape_custom_url(url)
            return jsonify({"success": True, "data": res})
        else:
            return jsonify({"success": False, "error": "Invalid source or missing URL"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ----------------- EMAIL CENTER API -----------------

@app.route("/api/email/send", methods=["POST"])
def api_send_email():
    data = request.json or {}
    to_email = data.get("to_email", "user@example.com")
    subject = data.get("subject", "DataFlow Automated Digest")
    template_name = data.get("template", "executive_report")
    mock_mode = data.get("mock_mode", True)
    custom_msg = data.get("message", "")
    attachments = data.get("attachments", [])

    # Map attachment filenames in exports/
    full_attachments = []
    for att in attachments:
        full_p = os.path.join(EXPORT_DIR, att)
        if os.path.exists(full_p):
            full_attachments.append(full_p)

    dispatcher = EmailDispatcher(mock_mode=mock_mode)
    try:
        res = dispatcher.send_email(
            to_addresses=[to_email],
            subject=subject,
            template_name=template_name,
            context={"recipient_name": to_email.split("@")[0].title(), "message": custom_msg},
            attachments=full_attachments
        )
        return jsonify({"success": True, "result": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/email/history", methods=["GET"])
def api_email_history():
    history = get_sent_emails(50)
    return jsonify({"success": True, "emails": history})


# ----------------- PIPELINES API -----------------

@app.route("/api/pipeline/run", methods=["POST"])
def api_run_pipeline():
    data = request.json or {}
    pipe_name = data.get("pipeline", "ecommerce")
    email = data.get("email", "executive@dataflowpro.local")

    orch = WorkflowOrchestrator()
    try:
        if pipe_name == "ecommerce":
            res = orch.run_ecommerce_intelligence_pipeline(recipient_email=email, pages=1)
            return jsonify({"success": True, "result": res})
        else:
            return jsonify({"success": False, "error": "Unknown pipeline"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ----------------- DOWNLOADS & ASSETS -----------------

@app.route("/api/download/exports/<filename>")
def download_export(filename):
    return send_from_directory(EXPORT_DIR, filename, as_attachment=True)


@app.route("/api/download/project-report")
def download_project_report():
    report_path = os.path.join(DOCS_DIR, "Project_Report.pdf")
    if not os.path.exists(report_path):
        from generate_report import build_project_report
        build_project_report(report_path)
    return send_file(report_path, as_attachment=False, mimetype="application/pdf")


if __name__ == "__main__":
    logger.info("Starting DataFlow Automator Pro Flask server on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
