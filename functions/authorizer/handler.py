""" Commone lambda authorizer """
import base64
import contextlib
import os

from jose import JWTError, jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.sessions import Sessions

allowed_http_paths = ["/api/signup", "/api/token", "/api/verify", "/api/google_signin"]

secret_key = "74192c43d038bdc5d11a354d6c950ddb5d1fe6a2c21a122fbb10f3e2eeb49cd9"
algorithm = "HS256"


@contextlib.contextmanager
def get_session():
    """Create a session from db connection"""
    endpoint = os.environ.get("database_endpoint")
    port = os.environ.get("database_port")
    username = os.environ.get("database_username")
    password = os.environ.get("database_password")
    database = os.environ.get("database_name")

    db_url = f"postgresql+pg8000://{username}:{password}@{endpoint}:{port}/{database}"
    print(db_url)
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


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
    print(event)
    auth_header = event.get("headers", "").get("authorization", "")
    print(auth_header)

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

            if subject is None:
                return response
            else:
                # Check if token is in blacklist
                with get_session() as session:
                    session = session.query(Sessions).filter(Sessions.username == subject).first()
                    if session:
                        response["isAuthorized"] = True
                        response["context"]["user"] = subject
                        return response
                    else:
                        return response

        except (JWTError, Exception):
            return response

    return response
