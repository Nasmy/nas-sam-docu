import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from urllib.request import urlretrieve

import boto3
from loguru import logger

from aws.aws_s3 import S3Wrapper

# Lambda layer
from db.database import Database
from db.tables import Users, Documents, DocumentTypesTable as DocumentTypesTable
from utils.custom_exceptions import MissingBodyParameter, UserNotFoundError, RaiseCustomException
from utils.document_types import DocumentTypes, get_document_type_from_extension, doc_type_to_mime_type
from utils.util import json_return, get_body_parameter, get_http_path

response = {"isBase64Encoded": False, "statusCode": 500, "body": "", "headers": {"content-type": "application/json"}}

s3 = boto3.client("s3")
bucket_name = os.getenv("bucket")


def handler(event, _):
    """
    Uploads a PDF file to S3
    """
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            http_path = get_http_path(event)
            logger.info(f"username: {username}, HTTP Path: {http_path}")

            if not username:
                raise UserNotFoundError(username)

            user = session.query(Users).filter(Users.username == username).first()
            if not user:
                raise UserNotFoundError(username)

            body = event.get("body", None)

            if http_path == "/api/documents":
                body = json.loads(body)
                file_download_url = get_body_parameter(body, "file_name")
                file_name = Path(file_download_url)

                logger.info(f"file_name: {file_name}")
                document_ext = f"{file_name.suffix}".lower()
                logger.info(f"doc_type: {document_ext}")

                doc_type: DocumentTypes = get_document_type_from_extension(document_ext)
                logger.info(f"doc_type: {doc_type}")

                if doc_type not in [
                    DocumentTypes.PDF,
                    DocumentTypes.IMAGE_JPG,
                    DocumentTypes.IMAGE_PNG,
                    DocumentTypes.TXT,
                ]:
                    logger.error(f"invalid document type: {document_ext}")
                    status_code, msg = 400, {
                        "status": "failed",
                        "message": "document type not supported",
                        "details": {"document_type": document_ext},
                    }
                    return json_return(status_code, msg)

                db_doc_type = (
                    session.query(DocumentTypesTable).filter(DocumentTypesTable.document_type == doc_type.name).first()
                )

                logger.info(f"db_doc_type: {db_doc_type}")

                if not doc_type:
                    db_doc_type = DocumentTypesTable(
                        document_type=doc_type.name,
                        mime_type=doc_type_to_mime_type(doc_type),
                    )
                    session.add(db_doc_type)
                    session.commit()

                document_id = str(uuid.uuid4())
                logger.info(f"document_id: {document_id}")
                name, ext = os.path.splitext(str(file_name))
                trimmed_filename = name[:56] + ext
                if str(file_name) != trimmed_filename:
                    logger.info(f"Filename trimmed: {file_name} > {trimmed_filename}")
                db_doc = Documents(
                    id=document_id,
                    user_id=user.id,
                    document_type_id=db_doc_type.id,
                    file_name=trimmed_filename,
                    file_alias=trimmed_filename,
                    file_extension=document_ext,
                )
                file_key = f"{user.id}/{document_id}{document_ext}"
                metadata = {
                    "user_id": str(user.id),
                    "document_id": str(document_id),
                    "document_ext": document_ext,
                    "document_type": doc_type.value,
                }
                # Upload the file to S3
                pre_signed_url = s3.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": bucket_name,
                        "Key": file_key,
                        "Metadata": metadata,
                        "ContentType": db_doc_type.mime_type,
                    },
                    ExpiresIn=3600,
                )
                logger.info(f"pre_signed_url: {pre_signed_url}")
                session.add(db_doc)

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
            elif http_path == "/api/document-url":
                body = json.loads(body)
                file_download_url = get_body_parameter(body, "url")
                filename = file_download_url.split("/")[-1]
                if file_download_url.endswith(".pdf"):
                    document_ext = ".pdf"
                    doc_type = DocumentTypes.PDF
                    # download the file from the public URL
                    temp_filename = f"/tmp/{filename}"
                    urlretrieve(file_download_url, temp_filename)

                    document_id = str(uuid.uuid4())
                    name, ext = os.path.splitext(str(filename))
                    trimmed_filename = name[:56] + ext

                    db_doc_type = (
                        session.query(DocumentTypesTable)
                        .filter(DocumentTypesTable.document_type == doc_type.name)
                        .first()
                    )

                    db_doc = Documents(
                        id=document_id,
                        user_id=user.id,
                        document_type_id=db_doc_type.id,
                        file_name=trimmed_filename,
                        file_alias=trimmed_filename,
                        file_extension=document_ext,
                    )
                    file_key = f"{user.id}/{document_id}{document_ext}"
                    metadata = {
                        "user_id": str(user.id),
                        "document_id": str(document_id),
                        "document_ext": document_ext,
                        "document_type": "pdf",
                    }
                    # Upload the file to S3
                    dd_s3 = S3Wrapper()
                    ret = dd_s3.s3_put_object(
                        bucket=bucket_name, key=file_key, body=open(temp_filename, "rb"), metadata=metadata
                    )
                    logger.info(f"uploaded: {ret}")
                    os.remove(temp_filename)
                    if not ret:
                        raise RaiseCustomException(500, "failed to upload file to S3", {"file_key": file_key})
                    session.add(db_doc)

                    status_code, msg = 201, {
                        "status": "success",
                        "message": "file uploaded",
                        "details": {
                            "document_id": str(document_id),
                            "document_type": doc_type.value,
                            "metadata": metadata,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    }
                else:
                    raise RaiseCustomException(400, "url type is not supported!", {"url": file_download_url})
            else:
                raise RaiseCustomException(400, "invalid HTTP path", {"http_path": http_path})

        except (MissingBodyParameter, UserNotFoundError, RaiseCustomException) as e:
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except Exception as exception:
            database.close_connection()
            error_id = uuid.uuid4()
            logger.exception(f"an error occurred, id: {error_id} error: {exception}")
            logger.error(f"an error occurred, id: {error_id} error: {exception}")
            return json_return(500, {"status": "failed", "message": f"{exception}"})
        else:
            session.commit()
            return json_return(status_code, msg)
