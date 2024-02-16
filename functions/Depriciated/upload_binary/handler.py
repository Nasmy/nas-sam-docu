import base64
import json
import os
import uuid
from mimetypes import guess_extension

import boto3
from loguru import logger

# Lambda layer
from db.database import Database
from db.tables import Users, Documents
from utils.document_types import get_document_type_from_extension, DocumentTypes

response = {"isBase64Encoded": False, "statusCode": 500, "body": "", "headers": {"content-type": "application/json"}}

s3 = boto3.client("s3")
bucket_name = os.getenv("bucket")


def handler(event, _):
    """
    Uploads a PDF file to S3
    """
    try:
        logger.info(event)
        database = Database()
        with database.get_session() as session:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            if username:
                user = session.query(Users).filter(Users.username == username).first()
                if user:
                    document_type = ".unknown"
                    content_type = event["headers"].get("content-type", None)
                    if content_type:
                        guessed_type = guess_extension(content_type)
                        if guessed_type:
                            document_type = guessed_type
                    else:
                        content_type = "application/octet-stream"

                    file_content = (
                        base64.b64decode(event["body"]) if event["isBase64Encoded"] else event["body"].encode()
                    )
                    file_name = "somefile"

                    doc_type: DocumentTypes = get_document_type_from_extension(document_type)

                    if doc_type == DocumentTypes.PDF or doc_type in [
                        DocumentTypes.IMAGE_JPG.value,
                        DocumentTypes.IMAGE_PNG.value,
                    ]:
                        document_id = str(uuid.uuid4())
                        doc = Documents(
                            id=str(uuid.uuid4()),
                            user_id=user.id,
                            document_id=document_id,
                            document_type=document_type,
                            file_name=file_name,
                            file_alias=file_name,
                            mime_type=content_type,
                        )
                        file_key = f"{user.id}/{document_id}{document_type}"
                        meta_data = {
                            "user_id": str(user.id),
                            "document_id": str(document_id),
                            "document_ext": document_type,
                            "document_type": doc_type.value,
                        }
                        # Upload the file to S3
                        s3.put_object(Body=file_content, Bucket=bucket_name, Key=file_key, Metadata=meta_data)

                        session.add(doc)
                        session.commit()

                        status_code, msg = 201, {
                            "status": "success",
                            "message": "file uploaded",
                            "details": {"document_id": str(document_id)},
                        }
                    else:
                        logger.error(f"invalid document type: {document_type}")
                        status_code, msg = 400, {
                            "status": "failed",
                            "message": "document type not supported",
                            "details": {"document_type": document_type},
                        }

                else:
                    logger.error(f"user does not exist: {username}")
                    status_code, msg = 403, {
                        "status": "failed",
                        "message": "user doesn't exist",
                        "details": {"username": username},
                    }
            else:
                logger.error(f"!Very important: user was not passed from authorizer: {username}")
                status_code, msg = 403, {
                    "status": "failed",
                    "message": "user doesn't exist",
                    "details": {"username": username},
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
