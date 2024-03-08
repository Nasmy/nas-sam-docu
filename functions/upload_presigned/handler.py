import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import boto3
from loguru import logger

# Lambda layer
from db.database import Database
from db.documents import Documents
from db.users import Users
from utils.document_types import DocumentTypes, get_document_type_from_extension, doc_type_to_mime_type

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
                    body = event.get("body", None)

                    body = json.loads(body)
                    file_name_str = body.get("file_name", None)

                    if not file_name_str:
                        return {
                            "isBase64Encoded": False,
                            "statusCode": 400,
                            "body": "file_name is required",
                        }
                    file_name = Path(file_name_str)

                    logger.info(f"file_name: {file_name}")
                    document_type = f"{file_name.suffix}".lower()

                    doc_type: DocumentTypes = get_document_type_from_extension(document_type)

                    if doc_type in [
                        DocumentTypes.PDF,
                        DocumentTypes.IMAGE_JPG,
                        DocumentTypes.IMAGE_PNG,
                        DocumentTypes.TXT,
                    ]:
                        document_id = str(uuid.uuid4())
                        doc = Documents(
                            id=str(uuid.uuid4()),
                            user_id=user.id,
                            document_id=document_id,
                            document_type=document_type,
                            file_name=str(file_name),
                            file_alias=str(file_name),
                            mime_type=doc_type_to_mime_type(doc_type),
                        )
                        file_key = f"{user.id}/{document_id}{document_type}"
                        metadata = {
                            "user_id": str(user.id),
                            "document_id": str(document_id),
                            "document_ext": document_type,
                            "document_type": doc_type.value,
                        }
                        # Upload the file to S3
                        pre_signed_url = s3.generate_presigned_url(
                            "put_object",
                            Params={
                                "Bucket": bucket_name,
                                "Key": file_key,
                                "Metadata": metadata,
                                "ContentType": doc_type_to_mime_type(doc_type),
                            },
                            ExpiresIn=3600,
                        )

                        session.add(doc)
                        session.commit()

                        status_code, msg = 201, {
                            "status": "success",
                            "message": "file uploaded",
                            "details": {
                                "document_id": str(document_id),
                                "document_type": doc_type.value,
                                "metadata": metadata,
                                "pre_signed_url": pre_signed_url,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
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
        logger.exception(f"an error occurred, id: {error_id} error: {exception}")
        logger.error(f"an error occurred, id: {error_id} error: {exception}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": exception,
            "headers": {"content-type": "application/json"},
        }
