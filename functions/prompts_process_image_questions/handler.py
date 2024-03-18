import json

from loguru import logger

from chat.chatgpt import ChatGPT
from chat.chatgpt_vision import ChatGptVision
from chat.model_info import OpenAIModels, ModelInfo
from chat.prompt_image_handler import prompt_image_handler
from chat.query_types import PromptResponse
from utils.annotation_types import AnnotationTypes


def prompt_process_image_questions(image_url=None, open_api_key=None, insight_type=None):
    # Get the model
    question = (
        "\n\nBased on the image, suggest me 5 important possible questions and relevant answers."
        "Form your answer in the following exact json inside a list "
        'format:\n[{\n "question": "question text",\n "answer": "answer text"\n}]\n'
    )

    question_word_count = len(question.split(" "))

    promptData = f"{image_url} - {question}"

    model: ModelInfo = OpenAIModels.get_model("gpt-4-vision-preview")

    information = {
        "model_name": model.name,
        "model_max_words": model.max_words,
        "model_max_tokens": model.max_tokens,
        "question_word_count": question_word_count,
    }

    gpt_model = ChatGPT(model=model, api_key=open_api_key, verbose=True)
    prompt = {
        "image_string": image_url,
        "questions": question
    }

    chat_response = ChatGptVision(open_api_key, "gpt-4-vision-preview", prompt)
    received_string = chat_response.gpt_analysis_image_url()
    received_string = received_string.strip('```json')
    received_string = received_string.strip('```')
    received_string = received_string.replace('\n', '\\n')
    questions_output_list = []
    question_and_answer_list = json.loads(received_string)
    try:
        for i, qa_dict in enumerate(question_and_answer_list):
            questions_output_list.append(qa_dict)
    except Exception as e:
        logger.error(e)

    return PromptResponse(response=questions_output_list, prompt=promptData, debug_info=information, gpt_model=gpt_model)


def handler(event, _):
    return prompt_image_handler(event, prompt_process_image_questions, AnnotationTypes.QUESTIONS)
