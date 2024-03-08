from pathlib import Path

from loguru import logger

from chat.chatgpt import ChatGPT
from chat.model_info import OpenAIModels
from chat.prompt_handler import prompt_handler, page_wise_questions
from chat.query_types import PromptResponse
from text.scrape_prediction import TextDetScrapePrediction
from utils.annotation_types import AnnotationTypes


def load_multiple_json_files(data_string):
    """
    # Input format example
    data_string = '{"name": "Alice", "age": 25}{"country": "USA", "capital": "Washington"}'
    """
    import json

    parsed_data = []

    while data_string:
        try:
            obj, idx = json.JSONDecoder().raw_decode(data_string)
            parsed_data.append(obj)
            data_string = data_string[idx:].lstrip()
        except json.JSONDecodeError:
            break

    return parsed_data


def prompt_timeline(text_prediction: TextDetScrapePrediction):
    question = (
        "Extract a timeline if exists in the context. If a timeline does not exist, then please provide the answer as "
        '"no timeline". Make sure in your answer you only include the timeline and not any other summarised answer. '
        "Form your answer in the following json format. Each json node should include one timeline information only:"
        '\n\n{\n "Time": "time element",\n "summary": "Summary text"\n}\n\ncontext:\n'
    )

    gpt_model = ChatGPT(model=OpenAIModels.get_model("gpt-3.5-turbo"), verbose=False)

    response_list, prompts, model_names, pages_per_iterations = page_wise_questions(
        text_prediction, question, gpt_model
    )

    timeline_summary_list = []
    loop_count = 1
    for response in response_list:
        cleaned_response = "NA"
        try:
            cleaned_response = response.replace("\n", "").replace("\r", "").replace("\t", " ")
            for timeline_summary_dict in load_multiple_json_files(cleaned_response):
                # timeline_summary_dict = json.loads(cleaned_response)
                timeline_summary_dict[f"T{loop_count}"] = timeline_summary_dict.pop("Time")
                timeline_summary_dict[f"S{loop_count}"] = timeline_summary_dict.pop("summary")
                timeline_summary_list.append(timeline_summary_dict)
                loop_count += 1
        except Exception as e:
            logger.warning(cleaned_response)
            logger.error(e)
            continue

    information = {
        "model_name": model_names,
        "iteration_count": len(model_names),
        "pages_per_iterations": pages_per_iterations,
    }

    timeline_summary_dict = {
        "timeline": timeline_summary_list,
    }

    return PromptResponse(
        response=timeline_summary_dict,
        prompt=prompts,
        debug_info=information,
        gpt_model=gpt_model,
    )


def handler(event, _):
    return prompt_handler(event, prompt_timeline, AnnotationTypes.TIMELINE)


"""
This is a test function to test the prompt_questions function
"""


def docudive_test():
    from scrape.pymupdf_scrape import PyMuPDF

    pymu_obj = PyMuPDF(file_path=Path("/home/dulanj/cube/test_doc/nex-markets-data-protection-policy.pdf"))
    text_prediction: TextDetScrapePrediction = pymu_obj.predict()

    return prompt_timeline(text_prediction)


if __name__ == "__main__":
    import json

    prompt_res = docudive_test()
    logger.info(json.dumps(prompt_res.response, indent=4))
