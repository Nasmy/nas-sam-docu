import json
import os
import uuid
from datetime import datetime, timedelta

from loguru import logger
from passlib.context import CryptContext

# Lambda layer
from db.database import Database
from db.sessions import Sessions
from db.users import Users
from jwt.jwt_token import JWT

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
jwt = JWT()


def handler(event, context):
    try:
        database = Database()
        with database.get_session() as session:
            body = event.get("body", None)
            if body:
                body = json.loads(body)
                username = body.get("username", None)
                password = body.get("password", None)
                if username and password:
                    user = session.query(Users).filter(Users.username == username).first()
                    if not user:
                        status_code, msg = 404, {
                            "status": "failed",
                            "message": "user does not exist",
                            "detail": {"username": username},
                        }
                    else:
                        password_check = pwd_context.verify(password, user.password)
                        if password_check:
                            if user.is_verified:
                                session_id = uuid.uuid4()
                                expire_at = datetime.utcnow() + timedelta(days=1)
                                current_session = session.query(Sessions).filter(Sessions.user_id == user.id).first()
                                if not current_session:
                                    current_session = Sessions(
                                        user_id=user.id, username=username, session=session_id, expire_at=expire_at
                                    )
                                    session.add(current_session)
                                    session.commit()
                                else:
                                    current_session.session = session_id
                                    current_session.expire_at = expire_at
                                    session.commit()

                                data = {"sub": username, "session": str(session_id)}
                                token = jwt.create_access_token(data)
                                status_code, msg = 201, {
                                    "status": "success",
                                    "message": "token generated",
                                    "access_token": token,
                                    "token_type": "bearer",
                                    "refresh_token": "none",
                                    "details": {
                                        "user_alias": f"{username[:2].upper()}",  # first two letters of username
                                        "username": username,
                                        "icon": f"{os.getenv('DEFAULT_ICON', 'https://i.imgur.com/x2c5ou4.png')}",
                                    },
                                }
                            else:
                                status_code, msg = 403, {
                                    "status": "failed",
                                    "message": "email verification pending",
                                    "detail": {},
                                }
                        else:
                            status_code, msg = 401, {
                                "status": "failed",
                                "message": "invalid username or password",
                                "detail": {"username": username},
                            }
                else:
                    status_code, msg = 401, {
                        "status": "failed",
                        "message": "invalid username or password",
                        "detail": {"username": username},
                    }
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
