import uuid
import json

from loguru import logger

# Lambda layer
from db.database import Database
from db.users import Users


def handler(event, context):
    try:
        database = Database()
        with database.get_session() as session:
            verification_token = event["queryStringParameters"]["vt"]
            if verification_token:
                user = session.query(Users).filter(Users.verification_token==verification_token).first()
                if user:
                    user.is_verified = True
                    user.verification_token = None
                    session.commit()
                    logger.info(f"email verified for user: {user.username}")
                    status_code, msg = 200, {"status": "success", "message": "email verified", "detail": {}}
                else:
                    logger.error(f"email verification failed for token: {verification_token}")
                    status_code, msg = 404, {"status": "failed", "message": "invalid or expired verification link", "detail": {}}
            else:
                logger.error("invalid url, query parameter missing")
                status_code, msg = 404, {"status": "failed", "message": "invalid verification link", "detail": {}}
        database.close_connection()
        return {
            "isBase64Encoded": False,
            "statusCode": status_code,
            "body": json.dumps(msg),
            "headers": {
                "content-type": "application/json"
            }
        }
    except Exception as exception:
        database.close_connection()
        error_id = uuid.uuid4()
        logger.error(f"an error occured, id: {error_id} error: {exception}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": exception,
            "headers": {
                "content-type": "application/json"
            }
        }
