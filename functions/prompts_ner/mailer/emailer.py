import json
from loguru import logger

from email_validator import validate_email, EmailNotValidError

from mailer.email_list import EMAIL_LIST


class Email():
    """ Email related functions """
    def __init__(self):
        self.email_list = EMAIL_LIST

    def check_email_validity(self, email):
        """ Checks the email """
        try:
            email_object = validate_email(email, check_deliverability=True)
            email = email_object.normalized
            domain = email.split('@')[1]
            if self.email_list.get(domain, True):
                logger.info("email address is valid")
                return email
            logger.error("email address is invalid")
            return False
        except EmailNotValidError as error:
            print(f"email {email} is invalid, error {error}")
            return False

    def send_verification_email(self):
        """ Send verification email """
        return
