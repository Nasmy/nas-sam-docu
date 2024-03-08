import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from loguru import logger


smtp_server = os.environ.get('smtp_server')
smtp_port = os.environ.get('smtp_port')
smtp_username = os.environ.get('smtp_username')
smtp_password = os.environ.get('smtp_password')

VERIFICATION_EMAIL_PLAINTEXT = """
    Thanks for registering with docudiveai.com.
    To verify your email, please copy the following link and paste in a new browser tab.
    {0}
    """

class SMTPEmailer:
    """
    Emailer interface
    """

    def __init__(self):
        return

    @staticmethod
    def send_verification_email(to_address: str, verification_url: str):
        """
        Sends the verification email
        """
        try:
            from_address = "no-reply@docudiveai.com"

            msg = MIMEMultipart("alternative")
            msg["From"] = from_address
            msg["To"] = to_address
            msg["Subject"] = "Verify your email on docudiveai"

            # Plaintext and html version of the email
            text = VERIFICATION_EMAIL_PLAINTEXT.format(verification_url)
            # html = EmailTemplates.VERIFICATION_EMAIL_HTML.format(verification_url)

            # Updated email format
            # html = EmailTemplates.VERIFICATION_EMAIL_HTML_V2.format(verification_url)

            # Turn these into plain/html MIMEText objects
            part1 = MIMEText(text, "plain")
            # part2 = MIMEText(html, "html")

            # The email client will try to render the last part first
            msg.attach(part1)
            # msg.attach(part2)

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            text = msg.as_string()

            server.sendmail(from_address, to_address, text)
            server.quit()

            return True

        except Exception as exception:
            logger.error(f"Failed to send email {exception}")

        return False
