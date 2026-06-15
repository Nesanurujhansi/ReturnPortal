import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128

def draw_shipping_label(filename, return_id, tracking_number, carrier):
    # Setup canvas on standard letter size (612 x 792 points)
    # The label itself should be centered and sized around 4x6 inches (288 x 432 points)
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Define bounds for the label box (Centered on page)
    width = 288
    height = 432
    x = (612 - width) / 2
    y = (792 - height) / 2
    
    # 1. External label border
    c.setLineWidth(2)
    c.rect(x, y, width, height, stroke=1, fill=0)
    
    # 2. Top Banner / Postage block
    # Draw horizontal divider for top header
    c.setLineWidth(1)
    header_divider_y = y + height - 80
    c.line(x, header_divider_y, x + width, header_divider_y)
    
    # Draw vertical divider in header (Postage / Service indicator)
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
    
    # 3. Return Address (Sender)
    addr_y = header_divider_y - 12
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + 12, addr_y, "FROM:")
    c.setFont("Helvetica", 7.5)
    c.drawString(x + 45, addr_y, "Bar Vas")
    c.drawString(x + 45, addr_y - 10, "123 Customer St")
    c.drawString(x + 45, addr_y - 20, "Orlando, FL 32801")
    
    # Divider below FROM
    from_divider_y = header_divider_y - 50
    c.line(x, from_divider_y, x + width, from_divider_y)
    
    # 4. Ship To Address (Recipient - Store Warehouse)
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
    
    # 5. Bold USPS "T" Tracking indicator box
    c.setLineWidth(4)
    c.line(x, to_divider_y - 15, x + width, to_divider_y - 15)
    
    # 6. Barcode Section
    barcode_y = to_divider_y - 85
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x + width/2, to_divider_y - 32, "USPS TRACKING # / Return ID")
    
    # Generate Code128 Barcode drawing
    clean_tracking = ''.join(filter(str.isalnum, tracking_number))
    try:
        # Standard width: 1.1 pt, height: 42 pt
        barcode = code128.Code128(clean_tracking, barWidth=1.05, barHeight=42)
        # Draw directly to canvas
        # Center the barcode (calculate starting x coordinate)
        barcode_width = len(clean_tracking) * 11 # approximate width calculation
        start_barcode_x = x + (width - barcode_width) / 2
        barcode.drawOn(c, start_barcode_x, barcode_y)
    except Exception as e:
        print(f"Failed to render barcode: {e}")
        
    # Render human readable tracking number below barcode
    formatted_tracking = " ".join([tracking_number[i:i+4] for i in range(0, len(tracking_number), 4)])
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x + width/2, barcode_y - 15, formatted_tracking)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(x + width/2, barcode_y - 27, f"Return Ref: {return_id}")
    
    # End page & save
    c.showPage()
    c.save()
    print(f"Beautiful PDF created successfully: {filename}")

if __name__ == "__main__":
    draw_shipping_label("beautiful_label.pdf", "RET-595978", "9400100000007439653032", "USPS")
