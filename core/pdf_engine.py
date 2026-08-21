"""
DataFlow Automator Pro - PDF Generation & Manipulation Engine
Provides high-fidelity PDF report generation, invoice generation,
embedded chart synthesis, and PDF document utilities using ReportLab.
"""

import os
import io
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

from core.logger import logger
from core.exceptions import PDFGenerationError


class NumberedCanvas(canvas.Canvas):
    """Custom canvas that performs two passes to dynamically render total page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header (pages 2+)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 750, 558, 750)
            self.drawString(54, 755, "DataFlow Automator Pro | Executive Report")
            self.drawRightString(558, 755, datetime.now().strftime("%Y-%m-%d"))

        # Footer
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        self.drawString(54, 32, "Confidential - Generated automatically by DataFlow Automator Suite")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_text)
        self.restoreState()


def create_chart_image(
    chart_type: str,
    data: Dict[str, Union[int, float]],
    title: str = "",
    figsize=(6, 3),
    colors_list=None
) -> io.BytesIO:
    """Generates an in-memory PNG chart stream using Matplotlib."""
    fig, ax = plt.subplots(figsize=figsize, dpi=200)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#f8fafc')

    default_colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899']
    palette = colors_list or default_colors

    keys = list(data.keys())
    values = list(data.values())

    if chart_type == "bar":
        bars = ax.bar(keys, values, color=palette[:len(keys)], edgecolor='#cbd5e1', width=0.55)
        ax.set_title(title, fontsize=11, fontweight='bold', color='#1e293b', pad=12)
        ax.grid(axis='y', linestyle='--', alpha=0.5, color='#cbd5e1')
        ax.tick_params(colors='#475569', labelsize=8)
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:,.0f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=8, fontweight='bold', color='#1e293b')
        plt.xticks(rotation=15, ha='right')

    elif chart_type == "pie" or chart_type == "donut":
        wedges, texts, autotexts = ax.pie(
            values, labels=keys, autopct='%1.1f%%',
            startangle=140, colors=palette[:len(keys)],
            wedgeprops=dict(width=0.4 if chart_type == "donut" else 1, edgecolor='#ffffff', linewidth=2),
            textprops=dict(color='#1e293b', fontsize=8)
        )
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_weight('bold')
        ax.set_title(title, fontsize=11, fontweight='bold', color='#1e293b', pad=12)

    elif chart_type == "line":
        ax.plot(keys, values, marker='o', color='#3b82f6', linewidth=2.5, markersize=6, markerfacecolor='#1d4ed8')
        ax.fill_between(keys, values, color='#3b82f6', alpha=0.1)
        ax.set_title(title, fontsize=11, fontweight='bold', color='#1e293b', pad=12)
        ax.grid(True, linestyle='--', alpha=0.5, color='#cbd5e1')
        ax.tick_params(colors='#475569', labelsize=8)
        plt.xticks(rotation=15, ha='right')

    plt.tight_layout()
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer


def generate_executive_report(
    output_path: str,
    report_title: str,
    subtitle: str = "Automated Business Intelligence & Operational Audit",
    kpis: Optional[List[Dict[str, str]]] = None,
    table_headers: Optional[List[str]] = None,
    table_rows: Optional[List[List[Any]]] = None,
    chart_config: Optional[Dict[str, Any]] = None,
    summary_text: Optional[str] = None
) -> str:
    """
    Synthesize a corporate PDF report.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=14
        )
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=17,
            textColor=colors.HexColor('#1E293B'),
            spaceBefore=14,
            spaceAfter=8
        )
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor('#334155')
        )
        kpi_label_style = ParagraphStyle(
            'KPILabel',
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#64748B'),
            alignment=1
        )
        kpi_val_style = ParagraphStyle(
            'KPIVal',
            fontName='Helvetica-Bold',
            fontSize=15,
            leading=18,
            textColor=colors.HexColor('#0284C7'),
            alignment=1
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph(report_title, title_style))
        story.append(Paragraph(f"{subtitle} | Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceBefore=2, spaceAfter=14))

        # 2. Executive Summary Block
        if summary_text:
            story.append(Paragraph("Executive Overview", section_heading))
            story.append(Paragraph(summary_text, body_style))
            story.append(Spacer(1, 10))

        # 3. KPI Cards Block
        if kpis and len(kpis) > 0:
            story.append(Paragraph("Key Performance Metrics", section_heading))
            kpi_cells = []
            for k in kpis:
                card_content = [
                    Paragraph(k.get("value", "-"), kpi_val_style),
                    Spacer(1, 3),
                    Paragraph(k.get("label", "Metric").upper(), kpi_label_style)
                ]
                kpi_cells.append(card_content)

            # Arrange in single row table
            col_width = (504.0 / len(kpis))
            kpi_table = Table([kpi_cells], colWidths=[col_width] * len(kpis))
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('INNERGRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(kpi_table)
            story.append(Spacer(1, 14))

        # 4. Chart Visualization (if provided)
        if chart_config:
            story.append(Paragraph("Visual Analysis", section_heading))
            chart_stream = create_chart_image(
                chart_type=chart_config.get("type", "bar"),
                data=chart_config.get("data", {}),
                title=chart_config.get("title", "Metric Distribution"),
                figsize=(5.5, 2.5)
            )
            chart_flowable = Image(chart_stream, width=504, height=229)
            story.append(chart_flowable)
            story.append(Spacer(1, 12))

        # 5. Data Records Table
        if table_headers and table_rows:
            story.append(Paragraph("Detailed Data Breakdown", section_heading))
            table_data = []

            # Headers
            header_row = [
                Paragraph(f"<b>{h}</b>", ParagraphStyle('TH', parent=body_style, textColor=colors.white, fontName='Helvetica-Bold'))
                for h in table_headers
            ]
            table_data.append(header_row)

            # Rows (limit to first 30 rows for clean PDF formatting)
            for row in table_rows[:30]:
                data_row = [
                    Paragraph(str(cell), body_style) for cell in row
                ]
                table_data.append(data_row)

            col_w = 504.0 / len(table_headers)
            records_table = Table(table_data, colWidths=[col_w] * len(table_headers), repeatRows=1)
            records_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8FAFC')])
            ]))
            story.append(records_table)

        doc.build(story, canvasmaker=NumberedCanvas)
        logger.info(f"Generated PDF report successfully: '{output_path}'")
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}")
        raise PDFGenerationError(f"PDF generation error: {e}")


def generate_invoice_pdf(
    output_path: str,
    invoice_number: str,
    client_name: str,
    client_email: str,
    items: List[Dict[str, Any]],
    tax_rate: float = 0.10,
    currency_symbol: str = "$"
) -> str:
    """Generate a clean, modern commercial invoice PDF."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=45, rightMargin=45, topMargin=45, bottomMargin=45)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('InvTitle', fontName='Helvetica-Bold', fontSize=24, textColor=colors.HexColor('#0F172A'))
        inv_num_style = ParagraphStyle('InvNum', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#0284C7'))
        body_style = ParagraphStyle('InvBody', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#334155'), leading=13)
        body_bold = ParagraphStyle('InvBold', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#0F172A'))

        story = []

        # Top Header (Company & Invoice Title)
        header_data = [
            [
                Paragraph("<b>DataFlow Systems Inc.</b><br/>100 Automation Blvd<br/>San Francisco, CA 94107<br/>billing@dataflowpro.io", body_style),
                Paragraph(f"<b>INVOICE</b><br/><font color='#0284C7'>#{invoice_number}</font><br/>Date: {datetime.now().strftime('%Y-%m-%d')}<br/>Due: In 30 Days", ParagraphStyle('InvRight', parent=body_style, alignment=2))
            ]
        ]
        h_table = Table(header_data, colWidths=[260, 260])
        h_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
        ]))
        story.append(h_table)
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0'), spaceAfter=14))

        # Bill To
        bill_to_data = [
            [
                Paragraph(f"<b>Billed To:</b><br/><b>{client_name}</b><br/>{client_email}", body_style),
                Paragraph("<b>Payment Status:</b> <font color='#10B981'><b>PENDING</b></font><br/>Payment Method: ACH / Wire / Credit Card", body_style)
            ]
        ]
        b_table = Table(bill_to_data, colWidths=[260, 260])
        b_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 14)]))
        story.append(b_table)

        # Line Items
        item_rows = [[
            Paragraph("<b>Description</b>", ParagraphStyle('IH', parent=body_style, textColor=colors.white)),
            Paragraph("<b>Qty</b>", ParagraphStyle('IH_R', parent=body_style, textColor=colors.white, alignment=2)),
            Paragraph("<b>Unit Price</b>", ParagraphStyle('IH_R', parent=body_style, textColor=colors.white, alignment=2)),
            Paragraph("<b>Amount</b>", ParagraphStyle('IH_R', parent=body_style, textColor=colors.white, alignment=2))
        ]]

        subtotal = 0.0
        for itm in items:
            qty = float(itm.get("qty", 1))
            rate = float(itm.get("rate", 0.0))
            amount = qty * rate
            subtotal += amount
            item_rows.append([
                Paragraph(itm.get("description", "Service Item"), body_style),
                Paragraph(f"{qty:g}", ParagraphStyle('Q', parent=body_style, alignment=2)),
                Paragraph(f"{currency_symbol}{rate:,.2f}", ParagraphStyle('R', parent=body_style, alignment=2)),
                Paragraph(f"{currency_symbol}{amount:,.2f}", ParagraphStyle('A', parent=body_style, alignment=2))
            ])

        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount

        # Summary rows
        item_rows.append(["", "", Paragraph("<b>Subtotal</b>", body_bold), Paragraph(f"<b>{currency_symbol}{subtotal:,.2f}</b>", ParagraphStyle('ST', parent=body_bold, alignment=2))])
        item_rows.append(["", "", Paragraph(f"Tax ({tax_rate*100:.0f}%)", body_style), Paragraph(f"{currency_symbol}{tax_amount:,.2f}", ParagraphStyle('TX', parent=body_style, alignment=2))])
        item_rows.append(["", "", Paragraph("<b>TOTAL DUE</b>", ParagraphStyle('TT', parent=body_bold, textColor=colors.HexColor('#0284C7'))), Paragraph(f"<b>{currency_symbol}{total_amount:,.2f}</b>", ParagraphStyle('TTV', parent=body_bold, textColor=colors.HexColor('#0284C7'), alignment=2))])

        inv_table = Table(item_rows, colWidths=[270, 50, 100, 100])
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, len(items)), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, len(items)), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEABOVE', (2, len(items) + 1), (3, len(items) + 1), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (2, len(items) + 3), (3, len(items) + 3), colors.HexColor('#F1F5F9'))
        ]))
        story.append(inv_table)
        story.append(Spacer(1, 25))

        # Payment details
        notes = Paragraph(
            "<b>Terms & Conditions:</b> Payment is due within 30 days of invoice date. "
            "Thank you for your business!",
            body_style
        )
        story.append(notes)

        doc.build(story)
        logger.info(f"Generated Invoice PDF successfully: '{output_path}'")
        return output_path
    except Exception as e:
        logger.error(f"Failed to generate invoice: {e}")
        raise PDFGenerationError(f"Invoice generation failed: {e}")
