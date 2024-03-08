from loguru import logger

from db.database import Database
from db.tables import Sessions
from utils.util import json_return


def handler(event, _):
    """authorizer lambda handler"""
    database = Database()
    with database.get_session() as session:
        try:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            session_id = event["requestContext"]["authorizer"]["lambda"]["session_id"]
            current_session = session.query(Sessions).filter(Sessions.session == session_id).first()
            if current_session:
                session.delete(current_session)
                logger.info(f"Session {session_id} deleted")
                status_code = 200
                message = {"status": "success", "message": "user sign-out success", "details": {"username": username}}

            else:
                status_code = 404
                message = {"status": "failed", "message": "user sign-out failed", "details": {"username": username}}
        except Exception as exception:
            status_code = 500
            message = {"status": "failed", "message": "user sign-out failed", "details": {"username": username}}
            logger.error(exception)
            return json_return(status_code, message)
        else:
            session.commit()
            return json_return(status_code, message)
