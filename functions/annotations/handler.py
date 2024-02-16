import base64
import json
import os
import uuid
from datetime import datetime, timedelta

from loguru import logger

from aws.aws_s3 import S3Wrapper
from db.database import Database
from db.tables import Users, Documents, Annotations, AnnotationTypesTable
from utils.annotation_types import AnnotationTypes, get_annotation_types, AnnotationStatus, get_insight_type
from utils.custom_exceptions import (
    DocumentNotFoundError,
    UserNotFoundError,
    MissingQueryParameterError,
    RaiseCustomException,
)
from utils.util import (
    json_return,
    get_query_parameter,
    get_request_method,
    get_request_user,
    get_http_path,
)

dd_s3 = S3Wrapper()
bucket_name = os.getenv("bucket")


def handler(event, _):
    """
    Downloads a PDF file from S3 given the file id
    """
    database = Database()
    logger.info(event)
    with database.get_session() as session:
        try:
            request_method = get_request_method(event)
            http_path = get_http_path(event)
            username = get_request_user(event)
            if request_method == "GET":
                document_id = get_query_parameter(event, "document_id")
            else:
                raise RaiseCustomException(400, f"invalid request method - {request_method}, only GET supported")

            if not username:
                raise UserNotFoundError(username)

            result = (
                session.query(Users.username, Users.id, Documents.id)
                .join(Documents, Documents.user_id == Users.id)
                .filter(Documents.id == document_id)
                .filter(Documents.is_deleted == False)
                .first()
            )
            if not result:
                raise DocumentNotFoundError(document_id)

            db_username, db_user_id, db_document_id = result
            if db_username != username:
                logger.error(f"username mismatch, request username: {username}, db username: {db_username}")
                raise UserNotFoundError(username)

            if http_path == "/api/annotations":
                logger.info("GET-/api/annotations request processing")
                annotation_type_str = get_query_parameter(event, "annotation_type")
                debug_enabled = get_query_parameter(event, "debug", required=False)
                logger.info(
                    f"user {username} is requesting {annotation_type_str} annotations for document {document_id}"
                )

                annotation_type: AnnotationTypes = get_annotation_types(annotation_type_str)
                file_key = f"{db_user_id}/{db_document_id}/{db_document_id}-{annotation_type.value}.json"

                try:
                    content, _ = dd_s3.s3_get_object(bucket=bucket_name, key=file_key)
                    if not debug_enabled:
                        # remove debug information from object json
                        full_json = json.loads(content.decode("utf-8"))
                        if "debug" in full_json:
                            del full_json["debug"]
                        file_content = base64.b64encode(json.dumps(full_json).encode("utf-8")).decode("utf-8")
                    else:
                        file_content = base64.b64encode(content).decode("utf-8")
                except Exception as exception:
                    logger.error(f"document: {document_id} with error: {exception}")
                    return json_return(202, {"status": "processing", "document_id": str(db_document_id)})

                response = {
                    "isBase64Encoded": True,
                    "statusCode": 200,
                    "body": file_content,
                    "headers": {
                        "Content-Type": "application/json",  # Replace this with the correct MIME type for your file
                    },
                }

            elif http_path == "/api/annotation-progress":
                logger.info(f"GET-{http_path} request processing")

                all_annotations = (
                    session.query(Annotations, AnnotationTypesTable.name, AnnotationTypesTable.is_insight, AnnotationTypesTable.display_name)
                    .join(AnnotationTypesTable, AnnotationTypesTable.id == Annotations.annotation_type_id)
                    .filter(Annotations.document_id == document_id)
                    .filter(AnnotationTypesTable.is_enabled == True)
                    .all()
                )
                if not all_annotations:
                    raise RaiseCustomException(202, "document not yet received", {"document_id": document_id})

                annotation_status_list = []
                total_annotations = 0
                completed_annotations = 0
                total_insights = 0
                completed_insights = 0
                for anno, annotation_type, is_insight, display_name in all_annotations:
                    logger.info(f"status: {anno.status}, annotation_type: {annotation_type}, is_insight: {is_insight}")
                    total_annotations += 1
                    if is_insight:
                        total_insights += 1

                    is_completed_annotation = anno.status in [
                        AnnotationStatus.COMPLETED.value,
                        AnnotationStatus.FAILED.value,
                        AnnotationStatus.EMPTY.value,
                        AnnotationStatus.TIMEOUT.value
                    ]

                    if not is_completed_annotation:
                        # get the second difference between created_at and current time
                        if datetime.utcnow() - anno.created_at > timedelta(seconds=600):
                            anno.status = AnnotationStatus.TIMEOUT.value
                            logger.info(f"Setting {annotation_type} status to timeout - which is completed")
                            is_completed_annotation = True

                    if is_completed_annotation:
                        completed_annotations += 1
                        if is_insight:
                            completed_insights += 1

                    annotation_status_list.append(
                        {
                            "status": anno.status,
                            "annotation_type": annotation_type,
                            "display_name": display_name,
                            "is_insight": is_insight,
                            "insight_type": get_insight_type(annotation_type).value
                        }
                    )

                output_dict = {
                    "status": "success",
                    "message": "all annotations retrieved",
                    "details": {
                        "document_id": document_id,
                        "progress": f"{completed_annotations}/{total_annotations}",
                        "insights_progress": f"{completed_insights}/{total_insights}",
                        "annotations_list": annotation_status_list,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
                logger.info(output_dict)
                response = json_return(200, output_dict)
            else:
                raise RaiseCustomException(400, f"invalid http path - {http_path}")

        except (MissingQueryParameterError, UserNotFoundError, DocumentNotFoundError, RaiseCustomException) as e:
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except Exception as exception:
            error_id = uuid.uuid4()
            status_code = 500
            logger.exception(f"an error occurred, id: {error_id} error: {exception}")
            logger.error(f"an error occurred, id: {error_id} error: {exception}")
            return json_return(status_code, exception)
        else:
            session.commit()
            return response
