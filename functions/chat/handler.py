import json
import os
import uuid
from datetime import datetime, timedelta
import boto3
from loguru import logger

from aws.aws_s3 import S3Wrapper
from chat.chat_types import ChatTypes
from chat.chatgpt import ChatGPT
from chat.chatgpt_vision import ChatGptVision
from chat.model_info import OpenAIModels, ModelInfo
from chat.query_types import ContextTypes
from context_loader import ContextLoader
from db.database import Database
from db.tables import Users, Documents, Chats, Queries, Models, APIKeys
from utils.custom_exceptions import (
    MissingBodyParameter,
    UserNotFoundError,
    DocumentNotFoundError,
    ChatNotFoundError,
    RaiseCustomException,
)
from utils.util import json_return, get_body_parameter
from utils.document_types import get_document_type_from_extension, DocumentTypes

s3 = boto3.client("s3")
files_digest_bucket = os.getenv("files_digest_bucket")
chat_context_bucket = os.getenv("chat_context_bucket")
chat_history_bucket = os.getenv("chat_history_bucket")
bucket_name = os.getenv("bucket")


def handler(event, _):
    """
    Chat handler for the chatbot
    1. Upgrade to context based chatbot
    """
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            """
            Get all the parameters
            """
            body = event.get("body", None)
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            body = json.loads(body)

            document_id = get_body_parameter(body, "document_id")
            chat_id = get_body_parameter(body, "chat_id", required=False)
            chat_name = get_body_parameter(body, "chat_name", required=False)
            query_id = get_body_parameter(body, "query_id", required=False)
            query = get_body_parameter(body, "query")
            doc_context = get_body_parameter(body, "context", required=False)
            reset_context = get_body_parameter(body, "reset_context", required=False)
            chat_debug = get_body_parameter(body, "debug", required=False)
            gpt_4_vision_enable = False
            logger.info(f"{username}, {document_id}, {query_id}, {query}, {doc_context}")

            """Check whether chat id or chat name is set"""
            if not (chat_id or chat_name):
                raise RaiseCustomException(400, "chat_id or chat_name is required")

            """Check other parameters"""
            if not (username and (chat_name or chat_id) and (not query_id or len(query_id) <= 36)):
                api_response = {"query_id": query_id, "document_id": document_id, "response": None}
                raise RaiseCustomException(400, "incomplete request", api_response)

            """If query id is not present, generate one"""
            query_id = query_id if query_id else str(uuid.uuid4())

            result = (
                session.query(Users.username, Users.id, Documents.id, Documents.file_extension)
                .join(Documents, Documents.user_id == Users.id)
                .filter(Documents.id == document_id)
                .filter(Documents.is_deleted == False)
                .first()
            )
            logger.info(f"results - {result}")

            if not result:
                raise DocumentNotFoundError(document_id)

            db_username, db_user_id, db_document_id, db_doc_ext = result
            if db_username != username:
                raise UserNotFoundError(username)

            """Check whether chat id is present, or create a new one"""
            if chat_id:
                db_doc_chat = (
                    session.query(Chats).filter(Chats.id == chat_id, Chats.document_id == db_document_id).first()
                )
                if not db_doc_chat:
                    raise ChatNotFoundError(chat_id)
            else:
                db_doc_chat = (
                    session.query(Chats)
                    .filter(Chats.chat_name == chat_name, Chats.document_id == db_document_id)
                    .first()
                )
                if not db_doc_chat:
                    db_doc_chat = Chats(
                        document_id=db_document_id,
                        chat_name=chat_name,
                        chat_type=ChatTypes.USER.value,
                    )
                    session.add(db_doc_chat)
                    session.commit()
                    reset_context = True

                chat_id = db_doc_chat.id

            """Load chat context from S3 if present"""
            file_key = f"{db_user_id}/{db_document_id}/{chat_id}.json"
            chat_initialized = True
            try:
                if not reset_context:
                    content, _ = s3.get_object(bucket=chat_context_bucket, key=file_key)
                    chat_context = json.loads(content.decode("utf-8"))
                    logger.info("chat context loaded!")
                    chat_initialized = False
                else:
                    chat_context = {"conversation": []}
                    logger.info("chat context reset!")
            except Exception as _:
                chat_context = {"conversation": []}

            """
            If the context is available and 
            1. if the chat is initialized
            2. if the reset context is false
            ,then load the context
            """
            doc_context_initialized = False
            doc_type = get_document_type_from_extension(db_doc_ext)
            context_type = None
            if chat_initialized and doc_context:
                context_loader_obj = ContextLoader(db_user_id, document_id, doc_context)
                chat_context, context_type = context_loader_obj.load_context_and_type()
                if chat_context:
                    doc_context_initialized = True

            query_request_timestamp = datetime.utcnow().isoformat()
            """If the context is questions, we dont need to invoke chatgpt since we have the answers"""
            if doc_context_initialized and context_type == ContextTypes.QUESTION.value:
                query = chat_context["question"]
                chat_response = chat_context["answer"]
                query_response_timestamp = datetime.utcnow().isoformat()
                total_tokens = 0
                selected_model = OpenAIModels.get_model("gpt-3.5-turbo")
            else:
                logger.info("Enter into else part")
                """Model selection based on context length"""
                full_word_count = ContextLoader.context_length(chat_context) + query.count(" ")
                """ 
                Check the document type is relevant to images
                If document type is image then change the gpt model to gpt model vision api
                """
                if doc_type in [
                    DocumentTypes.IMAGE_JPG,
                    DocumentTypes.IMAGE_PNG,
                ]:
                    gpt_4_vision_enable = True
                    selected_model: ModelInfo = OpenAIModels.get_model("gpt-4-vision-preview")
                else:
                    gpt_4_vision_enable = False
                    selected_model: ModelInfo = OpenAIModels.get_model_based_on_text_length(full_word_count)

                """
                Need to get the API key from db and set in chatGPT class
                This is WIP code
                """
                db_api_key = session.query(APIKeys).filter(APIKeys.service_key == "openai_key1").first()
                if not db_api_key:
                    logger.error("API key not found!")
                    details = {"service_key": "openai_key1"}
                    raise RaiseCustomException(404, "API key not found", details)

                gpt_model = ChatGPT(selected_model, api_key=db_api_key.api_key, verbose=True)
                gpt_model.set_context_dict(chat_context)
                logger.info(f"query message - {query}")

                """ enable the gpt 4 """
                if gpt_4_vision_enable:
                    """"file_key = f"{db_user_id}/{db_document_id}.{db_doc_ext}"
                    content = s3.get_object(Bucket=bucket_name, key=file_key)
                    logger.info(json.loads(content["Body"].read().decode("utf-8")))
                    print(json.loads(content["Body"].read().decode("utf-8")))"""""
                    prompt = {
                     "image_string": "https://www.peacepost.asia/wp-content/uploads/2019/06/11560198184_.pic_-1024x768.jpg",
                     "questions": query
                    }

                    gpt_vision = ChatGptVision(db_api_key, selected_model, prompt)
                    chat_response = gpt_vision.analyse_image_string()
                else:
                    chat_response = gpt_model.chat_with_context(prompt=query)

                query_response_timestamp = datetime.utcnow().isoformat()
                total_tokens = gpt_model.get_total_tokens()
                logger.info(f"Total tokens used: {total_tokens}")

                db_model = session.query(Models).filter(Models.name == selected_model.name).first()

                if not db_model:
                    details = {"model": selected_model.name}
                    raise RaiseCustomException(404, "model not found", details)

                """Update the query cost in the database"""
                prompt_tokens = gpt_model.get_prompt_tokens()
                completion_tokens = gpt_model.get_completion_tokens()
                prompt_1k_cost = db_model.prompt_1k_cost
                completion_1k_cost = db_model.completion_1k_cost
                total_cost = prompt_tokens * prompt_1k_cost + completion_tokens * completion_1k_cost

                chat_query = Queries(
                    id=query_id,
                    chat_id=chat_id,
                    model_id=db_model.id,
                    api_key_id=db_api_key.id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    prompt_1k_cost=prompt_1k_cost,
                    completion_1k_cost=prompt_1k_cost,
                    total_amount=total_cost,
                )
                session.add(chat_query)

                """Create the chat context output"""
                chat_context_output = gpt_model.get_context_dict()
                json_str = json.dumps(chat_context_output)

            try:
                """Update the chat context in S3"""
                s3.put_object(
                    body=json_str,
                    bucket=chat_context_bucket,
                    key=file_key,
                    content_type="application/json",
                )
            except Exception as exception:
                logger.info("failed to update object")

            """Prepare the chat history"""
            chat_history_entry = {
                "request": {"sender": "me", "timestamp": query_request_timestamp, "message": query},
                "response": {
                    "sender": "Docudive AI",
                    "timestamp": query_response_timestamp,
                    "message": chat_response,
                },
                "usage": {"tokens": total_tokens, "model": selected_model.name},
            }

            chat_history = {"conversation": [chat_history_entry]}

            try:
                """Load the chat history in S3"""
                content, _ = s3.get_object(bucket=chat_history_bucket, key=file_key)
                chat_history = json.loads(content.decode("utf-8"))
                chat_history["conversation"].append(chat_history_entry)
            except Exception as exception:
                logger.info("no chat history, creating")

            """Update the chat history in S3"""
            chat_history_str = json.dumps(chat_history)
            s3.put_object(
                body=chat_history_str,
                bucket=chat_history_bucket,
                key=file_key,
                content_type="application/json",
            )

            api_response = {
                "status": "success",
                "message": "chat complete",
                "details": {
                    "document_id": document_id,
                    "chat_id": chat_id,
                    "query_id": query_id,
                    "response": chat_response,
                    "chat_reset": chat_initialized,
                    "context_initialized": doc_context_initialized,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": selected_model.name,
                    "total_tokens": total_tokens,
                },
            }
            if chat_debug:
                api_response["debug"] = {
                    "max_tokens": selected_model.max_tokens,
                    "chat_context": chat_context,
                }

        except (MissingBodyParameter, UserNotFoundError, DocumentNotFoundError, RaiseCustomException) as e:
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except Exception as exception:
            error_id = uuid.uuid4()
            logger.exception("Exception occurred")
            logger.error(f"an error occured, id: {error_id} error: {exception}")
            return {
                "isBase64Encoded": False,
                "statusCode": 500,
                "body": f"error id:{error_id}",
                "headers": {"content-type": "application/json"},
            }
        else:
            session.commit()
            return {
                "isBase64Encoded": False,
                "statusCode": 200,
                "body": json.dumps(api_response),
                "headers": {"content-type": "application/json"},
            }
