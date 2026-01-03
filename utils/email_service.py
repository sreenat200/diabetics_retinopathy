import smtplib
import random
import string
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    """Service for sending emails with OTP using SMTP (Gmail)"""

    def __init__(self):
        # Load email configuration from .env
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        
        if not self.sender_email or not self.sender_password:
            print("[DEBUG] CRITICAL: SENDER_EMAIL or SENDER_PASSWORD not configured. Email sending will fail.")

    def generate_otp(self, length=6):
        """Generate a random 6-digit OTP"""
        characters = string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def send_otp_email(self, recipient_email, otp, username=None):
        """Send OTP to the recipient's email"""
        if not self.sender_email or not self.sender_password:
            print("Error: SENDER_EMAIL or SENDER_PASSWORD not configured in .env")
            return False

        # Create message
        subject = "Your OTP Code"
        if username:
            body_text = f"Hello {username},\n\nYour OTP code is: {otp}\nThis code is valid for 10 minutes.\n\nRegards,\nDR Detection System"
        else:
            body_text = f"Your OTP code is: {otp}\nThis code is valid for 10 minutes."
            
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        message.attach(MIMEText(body_text, "plain"))

        try:
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable TLS
            server.login(self.sender_email, self.sender_password)
            
            # Send email
            server.send_message(message)
            print(f"OTP sent successfully to {recipient_email}")
            server.quit()
            return True
        except smtplib.SMTPAuthenticationError:
            print("Authentication failed. Check your email and App Password. Ensure 2-Step Verification is enabled and use an App Password.")
            return False
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
            
    def send_password_reset_email(self, recipient_email, reset_code, username=None):
        """Send password reset code via email"""
        if not self.sender_email or not self.sender_password:
            print("Error: SENDER_EMAIL or SENDER_PASSWORD not configured in .env")
            return False

        # Create message
        subject = "Password Reset Code"
        if username:
            body_text = f"Hello {username},\n\nYour password reset code is: {reset_code}\nThis code is valid for 10 minutes.\n\nRegards,\nDR Detection System"
        else:
            body_text = f"Your password reset code is: {reset_code}\nThis code is valid for 10 minutes."

        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        message.attach(MIMEText(body_text, "plain"))

        try:
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable TLS
            server.login(self.sender_email, self.sender_password)
            
            # Send email
            server.send_message(message)
            print(f"Password reset email sent successfully to {recipient_email}")
            server.quit()
            return True
        except smtplib.SMTPAuthenticationError:
            print("Authentication failed. Check your email and App Password. Ensure 2-Step Verification is enabled and use an App Password.")
            return False
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
