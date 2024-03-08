import json
import uuid
from datetime import datetime

from loguru import logger

# Lambda layer
from db.database import Database
from db.users import Users


def handler(event, _):
    try:
        database = Database()
        with database.get_session() as session:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            if username:
                user = session.query(Users).filter(Users.username == username).first()
                if user:
                    status_code, msg = 200, {
                        "status": "success",
                        "message": "Fetched user information",
                        "details": {
                            "user_id": user.id,
                            "username": user.username,
                            "created_at": user.created_at.isoformat(),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    }
                else:
                    logger.error(f"unknown user: {username}")
                    status_code, msg = 404, {"status": "failed", "message": "unknown user", "details": {}}
            else:
                logger.error(f"unknown user: {username}")
                status_code, msg = 404, {"status": "failed", "message": "unknown user", "details": {}}

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
        logger.error(f"an error occured, id: {error_id} error: {exception}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": exception,
            "headers": {"content-type": "application/json"},
        }
