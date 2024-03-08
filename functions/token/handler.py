import os
import uuid
from datetime import datetime, timedelta

from loguru import logger
from passlib.context import CryptContext

from aws.aws_eb import EBWrapper, CustomEventSources, CustomEventDetailTypes

# Lambda layer
from db.database import Database
from db.tables import Users, Sessions, UserAttributes, UserDetails
from jwt.jwt_token import JWT
from utils.custom_exceptions import MissingBodyParameter, UserNotFoundError, RaiseCustomException
from utils.util import json_return, get_body_parameter

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
jwt = JWT()
event_bus = EBWrapper()


def handler(event, _):
    database = Database()
    with database.get_session() as session:
        try:
            body = event.get("body", None)
            username = get_body_parameter(body, "username")
            password = get_body_parameter(body, "password")

            user = session.query(Users).filter(Users.username == username).first()
            if not user:
                raise UserNotFoundError(username)
            else:
                result = (
                    session.query(UserDetails.value)
                    .join(UserAttributes, UserAttributes.id == UserDetails.user_attribute_id)
                    .filter(UserAttributes.attribute_name == "image_url", UserDetails.user_id == user.id)
                    .first()
                )
                icon_url = result[0] if result else None
                logger.info(f"icon_url: {icon_url}")

            if user.is_google:
                error_message = "This user is registered/signed-in with Google. Please use Google Sign In"
                details = {"username": username}
                raise RaiseCustomException(401, error_message, details)

            password_check = pwd_context.verify(password, user.password)
            if not password_check:
                error_message = "invalid username or password"
                details = {"username": username}
                raise RaiseCustomException(401, error_message, details)

            if not user.is_verified:
                error_message = "email verification pending"
                details = {"username": username}
                raise RaiseCustomException(403, error_message, details)

            session_id = str(uuid.uuid4())
            expire_at = datetime.utcnow() + timedelta(days=1)
            current_session = session.query(Sessions).filter(Sessions.user_id == user.id).first()
            if not current_session:
                current_session = Sessions(user_id=user.id, session=session_id, expire_at=expire_at)
                session.add(current_session)
            else:
                current_session.session = session_id
                current_session.expire_at = expire_at

            data = {"sub": username, "session": session_id}
            token = jwt.create_access_token(data)
            status_code, msg = 201, {
                "status": "success",
                "message": "token generated",
                "details": {
                    "access_token": token,
                    "token_type": "bearer",
                    "refresh_token": "none",
                    "expires_in": expire_at.isoformat(),
                    "user_alias": f"{username[:2].upper()}",  # first two letters of username
                    "username": username,
                    "icon": icon_url,
                },
            }

            try:
                event_bus.send_event(
                    source=CustomEventSources.SIGNIN,
                    detail_type=CustomEventDetailTypes.SUCCESS,
                    detail={"username": username},
                )
            except Exception as exception:
                logger.error(f"Failed to send event, error: {exception}")

        except (MissingBodyParameter, UserNotFoundError, RaiseCustomException) as e:
            session.rollback()
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except Exception as exception:
            error_id = uuid.uuid4()
            logger.error(f"an error occured, id: {error_id} error: {exception}")
            return {
                "isBase64Encoded": False,
                "statusCode": 500,
                "body": exception,
                "headers": {"content-type": "application/json"},
            }
        else:
            session.commit()
            return json_return(status_code, msg)
