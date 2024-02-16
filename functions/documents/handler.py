import json
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger

# Lambda layer
from db.database import Database
from db.tables import Users, Documents, DocumentTypesTable
from utils.custom_exceptions import (
    MissingQueryParameterError,
    UserNotFoundError,
    DocumentNotFoundError,
    RaiseCustomException,
    MissingBodyParameter,
)
from utils.util import json_return, get_query_parameter, get_body_parameter


def handler(event, _):
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            request_method = event["requestContext"]["http"]["method"]
            logger.info(f"username: {username} request method: {request_method}")

            if not username:
                raise UserNotFoundError(username)

            user = session.query(Users).filter(Users.username == username).first()
            if not user:
                raise UserNotFoundError(username)

            if request_method == "GET":
                """Get all documents for a user"""
                logger.info(f"getting all documents for the user: {username}")
                doc_list = (
                    session.query(
                        Documents.id,
                        Documents.file_extension,
                        Documents.file_alias,
                        DocumentTypesTable.mime_type,
                        Documents.is_opened,
                        Documents.is_uploaded,
                        Documents.page_count,
                        Documents.uploaded_at,
                    )
                    .join(DocumentTypesTable, DocumentTypesTable.id == Documents.document_type_id)
                    .filter(Documents.user_id == user.id)
                    .filter(Documents.is_deleted == False)
                    .order_by(Documents.uploaded_at.desc())
                    .all()
                )

                docs_dict_list = []
                for doc_id, file_ext, file_alias, mime_type, is_opened, is_uploaded, page_count, uploaded_at in doc_list:
                    """
                    Uploaded at should be within 60 seconds or is_uploaded should be True
                    """
                    if not is_uploaded and (datetime.utcnow() - uploaded_at).total_seconds() > 60:
                        logger.info(f"skipping document {doc_id} as it is not uploaded")
                        continue
                    logger.info(doc_id, file_ext, file_alias, mime_type, page_count, uploaded_at)
                    docs_dict_list.append(
                        {
                            "document_id": f"{doc_id}",
                            "document_type": f"{file_ext}",
                            "file_name": f"{file_alias}",
                            "mime_type": f"{mime_type}",
                            "is_opened": is_opened,
                            "page_count": page_count,
                            "uploaded_at": f"{uploaded_at.isoformat()}",
                        }
                    )

                status_code, msg = 200, {
                    "status": "success",
                    "message": "Fetched all documents",
                    "details": {
                        "user_id": user.id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "document_list": docs_dict_list,
                    },
                }
            elif request_method == "DELETE":
                """Delete a document for a user"""
                document_id = get_query_parameter(event, "document_id")
                logger.info(f"deleting a document for the user: {username} document_id: {document_id}")
                db_document = session.query(Documents).filter(Documents.id == document_id).first()
                if not db_document:
                    raise DocumentNotFoundError(document_id)

                if db_document.is_deleted:
                    status_code, msg = 404, {
                        "status": "failed",
                        "message": "document already deleted",
                        "details": {"document_id": document_id},
                    }
                    return json_return(status_code, msg)

                db_document.is_deleted = True
                session.commit()
                status_code, msg = 200, {
                    "status": "success",
                    "message": "document deleted",
                    "details": {"document_id": document_id},
                }
            elif request_method == "PATCH":
                """patch a document"""
                body = event.get("body", None)
                logger.info(f"body: {body}")
                body = json.loads(body)
                document_id = get_body_parameter(body, "document_id")
                attribute_name = get_body_parameter(body, "name")
                attribute_value = get_body_parameter(body, "value")

                logger.info(f"Changing a document for the user: {username} document_id: {document_id}")
                db_document = session.query(Documents).filter(Documents.id == document_id).first()
                if not db_document:
                    raise DocumentNotFoundError(document_id)

                available_attributes = ["document_name", "document_is_opened"]

                if attribute_name not in available_attributes:
                    raise RaiseCustomException(status_code=400, message="Invalid attribute name")

                if attribute_name == available_attributes[0]:
                    logger.info(f"Renaming the document {db_document.file_alias} to {attribute_value}")
                    doc_name = Path(attribute_value)
                    if doc_name.suffix != db_document.file_extension:
                        raise RaiseCustomException(
                            status_code=400,
                            message=f"Invalid extension {doc_name.suffix}, {db_document.file_extension} expected",
                        )
                    db_document.file_alias = attribute_value

                if attribute_name == available_attributes[1]:
                    logger.info(f"Setting the document {db_document.file_alias} is_opened to {attribute_value}")
                    if attribute_value not in [True, False]:
                        raise RaiseCustomException(
                            status_code=400,
                            message=f"Invalid attribute value: {attribute_value}, expected True or False",
                        )
                    db_document.is_opened = attribute_value

                status_code, msg = 200, {
                    "status": "success",
                    "message": "document updated",
                    "details": {"document_id": document_id, "updated_field": attribute_name},
                }
            else:
                status_code, msg = 404, {
                    "status": "failed",
                    "message": "unknown request method",
                    "details": {"request_method": request_method},
                }
        except (
            MissingQueryParameterError,
            UserNotFoundError,
            DocumentNotFoundError,
            RaiseCustomException,
            MissingBodyParameter,
        ) as e:
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except Exception as exception:
            error_id = uuid.uuid4()
            logger.error(f"an error occurred, id: {error_id} error: {exception}")
            return {
                "isBase64Encoded": False,
                "statusCode": 500,
                "body": exception,
                "headers": {"content-type": "application/json"},
            }
        else:
            session.commit()
            return json_return(status_code, msg)
