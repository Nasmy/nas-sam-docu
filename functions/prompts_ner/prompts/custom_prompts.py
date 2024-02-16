import os

from loguru import logger

from chat.chatgpt import ChatGPT
from chat.prompt_handler import page_wise_questions
from chat.query_types import PromptResponse
from prompts.insights import InsightTypes
from text.scrape_prediction import TextDetScrapePrediction
from utils.custom_exceptions import MissingEnvironmentVariableError
from utils.util import load_multiple_json_files


def is_item_valid(item_key, item_dict):
    if len(item_dict) == 0:
        return False

    if not item_key:
        return False
    all_values = list(item_dict.values())
    if any(not x for x in all_values):
        return False

    should_not_list = ['does not exist', 'none']
    if any(x in item_key.lower() for x in should_not_list):
        return False
    if any(x in y.lower() for y in all_values for x in should_not_list):
        return False

    return True


def dict_list_prompt(text_prediction: TextDetScrapePrediction, open_api_key=None, insight_type=InsightTypes.ESSENTIAL):
    """
    This function is used to prompt questions to the user
    Expected output is a list of dictionaries
    """
    question = os.getenv("QUESTION")
    if not question:
        raise MissingEnvironmentVariableError("QUESTION")

    gpt_model = ChatGPT(api_key=open_api_key, verbose=False)

    response_list, prompts, model_names, pages_per_iterations = page_wise_questions(
        text_prediction, question, gpt_model
    )

    response_dict_list = {} if insight_type == InsightTypes.BUSINESS else []
    loop_count = 1
    for index, response in enumerate(response_list):
        cleaned_response = "NA"
        try:
            cleaned_response = response.replace("\n", "").replace("\r", "").replace("\t", " ")
            logger.info(f"No: {index} | Response: {cleaned_response}")
            for current_dict in load_multiple_json_files(cleaned_response):
                logger.info(f"No: {index} | LC: {loop_count} | Response: {current_dict}")
                if insight_type == InsightTypes.BUSINESS:
                    for item_key, item_dict in current_dict.items():
                        if not is_item_valid(item_key, item_dict):
                            continue
                        response_dict_list.setdefault(item_key, []).append(item_dict)
                        loop_count += 1
                else:
                    for _, item_dict in current_dict.items():
                        response_dict_list.append(item_dict)
                        loop_count += 1
        except Exception as e:
            logger.warning(cleaned_response)
            logger.exception(e)
            continue

    information = {
        "model_name": model_names,
        "iteration_count": len(model_names),
        "pages_per_iterations": pages_per_iterations,
        "question": question,
        "response": response_list
    }

    return PromptResponse(
        response=response_dict_list,
        prompt=prompts,
        debug_info=information,
        gpt_model=gpt_model,
    )
