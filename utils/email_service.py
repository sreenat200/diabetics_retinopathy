import os
from dotenv import load_dotenv
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

load_dotenv()

class EmailService:
    """Service for sending emails with OTP using Brevo API"""

    def __init__(self):
        self.api_key = os.getenv("BREVO_API_KEY")
        self.sender_email = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@example.com")

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = self.api_key

        self.api_client = sib_api_v3_sdk.ApiClient(configuration)
        self.email_api = sib_api_v3_sdk.TransactionalEmailsApi(self.api_client)

    def email_template(self, title, message, code):
        """Reusable professional email template"""
        return f"""
        <html>
        <body style="margin:0; padding:0; font-family:Arial, sans-serif; background:#f3f6fa;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6fa; padding:40px 0;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background:white; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,0.08); padding:30px;">
                            
                            <!-- Header -->
                            <tr>
                                <td style="text-align:center;">
                                    <h2 style="color:#1e3a8a; margin:0; font-size:26px; font-weight:700;">
                                        {title}
                                    </h2>
                                    <p style="color:#555; margin-top:8px; font-size:15px;">
                                        DR Detection System – AI Powered Screening
                                    </p>
                                </td>
                            </tr>

                            <!-- Message -->
                            <tr>
                                <td style="padding:20px 0;">
                                    <p style="color:#333; font-size:16px; text-align:center; margin:0 20px;">
                                        {message}
                                    </p>
                                </td>
                            </tr>

                            <!-- OTP / Code Box -->
                            <tr>
                                <td align="center">
                                    <div style="
                                        background:#1e3a8a;
                                        color:white;
                                        padding:20px 40px;
                                        border-radius:10px;
                                        font-size:38px;
                                        letter-spacing:5px;
                                        font-weight:bold;
                                        text-align:center;
                                        display:inline-block;
                                        box-shadow:0 3px 10px rgba(0,0,0,0.15);
                                    ">
                                        {code}
                                    </div>
                                </td>
                            </tr>

                            <!-- Footer Info -->
                            <tr>
                                <td style="padding-top:30px; text-align:center;">
                                    <p style="color:#777; font-size:13px; margin:0;">
                                        This code expires in 10 minutes.
                                    </p>
                                    <p style="color:#a1a1a1; font-size:12px; margin-top:12px;">
                                        © 2024 DR Detection System • Medical AI Screening  
                                    </p>
                                </td>
                            </tr>

                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

    def send_otp_email(self, recipient_email, otp, username=None):
        """Send OTP email using a professional template"""
        try:
            if username:
                message = f"Hello <strong>{username}</strong>, your OTP for authentication is shown below."
            else:
                message = "Your verification OTP is shown below."

            html_content = self.email_template(
                title="Your OTP Code",
                message=message,
                code=otp
            )

            email = sib_api_v3_sdk.SendSmtpEmail(
                sender={"email": self.sender_email, "name": "DR Detection System"},
                to=[{"email": recipient_email}],
                subject="Your OTP for DR Detection System",
                html_content=html_content
            )

            self.email_api.send_transac_email(email)
            return True

        except ApiException as e:
            print(f"Error sending OTP email: {e}")
            return False

    def send_password_reset_email(self, recipient_email, reset_code, username=None):
        """Send password reset email using a professional template"""
        try:
            if username:
                message = f"Hello <strong>{username}</strong>, use the reset code below to reset your password."
            else:
                message = "Use the reset code below to proceed with password reset."

            html_content = self.email_template(
                title="Password Reset Code",
                message=message,
                code=reset_code
            )

            email = sib_api_v3_sdk.SendSmtpEmail(
                sender={"email": self.sender_email, "name": "DR Detection System"},
                to=[{"email": recipient_email}],
                subject="Password Reset Code for DR Detection System",
                html_content=html_content
            )

            self.email_api.send_transac_email(email)
            return True

        except ApiException as e:
            print(f"Error sending password reset email: {e}")
            return False
