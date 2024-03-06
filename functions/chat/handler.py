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
s3_dd = S3Wrapper()
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
                    file_key = f"{db_user_id}/{db_document_id}{db_doc_ext}"
                    logger.info(bucket_name)
                    # image, _ = s3_dd.load_image_from_s3(bucket_name, file_key)
                    # print(image)

                    # body, _ = s3_dd.s3_get_object(bucket=bucket_name, key=file_key)
                    # print("Length of binary data:", len(body))

                    # Encode the binary image data to base64
                    # image_string = base64.b64encode(body).decode('utf-8')  # Convert bytes to string

                    # Check the type and length of the 'image_string' variable
                    # print(type(image_string))
                    # print(len(image_string))
                    prompt = {
                     "image_string": file_key,
                     "questions": query
                    }

                    gpt_vision = ChatGptVision(db_api_key.api_key, selected_model, prompt)
                    chat_response = gpt_vision.analyse_image_string()
                else:
                    chat_response = gpt_model.chat_with_context(prompt=query)

                print(chat_response)
        except Exception as e:
            return f"error {e}"
