import io
import os
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

from num2words import num2words
from app.core.config import settings
from app.models.document import Document, DocumentType, DocumentItem

class PDFService:
    def __init__(self):
        self.width, self.height = A4
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        self.style_header = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'), # Deep Blue
            alignment=TA_RIGHT,
            spaceAfter=20
        )
        self.style_company = ParagraphStyle(
            'CompanyInfo',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#424242')
        )
        self.style_client_label = ParagraphStyle(
            'ClientLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.gray
        )
        self.style_client_value = ParagraphStyle(
            'ClientValue',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        )
        self.style_total_label = ParagraphStyle(
            'TotalLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT,
            textColor=colors.black
        )
        self.style_total_value = ParagraphStyle(
            'TotalValue',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        )
        self.style_footer = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.gray
        )

    def format_currency(self, amount: float) -> str:
        return f"{amount:,.3f} TND".replace(",", " ").replace(".", ",")

    def generate_pdf(self, document: Document) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm,
            title=f"{document.type.value}_{document.document_number}"
        )

        elements = []

        # --- HEADER ---
        # Logo could go here if available
        # Header Table: Company Info (Left) | Document Title & Info (Right)
        
        company_info = [
            Paragraph(f"<b>{settings.PROJECT_NAME}</b>", self.styles['Heading2']),
            Paragraph("Vente en gros de matériel électrique", self.style_company),
            Spacer(1, 5),
            Paragraph(f"MF: {settings.COMPANY_MATRICULE_FISCAL or 'En cours'}", self.style_company),
            Paragraph(f"RC: {settings.COMPANY_REGISTRE_COMMERCE or 'En cours'}", self.style_company),
            Paragraph(f"Tel: +216 12 345 678", self.style_company), # TODO: Add to settings
            Paragraph("Email: sales@nour-distribution.com", self.style_company),
        ]
        
        doc_type_label = document.type.value.upper()
        if document.type == DocumentType.DEVIS:
            doc_type_label = "DEVIS"
        elif document.type == DocumentType.FACTURE:
            doc_type_label = "FACTURE"
        elif document.type == DocumentType.AVOIR:
            doc_type_label = "AVOIR"

        doc_info = [
            Paragraph(doc_type_label, self.style_header),
            Paragraph(f"N°: <b>{document.document_number}</b>", ParagraphStyle('DocNum', parent=self.styles['Normal'], alignment=TA_RIGHT, fontSize=12)),
            Paragraph(f"Date: {document.issue_date.strftime('%d/%m/%Y')}", ParagraphStyle('DocDate', parent=self.styles['Normal'], alignment=TA_RIGHT)),
        ]
        
        if document.valid_until:
             doc_info.append(Paragraph(f"Valide jusqu'au: {document.valid_until.strftime('%d/%m/%Y')}", ParagraphStyle('DocValid', parent=self.styles['Normal'], alignment=TA_RIGHT, textColor=colors.red)))

        header_data = [[company_info, doc_info]]
        header_table = Table(header_data, colWidths=[10*cm, 8*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 1.5*cm))

        # --- CLIENT INFO ---
        client = document.client
        if client.type.value == "b2b":
            client_display_name = client.company_name or client.contact_name or "Client Professionnel"
        else:
            client_display_name = f"{client.first_name or ''} {client.last_name or ''}".strip() or client.contact_name or "Client Particulier"

        client_data = [
            [Paragraph("FACTURER A:", self.style_client_label)],
            [Paragraph(f"{client_display_name}", self.style_client_value)],
            [Paragraph(client.address or "Adresse non renseignée", self.style_client_value)],
            [Paragraph(f"MF: {client.fiscal_id or 'N/A'}", self.style_client_value)] if client.fiscal_id else [],
            [Paragraph(f"Tel: {client.phone or 'N/A'}", self.style_client_value)],
        ]
        # Clean empty lists
        client_data = [r for r in client_data if r]
        
        client_table = Table(client_data, colWidths=[10*cm])
        client_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e0e0e0')),
            ('BACKGROUND', (0,0), (0,0), colors.HexColor('#f5f5f5')),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
        ]))
        elements.append(client_table)
        elements.append(Spacer(1, 1.5*cm))

        # --- ITEMS TABLE ---
        # Headers
        headers = ["#", "Désignation", "Qté", "P.U. (HT)", "Remise", "Total (HT)"]
        col_widths = [1*cm, 8*cm, 1.5*cm, 2.5*cm, 2*cm, 3*cm]
        
        table_data = [headers]
        
        for idx, item in enumerate(document.items, 1):
            row = [
                str(idx),
                Paragraph(item.product_name, self.styles['Normal']),
                str(item.quantity),
                self.format_currency(item.unit_price or 0),
                f"{item.discount_percent}%" if item.discount_percent else "-",
                self.format_currency(item.subtotal or 0)
            ]
            table_data.append(row)

        # Style Items Table
        items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f5f5f5')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),  # Default align
            ('ALIGN', (2,0), (-1,-1), 'RIGHT'), # Numbers align right
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('TOPPADDING', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 1*cm))

        # --- TOTALS ---
        # Right aligned totals, Left aligned "Words"
        
        # Calculate totals
        subtotal = document.subtotal or 0
        remise_globale = document.discount or 0
        tva = document.tax_amount or 0
        timbre = 1.000 # Fixed for now or 0.600
        net_to_pay = document.total_amount or 0 # Logic might differ if timbre is added on top
        
        # Adjust logic if timbre is not in document.total_amount yet (usually backend handles it)
        # For display, we trust document fields.
        
        totals_data = [
            [Paragraph("Total HT:", self.style_total_label), Paragraph(self.format_currency(subtotal), self.style_total_value)],
            [Paragraph("Remise Globale:", self.style_total_label), Paragraph(self.format_currency(remise_globale), self.style_total_value)],
            [Paragraph("Total TVA (19%):", self.style_total_label), Paragraph(self.format_currency(tva), self.style_total_value)],
            [Paragraph("Timbre Fiscal:", self.style_total_label), Paragraph(self.format_currency(settings.TIMBRE_FISCAL_RATE if settings.TIMBRE_FISCAL_RATE > 0.01 else 1.000), self.style_total_value)],
            [Paragraph("<b>NET A PAYER:</b>", self.style_total_label), Paragraph(f"<b>{self.format_currency(net_to_pay)}</b>", self.style_total_value)],
        ]
        
        totals_table = Table(totals_data, colWidths=[4*cm, 4*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('LINEABOVE', (0,-1), (-1,-1), 1, colors.black), # Line above Total Net
            ('TOPPADDING', (0,-1), (-1,-1), 8),
        ]))
        
        # Layout: Words on Left, Totals on Right
        net_text = num2words(net_to_pay, lang='fr').capitalize() + " dinars"
        # Handle millimes
        rest = round((net_to_pay - int(net_to_pay)) * 1000)
        if rest > 0:
            net_text = num2words(int(net_to_pay), lang='fr').capitalize() + f" dinars et {rest} millimes"
        
        words_paragraph = Paragraph(f"Arrêté la présente facture à la somme de :<br/><b>{net_text}</b>", self.styles['Normal'])
        
        summary_table_data = [[words_paragraph, totals_table]]
        summary_table = Table(summary_table_data, colWidths=[10*cm, 8*cm])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 2*cm))

        # --- FOOTER / PAYMENT ---
        if document.type == DocumentType.FACTURE:
            payment_info = [
                Paragraph("<b>Informations de Paiement</b>", self.styles['Normal']),
                Paragraph(f"Banque: {settings.BANK_NAME}", self.styles['Normal']),
                Paragraph(f"RIB: {settings.BANK_IBAN}", self.styles['Normal']),
            ]
            for p in payment_info:
                elements.append(p)
                elements.append(Spacer(1, 2))
        
        # Build
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
