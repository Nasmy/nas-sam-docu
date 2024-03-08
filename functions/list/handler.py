import json
import uuid
from datetime import datetime

from loguru import logger

# Lambda layer
from db.database import Database
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
                    # order by updated_at desc
                    docs = (
                        session.query(Documents)
                        .filter(Documents.user_id == user.id)
                        .order_by(Documents.uploaded_at.desc())
                        .all()
                    )
                    docs_dict_list = object_as_dict(docs)
                    keys_to_delete = ["user_id", "updated_at", "id", "is_deleted"]
                    # remove keys from dict list
                    for doc in docs_dict_list:
                        for key in keys_to_delete:
                            doc.pop(key, None)

                    status_code, msg = 200, {
                        "status": "success",
                        "message": "Fetched all documents",
                        "details": {
                            "user_id": user.id,
                            "timestamp": datetime.utcnow().isoformat(),
                            "document_list": docs_dict_list,
                        },
                    }
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
        logger.error(f"an error occured, id: {error_id} error: {exception}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": exception,
            "headers": {"content-type": "application/json"},
        }
