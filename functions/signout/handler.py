import json

from db.database import Database
from db.sessions import Sessions


def handler(event, _):
    """authorizer lambda handler"""
    username = event["requestContext"]["authorizer"]["lambda"]["user"]

    try:
        database = Database()
        with database.get_session() as session:
            current_session = session.query(Sessions).filter(Sessions.username == username).first()
            if current_session:
                session.delete(current_session)
                print("Session deleted")
                session.commit()
                return {
                    "isBase64Encoded": False,
                    "statusCode": 200,
                    "body": json.dumps(
                        {"status": "success", "message": "user signout success", "detail": {"username": username}}
                    ),
                    "headers": {"content-type": "application/json"},
                }
            else:
                return {
                    "isBase64Encoded": False,
                    "statusCode": 404,
                    "body": json.dumps(
                        {"status": "failed", "message": "user signout failed", "detail": {"username": username}}
                    ),
                    "headers": {"content-type": "application/json"},
                }
    except Exception as exception:
        print(exception)
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": json.dumps(
                {"status": "failed", "message": "user signout failed", "detail": {"username": username}}
            ),
            "headers": {"content-type": "application/json"},
        }
