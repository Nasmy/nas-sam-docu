import json
import os
import uuid
from datetime import datetime, timedelta

from google.auth.transport import requests
from google.oauth2 import id_token
from loguru import logger
from passlib.context import CryptContext

from aws.aws_eb import EBWrapper, CustomEventSources, CustomEventDetailTypes
# Lambda layer
from db.database import Database
from db.tables import Users, Sessions, UserDetails, UserAttributes
from jwt.jwt_token import JWT
from user.user_details import set_user_details
from utils.util import json_return

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
jwt = JWT()
event_bus = EBWrapper()

def handler(event, _):
    """
    Reference - https://developers.google.com/identity/sign-in/web/backend-auth
    Verify Google token and generate JWT token
    """
    logger.info(event)
    database = Database()
    with database.get_session() as session:
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
            g_user_icon = google_id_info.get("picture", None)

            logger.info(f"username_google_id: {username_google_id}")
            logger.info(f"email_verified: {email_verified}")
            logger.info(f"username_email: {username_email}")
            logger.info(f"user_icon: {g_user_icon}")

            if not username_email:
                status_code, msg = 400, {
                    "status": "failed",
                    "message": "Please grant email access to the app",
                    "details": {},
                }

                return json_return(status_code, msg)

            user = session.query(Users).filter(Users.username == username_email).first()
            if not user:
                # create user if not exists
                user = Users(
                    id=str(uuid.uuid4()),
                    username=username_email,
                    password="",
                    verification_token="",
                    is_google=True,
                )
                session.add(user)
                session.commit()
                user_icon = g_user_icon
            else:
                result = (
                    session.query(UserDetails.value)
                    .join(UserAttributes, UserAttributes.id == UserDetails.user_attribute_id)
                    .filter(UserAttributes.attribute_name == 'image_url', UserDetails.user_id == user.id)
                    .first()
                )
                if result is None or not result[0]:
                    if g_user_icon:
                        image_date = {"image_url": g_user_icon}
                        created_attributes, updated_attributes = set_user_details(session, user.id, image_date)
                        logger.info(f"created_attributes: {created_attributes}")
                        logger.info(f"updated_attributes: {updated_attributes}")
                    user_icon = g_user_icon
                else:
                    dd_user_icon = result[0] if result else None
                    logger.info(f"icon_url: {dd_user_icon}")
                    user_icon = dd_user_icon or g_user_icon

            if not user.is_google:
                user.is_google = True
                session.commit()

            if not email_verified:
                status_code, msg = 403, {
                    "status": "failed",
                    "message": "Google email verification pending",
                    "details": {},
                }
                return json_return(status_code, msg)

            session_id = str(uuid.uuid4())
            expire_at = datetime.utcnow() + timedelta(days=1)
            current_session = session.query(Sessions).filter(Sessions.user_id == user.id).first()
            if not current_session:
                current_session = Sessions(user_id=user.id, session=session_id, expire_at=expire_at)
                session.add(current_session)
            else:
                current_session.session = session_id
                current_session.expire_at = expire_at

            data = {"sub": username_email, "session": str(session_id)}
            token = jwt.create_access_token(data)
            status_code, msg = 201, {
                "status": "success",
                "message": "token generated",
                "details": {
                    "access_token": token,
                    "token_type": "bearer",
                    "refresh_token": "none",
                    "expires_in": expire_at.isoformat(),
                    "user_alias": f"{username_email[:2].upper()}",  # first two letters of username
                    "username": username_email,
                    "icon": user_icon
                },
            }

            # Sent event to usage trigger function
            try:
                event_bus.send_event(
                    source=CustomEventSources.SIGNIN,
                    detail_type=CustomEventDetailTypes.SUCCESS,
                    detail={"username": username_email},
                )
            except Exception as exception:
                logger.error(f"Failed to send event, error: {exception}")

        except ValueError:
            msg = {
                "status": "failed",
                "message": "Invalid token",
                "details": {},
            }
            return json_return(400, msg)
        except Exception as e:
            error_id = uuid.uuid4()
            logger.exception(f"an error occurred, id: {error_id}")
            return {
                "isBase64Encoded": False,
                "statusCode": 500,
                "body": json.dumps(str(e)),
                "headers": {"content-type": "application/json"},
            }
        else:
            session.commit()
            return json_return(status_code, msg)
