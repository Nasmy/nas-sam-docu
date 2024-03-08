import spacy
from loguru import logger

from chat.prompt_handler import prompt_handler
from chat.query_types import PromptResponse
from text.scrape_prediction import TextDetScrapePrediction
from utils.annotation_types import AnnotationTypes

# Load the English NLP model
nlp = spacy.load("en_core_web_md")


display_name_dict = {
    "CARDINAL": "Number",
    "DATE": "Date",
    "EVENT": "Event",
    "FAC": "Facility",
    "GPE": "Geopolitical Entity",
    "LANGUAGE": "Language",
    "LAW": "Law",
    "LOC": "Location",
    "MONEY": "Money",
    "NORP": "Nationality or Religious or Political Group",
    "ORDINAL": "Ordinal Number",
    "ORG": "Organization",
    "PERCENT": "Percentage",
    "PERSON": "Person",
    "PRODUCT": "Product",
    "QUANTITY": "Quantity",
    "TIME": "Time",
    "WORK_OF_ART": "Work of Art"
}


def prompt_ner(text_prediction: TextDetScrapePrediction, open_api_key=None, insight_type=None):
    # Get the model
    selected_text = text_prediction.get_text()
    model = None

    # do ner using spacy
    doc = nlp(selected_text)
    entities_dict = {}
    for ent in doc.ents:
        entities_dict.setdefault(ent.label_, []).append(ent.text.strip())

    entities_list = []
    for label, entities in entities_dict.items():
        unique_list = list(set(entities))
        disp_name = display_name_dict.get(label, label)
        entities_list.append({"label": label, "display_name": disp_name, "entities": unique_list})
        logger.info(f"{label}| {disp_name}| {unique_list}")

    debug_info = {"model_name": "en_core_web_md", "library_name": "spacy"}
    labels_dict = {}  # labels are the list of annotations

    return PromptResponse(
        response=entities_list, prompt=selected_text, debug_info=debug_info, gpt_model=model, information=labels_dict
    )


def handler(event, _):
    return prompt_handler(event, prompt_ner, AnnotationTypes.NER)
