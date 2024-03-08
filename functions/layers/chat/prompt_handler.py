import json
import os
import pickle
import uuid
from datetime import datetime

import boto3
from loguru import logger

from chat.model_info import ModelInfo, OpenAIModels
from chat.query_types import PromptResponse
from db.chat_cost import ChatCost
from db.database import Database
from text.scrape_prediction import TextDetScrapePrediction
from text.timer import Timer

# initialize s3 client
s3 = boto3.client("s3")
predict_bucket_name = os.getenv("predict_bucket_name")
output_bucket = os.getenv("output_bucket")


def prompt_handler(event, function, annotation_type):
    try:
        logger.info(event)
        file_key = event["detail"]["object"]["key"]  # replace with your object key
        # Fetch the file from S3
        obj = s3.get_object(Bucket=predict_bucket_name, Key=file_key)
        logger.info(f"File downloaded from s3 - {predict_bucket_name}:{file_key}")
        user_id = obj["Metadata"]["user_id"]
        document_id = obj["Metadata"]["document_id"]
        input_text_prediction = obj["Metadata"]["text_prediction"]
        file_content = obj["Body"].read()
        logger.info(f"User id: {user_id}, document id: {document_id}")

        # Load the pickled data
        text_prediction: TextDetScrapePrediction = pickle.loads(file_content)

        # Prompt questions
        prompt_object = None
        try:
            # start and end time using datetime module
            stat_time = datetime.utcnow()
            prompt_object: PromptResponse = function(text_prediction)

            end_time = datetime.utcnow()
            time_taken = end_time - stat_time
            logger.info(f"Time taken to generate response: {time_taken}")

            logger.info(prompt_object.response)
            output_dict = {
                "status": "success",
                "message": "Successfully extracted headings and summaries",
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
            logger.error(e)
            output_dict = {
                "status": "failed",
                "message": "Failed to extracted headings and summaries",
                "details": {
                    "response": "",
                },
                "debug": {
                    "prompt": prompt_object.prompt if prompt_object else "NA",
                    "error": f"Failed to extract: {str(e)}",
                },
            }

        query_id = str(uuid.uuid4())

        # Add metadata
        output_dict["debug"]["input_file"] = file_key
        output_dict["debug"]["text_prediction"] = input_text_prediction

        output_dict["details"]["query_id"] = query_id
        output_dict["details"]["annotation_type"] = annotation_type
        output_dict["details"]["timestamp"] = datetime.utcnow().isoformat()

        # Upload the questions to S3
        upload_key = f"{user_id}/{document_id}/{document_id}-{annotation_type.value}.json"
        s3.put_object(Body=json.dumps(output_dict, indent=4), Bucket=output_bucket, Key=upload_key)
        logger.info(f"Uploaded file to s3 - {output_bucket}:{upload_key}")

        # Update the database
        database = Database()
        p_gpt_model = prompt_object.gpt_model
        with database.get_session() as session:
            chat_cost = ChatCost(
                id=str(uuid.uuid4()),
                user_id=user_id,
                document_id=document_id,
                chat_id="NA",
                query_id=query_id,
                query_type=f"{annotation_type.value}",
                model_name=p_gpt_model.get_current_model() if p_gpt_model else "NA",
                prompt_tokens=p_gpt_model.get_prompt_tokens() if p_gpt_model else 0,
                completion_tokens=p_gpt_model.get_completion_tokens() if p_gpt_model else 0,
                total_tokens=p_gpt_model.get_total_tokens() if p_gpt_model else 0,
                prompt_1k_cost=p_gpt_model.get_prompt_1k_cost() if p_gpt_model else 0,
                completion_1k_cost=p_gpt_model.get_completion_1k_cost() if p_gpt_model else 0,
                total_amount=p_gpt_model.get_total_amount() if p_gpt_model else 0,
            )
            session.add(chat_cost)
            session.commit()
        database.close_connection()

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Success", "key": upload_key}),
        }
    except Exception as e:
        logger.exception(e)
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
        logger.info(f"start_page: {start_page}, end_page: {end_page}")
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
