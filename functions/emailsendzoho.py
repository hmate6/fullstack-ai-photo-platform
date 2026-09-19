from functions.auth_functions import log  # REMOVED: a nem használt 'import os' törölve innen
import smtplib
import ssl  # CHANGED: ez korábban lentebb, a kód közepén volt importálva, most a többi import mellé került
from app_init import *
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

mode = "email_send"

sender = getenv("GMAIL_SENDER")
passwordd = getenv("GMAIL_PASSWORD")

def send_email_new(recipient, subject, message):
    "Email Send"
    # Create a secure SSL context
    context = ssl.create_default_context()

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "html"))

        # FIX: Use smtplib.SMTP (NOT SMTP_SSL) for port 587
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls(context=context)  # Secure the connection
            server.login(sender, passwordd)   # Use your App Password
            server.sendmail(sender, recipient, msg.as_string())
            print("Send success")
        return 0

    except Exception as e:
        print(f"Error occurred: {e}") # Or use your log(mode, "ERROR", e)
        return 1
