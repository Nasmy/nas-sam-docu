import base64
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import boto3
from loguru import logger
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import ValueTarget

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
                    # Reference - https://pinchoflogic.com/multiplepartfrom-data-aws-api-gateway-lambda
                    parser = StreamingFormDataParser(headers=event["headers"])
                    parser_file_name = ValueTarget()
                    uploaded_file = ValueTarget()

                    parser.register("filename", parser_file_name)
                    parser.register("file", uploaded_file)

                    parser.data_received(base64.b64decode(event["body"]))

                    file_content = uploaded_file.value
                    file_name = Path(parser_file_name.value.decode("utf-8"))

                    logger.info(f"file_name: {file_name}")
                    document_type = f"{file_name.suffix}".lower()

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
                            file_name=str(file_name),
                            file_alias=str(file_name),
                            mime_type=doc_type_to_mime_type(doc_type),
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
                            "details": {
                                "document_id": str(document_id),
                                "document_type": doc_type.value,
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
        logger.error(f"an error occured, id: {error_id} error: {exception}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": exception,
            "headers": {"content-type": "application/json"},
        }
