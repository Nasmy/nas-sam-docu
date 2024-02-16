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
from mailer.templates import EmailResetTemplate
from utils.custom_exceptions import MissingBodyParameter, EmailSendError, RaiseCustomException
from utils.util import json_return, get_body_parameter, get_http_path, get_host_url

verification_base_url = os.environ.get("verification_url")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
emaile = Email()


def handler(event, _):
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            body = event.get("body", None)
            body = json.loads(body)
            http_path = get_http_path(event)

            if http_path == "/api/reset-email":
                host_url = get_host_url(event)
                logger.info(f"host_url: {host_url}")
                username = get_body_parameter(body, "username")

                logger.info(f"username: {username}")
                user = session.query(Users).filter(Users.username == username).first()
                if not user:
                    logger.info(f"user not exists: {username}")
                    status_code, msg = 200, {
                        "status": "success",
                        "message": "user already exists",
                        "details": {
                            "username": username,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    }
                    return json_return(status_code, msg)

                if not user.is_verified:
                    logger.info(f"user not verified: {username}")
                    status_code, msg = 200, {
                        "status": "success",
                        "message": "user not verified",
                        "details": {
                            "username": username,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    }
                    return json_return(status_code, msg)

                verification_token = generate_password(36)
                user.verification_token = verification_token
                user.is_reset = True
                logger.info(f"sending email to {username}")

                # Send email
                verification_url = f"{host_url}/reset?user={username}&vt={verification_token}"
                send_mail = SMTPEmailer.send_verification_email(
                    to_address=username, verification_url=verification_url, email_type_cls=EmailResetTemplate
                )
                if not send_mail:
                    raise EmailSendError(username)
                logger.info(f"Password reset email sent to {username}")

                status_code, msg = 201, {
                    "status": "success",
                    "message": "Reset email sent",
                    "details": {
                        "username": username,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
            elif http_path == "/api/reset-password":
                verification_token = get_body_parameter(body, "vt")
                password = get_body_parameter(body, "password")

                logger.info(f"verification token: {verification_token}")

                user = (
                    session.query(Users)
                    .filter(Users.verification_token == verification_token, Users.is_reset == True)
                    .first()
                )
                if not user:
                    logger.error(f"password reset failed for token: {verification_token}")
                    error_message = "invalid or expired verification link"
                    raise RaiseCustomException(404, error_message)

                user.password = pwd_context.hash(password)
                user.verification_token = None
                user.is_reset = False

                logger.info(f"password reset for user: {user.username}")
                status_code, msg = 201, {
                    "status": "success",
                    "message": "Password reset successful",
                    "details": {
                        "username": user.username,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
            else:
                raise RaiseCustomException(400, f"invalid http path - {http_path}")

        except (MissingBodyParameter, EmailSendError, RaiseCustomException) as e:
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
