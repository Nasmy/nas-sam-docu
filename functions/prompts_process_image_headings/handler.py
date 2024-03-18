import json

from loguru import logger

from chat.chatgpt import ChatGPT
from chat.chatgpt_vision import ChatGptVision
from chat.model_info import OpenAIModels, ModelInfo
from chat.prompt_image_handler import prompt_image_handler
from chat.query_types import PromptResponse
from utils.annotation_types import AnnotationTypes


def prompt_process_image_headings(image_url=None, open_api_key=None, insight_type=None):
    question = (
        "\n\nConsider the given image and generate 1 heading and the corresponding summary. Suggest the "
        "heading text except introduction and conclusion. Make sure the the summary is in bullet points. "
        "The summary should include all the data points, facts and figures in minimum of 5 lines. "
        "The summary should contain as much information as possible. Form your answer in the following json "
        'format:\n{\n "heading": "heading text",\n "summary": "Summary text"\n}\n\nimage:\n'
    )

    promptData = f"{image_url} - {question}"
    model: ModelInfo = OpenAIModels.get_model("gpt-4-vision-preview")
    gpt_model = ChatGPT(model=model, api_key=open_api_key, verbose=True)
    prompt = {
        "image_string": image_url,
        "questions": question
    }

    chat_response = ChatGptVision(open_api_key, "gpt-4-vision-preview", prompt)
    received_string = chat_response.gpt_analysis_image_url()
    heading_summary_list = []
    # cleaned_response = response_list_data.replace("\n", "").replace("\r", "").replace("\t", " ")
    received_string = received_string.strip('```json')
    received_string = received_string.strip('```')
    cleaned_response = received_string.replace("\n", "").replace("\r", "").replace("\t", " ")
    heading_summary_dict = json.loads(cleaned_response)
    # heading_summary_list.append(heading_summary_dict)
    try:
        for i, qa_dict in enumerate(heading_summary_dict):
            heading_summary_list.append(qa_dict)
    except Exception as e:
        logger.error(e)

    logger.info(f"heading - {heading_summary_list}")

    information = {
        "model_name": model.name
    }

    return PromptResponse(
        response=heading_summary_list,
        prompt=promptData,
        debug_info=information,
        gpt_model=gpt_model
    )


def handler(event, _):
    return prompt_image_handler(event, prompt_process_image_headings, AnnotationTypes.HEADINGS)
