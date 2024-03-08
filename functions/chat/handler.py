import json
import os
import random
import uuid
from datetime import datetime

import boto3
from loguru import logger

from chat.chatgpt import ChatGPT
from chat.model_info import OpenAIModels, ModelInfo
from chat.query_types import QueryTypes, ContextTypes
from context_loader import ContextLoader
from db.chat_cost import ChatCost
from db.database import Database
from db.document_chat import DocumentChat
from db.documents import Documents
from db.users import Users

s3 = boto3.client("s3")
files_digest_bucket = os.getenv("files_digest_bucket")
chat_context_bucket = os.getenv("chat_context_bucket")
chat_history_bucket = os.getenv("chat_history_bucket")


def generate_random_string(length: int) -> str:
    """
    Generate a random string of the given length using characters a-z and underscore.

    Args:
    - length (int): Desired length of the random string.

    Returns:
    - str: Randomly generated string.
    """
    characters = "abcdefghijklmnopqrstuvwxyz_"
    return "".join(random.choice(characters) for _ in range(length))


def handler(event, _):
    """
    Chat handler for the chatbot
    1. Upgrade to context based chatbot
    """
    logger.info(event)
    try:
        database = Database()

        body = event.get("body", None)
        username = event["requestContext"]["authorizer"]["lambda"]["user"]
        body = json.loads(body)

        document_id = body.get("document_id", None)
        chat_id = body.get("chat_id", None)
        chat_name = body.get("chat_name", None)
        query_id = body.get("query_id", None)
        query = body.get("query", None)
        doc_context = body.get("context", None)
        reset_context = body.get("reset_context", None)
        chat_debug = body.get("debug", None)
        logger.info(f"{username}, {document_id}, {query_id}, {query}")

        if not (chat_id or chat_name):
            return {
                "isBase64Encoded": False,
                "statusCode": 400,
                "body": json.dumps({"status": "failed", "message": "chat_id or chat_name is required"}),
                "headers": {"content-type": "application/json"},
            }

        if username and document_id and query and (chat_name or chat_id) and (not query_id or len(query_id) <= 36):

            if not query_id:
                # If query_id is not present, create a new one
                # why: Query id is not that important, but it is useful when tracking multiple queries
                query_id = str(uuid.uuid4())

            with database.get_session() as session:
                user = session.query(Users).filter(Users.username == username).first()
                if user:
                    user_id = user.id
                    document = (
                        session.query(Documents)
                        .filter(Documents.user_id == user_id, Documents.document_id == document_id)
                        .first()
                    )
                    if document:
                        if chat_id:
                            doc_chat = (
                                session.query(DocumentChat)
                                .filter(DocumentChat.chat_id == chat_id, DocumentChat.document_id == document_id)
                                .first()
                            )
                            if not doc_chat:
                                logger.info("Invalid chat id!")
                                return {
                                    "isBase64Encoded": False,
                                    "statusCode": 400,
                                    "body": f"Invalid chat id! - {chat_id}",
                                }
                        else:
                            doc_chat = (
                                session.query(DocumentChat)
                                .filter(DocumentChat.chat_name == chat_name, DocumentChat.document_id == document_id)
                                .first()
                            )
                            if not doc_chat:
                                doc_chat = DocumentChat(
                                    id=str(uuid.uuid4()),
                                    document_id=document_id,
                                    chat_id=str(uuid.uuid4()),
                                    chat_name=chat_name,
                                )
                                session.add(doc_chat)
                                session.commit()
                                reset_context = True

                            chat_id = doc_chat.chat_id

                        file_key = f"{user_id}/{document_id}/{chat_id}.json"
                        chat_initialized = True
                        try:
                            if not reset_context:
                                response = s3.get_object(Bucket=chat_context_bucket, Key=file_key)
                                chat_context = json.loads(response["Body"].read().decode("utf-8"))
                                logger.info("chat context loaded!")
                                chat_initialized = False
                            else:
                                chat_context = {"conversation": []}
                                logger.info("chat context reset!")
                        except Exception as _:
                            chat_context = {"conversation": []}

                        doc_context_initialized = False
                        context_type = None
                        if chat_initialized and doc_context:
                            context_loader_obj = ContextLoader(user_id, document_id, doc_context)
                            chat_context, context_type = context_loader_obj.load_context_and_type()
                            if chat_context:
                                doc_context_initialized = True

                        query_request_timestamp = datetime.utcnow().isoformat()
                        if doc_context_initialized and context_type == ContextTypes.QUESTION.value:
                            # If the context is question, then we need to add the question to the chat context
                            # last_context_dict = chat_context["conversation"][-1]
                            # query = f"{last_context_dict['content']}"
                            # chat_context["conversation"] = chat_context["conversation"][:-1]
                            query = chat_context["question"]
                            chat_response = chat_context["answer"]
                            query_response_timestamp = datetime.utcnow().isoformat()
                            total_tokens = 0
                            selected_model = OpenAIModels.get_model("gpt-3.5-turbo")
                        else:
                            # Set OPENAI_API_KEY as environment variable
                            full_word_count = ContextLoader.context_length(chat_context) + query.count(" ")
                            selected_model: ModelInfo = OpenAIModels.get_model_based_on_text_length(full_word_count)

                            gpt_model = ChatGPT(selected_model)
                            gpt_model.set_context_dict(chat_context)
                            chat_response = gpt_model.chat_with_context(prompt=query)

                            query_response_timestamp = datetime.utcnow().isoformat()
                            total_tokens = gpt_model.get_total_tokens()
                            logger.info(f"Total tokens used: {total_tokens}")

                            with database.get_session() as session:
                                chat_cost = ChatCost(
                                    id=str(uuid.uuid4()),
                                    user_id=user_id,
                                    document_id=document_id,
                                    chat_id=chat_id,
                                    query_id=query_id,
                                    query_type=f"{QueryTypes.CHAT.value}",
                                    model_name=selected_model.name,
                                    prompt_tokens=gpt_model.get_prompt_tokens(),
                                    completion_tokens=gpt_model.get_completion_tokens(),
                                    total_tokens=gpt_model.get_total_tokens(),
                                    prompt_1k_cost=gpt_model.get_prompt_1k_cost(),
                                    completion_1k_cost=gpt_model.get_completion_1k_cost(),
                                    total_amount=gpt_model.get_total_amount(),
                                )
                                session.add(chat_cost)
                                session.commit()

                            # Get chat history dictionary
                            chat_context_output = gpt_model.get_context_dict()
                            json_str = json.dumps(chat_context_output)

                            try:
                                # Put the JSON string to S3
                                s3.put_object(
                                    Body=json_str,
                                    Bucket=chat_context_bucket,
                                    Key=file_key,
                                    ContentType="application/json",
                                )
                            except Exception as exception:
                                logger.info("failed to update object")

                        # Chat history
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
                            response = s3.get_object(Bucket=chat_history_bucket, Key=file_key)
                            chat_history = json.loads(response["Body"].read().decode("utf-8"))
                            chat_history["conversation"].append(chat_history_entry)
                        except Exception as exception:
                            logger.info("no chat history, creating")

                        chat_history_str = json.dumps(chat_history)
                        s3.put_object(
                            Body=chat_history_str,
                            Bucket=chat_history_bucket,
                            Key=file_key,
                            ContentType="application/json",
                        )

                        database.close_connection()

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

                        return {
                            "isBase64Encoded": False,
                            "statusCode": 200,
                            "body": json.dumps(api_response),
                            "headers": {"content-type": "application/json"},
                        }
                    api_response = {
                        "status": "failed",
                        "message": "document not found",
                        "details": {"query_id": query_id, "document_id": document_id},
                    }
                    return {
                        "isBase64Encoded": False,
                        "statusCode": 400,
                        "body": json.dumps(api_response),
                        "headers": {"content-type": "application/json"},
                    }
                api_response = {
                    "status": "failed",
                    "message": "user not found",
                    "details": {"query_id": query_id, "document_id": document_id},
                }
                return {
                    "isBase64Encoded": False,
                    "statusCode": 401,
                    "body": json.dumps(api_response),
                    "headers": {"content-type": "application/json"},
                }

        api_response = {
            "status": "failed",
            "message": "incomplete request",
            "details": {"query_id": query_id, "document_id": document_id, "response": None},
        }

        return {
            "isBase64Encoded": False,
            "statusCode": 400,
            "body": json.dumps(api_response),
            "headers": {"content-type": "application/json"},
        }
    except Exception as exception:
        database.close_connection()
        error_id = uuid.uuid4()
        logger.exception("Exception occurred")
        logger.error(f"an error occured, id: {error_id} error: {exception}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": f"error id:{error_id}",
            "headers": {"content-type": "application/json"},
        }
