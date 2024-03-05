import json
from pathlib import Path

from loguru import logger

from chat.chatgpt import ChatGPT
from chat.model_info import OpenAIModels
from chat.prompt_handler import prompt_handler, page_wise_questions
from chat.query_types import PromptResponse
from prompts.insights import InsightTypes
from text.scrape_prediction import TextDetScrapePrediction
from utils.annotation_types import AnnotationTypes

number_of_pages = 50


def prompt_headings(text_prediction: TextDetScrapePrediction, open_api_key=None, insight_type=None):
    question = (
        "\n\nConsider the given context and generate 1 heading and the corresponding summary. Suggest the "
        "heading text except introduction and conclusion. Make sure the the summary is in bullet points and should be in markup language"
        "The summary should include all the data points, facts and figures in minimum of 5 lines. "
        "The summary should contain as much information as possible. Form your answer in the following json "
        'format:\n{\n "heading": "heading text",\n "summary": "Summary text"\n}\n\ncontext:\n'
    )

    gpt_model = ChatGPT(model=OpenAIModels.get_model("gpt-3.5-turbo"), api_key=open_api_key, verbose=False)

    response_list, prompts, model_names, pages_per_iterations = page_wise_questions(
        text_prediction, question, gpt_model
    )

    print(gpt_model.get_total_amount())

    heading_summary_list = []
    loop_count = 1
    for response in response_list:
        try:
            cleaned_response = response.replace("\n", "").replace("\r", "").replace("\t", " ")
            heading_summary_dict = json.loads(cleaned_response)
            heading_summary_list.append(heading_summary_dict)
            loop_count += 1
        except Exception as e:
            logger.exception(e)
            continue

    information = {
        "model_name": model_names,
        "iteration_count": len(model_names),
        "pages_per_iterations": pages_per_iterations,
    }

    return PromptResponse(
        response=heading_summary_list,
        prompt=prompts,
        debug_info=information,
        gpt_model=gpt_model,
    )


def handler(event, _):
    return prompt_handler(event, prompt_headings, AnnotationTypes.HEADINGS)


def heading_test():
    from scrape.pymupdf_scrape import PyMuPDF

    pymu_obj = PyMuPDF(file_path=Path("/home/dulanj/cube/test_doc/nex-markets-data-protection-policy.pdf"))
    text_prediction: TextDetScrapePrediction = pymu_obj.predict()
    return prompt_headings(text_prediction)


if __name__ == "__main__":
    ret = heading_test()
    logger.info(json.dumps(ret.response, indent=4))
