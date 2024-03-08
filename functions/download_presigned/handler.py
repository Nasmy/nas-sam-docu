import json
import os
import uuid
from datetime import datetime, timedelta

from loguru import logger

from aws.aws_s3 import S3Wrapper
from db.database import Database
from db.tables import Users, Documents
from utils.custom_exceptions import (
    MissingQueryParameterError,
    DocumentNotFoundError,
    UserNotFoundError,
    MissingPathParameterError,
)
from utils.util import json_return, get_query_parameter, get_path_parameter

s3_dd = S3Wrapper()
bucket_name = os.getenv("bucket")


def handler(event, _):
    """
    Downloads a PDF file from S3 given the file id
    """
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            if "queryStringParameters" in event:
                document_id = get_query_parameter(event, "document_id")
            else:
                document_id = get_path_parameter(event, "document_id")
            result = (
                session.query(Users.username, Users.id, Documents.id, Documents.file_extension)
                .join(Documents, Documents.user_id == Users.id)
                .filter(Documents.id == document_id)
                .first()
            )
            if not result:
                raise DocumentNotFoundError(document_id)

            db_username, db_user_id, db_document_id, db_doc_ext = result

            if username != db_username:
                raise UserNotFoundError(username)

            exp_seconds = int(os.getenv("link_expiration_seconds", 600))
            expiration = datetime.utcnow() + timedelta(seconds=exp_seconds)
            file_key = f"{db_user_id}/{db_document_id}{db_doc_ext}"
            pre_signed_url = s3_dd.s3_generate_presigned_url(
                bucket_name=bucket_name,
                file_key=file_key,
                exp_seconds=exp_seconds,
            )

            output_dict = {
                "status": "success",
                "message": "document download url created!",
                "details": {
                    "document_id": document_id,
                    "pre_signed_url": pre_signed_url,
                    "link_expiration_seconds": exp_seconds,
                    "timestamp": datetime.utcnow().isoformat(),
                    "expiration": expiration.isoformat(),
                },
            }

            return {
                "isBase64Encoded": False,
                "statusCode": 200,
                "body": json.dumps(output_dict),
                "headers": {"content-type": "application/json"},
            }
        except (MissingQueryParameterError, UserNotFoundError, DocumentNotFoundError, MissingPathParameterError) as e:
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
