import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime

def generate_invoice_pdf(order_details, items, output_path):
    """
    Generates a formal invoice PDF using ReportLab.
    order_details: dict containing user_name, user_email, payment_id, date, amount
    items: list of dicts containing name, category, price
    output_path: path to save the PDF
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # --- Header ---
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.HexColor("#006BB6")) # MataVex blue-ish
    c.drawString(50, height - 70, "MATAVEX TECHNOLOGIES")
    
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(50, height - 85, "Secure Infrastructure & Project Solutions")
    c.drawString(50, height - 98, "Email: contact@matavex.tech")
    
    # --- Invoice Info ---
    c.setFont("Helvetica-Bold", 14)
    c.drawString(400, height - 70, "INVOICE")
    
    c.setFont("Helvetica", 10)
    c.drawString(400, height - 85, f"Invoice No: INV-{order_details['payment_id']}")
    c.drawString(400, height - 98, f"Date: {order_details['date']}")
    c.drawString(400, height - 111, f"Status: PAID")

    # --- Bill To ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 150, "BILL TO:")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 165, f"Name: {order_details['user_name']}")
    c.drawString(50, height - 178, f"Email: {order_details['user_email']}")

    # --- Table Header ---
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(50, height - 210, 550, height - 210) # Top line
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, height - 225, "Description")
    c.drawString(300, height - 225, "Category")
    c.drawString(480, height - 225, "Amount (INR)")
    
    c.line(50, height - 235, 550, height - 235) # Bottom header line

    # --- Table Items ---
    y = height - 255
    c.setFont("Helvetica", 10)
    for item in items:
        c.drawString(60, y, item['name'])
        c.drawString(300, y, item['category'].upper())
        c.drawString(480, y, f" {item['price']:.2f}")
        y -= 20
        if y < 100: # Simple page break if too many items
            c.showPage()
            y = height - 50

    # --- Totals ---
    c.line(50, y, 550, y)
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(380, y, "Total Amount:")
    c.drawString(480, y, f"INR {order_details['amount']:.2f}")

    # --- Footer ---
    c.setFont("Helvetica-Oblique", 9)
    footer_text = "This is a computer-generated invoice and doesn't require a physical signature."
    c.drawCentredString(width / 2, 50, footer_text)
    
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2, 35, "Thank you for your business!")

    c.save()

def send_invoice_email(user_email, pdf_path, payment_id):
    """
    Sends the invoice PDF via email.
    """
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    owner_email = os.getenv("OWNER_EMAIL")

    if not email_user or not email_pass:
        return False

    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = f"{user_email}, {owner_email}"
    msg['Subject'] = f"Invoice for your Matavex Tech Order - {payment_id}"

    body = f"""
    Hello,

    Thank you for your purchase from Matavex Technologies!
    Your transaction has been successfully verified. 
    
    Please find attached your formal invoice for Payment ID: {payment_id}.
    
    Your project is now available in your Matavex Portal Library.

    Best Regards,
    The Matavex Finance Team
    """
    msg.attach(MIMEText(body, 'plain'))

    # Attach PDF
    filename = os.path.basename(pdf_path)
    try:
        with open(pdf_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {filename}")
            msg.attach(part)
    except Exception as e:
        return False

    # Send
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_user, email_pass)
        text = msg.as_string()
        server.sendmail(email_user, [user_email, owner_email], text)
        server.quit()
        return True
    except Exception as e:
        return False
