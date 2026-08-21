"""
DataFlow Automator Pro - Email Automation Module
Provides automated SMTP email dispatching, Jinja2 dynamic HTML templates,
attachment handlers, and an in-memory/disk mock sandbox for testing.
"""

import os
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from jinja2 import Template

from core.logger import logger
from core.exceptions import EmailDispatchError

# Directory for storing mock sandbox outgoing emails
MOCK_EMAIL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sent_emails")
os.makedirs(MOCK_EMAIL_DIR, exist_ok=True)

# In-memory sent email history for live Web UI inspection
_SENT_EMAIL_BOX: List[Dict[str, Any]] = []


BUILTIN_TEMPLATES = {
    "executive_report": """
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 620px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #ffffff;">
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 24px; color: #ffffff; text-align: left;">
            <h1 style="margin: 0; font-size: 22px; font-weight: 600; color: #38bdf8;">DataFlow Automator Pro</h1>
            <p style="margin: 6px 0 0 0; font-size: 13px; color: #94a3b8;">Automated Business Intelligence & Operational Digest</p>
        </div>
        <div style="padding: 24px; color: #334155; line-height: 1.6;">
            <h2 style="font-size: 18px; color: #0f172a; margin-top: 0;">{{ title or 'Weekly Automation Digest' }}</h2>
            <p>Hello <b>{{ recipient_name or 'Valued Team' }}</b>,</p>
            <p>{{ message or 'Your scheduled data automation report has completed successfully. Please review the key highlights below and find attached documents for complete details.' }}</p>
            
            {% if metrics %}
            <div style="display: flex; gap: 12px; margin: 20px 0; background: #f8fafc; padding: 14px; border-radius: 6px; border: 1px solid #e2e8f0;">
                {% for k, v in metrics.items() %}
                <div style="flex: 1; text-align: center;">
                    <div style="font-size: 11px; text-transform: uppercase; color: #64748B; font-weight: 600;">{{ k }}</div>
                    <div style="font-size: 18px; font-weight: bold; color: #0284c7; margin-top: 4px;">{{ v }}</div>
                </div>
                {% endfor %}
            </div>
            {% endif %}

            <p style="font-size: 13px; color: #64748b;">Generated automatically at {{ timestamp }} by DataFlow Workflow Engine.</p>
        </div>
        <div style="background: #f1f5f9; padding: 14px 24px; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; text-align: center;">
            &copy; 2026 DataFlow Systems. All rights reserved. | Automated Delivery
        </div>
    </div>
    """,

    "invoice_notification": """
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 620px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #ffffff;">
        <div style="background: #0284c7; padding: 22px; color: #ffffff;">
            <h2 style="margin: 0; font-size: 20px;">New Invoice Generated</h2>
            <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.9;">Invoice #{{ invoice_number }}</p>
        </div>
        <div style="padding: 24px; color: #334155; line-height: 1.6;">
            <p>Dear <b>{{ recipient_name }}</b>,</p>
            <p>Please find attached invoice <b>#{{ invoice_number }}</b> for the amount of <b>{{ total_amount }}</b>.</p>
            <p>Due Date: <b>{{ due_date or '30 days upon receipt' }}</b></p>
            <div style="margin: 20px 0; padding: 14px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; color: #166534; font-size: 14px;">
                ✓ Official PDF invoice is attached with itemized breakdown.
            </div>
        </div>
        <div style="background: #f8fafc; padding: 12px 24px; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; text-align: center;">
            Thank you for your business!
        </div>
    </div>
    """,

    "alert_notification": """
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 620px; margin: 0 auto; border: 1px solid #fecaca; border-radius: 8px; overflow: hidden; background: #ffffff;">
        <div style="background: #ef4444; padding: 20px; color: #ffffff;">
            <h2 style="margin: 0; font-size: 20px;">⚠️ Automation System Alert</h2>
        </div>
        <div style="padding: 24px; color: #334155; line-height: 1.6;">
            <p><b>Alert Level:</b> <span style="color: #dc2626; font-weight: bold;">{{ alert_level or 'WARNING' }}</span></p>
            <p>{{ alert_message }}</p>
            <pre style="background: #1e293b; color: #f8fafc; padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto;">{{ details }}</pre>
        </div>
    </div>
    """
}


class EmailDispatcher:
    """
    Automated Email Dispatcher supporting live SMTP servers and mock test mode.
    """
    def __init__(
        self,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
        sender_email: Optional[str] = None,
        mock_mode: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username or os.environ.get("SMTP_USER", "")
        self.password = password or os.environ.get("SMTP_PASS", "")
        self.use_tls = use_tls
        self.sender_email = sender_email or self.username or "automator@dataflowpro.local"
        self.mock_mode = mock_mode

    def render_template(self, template_name_or_html: str, context: Dict[str, Any]) -> str:
        """Render dynamic HTML template using Jinja2."""
        raw_html = BUILTIN_TEMPLATES.get(template_name_or_html, template_name_or_html)
        template = Template(raw_html)
        context["timestamp"] = context.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return template.render(**context)

    def send_email(
        self,
        to_addresses: Union[str, List[str]],
        subject: str,
        template_name: str = "executive_report",
        context: Optional[Dict[str, Any]] = None,
        plain_text: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Construct and dispatch an automated email with optional attachments.
        """
        if isinstance(to_addresses, str):
            to_addresses = [to_addresses]

        context = context or {}
        html_body = self.render_template(template_name, context)

        msg = MIMEMultipart("mixed")
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(to_addresses)
        msg["Subject"] = subject
        msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

        # HTML / Plain body
        body_part = MIMEMultipart("alternative")
        if plain_text:
            body_part.attach(MIMEText(plain_text, "plain", "utf-8"))
        body_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(body_part)

        # Attachments
        attached_files = []
        if attachments:
            for filepath in attachments:
                if os.path.exists(filepath):
                    filename = os.path.basename(filepath)
                    with open(filepath, "rb") as f:
                        part = MIMEApplication(f.read(), Name=filename)
                        part['Content-Disposition'] = f'attachment; filename="{filename}"'
                        msg.attach(part)
                        attached_files.append(filename)
                else:
                    logger.warning(f"Attachment not found: {filepath}")

        # Send via Live SMTP or Record in Mock Sandbox
        dispatch_record = {
            "id": f"mail_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:18]}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "from": self.sender_email,
            "to": to_addresses,
            "subject": subject,
            "attachments": attached_files,
            "mock_mode": self.mock_mode,
            "status": "pending"
        }

        if self.mock_mode:
            # Save mock email to disk and in-memory box
            dispatch_record["status"] = "delivered_mock_sandbox"
            dispatch_record["html_preview"] = html_body

            json_path = os.path.join(MOCK_EMAIL_DIR, f"{dispatch_record['id']}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(dispatch_record, f, indent=2)

            _SENT_EMAIL_BOX.append(dispatch_record)
            logger.info(f"[MOCK EMAIL] Delivered message '{subject}' to {to_addresses} (Sandbox saved: {json_path})")
            return dispatch_record

        # Live SMTP Sending
        try:
            logger.info(f"Connecting to SMTP server {self.smtp_host}:{self.smtp_port}...")
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15)
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)

            server.sendmail(self.sender_email, to_addresses, msg.as_string())
            server.quit()

            dispatch_record["status"] = "delivered_smtp"
            _SENT_EMAIL_BOX.append(dispatch_record)
            logger.info(f"Successfully sent live email to {to_addresses}")
            return dispatch_record
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            dispatch_record["status"] = "failed"
            dispatch_record["error"] = str(e)
            _SENT_EMAIL_BOX.append(dispatch_record)
            raise EmailDispatchError(f"Email delivery failed: {e}", {"details": str(e)})


def get_sent_emails(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve sent email history from in-memory / disk cache."""
    return list(reversed(_SENT_EMAIL_BOX[-limit:]))
