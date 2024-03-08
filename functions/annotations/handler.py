import base64
import json
import os
import uuid

import boto3
from loguru import logger

from db.database import Database
from db.documents import Documents
from db.users import Users
from utils.annotation_types import AnnotationTypes, get_annotation_types

app_json = "application/json"
response = {"isBase64Encoded": False, "statusCode": 500, "body": "", "headers": {"content-type": app_json}}

s3 = boto3.client("s3")
bucket_name = os.getenv("bucket")


def handler(event, _):
    """
    Downloads a PDF file from S3 given the file id
    """
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
                        annotation_type_str = event["queryStringParameters"].get("annotation_type", "None")
                        debug_enabled = event["queryStringParameters"].get("debug", None)
                        annotation_type: AnnotationTypes = get_annotation_types(annotation_type_str)
                        file_key = f"{user.id}/{doc.document_id}/{doc.document_id}-{annotation_type.value}.json"

                        try:
                            obj = s3.get_object(Bucket=bucket_name, Key=file_key)
                            if not debug_enabled:
                                # remove debug information from object json
                                full_json = json.loads(obj["Body"].read().decode("utf-8"))
                                if "debug" in full_json:
                                    del full_json["debug"]
                                file_content = base64.b64encode(json.dumps(full_json).encode("utf-8")).decode("utf-8")
                            else:
                                file_content = base64.b64encode(obj["Body"].read()).decode("utf-8")
                        except Exception as exception:
                            logger.info(f"document: {document_id} with error: {exception}")
                            return {
                                "isBase64Encoded": True,
                                "statusCode": 202,
                                "detail": {"status": "processing", "document_id": str(doc.document_id)},
                                "headers": {"content-type": app_json},
                            }

                        return {
                            "isBase64Encoded": True,
                            "statusCode": 200,
                            "body": file_content,
                            "headers": {
                                "Content-Type": app_json,  # Replace this with the correct MIME type for your file
                            },
                        }
                    else:
                        logger.error(f"Invalid document id: {document_id}")
                        status_code, msg = 404, {
                            "status": "failed",
                            "message": "document doesn't exist",
                            "detail": {"document_id": document_id},
                        }
                else:
                    logger.error(f"user does not exist: {username}")
                    status_code, msg = 403, {
                        "status": "failed",
                        "message": "user doesn't exist",
                        "detail": {"username": username},
                    }
            else:
                logger.error(f"!Very important: user was not passed from authorizer: {username}")
                status_code, msg = 403, {
                    "status": "failed",
                    "message": "user doesn't exist",
                    "detail": {"username": username},
                }
        database.close_connection()
        response["statusCode"] = status_code
        response["body"] = json.dumps(msg)
        return response

    except Exception as exception:
        database.close_connection()
        error_id = uuid.uuid4()
        logger.error(f"an error occured, id: {error_id} error: {exception}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": exception,
            "headers": {"content-type": app_json},
        }
