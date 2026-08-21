"""
Unit tests for PDF Engine, Email Automator, Web Scraper, and Orchestrator.
"""

import os
import tempfile
import unittest
from core.pdf_engine import generate_executive_report, generate_invoice_pdf
from core.email_automator import EmailDispatcher, get_sent_emails
from core.web_scraper import WebScraper
from core.orchestrator import WorkflowOrchestrator


class TestPDFEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def test_generate_executive_report(self):
        out_pdf = os.path.join(self.test_dir, "test_report.pdf")
        kpis = [{"label": "Revenue", "value": "$52,000"}, {"label": "Orders", "value": "1,450"}]
        headers = ["Department", "Budget", "Spent", "Remaining"]
        rows = [
            ["Engineering", "$25,000", "$21,000", "$4,000"],
            ["Marketing", "$15,000", "$14,200", "$800"],
            ["Operations", "$12,000", "$10,500", "$1,500"]
        ]
        chart_data = {"Engineering": 21000, "Marketing": 14200, "Operations": 10500}

        path = generate_executive_report(
            output_path=out_pdf,
            report_title="Q3 Operational Review",
            kpis=kpis,
            table_headers=headers,
            table_rows=rows,
            chart_config={"type": "bar", "data": chart_data, "title": "Department Spend"},
            summary_text="Automated summary test."
        )
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 1000)

    def test_generate_invoice_pdf(self):
        out_pdf = os.path.join(self.test_dir, "test_invoice.pdf")
        items = [
            {"description": "Cloud Infrastructure Setup", "qty": 1, "rate": 1500.0},
            {"description": "Workflow Automation Scripting", "qty": 10, "rate": 85.0}
        ]
        path = generate_invoice_pdf(
            output_path=out_pdf,
            invoice_number="INV-2026-001",
            client_name="Acme Corp",
            client_email="finance@acme.com",
            items=items
        )
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 1000)


class TestEmailAutomator(unittest.TestCase):
    def test_mock_email_dispatch(self):
        dispatcher = EmailDispatcher(mock_mode=True)
        res = dispatcher.send_email(
            to_addresses=["client@example.com"],
            subject="Test Automation Dispatch",
            template_name="executive_report",
            context={"title": "Test Title", "message": "Test Message", "metrics": {"Status": "OK"}}
        )
        self.assertEqual(res["status"], "delivered_mock_sandbox")
        sent = get_sent_emails()
        self.assertGreater(len(sent), 0)


class TestWebScraper(unittest.TestCase):
    def test_scraper_instance(self):
        scraper = WebScraper(timeout=10, max_retries=2)
        self.assertIsNotNone(scraper.session)


if __name__ == "__main__":
    unittest.main()
