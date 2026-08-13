import os
import time
import smtplib
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Dict, Any, List, Optional, Callable

LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outreach_log.csv")

class EmailSender:
    """SMTP Email Sender with attachment support, delay timers, and logging."""

    def __init__(self, smtp_server: str = "smtp.gmail.com", port: int = 587, sender_email: str = "Irtazakhalidll@gmail.com", sender_password: str = ""):
        self.smtp_server = smtp_server
        self.port = port
        self.sender_email = sender_email
        self.sender_password = sender_password.replace(" ", "").strip()

    def test_connection(self) -> Dict[str, Any]:
        """Test SMTP server connection and login credentials."""
        try:
            with smtplib.SMTP(self.smtp_server, self.port, timeout=10) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                return {"success": True, "message": "SMTP Connection Successful! Ready to send emails."}
        except smtplib.SMTPAuthenticationError as e:
            err_msg = str(e)
            if "5.7.9" in err_msg or "Application-specific password required" in err_msg:
                return {
                    "success": False,
                    "message": "🔒 Gmail App Password Required!\n\nYou entered your standard Gmail account password. Google requires a 16-character 'App Password' for SMTP apps.\n\n👉 How to fix in 1 minute:\n1. Go to https://myaccount.google.com/security\n2. Enable 2-Step Verification\n3. Search for 'App Passwords' -> Create a new App Password\n4. Paste the 16-character code into the password box."
                }
            return {"success": False, "message": f"SMTP Authentication Failed: {err_msg}"}
        except Exception as e:
            return {"success": False, "message": f"SMTP Connection Failed: {str(e)}"}

    def send_single_email(self, to_email: str, subject: str, body: str, cv_attachment_path: Optional[str] = None) -> Dict[str, Any]:
        """Send a single email via SMTP with optional CV attachment."""
        if not to_email or "@" not in to_email:
            return {"success": False, "message": "Invalid recipient email address."}

        try:
            msg = MIMEMultipart()
            msg["From"] = f"Irtaza Khalid <{self.sender_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            # Attach Body Text
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Attach CV PDF if provided
            if cv_attachment_path and os.path.exists(cv_attachment_path):
                filename = os.path.basename(cv_attachment_path)
                with open(cv_attachment_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=filename)
                    part["Content-Disposition"] = f'attachment; filename="{filename}"'
                    msg.attach(part)

            # Send via SMTP
            with smtplib.SMTP(self.smtp_server, self.port, timeout=15) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            # Log dispatch
            self._log_sent_mail(to_email, subject, "Success")
            return {"success": True, "message": f"Email sent successfully to {to_email}!"}

        except Exception as e:
            self._log_sent_mail(to_email, subject, f"Failed: {str(e)}")
            return {"success": False, "message": f"Failed to send email to {to_email}: {str(e)}"}

    def send_campaign(self, items: List[Dict[str, str]], delay_seconds: float = 30.0, cv_attachment_path: Optional[str] = None, progress_callback: Optional[Callable[[int, int, str, bool], None]] = None) -> List[Dict[str, Any]]:
        """Send batch email campaign with rate limiting delays."""
        results = []
        total = len(items)

        for i, item in enumerate(items, 1):
            to_email = item.get("to_email", "").strip()
            subject = item.get("subject", "")
            body = item.get("body", "")

            if not to_email:
                continue

            res = self.send_single_email(to_email, subject, body, cv_attachment_path)
            results.append({"to": to_email, "status": res["success"], "message": res["message"]})

            if progress_callback:
                progress_callback(i, total, to_email, res["success"])

            # Delay between emails unless it's the last email
            if i < total and delay_seconds > 0:
                time.sleep(delay_seconds)

        return results

    def _log_sent_mail(self, to_email: str, subject: str, status: str):
        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sender": self.sender_email,
            "recipient": to_email,
            "subject": subject,
            "status": status
        }
        df = pd.DataFrame([record])
        if os.path.exists(LOG_FILE_PATH):
            df.to_csv(LOG_FILE_PATH, mode='a', header=False, index=False)
        else:
            df.to_csv(LOG_FILE_PATH, index=False)

    @staticmethod
    def get_logs() -> pd.DataFrame:
        if os.path.exists(LOG_FILE_PATH):
            try:
                return pd.read_csv(LOG_FILE_PATH)
            except Exception:
                pass
        return pd.DataFrame(columns=["timestamp", "sender", "recipient", "subject", "status"])
