import uuid
from datetime import datetime

from loguru import logger

from chat.chat_types import ChatTypes

# Lambda layer
from db.database import Database
from db.tables import Documents, Chats, Users, Annotations, AnnotationTypesTable
from utils.custom_exceptions import MissingQueryParameterError, UserNotFoundError, DocumentNotFoundError
from utils.util import json_return, get_query_parameter


def handler(event, _):
    database = Database()
    with database.get_session() as session:
        try:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            document_id = get_query_parameter(event, "document_id")
            logger.info(f"username: {username}")
            logger.info(f"document_id: {document_id}")
            logger.info(f"doc id type: {type(document_id)}")
            logger.info(f"Connection string: {database.get_database_connection_string()}")

            result = (
                session.query(Users.username, Users.id, Documents.id)
                .join(Documents, Documents.user_id == Users.id)
                .filter(Documents.id == str(document_id))
                .first()
            )
            logger.info(f"result: {result}")

            if not result:
                raise DocumentNotFoundError(document_id)

            db_username, db_user_id, db_document_id = result

            if username != db_username:
                raise UserNotFoundError(username)

            db_chats = (
                session.query(Chats.id, Chats.chat_name, Chats.created_at, Chats.chat_type)
                .filter(Chats.document_id == document_id)
                .filter(Chats.chat_type == ChatTypes.USER.value)
                .order_by(Chats.created_at.desc())
                .all()
            )
            docs_dict_list = []
            for chat_id, chat_name, created_at, chat_type in db_chats:
                docs_dict_list.append(
                    {
                        "chat_id": chat_id,
                        "chat_name": chat_name,
                        "created_at": created_at.isoformat(),
                    }
                )

            is_chat_ready = True
            if len(docs_dict_list) == 0:
                # SQL Alchemy query
                annotation_list = ['full_text', 'spans']
                completed_count = session.query(Annotations).join(
                    AnnotationTypesTable, AnnotationTypesTable.id == Annotations.annotation_type_id
                ).filter(
                    Annotations.document_id == document_id,
                    AnnotationTypesTable.is_enabled == True,
                    AnnotationTypesTable.name.in_(annotation_list),
                    Annotations.status == 'completed'
                ).count()

                logger.info(f"Completed count : {completed_count}/2")
                is_chat_ready = completed_count == len(annotation_list)

                logger.info(f"chat ready : {is_chat_ready}")

            status_code, msg = 200, {
                "status": "success",
                "message": "Fetched all chats",
                "details": {
                    "user_id": db_user_id,
                    "document_id": db_document_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "chat_ready": is_chat_ready,
                    "chat_list": docs_dict_list,
                },
            }

        except (MissingQueryParameterError, UserNotFoundError, DocumentNotFoundError) as e:
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except Exception as exception:
            error_id = uuid.uuid4()
            logger.exception(exception)
            logger.error(f"an error occurred, id: {error_id} error: {exception}")
            return {
                "isBase64Encoded": False,
                "statusCode": 500,
                "body": exception,
                "headers": {"content-type": "application/json"},
            }
        else:
            return json_return(status_code, msg)
