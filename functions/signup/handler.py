import json
import os
import uuid
from datetime import datetime

from loguru import logger
from passlib.context import CryptContext
from passlib.utils import generate_password

# Lambda layer
from db.database import Database
from db.users import Users

# Local
from emailer import Email
from mailer.sender import SMTPEmailer

verification_base_url = os.environ.get("verification_url")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
emaile = Email()


def handler(event, _):
    logger.info(event)
    try:
        database = Database()
        with database.get_session() as session:
            body = event.get("body", None)
            if body:
                body = json.loads(body)
                username = body.get("username", None)
                if username:
                    validated_username = emaile.check_email_validity(username)
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
                    else:
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
                        else:
                            password = body.get("password", None)
                            verification_token = generate_password(36)
                            user = Users(
                                id=str(uuid.uuid4()),
                                username=validated_username,
                                password=pwd_context.hash(password),
                                verification_token=verification_token,
                            )
                            session.add(user)
                            session.commit()
                            logger.info(f"user created: {validated_username}")
                            status_code, msg = 201, {
                                "status": "success",
                                "message": "user created",
                                "details": {
                                    "username": validated_username,
                                    "timestamp": datetime.utcnow().isoformat(),
                                },
                            }
                            # Send email
                            verification_url = f"{verification_base_url}/api/verify?vt={verification_token}"
                            send_mail = SMTPEmailer.send_verification_email(
                                to_address=validated_username, verification_url=verification_url
                            )
                            if send_mail:
                                logger.info(f"verification email sent to {validated_username}")
                            else:
                                logger.error(f"failed to send verification email to: {validated_username}")

        database.close_connection()
        return {
            "isBase64Encoded": False,
            "statusCode": status_code,
            "body": json.dumps(msg),
            "headers": {"content-type": "application/json"},
        }
    except Exception as exception:
        database.close_connection()
        error_id = uuid.uuid4()
        logger.error(f"an error occurred, id: {error_id} error: {exception}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": exception,
            "headers": {"content-type": "application/json"},
        }
