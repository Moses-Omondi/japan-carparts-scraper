"""
PDF generation module for creating professional reports with Japanese OEM car parts data.
This module formats scraped data with images into a professional PDF report.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from PIL import Image as PILImage
import pandas as pd


class PDFGenerator:
    """PDF generator class for creating car parts reports."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the PDF generator."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Set up custom styles for the PDF."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=15,
            textColor=colors.darkblue
        ))
        
        # Part name style
        self.styles.add(ParagraphStyle(
            name='PartName',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceBefore=10,
            spaceAfter=5,
            textColor=colors.black
        ))
        
        # Price style
        self.styles.add(ParagraphStyle(
            name='Price',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.red,
            fontName='Helvetica-Bold'
        ))
        
        # Description style
        self.styles.add(ParagraphStyle(
            name='Description',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=10,
            textColor=colors.darkgrey
        ))
    
    def create_cover_page(self, story: List, total_parts: int, generation_date: str):
        """Create a cover page for the PDF report."""
        # Title
        story.append(Paragraph("Japanese OEM Car Parts Catalog", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        # Report info
        info_data = [
            ["Total Parts Listed:", str(total_parts)],
            ["Report Generated:", generation_date],
            ["Currency:", "Original (KES, USD, JPY)"],
            ["Data Source:", "Various Japanese OEM Parts Websites"]
        ]
        
        info_table = Table(info_data, colWidths=[2.5*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 1*inch))
        
        # Disclaimer
        disclaimer_text = """
        <b>Disclaimer:</b> This report contains pricing and availability information scraped from various 
        Japanese OEM car parts websites. Prices are approximate and may have changed since data collection. 
        Please verify current pricing and availability directly with the suppliers before making any purchases.
        Exchange rates are updated regularly but may not reflect real-time rates.
        """
        
        story.append(Paragraph(disclaimer_text, self.styles['Normal']))
        story.append(PageBreak())
    
    def add_part_to_story(self, story: List, part_data: Dict[str, Any], part_number: int):
        """Add a single car part to the PDF story."""
        # Part number and name
        part_title = f"{part_number}. {part_data.get('name', 'Unknown Part')}"
        story.append(Paragraph(part_title, self.styles['PartName']))
        
        # Create a table for part details
        details = []
        
        # Part number if available
        if part_data.get('part_number'):
            details.append(["Part Number:", part_data['part_number']])
        
        # Price in original currency only
        price_jpy = part_data.get('price_jpy')
        price_usd = part_data.get('price_usd')
        price_kes = part_data.get('price_kes')
        
        price_text = None
        if price_kes:
            price_text = f"KES {price_kes:,.0f}"
        elif price_usd:
            price_text = f"${price_usd:.2f} USD"
        elif price_jpy:
            price_text = f"¥{price_jpy:,.0f} JPY"
        
        if price_text:
            details.append(["Price:", price_text])
        
        
        # Source URL with hyperlink
        if part_data.get('source_url'):
            source_url = part_data['source_url']
            # Create clickable hyperlink
            link_text = f'<link href="{source_url}" color="blue">{source_url}</link>'
            details.append(["Source:", Paragraph(link_text, self.styles['Normal'])])
        
        # Create table
        if details:
            details_table = Table(details, colWidths=[1.5*inch, 4*inch])
            details_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ]))
            story.append(details_table)
        
        # Add image if available
        image_path = part_data.get('local_image_path')
        if image_path and os.path.exists(image_path):
            try:
                # Create image with appropriate size
                img = Image(image_path)
                img._restrictSize(3*inch, 2.5*inch)  # Max size
                story.append(Spacer(1, 0.1*inch))
                story.append(img)
            except Exception as e:
                self.logger.warning(f"Could not add image {image_path}: {e}")
        
        # Add description
        description = part_data.get('description')
        if description:
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(f"<b>Description:</b> {description}", self.styles['Description']))
        
        # Add some space before next part
        story.append(Spacer(1, 0.3*inch))
    
    def create_summary_table(self, story: List, parts_data: List[Dict[str, Any]]):
        """Create a summary table with key statistics."""
        story.append(Paragraph("Price Summary", self.styles['CustomSubtitle']))
        
        if not parts_data:
            story.append(Paragraph("No parts data available for summary.", self.styles['Normal']))
            return
        
        # Calculate statistics
        jpy_prices = [part.get('price_jpy', 0) for part in parts_data if part.get('price_jpy')]
        usd_prices = [part.get('price_usd', 0) for part in parts_data if part.get('price_usd')]
        
        if jpy_prices:
            summary_data = [
                ["Metric", "JPY", "USD"],
                ["Total Parts", str(len(parts_data)), str(len(parts_data))],
                ["Parts with Prices", str(len(jpy_prices)), str(len(usd_prices))],
                ["Average Price", f"¥{sum(jpy_prices)/len(jpy_prices):,.2f}" if jpy_prices else "N/A",
                 f"${sum(usd_prices)/len(usd_prices):.2f}" if usd_prices else "N/A"],
                ["Minimum Price", f"¥{min(jpy_prices):,.2f}" if jpy_prices else "N/A",
                 f"${min(usd_prices):.2f}" if usd_prices else "N/A"],
                ["Maximum Price", f"¥{max(jpy_prices):,.2f}" if jpy_prices else "N/A",
                 f"${max(usd_prices):.2f}" if usd_prices else "N/A"],
            ]
            
            summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            story.append(summary_table)
            story.append(PageBreak())
    
    def generate_pdf(self, parts_data: List[Dict[str, Any]], output_filename: str = None) -> str:
        """
        Generate PDF report from parts data.
        
        Args:
            parts_data: List of dictionaries containing part data
            output_filename: Optional custom filename for the PDF
            
        Returns:
            Path to the generated PDF file
        """
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"japanese_car_parts_report_{timestamp}.pdf"
        
        # Ensure outputs directory exists
        os.makedirs('outputs', exist_ok=True)
        output_path = os.path.join('outputs', output_filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build story
        story = []
        
        # Cover page
        generation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.create_cover_page(story, len(parts_data), generation_date)
        
        # Summary table
        self.create_summary_table(story, parts_data)
        
        # Parts listing
        story.append(Paragraph("Parts Listing", self.styles['CustomSubtitle']))
        story.append(Spacer(1, 0.2*inch))
        
        # Add each part
        for i, part in enumerate(parts_data, 1):
            self.add_part_to_story(story, part, i)
            
            # Add page break every 3 parts to avoid overcrowding
            if i % 3 == 0 and i < len(parts_data):
                story.append(PageBreak())
        
        # Build PDF
        try:
            doc.build(story)
            self.logger.info(f"PDF report generated: {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Error generating PDF: {e}")
            raise
    
    def generate_compact_pdf(self, parts_data: List[Dict[str, Any]], output_filename: str = None) -> str:
        """
        Generate a more compact PDF report in table format.
        
        Args:
            parts_data: List of dictionaries containing part data
            output_filename: Optional custom filename for the PDF
            
        Returns:
            Path to the generated PDF file
        """
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"japanese_car_parts_compact_{timestamp}.pdf"
        
        os.makedirs('outputs', exist_ok=True)
        output_path = os.path.join('outputs', output_filename)
        
        doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=1*inch)
        story = []
        
        # Title
        story.append(Paragraph("Japanese OEM Car Parts - Compact Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.3*inch))
        
        # Create table data with original currencies only
        table_data = [["#", "Part Name", "Part Number", "Price", "Currency", "Source"]]
        
        for i, part in enumerate(parts_data, 1):
            # Determine price and currency
            price_text = 'N/A'
            currency = 'N/A'
            
            if part.get('price_kes'):
                price_text = f"KES {part.get('price_kes'):,.0f}"
                currency = 'KES'
            elif part.get('price_usd'):
                price_text = f"${part.get('price_usd'):.2f}"
                currency = 'USD'
            elif part.get('price_jpy'):
                price_text = f"¥{part.get('price_jpy'):,.0f}"
                currency = 'JPY'
            
            row = [
                str(i),
                part.get('name', 'N/A')[:30] + ('...' if len(part.get('name', '')) > 30 else ''),
                part.get('part_number', part.get('sku', 'N/A')),
                price_text,
                currency,
                Paragraph(f'<link href="{part.get("source_url", "#")}" color="blue">{part.get("source_url", "N/A")[:20] + "..." if part.get("source_url") else "N/A"}</link>', self.styles['Normal']) if part.get('source_url') else 'N/A'
            ]
            table_data.append(row)
        
        # Create table with adjusted column widths for original currencies only
        table = Table(table_data, colWidths=[0.3*inch, 2.2*inch, 1*inch, 1.2*inch, 0.6*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table)
        
        # Add generation info
        story.append(Spacer(1, 0.3*inch))
        generation_info = f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        story.append(Paragraph(generation_info, self.styles['Normal']))
        
        try:
            doc.build(story)
            self.logger.info(f"Compact PDF report generated: {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Error generating compact PDF: {e}")
            raise
    
    def generate_csv_export(self, parts_data: List[Dict[str, Any]], output_filename: str = None) -> str:
        """
        Generate CSV export of the parts data.
        
        Args:
            parts_data: List of dictionaries containing part data
            output_filename: Optional custom filename for the CSV
            
        Returns:
            Path to the generated CSV file
        """
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"japanese_car_parts_data_{timestamp}.csv"
        
        os.makedirs('outputs', exist_ok=True)
        output_path = os.path.join('outputs', output_filename)
        
        # Convert to DataFrame and export
        df = pd.DataFrame(parts_data)
        
        # Get all available columns from the data
        all_columns = set()
        for part in parts_data:
            all_columns.update(part.keys())
        
        # Define priority columns (will appear first) - no converted currencies
        priority_columns = [
            'name', 'sku', 'brand', 'model', 'category', 'stock_status',
            'price_jpy', 'price_usd', 'price_kes', 'original_currency',
            'description', 'primary_image', 'images', 'source_url',
            'page_title', 'has_warranty', 'has_shipping_info',
            'scraped_at'
        ]
        
        # Add specification columns
        spec_columns = [col for col in all_columns if col.startswith('spec_') or col.startswith('info_')]
        spec_columns.sort()
        
        # Combine all columns in logical order
        columns_to_export = []
        
        # Add priority columns that exist in data
        for col in priority_columns:
            if col in all_columns:
                columns_to_export.append(col)
        
        # Add specification columns
        columns_to_export.extend(spec_columns)
        
        # Add any remaining columns not already included
        remaining_columns = [col for col in all_columns if col not in columns_to_export]
        remaining_columns.sort()
        columns_to_export.extend(remaining_columns)
        
        if columns_to_export:
            # Create export dataframe with available columns
            export_df = df[columns_to_export].copy()
            
            # Handle complex data types (lists, dicts)
            for col in export_df.columns:
                export_df[col] = export_df[col].apply(self._format_csv_value)
            
            # Save with proper formatting
            export_df.to_csv(output_path, index=False, encoding='utf-8')
            
            # Log column information
            self.logger.info(f"CSV export generated: {output_path}")
            self.logger.info(f"Exported {len(export_df)} rows with {len(columns_to_export)} columns")
            self.logger.info(f"Columns: {', '.join(columns_to_export[:10])}{'...' if len(columns_to_export) > 10 else ''}")
        else:
            self.logger.warning("No suitable columns found for CSV export")
            return None
        
        return output_path
    
    def _format_csv_value(self, value):
        """
        Format values for CSV export, handling complex data types.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted string value
        """
        if value is None:
            return ''
        elif isinstance(value, list):
            # Join list items with semicolon separator
            return '; '.join(str(item) for item in value if item)
        elif isinstance(value, dict):
            # Convert dict to key=value pairs
            return '; '.join(f"{k}={v}" for k, v in value.items() if v is not None)
        elif isinstance(value, (int, float)):
            # Keep numbers as they are
            return value
        else:
            # Convert to string and clean up
            str_value = str(value).strip()
            # Remove newlines and excessive whitespace
            str_value = ' '.join(str_value.split())
            return str_value


def generate_sample_report():
    """Generate a sample PDF report with dummy data for testing."""
    # Sample data
    sample_parts = [
        {
            'name': 'Toyota Camry Front Brake Pads',
            'part_number': 'T-BP-001',
            'price_jpy': 15000,
            'price_usd': 100.50,
            'exchange_rate': 0.0067,
            'description': 'High-quality front brake pads for Toyota Camry 2015-2020',
            'source_url': 'https://example-carparts.jp/brake-pads',
            'rate_source': 'api'
        },
        {
            'name': 'Honda Civic Engine Oil Filter',
            'part_number': 'H-OF-002',
            'price_jpy': 2500,
            'price_usd': 16.75,
            'exchange_rate': 0.0067,
            'description': 'OEM engine oil filter for Honda Civic 2016-2021',
            'source_url': 'https://example-carparts.jp/oil-filter',
            'rate_source': 'api'
        }
    ]
    
    config = {'request_delay': 2}
    generator = PDFGenerator(config)
    
    pdf_path = generator.generate_pdf(sample_parts, 'sample_report.pdf')
    compact_pdf_path = generator.generate_compact_pdf(sample_parts, 'sample_compact_report.pdf')
    csv_path = generator.generate_csv_export(sample_parts, 'sample_data.csv')
    
    return pdf_path, compact_pdf_path, csv_path
