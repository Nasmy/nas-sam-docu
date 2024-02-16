from chat.prompt_handler import prompt_handler
from chat.query_types import PromptResponse
from info_extractor import extract_info
from text.scrape_prediction import TextDetScrapePrediction
from utils.annotation_types import AnnotationTypes


def info_snippets(text_prediction: TextDetScrapePrediction, open_api_key=None, insight_type=None):
    all_text = text_prediction.get_text()
    all_info_dict = extract_info(all_text)

    return PromptResponse(
        response=all_info_dict,
        prompt="",
        debug_info={},
        gpt_model=None,
    )


def handler(event, _):
    return prompt_handler(event, info_snippets, AnnotationTypes.INFO_SNIPPETS)
