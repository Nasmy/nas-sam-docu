import json
import os
import pickle
import uuid
from datetime import datetime

from loguru import logger

from aws.aws_s3 import S3Wrapper
from chat.chat_types import ChatTypes
from chat.model_info import ModelInfo, OpenAIModels
from chat.query_types import PromptResponse
from db.database import Database
from db.tables import Chats, Queries, Models, APIKeys, AnnotationTypesTable, Annotations
from text.scrape_prediction import TextDetScrapePrediction
from text.timer import Timer
from utils.annotation_types import AnnotationStatus, get_insight_type
from utils.custom_exceptions import RaiseCustomException

# initialize s3 client
dd_s3 = S3Wrapper()
predict_bucket_name = os.getenv("image_predict_bucket_name")
output_bucket = os.getenv("image_output_bucket")


def prompt_image_handler(event, function, annotation_type):
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:

            file_key = event["detail"]["object"]["key"]  # replace with your object key
            # Fetch the file from S3
            file_content, metadata_dict = dd_s3.s3_get_object(bucket=predict_bucket_name, key=file_key)
            user_id = metadata_dict["user_id"]
            document_id = metadata_dict["document_id"]
            logger.info(f"Meta Dictionary {metadata_dict}")
            """
            input_text_prediction = metadata_dict["text_prediction"]
            logger.info(f"User id: {user_id}, document id: {document_id}")

            # update annotations table
            db_annotations = (
                session.query(Annotations)
                .join(AnnotationTypesTable, AnnotationTypesTable.id == Annotations.annotation_type_id)
                .filter(Annotations.document_id == document_id)
                .filter(AnnotationTypesTable.name == annotation_type.value)
                .first()
            )
            if db_annotations:
                db_annotations.status = AnnotationStatus.IN_PROGRESS.value
                session.commit()

            # Load openapi key
            db_api_key = session.query(APIKeys).filter(APIKeys.service_key == "openai_key1").first()

            # Load the pickled data
            text_prediction: TextDetScrapePrediction = pickle.loads(file_content)

            # Prompt questions
            prompt_object = None
            try:
                # start and end time using datetime module
                stat_time = datetime.utcnow()
                prompt_object: PromptResponse = function(
                    text_prediction,
                    open_api_key=db_api_key.api_key,
                    insight_type=get_insight_type(annotation_type)
                )

                end_time = datetime.utcnow()
                time_taken = end_time - stat_time
                logger.info(f"Time taken to generate response: {time_taken}")

                logger.info(prompt_object.response)
                if not prompt_object.response:
                    raise RaiseCustomException(204, "Annotations are empty", prompt_object.response)

                output_dict = {
                    "status": "success",
                    "message": f"Successfully extracted {annotation_type.value}",
                    "details": {
                        "response": prompt_object.response,
                    },
                    "debug": {
                        "prompt": prompt_object.prompt,
                        "start_time": stat_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "time_taken": f"{time_taken.seconds} seconds",
                    },
                }
                # add more information dictionary content to debug
                output_dict["debug"].update(prompt_object.debug_info)
            except Exception as e:
                logger.exception(e)
                raise e

            query_id = str(uuid.uuid4())

            # Add metadata
            output_dict["debug"]["input_file"] = file_key
            output_dict["debug"]["text_prediction"] = input_text_prediction

            output_dict["details"]["query_id"] = query_id
            output_dict["details"]["annotation_type"] = annotation_type
            output_dict["details"]["timestamp"] = datetime.utcnow().isoformat()

            # Upload the annotations to S3
            upload_key = f"{user_id}/{document_id}/{document_id}-{annotation_type.value}.json"
            dd_s3.s3_put_object(body=json.dumps(output_dict, indent=4), bucket=output_bucket, key=upload_key)

            # Update the database
            p_gpt_model = prompt_object.gpt_model
            if p_gpt_model:
                chat_id = str(uuid.uuid4())
                new_chat = Chats(
                    id=chat_id,
                    document_id=document_id,
                    chat_name=f"{annotation_type.value}",
                    chat_type=ChatTypes.ANNOTATIONS.value,
                )
                session.add(new_chat)
                session.flush()

                model_name = p_gpt_model.get_current_model()
                db_model = session.query(Models).filter(Models.name == model_name).first()

                prompt_tokens = p_gpt_model.get_prompt_tokens()
                completion_tokens = p_gpt_model.get_completion_tokens()
                prompt_1k_cost = db_model.prompt_1k_cost
                completion_1k_cost = db_model.completion_1k_cost
                total_cost = prompt_tokens * prompt_1k_cost + completion_tokens * completion_1k_cost

                chat_cost = Queries(
                    id=query_id,
                    chat_id=new_chat.id,
                    model_id=db_model.id,
                    api_key_id=db_api_key.id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    prompt_1k_cost=prompt_1k_cost,
                    completion_1k_cost=prompt_1k_cost,
                    total_amount=total_cost,
                )
                session.add(chat_cost)

            if db_annotations:
                db_annotations.status = AnnotationStatus.COMPLETED.value

        except Exception as e:
            logger.exception(e)
            session.rollback()
            logger.info("Session rollback")
            status_code = e.status_code if hasattr(e, "status_code") else 500
            if db_annotations:
                db_annotations.status = AnnotationStatus.FAILED.value if status_code != 204 else AnnotationStatus.EMPTY.value
            session.commit()
            logger.info("Session commit")
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "Failed", "error": str(e)}),
            }
        else:
            session.commit()
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Success", "key": upload_key}),
            }
            """""
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "Failed", "error": str(e)}),
            }


def page_wise_questions(text_prediction: TextDetScrapePrediction, question, gpt_model):
    no_of_pages = len(text_prediction.pages)
    pages_per_iterations = predict_pages_per_iterations(no_of_pages)
    logger.info(f"no_of_pages: {no_of_pages}, pages_per_iterations: {pages_per_iterations}")

    model_names = []
    prompts = []
    response_list = []

    start_page = 1
    for end_page in range(1, no_of_pages + 1 + pages_per_iterations, pages_per_iterations):
        if end_page == 1:
            continue
        logger.info(f"start_page: {start_page}, end_page: {end_page}, total_pages: {no_of_pages}")
        with Timer(f"prompt_headings start_page: {start_page}, end_page: {end_page}"):
            selected_text = "\n\n".join(
                [text_prediction.get_text(page_number=page_no) for page_no in range(start_page, end_page)]
            )

            selected_text_word_len = len(selected_text.split(" "))
            logger.info(f"selected_text_word_len: {selected_text_word_len}")
            if selected_text_word_len < int(os.getenv("MINIMUM_WORD_COUNT", 75)):
                continue

            prompt = question + selected_text
            # logger.info(prompt)
            total_expected_word_count = len(prompt.split(" ")) + 500
            model: ModelInfo = OpenAIModels.get_model_based_on_text_length(total_expected_word_count)
            model_names.append(model.name)

            gpt_model.set_model(model=model)
            logger.info("Total cost: " + str(gpt_model.get_total_amount()))
            gpt_model.reset_context()
            response = gpt_model.chat_with_context(prompt)
            prompts.append(prompt)

            start_page = end_page
            logger.info(f"response: {response}")
            response_list.append(response)
    return response_list, prompts, model_names, pages_per_iterations


def predict_pages_per_iterations(number_of_pages):
    if number_of_pages < 5:
        pages_per_iterations = 1
    elif number_of_pages <= 20:
        pages_per_iterations = 2
    else:
        pages_per_iterations = 3
    return pages_per_iterations
