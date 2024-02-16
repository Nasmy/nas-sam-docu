from pathlib import Path
from pprint import pprint

from loguru import logger

from chat.chatgpt import ChatGPT
from chat.prompt_handler import page_wise_questions
from functions.scrape.pymupdf_scrape import PyMuPDF
from text.scrape_prediction import TextDetScrapePrediction
from utils.util import load_multiple_json_files


def main():
    tmp_file_location = "assets/statistics.pdf"
    open_api_key = "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"
    question = 'Extract the following items from the given context \nAuthor Information\nContent Quality and Originality\nWriting Style and Clarity\nConsistency and Coherence\nTitle and Metadata\nPeer Review Feedback. If any of the items does not exist, then please provide the answer as \"Information does not exist\". Make sure in your answer you only include the items and not any other summarised answer. Form your answer in the following json format. Each json string should be in markup language. Each json node should include one example information only:\n\n{\n"item_name": {\n"item": "term_text",\n"term_description": "term_description"\n},\n...\n}'
    gpt_model = ChatGPT(api_key=open_api_key, verbose=False)

    pymu_obj = PyMuPDF(file_path=Path(tmp_file_location))
    text_prediction: TextDetScrapePrediction = pymu_obj.predict()

    response_list, prompts, model_names, pages_per_iterations = page_wise_questions(
        text_prediction, question, gpt_model
    )

    response_dict_list = {}
    loop_count = 1
    for index, response in enumerate(response_list):
        cleaned_response = "NA"
        try:
            cleaned_response = response.replace("\n", "").replace("\r", "").replace("\t", " ")
            logger.info(f"No: {index} | Response: {cleaned_response}")
            for current_dict in load_multiple_json_files(cleaned_response):
                logger.info(f"No: {index} | LC: {loop_count} | Response: {current_dict}")
                for item_key, item_dict in current_dict.items():
                    response_dict_list.setdefault(item_key, []).append(item_dict)
                    loop_count += 1
        except Exception as e:
            logger.warning(cleaned_response)
            logger.exception(e)
            continue

    print(response_dict_list)


if __name__ == '__main__':
    main()