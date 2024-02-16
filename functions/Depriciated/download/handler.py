import base64
import os
import uuid

import boto3
from loguru import logger

from db.database import Database
from db.tables import Users, DocumentTypesTable, Documents
from utils.util import json_return

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
            document_id = event["queryStringParameters"]["document_id"]

            if not username:
                logger.error(f"!Very important: user was not passed from authorizer: {username}")
                status_code, msg = 403, {
                    "status": "failed",
                    "message": "user doesn't exist",
                    "detail": {"username": username},
                }
                return json_return(status_code, msg)

            result = (
                session.query(
                    Users.username,
                    Users.id,
                    Documents.id,
                    DocumentTypesTable.document_type,
                    DocumentTypesTable.mime_type,
                )
                .join(Documents, Documents.user_id == Users.id)
                .join(DocumentTypesTable, DocumentTypesTable.id == Documents.document_type_id)
                .filter(Documents.id == document_id)
                .first()
            )

            if not result:
                msg = {"status": "failed", "message": "document doesn't exist"}
                return json_return(404, msg)

            db_username, db_user_id, db_document_id, db_doc_type, db_doc_mime = result

            if username != db_username:
                msg = {"status": "failed", "message": f"user {username} not authorized to access this document"}
                return json_return(401, msg)

            file_key = f"{db_user_id}/{db_document_id}{db_doc_type}"
            obj = s3.get_object(Bucket=bucket_name, Key=file_key)
            file_content = base64.b64encode(obj["Body"].read()).decode("utf-8")

            return {
                "isBase64Encoded": True,
                "statusCode": 200,
                "body": file_content,
                "headers": {
                    "Content-Type": f"{db_doc_mime}",  # Replace this with the correct MIME type for your file
                },
            }

    except Exception as exception:
        error_id = uuid.uuid4()
        logger.error(f"an error occured, id: {error_id} error: {exception}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": exception,
            "headers": {"content-type": "application/json"},
        }
