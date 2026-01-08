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
        # Base styles
        self.style_normal = self.styles['Normal']
        self.style_bold = ParagraphStyle(
            'Bold',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold'
        )
        
        # Header styles
        self.style_company_name = ParagraphStyle(
            'CompanyName',
            parent=self.styles['Normal'],
            fontSize=16,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1a237e')
        )
        self.style_company_info = ParagraphStyle(
            'CompanyInfo',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11
        )
        
        # Document Title style
        self.style_doc_title = ParagraphStyle(
            'DocTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=10,
            textColor=colors.black
        )
        
        # Client style
        self.style_client_box = ParagraphStyle(
            'ClientBox',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14
        )
        
        # Table styles
        self.style_table_header = ParagraphStyle(
            'TableHeader',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            textColor=colors.white
        )
        self.style_table_cell = ParagraphStyle(
            'TableCell',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER
        )
        self.style_table_cell_left = ParagraphStyle(
            'TableCellLeft',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_LEFT
        )
        
        # Totals styles
        self.style_total_label = ParagraphStyle(
            'TotalLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT
        )
        self.style_total_value = ParagraphStyle(
            'TotalValue',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        )
        
        # Footer style
        self.style_footer = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=7,
            alignment=TA_CENTER,
            textColor=colors.gray
        )

    def format_currency(self, amount: float) -> str:
        return f"{amount:,.3f}".replace(",", " ").replace(".", ",")

    def generate_pdf(self, document: Document) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1.5*cm,
            title=f"{document.type.value}_{document.document_number}"
        )

        elements = []

        # 1. Company Information & Document Header
        elements.append(self._create_header_section(document))
        elements.append(Spacer(1, 0.5*cm))

        # 2. Client Information
        elements.append(self._create_client_section(document))
        elements.append(Spacer(1, 1*cm))

        # 3. Line Items Table
        elements.append(self._create_items_table(document))
        elements.append(Spacer(1, 0.5*cm))

        # 4. VAT Breakdown & Totals
        # We use a table for Totals and VAT Breakdown layout
        vat_and_totals = self._create_vat_and_totals_layout(document)
        elements.append(vat_and_totals)
        elements.append(Spacer(1, 0.5*cm))

        # 5. Amount in Words
        elements.append(self._create_amount_in_words(document))
        elements.append(Spacer(1, 1*cm))

        # 6. Legal Footer
        
        def add_footer(canvas, doc):
            canvas.saveState()
            footer_text = f"{settings.COMPANY_NAME} - RC: {settings.COMPANY_REGISTRE_COMMERCE} - MF: {settings.COMPANY_MATRICULE_FISCAL}\n" \
                          f"{settings.COMPANY_ADDRESS} - Tel: {settings.COMPANY_PHONE} - Email: {settings.COMPANY_EMAIL}"
            p = Paragraph(footer_text.replace("\n", "<br/>"), self.style_footer)
            w, h = p.wrap(doc.width, doc.bottomMargin)
            p.drawOn(canvas, doc.leftMargin, 0.5*cm)
            canvas.restoreState()

        doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
        buffer.seek(0)
        return buffer.getvalue()

    def _create_header_section(self, document: Document) -> Table:
        # Left side: Company Logo & Info
        company_col = [
            Paragraph(f"<b>{settings.COMPANY_NAME}</b>", self.style_company_name),
            Paragraph(f"<i>{settings.COMPANY_ACTIVITY}</i>", self.style_company_info),
            Spacer(1, 5),
            Paragraph(settings.COMPANY_ADDRESS, self.style_company_info),
            Paragraph(f"Tel: {settings.COMPANY_PHONE} / GSM: {settings.COMPANY_GSM}", self.style_company_info),
            Paragraph(f"MF: {settings.COMPANY_MATRICULE_FISCAL}", self.style_company_info),
            Paragraph(f"RIB: {settings.COMPANY_RIB}", self.style_company_info),
            Paragraph(f"Banque: {settings.COMPANY_BANK}", self.style_company_info),
            Paragraph(f"Email: {settings.COMPANY_EMAIL}", self.style_company_info),
        ]

        # Right side: Invoice Header (Number & Date)
        doc_label = "FACTURE" if document.type == DocumentType.FACTURE else \
                    "DEVIS" if document.type == DocumentType.DEVIS else "AVOIR"
        
        header_col = [
            Paragraph(f"<b>{doc_label}</b>", self.style_doc_title),
            Paragraph(f"{doc_label} N°: <b>{document.document_number}</b>", self.style_bold),
            Paragraph(f"Date: {document.issue_date.strftime('%d/%m/%Y')}", self.style_normal),
        ]

        data = [[company_col, header_col]]
        table = Table(data, colWidths=[11*cm, 8*cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        return table

    def _create_client_section(self, document: Document) -> Table:
        client = document.client
        if client.type.value == "b2b":
            client_display_name = client.company_name or client.contact_name or "Client Professionnel"
        else:
            client_display_name = f"{client.first_name or ''} {client.last_name or ''}".strip() or client.contact_name or "Client Particulier"

        client_data = [
            [Paragraph("<b>CLIENT:</b>", self.style_bold)],
            [Paragraph(f"Nom: {client_display_name}", self.style_client_box)],
            [Paragraph(f"Adresse: {client.address or 'N/A'}", self.style_client_box)],
            [Paragraph(f"MF: {client.fiscal_id or 'N/A'}", self.style_client_box)],
            [Paragraph(f"Code Client: {str(client.id)[:8]}", self.style_client_box)],
        ]
        
        data = [["", client_data]]
        table = Table(data, colWidths=[10*cm, 9*cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOX', (1,0), (1,-1), 1, colors.black),
            ('TOPPADDING', (1,0), (1,-1), 10),
            ('BOTTOMPADDING', (1,0), (1,-1), 10),
            ('LEFTPADDING', (1,0), (1,-1), 10),
        ]))
        return table

    def _create_items_table(self, document: Document) -> Table:
        headers = [
            Paragraph("Code", self.style_table_header),
            Paragraph("Désignation", self.style_table_header),
            Paragraph("Qté", self.style_table_header),
            Paragraph("P.U HT", self.style_table_header),
            Paragraph("Rem.%", self.style_table_header),
            Paragraph("P.U Net HT", self.style_table_header),
            Paragraph("TVA%", self.style_table_header),
            Paragraph("Total HT", self.style_table_header),
            Paragraph("P.U TTC", self.style_table_header),
        ]
        
        col_widths = [2*cm, 5.5*cm, 1.2*cm, 2*cm, 1.3*cm, 2*cm, 1.2*cm, 2*cm, 2*cm]
        data = [headers]

        for item in document.items:
            pu_ht = item.unit_price or 0
            qty = item.quantity or 0
            rem_pct = item.discount_percent or 0
            tva_pct = item.tax_percent or 0
            
            pu_net_ht = pu_ht * (1 - rem_pct / 100)
            total_ht = pu_net_ht * qty
            pu_ttc = pu_net_ht * (1 + tva_pct / 100)
            
            row = [
                Paragraph(item.product_sku or "", self.style_table_cell),
                Paragraph(item.product_name or "", self.style_table_cell_left),
                Paragraph(str(qty), self.style_table_cell),
                Paragraph(self.format_currency(pu_ht), self.style_table_cell),
                Paragraph(f"{rem_pct}%" if rem_pct > 0 else "0%", self.style_table_cell),
                Paragraph(self.format_currency(pu_net_ht), self.style_table_cell),
                Paragraph(f"{int(tva_pct)}%", self.style_table_cell),
                Paragraph(self.format_currency(total_ht), self.style_table_cell),
                Paragraph(self.format_currency(pu_ttc), self.style_table_cell),
            ]
            data.append(row)

        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a237e')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ]))
        return table

    def _create_vat_and_totals_layout(self, document: Document) -> Table:
        vat_table = self._create_vat_breakdown_table(document)
        totals_table = self._create_totals_section(document)
        
        data = [[vat_table, totals_table]]
        table = Table(data, colWidths=[10*cm, 9*cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        return table

    def _create_vat_breakdown_table(self, document: Document) -> Table:
        vat_breakdown = {}
        for item in document.items:
            tva_pct = item.tax_percent or 0
            qty = item.quantity or 0
            pu_ht = item.unit_price or 0
            rem_pct = item.discount_percent or 0
            
            base_ht = pu_ht * (1 - rem_pct / 100) * qty
            vat_amount = base_ht * (tva_pct / 100)
            
            if tva_pct not in vat_breakdown:
                vat_breakdown[tva_pct] = {'base': 0, 'amount': 0}
            vat_breakdown[tva_pct]['base'] += base_ht
            vat_breakdown[tva_pct]['amount'] += vat_amount

        data = [
            [Paragraph("Base HT", self.style_bold), Paragraph("TVA %", self.style_bold), Paragraph("Mnt TVA", self.style_bold)]
        ]
        
        for pct, vals in sorted(vat_breakdown.items()):
            data.append([
                Paragraph(self.format_currency(vals['base']), self.style_table_cell),
                Paragraph(f"{int(pct)}%", self.style_table_cell),
                Paragraph(self.format_currency(vals['amount']), self.style_table_cell),
            ])
            
        table = Table(data, colWidths=[3*cm, 2*cm, 3*cm])
        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eeeeee')),
        ]))
        
        return table

    def _create_totals_section(self, document: Document) -> Table:
        subtotal = document.subtotal or 0
        discount = document.discount or 0
        net_ht = subtotal - discount
        total_tva = document.tax_amount or 0
        timbre = settings.TIMBRE_FISCAL_RATE if document.type == DocumentType.FACTURE else 0
        net_to_pay = net_ht + total_tva + timbre

        data = [
            [Paragraph("Total HT:", self.style_total_label), Paragraph(self.format_currency(subtotal), self.style_total_value)],
            [Paragraph("Escompte:", self.style_total_label), Paragraph(self.format_currency(discount), self.style_total_value)],
            [Paragraph("Net HT:", self.style_total_label), Paragraph(self.format_currency(net_ht), self.style_total_value)],
            [Paragraph("Total TVA:", self.style_total_label), Paragraph(self.format_currency(total_tva), self.style_total_value)],
            [Paragraph("Timbre:", self.style_total_label), Paragraph(self.format_currency(timbre), self.style_total_value)],
            [Paragraph("<b>NET A PAYER:</b>", self.style_total_label), Paragraph(f"<b>{self.format_currency(net_to_pay)} DT</b>", self.style_total_value)],
        ]
        
        table = Table(data, colWidths=[5*cm, 4*cm])
        table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('LINEABOVE', (0,-1), (-1,-1), 1, colors.black),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        return table

    def _create_amount_in_words(self, document: Document) -> Paragraph:
        subtotal = document.subtotal or 0
        discount = document.discount or 0
        net_ht = subtotal - discount
        total_tva = document.tax_amount or 0
        timbre = settings.TIMBRE_FISCAL_RATE if document.type == DocumentType.FACTURE else 0
        net_to_pay = net_ht + total_tva + timbre
        
        main_part = int(net_to_pay)
        millimes_part = int(round((net_to_pay - main_part) * 1000))
        
        words_main = num2words(main_part, lang='fr').upper()
        words_millimes = num2words(millimes_part, lang='fr').upper() if millimes_part > 0 else ""
        
        text = f"Arrêté la présente facture à la somme de : <br/><b>{words_main} DINAR(S)"
        if millimes_part > 0:
            text += f" ET {words_millimes} MILLIMES"
        text += "</b>"
        
        return Paragraph(text, self.style_normal)
