from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
import os
import qrcode
import tempfile
import base64
from io import BytesIO

class TunisianPDFGenerator:
    """Tunisian VAT compliant PDF generator for invoices and quotes"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self._register_arabic_font()
        
        # Tunisian VAT rates (standard 19%, reduced rates: 7%, 13%)
        self.VAT_RATES = {
            'standard': 0.19,    # 19% - Most goods and services
            'reduced1': 0.13,    # 13% - Some goods
            'reduced2': 0.07,    # 7%  - Basic necessities
            'exempt': 0.00       # 0%  - Exempt goods
        }
        
        # Tunisian fiscal information
        self.COMPANY_INFO = {
            'name': 'NOUR DISTRIBUTION SARL',
            'address': 'Rue Habib Bourguiba, Tunis 1001',
            'city': 'Tunis',
            'phone': '+216 71 123 456',
            'email': 'contact@nour-distribution.tn',
            'website': 'www.nour-distribution.tn',
            'matricule_fiscale': '12345678/A/M/000',
            'registre_commerce': 'B123456',
            'code_tva': 'TVA12345678',
            'agent_économique': '123456789',
            'banque': 'BIAT',
            'rib': '12 345 67890123456789 12',
            'iban': 'TN59 1234 5678 9012 3456 7890',
            'bic': 'BIATNTTNXXX'
        }
    
    def _register_arabic_font(self):
        """Register Arabic font for Tunisian documents"""
        try:
            # Try to register Arabic font if available
            arabic_font_path = "/usr/share/fonts/truetype/arabic/arial.ttf"
            if os.path.exists(arabic_font_path):
                pdfmetrics.registerFont(TTFont('Arabic', arabic_font_path))
                addMapping('Arabic', 0, 0, 'Arabic')
        except Exception as e:
            # Fallback to default font if Arabic font registration fails
            print(f"[PDF] Could not register Arabic font: {e}")
    
    def _setup_custom_styles(self):
        """Setup Tunisian-style document formatting"""
        
        # Company info style
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Title'],
            fontSize=18,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=10,
            alignment=TA_CENTER
        ))
        
        # Document title style (French/Arabic)
        self.styles.add(ParagraphStyle(
            name='DocumentTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#E74C3C'),
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        ))
        
        # Tunisian address style
        self.styles.add(ParagraphStyle(
            name='TunisianAddress',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#7F8C8D'),
            alignment=TA_CENTER,
            spaceAfter=6
        ))
        
        # Fiscal info style (Tunisian requirements)
        self.styles.add(ParagraphStyle(
            name='FiscalInfo',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#C0392B'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Amount style in Tunisian Dinar
        self.styles.add(ParagraphStyle(
            name='AmountTND',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#27AE60'),
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        ))
        
        # Legal notice style (Tunisian law)
        self.styles.add(ParagraphStyle(
            name='LegalNotice',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#7F8C8D'),
            alignment=TA_JUSTIFY,
            spaceBefore=10,
            spaceAfter=10
        ))
        
        # Arabic text style
        self.styles.add(ParagraphStyle(
            name='ArabicText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_RIGHT,
            fontName='Arabic' if hasattr(self, 'arabic_font') else 'Helvetica'
        ))
    
    def generate_devis_pdf(self, devis: Dict, client: Dict, items: List[Dict]) -> str:
        """Generate Tunisian-compliant devis (quote) PDF"""
        filename = f"devis_{devis['document_number']}.pdf"
        filepath = os.path.join("documents", "devis", filename)
        
        # Create directory if not exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"Devis {devis['document_number']}",
            author="NOUR DISTRIBUTION"
        )
        
        elements = []
        
        # ============ PAGE 1: HEADER & CLIENT INFO ============
        elements.extend(self._create_tunisian_header("DEVIS"))
        elements.append(Spacer(1, 0.5*cm))
        
        # Document number and dates
        elements.extend(self._create_document_info(devis))
        elements.append(Spacer(1, 1*cm))
        
        # Client information (Tunisian format)
        elements.extend(self._create_tunisian_client_section(client))
        elements.append(Spacer(1, 1*cm))
        
        # ============ ITEMS TABLE WITH TUNISIAN VAT ============
        elements.append(self._create_tunisian_items_table(items, is_devis=True))
        elements.append(Spacer(1, 1*cm))
        
        # ============ TOTALS WITH TUNISIAN VAT CALCULATION ============
        elements.extend(self._create_tunisian_totals_section(devis, "devis"))
        elements.append(Spacer(1, 1*cm))
        
        # ============ TUNISIAN LEGAL REQUIREMENTS FOR DEVIS ============
        elements.extend(self._create_tunisian_legal_section_devis(devis))
        
        # ============ TERMS & CONDITIONS ============
        elements.append(PageBreak())
        elements.extend(self._create_terms_section_tunisia(devis))
        
        # ============ SIGNATURE SECTION ============
        elements.append(Spacer(1, 3*cm))
        elements.extend(self._create_signature_section_tunisia())
        
        # ============ FOOTER WITH TUNISIAN INFO ============
        elements.append(self._create_tunisian_footer())
        
        # Generate PDF
        doc.build(elements, onFirstPage=self._add_tunisian_page_numbers, 
                 onLaterPages=self._add_tunisian_page_numbers)
        
        return filepath
    
    def generate_facture_pdf(self, facture: Dict, client: Dict, items: List[Dict], payments: List[Dict]) -> str:
        """Generate Tunisian-compliant facture (invoice) PDF"""
        filename = f"facture_{facture['document_number']}.pdf"
        filepath = os.path.join("documents", "factures", filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"Facture {facture['document_number']}",
            author="NOUR DISTRIBUTION"
        )
        
        elements = []
        
        # ============ PAGE 1: HEADER & TUNISIAN FISCAL INFO ============
        elements.extend(self._create_tunisian_header("FACTURE", is_invoice=True))
        elements.append(Spacer(1, 0.5*cm))
        
        # Tunisian fiscal stamp simulation
        elements.extend(self._create_tunisian_fiscal_stamp(facture))
        elements.append(Spacer(1, 0.5*cm))
        
        # Document info with Tunisian requirements
        elements.extend(self._create_document_info(facture))
        elements.append(Spacer(1, 1*cm))
        
        # Client info (Tunisian format)
        elements.extend(self._create_tunisian_client_section(client, is_invoice=True))
        elements.append(Spacer(1, 1*cm))
        
        # ============ ITEMS TABLE WITH TUNISIAN VAT BREAKDOWN ============
        elements.append(self._create_tunisian_items_table(items, is_devis=False))
        elements.append(Spacer(1, 1*cm))
        
        # ============ TUNISIAN VAT CALCULATION DETAILS ============
        elements.extend(self._create_tunisian_vat_breakdown(items, facture))
        elements.append(Spacer(1, 1*cm))
        
        # ============ TOTALS IN TUNISIAN DINAR ============
        elements.extend(self._create_tunisian_totals_section(facture, "facture"))
        elements.append(Spacer(1, 1*cm))
        
        # ============ PAYMENT INFORMATION ============
        if payments:
            elements.extend(self._create_payment_section_tunisia(payments, facture))
        
        # ============ TUNISIAN LEGAL REQUIREMENTS FOR INVOICES ============
        elements.extend(self._create_tunisian_legal_section_facture(facture))
        
        # ============ PAGE 2: BANK INFO & TERMS ============
        elements.append(PageBreak())
        elements.extend(self._create_tunisian_bank_info())
        elements.append(Spacer(1, 1*cm))
        
        # QR Code for Tunisian tax authority (optional but recommended)
        elements.extend(self._create_tunisian_tax_qr_code(facture, client))
        
        # ============ TERMS IN FRENCH & ARABIC ============
        elements.extend(self._create_terms_section_tunisia(facture, is_invoice=True))
        
        # ============ SIGNATURE ============
        elements.append(Spacer(1, 3*cm))
        elements.extend(self._create_signature_section_tunisia(is_invoice=True))
        
        # ============ FOOTER ============
        elements.append(self._create_tunisian_footer(is_invoice=True))
        
        doc.build(elements, onFirstPage=self._add_tunisian_page_numbers, 
                 onLaterPages=self._add_tunisian_page_numbers)
        
        return filepath
    
    def generate_avoir_pdf(self, avoir: Dict, client: Dict, items: List[Dict]) -> str:
        """Generate Tunisian-compliant avoir (credit note) PDF"""
        filename = f"avoir_{avoir['document_number']}.pdf"
        filepath = os.path.join("documents", "avoirs", filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"Avoir {avoir['document_number']}",
            author="NOUR DISTRIBUTION"
        )
        
        elements = []
        
        # ============ AVOIR HEADER ============
        elements.extend(self._create_tunisian_header("AVOIR", is_credit_note=True))
        elements.append(Spacer(1, 0.5*cm))
        
        # Reference to original facture
        elements.extend(self._create_avoir_reference_section(avoir))
        elements.append(Spacer(1, 1*cm))
        
        # Client info
        elements.extend(self._create_tunisian_client_section(client))
        elements.append(Spacer(1, 1*cm))
        
        # Items being credited
        elements.append(self._create_tunisian_items_table(items, is_avoir=True))
        elements.append(Spacer(1, 1*cm))
        
        # Totals with VAT adjustment
        elements.extend(self._create_tunisian_totals_section(avoir, "avoir"))
        elements.append(Spacer(1, 1*cm))
        
        # Reason for credit note (Tunisian requirements)
        elements.extend(self._create_avoir_reason_section(avoir))
        
        # Legal requirements for avoir in Tunisia
        elements.extend(self._create_tunisian_legal_section_avoir(avoir))
        
        # Signature
        elements.append(Spacer(1, 3*cm))
        elements.extend(self._create_signature_section_tunisia(is_credit_note=True))
        
        # Footer
        elements.append(self._create_tunisian_footer())
        
        doc.build(elements, onFirstPage=self._add_tunisian_page_numbers)
        
        return filepath
    
    def _create_tunisian_header(self, doc_type: str, is_invoice: bool = False, is_credit_note: bool = False) -> List:
        """Create Tunisian compliant header"""
        elements = []
        
        # Company name in French and Arabic
        elements.append(Paragraph("NOUR DISTRIBUTION SARL", self.styles['CompanyName']))
        
        # Business description in French
        elements.append(Paragraph("Grossiste en cheveux de qualité professionnelle", self.styles['TunisianAddress']))
        
        # Address in Tunisian format
        address_lines = [
            self.COMPANY_INFO['address'],
            self.COMPANY_INFO['city'] + ", Tunisie",
            f"Tél: {self.COMPANY_INFO['phone']} | Email: {self.COMPANY_INFO['email']}",
            f"Site: {self.COMPANY_INFO['website']}"
        ]
        
        for line in address_lines:
            elements.append(Paragraph(line, self.styles['TunisianAddress']))
        
        # Tunisian fiscal information (REQUIRED)
        fiscal_info = [
            f"Matricule Fiscale: {self.COMPANY_INFO['matricule_fiscale']}",
            f"Registre de Commerce: {self.COMPANY_INFO['registre_commerce']}",
            f"Code TVA: {self.COMPANY_INFO['code_tva']}",
            f"Agent Économique: {self.COMPANY_INFO['agent_économique']}"
        ]
        
        for info in fiscal_info:
            elements.append(Paragraph(info, self.styles['FiscalInfo']))
        
        # Document type with French/Arabic
        if is_invoice:
            title = f"FACTURE N° {doc_type}<br/><font size=10>فاتورة</font>"
            elements.append(Paragraph(title, self.styles['DocumentTitle']))
        elif is_credit_note:
            title = f"AVOIR N° {doc_type}<br/><font size=10>أمر إرجاع</font>"
            elements.append(Paragraph(title, self.styles['DocumentTitle']))
        else:
            title = f"DEVIS N° {doc_type}<br/><font size=10>عرض سعر</font>"
            elements.append(Paragraph(title, self.styles['DocumentTitle']))
        
        return elements
    
    def _create_tunisian_fiscal_stamp(self, document: Dict) -> List:
        """Create simulated Tunisian fiscal stamp"""
        elements = []
        
        stamp_text = """
        <para align=center>
        <font name="Helvetica-Bold" size=10 color="red">
        TIMBRE FISCAL<br/>
        Conforme à la réglementation tunisienne<br/>
        Article 10 du Code de la TVA
        </font>
        </para>
        """
        
        elements.append(Paragraph(stamp_text, self.styles['Normal']))
        
        return elements
    
    def _create_tunisian_client_section(self, client: Dict, is_invoice: bool = False) -> List:
        """Create client section in Tunisian format"""
        elements = []
        
        client_type = "Client Professionnel" if client.get("type") == "b2b" else "Client Particulier"
        title = f"INFORMATIONS CLIENT ({client_type})"
        
        elements.append(Paragraph(title, self.styles['Heading2']))
        
        # Tunisian client information requirements
        if client.get("type") == "b2b":
            client_info = [
                f"Raison Sociale: {client.get('company_name', 'Non spécifié')}",
                f"Matricule Fiscale: {client.get('fiscal_id', 'Non spécifié')}",
                f"Adresse: {client.get('address', 'Non spécifié')}",
                f"Contact: {client.get('contact_name', 'Non spécifié')}",
                f"Téléphone: {client.get('phone', 'Non spécifié')}",
                f"Email: {client.get('email', 'Non spécifié')}"
            ]
        else:
            client_info = [
                f"Nom: {client.get('first_name', '')} {client.get('last_name', '')}",
                f"Carte d'Identité: {client.get('id_card', 'Non spécifié')}",
                f"Adresse: {client.get('address', 'Non spécifié')}",
                f"Téléphone: {client.get('phone', 'Non spécifié')}",
                f"Email: {client.get('email', 'Non spécifié')}"
            ]
        
        # Add Tunisian VAT info for B2B clients
        if client.get("type") == "b2b" and is_invoice:
            client_info.append(f"Code TVA Client: {client.get('vat_number', 'Non assujetti')}")
        
        for info in client_info:
            elements.append(Paragraph(info, self.styles['Normal']))
        
        return elements
    
    def _create_tunisian_items_table(self, items: List[Dict], is_devis: bool = False, is_avoir: bool = False) -> Table:
        """Create items table with Tunisian VAT columns"""
        
        # Headers in French with Tunisian requirements
        headers = ["Désignation", "Réf.", "Qté", "Prix U HT", "Remise %", "Montant HT"]
        
        # Add VAT columns for invoices (required in Tunisia)
        if not is_devis:
            headers.extend(["Taux TVA", "Montant TVA", "Montant TTC"])
        
        data = [headers]
        
        for item in items:
            unit_price_ht = item.get('unit_price', 0) / (1 + self.VAT_RATES['standard'])
            quantity = item.get('quantity', 0)
            discount = item.get('discount_percent', 0)
            
            # Calculate amounts
            base_amount = unit_price_ht * quantity
            discount_amount = base_amount * (discount / 100)
            net_amount_ht = base_amount - discount_amount
            
            # Tunisian VAT calculation
            vat_rate = item.get('vat_rate', 'standard')
            vat_percent = self.VAT_RATES.get(vat_rate, 0.19) * 100
            vat_amount = net_amount_ht * self.VAT_RATES.get(vat_rate, 0.19)
            amount_ttc = net_amount_ht + vat_amount
            
            row = [
                item.get('product_name', '')[:40],  # Limit length
                item.get('product_sku', ''),
                str(quantity),
                f"{unit_price_ht:,.3f} DT",
                f"{discount}%" if discount > 0 else "-",
                f"{net_amount_ht:,.3f} DT"
            ]
            
            if not is_devis:
                row.extend([
                    f"{vat_percent:.0f}%",
                    f"{vat_amount:,.3f} DT",
                    f"{amount_ttc:,.3f} DT"
                ])
            
            data.append(row)
        
        # Column widths for Tunisian format
        col_widths = [8*cm, 2.5*cm, 2*cm, 3*cm, 2*cm, 3*cm]
        if not is_devis:
            col_widths.extend([2*cm, 3*cm, 3*cm])
        
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Tunisian style
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Product name left aligned
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        
        # Highlight totals row
        if len(data) > 1:
            style.add('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8F9F9'))
            style.add('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
            style.add('LINEABOVE', (0, -1), (-1, -1), 2, colors.black)
        
        table.setStyle(style)
        
        return table
    
    def _create_tunisian_vat_breakdown(self, items: List[Dict], document: Dict) -> List:
        """Create detailed Tunisian VAT breakdown"""
        elements = []
        
        elements.append(Paragraph("<b>DÉTAIL DE LA TVA</b>", self.styles['Heading3']))
        
        # Group items by VAT rate
        vat_totals = {}
        
        for item in items:
            vat_rate = item.get('vat_rate', 'standard')
            vat_percent = self.VAT_RATES.get(vat_rate, 0.19) * 100
            
            unit_price_ht = item.get('unit_price', 0) / (1 + self.VAT_RATES.get(vat_rate, 0.19))
            quantity = item.get('quantity', 0)
            discount = item.get('discount_percent', 0)
            
            base_amount = unit_price_ht * quantity
            discount_amount = base_amount * (discount / 100)
            net_amount_ht = base_amount - discount_amount
            vat_amount = net_amount_ht * self.VAT_RATES.get(vat_rate, 0.19)
            
            if vat_percent not in vat_totals:
                vat_totals[vat_percent] = {
                    'base_ht': 0,
                    'vat_amount': 0,
                    'ttc': 0
                }
            
            vat_totals[vat_percent]['base_ht'] += net_amount_ht
            vat_totals[vat_percent]['vat_amount'] += vat_amount
            vat_totals[vat_percent]['ttc'] += net_amount_ht + vat_amount
        
        # Create VAT breakdown table
        vat_data = [["Taux TVA", "Base HT (DT)", "Montant TVA (DT)", "Montant TTC (DT)"]]
        
        total_base_ht = 0
        total_vat = 0
        total_ttc = 0
        
        for vat_percent, totals in sorted(vat_totals.items()):
            vat_data.append([
                f"{vat_percent:.0f}%",
                f"{totals['base_ht']:,.3f}",
                f"{totals['vat_amount']:,.3f}",
                f"{totals['ttc']:,.3f}"
            ])
            
            total_base_ht += totals['base_ht']
            total_vat += totals['vat_amount']
            total_ttc += totals['ttc']
        
        # Add totals row
        vat_data.append([
            "<b>TOTAL</b>",
            f"<b>{total_base_ht:,.3f}</b>",
            f"<b>{total_vat:,.3f}</b>",
            f"<b>{total_ttc:,.3f}</b>"
        ])
        
        vat_table = Table(vat_data, colWidths=[3*cm, 4*cm, 4*cm, 4*cm])
        vat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8F9F9')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(vat_table)
        
        # Tunisian legal note about VAT
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph(
            "<font size=8>Conforme à l'article 8 du Code de la TVA tunisienne - " +
            "TVA collectée par NOUR DISTRIBUTION SARL, " +
            f"Matricule Fiscale: {self.COMPANY_INFO['matricule_fiscale']}</font>",
            self.styles['LegalNotice']
        ))
        
        return elements
    
    def _create_tunisian_totals_section(self, document: Dict, doc_type: str) -> List:
        """Create totals section in Tunisian Dinar"""
        elements = []
        
        # Main totals table
        totals_data = [
            ["Sous-total HT", f"{document.get('subtotal', 0):,.3f} DT"],
            ["Remise globale", f"{document.get('discount', 0):,.3f} DT"],
            ["Frais de livraison", f"{document.get('shipping_fee', 0):,.3f} DT"],
            ["TVA 19%", f"{document.get('tax_amount', 0):,.3f} DT"],
            ["<b>TOTAL TTC</b>", f"<b>{document.get('total_amount', 0):,.3f} DT</b>"]
        ]
        
        if doc_type == "facture":
            totals_data.insert(4, ["Timbre fiscal", "0,600 DT"])  # Tunisian stamp duty
        
        totals_table = Table(totals_data, colWidths=[10*cm, 5*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#27AE60')),
            ('LINEABOVE', (0, -2), (-1, -2), 1, colors.black),
            ('SPACEAFTER', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(totals_table)
        
        # Amount in letters (French)
        elements.append(Spacer(1, 0.5*cm))
        amount_in_words = self._number_to_french_words(document.get('total_amount', 0))
        elements.append(Paragraph(
            f"<b>Arrêté la présente facture à la somme de :</b> {amount_in_words} dinars tunisiens",
            self.styles['Normal']
        ))
        
        return elements
    
    def _create_tunisian_legal_section_facture(self, facture: Dict) -> List:
        """Create Tunisian legal requirements section for invoices"""
        elements = []
        
        elements.append(Spacer(1, 1*cm))
        
        legal_text = """
        <para align=justify>
        <font size=9>
        <b>CONDITIONS LÉGALES - RÉPUBLIQUE TUNISIENNE</b><br/><br/>
        
        1. Conformément à la loi n°2016-71 du 30 septembre 2016 relative au recouvrement des créances commerciales.<br/>
        2. Tout retard de paiement entraînera l'application d'intérêts de retard au taux légal en vigueur.<br/>
        3. La TVA est exigible selon les dispositions du Code de la TVA tunisien.<br/>
        4. En cas de litige, les tribunaux de Tunis sont seuls compétents.<br/>
        5. Les marchandises voyagent aux risques et périls du destinataire.<br/>
        6. Aucun retour n'est accepté sans autorisation préalable.<br/>
        7. Cette facture constitue un titre exécutoire conformément à l'article 334 du Code de Commerce.<br/>
        <br/>
        <b>Mention légale obligatoire :</b> "Le client dispose d'un délai de 10 jours pour formuler ses réserves par écrit."
        </font>
        </para>
        """
        
        elements.append(Paragraph(legal_text, self.styles['LegalNotice']))
        
        return elements
    
    def _create_tunisian_bank_info(self) -> List:
        """Create Tunisian bank information section"""
        elements = []
        
        elements.append(Paragraph("<b>INFORMATIONS BANCAIRES</b>", self.styles['Heading2']))
        
        bank_data = [
            ["Banque", self.COMPANY_INFO['banque']],
            ["RIB", self.COMPANY_INFO['rib']],
            ["IBAN", self.COMPANY_INFO['iban']],
            ["BIC/SWIFT", self.COMPANY_INFO['bic']],
            ["Titulaire du compte", "NOUR DISTRIBUTION SARL"],
            ["Adresse de la banque", "Avenue Habib Bourguiba, Tunis 1000"]
        ]
        
        bank_table = Table(bank_data, colWidths=[5*cm, 10*cm])
        bank_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECF0F1')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(bank_table)
        
        elements.append(Spacer(1, 0.5*cm))
        
        # Payment terms in Tunisian context
        payment_terms = """
        <para align=justify>
        <font size=9>
        <b>CONDITIONS DE PAIEMENT :</b><br/>
        • Paiement par virement bancaire à réception de la facture<br/>
        • Les chèques sont acceptés sous réserve de provision<br/>
        • Paiement en espèces limité à 5 000 DT conformément à la réglementation<br/>
        • Escompte de 2% pour paiement dans les 7 jours<br/>
        </font>
        </para>
        """
        
        elements.append(Paragraph(payment_terms, self.styles['Normal']))
        
        return elements
    
    def _create_tunisian_tax_qr_code(self, document: Dict, client: Dict) -> List:
        """Create QR code for Tunisian tax authority (e-invoicing)"""
        elements = []
        
        try:
            # Tunisian e-invoicing QR code data structure
            qr_data = {
                "version": "1.0",
                "seller": {
                    "name": self.COMPANY_INFO['name'],
                    "vat": self.COMPANY_INFO['code_tva'],
                    "tax": self.COMPANY_INFO['matricule_fiscale']
                },
                "buyer": {
                    "name": client.get('company_name') or f"{client.get('first_name', '')} {client.get('last_name', '')}",
                    "vat": client.get('vat_number', ''),
                    "tax": client.get('fiscal_id', '')
                },
                "invoice": {
                    "number": document.get('document_number', ''),
                    "date": document.get('issue_date', datetime.now()).strftime("%Y-%m-%d"),
                    "total": document.get('total_amount', 0),
                    "tax": document.get('tax_amount', 0),
                    "currency": "TND"
                }
            }
            
            # Create QR code
            qr = qrcode.QRCode(version=1, box_size=4, border=2)
            qr.add_data(str(qr_data))
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to bytes
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Convert to base64 for PDF embedding
            img_str = base64.b64encode(buffer.read()).decode()
            
            # Create image in PDF
            from reportlab.platypus import Image as RLImage
            
            qr_img = RLImage(BytesIO(base64.b64decode(img_str)), width=4*cm, height=4*cm)
            
            elements.append(Spacer(1, 1*cm))
            elements.append(Paragraph("<b>CODE QR POUR ADMINISTRATION FISCALE</b>", self.styles['Heading3']))
            elements.append(qr_img)
            elements.append(Paragraph(
                "<font size=8>Scannez pour vérification électronique - Conforme à la loi tunisienne sur l'e-facturation</font>",
                self.styles['LegalNotice']
            ))
            
        except Exception as e:
            # Fallback if QR generation fails
            print(f"QR Code generation failed: {e}")
        
        return elements
    
    def _number_to_french_words(self, number: float) -> str:
        """Convert number to French words for Tunisian invoices"""
        # Simplified version - in production, use a proper library
        integer_part = int(number)
        decimal_part = int(round((number - integer_part) * 100))
        
        # Basic number conversion
        units = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
        teens = ["dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", 
                "dix-sept", "dix-huit", "dix-neuf"]
        tens = ["", "dix", "vingt", "trente", "quarante", "cinquante", 
               "soixante", "soixante-dix", "quatre-vingt", "quatre-vingt-dix"]
        
        def convert_numeric(n):
            if n == 0:
                return "zéro"
            elif n < 10:
                return units[n]
            elif n < 20:
                return teens[n - 10]
            elif n < 100:
                ten = n // 10
                unit = n % 10
                if unit == 0:
                    return tens[ten]
                elif ten == 7 or ten == 9:
                    # Special case for 70-79 and 90-99
                    return convert_numeric(60 + (n - 60)) if ten == 7 else convert_numeric(80 + (n - 80))
                else:
                    return f"{tens[ten]}-{units[unit]}"
            elif n < 1000:
                hundred = n // 100
                rest = n % 100
                if hundred == 1:
                    prefix = "cent"
                else:
                    prefix = f"{units[hundred]} cents"
                if rest == 0:
                    return prefix
                else:
                    return f"{prefix} {convert_numeric(rest)}"
            elif n < 1000000:
                thousand = n // 1000
                rest = n % 1000
                if thousand == 1:
                    prefix = "mille"
                else:
                    prefix = f"{convert_numeric(thousand)} mille"
                if rest == 0:
                    return prefix
                else:
                    return f"{prefix} {convert_numeric(rest)}"
            else:
                return str(n)
        
        words = convert_numeric(integer_part)
        
        if decimal_part > 0:
            words += f" et {decimal_part:02d}/100"
        
        return words.capitalize()
    
    def _add_tunisian_page_numbers(self, canvas_obj, doc):
        """Add Tunisian-style page numbers"""
        page_num = canvas_obj.getPageNumber()
        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.drawRightString(doc.pagesize[0] - 2*cm, 1*cm, f"Page {page_num}")
        
        # Add Tunisian company info at bottom of every page
        canvas_obj.drawCentredString(
            doc.pagesize[0] / 2, 
            1*cm, 
            f"{self.COMPANY_INFO['name']} - {self.COMPANY_INFO['matricule_fiscale']}"
        )
    
    def _create_tunisian_footer(self, is_invoice: bool = False) -> Spacer:
        """Create Tunisian footer with legal info"""
        # Footer is handled by _add_tunisian_page_numbers
        return Spacer(1, 2*cm)

# Update the NotificationService to use current year
def _get_base_context(self):
    """Get base context for all email templates"""
    from datetime import datetime
    return {
        "current_year": datetime.now().year,
        "company_name": "NOUR DISTRIBUTION",
        "company_email": "contact@nour-distribution.tn",
        "company_phone": "+216 71 123 456",
        "company_address": "Rue Habib Bourguiba, Tunis 1001, Tunisie",
        "company_website": "https://www.nour-distribution.tn"
    }

def _create_document_info(self, document: Dict) -> List:
    """Create document info section"""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    
    elements = []
    
    doc_info_data = [
        ["N° Document:", document.get('document_number', '')],
        ["Date d'émission:", document.get('issue_date', datetime.now()).strftime("%d/%m/%Y") if isinstance(document.get('issue_date'), datetime) else document.get('issue_date', '')],
    ]
    
    if document.get('due_date'):
        due_date = document['due_date']
        due_date_str = due_date.strftime("%d/%m/%Y") if isinstance(due_date, datetime) else due_date
        doc_info_data.append(["Date d'échéance:", due_date_str])
    
    doc_info_table = Table(doc_info_data, colWidths=[5*cm, 8*cm])
    doc_info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(doc_info_table)
    
    return elements


def _create_terms_section_tunisia(self, document: Dict, is_invoice: bool = False) -> List:
    """Create terms and conditions section"""
    from reportlab.platypus import Paragraph, Spacer
    
    elements = []
    
    elements.append(Paragraph("<b>CONDITIONS GÉNÉRALES</b>", self.styles['Heading2']))
    elements.append(Spacer(1, 0.5*cm))
    
    if is_invoice:
        terms_text = """
        <para align=justify>
        <font size=9>
        1. Paiement à réception de facture sauf accord préalable<br/>
        2. Tout retard de paiement entraîne l'application d'intérêts de retard<br/>
        3. En cas de litige, seuls les tribunaux de Tunis sont compétents<br/>
        4. Les marchandises voyagent aux risques du destinataire<br/>
        5. Garantie limitée selon nos conditions générales de vente<br/>
        </font>
        </para>
        """
    else:
        terms_text = """
        <para align=justify>
        <font size=9>
        1. Devis valable 30 jours à compter de la date d'émission<br/>
        2. Prix exprimés en Dinars Tunisiens (TND), TVA incluse<br/>
        3. Délai de livraison estimé: 7-14 jours ouvrables<br/>
        4. Conditions de paiement à convenir<br/>
        5. Réservation de stock sous acceptation du devis<br/>
        </font>
        </para>
        """
    
    elements.append(Paragraph(terms_text, self.styles['Normal']))
    
    if document.get('terms'):
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("<b>Notes additionnelles:</b>", self.styles['Heading3']))
        elements.append(Paragraph(document['terms'], self.styles['Normal']))
    
    return elements


def _create_signature_section_tunisia(self, is_invoice: bool = False, is_credit_note: bool = False) -> List:
    """Create signature section"""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    
    elements = []
    
    signature_data = [
        ["Signature du client", "Cachet et signature NOUR DISTRIBUTION"],
        ["", ""],
        ["", ""],
        ["Date: _______________", "Date: _______________"]
    ]
    
    signature_table = Table(signature_data, colWidths=[8*cm, 8*cm])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (0, -1), 1, colors.grey),
        ('BOX', (1, 0), (1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    
    elements.append(signature_table)
    
    return elements


def _create_tunisian_legal_section_devis(self, devis: Dict) -> List:
    """Create legal section for devis"""
    from reportlab.platypus import Paragraph, Spacer
    
    elements = []
    
    elements.append(Spacer(1, 1*cm))
    
    legal_text = """
    <para align=justify>
    <font size=8>
    <b>MENTIONS LÉGALES:</b><br/>
    Ce devis est valable 30 jours. Les prix sont exprimés en Dinars Tunisiens TTC.
    Conformément à la législation tunisienne, ce devis n'engage le vendeur qu'après acceptation écrite du client.
    La commande ferme ne sera considérée qu'après signature du devis et versement de l'acompte si requis.
    </font>
    </para>
    """
    
    elements.append(Paragraph(legal_text, self.styles['LegalNotice']))
    
    return elements


def _create_avoir_reference_section(self, avoir: Dict) -> List:
    """Create avoir reference to original facture"""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    
    elements = []
    
    elements.append(Paragraph("<b>RÉFÉRENCE</b>", self.styles['Heading2']))
    
    if avoir.get('reference_document_id'):
        ref_data = [
            ["Facture d'origine:", avoir.get('reference_document_number', 'N/A')],
            ["Raison:", avoir.get('notes', 'Avoir commercial').split('\n')[0][:100]]
        ]
        
        ref_table = Table(ref_data, colWidths=[5*cm, 10*cm])
        ref_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8F9F9')),
        ]))
        
        elements.append(ref_table)
    
    return elements


def _create_avoir_reason_section(self, avoir: Dict) -> List:
    """Create reason section for avoir"""
    from reportlab.platypus import Paragraph, Spacer
    
    elements = []
    
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("<b>MOTIF DE L'AVOIR</b>", self.styles['Heading2']))
    
    reason_text = avoir.get('notes', 'Avoir commercial')
    elements.append(Paragraph(reason_text, self.styles['Normal']))
    
    return elements


def _create_tunisian_legal_section_avoir(self, avoir: Dict) -> List:
    """Create legal section for avoir"""
    from reportlab.platypus import Paragraph, Spacer
    
    elements = []
    
    elements.append(Spacer(1, 1*cm))
    
    legal_text = """
    <para align=justify>
    <font size=8>
    <b>MENTIONS LÉGALES - AVOIR:</b><br/>
    Cet avoir annule partiellement ou totalement la facture référencée ci-dessus.
    Le montant de l'avoir peut être déduit des factures à venir ou remboursé selon accord.
    Conforme à la réglementation tunisienne en matière de TVA.
    </font>
    </para>
    """
    
    elements.append(Paragraph(legal_text, self.styles['LegalNotice']))
    
    return elements


def _create_payment_section_tunisia(self, payments: List[Dict], facture: Dict) -> List:
    """Create payment details section"""
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    
    elements = []
    
    if not payments:
        return elements
    
    elements.append(Paragraph("<b>PAIEMENTS REÇUS</b>", self.styles['Heading2']))
    elements.append(Spacer(1, 0.5*cm))
    
    payment_data = [["Date", "Montant", "Méthode", "Référence"]]
    
    for payment in payments:
        payment_date = payment['payment_date']
        date_str = payment_date.strftime("%d/%m/%Y") if isinstance(payment_date, datetime) else payment_date
        
        payment_data.append([
            date_str,
            f"{payment['amount']:,.3f} DT",
            payment.get('payment_method', 'N/A'),
            payment.get('reference_number', '-')
        ])
    
    # Add total row
    payment_data.append([
        "<b>TOTAL PAYÉ</b>",
        f"<b>{facture.get('paid_amount', 0):,.3f} DT</b>",
        "",
        ""
    ])
    
    payment_data.append([
        "<b>RESTE À PAYER</b>",
        f"<b>{facture.get('remaining_amount', 0):,.3f} DT</b>",
        "",
        ""
    ])
    
    payment_table = Table(payment_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
    payment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -3), colors.white),
        ('BACKGROUND', (0, -2), (-1, -1), colors.HexColor('#F8F9F9')),
        ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    elements.append(payment_table)
    elements.append(Spacer(1, 1*cm))
    
    return elements