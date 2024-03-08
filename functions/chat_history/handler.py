import base64
import json
import os
import uuid
from datetime import datetime

from loguru import logger

from aws.aws_s3 import S3Wrapper
from db.database import Database
from db.tables import Users, Documents, Chats
from utils.custom_exceptions import (
    MissingQueryParameterError,
    ChatNotFoundError,
    UserNotFoundError,
    DocumentNotFoundError,
)
from utils.util import json_return, get_query_parameter


def handler(event, _):
    """
    Downloads a PDF file from S3 given the file id
    """
    logger.info(event)
    database = Database()

    with database.get_session() as session:
        try:
            # Initialize custom S3 client
            s3_dd = S3Wrapper()

            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            request_method = event["requestContext"]["http"]["method"]
            document_id = get_query_parameter(event, "document_id")
            chat_id = get_query_parameter(event, "chat_id")
            result = (
                session.query(Users.username, Users.id, Documents.id)
                .join(Documents, Documents.user_id == Users.id)
                .join(Chats, Chats.document_id == Documents.id)
                .filter(Chats.id == chat_id)
                .filter(Documents.is_deleted == False)
                .first()
            )
            if not result:
                raise ChatNotFoundError(chat_id)
            db_username, db_user_id, db_document_id = result

            if username != db_username:
                raise UserNotFoundError(username)

            if document_id != db_document_id:
                raise DocumentNotFoundError(document_id)

            file_key = f"{db_user_id}/{db_document_id}/{chat_id}.json"
            debug_enabled = get_query_parameter(event, "debug", required=False)

            if request_method == "GET":
                if debug_enabled:
                    bucket_name = os.getenv("chat_context_bucket")
                else:
                    bucket_name = os.getenv("chat_history_bucket")
                data, _ = s3_dd.s3_get_object(bucket=bucket_name, key=file_key)

                json_history = json.loads(data.decode("utf-8"))
                output_dict = {
                    "status": "success",
                    "message": "Successfully extracted chat history",
                    "details": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "response": json_history,
                    },
                }
                file_content = base64.b64encode(json.dumps(output_dict).encode("utf-8")).decode("utf-8")
                return {
                    "isBase64Encoded": True,
                    "statusCode": 200,
                    "body": file_content,
                    "headers": {
                        "Content-Type": "application/json",  # Replace this with the correct MIME type for your file
                    },
                }

            elif request_method == "DELETE":
                bucket_name = os.getenv("chat_history_bucket")
                data, _ = s3_dd.s3_get_object(bucket=bucket_name, key=file_key)

                # move as a different object to chat_history_bucket
                new_file_key = f"{file_key}.json.{datetime.utcnow().isoformat()}"
                s3_dd.s3_put_object(body=data, bucket=bucket_name, key=new_file_key)

                # delete the object from chat_history_bucket
                s3_dd.s3_delete_object(bucket=bucket_name, key=file_key)

                # put empty object in chat_context_bucket
                json_history = json.loads(data.decode("utf-8"))
                json_history["conversation"] = []
                s3_dd.s3_put_json(body=json_history, bucket=bucket_name, key=file_key)

                return json_return(
                    200,
                    {
                        "status": "success",
                        "message": "chat history deleted",
                        "details": {
                            "document_id": document_id,
                            "chat_id": chat_id,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    },
                )

        except (MissingQueryParameterError, ChatNotFoundError, UserNotFoundError, DocumentNotFoundError) as e:
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except Exception as exception:
            error_id = uuid.uuid4()
            logger.exception(f"an error occurred, id: {error_id} error: {exception}")
            return {
                "isBase64Encoded": False,
                "statusCode": 500,
                "body": exception,
                "headers": {"content-type": "application/json"},
            }
        else:
            session.cmmmit()
