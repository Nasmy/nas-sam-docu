import json

from loguru import logger

from chat.chatgpt import ChatGPT
from chat.model_info import OpenAIModels, ModelInfo
from chat.prompt_image_handler import prompt_image_handler
from chat.query_types import PromptResponse
from text.scrape_prediction import TextDetScrapePrediction
from utils.annotation_types import AnnotationTypes


def prompt_process_image_questions():
    return "test"


def handler(event, _):
    return prompt_image_handler(event, prompt_process_image_questions, AnnotationTypes.QUESTIONS)
