import io
import random
import logging
from typing import Dict, Any

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128

from app.database.mongodb import db
from app.services.gridfs_service import GridFSService

logger = logging.getLogger("app.services.label")

class ShippingLabelService:
    @classmethod
    async def generate_mock_label(cls, return_id: str, customer_name: str) -> Dict[str, Any]:
        """
        Generates return tracking details, generates a PDF, and stores it in GridFS.
        """
        serial = random.randint(10000, 99999)
        label_number = f"RET-2026-{serial}"
        tracking_number = f"940010000000{random.randint(1000000000, 9999999999)}"
        carrier = "USPS"

        # Generate PDF in memory
        pdf_bytes = cls.generate_pdf_bytes(return_id, customer_name, tracking_number, carrier)

        # Store in GridFS
        label_file_id = await GridFSService.upload_bytes(
            data=pdf_bytes,
            filename=f"shipping_label_{return_id}.pdf",
            content_type="application/pdf",
            metadata={
                "return_id": return_id,
                "label_number": label_number,
                "tracking_number": tracking_number,
                "carrier": carrier
            }
        )

        label_doc = {
            "label_number": label_number,
            "tracking_number": tracking_number,
            "carrier": carrier,
            "label_file_id": label_file_id,
            "shipping_label_url": f"http://localhost:8000/api/uploads/{label_file_id}"
        }

        logger.info(f"Generated and stored mock shipping label {label_number} for return {return_id} in GridFS. ID: {label_file_id}")
        return label_doc

    @classmethod
    def generate_pdf_bytes(cls, return_id: str, customer_name: str, tracking_number: str, carrier: str) -> bytes:
        """
        Generates a USPS mock shipping label PDF using ReportLab and returns raw bytes.
        """
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Define bounds for the label box (Centered on page)
        width = 288
        height = 432
        x = (612 - width) / 2
        y = (792 - height) / 2
        
        # External label border
        c.setLineWidth(2)
        c.rect(x, y, width, height, stroke=1, fill=0)
        
        # Top Banner / Postage block
        c.setLineWidth(1)
        header_divider_y = y + height - 80
        c.line(x, header_divider_y, x + width, header_divider_y)
        
        # Draw vertical divider in header
        vert_divider_x = x + 160
        c.line(vert_divider_x, y + height, vert_divider_x, header_divider_y)
        
        # Top-Left Header: Service Name
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x + 10, y + height - 25, "USPS RETURN SERVICE")
        c.setFont("Helvetica", 8)
        c.drawString(x + 10, y + height - 42, "USPS GROUND ADVANTAGE")
        c.drawString(x + 10, y + height - 55, "ESTIMATED WT: 1 LB 0 OZ")
        c.drawString(x + 10, y + height - 68, "POSTAGE PAID BY SENDER")
        
        # Top-Right Header: Postage indicator box
        c.rect(vert_divider_x + 15, y + height - 65, 95, 50, stroke=1, fill=0)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(vert_divider_x + 62, y + height - 25, "NO POSTAGE")
        c.drawCentredString(vert_divider_x + 62, y + height - 35, "NECESSARY")
        c.drawCentredString(vert_divider_x + 62, y + height - 45, "IF MAILED IN THE")
        c.drawCentredString(vert_divider_x + 62, y + height - 55, "UNITED STATES")
        
        # Return Address (Sender)
        addr_y = header_divider_y - 12
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(x + 12, addr_y, "FROM:")
        c.setFont("Helvetica", 7.5)
        c.drawString(x + 45, addr_y, customer_name)
        c.drawString(x + 45, addr_y - 10, "123 Customer St")
        c.drawString(x + 45, addr_y - 20, "Orlando, FL 32801")
        
        # Divider below FROM
        from_divider_y = header_divider_y - 50
        c.line(x, from_divider_y, x + width, from_divider_y)
        
        # Ship To Address (Recipient)
        ship_y = from_divider_y - 18
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x + 12, ship_y, "DELIVER TO:")
        c.setFont("Helvetica", 9.5)
        c.drawString(x + 12, ship_y - 15, "lateshipmentdev Return Center")
        c.drawString(x + 12, ship_y - 28, "Attention: Returns Department")
        c.drawString(x + 12, ship_y - 41, "456 Warehouse Blvd")
        c.drawString(x + 12, ship_y - 54, "Orlando, FL 32801")
        
        # Divider below Ship To
        to_divider_y = from_divider_y - 82
        c.line(x, to_divider_y, x + width, to_divider_y)
        
        # Bold USPS "T" Tracking indicator box
        c.setLineWidth(4)
        c.line(x, to_divider_y - 15, x + width, to_divider_y - 15)
        
        # Barcode Section
        barcode_y = to_divider_y - 85
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(x + width/2, to_divider_y - 32, "USPS TRACKING # / Return ID")
        
        # Generate Code128 Barcode drawing
        clean_tracking = ''.join(filter(str.isalnum, tracking_number))
        try:
            barcode = code128.Code128(clean_tracking, barWidth=1.05, barHeight=42)
            barcode_width = len(clean_tracking) * 11
            start_barcode_x = x + (width - barcode_width) / 2
            barcode.drawOn(c, start_barcode_x, barcode_y)
        except Exception as e:
            logger.error(f"Failed to render barcode: {e}")
            
        # Render human readable tracking number below barcode
        formatted_tracking = " ".join([tracking_number[i:i+4] for i in range(0, len(tracking_number), 4)])
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + width/2, barcode_y - 15, formatted_tracking)
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(x + width/2, barcode_y - 27, f"Return Ref: {return_id}")
        
        # End page & save
        c.showPage()
        c.save()
        
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data
