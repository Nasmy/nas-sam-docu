import json
import os
import uuid
from datetime import datetime

from loguru import logger
from passlib.context import CryptContext
from passlib.utils import generate_password

# Lambda layer
from db.database import Database
from db.tables import Users

# Local
from mailer.emailer import Email
from mailer.sender import SMTPEmailer
from mailer.templates import EmailVerificationTemplate
from utils.custom_exceptions import MissingBodyParameter, EmailSendError
from utils.util import json_return, get_body_parameter, get_host_url

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
emaile = Email()


def handler(event, _):
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            body = event.get("body", None)
            body = json.loads(body)
            username = get_body_parameter(body, "username")
            host_url = get_host_url(event)
            logger.info(f"host_url: {host_url}")

            logger.info(f"username: {username}")
            validated_username = username  # emaile.check_email_validity(username)
            if not validated_username:
                logger.error(f"email address is invalid: {username}")
                status_code, msg = 400, {
                    "status": "failed",
                    "message": "email validation failed",
                    "details": {
                        "username": username,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
                return json_return(status_code, msg)

            user = session.query(Users).filter(Users.username == validated_username).first()
            if user:
                logger.info(f"user already exists: {validated_username}")
                status_code, msg = 200, {
                    "status": "success",
                    "message": "user already exists",
                    "details": {
                        "username": validated_username,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
                return json_return(status_code, msg)

            password = body.get("password", None)
            verification_token = generate_password(36)
            user = Users(
                id=str(uuid.uuid4()),
                username=validated_username,
                password=pwd_context.hash(password),
                verification_token=verification_token,
            )
            session.add(user)
            logger.info(f"user created: {validated_username}")

            # Send email
            verification_url = f"{host_url}/verify?vt={verification_token}"
            send_mail = SMTPEmailer.send_verification_email(
                to_address=validated_username,
                verification_url=verification_url,
                email_type_cls=EmailVerificationTemplate,
            )
            if not send_mail:
                raise EmailSendError(validated_username)
            logger.info(f"verification email sent to {validated_username}")

            status_code, msg = 201, {
                "status": "success",
                "message": "user created",
                "details": {
                    "username": validated_username,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }

        except (MissingBodyParameter, EmailSendError) as e:
            session.rollback()
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except Exception as exception:
            session.rollback()
            database.close_connection()
            error_id = uuid.uuid4()
            logger.error(f"an error occurred, id: {error_id} error: {exception}")
            return {
                "isBase64Encoded": False,
                "statusCode": 500,
                "body": exception,
                "headers": {"content-type": "application/json"},
            }
        else:
            session.commit()
            return json_return(status_code, msg)
