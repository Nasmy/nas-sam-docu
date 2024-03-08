import json
import uuid
from datetime import datetime

from loguru import logger

# Lambda layer
from db.database import Database
from db.tables import Users
from utils.custom_exceptions import MissingQueryParameterError, RaiseCustomException
from utils.util import json_return, get_query_parameter


def handler(event, _):
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            verification_token = get_query_parameter(event, "vt")
            action = event["queryStringParameters"].get("action", None)
            logger.info(f"verification token: {verification_token}")

            user = session.query(Users).filter(Users.verification_token == verification_token).first()
            if not user:
                logger.error(f"email verification failed for token: {verification_token}")
                error_message = "invalid or expired verification link"
                raise RaiseCustomException(404, error_message)

            user.is_verified = True
            user.verification_token = None
            logger.info(f"email verified for user: {user.username}")

            if action == "redirect":
                response = {
                    "isBase64Encoded": False,
                    "statusCode": 302,
                    "body": json.dumps({"message": "Redirecting..."}),
                    "headers": {"Location": "https://docudive.vercel.app/"},
                }
            else:
                status_code, msg = 200, {
                    "status": "success",
                    "message": "email verified",
                    "details": {
                        "username": user.username,
                        "user_created_at": user.created_at.isoformat(),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
                response = json_return(status_code, msg)

        except (MissingQueryParameterError, RaiseCustomException) as e:
            return json_return(
                e.status_code,
                {
                    "status": "failed",
                    "message": e.message,
                    "details": e.details,
                },
            )
        except Exception as exception:
            error_id = uuid.uuid4()
            logger.error(f"an error occurred, id: {error_id} error: {exception}")
            json_return(500, f"{exception}")
        else:
            session.commit()
            return response
