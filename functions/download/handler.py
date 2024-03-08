import base64
import json
import os
import uuid

import boto3
from loguru import logger

from db.database import Database
from db.documents import Documents
from db.users import Users

response = {"isBase64Encoded": False, "statusCode": 500, "body": "", "headers": {"content-type": "application/json"}}

s3 = boto3.client("s3")
bucket_name = os.getenv("bucket")


def handler(event, context):
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
                        file_key = f"{user.id}/{doc.document_id}{doc.document_type}"

                        obj = s3.get_object(Bucket=bucket_name, Key=file_key)
                        file_content = base64.b64encode(obj["Body"].read()).decode("utf-8")

                        return {
                            "isBase64Encoded": True,
                            "statusCode": 200,
                            "body": file_content,
                            "headers": {
                                "Content-Type": f"{doc.mime_type}",  # Replace this with the correct MIME type for your file
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
            "headers": {"content-type": "application/json"},
        }
