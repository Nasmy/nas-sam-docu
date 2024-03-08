import base64
import json
import os
import uuid
from datetime import datetime

import boto3
from loguru import logger

from db.database import Database
from db.document_chat import DocumentChat
from db.documents import Documents
from db.users import Users

response = {"isBase64Encoded": False, "statusCode": 500, "body": "", "headers": {"content-type": "application/json"}}

s3 = boto3.client("s3")


def return_response(status_code: int, msg: dict):

    response["statusCode"] = status_code
    response["body"] = json.dumps(msg)
    return response


def handler(event, _):
    """
    Downloads a PDF file from S3 given the file id
    """
    logger.info(event)
    try:
        database = Database()
        with database.get_session() as session:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            request_method = event["requestContext"]["http"]["method"]
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
                        chat_id = event["queryStringParameters"]["chat_id"]
                        document_chat = (
                            session.query(DocumentChat)
                            .filter(DocumentChat.chat_id == chat_id, DocumentChat.document_id == document_id)
                            .first()
                        )
                        if document_chat:
                            file_key = f"{user.id}/{document_id}/{chat_id}.json"
                            debug_enabled = event["queryStringParameters"].get("debug", None)
                            try:
                                if request_method == "GET":
                                    if debug_enabled:
                                        bucket_name = os.getenv("chat_context_bucket")
                                    else:
                                        bucket_name = os.getenv("chat_history_bucket")
                                    obj = s3.get_object(Bucket=bucket_name, Key=file_key)
                                elif request_method == "DELETE":
                                    bucket_name = os.getenv("chat_history_bucket")
                                    obj = s3.get_object(Bucket=bucket_name, Key=file_key)

                                    # move as a different object to chat_history_bucket
                                    new_file_key = f"{file_key}.json.{datetime.utcnow().isoformat()}"
                                    s3.put_object(Body=obj["Body"].read(), Bucket=bucket_name, Key=new_file_key)

                                    # delete the object from chat_history_bucket
                                    obj = s3.delete_object(Bucket=bucket_name, Key=file_key)
                                    return return_response(
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

                            except Exception as exception:
                                logger.info(f"document: {document_id}, chat: {chat_id}, with error: {exception}")
                                return {
                                    "isBase64Encoded": True,
                                    "statusCode": 202,
                                    "detail": {
                                        "status": "processing",
                                        "document_id": str(doc.document_id),
                                        "chat_id": str(chat_id),
                                    },
                                    "headers": {"content-type": "application/json"},
                                }
                            json_history = json.loads(obj["Body"].read().decode("utf-8"))
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
                        else:
                            logger.error(f"Invalid chat id: {chat_id}")
                            status_code, msg = 404, {
                                "status": "failed",
                                "message": "chat doesn't exist",
                                "detail": {"chat_id": chat_id},
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
        return return_response(status_code, msg)

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
