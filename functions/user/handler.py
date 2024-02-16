import json
import uuid
from datetime import datetime

from loguru import logger

# Lambda layer
from db.database import Database
from db.tables import Users
from user.user_details import set_user_details, get_user_details
from utils.custom_exceptions import UserNotFoundError, RaiseCustomException
from utils.util import json_return


def handler(event, _):
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            request_method = event["requestContext"]["http"]["method"]

            logger.info(f"username: {username} request method: {request_method}")
            if not username:
                raise UserNotFoundError(username)

            db_user = session.query(Users).filter(Users.username == username).first()
            if not db_user:
                raise UserNotFoundError(username)

            user_id = db_user.id
            user_created_at = db_user.created_at

            if request_method == "GET":
                user_data = get_user_details(session, username)

                user_details_dict = dict()
                logger.info("User details dict: " + str(user_details_dict))
                user_details_dict["user_id"] = user_id
                user_details_dict["username"] = username
                user_details_dict["no_of_attributes"] = len(user_data.keys())
                user_details_dict["created_at"] = user_created_at.isoformat()
                user_details_dict["timestamp"] = datetime.utcnow().isoformat()
                user_details_dict["user_data"] = user_data

                status_code, msg = 200, {
                    "status": "success",
                    "message": "Fetched user information",
                    "details": user_details_dict,
                }
            elif request_method == "POST":
                body_plain = event.get("body", None)
                body = json.loads(body_plain)
                logger.info(f"body: {body}")
                created_attributes, updated_attributes = set_user_details(session, user_id, body)
                status_code, msg = 200, {
                    "status": "success",
                    "message": "Updated user information",
                    "details": {
                        "created_attributes": created_attributes,
                        "updated_attributes": updated_attributes,
                    },
                }

        except (UserNotFoundError, RaiseCustomException) as e:
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except Exception as exception:
            logger.exception(exception)
            error_id = uuid.uuid4()
            logger.error(f"an error occurred, id: {error_id} error: {exception}")
            json_return(500, f"{exception}")
        else:
            session.commit()
            return json_return(status_code, msg)
