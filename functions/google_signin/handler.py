import json
import os
import uuid
from datetime import datetime, timedelta

from google.auth.transport import requests
from google.oauth2 import id_token
from loguru import logger
from passlib.context import CryptContext

# Lambda layer
from db.database import Database
from db.sessions import Sessions
from db.users import Users
from jwt.jwt_token import JWT

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
jwt = JWT()


def handler(event, _):
    """
    Reference - https://developers.google.com/identity/sign-in/web/backend-auth
    Verify Google token and generate JWT token
    """
    logger.info(event)
    database = Database()
    try:

        # Extract the token from the event payload
        body = json.loads(event["body"])
        token = body["token"]

        # Specify the CLIENT_ID of the app that accesses the backend
        client_id = os.getenv("CLIENT_ID", "<YOUR_CLIENT_ID_HERE>")
        logger.info(f"Client ID : {client_id}")
        # Verify the token
        google_id_info = id_token.verify_oauth2_token(token, requests.Request(), client_id)

        # Optional: if multiple clients access the backend server:
        # if idinfo['aud'] not in [CLIENT_ID_1, CLIENT_ID_2, CLIENT_ID_3]:
        #     raise ValueError('Could not verify audience.')

        # Optional: if auth request is from a G Suite domain:
        # GSUITE_DOMAIN_NAME = "YOUR_GSUITE_DOMAIN_NAME_HERE"
        # if idinfo['hd'] != GSUITE_DOMAIN_NAME:
        #     raise ValueError('Wrong hosted domain.')

        # ID token is valid, extract the user's Google Account ID
        username_google_id = google_id_info["sub"]
        email_verified = google_id_info.get("email_verified", False)
        username_email = google_id_info.get("email", None)
        user_icon = google_id_info.get("picture", None)

        logger.info(f"username_google_id: {username_google_id}")
        logger.info(f"email_verified: {email_verified}")
        logger.info(f"username_email: {username_email}")
        logger.info(f"user_icon: {user_icon}")

        if not username_email:
            status_code, msg = 400, {
                "status": "failed",
                "message": "Please grant email access to the app",
                "detail": {},
            }

            return {
                "isBase64Encoded": False,
                "statusCode": status_code,
                "body": json.dumps(msg),
                "headers": {"content-type": "application/json"},
            }

        with database.get_session() as session:
            user = session.query(Users).filter(Users.username == username_email).first()
            if not user:
                # create user if not exists
                user = Users(
                    id=str(uuid.uuid4()),
                    username=username_email,
                    password="",
                    verification_token="",
                )
                session.add(user)
                session.commit()

            if email_verified:
                session_id = str(uuid.uuid4())
                expire_at = datetime.utcnow() + timedelta(days=1)
                current_session = session.query(Sessions).filter(Sessions.user_id == user.id).first()
                if not current_session:
                    current_session = Sessions(
                        user_id=user.id, username=username_email, session=session_id, expire_at=expire_at
                    )
                    session.add(current_session)
                    session.commit()
                else:
                    current_session.session = session_id
                    current_session.expire_at = expire_at
                    session.commit()

                data = {"sub": username_email, "session": str(session_id)}
                token = jwt.create_access_token(data)
                status_code, msg = 201, {
                    "status": "success",
                    "message": "token generated",
                    "access_token": token,
                    "token_type": "bearer",
                    "refresh_token": "none",
                    "expires_in": expire_at.isoformat(),
                    "details": {
                        "user_alias": f"{username_email[:2].upper()}",  # first two letters of username
                        "username": username_email,
                        "icon": f"{user_icon if user_icon else os.getenv('DEFAULT_ICON', 'https://i.imgur.com/x2c5ou4.png')}",
                    },
                }
            else:
                status_code, msg = 403, {
                    "status": "failed",
                    "message": "Google email verification pending",
                    "detail": {},
                }
        return {
            "isBase64Encoded": False,
            "statusCode": status_code,
            "body": json.dumps(msg),
            "headers": {"content-type": "application/json"},
        }

    except ValueError:
        return {
            "isBase64Encoded": False,
            "statusCode": 400,
            "body": json.dumps(
                {
                    "status": "failed",
                    "message": "Invalid token",
                    "detail": {},
                }
            ),
            "headers": {"content-type": "application/json"},
        }
    except Exception as e:
        error_id = uuid.uuid4()
        logger.exception(f"an error occurred, id: {error_id}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": json.dumps(str(e)),
            "headers": {"content-type": "application/json"},
        }
    finally:
        database.close_connection()
