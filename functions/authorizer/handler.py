""" Commone lambda authorizer """
import base64

from jose import JWTError, jwt
from loguru import logger

from db.database import Database
from db.tables import Sessions

allowed_http_paths = [
    "/api/signup",
    "/api/verify",
    "/api/google-signin",
    "/api/signin",
    "/api/reset-email",
    "/api/reset-password",
    "/api/subscription-list",
]

secret_key = "74192c43d038bdc5d11a354d6c950ddb5d1fe6a2c21a122fbb10f3e2eeb49cd9"
algorithm = "HS256"


def handler(event, _):
    """authorizer lambda handler"""
    response = {"isAuthorized": False, "context": {"user": "unknown"}}

    # Ignore key authentication for login endpoints
    http_path = (
        event.get("requestContext", None).get("http", None).get("path", None).replace("/dev", "").replace("/prod", "")
    )
    if http_path and http_path in allowed_http_paths:
        response["isAuthorized"] = True
        return response

    # Decode Basic auth
    # Check auth type
    logger.info(event)
    auth_header = event.get("headers", "").get("authorization", "")
    logger.info(auth_header)

    if "Basic" in auth_header:
        # Basic auth handler
        token = auth_header.replace("Basic", "").strip()
        token = token.encode("ascii")
        decoded_token = base64.b64decode(token)
        decoded_token = decoded_token.decode("ascii")
        user_name = decoded_token.split(":")[0]
        password = decoded_token.split(":")[1]
        if user_name == "np@docudiveai.com" and password == "Docudive2023#":
            response["isAuthorized"] = True
            response["context"]["user"] = user_name
            return response

    elif "Bearer" in auth_header:
        # Google or self token
        token = auth_header.replace("Bearer", "").strip()
        token = token.encode("ascii")
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
            subject = payload.get("sub")
            session_id = payload.get("session")

            if subject is None:
                return response
            else:
                database = Database(echo=True)
                with database.get_session() as session:
                    session = session.query(Sessions).filter(Sessions.session == session_id).first()
                    if session:
                        response["isAuthorized"] = True
                        response["context"]["user"] = subject
                        response["context"]["session_id"] = session_id
                        return response
                    else:
                        return response

        except JWTError:
            return response
        except Exception as exception:
            logger.error(exception)
            return response

    return response
