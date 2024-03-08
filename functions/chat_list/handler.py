import json
import uuid
from datetime import datetime

from loguru import logger

# Lambda layer
from db.database import Database
from db.document_chat import DocumentChat
from db.documents import Documents
from db.users import Users
from utils.util import object_as_dict


def handler(event, _):
    try:
        database = Database()
        with database.get_session() as session:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            if username:
                user = session.query(Users).filter(Users.username == username).first()
                if user:
                    document_id = event["queryStringParameters"]["document_id"]

                    doc = (
                        session.query(Documents)
                        .filter(Documents.user_id == user.id, Documents.document_id == document_id)
                        .first()
                    )
                    if doc:
                        chats = (
                            session.query(DocumentChat)
                            .filter(DocumentChat.document_id == document_id)
                            .order_by(DocumentChat.created_at.desc())
                            .all()
                        )
                        docs_dict_list = object_as_dict(chats)
                        keys_to_delete = ["id", "document_id"]
                        # remove keys from dict list
                        for chat in docs_dict_list:
                            for key in keys_to_delete:
                                chat.pop(key, None)

                        status_code, msg = 200, {
                            "status": "success",
                            "message": "Fetched all chats",
                            "details": {
                                "user_id": user.id,
                                "document_id": document_id,
                                "timestamp": datetime.utcnow().isoformat(),
                                "chat_list": docs_dict_list,
                            },
                        }
                    else:
                        logger.error(f"unknown document: {document_id}")
                        status_code, msg = 404, {"status": "failed", "message": "unknown doc", "details": {}}
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
        logger.exception(exception)
        logger.error(f"an error occured, id: {error_id} error: {exception}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": exception,
            "headers": {"content-type": "application/json"},
        }
