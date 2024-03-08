from loguru import logger

from chat.chatgpt import ChatGPT
from chat.model_info import OpenAIModels, ModelInfo
from chat.prompt_handler import prompt_handler
from chat.query_types import PromptResponse
from text.scrape_prediction import TextDetScrapePrediction
from utils.annotation_types import AnnotationTypes
from utils.custom_exceptions import RaiseCustomException


def prompt_summary(text_prediction: TextDetScrapePrediction, open_api_key=None, insight_type=None):
    # Get the model
    # question = "Give me short summary in 300 words max for the above context."
    question = (
        "Give me short summary in maximum of 300 for the context. Make sure the answer is in single or "
        "multiple paragraph format. Avoid any bullet points, headings and subheadings"
    )
    question_word_count = len(question.split(" "))
    document_word_count = text_prediction.get_word_count()
    expected_response_word_count = 300
    total_expected_word_count = document_word_count + question_word_count + expected_response_word_count
    logger.info(
        f"Question word count: {question_word_count}, Document word count: {document_word_count}, "
        f"Expected response word count: {expected_response_word_count}, Total word count: {total_expected_word_count}"
    )
    model: ModelInfo = OpenAIModels.get_model_based_on_text_length(total_expected_word_count)

    max_document_content = model.max_words - question_word_count - expected_response_word_count
    selected_text = text_prediction.get_text(word_limit=max_document_content)
    selected_word_count = len(selected_text.split(" "))
    prompt = f"{selected_text}  - {question}"

    information = {
        "model_name": model.name,
        "model_max_words": model.max_words,
        "model_max_tokens": model.max_tokens,
        "question_word_count": question_word_count,
        "document_word_count": document_word_count,
        "expected_response_word_count": expected_response_word_count,
        "total_expected_word_count": total_expected_word_count,
        "document_word_count_limit": max_document_content,
        "selected_word_count": selected_word_count,
        "percentage_of_document_used_for_prediction": f"{round(selected_word_count * 100 / document_word_count, 2)}%",
    }

    gpt_model = ChatGPT(model=model, api_key=open_api_key)
    gpt_model.reset_context()
    response = gpt_model.chat_with_context(prompt)
    if not response:
        raise RaiseCustomException(204, "No content", response)
    summary_output = {"summary": response.replace("\n", " ").replace("  ", " ")}

    return PromptResponse(response=summary_output, prompt=prompt, debug_info=information, gpt_model=gpt_model)


def handler(event, _):
    return prompt_handler(event, prompt_summary, AnnotationTypes.SUMMARIES)


"""
This is a test function to test the prompt_summary function
"""


def docudive_test():
    # pickle load
    with open("/home/dulanj/PycharmProjects/docudive-backend/text_prediction.pickle", "rb") as f:
        import pickle

        text_prediction = pickle.load(f)

    return prompt_summary(text_prediction)


if __name__ == "__main__":
    import json

    prompt_res = docudive_test()
    logger.info(json.dumps(prompt_res.response, indent=4))
