import json
import uuid
from datetime import datetime

from loguru import logger

from db.chat_cost import ChatCost
# Lambda layer
from db.database import Database
from db.documents import Documents
from db.users import Users


def handler(event, _):
    try:
        database = Database()
        with database.get_session() as session:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            if username:
                user = session.query(Users).filter(Users.username == username).first()
                if user:
                    chat_costs = session.query(ChatCost).filter(ChatCost.user_id == user.id).all()
                    total_cost = 0
                    total_prompt_tokens = 0
                    total_completion_tokens = 0
                    for chat in chat_costs:
                        total_cost += chat.total_amount
                        total_prompt_tokens += chat.prompt_tokens
                        total_completion_tokens += chat.completion_tokens

                    all_docs = session.query(Documents).filter(Documents.user_id == user.id).all()
                    total_documents = len(all_docs)
                    total_pages = 0
                    doc_type_counts = {}
                    for doc in all_docs:
                        total_pages += doc.page_count
                        if doc.document_type in doc_type_counts:
                            doc_type_counts[doc.document_type] += 1
                        else:
                            doc_type_counts[doc.document_type] = 1

                    status_code, msg = 200, {
                        "status": "success",
                        "message": "Fetched usage information",
                        "details": {
                            "chat": {
                                "total_chat_cost": total_cost,
                                "total_prompt_tokens": total_prompt_tokens,
                                "total_completion_tokens": total_completion_tokens,
                            },
                            "document": {
                                "total_documents": total_documents,
                                "total_pages": total_pages,
                                "document_type_counts": doc_type_counts,
                            },
                            "timestamp": datetime.utcnow().isoformat(),
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
