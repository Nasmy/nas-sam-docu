from chat.prompt_handler import prompt_handler
from prompts.custom_prompts import dict_list_prompt
from utils.annotation_types import AnnotationTypes


def handler(event, _):
    return prompt_handler(event, dict_list_prompt, AnnotationTypes.CITED_EXAMPLES)
