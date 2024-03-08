import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from loguru import logger

from mailer.templates import EmailVerificationTemplate

smtp_server = os.environ.get("smtp_server")
smtp_port = os.environ.get("smtp_port")
smtp_username = os.environ.get("smtp_username")
smtp_password = os.environ.get("smtp_password")


# Usage example:
# formatted_email = VERIFICATION_EMAIL_HTML.format("https://your_verification_link_here.com")


class SMTPEmailer:
    """
    Emailer interface
    """

    def __init__(self):
        return

    @staticmethod
    def send_verification_email(to_address: str, verification_url: str, email_type_cls, format="html"):
        """
        Sends the verification email
        """
        try:
            from_address = "no-reply@docudiveai.com"

            msg = MIMEMultipart("alternative")
            msg["From"] = from_address
            msg["To"] = to_address
            msg["Subject"] = email_type_cls.SUBJECT

            # Plaintext and html version of the email
            if format == "html":
                text = email_type_cls.VERIFICATION_EMAIL_HTML.format(verification_url)
                part1 = MIMEText(text, "html")
            else:
                text = email_type_cls.VERIFICATION_EMAIL_PLAINTEXT.format(verification_url)
                part1 = MIMEText(text, "plain")

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





def test():
    try:
        validated_username = "docudive1@yopmail.com"
        verification_url = "https://docudive.vercel.app/"
        text = EmailVerificationTemplate.VERIFICATION_EMAIL_HTML.format(verification_url)

        print(text)
        send_mail = SMTPEmailer.send_verification_email(
            to_address=validated_username, verification_url="https://docudive.vercel.app/", email_type_cls=EmailVerificationTemplate
        )
        if send_mail:
            logger.info(f"verification email sent to {validated_username}")

    except Exception as exception:
        logger.error(f"Failed to send email {exception}")


if __name__ == "__main__":
    test()
